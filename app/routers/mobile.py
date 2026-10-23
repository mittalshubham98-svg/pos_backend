"""Endpoints shaped for the native mobile app (see mobile/). Thin views over the same
catalogue, pricing and login logic the web apps use — prices still come from the tax engine
via price_item, and orders still go through POST /api/orders unchanged."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..deps import get_current_customer, get_db
from ..models import Customer, Item, PoLine, PurchaseOrder
from ..pricing import price_item
from ..schemas import CustomerLoginIn
from .auth import customer_login

router = APIRouter(prefix="/api", tags=["mobile"])


def _catalog_item(item: Item) -> dict:
    piece = price_item(item)
    # Same rule as items._item_dict: a case option exists only with a case rate set and a
    # real multi-piece case.
    has_case = bool(item.case_taxable_value and (item.case_size or 1) > 1)
    case = price_item(item, uom="CASE") if has_case else None
    mrp = item.mrp or 0
    return {
        "id": item.id,
        "name": item.item_name,
        "brand": item.brand,
        "size": item.item_size,
        "category": item.category,
        "mrp": mrp,
        "selling_price": piece["selling"],
        "promo_status": item.promo_status or "",
        "discount_rate": item.discount_rate or 0,
        # A deliberate store promotion — not merely selling under MRP, which is most items.
        "on_offer": bool(item.promo_status) or bool(item.discount_rate),
        "image_url": f"/{item.image_path}" if item.image_path else None,
        "case_size": item.case_size or 1,
        # Per-piece price when bought by the full case; null when there's no case option.
        "case_selling_price": case["selling"] if case else None,
    }


@router.get("/catalog")
def get_catalog(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Active items with MRP, selling price and promo status, plus the category list for
    the app's category strip."""
    query = db.query(Item).filter(Item.is_active == 1)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Item.item_name.ilike(like), Item.category.ilike(like), Item.brand.ilike(like)))
    if category and category.strip().lower() != "all":
        query = query.filter(Item.category == category)
    items = query.order_by(Item.item_name.asc()).all()

    categories = [
        c for (c,) in db.query(Item.category).filter(Item.is_active == 1).distinct().order_by(Item.category.asc()) if c
    ]
    return {"categories": categories, "items": [_catalog_item(i) for i in items]}


@router.get("/customer/purchased-items")
def purchased_items(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    """The logged-in customer's previously ordered catalogue items, most bought (total
    pieces across all their orders) to least — the app's "your regular items" list.
    Items since deactivated or deleted are left out, as they can't be reordered."""
    rows = (
        db.query(
            PoLine.item_id,
            func.sum(PoLine.qty).label("total_qty"),
            func.count(func.distinct(PoLine.po_id)).label("times_ordered"),
            func.max(PurchaseOrder.created_at).label("last_ordered_at"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PoLine.po_id)
        .filter(PurchaseOrder.customer_id == customer.id, PoLine.item_id.isnot(None), PoLine.qty > 0)
        .group_by(PoLine.item_id)
        .all()
    )
    items = {i.id: i for i in db.query(Item).filter(Item.id.in_([r.item_id for r in rows]), Item.is_active == 1)}
    ranked = sorted(
        (r for r in rows if r.item_id in items),
        # Most pieces first; ties go to the item ordered more often, then more recently.
        key=lambda r: (r.total_qty, r.times_ordered, r.last_ordered_at),
        reverse=True,
    )
    return [
        {
            **_catalog_item(items[r.item_id]),
            "total_qty": r.total_qty,
            "times_ordered": r.times_ordered,
            "last_ordered_at": r.last_ordered_at,
        }
        for r in ranked
    ]


@router.post("/auth")
def mobile_auth(payload: CustomerLoginIn, db: Session = Depends(get_db)):
    """Customer login for the app: same check and token as /api/customer/login (401 on bad
    credentials), plus the customer's name so the app can greet them."""
    token = customer_login(payload, db)
    customer = db.query(Customer).filter(Customer.cust_code == payload.cust_code.strip().upper()).first()
    return {
        **token.model_dump(),
        "cust_code": customer.cust_code,
        "name": customer.name,
    }
