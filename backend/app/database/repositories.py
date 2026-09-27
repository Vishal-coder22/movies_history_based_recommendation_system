"""Hand-rolled SQL data access. Connections are owned by the caller."""

import json


def _row(row):
    return dict(row) if row is not None else None


class UserRepository:
    @staticmethod
    def create(conn, name: str, email: str, password_hash: str) -> int:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        return cursor.lastrowid

    @staticmethod
    def get_by_email(conn, email: str) -> dict | None:
        return _row(conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())

    @staticmethod
    def get_by_id(conn, user_id: int) -> dict | None:
        return _row(conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())


class MovieRepository:
    @staticmethod
    def count(conn) -> int:
        return conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]

    @staticmethod
    def get_all(conn) -> list[dict]:
        rows = conn.execute(
            "SELECT * FROM movies ORDER BY movie_id"
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn, movie_id: int) -> dict | None:
        return _row(conn.execute("SELECT * FROM movies WHERE movie_id = ?", (movie_id,)).fetchone())

    @staticmethod
    def get_genres(conn, movie_id: int) -> list[str]:
        rows = conn.execute(
            "SELECT genre FROM movie_genres WHERE movie_id = ? ORDER BY genre", (movie_id,)
        ).fetchall()
        return [row["genre"] for row in rows]

    @staticmethod
    def find_by_normalized(conn, normalized_title: str) -> list[dict]:
        rows = conn.execute(
            "SELECT * FROM movies WHERE normalized_title = ? ORDER BY vote_count DESC",
            (normalized_title,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def search_containing(conn, needle: str, limit: int = 100) -> list[dict]:
        rows = conn.execute(
            "SELECT * FROM movies WHERE instr(normalized_title, ?) > 0 "
            "ORDER BY vote_count DESC LIMIT ?",
            (needle, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def search_by_tokens(conn, tokens: list[str], limit: int = 100) -> list[dict]:
        found: dict[int, dict] = {}
        for token in tokens:
            rows = conn.execute(
                "SELECT * FROM movies WHERE instr(normalized_title, ?) > 0 "
                "ORDER BY vote_count DESC LIMIT ?",
                (token, limit),
            ).fetchall()
            for row in rows:
                found[row["movie_id"]] = dict(row)
                if len(found) >= limit:
                    return list(found.values())
        return list(found.values())

    @staticmethod
    def list_genre_names(conn) -> list[str]:
        rows = conn.execute(
            "SELECT DISTINCT genre FROM movie_genres ORDER BY genre"
        ).fetchall()
        return [row["genre"] for row in rows]

    @staticmethod
    def search(conn, query: str | None = None, genre: str | None = None,
               min_rating: float | None = None, limit: int = 20,
               offset: int = 0, order: str = "title") -> tuple[list[dict], int]:
        where = []
        params: list = []
        if query:
            where.append("instr(m.normalized_title, ?) > 0")
            params.append(" ".join(query.lower().split()))
        if genre:
            where.append(
                "EXISTS (SELECT 1 FROM movie_genres g WHERE g.movie_id = m.movie_id AND g.genre = ?)"
            )
            params.append(genre)
        if min_rating is not None:
            where.append("m.vote_average >= ?")
            params.append(min_rating)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        total = conn.execute(
            f"SELECT COUNT(*) FROM movies m {where_sql}", params
        ).fetchone()[0]

        order_sql = "m.popularity DESC" if order == "popularity" else "m.title COLLATE NOCASE ASC"
        rows = conn.execute(
            f"SELECT m.* FROM movies m {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return [dict(row) for row in rows], total

    @staticmethod
    def attach_genres(conn, movies: list[dict]) -> list[dict]:
        """Add `genre_list` (and keep the raw `genres` string) to each movie dict."""
        if not movies:
            return movies
        ids = [movie["movie_id"] for movie in movies]
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT movie_id, genre FROM movie_genres WHERE movie_id IN ({placeholders})",
            ids,
        ).fetchall()
        by_movie: dict[int, list[str]] = {}
        for row in rows:
            by_movie.setdefault(row["movie_id"], []).append(row["genre"])
        for movie in movies:
            movie["genre_list"] = sorted(by_movie.get(movie["movie_id"], []))
        return movies


class WatchedMovieRepository:
    @staticmethod
    def add(conn, user_id: int, movie_id: int, rating: float | None, source: str) -> bool:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO watched_movies (user_id, movie_id, user_rating, source) "
            "VALUES (?, ?, ?, ?)",
            (user_id, movie_id, rating, source),
        )
        return cursor.rowcount > 0

    @staticmethod
    def update_rating(conn, user_id: int, movie_id: int, rating: float | None) -> None:
        conn.execute(
            "UPDATE watched_movies SET user_rating = ? WHERE user_id = ? AND movie_id = ?",
            (rating, user_id, movie_id),
        )

    @staticmethod
    def get_movie_ids(conn, user_id: int) -> set[int]:
        rows = conn.execute(
            "SELECT movie_id FROM watched_movies WHERE user_id = ?", (user_id,)
        ).fetchall()
        return {row["movie_id"] for row in rows}

    @staticmethod
    def get_by_user(conn, user_id: int, limit: int = 500) -> list[dict]:
        rows = conn.execute(
            """
            SELECT w.watched_id, w.movie_id, w.user_rating, w.source, w.added_at,
                   m.title, m.release_year, m.genres, m.vote_average
            FROM watched_movies w
            JOIN movies m ON m.movie_id = w.movie_id
            WHERE w.user_id = ?
            ORDER BY w.added_at DESC, w.watched_id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_ratings(conn, user_id: int) -> list[float]:
        rows = conn.execute(
            "SELECT user_rating FROM watched_movies "
            "WHERE user_id = ? AND user_rating IS NOT NULL",
            (user_id,),
        ).fetchall()
        return [row["user_rating"] for row in rows]


class ImportRepository:
    @staticmethod
    def create(conn, user_id: int, file_name: str, file_type: str,
               columns: dict, total_rows: int) -> int:
        cursor = conn.execute(
            "INSERT INTO import_runs (user_id, file_name, file_type, columns_json, status, total_rows) "
            "VALUES (?, ?, ?, ?, 'validated', ?)",
            (user_id, file_name, file_type, json.dumps(columns), total_rows),
        )
        return cursor.lastrowid

    @staticmethod
    def get_by_id(conn, import_id: int) -> dict | None:
        row = conn.execute("SELECT * FROM import_runs WHERE import_id = ?", (import_id,)).fetchone()
        import_dict = _row(row)
        if import_dict and import_dict.get("columns_json"):
            try:
                import_dict["columns"] = json.loads(import_dict["columns_json"])
            except ValueError:
                import_dict["columns"] = {}
        elif import_dict:
            import_dict["columns"] = {}
        return import_dict

    @staticmethod
    def update_status(conn, import_id: int, status: str) -> None:
        conn.execute("UPDATE import_runs SET status = ? WHERE import_id = ?", (status, import_id))

    @staticmethod
    def add_records(conn, import_id: int, records: list[dict]) -> None:
        conn.executemany(
            "INSERT INTO import_records (import_id, raw_movie_title, raw_movie_id, raw_rating) "
            "VALUES (?, ?, ?, ?)",
            [
                (import_id, r.get("raw_movie_title"), r.get("raw_movie_id"), r.get("raw_rating"))
                for r in records
            ],
        )

    @staticmethod
    def get_records(conn, import_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT * FROM import_records WHERE import_id = ? ORDER BY record_id",
            (import_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def update_record(conn, record_id: int, *, raw_movie_title, normalized_title,
                      is_valid, is_duplicate, match_status, matched_movie_id,
                      match_candidates) -> None:
        conn.execute(
            "UPDATE import_records SET raw_movie_title = ?, normalized_title = ?, "
            "is_valid = ?, is_duplicate = ?, match_status = ?, matched_movie_id = ?, "
            "match_candidates = ? WHERE record_id = ?",
            (raw_movie_title, normalized_title, is_valid, is_duplicate,
             match_status, matched_movie_id, match_candidates, record_id),
        )

    @staticmethod
    def set_match_decision(conn, record_id: int, movie_id: int | None) -> None:
        if movie_id is None:
            conn.execute(
                "UPDATE import_records SET match_status = 'skipped', match_candidates = NULL "
                "WHERE record_id = ?",
                (record_id,),
            )
        else:
            conn.execute(
                "UPDATE import_records SET match_status = 'matched', matched_movie_id = ?, "
                "match_candidates = NULL WHERE record_id = ?",
                (movie_id, record_id),
            )

    @staticmethod
    def save_quality_report(conn, import_id: int, report: dict) -> None:
        conn.execute("DELETE FROM data_quality_reports WHERE import_id = ?", (import_id,))
        conn.execute(
            "INSERT INTO data_quality_reports "
            "(import_id, original_rows, duplicate_rows, missing_movie_rows, invalid_rows, "
            " matched_rows, ambiguous_rows, unmatched_rows, final_rows) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                import_id,
                report["original_rows"],
                report["duplicate_rows"],
                report["missing_movie_rows"],
                report["invalid_rows"],
                report["matched_rows"],
                report["ambiguous_rows"],
                report["unmatched_rows"],
                report["final_rows"],
            ),
        )

    @staticmethod
    def get_quality_report(conn, import_id: int) -> dict | None:
        row = conn.execute(
            "SELECT * FROM data_quality_reports WHERE import_id = ? "
            "ORDER BY report_id DESC LIMIT 1",
            (import_id,),
        ).fetchone()
        report = _row(row)
        if report:
            report.pop("report_id", None)
            report.pop("import_id", None)
        return report

    @staticmethod
    def quality_totals(conn, user_id: int) -> dict:
        """Aggregate quality reports across a user's confirmed/cleaned imports."""
        row = conn.execute(
            """
            SELECT COUNT(*) AS imports,
                   COALESCE(SUM(r.duplicate_rows), 0)   AS duplicates_removed,
                   COALESCE(SUM(r.missing_movie_rows), 0) AS missing_values,
                   COALESCE(SUM(r.invalid_rows), 0)     AS invalid_rows,
                   COALESCE(SUM(r.ambiguous_rows), 0)   AS ambiguous_rows,
                   COALESCE(SUM(r.unmatched_rows), 0)   AS unmatched_rows
            FROM import_runs i
            LEFT JOIN data_quality_reports r ON r.import_id = i.import_id
            WHERE i.user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return _row(row) or {}


class MiningRepository:
    @staticmethod
    def create_run(conn, user_id: int, algorithm: str, parameters: dict, metrics: dict) -> int:
        cursor = conn.execute(
            "INSERT INTO mining_runs (user_id, algorithm, parameters_json, metrics_json) "
            "VALUES (?, ?, ?, ?)",
            (user_id, algorithm, json.dumps(parameters), json.dumps(metrics)),
        )
        return cursor.lastrowid

    @staticmethod
    def save_kmeans(conn, run_id: int, assignments: list[dict], profiles: list[dict]) -> None:
        conn.executemany(
            "INSERT INTO kmeans_results (run_id, movie_id, cluster_id) VALUES (?, ?, ?)",
            [(run_id, a["movie_id"], a["cluster_id"]) for a in assignments],
        )
        conn.executemany(
            "INSERT INTO cluster_profiles (run_id, cluster_id, cluster_size, average_rating, "
            " average_movies_watched, dominant_genre, silhouette_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    p["cluster_id"],
                    p["cluster_size"],
                    p["average_rating"],
                    p.get("average_movies_watched"),
                    p["dominant_genre"],
                    p.get("silhouette_score"),
                )
                for p in profiles
            ],
        )

    @staticmethod
    def save_rules(conn, run_id: int, rules: list[dict]) -> None:
        conn.executemany(
            "INSERT INTO apriori_rules (run_id, antecedent, consequent, support, confidence, lift) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (run_id, r["antecedent"], r["consequent"], r["support"], r["confidence"], r["lift"])
                for r in rules
            ],
        )

    @staticmethod
    def save_naive_bayes(conn, run_id: int, probabilities: list[dict]) -> None:
        conn.executemany(
            "INSERT INTO naive_bayes_results (run_id, genre, probability) VALUES (?, ?, ?)",
            [(run_id, p["genre"], p["probability"]) for p in probabilities],
        )

    @staticmethod
    def list_runs(conn, user_id: int, limit: int = 50) -> list[dict]:
        rows = conn.execute(
            "SELECT run_id, algorithm, parameters_json, metrics_json, status, created_at "
            "FROM mining_runs WHERE user_id = ? ORDER BY run_id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        runs = []
        for row in rows:
            run = dict(row)
            for key in ("parameters_json", "metrics_json"):
                try:
                    run[key.replace("_json", "")] = json.loads(run.pop(key) or "{}")
                except ValueError:
                    run.pop(key, None)
            runs.append(run)
        return runs


class RecommendationRepository:
    @staticmethod
    def replace(conn, user_id: int, items: list[dict]) -> None:
        """Replace the user's stored recommendation set with the latest top-N."""
        conn.execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT INTO recommendations (user_id, movie_id, score, reason) VALUES (?, ?, ?, ?)",
            [(user_id, item["movie_id"], item["score"], item["reason"]) for item in items],
        )

    @staticmethod
    def get_recent(conn, user_id: int, limit: int = 50) -> list[dict]:
        rows = conn.execute(
            "SELECT r.movie_id, r.score, r.reason, r.created_at, m.title, m.release_year, "
            "       m.vote_average "
            "FROM recommendations r JOIN movies m ON m.movie_id = r.movie_id "
            "WHERE r.user_id = ? ORDER BY r.score DESC, r.movie_id LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
