# Pilani Supply Co. — B2B Grocery Ordering System
### Backend build spec, handed off from the design prototype

This documents what was designed in `Customer App.dc.html`, `Admin Portal.dc.html`, and `Invoice and Picking Sheet.dc.html` so a real local Python + SQLite backend can be built to match. The prototype simulates all of this in the browser (local storage stands in for the database); nothing here has been executed as real code.

---

## 1. Stack

- **Backend:** FastAPI (recommended over Flask for automatic OpenAPI docs + Pydantic validation, both of which help hit the "no HTTP 500 on bad input" requirement).
- **DB:** SQLite file `grocery_b2b.db`, accessed via SQLAlchemy or raw `sqlite3` with WAL mode enabled (`PRAGMA journal_mode=WAL;`) for concurrent read/write from two UIs.
- **OCR:** `pytesseract` + `opencv-python` for deskew/threshold preprocessing; `thefuzz` (`process.extractOne`) for name matching against `items.item_name`.
- **Image fetch:** `duckduckgo_search` (`DDGS().images(...)`) + `requests` + `Pillow` to resize/save to `static/images/{item_id}.jpg`.
- **PDF:** `WeasyPrint` (renders HTML/CSS — reuse the invoice layout from `Invoice and Picking Sheet.dc.html` almost directly) or `ReportLab` if a pure-Python dependency is preferred.
- **Frontend:** the two `.dc.html` files are the UI spec. Rebuild them as server-rendered templates (Jinja2) or a small React/vanilla JS app hitting the API below — match their layout, copy, and interaction states exactly; they are the approved design.

---

## 2. Data model (SQLite DDL)

```sql
CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_name TEXT NOT NULL,
  category TEXT,
  item_size TEXT,
  case_size INTEGER NOT NULL DEFAULT 1 CHECK (case_size >= 1),
  mrp REAL NOT NULL DEFAULT 0 CHECK (mrp >= 0),
  taxable_value REAL NOT NULL DEFAULT 0 CHECK (taxable_value >= 0),
  total_gst_rate REAL NOT NULL DEFAULT 0 CHECK (total_gst_rate IN (0,3,5,18,28,40)),
  tax_type TEXT NOT NULL DEFAULT 'Exclusive' CHECK (tax_type IN ('Exclusive','Inclusive_MRP')),
  promo_status TEXT DEFAULT '' CHECK (promo_status IN ('','NEW','DISCOUNT')),
  discount_rate REAL NOT NULL DEFAULT 0 CHECK (discount_rate >= 0 AND discount_rate <= 100),
  is_daily_rate_change INTEGER NOT NULL DEFAULT 0,
  image_path TEXT,
  image_source TEXT DEFAULT 'none' CHECK (image_source IN ('auto','manual','none')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cust_code TEXT NOT NULL UNIQUE,        -- e.g. CUST-0418, auto-generated
  password_hash TEXT NOT NULL,           -- generated password, hashed (bcrypt), never stored plain
  name TEXT,                              -- nullable — all fields below optional
  phone TEXT,
  address TEXT,
  gstin TEXT,
  kind TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE purchase_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  po_number TEXT NOT NULL UNIQUE,         -- PO-1184
  customer_id INTEGER REFERENCES customers(id),
  status TEXT NOT NULL DEFAULT 'PO_RECEIVED' CHECK (status IN ('PO_RECEIVED','BILLED')),
  utr TEXT,                               -- nullable: blank = on-account order
  unlisted_text TEXT DEFAULT '',
  source TEXT NOT NULL DEFAULT 'web' CHECK (source IN ('web','ocr','manual')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE po_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  po_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
  item_id INTEGER REFERENCES items(id),   -- null for a custom/unlisted line
  custom_name TEXT,                       -- set only when item_id is null
  qty REAL NOT NULL DEFAULT 0 CHECK (qty >= 0),
  rate_override REAL,                     -- admin-edited unit rate; null = use item's computed rate
  gst_override REAL                       -- for custom lines only
);

CREATE TABLE sale_bills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  po_id INTEGER NOT NULL UNIQUE REFERENCES purchase_orders(id),
  invoice_number TEXT NOT NULL UNIQUE,    -- INV-2088
  taxable_total REAL NOT NULL,
  cgst_total REAL NOT NULL,
  sgst_total REAL NOT NULL,
  grand_total REAL NOT NULL,
  locked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  sale_bill_id INTEGER REFERENCES sale_bills(id),
  amount REAL NOT NULL,                   -- +ve = billed, -ve = payment received
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
-- seed rows: po_auto_purge_days, invoice_prefix, invoice_next_seq, upi_qr_path, ocr_confidence_floor
```

Indexes worth adding: `items(item_name)`, `items(is_daily_rate_change)`, `purchase_orders(status)`, `purchase_orders(customer_id)`.

---

## 3. Dual GST tax engine (must match the prototype exactly)

Given an item's `taxable_value` (or `mrp` for inclusive items), `total_gst_rate`, `tax_type`, `discount_rate`, and a quantity:

```python
def price_unit(mrp, taxable_value, gst_rate, tax_type, discount_rate, rate_override=None):
    disc = min(max(discount_rate, 0), 100)
    if tax_type == "Inclusive_MRP":
        base = rate_override if rate_override is not None else mrp * (1 - disc / 100)
        selling = base
        taxable = selling / (1 + gst_rate / 100)
        gst = selling - taxable
    else:  # Exclusive
        base = rate_override if rate_override is not None else taxable_value * (1 - disc / 100)
        taxable = base
        gst = taxable * gst_rate / 100
        selling = taxable + gst
    cgst = gst / 2
    sgst = gst / 2
    return {"taxable": taxable, "cgst": cgst, "sgst": sgst, "gst": gst, "selling": selling}
```

