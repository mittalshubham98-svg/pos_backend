"""Unit tests for the dual GST tax engine. The Exclusive/Inclusive_MRP figures below are
taken directly from Invoice and Picking Sheet.dc.html so we know the backend matches the
approved prototype, not just its own internal logic.
"""
import pytest

from app.tax_engine import (
    TaxEngineError,
    invoice_round_off,
    line_totals,
    price_unit,
    round0,
    round2,
    split_gst,
)


def test_exclusive_matches_reference_invoice_chakki_atta():
    # Chakki Atta 5 kg: MRP 285, taxable 244, 5% GST, 4% trade discount, qty 20.
    unit = price_unit(mrp=285, taxable_value=244, gst_rate=5, tax_type="Exclusive", discount_rate=4)
    totals = line_totals(unit, qty=20)
    cgst, sgst = split_gst(totals["gst"])
    assert round2(totals["taxable"]) == 4684.80
    assert cgst == 117.12
    assert sgst == 117.12
    assert round2(totals["selling"]) == 4919.04


def test_inclusive_mrp_matches_reference_invoice_dishwash_bar():
    # Dishwash Bar 300 g: MRP 25, 18% GST, inclusive of MRP, qty 60 — the invoice's own
    # worked example for the CGST/SGST paisa-remainder rule (114.41 / 114.40).
    unit = price_unit(mrp=25, taxable_value=21, gst_rate=18, tax_type="Inclusive_MRP", discount_rate=0)
    totals = line_totals(unit, qty=60)
    cgst, sgst = split_gst(totals["gst"])
    assert cgst == 114.41
    assert sgst == 114.40
    assert round2(totals["selling"]) == 1500.00


def test_zero_rated_item_has_no_gst():
    # Toor Dal 1 kg: 0% GST — the invoice shows "—" for GST/CGST/SGST.
    unit = price_unit(mrp=168, taxable_value=160, gst_rate=0, tax_type="Exclusive")
    totals = line_totals(unit, qty=30)
    cgst, sgst = split_gst(totals["gst"])
    assert cgst == 0.0
    assert sgst == 0.0
    assert round2(totals["selling"]) == 4800.00


def test_rate_override_beats_computed_rate():
    unit = price_unit(mrp=285, taxable_value=244, gst_rate=5, tax_type="Exclusive", discount_rate=4, rate_override=200)
    assert unit["taxable"] == 200
    assert unit["base"] == 200


def test_out_of_slab_gst_rate_rejected():
    with pytest.raises(TaxEngineError):
        price_unit(mrp=10, taxable_value=10, gst_rate=12, tax_type="Exclusive")


def test_unknown_tax_type_rejected():
    with pytest.raises(TaxEngineError):
        price_unit(mrp=10, taxable_value=10, gst_rate=5, tax_type="Weird")


def test_invoice_round_off_matches_reference_invoice():
    rounded, delta = invoice_round_off(17575.40)
    assert rounded == 17575
    assert delta == -0.40


def test_round2_and_round0_half_up():
    assert round2(2.675) == 2.68  # classic binary-float rounding trap avoided via Decimal
    assert round0(4.5) == 5
    assert round0(4.4) == 4
