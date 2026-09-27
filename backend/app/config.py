import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
SEED_DIR = os.path.join(BASE_DIR, "seed")

DATABASE_PATH = os.environ.get("CINEMINE_DB_PATH") or os.path.join(DATA_DIR, "cinemine.db")
MOVIES_CSV = os.environ.get("CINEMINE_SEED_CSV") or os.path.join(SEED_DIR, "tmdb_5000_movies.csv")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

MAX_MASTER_MOVIES = 5000
MAX_FILE_SIZE_MB = 10

JWT_SECRET = os.environ.get(
    "CINEMINE_JWT_SECRET", "cinemine-local-dev-secret-0123456789abcdef"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

RATING_MIN = 0.0
RATING_MAX = 5.0

BCRYPT_ROUNDS = int(os.environ.get("CINEMINE_BCRYPT_ROUNDS", "12"))
