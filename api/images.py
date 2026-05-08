import os
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from api.deps import get_session
from config import AUDIT_IMAGE_DIR, EXAMPLE_IMAGE_DIR

router = APIRouter(tags=["images"])


@router.get("/api/images/{filename}")
def audit_image(filename: str, session: dict = Depends(get_session)):
    path = os.path.join(AUDIT_IMAGE_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "Not found"}, 404


@router.get("/api/examples/{filename}")
def example_image(filename: str, session: dict = Depends(get_session)):
    path = os.path.join(EXAMPLE_IMAGE_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "Not found"}, 404
