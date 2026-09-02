"""Catalogue: search, admin edit, CSV import (dry-run/commit), template download, and
manual/automatic image handling.
"""
import io
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_admin, get_db
from ..models import Item, PoLine
from ..pricing import price_item
from ..schemas import ImportResultOut, ItemCreateIn, ItemUpdateIn, WatchlistReorderIn
from ..services.csv_import import process_csv, template_csv_bytes
from ..services.image_fetch import fetch_and_save_image

router = APIRouter(prefix="/api/items", tags=["items"])


def _item_dict(item: Item) -> dict:
    return {
        "id": item.id,
        "item_name": item.item_name,
        "category": item.category,
        "brand": item.brand,
        "item_size": item.item_size,
        "case_size": item.case_size,
        "mrp": item.mrp,
        "taxable_value": item.taxable_value,
        "total_gst_rate": item.total_gst_rate,
        "tax_type": item.tax_type,
        "promo_status": item.promo_status,
        "discount_rate": item.discount_rate,
        "is_daily_rate_change": bool(item.is_daily_rate_change),
        "is_active": bool(item.is_active),
        "image_path": item.image_path,
        "image_source": item.image_source,
        "aisle": item.aisle,
        "hsn_code": item.hsn_code,
        "watchlist_order": item.watchlist_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "pricing": price_item(item),
    }


# NOTE: static sub-paths (template.csv) must be registered before the dynamic
# /{item_id} routes below, or FastAPI will try to parse "template.csv" as an item id.


@router.get("/template.csv")
def download_template():
    return Response(
        content=template_csv_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=item_master_template.csv"},
    )


@router.get("")
def list_items(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    brand: Optional[str] = Query(default=None),
    daily_only: bool = Query(default=False),
    include_inactive: bool = Query(default=False, description="Admin portal only — also return items hidden from the customer app"),
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if not include_inactive:
        query = query.filter(Item.is_active == 1)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Item.item_name.ilike(like), Item.category.ilike(like), Item.brand.ilike(like)))
    if category and category.strip().lower() != "all":
        query = query.filter(Item.category == category)
    if brand and brand.strip().lower() != "all":
        query = query.filter(Item.brand == brand)
    if daily_only:
        query = query.filter(Item.is_daily_rate_change == 1)
        # Admin-chosen watchlist_order first (nulls — never explicitly ordered — sort after
        # everything that has been), then item name as the tiebreak/fallback.
        items = query.order_by(Item.watchlist_order.is_(None), Item.watchlist_order.asc(), Item.item_name.asc()).all()
    else:
        items = query.order_by(Item.item_name.asc()).all()
    return [_item_dict(i) for i in items]


@router.post("/watchlist/reorder")
def reorder_watchlist(
    payload: WatchlistReorderIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Persists the admin's chosen top-to-bottom order for the dashboard's daily rate
    watchlist. Any item id not in the list keeps its existing watchlist_order untouched."""
    for position, item_id in enumerate(payload.item_ids):
        item = db.get(Item, item_id)
        if item:
            item.watchlist_order = position
    db.commit()
    return {"reordered": len(payload.item_ids)}


@router.post("", status_code=201)
def create_item(
    payload: ItemCreateIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    background_tasks.add_task(fetch_and_save_image, item.id, item.item_name)
    return _item_dict(item)


@router.post("/import", response_model=ImportResultOut)
async def import_items(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    result = process_csv(db, text, dry_run=dry_run)

    if not dry_run:
        for item_id in result.get("new_item_ids", []):
            item = db.get(Item, item_id)
            if item:
                background_tasks.add_task(fetch_and_save_image, item.id, item.item_name)

    return ImportResultOut(
        dry_run=dry_run,
        valid_rows=result["valid_rows"],
        warnings=result["warnings"],
        new_skus=result["new_skus"],
        committed=result.get("committed", 0),
    )


@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_dict(item)


@router.patch("/{item_id}")
def update_item(
    item_id: int,
    payload: ItemUpdateIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return _item_dict(item)


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Removing an item that's never been ordered is safe and immediate. One that's already
    on a PO (pending or billed — po_lines aren't cleared by billing, only supplemented with a
    frozen sale_bill_lines snapshot) is refused with 409 rather than silently orphaning those
    lines or corrupting a past invoice's numbers."""
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    in_use = db.query(PoLine).filter(PoLine.item_id == item_id).count()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete — referenced by {in_use} existing order line(s). Remove those lines first.",
        )
    db.delete(item)
    db.commit()
    return {"deleted": True, "id": item_id}


@router.post("/{item_id}/image")
async def upload_item_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((800, 800))
        dest = settings.IMAGES_DIR / f"{item_id}.jpg"
        img.save(dest, "JPEG", quality=85)
    except Exception as exc:  # noqa: BLE001 — a bad upload is a 400, never a 500
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    item.image_path = f"static/images/{item_id}.jpg"
    item.image_source = "manual"
    db.commit()
    db.refresh(item)
    return _item_dict(item)
