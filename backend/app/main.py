import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DATA_DIR, MOVIES_CSV, UPLOAD_DIR
from app.database.connection import init_db
from app.routes import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()

    from app.database.repositories import MovieRepository
    from app.database.connection import connect
    from app.database.seed import seed_movies

    conn = connect()
    try:
        needs_seed = MovieRepository.count(conn) == 0
    finally:
        conn.close()
    if needs_seed and os.path.exists(MOVIES_CSV):
        seed_movies()
    yield


app = FastAPI(title="CineMine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/api/health")
def health():
    from app.database.connection import connect
    from app.database.repositories import MovieRepository

    conn = connect()
    try:
        movies = MovieRepository.count(conn)
    finally:
        conn.close()
    return {"status": "ok", "app": "CineMine", "master_movies": movies}
