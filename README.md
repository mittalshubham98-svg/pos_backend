# Pilani Supply Co. — B2B Grocery Ordering System (backend)

A FastAPI + SQLite backend for the kirana-shop B2B ordering platform described in
`Handoff - Claude Code Build Spec.md`, built to serve the two prototype UIs in this
repo (`Customer App.dc.html`, `Admin Portal.dc.html`, `Invoice and Picking Sheet.dc.html`)
without changing their behaviour.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # optional — every setting has a working default
```

### Windows-only extra dependencies

Two features shell out to native libraries that Windows doesn't ship with. The rest of
the app runs fine without them — only these two features degrade (OCR fails gracefully
with `{"success": false, ...}`; PDF endpoints return `503`).

- **Tesseract-OCR** (for the parchi/OCR feature): install from
  [UB-Mannheim's build](https://github.com/UB-Mannheim/tesseract/wiki), then set
  `TESSERACT_CMD` in `.env` to the installed `tesseract.exe` path.
- **WeasyPrint** (for invoice/picking-sheet PDFs) needs the GTK3 runtime on Windows.
  Install the [GTK3 runtime installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
  and restart your shell before running the server. (macOS/Linux: WeasyPrint's own
  install docs cover `brew install pango` / the equivalent apt packages.)

### Run it

```bash
uvicorn app.main:app --reload --port 8000
```

This creates `grocery_b2b.db` (SQLite, WAL mode) next to the project root on first run
and seeds the `settings` table with defaults. Interactive API docs: `http://127.0.0.1:8000/docs`.

### Demo data

```bash
python -m scripts.seed_demo_data           # seed if the catalogue is empty
python -m scripts.seed_demo_data --force   # wipe items/customers/orders and reseed
```

Seeds a representative subset of the prototype's catalogue, the same three demo
customers (with printed login credentials), and one order converted to a bill so
`/api/reports/*` and the customer ledger have something to show.

### Tests

```bash
pytest
```

`tests/test_tax_engine.py` covers the tax engine in isolation against the reference
invoice's exact printed figures. `tests/test_scenarios.py` runs the six integration
scenarios from spec section 6 end-to-end through the API (TestClient), each against a
freshly reset in-memory-style SQLite file.

> **Note on this build:** this backend was written in a sandboxed environment with no
> package-registry access, so `pip install` could not be run and the test suite has not
> actually been executed end-to-end anywhere yet. Every module has been checked for
> syntax errors, and the tax engine, currency-words formatter, and PDF templates were
> each verified independently with standalone scripts against the reference invoice's
> exact numbers — but you should run `pytest` yourself after installing dependencies as
> the real confirmation that everything wires together.

## Deploying to Railway

