"""Order lifecycle: customer places a PO, admin edits/reviews it, then converts it to a
locked sale bill. Two routers live here: `router` (admin + creation, under /api/orders) and
`customer_router` (a customer's own order history, under /api/customer/orders — an
addition; the prototype's "order received" screen implies customers want this).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import settings_store
from ..deps import get_current_admin, get_current_customer, get_db
from ..models import Customer, Item, LedgerEntry, PoLine, PurchaseOrder
from ..pricing import po_summary
from ..schemas import BillOut, OrderCreateIn, OrderPatchIn, POOut
from ..services.billing import convert_po_to_bill
from ..utils import clean_utr

router = APIRouter(prefix="/api/orders", tags=["orders"])
customer_router = APIRouter(prefix="/api/customer", tags=["orders"])


@router.post("", status_code=201, response_model=POOut)
def create_order(
    payload: OrderCreateIn,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    unlisted = (payload.unlisted_text or "").strip()
    if not payload.lines and not unlisted:
        raise HTTPException(status_code=400, detail="Order needs at least one line or an unlisted request")

    items_by_id = {}
    for line in payload.lines:
        item = db.get(Item, line.item_id)
        if not item:
            raise HTTPException(status_code=400, detail=f"Item {line.item_id} does not exist")
        items_by_id[line.item_id] = item

    po = PurchaseOrder(
        po_number=settings_store.next_po_number(db),
        customer_id=customer.id,
        status="PO_RECEIVED",
        utr=clean_utr(payload.utr) or None,
        unlisted_text=unlisted,
        source="web",
    )
    db.add(po)
    db.flush()

    for line in payload.lines:
        # qty arrives in the chosen uom (piece count for PCS, case count for CASE) — convert
        # to pieces once here so every downstream consumer (tax engine, invoice, picking
        # sheet) keeps working in piece terms unchanged.
        item = items_by_id[line.item_id]
        pieces = line.qty * (item.case_size or 1) if line.uom == "CASE" else line.qty
        db.add(PoLine(po_id=po.id, item_id=line.item_id, qty=pieces, uom=line.uom))

    settings_store.bump_po_seq(db)
    db.commit()
    db.refresh(po)
    return po_summary(po)


@router.get("", response_model=List[POOut])
def list_orders(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    query = db.query(PurchaseOrder)
    if status:
        query = query.filter(PurchaseOrder.status == status)
    orders = query.order_by(PurchaseOrder.id.desc()).all()
    return [po_summary(o) for o in orders]


@router.get("/{po_id}", response_model=POOut)
def get_order(po_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    return po_summary(po)


@router.patch("/{po_id}", response_model=POOut)
def patch_order(
    po_id: int,
    payload: OrderPatchIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    if po.status == "BILLED" or po.sale_bill is not None:
        raise HTTPException(status_code=409, detail=f"{po.po_number} is already billed and locked")

    remove_ids = set(payload.remove_line_ids or [])
    if remove_ids:
        for line in db.query(PoLine).filter(PoLine.po_id == po.id, PoLine.id.in_(remove_ids)).all():
            db.delete(line)
        db.flush()

    if payload.update_lines:
        current = {l.id: l for l in db.query(PoLine).filter(PoLine.po_id == po.id).all()}
        for upd in payload.update_lines:
            line = current.get(upd.line_id)
            if not line:
                raise HTTPException(status_code=400, detail=f"Line {upd.line_id} not found on {po.po_number}")
            if upd.qty is not None:
                line.qty = upd.qty
            if upd.rate_override is not None:
                line.rate_override = upd.rate_override
            if upd.uom is not None:
                line.uom = upd.uom

    if payload.add_item_lines:
        for il in payload.add_item_lines:
            item = db.get(Item, il.item_id)
            if not item:
                raise HTTPException(status_code=400, detail=f"Item {il.item_id} does not exist")
            pieces = il.qty * (item.case_size or 1) if il.uom == "CASE" else il.qty
            db.add(PoLine(po_id=po.id, item_id=il.item_id, qty=pieces, rate_override=il.rate_override, uom=il.uom))

    if payload.add_custom_lines:
        for cl in payload.add_custom_lines:
            db.add(
                PoLine(
                    po_id=po.id,
                    item_id=None,
                    custom_name=cl.custom_name,
                    qty=cl.qty,
                    rate_override=cl.rate_override,
                    gst_override=cl.gst_override,
                )
            )

    if payload.utr is not None:
        po.utr = clean_utr(payload.utr) or None
    if payload.unlisted_text is not None:
        po.unlisted_text = payload.unlisted_text

    if not (
        remove_ids
        or payload.update_lines
        or payload.add_item_lines
        or payload.add_custom_lines
        or payload.utr is not None
        or payload.unlisted_text is not None
    ):
        raise HTTPException(status_code=400, detail="Patch body has nothing to apply")

    db.commit()
    db.refresh(po)
    return po_summary(po)


@router.post("/{po_id}/bill", response_model=BillOut)
def bill_order(po_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    bill = convert_po_to_bill(db, po)
    db.refresh(po)
    return BillOut(
        po_id=po.id,
        po_number=po.po_number,
        invoice_number=bill.invoice_number,
        taxable_total=bill.taxable_total,
        cgst_total=bill.cgst_total,
        sgst_total=bill.sgst_total,
        grand_total=bill.grand_total,
        locked_at=bill.locked_at,
    )


@router.delete("/{po_id}")
def delete_order(po_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """Manually remove a PO — pending or already billed. Deleting a billed one removes its
    invoice too: the ledger entries it posted are cleared first (they carry a FK to the sale
    bill), then the sale bill (cascading to its frozen sale_bill_lines snapshot), then the PO
    itself (cascading to po_lines). Everything downstream — dashboard metrics, reports, the
    customer's balance due — is computed live from what remains, so nothing is left dangling."""
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    po_number = po.po_number
    invoice_number = po.sale_bill.invoice_number if po.sale_bill else None
    if po.sale_bill is not None:
        db.query(LedgerEntry).filter(LedgerEntry.sale_bill_id == po.sale_bill.id).delete()
        db.flush()
        db.delete(po.sale_bill)
    db.delete(po)
    db.commit()
    return {"deleted": True, "po_number": po_number, "invoice_number": invoice_number}


@customer_router.get("/orders", response_model=List[POOut])
def list_my_orders(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    orders = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.customer_id == customer.id)
        .order_by(PurchaseOrder.id.desc())
        .all()
    )
    return [po_summary(o) for o in orders]
