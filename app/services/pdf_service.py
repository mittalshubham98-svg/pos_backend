"""Renders the tax invoice and picking sheet as PDFs via Jinja2 + WeasyPrint, reusing the
layout, copy, and figures from `Invoice and Picking Sheet.dc.html` (handoff spec section 1:
"reuse the invoice layout ... almost directly").

WeasyPrint is imported lazily inside the render_* functions: it needs system libraries
(cairo/pango/gdk-pixbuf) that aren't guaranteed everywhere the rest of the app can run, so a
broken/missing WeasyPrint install only breaks PDF export, not the whole API.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import settings
from ..models import PurchaseOrder
from ..pricing import gst_slab_summary, priced_view
from ..utils import amount_in_words_inr, inr, inr0

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
_env.filters["inr"] = inr
_env.filters["inr0"] = inr0


def _store_context() -> dict:
    return {
        "name": settings.STORE_NAME,
        "address": settings.STORE_ADDRESS,
        "gstin": settings.STORE_GSTIN,
        "fssai": settings.STORE_FSSAI,
        "phone": settings.STORE_PHONE,
        "upi_id": settings.STORE_UPI_ID,
    }


def _fmt_num(n: float) -> str:
    """9.0 -> '9', 2.5 -> '2.5' — avoids Jinja's round filter leaving a trailing '.0' on
    whole-number GST-rate halves (matches the reference invoice's '9 + 9' / '2.5 + 2.5')."""
    n = float(n)
    return str(int(n)) if n.is_integer() else f"{n:g}"


def _line_note(line: dict) -> str:
    if line["is_unlisted"]:
        return "unlisted request · priced at billing"
    if line["tax_type"] == "Inclusive_MRP":
        return "inclusive of MRP · GST reverse-derived"
    return "exclusive"


def invoice_context(po: PurchaseOrder) -> dict:
    priced = priced_view(po)
    lines = []
    for i, l in enumerate(priced["lines"], start=1):
        lines.append(
            {
                "idx": i,
                "name": l["name"],
                "note": _line_note(l),
                "hsn": l.get("hsn_code") or "—",
                "mrp": l["mrp"],
                "qty": l["qty"],
                "rate": l["unit_rate"],
                "taxable": l["taxable"],
                "gst_rate": l["gst_rate"],
                "cgst": l["cgst"],
                "sgst": l["sgst"],
                "total": l["selling"],
            }
        )
    customer = po.customer
    bill = po.sale_bill
    invoice_number = bill.invoice_number if bill else "DRAFT — not yet billed"
    invoice_date = (bill.locked_at if bill else po.created_at)[:10]
    po_time = po.created_at[11:16] if len(po.created_at) >= 16 else ""

    return {
        "store": _store_context(),
        "invoice": {
            "number": invoice_number,
            "date": invoice_date,
            "po_number": po.po_number,
            "po_time": po_time,
            "place_of_supply": settings.PLACE_OF_SUPPLY,
            "is_draft": bill is None,
        },
        "customer": {
            "name": customer.name if (customer and customer.name) else "(no name on record)",
            "cust_code": customer.cust_code if customer else "—",
            "phone": customer.phone if (customer and customer.phone) else "not provided",
            "address": customer.address if (customer and customer.address) else "not provided",
            "gstin": customer.gstin if (customer and customer.gstin) else "not registered",
        },
        "lines": lines,
        "slab_summary": [
            {**s, "half_label": _fmt_num(s["rate"] / 2)} for s in gst_slab_summary(priced["lines"])
        ],
        "totals": {
            "taxable": priced["taxable"],
            "cgst": priced["cgst"],
            "sgst": priced["sgst"],
            "round_off": priced["round_off"],
            "grand_total": priced["grand_total"],
        },
        "amount_in_words": amount_in_words_inr(priced["grand_total"]),
        "payment": {
            "utr": po.utr or "",
            "paid": bool(po.utr),
            "amount": priced["grand_total"],
        },
    }


def picking_sheet_context(po: PurchaseOrder) -> dict:
    priced = priced_view(po)
    lines = []
    total_pieces = 0.0
    aisles = set()
    unlisted_count = 0
    for i, l in enumerate(priced["lines"], start=1):
        total_pieces += l["qty"]
        if l["aisle"]:
            aisles.add(l["aisle"])
        if l["is_unlisted"]:
            unlisted_count += 1
        lines.append(
            {
                "idx": i,
                "name": l["name"],
                "note": "unlisted · substitute if unavailable" if l["is_unlisted"] else "",
                "size": l["item_size"] or "—",
                "aisle": l["aisle"] or "—",
                "case": None if l["is_unlisted"] else l["case_size"],
                "qty": l["qty"],
            }
        )
    pieces_out = int(total_pieces) if float(total_pieces).is_integer() else round(total_pieces, 2)
    return {
        "po": {
            "po_number": po.po_number,
            "cust_name": po.customer.name if (po.customer and po.customer.name) else "(no name on record)",
            "cust_code": po.customer.cust_code if po.customer else "—",
            "date": po.created_at[:10],
            "time": po.created_at[11:16] if len(po.created_at) >= 16 else "",
        },
        "stats": {
            "lines": len(lines),
            "total_pieces": pieces_out,
            "aisles_touched": len(aisles),
            "unlisted": unlisted_count,
        },
        "lines": lines,
    }


def render_invoice_pdf(po: PurchaseOrder) -> bytes:
    from weasyprint import HTML  # lazy import — see module docstring

    template = _env.get_template("invoice.html")
    html = template.render(**invoice_context(po))
    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()


def render_picking_sheet_pdf(po: PurchaseOrder) -> bytes:
    from weasyprint import HTML

    template = _env.get_template("picking_sheet.html")
    html = template.render(**picking_sheet_context(po))
    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
