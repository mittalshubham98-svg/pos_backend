"""The six required test scenarios from the handoff spec, section 6, verbatim in spirit:

1. Customer logs in -> mixed Exclusive/Inclusive_MRP order, unlisted text, no UTR (on
   account) -> admin edits qty/rate -> converts to bill -> ledger reflects it correctly.
2. Customer created with every optional field blank.
3. CSV import with a blank MRP, a coerced Case_Size, an out-of-range GST rate, and a
   duplicate item name — import completes, bad rows reported, good rows commit.
4. OCR against an unreadable image -> graceful failure, no PO created, no 500.
5. Image auto-fetch whose network call raises -> item saves with image_source='none'.
6. Billing the same PO twice -> second call rejected with 409, never double-billed.
"""
import app.services.image_fetch as image_fetch


def _create_item(client, admin_headers, **overrides):
    payload = {
        "item_name": "Chakki Atta 5 kg",
        "category": "Atta & Flour",
        "item_size": "5 kg",
        "case_size": 10,
        "mrp": 285,
        "taxable_value": 244,
        "total_gst_rate": 5,
        "tax_type": "Exclusive",
        "discount_rate": 4,
    }
    payload.update(overrides)
    r = client.post("/api/items", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_customer(client, admin_headers, **overrides):
    payload = {"name": "Test Customer", "phone": "9876543210"}
    payload.update(overrides)
    r = client.post("/api/admin/customers", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _customer_headers(client, cust_code, password):
    r = client.post("/api/customer/login", json={"cust_code": cust_code, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _customer_row(client, admin_headers, cust_code):
    r = client.get("/api/admin/customers", headers=admin_headers)
    assert r.status_code == 200, r.text
    return next(c for c in r.json() if c["cust_code"] == cust_code)


# --- Scenario 1 ---------------------------------------------------------------------


def test_scenario_1_mixed_tax_types_on_account_order_to_bill(client, admin_headers):
    item_excl = _create_item(
        client, admin_headers,
        item_name="Chakki Atta 5 kg", tax_type="Exclusive", mrp=285, taxable_value=244,
        total_gst_rate=5, discount_rate=4,
    )
    item_incl = _create_item(
        client, admin_headers,
        item_name="Aerated Drink 750 ml", tax_type="Inclusive_MRP", mrp=45, taxable_value=35,
        total_gst_rate=28, discount_rate=0,
    )

    customer = _create_customer(client, admin_headers, name="Sharma Kirana Store")
    cust_headers = _customer_headers(client, customer["cust_code"], customer["password"])

    order_payload = {
        "lines": [
            {"item_id": item_excl["id"], "qty": 20},
            {"item_id": item_incl["id"], "qty": 48},
        ],
        "unlisted_text": "Kabuli chana 1kg — 5 packet",
        "utr": None,
    }
    r = client.post("/api/orders", json=order_payload, headers=cust_headers)
    assert r.status_code == 201, r.text
    po = r.json()
    assert po["status"] == "PO_RECEIVED"
    assert po["utr"] is None
    assert po["unlisted_text"].startswith("Kabuli")
    assert po["source"] == "web"

    excl_line_id = next(l["id"] for l in po["lines"] if l["item_id"] == item_excl["id"])
    r = client.patch(
        f"/api/orders/{po['id']}",
        json={"update_lines": [{"line_id": excl_line_id, "qty": 25}]},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert next(l["qty"] for l in updated["lines"] if l["id"] == excl_line_id) == 25

    r = client.post(f"/api/orders/{po['id']}/bill", headers=admin_headers)
    assert r.status_code == 200, r.text
    bill = r.json()
    assert bill["invoice_number"]

    cust_row = _customer_row(client, admin_headers, customer["cust_code"])
    r = client.get(f"/api/admin/customers/{cust_row['id']}", headers=admin_headers)
    assert r.status_code == 200, r.text
    detail = r.json()
    # On-account order (no UTR) -> the full billed amount is still on the ledger.
    assert detail["balance_due"] == bill["grand_total"]
    assert detail["lifetime_billed"] == bill["grand_total"]
    assert detail["order_count"] == 1

    r = client.get("/api/orders", params={"status": "BILLED"}, headers=admin_headers)
    assert any(o["id"] == po["id"] for o in r.json())


# --- Scenario 1b: loose (PCS) vs. full-case (CASE) ordering charge different rates -----


def test_scenario_1b_loose_vs_case_order_lines_price_differently(client, admin_headers):
    item = _create_item(
        client, admin_headers,
        item_name="Chakki Atta 5 kg", case_size=10, tax_type="Exclusive",
        mrp=285, taxable_value=244, case_taxable_value=228, total_gst_rate=5, discount_rate=0,
    )
    # The catalogue view exposes both rates: loose (taxable_value) and case (case_taxable_value).
    r = client.get(f"/api/items/{item['id']}")
    assert r.status_code == 200, r.text
    catalog_item = r.json()
    assert catalog_item["pricing"]["taxable"] == 244
    assert catalog_item["pricing_case"]["taxable"] == 228

    customer = _create_customer(client, admin_headers, name="Loose vs Case Store")
    cust_headers = _customer_headers(client, customer["cust_code"], customer["password"])

    # 5 loose pieces at the piece rate, plus 2 full cases (= 20 pieces) at the case rate.
    order_payload = {
        "lines": [
            {"item_id": item["id"], "qty": 5, "uom": "PCS"},
            {"item_id": item["id"], "qty": 2, "uom": "CASE"},
        ],
    }
    r = client.post("/api/orders", json=order_payload, headers=cust_headers)
    assert r.status_code == 201, r.text
    po = r.json()

    pcs_line = next(l for l in po["lines"] if l["uom"] == "PCS")
    case_line = next(l for l in po["lines"] if l["uom"] == "CASE")
    assert pcs_line["qty"] == 5
    assert pcs_line["unit_rate"] == 244
    # Case qty is stored in pieces (2 cases x 10/case = 20), priced at the case rate.
    assert case_line["qty"] == 20
    assert case_line["unit_rate"] == 228


def test_scenario_1c_zero_case_taxable_value_is_not_set_falls_back_to_loose_rate(client, admin_headers):
    """case_taxable_value defaults to 0 for items uploaded before this feature (and for any
    item where the admin just leaves it blank) — 0 must mean "no case rate configured" and
    fall back to the loose rate, the same "not set" convention already used by mrp/taxable_value
    elsewhere in the item master, never an actual free/₹0 case price."""
    item = _create_item(
        client, admin_headers,
        item_name="Old Stock Item", case_size=10, tax_type="Exclusive",
        mrp=100, taxable_value=90, total_gst_rate=5, discount_rate=0,
    )
    assert item["case_taxable_value"] == 0

    r = client.get(f"/api/items/{item['id']}")
    assert r.status_code == 200, r.text
    catalog_item = r.json()
    assert catalog_item["case_taxable_value"] == 0
    assert catalog_item["pricing_case"] is None  # no case option offered

    customer = _create_customer(client, admin_headers, name="Old Stock Store")
    cust_headers = _customer_headers(client, customer["cust_code"], customer["password"])
    r = client.post(
        "/api/orders",
        json={"lines": [{"item_id": item["id"], "qty": 2, "uom": "CASE"}]},
        headers=cust_headers,
    )
    assert r.status_code == 201, r.text
    case_line = r.json()["lines"][0]
    assert case_line["qty"] == 20
    assert case_line["unit_rate"] == 90  # loose rate, not free


# --- Scenario 2 ---------------------------------------------------------------------


def test_scenario_2_customer_created_with_all_optional_fields_blank(client, admin_headers):
    # name and phone are the only compulsory fields now: the ID is derived from the name,
    # and the phone is what powers self-service password reset.
    r = client.post("/api/admin/customers", json={"name": "Ramesh Kumar", "phone": "9876543210"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    cred = r.json()
    assert cred["cust_code"].startswith("RAMESH")
    assert cred["password"]
    assert cred["name"] == "Ramesh Kumar"
    assert cred["phone"] == "9876543210"
    assert cred["address"] is None
    assert cred["gstin"] is None
    assert cred["kind"] is None

    # And the generated credentials actually work.
    r = client.post("/api/customer/login", json={"cust_code": cred["cust_code"], "password": cred["password"]})
    assert r.status_code == 200, r.text


def test_scenario_2b_customer_creation_requires_name_and_phone(client, admin_headers):
    r = client.post("/api/admin/customers", json={}, headers=admin_headers)
    assert r.status_code == 400, r.text

    r = client.post("/api/admin/customers", json={"name": "No Phone Customer"}, headers=admin_headers)
    assert r.status_code == 400, r.text

    r = client.post("/api/admin/customers", json={"phone": "9876543210"}, headers=admin_headers)
    assert r.status_code == 400, r.text


# --- Scenario 3 ---------------------------------------------------------------------

_CSV_HEADER = "Item_Name,Category,Item_Size,Case_Size,MRP,Taxable_Value,Total_GST_Rate,Tax_Type,Promo_Status,Discount_Rate,Is_Daily_Rate_Change,Aisle,HSN_Code"
_CSV_BODY = "\n".join(
    [
        _CSV_HEADER,
        "Good Item A,Grocery,1 kg,10,100,90,5,Exclusive,,0,0,A1,1101",
        "Bad MRP Item,Grocery,1 kg,10,,90,5,Inclusive_MRP,,0,0,A1,1101",
        "Zero Case Item,Grocery,1 kg,0,100,90,5,Exclusive,,0,0,A1,1101",
        "Bad GST Item,Grocery,1 kg,10,100,90,12,Exclusive,,0,0,A1,1101",
        "Dup Name Item,Grocery,1 kg,10,100,90,5,Exclusive,,0,0,A1,1101",
        "Dup Name Item,Grocery,1 kg,10,200,180,5,Exclusive,,0,0,A1,1101",
    ]
)


def test_scenario_3_csv_import_bad_rows_reported_good_rows_commit(client, admin_headers):
    files = {"file": ("items.csv", _CSV_BODY, "text/csv")}
    r = client.post("/api/items/import", params={"dry_run": True}, files=files, headers=admin_headers)
    assert r.status_code == 200, r.text
    dry = r.json()
    assert dry["dry_run"] is True
    # Good Item A, Bad MRP Item (blank MRP imported at ₹0, not skipped), Zero Case Item
    # (coerced, not skipped), Dup Name Item (later row wins) = 4
    assert dry["valid_rows"] == 4
    assert dry["new_skus"] == 4
    assert len(dry["warnings"]) >= 3  # blank MRP, bad GST, coerced case size, + duplicate note

    files = {"file": ("items.csv", _CSV_BODY, "text/csv")}
    r = client.post("/api/items/import", params={"dry_run": False}, files=files, headers=admin_headers)
    assert r.status_code == 200, r.text
    commit = r.json()
    assert commit["dry_run"] is False
    assert commit["committed"] == 4

    r = client.get("/api/items", headers=admin_headers)
    items_by_name = {i["item_name"]: i for i in r.json()}
    assert "Good Item A" in items_by_name
    assert "Zero Case Item" in items_by_name
    assert items_by_name["Zero Case Item"]["case_size"] == 1  # coerced from 0
    assert "Dup Name Item" in items_by_name
    assert items_by_name["Dup Name Item"]["mrp"] == 200  # later duplicate row wins
    # Blank MRP no longer skips the row — item is imported with a ₹0 selling value so it
    # still shows up in the catalogue, ready for the admin to fill in the price manually.
    assert "Bad MRP Item" in items_by_name
    assert items_by_name["Bad MRP Item"]["mrp"] == 0
    assert "Bad GST Item" not in items_by_name


# --- Scenario 4 ---------------------------------------------------------------------


def test_scenario_4_ocr_unreadable_image_fails_gracefully(client, admin_headers):
    garbage = b"this is not image data, just plain bytes" * 20
    files = {"file": ("parchi.jpg", garbage, "image/jpeg")}
    r = client.post("/api/ocr/parchi", files=files, headers=admin_headers)
    assert r.status_code == 200  # never a 500
    body = r.json()
    assert body["success"] is False
    assert body["reason"]

    r = client.get("/api/orders", headers=admin_headers)
    assert r.json() == []  # no PO was created as a side effect of the failed read


# --- Scenario 5 ---------------------------------------------------------------------


def test_scenario_5_image_fetch_network_failure_leaves_placeholder(client, admin_headers, monkeypatch):
    item = _create_item(client, admin_headers, item_name="Unfetchable Item")
    assert item["image_source"] == "none"
    assert item["image_path"] is None

    def _boom(query):
        raise RuntimeError("network unreachable")

    monkeypatch.setattr(image_fetch, "_search_image_url", _boom)
    image_fetch.fetch_and_save_image(item["id"], item["item_name"])  # must not raise

    r = client.get(f"/api/items/{item['id']}", headers=admin_headers)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["image_source"] == "none"
    assert updated["image_path"] is None


# --- Scenario 6 ---------------------------------------------------------------------


def test_scenario_6_double_billing_rejected(client, admin_headers):
    item = _create_item(client, admin_headers, item_name="Bill Twice Item")
    customer = _create_customer(client, admin_headers)
    cust_headers = _customer_headers(client, customer["cust_code"], customer["password"])

    r = client.post(
        "/api/orders",
        json={"lines": [{"item_id": item["id"], "qty": 5}], "utr": None},
        headers=cust_headers,
    )
    assert r.status_code == 201, r.text
    po = r.json()

    r1 = client.post(f"/api/orders/{po['id']}/bill", headers=admin_headers)
    assert r1.status_code == 200, r1.text

    r2 = client.post(f"/api/orders/{po['id']}/bill", headers=admin_headers)
    assert r2.status_code == 409

    r = client.get(f"/api/orders/{po['id']}", headers=admin_headers)
    assert r.json()["invoice_number"] == r1.json()["invoice_number"]


# --- Scenario 7: mobile-number + OTP self-service password reset, admin visibility -----


def test_scenario_7_otp_password_reset_and_admin_visibility(client, admin_headers):
    customer = _create_customer(client, admin_headers, name="Ramesh Kumar", phone="9876543210")

    # The admin portal can see the current password right after creation.
    row = _customer_row(client, admin_headers, customer["cust_code"])
    assert row["password"] == customer["password"]
    assert row["otp_code"] is None

    # Wrong phone never matches, and never reveals which field was wrong.
    r = client.post(
        "/api/customer/otp/request",
        json={"cust_code": customer["cust_code"], "phone": "0000000000"},
    )
    assert r.status_code == 401, r.text

    # Requesting an OTP does not leak the actual code over the API...
    r = client.post(
        "/api/customer/otp/request",
        json={"cust_code": customer["cust_code"], "phone": "9876543210"},
    )
    assert r.status_code == 200, r.text
    assert set(r.json().keys()) == {"ok", "message"}

    # ...it shows up in the admin portal instead, for the shopkeeper to read out.
    detail = client.get(f"/api/admin/customers/{row['id']}", headers=admin_headers).json()
    otp = detail["otp_code"]
    assert otp and len(otp) == 6 and otp.isdigit()
    assert detail["otp_expires_at"]

    # A wrong OTP is rejected.
    r = client.post(
        "/api/customer/otp/reset",
        json={"cust_code": customer["cust_code"], "phone": "9876543210", "otp": "000000"},
    )
    assert r.status_code == 401, r.text

    # The correct OTP resets the password (chosen or random) and clears the OTP.
    r = client.post(
        "/api/customer/otp/reset",
        json={"cust_code": customer["cust_code"], "phone": "9876543210", "otp": otp, "new_password": "MyNewPass1"},
    )
    assert r.status_code == 200, r.text
    new_password = r.json()["password"]
    assert new_password == "MyNewPass1"

    # Old password no longer works, new one does.
    r = client.post("/api/customer/login", json={"cust_code": customer["cust_code"], "password": customer["password"]})
    assert r.status_code == 401
    r = client.post("/api/customer/login", json={"cust_code": customer["cust_code"], "password": new_password})
    assert r.status_code == 200, r.text

    # The OTP is single-use — reusing it now fails.
    r = client.post(
        "/api/customer/otp/reset",
        json={"cust_code": customer["cust_code"], "phone": "9876543210", "otp": otp},
    )
    assert r.status_code == 401, r.text

    # And the admin portal now shows the freshly reset password.
    detail = client.get(f"/api/admin/customers/{row['id']}", headers=admin_headers).json()
    assert detail["password"] == new_password
    assert detail["otp_code"] is None
