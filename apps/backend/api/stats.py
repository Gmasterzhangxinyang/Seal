from fastapi import APIRouter, Depends
from sqlalchemy import text

from api.deps import get_session
from database.connection import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/data")
def stats_data(session: dict = Depends(get_session)):
    with get_db() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM audit_log")).scalar()
        approved = conn.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE result='APPROVED'")
        ).scalar()
        rejected = conn.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE result='REJECTED'")
        ).scalar()
        pending_review = conn.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE result='PENDING_REVIEW'")
        ).scalar()
        pending_queue = conn.execute(
            text("SELECT COUNT(*) FROM review_queue WHERE status='pending'")
        ).scalar()

        type_rows = conn.execute(
            text("SELECT doc_type, COUNT(*) FROM audit_log GROUP BY doc_type")
        ).fetchall()
        result_rows = conn.execute(
            text("SELECT result, COUNT(*) FROM audit_log GROUP BY result")
        ).fetchall()
        daily_rows = conn.execute(
            text("""
            SELECT DATE(timestamp) as day, result, COUNT(*)
            FROM audit_log WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY day, result ORDER BY day
        """)
        ).fetchall()
        recent = conn.execute(
            text("SELECT * FROM audit_log ORDER BY id DESC LIMIT 10")
        ).fetchall()

    type_distribution = {c: n for c, n in type_rows}

    result_distribution = {r: n for r, n in result_rows}

    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "pending_review": pending_review,
        "pending_queue": pending_queue,
        "type_distribution": type_distribution,
        "result_distribution": result_distribution,
        "daily_trend": [[r[0], r[1], r[2]] for r in daily_rows],
        "recent": [
            [r[0], r[1], r[2], r[3], r[6]] for r in recent
        ],
    }
