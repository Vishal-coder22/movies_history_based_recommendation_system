import os
import sqlite3

from app.config import DATABASE_PATH, SEED_DEMO_USER

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class _CompatRow:
    """Minimal sqlite3.Row-compatible object for non-sqlite drivers."""

    __slots__ = ("_cursor", "_values", "_keys")

    def __init__(self, cursor, values):
        self._cursor = cursor
        self._values = values
        self._keys = tuple(c[0] for c in cursor.description) if cursor.description else ()

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._keys.index(key)]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._keys

    def __repr__(self):
        return f"<CompatRow {dict(self)}>"


def _make_row_factory():
    """Create a row factory that produces _CompatRow objects."""
    def factory(cursor, values):
        return _CompatRow(cursor, values)
    return factory


def _configure(conn) -> None:
    rf = _make_row_factory()
    conn.row_factory = rf
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
    except Exception:
        pass


def connect(db_path: str | None = None):
    path = db_path or DATABASE_PATH
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if turso_url and turso_token:
        import turso_serverless
        conn = turso_serverless.connect(turso_url, auth_token=turso_token)
        _configure(conn)
        return conn

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = connect(db_path)
    try:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except Exception:
            pass
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