"""请假条核验验证器 — 实现 PASS / REVIEW / REJECT 决策"""

import logging

from utils.qr_sign import verify_qr_payload, qr_string_to_payload
from database.connection import get_db

logger = logging.getLogger(__name__)

# 风险评分规则
_SCORE_HARD_FAIL = 70
_SCORE_GENERAL_FAIL = 40
_SCORE_WARNING_LOW = 10
_SCORE_WARNING_MEDIUM = 25

# OCR 置信度阈值
_CONFIDENCE_HIGH = 0.85
_CONFIDENCE_MEDIUM = 0.65


class LeaveVerificationResult:
    """请假条验证结果"""

    def __init__(self, decision: str, risk_score: int = 0):
        self.decision = decision  # PASS / REVIEW / REJECT
        self.risk_score = risk_score
        self.checks: list[dict] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.application_record: dict | None = None

    def add_check(self, name: str, result: str, score: int, reason: str):
        self.checks.append(
            {
                "name": name,
                "result": result,
                "score": score,
                "reason": reason,
            }
        )

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "risk_score": self.risk_score,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def verify_leave_application(
    qr_content: str,
    ocr_fields: dict,
    ocr_confidence: float = 1.0,
) -> LeaveVerificationResult:
    """请假条核验主函数

    Args:
        qr_content: 二维码原始字符串
        ocr_fields: OCR 抽取的字段 dict
        ocr_confidence: OCR 置信度 0.0~1.0

    Returns:
        LeaveVerificationResult 包含 decision, risk_score, checks, errors, warnings
    """
    result = LeaveVerificationResult("REJECTED", 0)

    # ── 检查1：二维码签名验证 ──────────────────────────────────────────────
    payload = qr_string_to_payload(qr_content)
    if not payload:
        result.add_check(
            "qr_signature_check", "fail", _SCORE_HARD_FAIL, "二维码内容解析失败"
        )
        result.errors.append("二维码内容无效")
        return _finalize(result)

    if not verify_qr_payload(payload):
        result.add_check(
            "qr_signature_check",
            "fail",
            _SCORE_HARD_FAIL,
            "二维码签名验证失败，文档可能被篡改",
        )
        result.errors.append("二维码验证失败")
        return _finalize(result)

    result.add_check("qr_signature_check", "pass", 0, "二维码签名验证通过")
    application_id = payload.get("application_id", "")
    qr_student_id = payload.get("student_id", "")

    # ── 检查2：申请记录存在性 ─────────────────────────────────────────────
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
        result.add_check(
            "application_exists_check",
            "fail",
            _SCORE_HARD_FAIL,
            f"申请记录不存在: {application_id}",
        )
        result.errors.append("申请不存在")
        return _finalize(result, qr_student_id)

    result.application_record = dict(row)
    result.add_check("application_exists_check", "pass", 0, "申请记录存在")

    app = result.application_record

    # ── 检查3：申请状态验证 ───────────────────────────────────────────────
    status = app.get("status", "")
    if status != "APPROVED":
        reason_map = {
            "SUBMITTED": "申请尚未审批",
            "REJECTED": "申请已被拒绝",
            "STAMPED": "申请已完成盖章",
            "CANCELLED": "申请已取消",
            "EXPIRED": "申请已过期",
        }
        reason = reason_map.get(status, f"申请状态异常: {status}")
        result.add_check("application_status_check", "fail", _SCORE_HARD_FAIL, reason)
        result.errors.append(reason)
        return _finalize(result, qr_student_id)

    result.add_check(
        "application_status_check", "pass", 0, "申请已审批通过 (APPROVED)"
    )

    # ── 检查4：重复盖章检测 ────────────────────────────────────────────────
    if app.get("stamped_at"):
        result.add_check(
            "duplicate_stamp_check",
            "fail",
            _SCORE_HARD_FAIL,
            "该申请已盖章，禁止重复盖章",
        )
        result.errors.append("该申请已盖章")
        return _finalize(result, qr_student_id)

    result.add_check("duplicate_stamp_check", "pass", 0, "该申请尚未盖章")

    # ── 检查5：学号一致性验证 ───────────────────────────────────────────────
    ocr_student_id = ocr_fields.get("student_id", "")
    if ocr_student_id and ocr_student_id != qr_student_id:
        result.add_check(
            "student_id_match_check",
            "fail",
            _SCORE_HARD_FAIL,
            "OCR 学号与申请记录不一致",
        )
        result.errors.append("学号不一致")
        return _finalize(result, qr_student_id)

    result.add_check("student_id_match_check", "pass", 0, "学号与申请记录一致")

    # ── 检查6：姓名一致性验证 ───────────────────────────────────────────────
    app_name = app.get("student_name", "")
    ocr_name = ocr_fields.get("student_name", "")
    if ocr_name:
        if not _name_similar(app_name, ocr_name):
            result.risk_score += _SCORE_GENERAL_FAIL
            result.add_check(
                "student_name_match_check",
                "fail",
                _SCORE_GENERAL_FAIL,
                "姓名与申请记录不一致",
            )
            result.errors.append("姓名不一致")
        else:
            result.add_check(
                "student_name_match_check", "pass", 0, "姓名与申请记录一致"
            )

    # ── 检查7：请假类型一致性 ──────────────────────────────────────────────
    app_type = app.get("leave_type", "")
    ocr_type = ocr_fields.get("leave_type", "")
    if ocr_type and app_type:
        if ocr_type != app_type:
            result.risk_score += _SCORE_GENERAL_FAIL
            result.add_check(
                "leave_type_match_check",
                "fail",
                _SCORE_GENERAL_FAIL,
                "请假类型与申请记录不一致",
            )
            result.errors.append("请假类型不一致")
        else:
            result.add_check(
                "leave_type_match_check", "pass", 0, "请假类型与申请记录一致"
            )

    # ── 检查8：日期一致性 ───────────────────────────────────────────────────
    app_start = app.get("start_date", "")
    app_end = app.get("end_date", "")
    ocr_start = ocr_fields.get("start_date", "")
    ocr_end = ocr_fields.get("end_date", "")

    date_ok = True
    if ocr_start and app_start and ocr_start != app_start:
        result.risk_score += _SCORE_GENERAL_FAIL
        result.add_check(
            "start_date_match_check",
            "fail",
            _SCORE_GENERAL_FAIL,
            f"开始日期不一致: OCR={ocr_start}, 申请={app_start}",
        )
        result.errors.append("开始日期不一致")
        date_ok = False

    if ocr_end and app_end and ocr_end != app_end:
        result.risk_score += _SCORE_GENERAL_FAIL
        result.add_check(
            "end_date_match_check",
            "fail",
            _SCORE_GENERAL_FAIL,
            f"结束日期不一致: OCR={ocr_end}, 申请={app_end}",
        )
        result.errors.append("结束日期不一致")
        date_ok = False

    if date_ok and (ocr_start or ocr_end):
        result.add_check("date_match_check", "pass", 0, "日期与申请记录一致")

    # ── 检查9：原因字段验证 ────────────────────────────────────────────────
    ocr_reason = ocr_fields.get("reason", "")
    if not ocr_reason:
        result.risk_score += _SCORE_WARNING_MEDIUM
        result.add_check(
            "reason_check", "warn", _SCORE_WARNING_MEDIUM, "请假原因字段缺失"
        )
        result.warnings.append("请假原因字段缺失")
    else:
        result.add_check("reason_check", "pass", 0, "请假原因字段存在")

    # ── 检查10：OCR 置信度验证 ─────────────────────────────────────────────
    if ocr_confidence >= _CONFIDENCE_HIGH:
        result.add_check(
            "ocr_confidence_check",
            "pass",
            0,
            f"OCR 置信度满足自动通过阈值 ({ocr_confidence:.2f} >= {_CONFIDENCE_HIGH})",
        )
    elif ocr_confidence >= _CONFIDENCE_MEDIUM:
        result.risk_score += _SCORE_WARNING_MEDIUM
        result.add_check(
            "ocr_confidence_check",
            "warn",
            _SCORE_WARNING_MEDIUM,
            f"OCR 置信度中等 ({ocr_confidence:.2f}), 进入人工复审",
        )
        result.warnings.append(f"OCR 置信度中等 ({ocr_confidence:.2f})")
    else:
        result.risk_score += _SCORE_GENERAL_FAIL
        result.add_check(
            "ocr_confidence_check",
            "fail",
            _SCORE_GENERAL_FAIL,
            f"OCR 置信度过低 ({ocr_confidence:.2f} < {_CONFIDENCE_MEDIUM})",
        )
        result.errors.append("OCR 识别不清晰")

    # ── 最终决策 ───────────────────────────────────────────────────────────
    if result.errors:
        result.decision = "REJECTED"
    elif result.risk_score >= 40:
        result.decision = "REVIEW"
    elif result.risk_score >= 0:
        result.decision = "PASS"

    return result


def _finalize(
    result: LeaveVerificationResult, qr_student_id: str = ""
) -> LeaveVerificationResult:
    """在早期失败时快速返回 REJECT"""
    if result.errors:
        result.decision = "REJECTED"
    elif result.warnings and result.risk_score >= 40:
        result.decision = "REVIEW"
    elif result.warnings:
        result.decision = "REVIEW"
    else:
        result.decision = "REJECTED"
    return result


def _name_similar(name1: str, name2: str) -> bool:
    """宽松的姓名比对，允许空格、大小写等轻微差异"""
    import re

    n1 = re.sub(r"\s+", "", name1.lower())
    n2 = re.sub(r"\s+", "", name2.lower())
    if n1 == n2:
        return True
    # 单字姓名完全匹配
    if len(n1) <= 3 and len(n2) <= 3 and n1 in n2 or n2 in n1:
        return True
    return False
