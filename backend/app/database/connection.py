import os
import sqlite3

from app.config import DATABASE_PATH

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DATABASE_PATH
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    _configure(conn)
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())
        conn.commit()
    finally:
        conn.close()


def get_db():
    """FastAPI dependency: one connection per request, commit on success."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
