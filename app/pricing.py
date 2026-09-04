"""Glue between a PO line's stored data (item reference or custom line) and the tax engine.
Shared by the orders router, the billing service, and the invoice/picking-sheet PDF service
so all three price a line exactly the same way.
"""
from dataclasses import dataclass
from typing import List, Optional

from .models import Item, PoLine, PurchaseOrder, SaleBill
from .tax_engine import invoice_round_off, line_totals, price_unit, split_gst, round2


@dataclass
class LineSource:
    name: str
    category: Optional[str]
    item_size: Optional[str]
    case_size: int
    mrp: Optional[float]
    taxable_value: float
    gst_rate: float
    tax_type: str
    discount_rate: float
    aisle: Optional[str] = None
    hsn_code: Optional[str] = None
    is_unlisted: bool = False
    uom: str = "PCS"


def price_item(item: Item, rate_override: Optional[float] = None, uom: str = "PCS") -> dict:
    """Priced view of a single catalogue item at piece rate (qty=1) — used by the catalogue
    endpoints and the admin portal's item table/daily-rate watchlist.

    uom="CASE" prices at item.case_taxable_value (the per-piece rate for a full-case buyer)
    instead of the loose item.taxable_value, falling back to the loose rate when no case rate
    has been configured for the item."""
    taxable_value = item.taxable_value
    if uom == "CASE" and item.case_taxable_value is not None:
        taxable_value = item.case_taxable_value
    unit = price_unit(
        mrp=item.mrp,
        taxable_value=taxable_value,
        gst_rate=item.total_gst_rate,
        tax_type=item.tax_type,
        discount_rate=item.discount_rate,
        rate_override=rate_override,
    )
    cgst, sgst = split_gst(unit["gst"])
    return {
        "rate": unit["rate"],
        "base": round2(unit["base"]),
        "taxable": round2(unit["taxable"]),
        "cgst": cgst,
        "sgst": sgst,
        "gst": round2(cgst + sgst),
        "selling": round2(unit["selling"]),
    }


def resolve_line_source(line: PoLine) -> LineSource:
    """A PO line either points at a catalogue item, or is a custom/unlisted line priced by
    the admin at billing time (item_id is null, custom_name is set)."""
    if line.item_id is not None and line.item is not None:
        it: Item = line.item
        uom = line.uom or "PCS"
        # "CASE" lines charge the item's per-piece case rate instead of the loose rate,
        # falling back to the loose rate when no case rate has been configured — see
        # Item.case_taxable_value's docstring in models.py.
        taxable_value = it.case_taxable_value if (uom == "CASE" and it.case_taxable_value is not None) else it.taxable_value
        return LineSource(
            name=it.item_name,
            category=it.category,
            item_size=it.item_size,
            case_size=it.case_size or 1,
            mrp=it.mrp,
            taxable_value=taxable_value,
            gst_rate=it.total_gst_rate,
            tax_type=it.tax_type,
            discount_rate=it.discount_rate,
            aisle=it.aisle,
            hsn_code=it.hsn_code,
            is_unlisted=False,
            uom=uom,
        )
    # Custom / unlisted line: rate_override carries the flat unit price the admin set,
    # gst_override carries its GST slab. Mirrors the prototype's custom-line handling
    # exactly (taxType always "Exclusive", disc always 0 for these).
    rate = line.rate_override or 0
    gst = line.gst_override if line.gst_override is not None else 0
    return LineSource(
        name=line.custom_name or "Unlisted item",
        category="Unlisted",
        item_size=None,
        case_size=1,
        mrp=None,
        taxable_value=rate,
        gst_rate=gst,
        tax_type="Exclusive",
        discount_rate=0,
        aisle=None,
        hsn_code=None,
        is_unlisted=True,
    )


def price_line(line: PoLine) -> dict:
    """Full priced view of one PO line: identity + rounded money fields ready to display
    or persist. rate_override on the line (an admin-edited unit rate) beats the item's own
    computed rate, per the handoff spec section 4."""
    src = resolve_line_source(line)
    rate_override = line.rate_override if (line.item_id is not None and line.rate_override is not None) else (
        src.taxable_value if src.is_unlisted else None
    )
    unit = price_unit(
        mrp=src.mrp or 0,
        taxable_value=src.taxable_value,
        gst_rate=src.gst_rate,
        tax_type=src.tax_type,
        discount_rate=src.discount_rate,
        rate_override=rate_override,
    )
    qty = max(float(line.qty or 0), 0)
    totals = line_totals(unit, qty)
    cgst, sgst = split_gst(totals["gst"])
    return {
        "id": line.id,
        "item_id": line.item_id,
        "custom_name": line.custom_name,
        "name": src.name,
        "category": src.category,
        "item_size": src.item_size,
        "case_size": src.case_size,
        "uom": src.uom,
        "aisle": src.aisle,
        "hsn_code": src.hsn_code,
        "tax_type": src.tax_type,
        "gst_rate": src.gst_rate,
        "qty": qty,
        "unit_rate": round2(unit["base"]),
        "mrp": src.mrp,
        "taxable": round2(totals["taxable"]),
        "cgst": cgst,
        "sgst": sgst,
        "gst": round2(cgst + sgst),
        "selling": round2(totals["selling"]),
        "is_unlisted": src.is_unlisted,
        # Raw (unrounded) values, used internally to sum totals without paisa drift.
        "_raw_taxable": totals["taxable"],
        "_raw_gst": totals["gst"],
        "_raw_selling": totals["selling"],
    }


