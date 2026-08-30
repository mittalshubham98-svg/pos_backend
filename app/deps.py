"""FastAPI dependencies: DB session passthrough + admin/customer auth guards.

Both guards raise 401 (never 403, never 500) on any kind of "not authenticated" — missing
header, malformed header, expired/invalid token, wrong role, or (for a customer token) a
customer that no longer exists. That keeps the failure mode uniform and matches the spec's
"never 500 on bad credentials" requirement generalised to all auth failures.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Customer
from .security import decode_token

__all__ = ["get_db", "get_current_admin", "get_current_customer"]


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def get_current_admin(authorization: Optional[str] = Header(default=None)) -> dict:
    payload = decode_token(_bearer_token(authorization))
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Invalid or expired admin session")
    return payload


def get_current_customer(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Customer:
    payload = decode_token(_bearer_token(authorization))
    if not payload or payload.get("role") != "customer":
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    customer = db.get(Customer, payload.get("customer_id"))
    if not customer:
        raise HTTPException(status_code=401, detail="Customer no longer exists")
    return customer
