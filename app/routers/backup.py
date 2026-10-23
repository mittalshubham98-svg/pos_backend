import os, sqlite3, tempfile, shutil
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from app.deps import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["backup"])

def _db_path():
    url = os.getenv("DATABASE_URL", "sqlite:///./grocery_b2b.db")
    return url.replace("sqlite:///", "", 1)

@router.get("/backup-db")
def backup_db(admin=Depends(get_current_admin)):
    tmp = os.path.join(tempfile.gettempdir(), "backup.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    s = sqlite3.connect(_db_path())
    d = sqlite3.connect(tmp)
    s.backup(d)
    d.close()
    s.close()
    return FileResponse(tmp, filename="grocery_b2b_backup.db")

@router.get("/backup-images")
def backup_images(admin=Depends(get_current_admin)):
    base = os.path.join(tempfile.gettempdir(), "images_backup")
    zip_path = shutil.make_archive(base, "zip", os.path.join("app", "static", "images"))
    return FileResponse(zip_path, filename="images_backup.zip")