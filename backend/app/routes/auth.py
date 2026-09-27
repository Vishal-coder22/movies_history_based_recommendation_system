from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database.connection import get_db
from app.database.repositories import UserRepository
from app.deps import get_current_user_id
from app.services.auth_service import (
    MIN_PASSWORD_LENGTH,
    create_access_token,
    hash_password,
    is_valid_email,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    password: str


class LoginInput(BaseModel):
    email: str
    password: str


def _public_user(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "created_at": user["created_at"],
    }


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", status_code=201)
def register(body: RegisterInput, db=Depends(get_db)):
    name = body.name.strip()
    email = _normalize_email(body.email)

    if not name:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Your password must be at least {MIN_PASSWORD_LENGTH} characters long.",
        )
    if UserRepository.get_by_email(db, email) is not None:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try logging in instead.",
        )

    user_id = UserRepository.create(db, name, email, hash_password(body.password))
    user = UserRepository.get_by_id(db, user_id)
    return {"access_token": create_access_token(user_id), "token_type": "bearer", "user": _public_user(user)}


@router.post("/login")
def login(body: LoginInput, db=Depends(get_db)):
    email = _normalize_email(body.email)
    user = UserRepository.get_by_email(db, email)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password. Check your details and try again.",
        )
    return {"access_token": create_access_token(user["user_id"]), "token_type": "bearer", "user": _public_user(user)}


@router.get("/me")
def me(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="This account no longer exists. Please register again.")
    return _public_user(user)
