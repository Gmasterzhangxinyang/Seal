import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import AUDIT_IMAGE_DIR, EXAMPLE_IMAGE_DIR

router = APIRouter(tags=["images"])


@router.get("/images/{path:path}")
def audit_image(path: str):
    basename = os.path.basename(path)
    full = os.path.join(AUDIT_IMAGE_DIR, basename)
    if os.path.exists(full):
        return FileResponse(full)
    raise HTTPException(404, "图片不存在")


@router.get("/examples/{path:path}")
def example_image(path: str):
    basename = os.path.basename(path)
    full = os.path.join(EXAMPLE_IMAGE_DIR, basename)
    if os.path.exists(full):
        return FileResponse(full)
    raise HTTPException(404, "图片不存在")
