"""Typed accessors for the DB-backed `settings` table (key/value strings)."""
from typing import Optional

from sqlalchemy.orm import Session

from .database import DEFAULT_SETTINGS
from .models import Setting


def get_raw(db: Session, key: str) -> Optional[str]:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    return DEFAULT_SETTINGS.get(key)


def set_raw(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value


def get_int(db: Session, key: str, default: int = 0) -> int:
    raw = get_raw(db, key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_float(db: Session, key: str, default: float = 0.0) -> float:
    raw = get_raw(db, key)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def get_str(db: Session, key: str, default: str = "") -> str:
    raw = get_raw(db, key)
    return raw if raw is not None else default


def all_settings(db: Session) -> dict:
    rows = {row.key: row.value for row in db.query(Setting).all()}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(rows)
    return merged


def next_invoice_number(db: Session) -> str:
    prefix = get_str(db, "invoice_prefix", "INV-")
    seq = get_int(db, "invoice_next_seq", 1001)
    return f"{prefix}{seq}"


def bump_invoice_seq(db: Session) -> None:
    seq = get_int(db, "invoice_next_seq", 1001)
    set_raw(db, "invoice_next_seq", str(seq + 1))


def next_po_number(db: Session) -> str:
    """PO-#### using an internal counter (settings key 'po_next_seq', not exposed via the
    public settings API) — the same scheme as invoice numbering."""
    seq = get_int(db, "po_next_seq", 1001)
    return f"PO-{seq}"


def bump_po_seq(db: Session) -> None:
    seq = get_int(db, "po_next_seq", 1001)
    set_raw(db, "po_next_seq", str(seq + 1))
