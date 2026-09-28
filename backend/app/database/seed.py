import csv

from app.config import MAX_MASTER_MOVIES, MOVIES_CSV
from app.database.connection import connect
from app.services.auth_service import hash_password


def normalize_title(title: str) -> str:
    return " ".join(str(title).lower().split())


def _to_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def read_catalogue(csv_path: str | None = None) -> list[dict]:
    path = csv_path or MOVIES_CSV
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) > MAX_MASTER_MOVIES:
        raise ValueError(
            f"Master dataset contains {len(rows)} movies; the maximum allowed is {MAX_MASTER_MOVIES}."
        )
    movies = []
    for row in rows:
        movie_id = _to_int(row.get("movie_id"))
        title = (row.get("title") or "").strip()
        if movie_id is None or not title:
            continue
        movies.append(
            {
                "movie_id": movie_id,
                "title": title,
                "normalized_title": normalize_title(title),
                "release_year": _to_int(row.get("release_year")),
                "genres": (row.get("genres") or "").strip(),
                "overview": (row.get("overview") or "").strip(),
                "runtime": _to_float(row.get("runtime")),
                "popularity": _to_float(row.get("popularity")),
                "vote_average": _to_float(row.get("vote_average")),
                "vote_count": _to_int(row.get("vote_count")),
            }
        )
    return movies


def seed_movies(csv_path: str | None = None, db_path: str | None = None) -> int:
    """Load the master catalogue. Idempotent: does nothing if movies already exist."""
    movies = read_catalogue(csv_path)
    conn = connect(db_path)
    try:
        if conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0] > 0:
            return 0
        conn.executemany(
            """
            INSERT INTO movies
                (movie_id, title, normalized_title, release_year, genres,
                 overview, runtime, popularity, vote_average, vote_count)
            VALUES
                (:movie_id, :title, :normalized_title, :release_year, :genres,
                 :overview, :runtime, :popularity, :vote_average, :vote_count)
            """,
            movies,
        )
        genre_rows = [
            (movie["movie_id"], genre.strip())
            for movie in movies
            for genre in movie["genres"].split("|")
            if genre.strip()
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO movie_genres (movie_id, genre) VALUES (?, ?)",
            genre_rows,
        )
        conn.commit()
        return len(movies)
    finally:
        conn.close()


def seed_demo_user(db_path: str | None = None) -> int | None:
    """Create the demo account if it doesn't exist. Idempotent."""
    from app.database.repositories import UserRepository
    conn = connect(db_path)
    try:
        existing = UserRepository.get_by_email(conn, "demo@cinemine.dev")
        if existing:
            return None
        user_id = UserRepository.create(
            conn, "Demo User", "demo@cinemine.dev", hash_password("secret123")
        )
        conn.commit()
        return user_id
    finally:
        conn.close()