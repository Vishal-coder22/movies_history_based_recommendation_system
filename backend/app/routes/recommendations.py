from fastapi import APIRouter, Depends

from app.database.connection import get_db
from app.deps import get_current_user_id
from app.services import recommendation_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def recommendations(
    limit: int = recommendation_service.DEFAULT_LIMIT,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    limit = max(1, min(limit, recommendation_service.MAX_LIMIT))
    return recommendation_service.recommend(db, user_id, limit)


@router.get("/{movie_id}")
def recommendation_for_movie(
    movie_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return recommendation_service.explain(db, user_id, movie_id)
