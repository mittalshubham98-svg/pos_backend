"""Customer directory. `POST /` is the endpoint named in the handoff spec ("every field but
cust_code/password nullable; server generates cust_code + random password, returns them
once in plaintext"). The list/detail GETs are an addition — the admin portal's Customers tab
(directory + balance due + order history) has nothing to render without them.
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from ..deps import get_current_admin, get_db
from ..models import Customer, LedgerEntry, PurchaseOrder
from ..pricing import po_summary
from ..schemas import CustomerCreateIn, CustomerCredentialsOut, CustomerOut, CustomerSetPasswordIn, PaymentIn
from ..security import hash_password
from ..utils import gen_cust_code, gen_password

router = APIRouter(prefix="/api/admin/customers", tags=["customers"])


def _balance_due(db: Session, customer_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(LedgerEntry.amount), 0.0))
        .filter(LedgerEntry.customer_id == customer_id)
        .scalar()
    )
    return round(float(total or 0), 2)


@router.post("", response_model=CustomerCredentialsOut, status_code=201)
def create_customer(
    payload: CustomerCreateIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    existing = {c for (c,) in db.query(Customer.cust_code).all()}
    cust_code = gen_cust_code(existing)
    password = payload.password or gen_password()

    customer = Customer(
        cust_code=cust_code,
        password_hash=hash_password(password),
        name=payload.name or None,
        phone=payload.phone or None,
        address=payload.address or None,
        gstin=payload.gstin or None,
        kind=payload.kind or None,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return CustomerCredentialsOut(
        cust_code=cust_code,
        password=password,
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        gstin=customer.gstin,
        kind=customer.kind,
    )


@router.post("/{customer_id}/reset-password", response_model=CustomerCredentialsOut)
def reset_customer_password(
    customer_id: int,
    payload: Optional[CustomerSetPasswordIn] = Body(default=None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Admin-triggered reset for a customer who's forgotten their password and can't (or
    won't) use the mobile-number self-service flow — e.g. no phone on file, or the phone
    changed. password_hash is a one-way bcrypt hash (see security.py), so there is no way to
    ever recover or display the existing password. The admin can hand the customer a
    password of their choosing (e.g. dictated over the counter so it's easy to remember), or
    leave it blank for a fresh random one, generated and shown once exactly like at account
    creation."""
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    password = (payload.password if payload else None) or gen_password()
    customer.password_hash = hash_password(password)
    db.commit()

    return CustomerCredentialsOut(
        cust_code=customer.cust_code,
        password=password,
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        gstin=customer.gstin,
        kind=customer.kind,
    )


@router.get("")
def list_customers(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    customers = db.query(Customer).order_by(Customer.id.desc()).all()
    out = []
    for c in customers:
        order_count = (
            db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.customer_id == c.id).scalar()
        )
        out.append(
            {
                **CustomerOut.model_validate(c).model_dump(),
                "balance_due": _balance_due(db, c.id),
                "order_count": int(order_count or 0),
            }
        )
    return out


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.customer_id == customer_id)
        .order_by(PurchaseOrder.id.desc())
        .all()
    )
    history = []
    lifetime_billed = 0.0
    for o in orders:
        summary = po_summary(o)
        if o.status == "BILLED":
            lifetime_billed += summary["totals"]["grand_total"]
        history.append(
            {
                "id": o.id,
                "po_number": o.po_number,
                "status": o.status,
                "created_at": o.created_at,
                "invoice_number": summary["invoice_number"],
                "grand_total": summary["totals"]["grand_total"],
            }
        )

    return {
        **CustomerOut.model_validate(customer).model_dump(),
        "balance_due": _balance_due(db, customer_id),
        "lifetime_billed": round(lifetime_billed, 2),
        "order_count": len(orders),
        "orders": history,
    }


@router.post("/{customer_id}/payments", status_code=201)
def record_payment(
    customer_id: int,
    payload: PaymentIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Manually settle part or all of a customer's balance due (e.g. cash collected, or a
    UPI payment against an on-account order)."""
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.add(
        LedgerEntry(
            customer_id=customer_id,
            sale_bill_id=None,
            amount=-abs(payload.amount),
            note=payload.note or "Payment received",
        )
    )
    db.commit()
    return {"customer_id": customer_id, "balance_due": _balance_due(db, customer_id)}
