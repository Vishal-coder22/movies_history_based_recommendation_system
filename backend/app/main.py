import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import DATA_DIR, MOVIES_CSV, UPLOAD_DIR
from app.database.connection import init_db
from app.database.seed import seed_movies, seed_demo_user
from app.errors import UserError
from app.routes import analytics, auth, mining, movies, recommendations, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except OSError:
        pass
    init_db()

    from app.database.repositories import MovieRepository
    from app.database.connection import connect

    conn = connect()
    try:
        needs_seed = MovieRepository.count(conn) == 0
    finally:
        conn.close()
    if needs_seed and os.path.exists(MOVIES_CSV):
        seed_movies()
    from app.config import SEED_DEMO_USER
    if SEED_DEMO_USER:
        seed_demo_user()
    yield


app = FastAPI(title="CineMine", version="1.0.0", lifespan=lifespan)


@app.exception_handler(UserError)
def user_error_handler(request, error: UserError):
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ] + [o.strip() for o in os.environ.get("CINEMINE_CORS_ORIGINS", "").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(movies.router)
app.include_router(analytics.router)
app.include_router(mining.router)
app.include_router(recommendations.router)


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
