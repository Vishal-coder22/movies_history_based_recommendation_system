from fastapi import Header, HTTPException

from app.services.auth_service import decode_access_token


def get_current_user_id(authorization: str | None = Header(default=None)) -> int:
    """FastAPI dependency: extracts the user id from a Bearer JWT."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="You are not logged in. Please log in and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_access_token(token)
    except Exception as exc:
        import jwt

        if isinstance(exc, jwt.ExpiredSignatureError):
            detail = "Your session has expired. Please log in again."
        else:
            detail = "Your session is invalid. Please log in again."
        raise HTTPException(
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
