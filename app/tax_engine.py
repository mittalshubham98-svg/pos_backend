"""Dual GST tax engine — the single source of price truth, ported 1:1 from the
`priceUnit()` function in Customer App.dc.html / Admin Portal.dc.html so the real
backend matches the approved prototype exactly.

Exclusive:      the item's taxable_value (minus discount) is the tax base; GST is added
                on top of it to get the selling price.
Inclusive_MRP:  the item's MRP (minus discount) IS the selling price; GST is reverse-derived
                out of it (selling / (1 + rate/100) = taxable).
CGST and SGST are always an exact half-split of GST. Any 1-paisa rounding remainder is
absorbed into CGST — that is how the reference invoice's per-line and slab-summary figures
balance (see split_gst() and its docstring for the worked example).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

ALLOWED_GST_RATES = (0, 3, 5, 18, 28, 40)
TAX_TYPES = ("Exclusive", "Inclusive_MRP")
# Ordering unit for a PO line: "PCS" (loose, priced off item.taxable_value) or "CASE" (a full
# case, priced off item.case_taxable_value) — see Item.case_taxable_value's docstring.
UOMS = ("PCS", "CASE")


class TaxEngineError(ValueError):
    """Raised for bad tax-relevant input (out-of-range GST slab, unknown tax type, ...).
    Routers catch this and turn it into an HTTP 400 — never a 500."""


def round2(value: float) -> float:
    """Round to 2 decimal places (paisa), half-up. Using Decimal avoids the classic
    binary-float rounding surprises (e.g. round(2.675, 2) == 2.67 in plain Python)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def round0(value: float) -> int:
    """Round to the nearest whole rupee, half-up."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def split_gst(gst_amount: float) -> Tuple[float, float]:
    """Split a GST amount into (cgst, sgst), each exactly half, with any 1-paisa rounding
    remainder absorbed into CGST.

    Worked example straight from the reference invoice (Dishwash Bar line): taxable 1271.19
    at 18% -> gst = 228.8142. Half of that is 114.4071, which rounds to 114.41; sgst is then
    the remainder, 228.81 - 114.41 = 114.40. That's exactly what the prototype's invoice
    prints: CGST 114.41, SGST 114.40.
    """
    gst_rounded = round2(gst_amount)
    cgst = round2(gst_rounded / 2)
    sgst = round2(gst_rounded - cgst)
    return cgst, sgst


def validate_gst_rate(gst_rate: float) -> None:
    if gst_rate not in ALLOWED_GST_RATES:
        raise TaxEngineError(
            f"total_gst_rate must be one of {ALLOWED_GST_RATES}, got {gst_rate!r}"
        )


def validate_tax_type(tax_type: str) -> None:
    if tax_type not in TAX_TYPES:
        raise TaxEngineError(f"tax_type must be one of {TAX_TYPES}, got {tax_type!r}")


def price_unit(
    mrp: float,
    taxable_value: float,
    gst_rate: float,
    tax_type: str,
    discount_rate: float = 0,
    rate_override: Optional[float] = None,
) -> dict:
    """Price a single unit of an item through the dual tax engine.

    Returns UNROUNDED (full float precision) amounts on purpose: per-line and invoice-level
    totals are obtained by multiplying by quantity and *then* summing across lines, and only
    rounded to paisa at the point of persisting/displaying a total (round2() / split_gst()).
    Rounding per-unit first and then multiplying by a large quantity is how off-by-a-paisa
    invoice totals happen in practice — so we deliberately don't do that here.

    Raises TaxEngineError (a ValueError) on an out-of-slab GST rate or unknown tax type;
    callers at the API boundary must catch this and respond 400, never let it become a 500.
    """
    validate_gst_rate(gst_rate)
    validate_tax_type(tax_type)

    disc = min(max(float(discount_rate or 0), 0), 100)

    if tax_type == "Inclusive_MRP":
        base = float(rate_override) if rate_override is not None else float(mrp or 0) * (1 - disc / 100)
        selling = base
        taxable = selling / (1 + gst_rate / 100)
        gst = selling - taxable
    else:  # Exclusive
        base = float(rate_override) if rate_override is not None else float(taxable_value or 0) * (1 - disc / 100)
        taxable = base
        gst = taxable * gst_rate / 100
        selling = taxable + gst

    cgst = gst / 2
    sgst = gst / 2
    return {
        "rate": gst_rate,
        "base": base,
        "taxable": taxable,
        "gst": gst,
        "cgst": cgst,
        "sgst": sgst,
        "selling": selling,
    }


def line_totals(unit: dict, qty: float) -> dict:
    """Multiply a price_unit() result by quantity to get an (unrounded) line total."""
    qty = max(float(qty or 0), 0)
    return {
        "qty": qty,
        "taxable": unit["taxable"] * qty,
        "gst": unit["gst"] * qty,
        "cgst": unit["cgst"] * qty,
        "sgst": unit["sgst"] * qty,
        "selling": unit["selling"] * qty,
    }


def invoice_round_off(sum_of_sellings: float) -> Tuple[int, float]:
    """Grand total rounded to the nearest rupee for the customer-facing total, plus the
    delta shown as 'Round off' on the invoice (rounded_total - raw_total)."""
    rounded_total = round0(sum_of_sellings)
    round_off = round2(rounded_total - sum_of_sellings)
    return rounded_total, round_off
