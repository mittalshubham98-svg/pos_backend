"""Test setup: an isolated SQLite file for the whole test session, wiped clean before every
test so scenarios never leak into each other, plus small fixtures for the FastAPI test
client and an authenticated admin.
"""
import os
import tempfile

# Must be set before `app.config` (and anything importing it) is first imported.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(tempfile.gettempdir(), 'pos_backend_test.db')}")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-pass")
os.environ.setdefault("IMAGE_FETCH_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from app.database import DEFAULT_SETTINGS, SessionLocal, engine, init_db
from app.main import app
from app.models import Base, Setting


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    init_db()
    yield


@pytest.fixture(autouse=True)
def _reset_database():
    """Wipe every table before each test, then reseed default settings rows — cheaper and
    more reliable for this app's size than juggling per-test SQLite files."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    with SessionLocal() as db:
        for key, value in DEFAULT_SETTINGS.items():
            db.add(Setting(key=key, value=value))
        db.commit()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def admin_headers(client):
    r = client.post(
        "/api/admin/login",
        json={"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]},
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}
