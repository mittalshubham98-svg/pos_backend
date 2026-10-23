"""Home-screen banners: upload from the admin portal, show/hide, link, reorder, delete, and
the public list the mobile app reads."""
import io

import pytest
from PIL import Image

from app.config import settings
from app.routers import banners


@pytest.fixture(autouse=True)
def _banner_files_in_tmp(tmp_path, monkeypatch):
    # Keep test uploads out of the real app/static/images/banners.
    monkeypatch.setattr(settings, "STATIC_DIR", tmp_path / "static")
    monkeypatch.setattr(banners, "BANNERS_DIR", tmp_path / "static" / "images" / "banners")


def _png(width=2400, height=900) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (236, 48, 19)).save(buf, "PNG")
    return buf.getvalue()


def _upload(client, headers, title="", link=""):
    r = client.post(
        "/api/admin/banners",
        files={"file": ("promo.png", _png(), "image/png")},
        data={"title": title, "link": link},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_upload_resizes_and_shows_in_public_list(client, admin_headers, tmp_path):
    b = _upload(client, admin_headers, title="Diwali sale", link="deals")
    assert b["is_active"] is True and b["link"] == "deals" and b["title"] == "Diwali sale"

    saved = tmp_path / b["image_url"].lstrip("/")
    with Image.open(saved) as img:
        assert img.width == banners.MAX_WIDTH  # 2400 wide upload scaled down
        assert img.height == 600

    public = client.get("/api/banners").json()
    assert [x["id"] for x in public] == [b["id"]]


def test_hide_reorder_relink_and_delete(client, admin_headers, tmp_path):
    first = _upload(client, admin_headers, title="one")
    second = _upload(client, admin_headers, title="two", link="category:SPICES")
    assert [x["id"] for x in client.get("/api/banners").json()] == [first["id"], second["id"]]

    r = client.post("/api/admin/banners/reorder", json={"banner_ids": [second["id"], first["id"]]}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert [x["id"] for x in client.get("/api/banners").json()] == [second["id"], first["id"]]

    r = client.patch(f"/api/admin/banners/{second['id']}", json={"is_active": False, "link": "catalogue"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["link"] == "catalogue"
    assert [x["id"] for x in client.get("/api/banners").json()] == [first["id"]]
    # Hidden banners still show in the admin list.
    assert len(client.get("/api/admin/banners", headers=admin_headers).json()) == 2

    saved = tmp_path / first["image_url"].lstrip("/")
    assert saved.exists()
    assert client.delete(f"/api/admin/banners/{first['id']}", headers=admin_headers).status_code == 200
    assert not saved.exists()
    assert client.get("/api/banners").json() == []


def test_rejects_bad_input_and_requires_admin(client, admin_headers):
    r = client.post(
        "/api/admin/banners",
        files={"file": ("promo.png", _png(), "image/png")},
        data={"link": "https://evil.example"},
        headers=admin_headers,
    )
    assert r.status_code == 400
    r = client.post("/api/admin/banners", files={"file": ("x.png", b"not an image", "image/png")}, headers=admin_headers)
    assert r.status_code == 400
    assert client.post("/api/admin/banners", files={"file": ("p.png", _png(), "image/png")}).status_code == 401
    assert client.get("/api/admin/banners").status_code == 401
