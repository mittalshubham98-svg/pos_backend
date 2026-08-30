#!/usr/bin/env python3
"""Seed the database with the same demo catalogue and customers used in the
Customer App.dc.html / Admin Portal.dc.html prototypes, so the real backend can be
exercised (and compared against the prototype) with recognisable data.

Usage:
    python -m scripts.seed_demo_data          # seed if the catalogue is empty
    python -m scripts.seed_demo_data --force   # wipe items/customers/orders and reseed

Run from the project root, with the virtualenv from requirements.txt active.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import settings_store  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Customer, Item, LedgerEntry, PoLine, PurchaseOrder, SaleBill, SaleBillLine  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.billing import convert_po_to_bill  # noqa: E402

# A representative subset of the prototype's CATALOG (Customer App.dc.html), covering both
# tax types, all non-zero GST slabs, daily-rate items, and a couple of promoted items.
CATALOG = [
    dict(item_name="Chakki Atta 5 kg", category="Atta & Flour", item_size="5 kg", case_size=10,
         mrp=285, taxable_value=244, total_gst_rate=5, tax_type="Exclusive", discount_rate=4,
         aisle="A1 · 03", hsn_code="1101"),
    dict(item_name="Refined Soyabean Oil 1 L", category="Oil & Ghee", item_size="1 L", case_size=12,
         mrp=165, taxable_value=145, total_gst_rate=5, tax_type="Exclusive", discount_rate=6,
         promo_status="DISCOUNT", aisle="B2 · 01", hsn_code="1507"),
    dict(item_name="Sona Masoori Rice 25 kg", category="Rice & Pulses", item_size="25 kg", case_size=1,
         mrp=1350, taxable_value=1285, total_gst_rate=0, tax_type="Exclusive",
         is_daily_rate_change=True, aisle="A2 · 05", hsn_code="1006"),
    dict(item_name="Toor Dal 1 kg", category="Rice & Pulses", item_size="1 kg", case_size=30,
         mrp=168, taxable_value=160, total_gst_rate=0, tax_type="Exclusive",
         is_daily_rate_change=True, aisle="A3 · 07", hsn_code="0713"),
    dict(item_name="Iodised Salt 1 kg", category="Sugar & Salt", item_size="1 kg", case_size=24,
         mrp=28, taxable_value=26, total_gst_rate=5, tax_type="Inclusive_MRP", aisle="C1 · 02",
         hsn_code="2501"),
    dict(item_name="Red Chilli Powder 500 g", category="Spices", item_size="500 g", case_size=20,
         mrp=148, taxable_value=132, total_gst_rate=5, tax_type="Exclusive",
         promo_status="NEW", aisle="C3 · 04", hsn_code="0904"),
    dict(item_name="Instant Coffee 200 g", category="Beverages", item_size="200 g", case_size=12,
         mrp=495, taxable_value=400, total_gst_rate=18, tax_type="Exclusive", aisle="D1 · 01",
         hsn_code="2101"),
    dict(item_name="Aerated Drink 750 ml", category="Beverages", item_size="750 ml", case_size=24,
         mrp=45, taxable_value=35, total_gst_rate=28, tax_type="Inclusive_MRP", aisle="C1 · 04",
         hsn_code="2202"),
    dict(item_name="Dishwash Bar 300 g", category="Cleaning", item_size="300 g", case_size=30,
         mrp=25, taxable_value=21, total_gst_rate=18, tax_type="Inclusive_MRP", aisle="D2 · 02",
         hsn_code="3401"),
    dict(item_name="Detergent Powder 4 kg", category="Cleaning", item_size="4 kg", case_size=4,
         mrp=420, taxable_value=356, total_gst_rate=18, tax_type="Exclusive",
         promo_status="DISCOUNT", discount_rate=7, aisle="D2 · 05", hsn_code="3402"),
    dict(item_name="Onion 10 kg", category="Vegetables", item_size="10 kg", case_size=1,
         mrp=320, taxable_value=320, total_gst_rate=0, tax_type="Exclusive",
         is_daily_rate_change=True, aisle="E1 · 01", hsn_code="0703"),
    dict(item_name="Hing 50 g", category="Spices", item_size="50 g", case_size=40,
         mrp=96, taxable_value=96, total_gst_rate=5, tax_type="Exclusive", aisle="C3 · 09",
         hsn_code="0910"),
]

CUSTOMERS = [
    dict(name="Sharma Kirana Store", phone="94140 77219", address="Nehru Road, Pilani 333031",
         gstin="08XYZAB5678K2Z1", kind="Kirana shop", password="PILANI0418"),
    dict(name="Annapurna Caterers", phone="98290 61143", address="Vidyavihar Road, Pilani 333031",
         gstin="", kind="Catering agency", password="PILANI0371"),
    dict(name="Birla Vidya Niketan Mess", phone="", address="Campus Mess, BITS Pilani 333031",
         gstin="08MESS4321L1Z9", kind="Institution mess", password="PILANI0209"),
]


def seed(force: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Item).count() > 0 and not force:
            print("Catalogue is not empty — pass --force to wipe and reseed. Nothing done.")
            return

        if force:
            db.query(SaleBillLine).delete()
            db.query(LedgerEntry).delete()
            db.query(SaleBill).delete()
            db.query(PoLine).delete()
            db.query(PurchaseOrder).delete()
            db.query(Item).delete()
            db.query(Customer).delete()
            db.commit()

        items = []
        for row in CATALOG:
            item = Item(**row)
            db.add(item)
            items.append(item)
        db.flush()

        customers = []
        for row in CUSTOMERS:
            plain_password = row.pop("password")
            digits = "".join(ch for ch in row.get("phone", "") if ch.isdigit()) or "0418"
            cust_code = f"CUST-{digits[-4:].rjust(4, '0')}"
            customer = Customer(cust_code=cust_code, password_hash=hash_password(plain_password), **row)
            db.add(customer)
            customers.append((customer, plain_password))
        db.commit()

        # One sample order + bill so /api/reports/*.csv and the ledger have something to show.
        # Minted through settings_store like a real order (and bumps po_next_seq afterwards) so
        # the next PO placed through the API doesn't collide with this one on po_number's unique
        # constraint.
        po = PurchaseOrder(po_number=settings_store.next_po_number(db), customer_id=customers[0][0].id,
                            status="PO_RECEIVED", utr="", unlisted_text="Kabuli chana 1kg — 5 packet",
                            source="web")
        db.add(po)
        db.flush()
        db.add(PoLine(po_id=po.id, item_id=items[0].id, qty=20))
        db.add(PoLine(po_id=po.id, item_id=items[7].id, qty=48))  # Aerated Drink (Inclusive_MRP)
        settings_store.bump_po_seq(db)
        db.commit()
        db.refresh(po)
        bill = convert_po_to_bill(db, po)

        print(f"Seeded {len(items)} items, {len(customers)} customers, and one sample bill ({bill.invoice_number}).\n")
        print("Customer login credentials (cust_code / password):")
        for customer, plain_password in customers:
            print(f"  {customer.cust_code} / {plain_password}  ({customer.name})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="wipe items/customers/orders and reseed")
    args = parser.parse_args()
    seed(force=args.force)
