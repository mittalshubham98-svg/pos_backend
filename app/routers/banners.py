"""Home-screen banners for the mobile app, managed from the admin portal's dashboard.
Admins upload a photo, optionally say what tapping it opens, and show/hide or reorder it;
the app reads the active ones from GET /api/banners."""
import io
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_admin, get_db
from ..models import Banner

router = APIRouter(prefix="/api/admin/banners", tags=["banners"])
public_router = APIRouter(prefix="/api", tags=["banners"])

BANNERS_DIR = settings.IMAGES_DIR / "banners"
MAX_WIDTH = 1600  # plenty for a phone-width banner, keeps uploads from phones' cameras small


def _clean_link(value: Optional[str]) -> str:
    link = (value or "").strip()
    if link in ("", "deals", "catalogue") or (link.startswith("category:") and len(link) > len("category:")):
        return link
    raise ValueError('link must be "", "deals", "catalogue" or "category:<name>"')


def _banner_dict(b: Banner) -> dict:
    return {
        "id": b.id,
        "image_url": f"/{b.image_path}",
        "title": b.title,
        "link": b.link,
        "sort_order": b.sort_order,
        "is_active": bool(b.is_active),
        "created_at": b.created_at,
    }


def _ordered(db: Session):
    return db.query(Banner).order_by(Banner.sort_order.asc(), Banner.id.asc())


class BannerPatchIn(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("link")
    @classmethod
    def _link_valid(cls, v):
        return None if v is None else _clean_link(v)


class BannerReorderIn(BaseModel):
    banner_ids: List[int]


@public_router.get("/banners")
def list_active_banners(db: Session = Depends(get_db)):
    """Active banners in display order — what the app's home carousel shows."""
    return [_banner_dict(b) for b in _ordered(db).filter(Banner.is_active == 1)]


@router.get("")
def list_banners(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return [_banner_dict(b) for b in _ordered(db)]


@router.post("", status_code=201)
async def upload_banner(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    link: str = Form(default=""),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    try:
        link = _clean_link(link)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        # exif_transpose: phone photos are often stored sideways with a rotation tag.
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
        BANNERS_DIR.mkdir(parents=True, exist_ok=True)
        # A fresh name per upload, so phones never show a cached older graphic.
        name = f"banner_{secrets.token_hex(6)}.jpg"
        img.save(BANNERS_DIR / name, "JPEG", quality=85)
    except Exception as exc:  # noqa: BLE001 — a bad upload is a 400, never a 500
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    last = db.query(func.max(Banner.sort_order)).scalar()
    banner = Banner(
        image_path=f"static/images/banners/{name}",
        title=title.strip(),
        link=link,
        sort_order=(last if last is not None else -1) + 1,
    )
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return _banner_dict(banner)


@router.patch("/{banner_id}")
def patch_banner(
    banner_id: int,
    payload: BannerPatchIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    banner = db.get(Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        banner.title = data["title"].strip()
    if "link" in data and data["link"] is not None:
        banner.link = data["link"]
    if "is_active" in data and data["is_active"] is not None:
        banner.is_active = 1 if data["is_active"] else 0
    db.commit()
    db.refresh(banner)
    return _banner_dict(banner)


@router.post("/reorder")
def reorder_banners(payload: BannerReorderIn, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """Sets display order to the given id sequence; ids not listed keep their relative
    order after the listed ones."""
    by_id = {b.id: b for b in db.query(Banner)}
    ordered = [by_id[i] for i in payload.banner_ids if i in by_id]
    rest = [b for b in _ordered(db) if b.id not in set(payload.banner_ids)]
    for position, banner in enumerate(ordered + rest):
        banner.sort_order = position
    db.commit()
    return [_banner_dict(b) for b in _ordered(db)]


@router.delete("/{banner_id}")
def delete_banner(banner_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    banner = db.get(Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    # image_path is relative to the app/ folder ("static/images/banners/..."), as item images are.
    path = settings.STATIC_DIR.parent / banner.image_path
    db.delete(banner)
    db.commit()
    path.unlink(missing_ok=True)
    return {"deleted": True, "id": banner_id}
