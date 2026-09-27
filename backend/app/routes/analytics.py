from fastapi import APIRouter, Depends

from app.database.connection import get_db
from app.deps import get_current_user_id
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return analytics_service.summary(db, user_id)


@router.get("/genres")
def genres(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return analytics_service.genre_stats(db, user_id)


@router.get("/ratings")
def ratings(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return analytics_service.rating_stats(db, user_id)
