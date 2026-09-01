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
    if "items" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("items")}
    if "brand" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE items ADD COLUMN brand VARCHAR"))


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
