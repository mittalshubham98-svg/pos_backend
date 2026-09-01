"""Pydantic v2 request/response models.

Validation here is the first line of defence for the "never 500 on bad input" requirement:
Pydantic itself rejects malformed JSON shapes before a handler ever runs, and
app/main.py's exception handler turns those failures into 400s (see the module docstring
there for why 400 rather than FastAPI's default 422).
"""
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tax_engine import ALLOWED_GST_RATES, TAX_TYPES

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


MIN_PASSWORD_LENGTH = 4


def _clean_optional_password(v: Optional[str]) -> Optional[str]:
    """Blank/omitted -> None (caller falls back to a random generated password); anything
    else must clear the minimum length so a customer's chosen password stays crackable-safe
    while still short enough to actually remember."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return v


def _clean_required_password(v: str) -> str:
    v = (v or "").strip()
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    return v


class AdminLoginIn(BaseModel):
    username: str
    password: str


class AdminChangePasswordIn(BaseModel):
    """Lets the shopkeeper replace the shared admin password with one of their own choosing
    instead of the env-var default — verified against the current password first."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _new_password_valid(cls, v):
        return _clean_required_password(v)


class CustomerLoginIn(BaseModel):
    cust_code: str
    password: str


class CustomerChangePasswordIn(BaseModel):
    """Self-service password change for a logged-in customer, so they can swap the
    store-issued random password for one they'll actually remember."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _new_password_valid(cls, v):
        return _clean_required_password(v)


class CustomerSetPasswordIn(BaseModel):
    """Optional body for the admin-triggered reset endpoint: give the customer a password
    of their choosing instead of a random one. Omitted/blank -> random, as before."""

    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _password_valid(cls, v):
        return _clean_optional_password(v)


def _digits_only(v: str) -> str:
    return re.sub(r"\D", "", v or "")


class CustomerRequestOtpIn(BaseModel):
    """Step 1 of self-service password reset: a customer proves ownership of the account by
    supplying the mobile number on file for their cust_code (no SMS gateway exists to verify
    any other way). On a match, a short-lived OTP is generated and stored — surfaced to the
    shopkeeper in the admin portal to read out over a call, since there's no SMS/WhatsApp
    gateway to deliver it directly."""

    cust_code: str
    phone: str


class CustomerResetWithOtpIn(BaseModel):
    """Step 2: cust_code + phone (same as the request step) plus the OTP the shopkeeper
    read out, and either the customer's own chosen new_password or (if left blank) a fresh
    random one — same generate-and-show-once mechanism as customer creation."""

    cust_code: str
    phone: str
    otp: str
    new_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def _new_password_valid(cls, v):
        return _clean_optional_password(v)


class TokenOut(BaseModel):
    token: str
    role: str
    expires_in_minutes: int


class CustomerCreateIn(BaseModel):
    """name and phone are compulsory: the customer ID is generated from the name (a short
    form of it, e.g. "Ramesh Kumar" -> RAMESH01) and the mobile number is what powers
    self-service password reset — a customer with no phone on file has no way to reset their
    own password. Every other field stays optional/nullable."""

    name: str = Field(min_length=1)
    phone: str
    address: Optional[str] = None
    gstin: Optional[str] = None
    kind: Optional[str] = None
    password: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name_valid(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("name is required")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v):
        v = (v or "").strip()
        if len(_digits_only(v)) < 10:
            raise ValueError("phone must have at least 10 digits")
        return v

    @field_validator("password")
    @classmethod
    def _password_valid(cls, v):
        return _clean_optional_password(v)


class CustomerCredentialsOut(BaseModel):
    """Returned in plaintext right after creation or a reset. The password stays visible
    afterwards too, via the admin portal's customer directory (CustomerOut.password)."""

    cust_code: str
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    kind: Optional[str] = None


class PaymentIn(BaseModel):
    """Records a payment received against a customer's outstanding balance (a negative
    ledger_entries row, per the DDL's own 'amount ... -ve = payment received' convention).
    Not named in the handoff spec's API list, but the ledger/outstanding-report features it
    does ask for have no way to ever reach zero without one."""

    amount: float = Field(gt=0)
    note: Optional[str] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cust_code: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    kind: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Items / catalogue
