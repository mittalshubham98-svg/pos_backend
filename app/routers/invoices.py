"""PDF export: tax invoice and picking sheet, rendered from the templates in
app/templates/ (which mirror Invoice and Picking Sheet.dc.html) via WeasyPrint.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..deps import get_current_admin, get_db
from ..models import PurchaseOrder
from ..services.pdf_service import render_invoice_pdf, render_picking_sheet_pdf

router = APIRouter(prefix="/api/orders", tags=["invoices"])


def _get_po_or_404(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    return po


@router.get("/{po_id}/invoice.pdf")
def get_invoice_pdf(po_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    po = _get_po_or_404(db, po_id)
    try:
        pdf_bytes = render_invoice_pdf(po)
    except Exception as exc:  # noqa: BLE001 — e.g. WeasyPrint/cairo not installed on this host
        raise HTTPException(status_code=503, detail=f"PDF rendering is unavailable: {exc}") from exc
    filename = f"{po.sale_bill.invoice_number if po.sale_bill else po.po_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{po_id}/picking-sheet.pdf")
def get_picking_sheet_pdf(po_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    po = _get_po_or_404(db, po_id)
    try:
        pdf_bytes = render_picking_sheet_pdf(po)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"PDF rendering is unavailable: {exc}") from exc
    filename = f"{po.po_number}-picking-sheet.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