Running on your laptop only serves clients on the same network — for customers to reach
the app from their own phones (any WiFi/cellular), the backend and its database need to
live on an always-on host with a public URL. This repo includes a `Dockerfile` (WeasyPrint,
Tesseract, and OpenCV all need native libraries a plain Python buildpack won't install).

1. **Push this repo to GitHub** (Railway deploys from a GitHub repo or the CLI).
2. **Create a Railway project** → "Deploy from GitHub repo" → pick this repo. Railway
   detects the `Dockerfile` automatically.
3. **Attach a volume** so the SQLite database and item images survive redeploys/restarts
   (container filesystems are otherwise wiped on every deploy): in the service's
   Settings → Volumes, add a volume mounted at `/data`.
4. **Set environment variables** on the service (Settings → Variables):
   - `SECRET_KEY` — a long random string (the code default is dev-only and must not ship)
   - `ADMIN_USERNAME` / `ADMIN_PASSWORD` — replace the `admin` / `changeme123` defaults
   - `DATABASE_URL=sqlite:////data/grocery_b2b.db` — note four slashes (absolute path
     into the volume from step 3); `docker-entrypoint.sh` also symlinks
     `app/static/images` into `/data/images` whenever `/data` exists, so uploaded/fetched
     item images land on the same volume automatically
   - `CORS_ORIGINS` — set once you have a domain (step 5), e.g.
     `https://your-app.up.railway.app`
   - the `STORE_*` letterhead variables from `.env.example`, if different from the
     Pilani Supply Co. defaults
5. **Generate a domain**: Settings → Networking → "Generate Domain". Railway terminates
   HTTPS for you. Customers open `https://your-app.up.railway.app` on their phones —
   that's the `/` route serving `customer.html`; `/admin` serves the admin portal.
6. **Redeploys**: pushing to the connected GitHub branch triggers a new build
   automatically; the volume (database + images) persists across deploys.

`pip install -r requirements.txt` on your laptop is still exactly right for local dev —
the Dockerfile is only used by Railway's build.

## Architecture

```
app/
  main.py            FastAPI app, exception handlers (never 500 on bad input), router wiring
  config.py           env-var settings (secrets, file paths, store letterhead)
  database.py         SQLAlchemy engine (WAL + FK pragmas), init_db(), get_db()
  models.py           ORM models — the DDL from the spec, plus documented extensions
  schemas.py           Pydantic v2 request/response models
  security.py          bcrypt password hashing, JWT issue/verify
  deps.py               get_current_admin / get_current_customer (both plain 401 on failure)
  settings_store.py     typed accessors over the `settings` key/value table
  tax_engine.py          pure functions: price_unit, line_totals, split_gst, invoice_round_off
  pricing.py             glues tax_engine + models into priced order/line/summary views
  utils.py                cust_code/password/PO-number generation, ₹ formatting, amount-in-words
  routers/                one module per resource (auth, items, orders, ocr, reports, settings, invoices, admin_customers)
  services/
    billing.py              PO → SaleBill conversion (atomic, snapshots line items, posts ledger)
    csv_import.py             two-phase (dry_run/commit) catalogue import with row-level warnings
    image_fetch.py             background DuckDuckGo image search, never raises
    ocr_service.py              OpenCV preprocessing + pytesseract + thefuzz matching
    pdf_service.py                Jinja2 context builders + WeasyPrint rendering
  templates/                     invoice.html, picking_sheet.html (styled to match the .dc.html reference)
  static/images/                  fetched/uploaded item images
tests/
scripts/seed_demo_data.py
```

### The dual tax engine

`app/tax_engine.py` ports the prototype's `priceUnit()` logic exactly:

- **Exclusive**: `taxable_value` from the catalogue is the base; GST is added on top
  (`gst = taxable * rate/100`, `selling = taxable + gst`).
- **Inclusive_MRP**: `mrp` is the base and already includes GST; the taxable value is
  reverse-derived (`taxable = mrp / (1 + rate/100)`, `gst = mrp - taxable`).

Every rupee amount is rounded with `Decimal(str(x)).quantize(..., ROUND_HALF_UP)` rather
than Python's native `round()`, which uses banker's rounding on binary floats and would
silently disagree with the reference invoice on values like 2.675. CGST/SGST are each
half of the rounded GST amount, with any odd paisa going to CGST — verified against the
reference invoice's own printed split.

### Historical invoice integrity (`sale_bill_lines`)

The given DDL stores only four aggregate totals per bill (`taxable_total`,
`cgst_total`, `sgst_total`, `grand_total`). Because the admin portal supports a "daily
rate watchlist" that edits `items.mrp` / `taxable_value` / `discount_rate` after orders
are placed, re-deriving a billed invoice's line items from the live `items` table would
make already-printed invoices, the picking sheet, and the sales reports silently change
whenever those prices moved — a real correctness bug. `SaleBillLine` is a new table that
freezes one row per line item (name, size, HSN, rate, GST split, everything) at the
moment `POST /api/orders/{id}/bill` runs. `app/pricing.priced_view(po)` returns that
frozen snapshot for any billed order and only recomputes live pricing for an order that
is still open — invoices, picking sheets, and reports all read through this function, so
history stays accurate no matter what happens to prices afterward.

## Additions beyond the literal spec

The spec's data model and endpoint list were followed exactly except for the following,
each added to close a gap the prototype UI or the spec's own stated behaviour needs and
otherwise couldn't have:

| Addition | Why |
|---|---|
| `items.aisle` (nullable column) | The picking sheet in the reference PDF has an aisle/bin column; the given item DDL has nowhere to store it. |
| `items.hsn_code` (nullable column) | The tax invoice has an HSN column per line; same gap. |
| `sale_bill_lines` table | See "Historical invoice integrity" above. |
| `po_next_seq` internal setting | Mirrors `invoice_next_seq`'s pattern for generating `PO-####` numbers; not exposed via the public `/api/settings` API. |
| `POST /api/admin/customers/{id}/payments` | The spec documents that a ledger entry with a negative amount represents a payment, but no endpoint in section 4 actually creates one — this is how an admin records money received against a customer's balance due. |
| `GET /api/admin/customers`, `GET /api/admin/customers/{id}` | List/detail views (balance due, order count, order history) needed by the Admin Portal's customer screens. |
| `GET /api/orders/{po_id}` | Fetch a single order — needed for the invoice/order-detail views, only list/create/patch/bill were specified. |
| `GET /api/customer/orders` | The customer-facing order history list. |
| `POST /api/settings/upi-qr` | Lets the admin upload the UPI QR image referenced by the `upi_qr_path` setting. |

None of these change or constrain any of the originally specified tables, columns, or
endpoints — existing behaviour and CSV imports that don't touch the new fields are
unaffected.

## API reference

All endpoints are prefixed `/api`. Admin endpoints require `Authorization: Bearer <token>`
from `POST /api/admin/login`; customer endpoints require a token from
`POST /api/customer/login`. Validation errors, business-rule violations (invalid GST
slab, double-billing, etc.), and database constraint violations all return `400` with a
`detail` field — the app never returns a bare `500` for bad input.

**Auth**
- `POST /api/admin/login` — `{username, password}` → `{access_token}`
- `POST /api/customer/login` — `{cust_code, password}` → `{access_token}`
- `POST /api/customer/otp/request` — `{cust_code, phone}`; on a match, generates a 5-minute
  OTP (not returned here — read it off the admin portal's customer detail panel, no SMS
  gateway is wired up)
- `POST /api/customer/otp/reset` — `{cust_code, phone, otp, new_password?}` → new
  credentials, once the OTP checks out
- `POST /api/customer/change-password` — logged-in self-service change

**Customers** *(admin)*
- `POST /api/admin/customers` — create a customer; `name`+`phone` are required (the ID is a
  short form of the name, e.g. "Ramesh Kumar" → `RAMESH01`; the phone powers OTP reset)
- `GET /api/admin/customers` — list, with balance due, order count, current password, and
  any active OTP
- `GET /api/admin/customers/{id}` — detail, with order history, current password, and any
  active OTP
- `POST /api/admin/customers/{id}/reset-password` — admin-triggered reset
- `POST /api/admin/customers/{id}/payments` — record a payment against balance due

**Catalogue** *(admin writes, public reads)*
- `GET /api/items` — search/filter
- `POST /api/items` — create; kicks off a background image fetch if no image given
- `GET /api/items/template.csv` — blank import template (12 columns incl. HSN)
- `POST /api/items/import?dry_run=true|false` — two-phase CSV import with row warnings
- `GET /api/items/{id}` / `PATCH /api/items/{id}`
- `POST /api/items/{id}/image` — manual image upload

**Orders**
- `POST /api/orders` — create a PO
- `GET /api/orders` — list (admin)
- `GET /api/orders/{id}` — detail
- `PATCH /api/orders/{id}` — edit lines/UTR/unlisted text (409 once billed)
- `POST /api/orders/{id}/bill` — convert to an immutable `SaleBill` (409 if already billed)
- `GET /api/customer/orders` — the logged-in customer's own order history

**OCR**
- `POST /api/ocr/parchi` — upload a photo of a handwritten order slip; always `200`,
  `{"success": false, "reason": ...}` on any failure to read/match it
- `POST /api/ocr/parchi/confirm` — turn a reviewed OCR result into a PO

**Reports** *(admin, CSV streaming, billed orders only)*
- `GET /api/reports/item-wise-sales.csv`
- `GET /api/reports/customer-wise-sales.csv`
- `GET /api/reports/customer-outstanding.csv`

**Settings** *(admin)*
- `GET /api/settings` / `PATCH /api/settings`
- `POST /api/settings/upi-qr`

**Invoices** *(admin, PDF)*
- `GET /api/orders/{id}/invoice.pdf`
- `GET /api/orders/{id}/picking-sheet.pdf`

**Misc**
- `GET /api/health`
