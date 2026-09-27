from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import RATING_MAX, RATING_MIN
from app.database.connection import get_db
from app.database.repositories import MovieRepository, WatchedMovieRepository
from app.deps import get_current_user_id

router = APIRouter(prefix="/api/movies", tags=["movies"])

MAX_LIMIT = 100


def _decorate(db, movies: list[dict], user_id: int) -> list[dict]:
    watched_ids = WatchedMovieRepository.get_movie_ids(db, user_id)
    MovieRepository.attach_genres(db, movies)
    ratings = {}
    if watched_ids:
        for row in db.execute(
            "SELECT movie_id, user_rating FROM watched_movies "
            "WHERE user_id = ? AND movie_id IN ({})".format(
                ",".join("?" for _ in watched_ids)
            ),
            [user_id, *watched_ids],
        ).fetchall():
            ratings[row["movie_id"]] = row["user_rating"]
    for movie in movies:
        movie["is_watched"] = movie["movie_id"] in watched_ids
        movie["user_rating"] = ratings.get(movie["movie_id"])
    return movies


@router.get("")
def list_movies(
    q: str | None = None,
    genre: str | None = None,
    min_rating: float | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    order = "popularity" if q else "title"
    movies, total = MovieRepository.search(
        db, query=q, genre=genre, min_rating=min_rating, limit=limit, offset=offset, order=order
    )
    return {"items": _decorate(db, movies, user_id), "total": total, "limit": limit, "offset": offset}


@router.get("/search")
def search_movies(
    q: str | None = None,
    genre: str | None = None,
    min_rating: float | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return list_movies(
        q=q, genre=genre, min_rating=min_rating, limit=limit, offset=offset,
        user_id=user_id, db=db,
    )


@router.get("/genres")
def genre_names(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return {"genres": MovieRepository.list_genre_names(db)}


class WatchedInput(BaseModel):
    rating: float | None = None


@router.post("/{movie_id}/watched")
def add_watched(
    movie_id: int,
    body: WatchedInput,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    movie = MovieRepository.get_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="We couldn't find that movie.")

    rating = body.rating
    if rating is not None and not (RATING_MIN <= rating <= RATING_MAX):
        raise HTTPException(
            status_code=400,
            detail=f"Your rating must be between {RATING_MIN:g} and {RATING_MAX:g}.",
        )

    inserted = WatchedMovieRepository.add(db, user_id, movie_id, rating, "manual")
    if not inserted:
        WatchedMovieRepository.update_rating(db, user_id, movie_id, rating)
    return {"added": inserted, "updated": not inserted, "movie_id": movie_id, "rating": rating}


@router.get("/{movie_id}")
def get_movie(
    movie_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    movie = MovieRepository.get_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="We couldn't find that movie.")
    return _decorate(db, [movie], user_id)[0]
