"""Engine/session setup. SQLite in WAL mode so the admin portal and customer app can read
and write concurrently without locking each other out (per the handoff spec, section 1)."""
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Base, Setting

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Seed rows per the handoff spec's DDL comment: "seed rows: po_auto_purge_days,
# invoice_prefix, invoice_next_seq, upi_qr_path, ocr_confidence_floor".
# `po_next_seq` is an additional, internal-only counter (not part of the public
# GET/PATCH /api/settings surface) used to mint PO-#### numbers the same way
# invoice_next_seq mints INV-####.
DEFAULT_SETTINGS = {
    "po_auto_purge_days": "30",
    "invoice_prefix": "INV-",
    "invoice_next_seq": "1001",
    "upi_qr_path": "",
    "ocr_confidence_floor": "0.6",
    "po_next_seq": "1001",
}


def _add_missing_columns() -> None:
    """`create_all` only creates tables that don't exist yet — it never alters an existing
    table's columns. Additive model fields (aisle, hsn_code, brand, ...) therefore need an
    explicit ALTER TABLE for databases that predate them. Safe to call every startup."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "items" in table_names:
        existing = {col["name"] for col in inspector.get_columns("items")}
        if "brand" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE items ADD COLUMN brand VARCHAR"))
        if "is_active" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE items ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"))
        if "watchlist_order" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE items ADD COLUMN watchlist_order INTEGER"))
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("items")}
        if "ix_items_item_name_brand" not in existing_indexes:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX ix_items_item_name_brand ON items (item_name, brand)"))
        if "ix_items_is_active" not in existing_indexes:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX ix_items_is_active ON items (is_active)"))

    if "customers" in table_names:
        existing = {col["name"] for col in inspector.get_columns("customers")}
        with engine.begin() as conn:
            if "password_plain" not in existing:
                conn.execute(text("ALTER TABLE customers ADD COLUMN password_plain VARCHAR"))
            if "otp_code" not in existing:
                conn.execute(text("ALTER TABLE customers ADD COLUMN otp_code VARCHAR"))
            if "otp_expires_at" not in existing:
                conn.execute(text("ALTER TABLE customers ADD COLUMN otp_expires_at VARCHAR"))


def init_db() -> None:
    """Create tables if missing and seed default settings rows. Safe to call every startup."""
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    with SessionLocal() as db:
        existing = {row.key for row in db.query(Setting).all()}
        added = False
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                db.add(Setting(key=key, value=value))
                added = True
        if added:
            db.commit()


def get_db():
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