# ---------------------------------------------------------------------------


class ItemBase(BaseModel):
    item_name: str = Field(min_length=1)
    category: Optional[str] = None
    brand: Optional[str] = None
    item_size: Optional[str] = None
    case_size: int = 1
    mrp: float = 0
    taxable_value: float = 0
    total_gst_rate: float = 0
    tax_type: str = "Exclusive"
    promo_status: str = ""
    discount_rate: float = 0
    is_daily_rate_change: bool = False
    aisle: Optional[str] = None
    hsn_code: Optional[str] = None

    @field_validator("total_gst_rate")
    @classmethod
    def _gst_rate_in_slab(cls, v):
        if v not in ALLOWED_GST_RATES:
            raise ValueError(f"total_gst_rate must be one of {ALLOWED_GST_RATES}")
        return v

    @field_validator("tax_type")
    @classmethod
    def _tax_type_known(cls, v):
        if v not in TAX_TYPES:
            raise ValueError(f"tax_type must be one of {TAX_TYPES}")
        return v

    @field_validator("promo_status")
    @classmethod
    def _promo_status_known(cls, v):
        if v not in ("", "NEW", "DISCOUNT"):
            raise ValueError("promo_status must be one of '', 'NEW', 'DISCOUNT'")
        return v

    @field_validator("case_size")
    @classmethod
    def _case_size_positive(cls, v):
        if v < 1:
            raise ValueError("case_size must be >= 1")
        return v

    @field_validator("discount_rate")
    @classmethod
    def _discount_in_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError("discount_rate must be between 0 and 100")
        return v

    @field_validator("mrp", "taxable_value")
    @classmethod
    def _non_negative(cls, v):
        if v < 0:
            raise ValueError("must be >= 0")
        return v


class ItemCreateIn(ItemBase):
    pass


