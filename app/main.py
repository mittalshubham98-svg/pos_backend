"""FastAPI application entrypoint.

Design principle running through this whole backend (handoff spec: "no HTTP 500 on bad
input"): Pydantic/FastAPI validation errors are remapped to 400 below, and every place that
touches something inherently unreliable — OCR, image fetch, CSV import — catches its own
failures and returns a normal response describing what went wrong, rather than raising.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import SessionLocal, init_db
from .models import PurchaseOrder
from .routers import admin_customers, auth, invoices, items, ocr, orders, reports, settings_router
from .tax_engine import TaxEngineError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pos_backend")

app = FastAPI(
    title="Pilani Supply Co. — B2B Grocery Ordering API",
    description="Backend for the customer ordering app and admin portal described in the handoff spec.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _json_safe_validation_errors(errors: list) -> list:
    """pydantic v2 puts the raw exception instance in ctx['error'] for any field_validator
    that raises ValueError (e.g. the GST slab check, or a too-short password) — Starlette's
    plain json.dumps can't serialize an exception object, which would otherwise turn a bad
    request into a 500. Stringify it so the 400 path below actually works."""
    safe = []
    for err in errors:
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict):
            err["ctx"] = {k: (str(v) if isinstance(v, BaseException) else v) for k, v in ctx.items()}
        safe.append(err)
    return safe


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Bad request shape/values -> 400, not FastAPI's default 422. The handoff spec is
    explicit about this for the GST slab check; we apply it uniformly to all request
    validation so the rule is simple and predictable for API consumers."""
    return JSONResponse(status_code=400, content={"detail": _json_safe_validation_errors(exc.errors())})


@app.exception_handler(TaxEngineError)
async def tax_engine_exception_handler(request: Request, exc: TaxEngineError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    """Catch-all for a plain ValueError bubbling up from business logic (bad numeric
    input, etc.) — still a client error, never a 500."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """A DB-level CHECK/NOT NULL/UNIQUE violation slipping past request validation (e.g. a
    PATCH that explicitly sets a required field to `null`) is still bad input, not a server
    fault — 400, not 500. The request-scoped session's own `finally: db.close()` (see
    database.get_db) unwinds the failed transaction; nothing more to clean up here."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Request violates a database constraint (e.g. a required field was null, or a value must be unique)."},
    )


app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(admin_customers.router)
app.include_router(items.router)
app.include_router(orders.router)
app.include_router(orders.customer_router)
app.include_router(ocr.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(invoices.router)


def purge_stale_pos() -> int:
    """Startup task: delete unbilled POs older than settings.po_auto_purge_days. Skipped
    entirely when that setting is 0. Never touches a PO that already has a sale bill —
    filtered both by status and by an explicit outer-join check, belt and suspenders."""
    from . import settings_store

    db = SessionLocal()
    try:
        days = settings_store.get_int(db, "po_auto_purge_days", 30)
        if days <= 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        stale = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.status == "PO_RECEIVED")
            .filter(PurchaseOrder.created_at < cutoff)
            .all()
        )
        count = 0
        for po in stale:
            if po.sale_bill is not None:
                continue  # never purge a billed PO, defensively, even though status should already exclude it
            db.delete(po)
            count += 1
        if count:
            db.commit()
        return count
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    purged = purge_stale_pos()
    if purged:
        logger.info("startup purge: removed %d stale unbilled PO(s)", purged)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "pos_backend"}


# The customer app and admin portal are static HTML/JS files served straight out of
# app/static (see app/static/customer.html, admin.html, api.js) — no separate frontend
# build step. These two routes just give them friendly URLs; the files are also reachable
# directly at /static/customer.html and /static/admin.html via the mount above.
#
# no-cache (not no-store) on all three: browsers must revalidate with the server on every
# request instead of serving straight from disk cache. Without this, FileResponse's own
# Last-Modified/ETag headers are the only cache signal, and a browser's heuristic freshness
# rules can serve an already-open tab a stale copy of the app shell for a long time after a
# deploy (a real incident: a newly deployed admin-table column stayed invisible in a
# customer's browser well after the server itself had the new file — see sw.js's matching
# fix for the service-worker layer of this same problem). Revalidation is cheap: an
# unchanged file still gets a 304 with no body.
_NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


@app.get("/")
def customer_app() -> FileResponse:
    return FileResponse(settings.STATIC_DIR / "customer.html", headers=_NO_CACHE_HEADERS)


@app.get("/admin")
def admin_portal() -> FileResponse:
    return FileResponse(settings.STATIC_DIR / "admin.html", headers=_NO_CACHE_HEADERS)


@app.get("/sw.js")
def service_worker() -> FileResponse:
    """Top-level route (not /static/sw.js) so the worker's default scope is the whole
    app ("/"), not just "/static/" — it must control navigations to "/" and "/admin"."""
    return FileResponse(settings.STATIC_DIR / "sw.js", media_type="application/javascript", headers=_NO_CACHE_HEADERS)
