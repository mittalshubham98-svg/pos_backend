"""SQLAlchemy 2.0 ORM models — a direct mapping of the DDL in
`Handoff - Claude Code Build Spec.md` section 2, plus three additive, backward-compatible
extensions the prototype's UI needs that the given DDL doesn't provide for:

- `items.aisle` (nullable) — the picking sheet's aisle/bin column.
- `items.hsn_code` (nullable) — the tax invoice's HSN column.
- `items.brand` (nullable) — manufacturer/brand name for catalogue search and CSV import.
- `sale_bill_lines` (a whole new table) — a frozen per-line snapshot taken at billing time;
  see its own docstring below for why this one isn't just a nice-to-have.

None of these touch or constrain the original five tables/columns; existing rows and CSV
imports that don't set them are unaffected.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Float,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Additive, nullable — manufacturer/brand name (e.g. "Tata", "Amul") for catalogue
    # search/filtering and CSV import; not in the original DDL.
    brand: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    item_size: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    case_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    mrp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    taxable_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_gst_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    tax_type: Mapped[str] = mapped_column(String, nullable=False, default="Exclusive")
    promo_status: Mapped[str] = mapped_column(String, nullable=False, default="")
    discount_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    is_daily_rate_change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_source: Mapped[str] = mapped_column(String, nullable=False, default="none")
    # Additive, nullable — warehouse aisle/bin (e.g. "A1 · 03") for the picking sheet.
    aisle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Additive, nullable — HSN code for the tax invoice's HSN column. Not in the original
    # DDL; the reference invoice shows one per line but the spec's items table has nowhere
    # to store it, so blank/unset just prints as "—" on the invoice.
    hsn_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default=_now, onupdate=_now)

    po_lines: Mapped[List["PoLine"]] = relationship(back_populates="item")

    __table_args__ = (
        CheckConstraint("case_size >= 1", name="ck_items_case_size"),
        CheckConstraint("mrp >= 0", name="ck_items_mrp"),
        CheckConstraint("taxable_value >= 0", name="ck_items_taxable_value"),
        CheckConstraint("total_gst_rate IN (0,3,5,18,28,40)", name="ck_items_gst_rate"),
        CheckConstraint("tax_type IN ('Exclusive','Inclusive_MRP')", name="ck_items_tax_type"),
        CheckConstraint("promo_status IN ('','NEW','DISCOUNT')", name="ck_items_promo_status"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_items_discount_rate"),
        CheckConstraint("image_source IN ('auto','manual','none')", name="ck_items_image_source"),
        Index("ix_items_item_name", "item_name"),
        Index("ix_items_is_daily_rate_change", "is_daily_rate_change"),
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cust_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    # Additive — mirrors password_hash in reversible form so the admin portal can display a
    # customer's current password on request (shop owner looks it up / reads it out over a
    # call). password_hash remains the only thing ever checked at login; this column is
    # display-only and is kept in sync wherever password_hash is set.
    password_plain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Additive — a short-lived numeric OTP for the mobile-number self-service password reset
    # flow (see /api/customer/otp/*). Stored in plaintext (unlike password_hash) because it's
    # single-use and expires in minutes, and because with no SMS gateway wired up, the admin
    # portal is what surfaces it to the shopkeeper to read out to the customer over a call.
    otp_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    otp_expires_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    orders: Mapped[List["PurchaseOrder"]] = relationship(back_populates="customer")
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(back_populates="customer")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PO_RECEIVED")
    utr: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    unlisted_text: Mapped[str] = mapped_column(String, nullable=False, default="")
    source: Mapped[str] = mapped_column(String, nullable=False, default="web")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    customer: Mapped[Optional[Customer]] = relationship(back_populates="orders")
    lines: Mapped[List["PoLine"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan", passive_deletes=True
    )
    sale_bill: Mapped[Optional["SaleBill"]] = relationship(back_populates="purchase_order", uselist=False)

    __table_args__ = (
        CheckConstraint("status IN ('PO_RECEIVED','BILLED')", name="ck_po_status"),
        CheckConstraint("source IN ('web','ocr','manual')", name="ck_po_source"),
        Index("ix_po_status", "status"),
        Index("ix_po_customer_id", "customer_id"),
    )


class PoLine(Base):
    __tablename__ = "po_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"), nullable=True)
    custom_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    qty: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rate_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gst_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    item: Mapped[Optional[Item]] = relationship(back_populates="po_lines")

    __table_args__ = (
        CheckConstraint("qty >= 0", name="ck_po_lines_qty"),
    )


class SaleBill(Base):
    __tablename__ = "sale_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, unique=True)
    invoice_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    taxable_total: Mapped[float] = mapped_column(Float, nullable=False)
    cgst_total: Mapped[float] = mapped_column(Float, nullable=False)
    sgst_total: Mapped[float] = mapped_column(Float, nullable=False)
    grand_total: Mapped[float] = mapped_column(Float, nullable=False)
    locked_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="sale_bill")
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(back_populates="sale_bill")
    lines: Mapped[List["SaleBillLine"]] = relationship(
        back_populates="sale_bill", cascade="all, delete-orphan", passive_deletes=True
    )


class SaleBillLine(Base):
    """Additive, beyond the original DDL: a frozen per-line snapshot taken at the moment a
    PO is billed. Not optional in practice — items.mrp/taxable_value/discount_rate change
    constantly (the whole point of the 'daily rate watchlist' feature), so without a
    snapshot, re-opening an old invoice or running a historical item-wise-sales report
    after a routine rate edit would silently show today's prices instead of what the
    customer was actually charged. sale_bills' own four aggregate columns are unaffected —
    this table only adds the line-level detail needed to render/report on them faithfully.
    """

    __tablename__ = "sale_bill_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_bill_id: Mapped[int] = mapped_column(ForeignKey("sale_bills.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    item_size: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    case_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    aisle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hsn_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tax_type: Mapped[str] = mapped_column(String, nullable=False)
    gst_rate: Mapped[float] = mapped_column(Float, nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    unit_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mrp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    taxable: Mapped[float] = mapped_column(Float, nullable=False)
    cgst: Mapped[float] = mapped_column(Float, nullable=False)
    sgst: Mapped[float] = mapped_column(Float, nullable=False)
    selling: Mapped[float] = mapped_column(Float, nullable=False)
    is_unlisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sale_bill: Mapped[SaleBill] = relationship(back_populates="lines")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    sale_bill_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sale_bills.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # +ve = billed, -ve = payment received
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    customer: Mapped[Customer] = relationship(back_populates="ledger_entries")
    sale_bill: Mapped[Optional[SaleBill]] = relationship(back_populates="ledger_entries")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
