from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_session
from database.audit import get_recent_logs, get_log_by_id
from database import template as tpl_db

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def list_logs(session: dict = Depends(get_session)):
    rows = get_recent_logs(50)
    type_map = tpl_db.get_type_name_map()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "timestamp": r[1],
            "operator_id": r[2],
            "doc_type": r[3],
            "doc_type_name": type_map.get(r[3], r[3] or "未知"),
            "qr_content": r[4],
            "result": r[5],
            "errors": r[6],
            "fields": r[7],
            "before_image": r[8],
            "after_image": r[9],
        })
    return result


@router.get("/{log_id}")
def log_detail(log_id: int, session: dict = Depends(get_session)):
    record = get_log_by_id(log_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    return record
