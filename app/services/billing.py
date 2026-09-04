"""Convert-PO-to-sale-bill: the one place in the app that must be all-or-nothing.

Per the handoff spec section 4: "Atomic (single DB transaction) — a crash mid-conversion
must not leave a PO half-billed", and section 6, test 6: billing the same PO twice must be
rejected with 409, never double-billed.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import settings_store
from ..models import LedgerEntry, PurchaseOrder, SaleBill, SaleBillLine
from ..pricing import price_order


def convert_po_to_bill(db: Session, po: PurchaseOrder) -> SaleBill:
    if po.status == "BILLED" or po.sale_bill is not None:
        raise HTTPException(status_code=409, detail=f"{po.po_number} is already billed")
    if not po.lines:
        raise HTTPException(status_code=400, detail="Cannot bill a PO with no lines")

    priced = price_order(po)

    try:
        invoice_number = settings_store.next_invoice_number(db)

        bill = SaleBill(
            po_id=po.id,
            invoice_number=invoice_number,
            taxable_total=priced["taxable"],
            cgst_total=priced["cgst"],
            sgst_total=priced["sgst"],
            grand_total=priced["grand_total"],
        )
        db.add(bill)
        db.flush()  # assign bill.id without committing yet

        # Freeze the line-level detail exactly as billed — see SaleBillLine's docstring for
        # why this can't just be recomputed from po_lines + items later.
        for l in priced["lines"]:
            db.add(
                SaleBillLine(
                    sale_bill_id=bill.id,
                    item_id=l["item_id"],
                    name=l["name"],
                    category=l["category"],
                    item_size=l["item_size"],
                    case_size=l["case_size"] or 1,
                    uom=l["uom"],
                    aisle=l["aisle"],
                    hsn_code=l["hsn_code"],
                    tax_type=l["tax_type"],
                    gst_rate=l["gst_rate"],
                    qty=l["qty"],
                    unit_rate=l["unit_rate"],
                    mrp=l["mrp"],
                    taxable=l["taxable"],
                    cgst=l["cgst"],
                    sgst=l["sgst"],
                    selling=l["selling"],
                    is_unlisted=1 if l["is_unlisted"] else 0,
                )
            )

        if po.customer_id is not None:
            db.add(
                LedgerEntry(
                    customer_id=po.customer_id,
                    sale_bill_id=bill.id,
                    amount=priced["grand_total"],
                    note=f"Billed {invoice_number} against {po.po_number}",
                )
            )
            if po.utr:
                # UTR was captured at order time, i.e. the customer already paid via UPI —
                # post the offsetting payment straight away so the bill nets to zero due,
                # matching the prototype ("Paid ... settled by UPI"). An on-account order
                # (no UTR) posts only the debit above and stays on the customer's balance
                # due until settled — see POST /api/admin/customers/{id}/payments.
                db.add(
                    LedgerEntry(
                        customer_id=po.customer_id,
                        sale_bill_id=bill.id,
                        amount=-priced["grand_total"],
                        note=f"UPI payment · UTR {po.utr} against {invoice_number}",
                    )
                )

        settings_store.bump_invoice_seq(db)
        po.status = "BILLED"

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bill)
    return bill
