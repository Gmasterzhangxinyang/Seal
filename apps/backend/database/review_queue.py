from datetime import datetime
from sqlalchemy import text
from database.connection import get_db


def add_to_queue(
    operator_id: str,
    doc_type: str,
    doc_fields: dict,
    warnings: list,
    image_path: str,
    ocr_text: str = "",
) -> int:
    """将需要人工复审的文件推入队列，返回队列记录 id。"""
    with get_db() as conn:
        r = conn.execute(
            text(
                """INSERT INTO review_queue
               (timestamp, operator_id, doc_type, doc_fields, ocr_text,
                warnings, image_path, status)
               VALUES (:ts, :oid, :dt, :df, :ot, :w, :img, 'pending')"""
            ),
            {
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "oid": operator_id,
                "dt": doc_type,
                "df": str(doc_fields),
                "ot": ocr_text,
                "w": str(warnings),
                "img": image_path,
            },
        )
        row_id = r.lastrowid
    assert row_id is not None

    # Feishu notification to Wene
    try:
        from services.notify import notify_review_queue
        notify_review_queue(
            operator_id=operator_id,
            doc_type=doc_type,
            reason="自动核验不确定，需人工复审",
            warnings=warnings,
        )
    except Exception:
        pass  # never let notification failure break the main flow

    return row_id


def get_pending() -> list:
    with get_db() as conn:
        rows = conn.execute(
            text("SELECT * FROM review_queue WHERE status='pending' ORDER BY id DESC")
        ).fetchall()
    return rows


def resolve(review_id: int, reviewer_id: str, decision: str):
    with get_db() as conn:
        conn.execute(
            text(
                """UPDATE review_queue
               SET status=:decision, reviewer_id=:rid,
                   resolved_at=:ts, decision=:decision2
               WHERE id=:id"""
            ),
            {
                "decision": decision,
                "rid": reviewer_id,
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "decision2": decision,
                "id": review_id,
            },
        )


def get_all(limit: int = 50) -> list:
    with get_db() as conn:
        rows = conn.execute(
            text("SELECT * FROM review_queue ORDER BY id DESC LIMIT :limit"),
            {"limit": limit},
        ).fetchall()
    return rows


def get_approved_for_stamping() -> list:
    """获取已批准但尚未盖章的复审记录。"""
    with get_db() as conn:
        rows = conn.execute(
            text(
                "SELECT * FROM review_queue "
                "WHERE status='approved' AND (stamped=0 OR stamped IS NULL) "
                "ORDER BY id DESC"
            )
        ).fetchall()
    return rows


def mark_stamped(review_id: int):
    with get_db() as conn:
        conn.execute(
            text("UPDATE review_queue SET stamped=1 WHERE id=:id"), {"id": review_id}
        )
