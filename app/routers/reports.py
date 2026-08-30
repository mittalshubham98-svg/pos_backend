"""Day-end CSV reports, generated from locked sale bills only (per the prototype's Reports
tab: "Generated from locked sale bills only"). Admin only.
"""
import csv
import io
from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_current_admin, get_db
from ..models import Customer, LedgerEntry, PurchaseOrder
from ..pricing import priced_view

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _csv_stream(header: list, rows: list) -> Iterator[str]:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    yield buf.getvalue()
    for row in rows:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(row)
        yield buf.getvalue()


def _billed_orders(db: Session):
    return db.query(PurchaseOrder).filter(PurchaseOrder.status == "BILLED").all()


@router.get("/item-wise-sales.csv")
def item_wise_sales_csv(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    agg: dict = {}
    for po in _billed_orders(db):
        priced = priced_view(po)
        for l in priced["lines"]:
            key = (l["name"], l["category"] or "")
            bucket = agg.setdefault(key, {"qty": 0.0, "taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "total": 0.0})
            bucket["qty"] += l["qty"]
            bucket["taxable"] += l["taxable"]
            bucket["cgst"] += l["cgst"]
            bucket["sgst"] += l["sgst"]
            bucket["total"] += l["selling"]

    rows = [
        [name, category, round(b["qty"], 2), round(b["taxable"], 2), round(b["cgst"], 2), round(b["sgst"], 2), round(b["total"], 2)]
        for (name, category), b in sorted(agg.items())
    ]
    header = ["item_name", "category", "qty_sold", "taxable_value", "cgst", "sgst", "total_value"]
    return StreamingResponse(
        _csv_stream(header, rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=item_wise_sales.csv"},
    )


@router.get("/customer-wise-sales.csv")
def customer_wise_sales_csv(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    agg: dict = {}
    for po in _billed_orders(db):
        priced = priced_view(po)
        cust_id = po.customer_id or 0
        cust_name = po.customer.name if po.customer and po.customer.name else "(no name on record)"
        bucket = agg.setdefault(
            cust_id, {"name": cust_name, "bills": 0, "taxable": 0.0, "gst": 0.0, "total": 0.0}
        )
        bucket["bills"] += 1
        bucket["taxable"] += priced["taxable"]
        bucket["gst"] += priced["gst"]
        bucket["total"] += priced["grand_total"]

    rows = [
        [cust_id, b["name"], b["bills"], round(b["taxable"], 2), round(b["gst"], 2), round(b["total"], 2)]
        for cust_id, b in sorted(agg.items())
    ]
    header = ["customer_id", "customer_name", "bills", "taxable_value", "total_gst", "total_value"]
    return StreamingResponse(
        _csv_stream(header, rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_wise_sales.csv"},
    )


@router.get("/customer-outstanding.csv")
def customer_outstanding_csv(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    customers = db.query(Customer).order_by(Customer.id.asc()).all()
    rows = []
    for c in customers:
        billed = (
            db.query(func.coalesce(func.sum(LedgerEntry.amount), 0.0))
            .filter(LedgerEntry.customer_id == c.id, LedgerEntry.amount > 0)
            .scalar()
        )
        paid = (
            db.query(func.coalesce(func.sum(LedgerEntry.amount), 0.0))
            .filter(LedgerEntry.customer_id == c.id, LedgerEntry.amount < 0)
            .scalar()
        )
        billed = round(float(billed or 0), 2)
        paid = round(-float(paid or 0), 2)  # payments are stored negative; report them positive
        balance_due = round(billed - paid, 2)
        rows.append([c.id, c.name or "(no name on record)", billed, paid, balance_due])

    header = ["customer_id", "customer_name", "billed_to_date", "paid", "balance_due"]
    return StreamingResponse(
        _csv_stream(header, rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_outstanding.csv"},
    )
