"""Admin and customer login. Neither ever 500s on bad credentials — both return a plain 401
(handoff spec section 4: "Never 500 on bad credentials; return 401")."""
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import settings_store
from ..config import settings
from ..deps import get_current_admin, get_current_customer, get_db
from ..models import Customer
from ..schemas import (
    AdminChangePasswordIn,
    AdminLoginIn,
    CustomerChangePasswordIn,
    CustomerCredentialsOut,
    CustomerLoginIn,
    CustomerRequestOtpIn,
    CustomerResetWithOtpIn,
    TokenOut,
)
from ..security import create_token, hash_password, verify_password
from ..utils import gen_otp, gen_password

router = APIRouter(prefix="/api", tags=["auth"])

_ADMIN_PASSWORD_HASH_KEY = "admin_password_hash"
OTP_TTL_MINUTES = 5


def _find_customer_by_code_and_phone(db: Session, cust_code: str, phone: str) -> Customer:
    """Shared lookup for both OTP steps: a generic 401 either way (never revealing which of
    cust_code/phone was wrong) so the endpoint can't be used to enumerate valid accounts."""
    cust_code = cust_code.strip().upper()
    phone_digits = re.sub(r"\D", "", phone or "")
    customer = db.query(Customer).filter(Customer.cust_code == cust_code).first()
    on_file_digits = re.sub(r"\D", "", customer.phone) if (customer and customer.phone) else ""
    if not customer or not phone_digits or not on_file_digits or not secrets.compare_digest(phone_digits, on_file_digits):
        raise HTTPException(status_code=401, detail="Customer ID and mobile number don't match our records")
    return customer


def _admin_password_ok(raw_password: str, db: Session) -> bool:
    """Checks against the admin's own chosen password (stored hashed via
    /admin/change-password) if one has been set, else falls back to the env-var default —
    so a fresh install still works out of the box."""
    stored_hash = settings_store.get_raw(db, _ADMIN_PASSWORD_HASH_KEY)
    if stored_hash:
        return verify_password(raw_password, stored_hash)
    return secrets.compare_digest(raw_password, settings.ADMIN_PASSWORD)


@router.post("/admin/login", response_model=TokenOut)
def admin_login(payload: AdminLoginIn, db: Session = Depends(get_db)):
    """Single shared admin account for v1, per handoff spec section 4."""
    user_ok = secrets.compare_digest(payload.username.strip(), settings.ADMIN_USERNAME)
    pass_ok = _admin_password_ok(payload.password, db)
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = create_token({"role": "admin", "sub": settings.ADMIN_USERNAME})
    return TokenOut(token=token, role="admin", expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@router.post("/admin/change-password")
def admin_change_password(
    payload: AdminChangePasswordIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Lets the shopkeeper set their own memorable admin password in place of the
    env-var default."""
    if not _admin_password_ok(payload.current_password, db):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    settings_store.set_raw(db, _ADMIN_PASSWORD_HASH_KEY, hash_password(payload.new_password))
    db.commit()
    return {"ok": True}


@router.post("/customer/login", response_model=TokenOut)
def customer_login(payload: CustomerLoginIn, db: Session = Depends(get_db)):
    cust_code = payload.cust_code.strip().upper()
    customer = db.query(Customer).filter(Customer.cust_code == cust_code).first()
    if not customer or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="ID or password not recognised")
    token = create_token({"role": "customer", "customer_id": customer.id, "sub": customer.cust_code})
    return TokenOut(token=token, role="customer", expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@router.post("/customer/otp/request")
def customer_request_otp(payload: CustomerRequestOtpIn, db: Session = Depends(get_db)):
    """Step 1 of self-service password reset, usable anytime (no login needed): a customer
    proves ownership of the account with cust_code + the mobile number on file. On a match a
    fresh 6-digit OTP is generated, valid for 5 minutes. There's no SMS/WhatsApp gateway
    wired up to text it to the customer directly, so it isn't returned here — instead it
    shows up next to that customer in the admin portal for the shopkeeper to read out over a
    call, the same "no gateway, so make it visible where a human can relay it" approach the
    rest of this app takes for credentials."""
    customer = _find_customer_by_code_and_phone(db, payload.cust_code, payload.phone)
    customer.otp_code = gen_otp()
    customer.otp_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    db.commit()
    return {"ok": True, "message": f"OTP sent — ask the store for the code, it's valid for {OTP_TTL_MINUTES} minutes"}


@router.post("/customer/otp/reset", response_model=CustomerCredentialsOut)
def customer_reset_with_otp(payload: CustomerResetWithOtpIn, db: Session = Depends(get_db)):
    """Step 2: cust_code + phone (re-checked) plus the OTP from step 1. A verified match is
    issued a password directly in the response, the same generate-and-show-once mechanism
    used everywhere else in this app. If the customer supplied their own new_password it's
    used as-is (so they can pick something memorable); otherwise a fresh random one is
    generated."""
    customer = _find_customer_by_code_and_phone(db, payload.cust_code, payload.phone)

    otp_valid = False
    if customer.otp_code and customer.otp_expires_at and secrets.compare_digest(payload.otp.strip(), customer.otp_code):
        try:
            expires = datetime.strptime(customer.otp_expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            otp_valid = expires > datetime.now(timezone.utc)
        except ValueError:
            otp_valid = False
    if not otp_valid:
        raise HTTPException(status_code=401, detail="OTP is incorrect or has expired")

    new_password = payload.new_password or gen_password()
    customer.password_hash = hash_password(new_password)
    customer.password_plain = new_password
    customer.otp_code = None
    customer.otp_expires_at = None
    db.commit()
    return CustomerCredentialsOut(
        cust_code=customer.cust_code,
        password=new_password,
        name=customer.name,
        phone=customer.phone,
        address=customer.address,
        gstin=customer.gstin,
        kind=customer.kind,
    )


@router.post("/customer/change-password")
def customer_change_password(
    payload: CustomerChangePasswordIn,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    """Self-service password change while logged in, so a customer can replace their
    store-issued password with one they'll actually remember."""
    if not verify_password(payload.current_password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    customer.password_hash = hash_password(payload.new_password)
    customer.password_plain = payload.new_password
    db.commit()
    return {"ok": True}
