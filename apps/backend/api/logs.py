import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_session, require_role
from database.audit import get_recent_logs, get_log_by_id
from database import template as tpl_db
from database.connection import get_db

router = APIRouter(prefix="/logs", tags=["logs"])
logger = logging.getLogger(__name__)


def _basename(path):
    return os.path.basename(path) if path else None


@router.get("")
def list_logs(session: dict = Depends(get_session)):
    rows = get_recent_logs(50)
    type_map = tpl_db.get_type_name_map()
    result = []
    for r in rows:
        # columns: id, timestamp, operator_id, doc_type, qr_content,
        #          doc_fields, ocr_text, result, errors, before_img, after_img, dms_doc_id
        result.append(
            {
                "id": r[0],
                "timestamp": r[1],
                "operator_id": r[2],
                "doc_type": r[3],
                "doc_type_name": type_map.get(r[3], r[3] or "未知"),
                "qr_content": r[4],
                "result": r[7],
                "errors": r[8],
                "fields": r[5],
                "ocr_text": r[6],
                "before_image": _basename(r[9]),
                "after_image": _basename(r[10]),
            }
        )
    return result


@router.get("/{log_id}")
def log_detail(log_id: int, session: dict = Depends(get_session)):
    record = get_log_by_id(log_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    return record


@router.delete("/{log_id}")
def delete_log(log_id: int, session: dict = Depends(require_role("admin"))):
    """删除审计日志，同时重置关联的请假申请状态（允许重新扫码盖章）"""
    from sqlalchemy import text

    record = get_log_by_id(log_id)
    if not record:
        raise HTTPException(404, "记录不存在")

    qr_content = record.get("qr_content")
    doc_type = record.get("doc_type")

    with get_db() as conn:
        # 如果是请假类型，重置 leave_applications 状态为 APPROVED，清除盖章信息
        if doc_type == "leave" and qr_content:
            try:
                payload = json.loads(qr_content)
                application_id = payload.get("application_id")
                if application_id:
                    conn.execute(
                        text("""
                            UPDATE leave_applications
                            SET status='APPROVED', stamped_at=NULL, updated_at=NOW()
                            WHERE application_id=:aid
                        """),
                        {"aid": application_id},
                    )
                    # 删除关联的 stamp_tasks 和 verification_results
                    conn.execute(
                        text("DELETE FROM verification_results WHERE task_id IN "
                             "(SELECT task_id FROM stamp_tasks WHERE application_id=:aid)"),
                        {"aid": application_id},
                    )
                    conn.execute(
                        text("DELETE FROM stamp_tasks WHERE application_id=:aid"),
                        {"aid": application_id},
                    )
                    logger.info(
                        f"[logs] 已重置请假申请 {application_id} 为 APPROVED"
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        # 删除审计日志
        conn.execute(text("DELETE FROM audit_log WHERE id=:id"), {"id": log_id})

    return {"success": True}
