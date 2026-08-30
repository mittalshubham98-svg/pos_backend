"""Background image fetch: on item creation, try to find a product photo via DuckDuckGo
image search and save it under static/images/. Runs as a FastAPI BackgroundTask (fire-and-
forget, after the response is sent) so item creation is never slowed down by — or fails
because of — a flaky network call.

On ANY failure (blocked search, no results, network error, bad image data, disk error) the
item is simply left with image_path=null, image_source='none'. This function must never
raise — the customer/admin UI already has a placeholder fallback for exactly that state
(handoff spec section 4).
"""
import io
import logging

import requests
from PIL import Image

from ..config import settings
from ..database import SessionLocal
from ..models import Item

logger = logging.getLogger("pos_backend.image_fetch")

MAX_DIMENSION = 800
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PilaniSupplyBot/1.0)"}


def _search_image_url(query: str) -> str:
    """Raises on any failure — caller (fetch_and_save_image) is the one that swallows it."""
    from duckduckgo_search import DDGS  # imported lazily so a missing/broken install only

    # breaks image fetch, never the rest of the app.
    with DDGS() as ddgs:
        results = list(ddgs.images(query, max_results=5))
    if not results:
        raise RuntimeError("no image results")
    return results[0]["image"]


def _download_and_save(url: str, item_id: int) -> str:
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=settings.IMAGE_FETCH_TIMEOUT_SECONDS)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img = img.convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    dest = settings.IMAGES_DIR / f"{item_id}.jpg"
    img.save(dest, "JPEG", quality=85)
    return f"static/images/{item_id}.jpg"


def fetch_and_save_image(item_id: int, item_name: str) -> None:
    if not settings.IMAGE_FETCH_ENABLED:
        return
    try:
        url = _search_image_url(item_name)
        rel_path = _download_and_save(url, item_id)
    except Exception as exc:  # noqa: BLE001 — deliberately broad: never let this crash the app
        logger.info("image auto-fetch failed for item %s (%r): %s", item_id, item_name, exc)
        db = SessionLocal()
        try:
            item = db.get(Item, item_id)
            if item is not None and item.image_source != "manual":
                item.image_source = "none"
                item.image_path = None
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        finally:
            db.close()
        return

    db = SessionLocal()
    try:
        item = db.get(Item, item_id)
        if item is not None and item.image_source != "manual":
            item.image_path = rel_path
            item.image_source = "auto"
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.info("image auto-fetch DB update failed for item %s: %s", item_id, exc)
        db.rollback()
    finally:
        db.close()
