#!/usr/bin/env python
"""One-time seed script for Turso: batched multi-row VALUES inserts to avoid per-row HTTP round-trips.

Usage (after Turso DB created and env vars set):
    TURSO_DATABASE_URL=libsql://... TURSO_AUTH_TOKEN=... python backend/scripts/seed_turso.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import MOVIES_CSV
from app.database.seed import read_catalogue


BATCH_SIZE = 500


def _build_multirow_insert(table: str, columns: list[str], rows: list[dict]) -> str:
    """Build a single INSERT statement with multiple VALUES tuples."""
    cols = ", ".join(columns)
    placeholders = ", ".join(["(" + ", ".join([f":{c}_{i}" for c in columns]) + ")" for i in range(len(rows))])
    return f"INSERT INTO {table} ({cols}) VALUES {placeholders}"


def _flatten_batch_params(rows: list[dict], columns: list[str]) -> dict:
    """Convert list of row dicts to flat param dict for multi-row INSERT."""
    params = {}
    for i, row in enumerate(rows):
        for c in columns:
            params[f"{c}_{i}"] = row.get(c)
    return params


def _chunked(iterable, size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def main():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    if not turso_url or not turso_token:
        print("ERROR: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    import turso_serverless

    conn = turso_serverless.connect(turso_url, auth_token=turso_token)
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "app", "database", "schema.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        print("Schema applied")

        movies = read_catalogue(MOVIES_CSV)
        print(f"Read {len(movies)} movies from CSV")

        count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        if count > 0:
            print(f"Movies table already has {count} rows, skipping movie seed")
        else:
            movie_cols = [
                "movie_id", "title", "normalized_title", "release_year", "genres",
                "overview", "runtime", "popularity", "vote_average", "vote_count"
            ]
            total = 0
            for batch in _chunked(movies, BATCH_SIZE):
                sql = _build_multirow_insert("movies", movie_cols, batch)
                params = _flatten_batch_params(batch, movie_cols)
                conn.execute(sql, params)
                total += len(batch)
                print(f"  Inserted {total}/{len(movies)} movies...")
            conn.commit()
            print(f"Seeded {len(movies)} movies")

        genre_rows = [
            (movie["movie_id"], genre.strip())
            for movie in movies
            for genre in movie["genres"].split("|")
            if genre.strip()
        ]
        genre_count = conn.execute("SELECT COUNT(*) FROM movie_genres").fetchone()[0]
        if genre_count > 0:
            print(f"Genres table already has {genre_count} rows, skipping genre seed")
        else:
            total = 0
            for batch in _chunked(genre_rows, BATCH_SIZE):
                # genre_rows are tuples (movie_id, genre)
                genre_batch = [{"movie_id": m, "genre": g} for m, g in batch]
                sql = _build_multirow_insert("movie_genres", ["movie_id", "genre"], genre_batch)
                params = _flatten_batch_params(genre_batch, ["movie_id", "genre"])
                conn.execute(sql, params)
                total += len(batch)
                print(f"  Inserted {total}/{len(genre_rows)} genre rows...")
            conn.commit()
            print(f"Seeded {len(genre_rows)} genre rows")

        final_movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        final_genres = conn.execute("SELECT COUNT(*) FROM movie_genres").fetchone()[0]
        print(f"Verification: {final_movies} movies, {final_genres} genre rows")

    finally:
        conn.close()


if __name__ == "__main__":
    main()