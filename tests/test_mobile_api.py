"""The mobile app's endpoints: /api/catalog and /api/auth, plus placing an order with the
token /api/auth returns (the app reuses POST /api/orders unchanged)."""
from tests.test_scenarios import _create_customer, _create_item


def test_catalog_prices_through_tax_engine_and_lists_categories(client, admin_headers):
    atta = _create_item(client, admin_headers, case_taxable_value=228, brand="Aashirvaad")
    _create_item(client, admin_headers, item_name="Toor Dal 1 kg", category="Rice & Pulses", discount_rate=0, case_size=1)

    r = client.get("/api/catalog")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["categories"] == ["Atta & Flour", "Rice & Pulses"]
    assert body["brands"] == ["Aashirvaad"]  # unbranded items add no entry

    row = next(i for i in body["items"] if i["id"] == atta["id"])
    assert row["mrp"] == 285
    assert row["selling_price"] == atta["pricing"]["selling"]
    assert row["case_selling_price"] == atta["pricing_case"]["selling"]
    assert row["on_offer"] is True  # discount_rate=4

    dal = next(i for i in body["items"] if i["name"] == "Toor Dal 1 kg")
    assert dal["case_selling_price"] is None
    assert dal["on_offer"] is False

    r = client.get("/api/catalog", params={"category": "Rice & Pulses"})
    assert [i["name"] for i in r.json()["items"]] == ["Toor Dal 1 kg"]


def test_catalog_hides_inactive_items(client, admin_headers):
    item = _create_item(client, admin_headers)
    r = client.patch(f"/api/items/{item['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert client.get("/api/catalog").json()["items"] == []


def test_auth_returns_token_and_name_and_rejects_bad_credentials(client, admin_headers):
    cred = _create_customer(client, admin_headers, name="Ramesh Kumar")

    r = client.post("/api/auth", json={"cust_code": cred["cust_code"].lower(), "password": cred["password"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "customer"
    assert body["cust_code"] == cred["cust_code"]
    assert body["name"] == "Ramesh Kumar"

    assert client.post("/api/auth", json={"cust_code": cred["cust_code"], "password": "wrong"}).status_code == 401
    assert client.post("/api/auth", json={"cust_code": "NOSUCH01", "password": "x"}).status_code == 401


def test_purchased_items_ranked_most_to_least_and_per_customer(client, admin_headers):
    atta = _create_item(client, admin_headers, item_name="Chakki Atta 5 kg", case_taxable_value=228)
    dal = _create_item(client, admin_headers, item_name="Toor Dal 1 kg")
    salt = _create_item(client, admin_headers, item_name="Iodised Salt 1 kg")
    never = _create_item(client, admin_headers, item_name="Never Bought")
    me = _create_customer(client, admin_headers, name="Ramesh Kumar")
    other = _create_customer(client, admin_headers, name="Other Shop", phone="9123456780")

    def headers_for(cred):
        token = client.post("/api/auth", json={"cust_code": cred["cust_code"], "password": cred["password"]}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    mine, theirs = headers_for(me), headers_for(other)
    for lines in (
        [{"item_id": dal["id"], "qty": 3}, {"item_id": salt["id"], "qty": 1}],
        [{"item_id": dal["id"], "qty": 2}, {"item_id": atta["id"], "qty": 1, "uom": "CASE"}],  # 1 case = 10 pcs
    ):
        assert client.post("/api/orders", json={"lines": lines}, headers=mine).status_code == 201
    # Another customer's orders must not leak into mine.
    client.post("/api/orders", json={"lines": [{"item_id": never["id"], "qty": 50}]}, headers=theirs)

    r = client.get("/api/customer/purchased-items", headers=mine)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [row["name"] for row in rows] == ["Chakki Atta 5 kg", "Toor Dal 1 kg", "Iodised Salt 1 kg"]
    assert [row["total_qty"] for row in rows] == [10, 5, 1]
    assert rows[1]["times_ordered"] == 2
    assert rows[0]["selling_price"] == atta["pricing"]["selling"]

    # Deactivated items drop out; no token is rejected.
    client.patch(f"/api/items/{atta['id']}", json={"is_active": False}, headers=admin_headers)
    assert [row["name"] for row in client.get("/api/customer/purchased-items", headers=mine).json()] == [
        "Toor Dal 1 kg",
        "Iodised Salt 1 kg",
    ]
    assert client.get("/api/customer/purchased-items").status_code == 401


def test_order_placed_with_auth_token(client, admin_headers):
    item = _create_item(client, admin_headers)
    cred = _create_customer(client, admin_headers)
    token = client.post("/api/auth", json={"cust_code": cred["cust_code"], "password": cred["password"]}).json()["token"]

    r = client.post(
        "/api/orders",
        json={"lines": [{"item_id": item["id"], "qty": 2}], "unlisted_text": "Kabuli chana 1kg - 2", "utr": "1234 5678 9012"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    po = r.json()
    assert po["utr"] == "123456789012"
    assert po["unlisted_text"] == "Kabuli chana 1kg - 2"
    assert po["lines"][0]["qty"] == 2
