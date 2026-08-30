"""Handwritten parchi OCR: upload a photo, get back fuzzy-matched draft lines; confirm the
accepted ones to create a PO exactly like a customer order, but source='ocr'.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import settings_store
from ..deps import get_current_admin, get_db
from ..models import Item, PoLine, PurchaseOrder
from ..pricing import po_summary
from ..schemas import OcrConfirmIn, OcrResultOut, POOut
from ..services.ocr_service import run_ocr
from ..utils import clean_utr

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/parchi", response_model=OcrResultOut)
async def ocr_parchi(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    raw = await file.read()
    if not raw:
        return OcrResultOut(success=False, reason="uploaded file is empty")

    floor = settings_store.get_float(db, "ocr_confidence_floor", 0.6)
    result = run_ocr(db, raw, floor)  # never raises — see services/ocr_service.py
    return OcrResultOut(**result)


@router.post("/parchi/confirm", status_code=201, response_model=POOut)
def confirm_parchi(
    payload: OcrConfirmIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    unlisted = (payload.unlisted_text or "").strip()
    if not payload.lines and not unlisted:
        raise HTTPException(status_code=400, detail="Nothing to confirm — no matched lines or unlisted text")

    for line in payload.lines:
        if not db.get(Item, line.item_id):
            raise HTTPException(status_code=400, detail=f"Item {line.item_id} does not exist")

    po = PurchaseOrder(
        po_number=settings_store.next_po_number(db),
        customer_id=payload.customer_id,
        status="PO_RECEIVED",
        utr=clean_utr(payload.utr) or None,
        unlisted_text=unlisted,
        source="ocr",
    )
    db.add(po)
    db.flush()

    for line in payload.lines:
        db.add(PoLine(po_id=po.id, item_id=line.item_id, qty=line.qty))

    settings_store.bump_po_seq(db)
    db.commit()
    db.refresh(po)
    return po_summary(po)
