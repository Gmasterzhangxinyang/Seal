from datetime import datetime
from sqlalchemy import text
from database.connection import get_db


def log_action(
    operator_id: str,
    doc_type: str,
    qr_content: str | None,
    doc_fields: dict,
    result: str,
    errors: list,
    before_img: str,
    after_img: str,
    dms_doc_id: str | None = None,
    ocr_text: str = '',
) -> int:
    """写入审计记录，返回新记录 id。"""
    with get_db() as conn:
        r = conn.execute(text(
            '''INSERT INTO audit_log
               (timestamp, operator_id, doc_type, qr_content, doc_fields,
                ocr_text, result, errors, before_img, after_img, dms_doc_id)
               VALUES (:ts, :oid, :dt, :qr, :df, :ot, :res, :err, :bi, :ai, :dms)'''
        ), {
            'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'oid': operator_id, 'dt': doc_type, 'qr': qr_content,
            'df': str(doc_fields), 'ot': ocr_text, 'res': result,
            'err': str(errors), 'bi': before_img, 'ai': after_img,
            'dms': dms_doc_id,
        })
        row_id = r.lastrowid
    assert row_id is not None
    return row_id


def get_recent_logs(limit: int = 50) -> list:
    with get_db() as conn:
        rows = conn.execute(text(
            'SELECT * FROM audit_log ORDER BY id DESC LIMIT :limit'
        ), {'limit': limit}).fetchall()
    return rows


def get_log_by_id(log_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT * FROM audit_log WHERE id = :id'
        ), {'id': log_id}).mappings().one_or_none()
    return dict(row) if row else None
