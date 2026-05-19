import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_session, require_role
from database.connection import get_db
from utils.qr_sign import create_leave_qr_payload, qr_payload_to_string

router = APIRouter(prefix="/leave-applications", tags=["leave-applications"])
logger = logging.getLogger(__name__)


class CreateLeaveApplicationRequest(BaseModel):
    student_id: str
    student_name: str
    dept: str | None = None
    leave_type: str
    start_date: str
    end_date: str
    reason: str


def _generate_application_id() -> str:
    """生成唯一申请编号，格式: LEAVE-YYYYMMDD-NNNN"""
    today = datetime.now().strftime("%Y%m%d")
    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT COUNT(*) as cnt FROM leave_applications "
                    "WHERE application_id LIKE :prefix"
                ),
                {"prefix": f"LEAVE-{today}-%"},
            )
            .mappings()
            .one_or_none()
        )
        seq = (row["cnt"] if row else 0) + 1
    return f"LEAVE-{today}-{seq:04d}"


@router.post("")
def create_leave_application(
    body: CreateLeaveApplicationRequest, session: dict = Depends(get_session)
):
    """创建请假申请，自动调用 Dify AI 审批"""
    application_id = _generate_application_id()
    now = datetime.now().isoformat()
    qr_payload = create_leave_qr_payload(application_id, body.student_id)
    qr_content = qr_payload_to_string(qr_payload)

    # 调用 Dify AI 审批
    from utils.dify_client import call_dify_approval

    ai_result = call_dify_approval(body.start_date, body.end_date, body.reason)
    approval_result = ai_result.get("approval_result")
    ai_comment = ai_result.get("comment", "")

    # 根据 AI 审批结果设置状态
    if approval_result == "Approved":
        status = "APPROVED"
        approved_by = "AI_AUTO"
        approved_at = now
    elif approval_result == "Rejected":
        status = "REJECTED"
        approved_by = "AI_AUTO"
        approved_at = now
    else:
        # Pending Review 或无法获取结果时保持 SUBMITTED
        status = "SUBMITTED"
        approved_by = None
        approved_at = None

    with get_db() as conn:
        from sqlalchemy import text

        conn.execute(
            text("""
            INSERT INTO leave_applications
            (application_id, student_id, student_name, dept, leave_type,
             start_date, end_date, reason, status, qr_content, created_by,
             created_at, updated_at, approved_by, approved_at, ai_comment)
            VALUES
            (:application_id, :student_id, :student_name, :dept, :leave_type,
             :start_date, :end_date, :reason, :status, :qr_content, :created_by,
             :created_at, :updated_at, :approved_by, :approved_at, :ai_comment)
        """),
            {
                "application_id": application_id,
                "student_id": body.student_id,
                "student_name": body.student_name,
                "dept": body.dept,
                "leave_type": body.leave_type,
                "start_date": body.start_date,
                "end_date": body.end_date,
                "reason": body.reason,
                "status": status,
                "qr_content": qr_content,
                "created_by": session["username"],
                "created_at": now,
                "updated_at": now,
                "approved_by": approved_by,
                "approved_at": approved_at,
                "ai_comment": ai_comment,
            },
        )

    logger.info(f"[leave] 创建申请 {application_id} by {session['username']}, AI审批: {approval_result}")
    return {
        "application_id": application_id,
        "status": status,
        "qr_content": qr_content,
        "ai_comment": ai_comment,
        "approval_result": approval_result,
    }


@router.get("")
def list_leave_applications(
    status: str | None = None, session: dict = Depends(get_session)
):
    """获取请假申请列表，支持按状态筛选；operator 只能查看自己创建的申请"""
    with get_db() as conn:
        from sqlalchemy import text

        role = session["role"]
        if role in ("admin", "reviewer"):
            if status:
                rows = (
                    conn.execute(
                        text(
                            "SELECT * FROM leave_applications WHERE status=:status ORDER BY created_at DESC"
                        ),
                        {"status": status},
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (
                    conn.execute(
                        text("SELECT * FROM leave_applications ORDER BY created_at DESC")
                    )
                    .mappings()
                    .all()
                )
        else:
            username = session["username"]
            if status:
                rows = (
                    conn.execute(
                        text(
                            "SELECT * FROM leave_applications WHERE status=:status AND created_by=:created_by ORDER BY created_at DESC"
                        ),
                        {"status": status, "created_by": username},
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (
                    conn.execute(
                        text(
                            "SELECT * FROM leave_applications WHERE created_by=:created_by ORDER BY created_at DESC"
                        ),
                        {"created_by": username},
                    )
                    .mappings()
                    .all()
                )
    return list(rows)


@router.get("/{application_id}")
def get_leave_application(application_id: str, session: dict = Depends(get_session)):
    """获取请假申请详情"""
    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT * FROM leave_applications WHERE application_id=:application_id"
                ),
                {"application_id": application_id},
            )
            .mappings()
            .one_or_none()
        )
    if not row:
        raise HTTPException(404, "申请不存在")
    return dict(row)


@router.post("/{application_id}/approve")
def approve_leave_application(
    application_id: str, session: dict = Depends(require_role("admin", "reviewer"))
):
    """审批通过请假申请"""
    now = datetime.now().isoformat()
    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT status FROM leave_applications WHERE application_id=:application_id"
                ),
                {"application_id": application_id},
            )
            .mappings()
            .one_or_none()
        )

    if not row:
        raise HTTPException(404, "申请不存在")
    if row["status"] not in ("SUBMITTED",):
        raise HTTPException(400, f"当前状态不允许审批: {row['status']}")

    with get_db() as conn:
        from sqlalchemy import text

        conn.execute(
            text("""
            UPDATE leave_applications
            SET status='APPROVED', approved_by=:approved_by, approved_at=:approved_at, updated_at=:updated_at
            WHERE application_id=:application_id
        """),
            {
                "application_id": application_id,
                "approved_by": session["username"],
                "approved_at": now,
                "updated_at": now,
            },
        )

    logger.info(f"[leave] 审批通过 {application_id} by {session['username']}")
    return {"status": "APPROVED"}


