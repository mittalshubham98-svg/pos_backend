"""Store settings: PO auto-purge, invoice numbering, UPI QR path, OCR confidence floor."""
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from .. import settings_store
from ..config import settings as app_settings
from ..deps import get_current_admin, get_db
from ..schemas import SettingsOut, SettingsPatchIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _settings_out(db: Session) -> SettingsOut:
    return SettingsOut(
        po_auto_purge_days=settings_store.get_int(db, "po_auto_purge_days", 30),
        invoice_prefix=settings_store.get_str(db, "invoice_prefix", "INV-"),
        invoice_next_seq=settings_store.get_int(db, "invoice_next_seq", 1001),
        upi_qr_path=settings_store.get_str(db, "upi_qr_path", ""),
        ocr_confidence_floor=settings_store.get_float(db, "ocr_confidence_floor", 0.6),
    )


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return _settings_out(db)


@router.patch("", response_model=SettingsOut)
def patch_settings(
    payload: SettingsPatchIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        settings_store.set_raw(db, key, str(value))
    db.commit()
    return _settings_out(db)


@router.post("/upi-qr")
async def upload_upi_qr(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Static image shown to every customer at checkout — no payment gateway involved."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        dest = app_settings.IMAGES_DIR / "upi_qr.png"
        img.save(dest, "PNG")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    rel_path = "static/images/upi_qr.png"
    settings_store.set_raw(db, "upi_qr_path", rel_path)
    db.commit()
    return {"upi_qr_path": rel_path}
