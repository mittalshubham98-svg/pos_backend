"""Password hashing (bcrypt) and session tokens (stateless JWT).

Sessions are deliberately stateless: nothing in the handoff spec's DDL has a sessions table,
and a signed, expiring JWT gives us "a session token" (per the API surface) without adding
one. Payload carries just {role, customer_id?, sub, exp}.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    if not raw or not hashed:
        return False
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = dict(data)
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