@router.post("/{application_id}/reject")
def reject_leave_application(
    application_id: str, session: dict = Depends(require_role("admin", "reviewer"))
):
    """拒绝请假申请"""
    now = datetime.now().isoformat()
    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT status FROM leave_applications WHERE application_id=:application_id"
                ),
                {"application_id": application_id},
            )
            .mappings()
            .one_or_none()
        )

    if not row:
        raise HTTPException(404, "申请不存在")
    if row["status"] != "SUBMITTED":
        raise HTTPException(400, f"当前状态不允许拒绝: {row['status']}")

    with get_db() as conn:
        from sqlalchemy import text

        conn.execute(
            text("""
            UPDATE leave_applications
            SET status='REJECTED', updated_at=:updated_at
            WHERE application_id=:application_id
        """),
            {
                "application_id": application_id,
                "updated_at": now,
            },
        )

    logger.info(f"[leave] 拒绝申请 {application_id} by {session['username']}")
    return {"status": "REJECTED"}


@router.get("/{application_id}/qr")
def get_leave_application_qr(application_id: str, session: dict = Depends(get_session)):
    """获取请假申请的二维码内容"""
    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT qr_content, status FROM leave_applications WHERE application_id=:application_id"
                ),
                {"application_id": application_id},
            )
            .mappings()
            .one_or_none()
        )

    if not row:
        raise HTTPException(404, "申请不存在")
    return {
        "qr_content": row["qr_content"],
        "status": row["status"],
    }


@router.get("/{application_id}/qr/image")
def get_leave_application_qr_image(
    application_id: str, session: dict = Depends(get_session)
):
    """生成请假申请二维码图片（PNG）"""
    import qrcode
    import io
    from fastapi.responses import StreamingResponse

    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text(
                    "SELECT qr_content FROM leave_applications WHERE application_id=:application_id"
                ),
                {"application_id": application_id},
            )
            .mappings()
            .one_or_none()
        )

    if not row or not row["qr_content"]:
        raise HTTPException(404, "申请不存在或无二维码内容")

    img = qrcode.make(row["qr_content"])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/{application_id}/download")
def download_leave_application(
    application_id: str, session: dict = Depends(get_session)
):
    """生成并下载请假条 PDF"""
    import io
    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Image,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from fastapi.responses import StreamingResponse

    with get_db() as conn:
        from sqlalchemy import text

        row = (
            conn.execute(
                text("SELECT * FROM leave_applications WHERE application_id=:id"),
                {"id": application_id},
            )
            .mappings()
            .one_or_none()
        )

    if not row:
        raise HTTPException(404, "申请不存在")

    app = dict(row)

    qr_img = qrcode.make(app["qr_content"] or application_id)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("NotoSansSC", "C:/Windows/Fonts/NotoSansSC-VF.ttf"))

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=22,
        spaceAfter=10,
        fontName="NotoSansSC",
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=10, fontName="NotoSansSC"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=12, fontName="NotoSansSC"
    )

    story = [Paragraph("请 假 条", title_style), Spacer(1, 8 * mm)]

    fields_para = [
        [
            Paragraph("<b>申请编号</b>", small_style),
            Paragraph(app["application_id"], body_style),
        ],
        [
            Paragraph("<b>学生姓名</b>", small_style),
            Paragraph(app["student_name"], body_style),
        ],
        [
            Paragraph("<b>学　　号</b>", small_style),
            Paragraph(app["student_id"], body_style),
        ],
        [
            Paragraph("<b>院　　系</b>", small_style),
            Paragraph(app["dept"] or "-", body_style),
        ],
        [
            Paragraph("<b>请假类型</b>", small_style),
            Paragraph(app["leave_type"], body_style),
        ],
        [
            Paragraph("<b>开始日期</b>", small_style),
            Paragraph(app["start_date"], body_style),
        ],
        [
            Paragraph("<b>结束日期</b>", small_style),
            Paragraph(app["end_date"], body_style),
        ],
        [
            Paragraph("<b>请假原因</b>", small_style),
            Paragraph(app["reason"], body_style),
        ],
    ]
    t = Table(fields_para, colWidths=[35 * mm, 120 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10 * mm))

    if app.get("approved_by"):
        story.append(
            Paragraph(
                f"<b>审批人：</b>{app['approved_by']}　　<b>审批时间：</b>{app.get('approved_at', '-')}",
                small_style,
            )
        )
        story.append(Spacer(1, 5 * mm))

    qr_buf.seek(0)
    qr_img_obj = Image(qr_buf, width=35 * mm, height=35 * mm)
    qr_para = Paragraph(
        "<b>二维码</b><br/><font size=8>（审批通过后有效）</font>", small_style
    )
    qr_table = Table([[qr_img_obj, qr_para]], colWidths=[40 * mm, 40 * mm])
    qr_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(qr_table)

    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"[leave] PDF build error: {e}", exc_info=True)
        raise

    pdf_buf.seek(0)

    filename = f"leave_{application_id}.pdf"
    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
