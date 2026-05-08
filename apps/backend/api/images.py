import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import AUDIT_IMAGE_DIR, EXAMPLE_IMAGE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


@router.get("/images/{filename}")
def audit_image(filename: str):
    basename = os.path.basename(filename)
    full = os.path.join(AUDIT_IMAGE_DIR, basename)
    if os.path.exists(full):
        return FileResponse(full)
    raise HTTPException(404, f"图片不存在: {basename}")


@router.get("/examples/{filename}")
def example_image(filename: str):
    basename = os.path.basename(filename)
    full = os.path.join(EXAMPLE_IMAGE_DIR, basename)
    if os.path.exists(full):
        return FileResponse(full)
    raise HTTPException(404, f"图片不存在: {basename}")
