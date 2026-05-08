import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from api.deps import get_session, require_role
from database import review_queue as rq
from database import template as tpl_db
from database.audit import log_action
from database.connection import get_db

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/pending")
def pending(session: dict = Depends(require_role("admin", "reviewer"))):
    items = rq.get_pending()
    type_map = tpl_db.get_type_name_map()
    return [_format_review_item(i, type_map) for i in items]


@router.get("/all")
def all_items(session: dict = Depends(require_role("admin", "reviewer"))):
    items = rq.get_all(50)
    type_map = tpl_db.get_type_name_map()
    return [_format_review_item(i, type_map) for i in items]


class ResolveRequest(BaseModel):
    decision: str
    reclassify: str | None = None


@router.post("/{review_id}/resolve")
def resolve(review_id: int, body: ResolveRequest, session: dict = Depends(require_role("admin", "reviewer"))):
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "无效的决策")
    rq.resolve(review_id, session["username"], body.decision)
    if body.decision == "rejected":
        with get_db() as conn:
            row = conn.execute(text(
                "SELECT image_path, operator_id, doc_type FROM review_queue WHERE id=:id"
            ), {"id": review_id}).fetchone()
        if row:
            actual_type = body.reclassify or row[2] or "review_rejected"
            log_action(
                operator_id=row[1], doc_type=actual_type, qr_content=None,
                doc_fields={}, result="REJECTED", errors=["人工复审拒绝"],
                before_img=row[0], after_img=row[0],
            )
    return {"status": "ok"}


@router.get("/pending_stamps")
def pending_stamps(session: dict = Depends(get_session)):
    items = rq.get_approved_for_stamping()
    type_map = tpl_db.get_type_name_map()
    result = []
    for item in items:
        result.append({
            "id": item[0],
            "timestamp": item[1],
            "operator_id": item[2],
            "doc_type": item[3],
            "doc_type_name": type_map.get(item[3], item[3] or "通用"),
        })
    return {"items": result}


def _basename(path):
    return os.path.basename(path) if path else None


def _format_review_item(item, type_map):
    # columns: id, timestamp, operator_id, doc_type, doc_fields,
    #          ocr_text, warnings, image_path, status, ...
    return {
        "id": item[0],
        "timestamp": item[1],
        "operator_id": item[2],
        "doc_type": item[3],
        "doc_type_name": type_map.get(item[3], item[3] or "通用"),
        "doc_fields": item[4],
        "ocr_text": item[5],
        "warnings": item[6],
        "image_path": _basename(item[7]),
        "status": item[8],
        "errors": item[6],
    }
