"""Central configuration, read from environment variables with sane local defaults.

Nothing here talks to the database — DB-backed, admin-editable settings (PO purge days,
invoice numbering, UPI QR path, OCR confidence floor) live in the `settings` table instead;
see app/settings_store.py. This module is for process-level config: secrets, file paths,
and the store's own letterhead details used on the printed invoice.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _default_weasyprint_dll_dir() -> None:
    """WeasyPrint needs Pango/cairo/GObject as native DLLs, which ctypes.util.find_library()
    can't locate on Windows unless told where to look (WEASYPRINT_DLL_DIRECTORIES). Rather
    than requiring every dev to set that env var by hand, default it to the standard MSYS2
    mingw64 bin directory when present and nothing else has already set it — this is exactly
    where WeasyPrint's own Windows install docs (via `pacman -S mingw-w64-x86_64-pango`) put
    those DLLs. Real deployments (Linux/mac, or a different Windows setup) are unaffected:
    this only fires when the env var is unset and that specific directory exists."""
    if sys.platform != "win32" or os.environ.get("WEASYPRINT_DLL_DIRECTORIES"):
        return
    default_dir = Path(r"C:\msys64\mingw64\bin")
    if default_dir.is_dir():
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = str(default_dir)


_default_weasyprint_dll_dir()


class Settings:
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'grocery_b2b.db').as_posix()}")

    # Auth
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    # Plain default password for a fresh local install; change via env var in any real deployment.
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "changeme123")

    # Filesystem
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    IMAGES_DIR: Path = STATIC_DIR / "images"

    # Store letterhead (printed on invoices / picking sheets)
    STORE_NAME: str = os.environ.get("STORE_NAME", "Pilani Supply Co.")
    STORE_GSTIN: str = os.environ.get("STORE_GSTIN", "08ABCDE1234F1Z5")
    STORE_FSSAI: str = os.environ.get("STORE_FSSAI", "12222016000123")
    STORE_ADDRESS: str = os.environ.get("STORE_ADDRESS", "Shop 14, Krishna Market, Pilani 333031, Rajasthan")
    STORE_PHONE: str = os.environ.get("STORE_PHONE", "+91 98280 44120")
    STORE_UPI_ID: str = os.environ.get("STORE_UPI_ID", "pilanisupply@upi")
    PLACE_OF_SUPPLY: str = os.environ.get("PLACE_OF_SUPPLY", "Rajasthan (08)")

    # OCR / image fetch behaviour
    OCR_LANG: str = os.environ.get("OCR_LANG", "eng")
    # On Windows, tesseract.exe usually isn't on PATH — point this at it explicitly, e.g.
    # C:\Program Files\Tesseract-OCR\tesseract.exe
    TESSERACT_CMD: str = os.environ.get("TESSERACT_CMD", "")
    IMAGE_FETCH_ENABLED: bool = _env_bool("IMAGE_FETCH_ENABLED", True)
    IMAGE_FETCH_TIMEOUT_SECONDS: int = int(os.environ.get("IMAGE_FETCH_TIMEOUT_SECONDS", "8"))

    # CORS: defaults to "*" for local dev (the two UIs run on file:// or a dev server).
    # In production, set CORS_ORIGINS to a comma-separated list of allowed origins, e.g.
    # "https://your-app.up.railway.app" — a customer's phone hitting the public API from
    # a real domain doesn't need every origin allowed.
    CORS_ORIGINS: list = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]


settings = Settings()
settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
settings.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