Multiply every field by `qty` for a line total. `total_gst_rate` is restricted to `{0, 3, 5, 18, 28, 40}` — reject any other value at the API boundary (400, not 500). CGST and SGST are always exactly half of GST, split to the paisa with any 1-paisa rounding remainder absorbed into CGST (matches the invoice's slab table).

Order/invoice grand total = sum of line `selling` values, rounded to the nearest rupee for the customer-facing total, with the rounding delta shown as "Round off" on the invoice (see the PDF layout).

---

## 4. API surface

Auth
- `POST /api/admin/login` — admin session (single shared admin account is fine for v1).
- `POST /api/customer/login` — `{cust_code, password}` → session token. Never 500 on bad credentials; return 401.
- `POST /api/admin/customers` — create customer; every field but `cust_code`/password nullable. Server generates `cust_code` + random password, returns them once in plaintext for the admin to hand over.

Catalog
- `GET /api/items?q=&category=&daily_only=` 
- `POST /api/items` / `PATCH /api/items/{id}` — admin edit (rate adjuster, watchlist).
- `POST /api/items/import` — CSV upload. Two-phase: `?dry_run=true` returns `{valid_rows, warnings[], new_skus}` without writing; a second call without `dry_run` commits. Row-level errors (bad GST slab, blank required field, non-numeric MRP) are collected into `warnings[]` and that row is skipped — the whole import must never fail wholesale on one bad row.
- `GET /api/items/template.csv` — template download.
- `POST /api/items/{id}/image` — manual image upload (multipart), overwrites `image_path`, sets `image_source='manual'`.
- Background job (APScheduler or a simple thread) on item create: attempt DuckDuckGo image fetch, save to `static/images/`, set `image_source='auto'`; on any failure (blocked, no results, network error) leave `image_path` null and `image_source='none'` — customer/admin UI falls back to a placeholder, never a broken image tag or a 500.

Orders
- `POST /api/orders` (customer) — `{lines: [{item_id, qty}], unlisted_text, utr}`. `utr` optional — null/blank means the order is placed on account (no payment gate server-side either; this mirrors the prototype's fix where UTR became optional).
- `GET /api/orders?status=` (admin)
- `PATCH /api/orders/{po_id}` — edit lines/qty/rate, add custom line, remove line. Blocked (409) once a sale bill exists for that PO.
- `POST /api/orders/{po_id}/bill` — converts to `sale_bills` row, allocates next invoice number from `settings`, writes a `ledger_entries` row for the customer, locks the PO. Atomic (single DB transaction) — a crash mid-conversion must not leave a PO half-billed.

OCR
- `POST /api/ocr/parchi` — image upload → `{lines: [{raw_text, matched_item_id, confidence, qty}], unmatched: []}`. On OCR failure (0 tokens, exception from tesseract) return `200 {success: false, reason: "..."}`, not a 500 — the admin UI shows the "could not read this parchi" state already designed.
- `POST /api/ocr/parchi/confirm` — accepted lines → creates a PO exactly like a customer order, `source='ocr'`.

Reports (admin, CSV streaming responses)
- `GET /api/reports/item-wise-sales.csv`
- `GET /api/reports/customer-wise-sales.csv`
- `GET /api/reports/customer-outstanding.csv`

Settings
- `GET/PATCH /api/settings` — purge days, invoice prefix/seq, UPI QR path, OCR confidence floor.
- Startup task: delete `purchase_orders` (and cascade `po_lines`) where `status='PO_RECEIVED'` and `created_at` older than `settings.po_auto_purge_days` (skip entirely if that setting is `0`). Never touch rows with a `sale_bills` match.

---

## 5. Screen ↔ file map

| Screen (prototype) | Rebuild target |
| --- | --- |
| `Customer App.dc.html` | Customer-facing web app: login, catalog, cart, unlisted box, QR + UTR checkout |
| `Admin Portal.dc.html` — Dashboard tab | `GET /api/orders`, `GET /api/items?daily_only=true`, aggregate metrics query |
| `Admin Portal.dc.html` — Orders tab | `PATCH/POST /api/orders/*`, `/bill` |
| `Admin Portal.dc.html` — Customers tab | `/api/admin/customers`, ledger join |
| `Admin Portal.dc.html` — Catalogue tab | `/api/items`, `/api/items/import`, image upload |
| `Admin Portal.dc.html` — Parchi OCR tab | `/api/ocr/*` |
| `Admin Portal.dc.html` — Reports & settings tab | `/api/reports/*`, `/api/settings` |
| `Invoice and Picking Sheet.dc.html` | WeasyPrint template for `GET /api/orders/{po_id}/invoice.pdf` and `/picking-sheet.pdf` |

---

## 6. Required test scenarios (from the original brief — keep these as pytest cases)

1. Customer logs in → adds items mixing `Exclusive` and `Inclusive_MRP` tax types → submits with unlisted text and no UTR (on-account) → admin edits qty/rate → converts to bill → dashboard metrics and customer ledger both reflect it correctly.
2. Create a customer with every optional field blank — only `cust_code`/password populate.
3. Import a CSV with a blank MRP, a zero qty, an out-of-range GST rate, and a duplicate item name in one file — import completes, bad rows are reported, good rows commit.
4. OCR run against an unreadable image — returns a graceful failure payload, PO is not created, no 500.
5. Image auto-fetch with the network call raising/timing out — item saves with `image_source='none'`, UI shows placeholder.
6. Convert-to-bill run twice against the same PO — second call is rejected (409), not double-billed.
