"""Test bootstrap.

Critical ordering rule: the environment variables below are set BEFORE any
`app.*` module is imported, so the app under test always uses a throwaway
database and the small fixture catalogue - never the real project data.
"""

import atexit
import os
import shutil
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="cinemine-tests-")
os.environ["CINEMINE_DB_PATH"] = os.path.join(_TEST_DIR, "test.db")
os.environ["CINEMINE_SEED_CSV"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "movies_small.csv"
)
# Fast hashing for tests (the app default remains the production-safe value).
os.environ.setdefault("CINEMINE_BCRYPT_ROUNDS", "4")
atexit.register(shutil.rmtree, _TEST_DIR, ignore_errors=True)

import pytest  # noqa: E402


def reset_database() -> None:
    """Drop every table and recreate the schema from scratch."""
    from app.database.connection import connect, init_db

    conn = connect()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for table in tables:
            conn.execute(f'DROP TABLE IF EXISTS "{table[0]}"')
        conn.commit()
    finally:
        conn.close()
    init_db()


@pytest.fixture()
def db():
    """A fresh, seeded database connection (25 fixture movies)."""
    reset_database()
    from app.database.seed import seed_movies

    seeded = seed_movies()
    assert seeded == 25, "fixture catalogue must seed exactly 25 movies"

    from app.database.connection import connect

    conn = connect()
    yield conn
    conn.close()


@pytest.fixture()
def client():
    """Fresh database + running FastAPI app (lifespan seeds the catalogue)."""
    reset_database()
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
