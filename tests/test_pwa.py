"""Verifies the PWA scaffolding added on top of the existing app: both manifests are served
as valid JSON with the required keys, the service worker is reachable at the top-level
/sw.js route (not /static/sw.js — see app/main.py for why the scope matters), and the two
generated app icons exist and are well-formed PNGs at the right dimensions.
"""
from PIL import Image

from app.config import settings


def test_customer_manifest_served_and_valid(client):
    r = client.get("/static/customer-manifest.json")
    assert r.status_code == 200
    data = r.json()
    for key in ("name", "start_url", "display", "icons"):
        assert key in data
    assert data["start_url"] == "/"
    assert len(data["icons"]) >= 2


def test_admin_manifest_served_and_valid(client):
    r = client.get("/static/admin-manifest.json")
    assert r.status_code == 200
    data = r.json()
    for key in ("name", "start_url", "display", "icons"):
        assert key in data
    assert data["start_url"] == "/admin"
    assert len(data["icons"]) >= 2


def test_service_worker_served_at_top_level_scope(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert "CACHE_NAME" in r.text
    assert "/api/" in r.text  # sanity-check the API-bypass logic is present in the served file


def test_icons_exist_and_are_valid_png_at_expected_sizes():
    for size in (192, 512):
        path = settings.STATIC_DIR / "icons" / f"icon-{size}.png"
        assert path.exists(), f"missing {path}"
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert img.size == (size, size)
