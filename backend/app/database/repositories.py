def _movie_dict(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


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
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_id(conn, user_id: int) -> dict | None:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


class MovieRepository:
    @staticmethod
    def count(conn) -> int:
        return conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]

    @staticmethod
    def get_by_id(conn, movie_id: int) -> dict | None:
        row = conn.execute("SELECT * FROM movies WHERE movie_id = ?", (movie_id,)).fetchone()
        return _movie_dict(row)

    @staticmethod
    def get_genres(conn, movie_id: int) -> list[str]:
        rows = conn.execute(
            "SELECT genre FROM movie_genres WHERE movie_id = ? ORDER BY genre", (movie_id,)
        ).fetchall()
        return [row["genre"] for row in rows]

    @staticmethod
    def get_all(conn, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = conn.execute(
            "SELECT * FROM movies ORDER BY title LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows]
