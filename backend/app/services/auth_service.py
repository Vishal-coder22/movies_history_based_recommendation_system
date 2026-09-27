import re
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import BCRYPT_ROUNDS, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET

_password_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=BCRYPT_ROUNDS)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 6


def hash_password(password: str) -> str:
    return _password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _password_context.verify(plain_password, password_hash)


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_PATTERN.match(email))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return int(payload["sub"])
