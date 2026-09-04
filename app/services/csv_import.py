"""Two-phase CSV catalogue import: `dry_run=true` validates and reports without writing;
a second call without dry_run commits. Row-level problems are collected as warnings and
that row is skipped — the whole import must never fail wholesale on one bad row (handoff
spec section 4).
"""
import csv
import io
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import Item
from ..tax_engine import ALLOWED_GST_RATES, TAX_TYPES

TEMPLATE_COLUMNS = [
    "Item_Name",
    "Category",
    "Brand",
    "Item_Size",
    "Case_Size",
    "MRP",
    "Taxable_Value",
    "Case_Taxable_Value",
    "Total_GST_Rate",
    "Tax_Type",
    "Promo_Status",
    "Discount_Rate",
    "Is_Daily_Rate_Change",
    "Aisle",
    "HSN_Code",
]

MRP_SANITY_CEILING = 500_000


def template_csv_bytes() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_COLUMNS)
    writer.writerow(
        ["Chakki Atta 5 kg", "Atta & Flour", "Aashirvaad", "5 kg", "10", "285", "244", "228", "5", "Exclusive", "", "4", "0", "A1 · 03", "1101"]
    )
    return buf.getvalue().encode("utf-8")


def _num(raw: Optional[str]):
    """Returns None for blank, the parsed float for a valid number, or the sentinel
    "INVALID" for something that isn't a number at all — three outcomes a warning message
    can distinguish between."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return "INVALID"


def _truthy(raw: Optional[str]) -> bool:
    return str(raw or "").strip().lower() in ("1", "true", "yes", "y")


def validate_row(row: Dict[str, str]) -> Tuple[Optional[dict], Optional[str]]:
    """Returns (item_data, warning). item_data is None when the row must be skipped
    entirely; warning is set whenever something about the row is worth flagging, even for
    rows that still commit (e.g. a coerced Case_Size)."""
    name = (row.get("Item_Name") or "").strip()
    if not name:
        return None, "Item_Name is blank — row skipped"

    gst = _num(row.get("Total_GST_Rate"))
    if gst is None:
        gst = 0
    if gst == "INVALID":
        return None, f"Total_GST_Rate {row.get('Total_GST_Rate')!r} is not numeric — row skipped"
    if gst not in ALLOWED_GST_RATES:
        return None, f"Total_GST_Rate {gst!r} is not in {ALLOWED_GST_RATES} — row skipped"

    tax_type = (row.get("Tax_Type") or "Exclusive").strip() or "Exclusive"
    if tax_type not in TAX_TYPES:
        return None, f"Tax_Type {tax_type!r} is not one of {TAX_TYPES} — row skipped"

    mrp = _num(row.get("MRP"))
    taxable_value = _num(row.get("Taxable_Value"))
    case_taxable_value = _num(row.get("Case_Taxable_Value"))
    if mrp == "INVALID" or taxable_value == "INVALID":
        return None, "MRP/Taxable_Value is not numeric — row skipped"
    if case_taxable_value == "INVALID":
        return None, "Case_Taxable_Value is not numeric — row skipped"

    if mrp is not None and mrp > MRP_SANITY_CEILING:
        return None, f"MRP {mrp:g} exceeds sanity ceiling of {MRP_SANITY_CEILING} — held for review, row skipped"

    warning = None
    if tax_type == "Inclusive_MRP" and not mrp:
        warning = "MRP blank — item imported at ₹0 selling value, set it manually before selling"
    elif tax_type == "Exclusive" and not taxable_value:
        warning = "Taxable_Value blank — item imported at ₹0 selling value, set it manually before selling"

    case_size_raw = _num(row.get("Case_Size"))
    if case_size_raw == "INVALID" or case_size_raw is None or case_size_raw < 1:
        prior = warning
        warning = (prior + "; " if prior else "") + f"Case_Size {row.get('Case_Size')!r} — coerced to 1"
        case_size = 1
    else:
        case_size = int(case_size_raw)

    discount_rate = _num(row.get("Discount_Rate"))
    if discount_rate == "INVALID" or discount_rate is None:
        discount_rate = 0
    if discount_rate < 0 or discount_rate > 100:
        prior = warning
        warning = (prior + "; " if prior else "") + f"Discount_Rate {discount_rate:g} out of 0-100 — clamped"
        discount_rate = min(max(discount_rate, 0), 100)

    promo_status = (row.get("Promo_Status") or "").strip()
    if promo_status not in ("", "NEW", "DISCOUNT"):
        prior = warning
        warning = (prior + "; " if prior else "") + f"Promo_Status {promo_status!r} not recognised — cleared"
        promo_status = ""

    data = {
        "item_name": name,
        "category": (row.get("Category") or "").strip() or None,
        "brand": (row.get("Brand") or "").strip() or None,
        "item_size": (row.get("Item_Size") or "").strip() or None,
        "case_size": case_size,
        "mrp": mrp or 0,
        "taxable_value": taxable_value or 0,
        "case_taxable_value": case_taxable_value or 0,
        "total_gst_rate": gst,
        "tax_type": tax_type,
        "promo_status": promo_status,
        "discount_rate": discount_rate,
        "is_daily_rate_change": _truthy(row.get("Is_Daily_Rate_Change")),
        "aisle": (row.get("Aisle") or "").strip() or None,
        "hsn_code": (row.get("HSN_Code") or "").strip() or None,
    }
    return data, warning


def _sku_key(item_name: str, brand: Optional[str]) -> Tuple[str, str]:
    """A SKU is identified by (name, brand) together, not name alone — two rows with the
    same Item_Name but different Brand are different products (e.g. "Chakki Atta 5 kg" from
    Aashirvaad vs. Patanjali) and must both be kept, not have one overwrite the other."""
    return (item_name.strip().lower(), (brand or "").strip().lower())


def process_csv(db: Session, csv_text: str, dry_run: bool) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return {"valid_rows": 0, "warnings": [{"row": 0, "message": "CSV appears to be empty"}], "new_skus": 0, "committed": 0}

    valid: Dict[Tuple[str, str], dict] = {}
    order: List[Tuple[str, str]] = []
    warnings: List[dict] = []

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        data, warning = validate_row(row)
        if data is None:
            warnings.append({"row": i, "message": warning or "row skipped"})
            continue
        key = _sku_key(data["item_name"], data["brand"])
        if key in valid:
            brand_note = f" (brand {data['brand']!r})" if data["brand"] else ""
            warnings.append({"row": i, "message": f"Item_Name {data['item_name']!r}{brand_note} duplicates an earlier row — later row wins"})
        else:
            order.append(key)
        valid[key] = data
        if warning:
            warnings.append({"row": i, "message": warning})

    existing = {
        _sku_key(name, brand): item_id
        for name, brand, item_id in db.query(Item.item_name, Item.brand, Item.id).all()
    }
    new_skus = sum(1 for k in valid if k not in existing)

    result = {"valid_rows": len(valid), "warnings": warnings, "new_skus": new_skus, "committed": 0, "new_item_ids": []}
    if dry_run:
        return result

    committed = 0
    new_item_ids: List[int] = []
    for key in order:
        data = valid[key]
        existing_id = existing.get(key)
        if existing_id:
            item = db.get(Item, existing_id)
            for field, value in data.items():
                setattr(item, field, value)
        else:
            item = Item(**data)
            db.add(item)
            db.flush()
            new_item_ids.append(item.id)
        committed += 1

    db.commit()
    result["committed"] = committed
    result["new_item_ids"] = new_item_ids
    return result