def price_order(po: PurchaseOrder) -> dict:
    """Priced lines + invoice-ready totals for a whole PO."""
    priced_lines = [price_line(l) for l in po.lines]
    raw_taxable = sum(l["_raw_taxable"] for l in priced_lines)
    raw_gst = sum(l["_raw_gst"] for l in priced_lines)
    raw_selling = sum(l["_raw_selling"] for l in priced_lines)
    cgst, sgst = split_gst(raw_gst)
    grand_total, round_off = invoice_round_off(raw_selling)
    return {
        "lines": priced_lines,
        "taxable": round2(raw_taxable),
        "cgst": cgst,
        "sgst": sgst,
        "gst": round2(cgst + sgst),
        "selling_raw": round2(raw_selling),
        "grand_total": grand_total,
        "round_off": round_off,
    }


def _priced_view_from_snapshot(bill: SaleBill) -> dict:
    """Rebuild the price_order()-shaped dict from a bill's frozen sale_bill_lines, instead
    of recomputing through the tax engine against (possibly since-changed) catalog data."""
    lines = []
    for sl in bill.lines:
        lines.append(
            {
                "id": sl.id,
                "item_id": sl.item_id,
                "custom_name": None if sl.item_id else sl.name,
                "name": sl.name,
                "category": sl.category,
                "item_size": sl.item_size,
                "case_size": sl.case_size,
                "uom": sl.uom or "PCS",
                "aisle": sl.aisle,
                "hsn_code": sl.hsn_code,
                "tax_type": sl.tax_type,
                "gst_rate": sl.gst_rate,
                "qty": sl.qty,
                "unit_rate": sl.unit_rate,
                "mrp": sl.mrp,
                "taxable": sl.taxable,
                "cgst": sl.cgst,
                "sgst": sl.sgst,
                "gst": round2(sl.cgst + sl.sgst),
                "selling": sl.selling,
                "is_unlisted": bool(sl.is_unlisted),
                "_raw_taxable": sl.taxable,
                "_raw_gst": sl.cgst + sl.sgst,
                "_raw_selling": sl.selling,
            }
        )
    return {
        "lines": lines,
        "taxable": bill.taxable_total,
        "cgst": bill.cgst_total,
        "sgst": bill.sgst_total,
        "gst": round2(bill.cgst_total + bill.sgst_total),
        "selling_raw": bill.grand_total,
        "grand_total": bill.grand_total,
        "round_off": round2(bill.grand_total - (bill.taxable_total + bill.cgst_total + bill.sgst_total)),
    }


def priced_view(po: PurchaseOrder) -> dict:
    """The lines+totals to show for a PO: the immutable, persisted snapshot once billed
    (so a later catalog/rate edit can never retroactively change an issued invoice), or a
    live recompute through the tax engine while it's still an editable, unbilled PO."""
    if po.sale_bill is not None and po.sale_bill.lines:
        return _priced_view_from_snapshot(po.sale_bill)
    return price_order(po)


def po_summary(po: PurchaseOrder) -> dict:
    """Full JSON-ready view of a PO: identity, lines, and invoice-ready totals. Shared by
    the orders and OCR routers so a PO looks identical however it was created."""
    priced = priced_view(po)
    lines_out = [
        {
            "id": l["id"],
            "item_id": l["item_id"],
            "custom_name": l["custom_name"],
            "name": l["name"],
            "category": l["category"],
            "case_size": l["case_size"],
            "uom": l["uom"],
            "tax_type": l["tax_type"],
            "gst_rate": l["gst_rate"],
            "qty": l["qty"],
            "unit_rate": l["unit_rate"],
            "mrp": l["mrp"],
            "taxable": l["taxable"],
            "cgst": l["cgst"],
            "sgst": l["sgst"],
            "selling": l["selling"],
        }
        for l in priced["lines"]
    ]
    return {
        "id": po.id,
        "po_number": po.po_number,
        "customer_id": po.customer_id,
        "customer_name": po.customer.name if po.customer else None,
        "cust_code": po.customer.cust_code if po.customer else None,
        "status": po.status,
        "utr": po.utr,
        "unlisted_text": po.unlisted_text,
        "source": po.source,
        "created_at": po.created_at,
        "invoice_number": po.sale_bill.invoice_number if po.sale_bill else None,
        "lines": lines_out,
        "totals": {
            "taxable": priced["taxable"],
            "cgst": priced["cgst"],
            "sgst": priced["sgst"],
            "selling_raw": priced["selling_raw"],
            "grand_total": priced["grand_total"],
            "round_off": priced["round_off"],
        },
    }


def gst_slab_summary(priced_lines: List[dict]) -> List[dict]:
    """Group priced lines by GST slab for the invoice's 'GST summary by slab' table."""
    buckets: dict = {}
    for l in priced_lines:
        rate = l["gst_rate"]
        b = buckets.setdefault(rate, {"rate": rate, "taxable": 0.0, "gst": 0.0})
        b["taxable"] += l["_raw_taxable"]
        b["gst"] += l["_raw_gst"]
    rows = []
    for rate in sorted(buckets):
        b = buckets[rate]
        cgst, sgst = split_gst(b["gst"])
        rows.append({"rate": rate, "taxable": round2(b["taxable"]), "cgst": cgst, "sgst": sgst})
    return rows
