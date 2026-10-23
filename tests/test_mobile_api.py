"""The mobile app's endpoints: /api/catalog and /api/auth, plus placing an order with the
token /api/auth returns (the app reuses POST /api/orders unchanged)."""
from tests.test_scenarios import _create_customer, _create_item


def test_catalog_prices_through_tax_engine_and_lists_categories(client, admin_headers):
    atta = _create_item(client, admin_headers, case_taxable_value=228)
    _create_item(client, admin_headers, item_name="Toor Dal 1 kg", category="Rice & Pulses", discount_rate=0, case_size=1)

    r = client.get("/api/catalog")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["categories"] == ["Atta & Flour", "Rice & Pulses"]

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