class ItemUpdateIn(BaseModel):
    """PATCH — every field optional; only provided fields are changed."""

    item_name: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = None
    brand: Optional[str] = None
    item_size: Optional[str] = None
    case_size: Optional[int] = None
    mrp: Optional[float] = None
    taxable_value: Optional[float] = None
    total_gst_rate: Optional[float] = None
    tax_type: Optional[str] = None
    promo_status: Optional[str] = None
    discount_rate: Optional[float] = None
    is_daily_rate_change: Optional[bool] = None
    aisle: Optional[str] = None
    hsn_code: Optional[str] = None

    @field_validator("total_gst_rate")
    @classmethod
    def _gst_rate_in_slab(cls, v):
        if v is not None and v not in ALLOWED_GST_RATES:
            raise ValueError(f"total_gst_rate must be one of {ALLOWED_GST_RATES}")
        return v

    @field_validator("tax_type")
    @classmethod
    def _tax_type_known(cls, v):
        if v is not None and v not in TAX_TYPES:
            raise ValueError(f"tax_type must be one of {TAX_TYPES}")
        return v

    @field_validator("promo_status")
    @classmethod
    def _promo_status_known(cls, v):
        if v is not None and v not in ("", "NEW", "DISCOUNT"):
            raise ValueError("promo_status must be one of '', 'NEW', 'DISCOUNT'")
        return v

    @field_validator("case_size")
    @classmethod
    def _case_size_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError("case_size must be >= 1")
        return v

    @field_validator("discount_rate")
    @classmethod
    def _discount_in_range(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("discount_rate must be between 0 and 100")
        return v


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    item_size: Optional[str] = None
    case_size: int
    mrp: float
    taxable_value: float
    total_gst_rate: float
    tax_type: str
    promo_status: str
    discount_rate: float
    is_daily_rate_change: bool
    image_path: Optional[str] = None
    image_source: str
    aisle: Optional[str] = None
    hsn_code: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class OrderLineIn(BaseModel):
    item_id: int
    qty: float = Field(gt=0)


class OrderCreateIn(BaseModel):
    lines: List[OrderLineIn] = Field(default_factory=list)
    unlisted_text: Optional[str] = ""
    utr: Optional[str] = None  # blank/null => on-account order, no payment gate server-side


class LineUpdateIn(BaseModel):
    line_id: int
    qty: Optional[float] = Field(default=None, ge=0)
    rate_override: Optional[float] = None


class CustomLineIn(BaseModel):
    custom_name: str = Field(min_length=1)
    qty: float = Field(gt=0)
    rate_override: float = 0
    gst_override: float = 0

    @field_validator("gst_override")
    @classmethod
    def _gst_in_slab(cls, v):
        if v not in ALLOWED_GST_RATES:
            raise ValueError(f"gst_override must be one of {ALLOWED_GST_RATES}")
        return v


class AddItemLineIn(BaseModel):
    """Adds a line pointing at an existing catalogue item — the admin manually adding a
    listed item to a PO, as distinct from a custom/unlisted line (CustomLineIn) that has no
    item_id at all."""

    item_id: int
    qty: float = Field(gt=0)
    rate_override: Optional[float] = None


class OrderPatchIn(BaseModel):
    """Admin edits to an unbilled PO: adjust/remove existing lines, add catalogue or custom
    lines, and/or amend UTR / unlisted text. Rejected with 409 once a sale bill exists (see
    routers/orders.py)."""

    update_lines: Optional[List[LineUpdateIn]] = None
    remove_line_ids: Optional[List[int]] = None
    add_item_lines: Optional[List[AddItemLineIn]] = None
    add_custom_lines: Optional[List[CustomLineIn]] = None
    utr: Optional[str] = None
    unlisted_text: Optional[str] = None


class POLineOut(BaseModel):
    id: int
    item_id: Optional[int] = None
    custom_name: Optional[str] = None
    name: str
    category: Optional[str] = None
    tax_type: str
    gst_rate: float
    qty: float
    unit_rate: float
    mrp: Optional[float] = None
    taxable: float
    cgst: float
    sgst: float
    selling: float


class OrderTotalsOut(BaseModel):
    taxable: float
    cgst: float
    sgst: float
    selling_raw: float
    grand_total: int
    round_off: float


class POOut(BaseModel):
    id: int
    po_number: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    cust_code: Optional[str] = None
    status: str
    utr: Optional[str] = None
    unlisted_text: str
    source: str
    created_at: str
    invoice_number: Optional[str] = None
    lines: List[POLineOut]
    totals: OrderTotalsOut


class BillOut(BaseModel):
    po_id: int
    po_number: str
    invoice_number: str
    taxable_total: float
    cgst_total: float
    sgst_total: float
    grand_total: float
    locked_at: str


# ---------------------------------------------------------------------------
# Item import (CSV)
# ---------------------------------------------------------------------------


class ImportWarning(BaseModel):
    row: int
    message: str


class ImportResultOut(BaseModel):
    dry_run: bool
    valid_rows: int
    warnings: List[ImportWarning]
    new_skus: int
    committed: int = 0


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------


class OcrLineOut(BaseModel):
    raw_text: str
    matched_item_id: Optional[int] = None
    matched_item_name: Optional[str] = None
    confidence: float
    qty: float


class OcrResultOut(BaseModel):
    success: bool
    reason: Optional[str] = None
    lines: List[OcrLineOut] = Field(default_factory=list)
    unmatched: List[str] = Field(default_factory=list)
    confidence_floor: Optional[float] = None


class OcrConfirmLineIn(BaseModel):
    item_id: int
    qty: float = Field(gt=0)


class OcrConfirmIn(BaseModel):
    lines: List[OcrConfirmLineIn] = Field(default_factory=list)
    unlisted_text: Optional[str] = ""
    customer_id: Optional[int] = None
    utr: Optional[str] = None


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class SettingsOut(BaseModel):
    po_auto_purge_days: int
    invoice_prefix: str
    invoice_next_seq: int
    upi_qr_path: str
    ocr_confidence_floor: float


class SettingsPatchIn(BaseModel):
    po_auto_purge_days: Optional[int] = Field(default=None, ge=0)
    invoice_prefix: Optional[str] = None
    invoice_next_seq: Optional[int] = Field(default=None, ge=1)
    upi_qr_path: Optional[str] = None
    ocr_confidence_floor: Optional[float] = Field(default=None, ge=0, le=1)
