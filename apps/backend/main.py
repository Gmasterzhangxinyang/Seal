import os

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"

import logging
import cv2
import numpy as np
from sqlalchemy import text
from vision.ocr import (
    extract_fields_with_positions,
    extract_fields_by_template,
)
from vision.qr_scanner import scan_qr
from vision.page_counter import check_page_completeness
from vision.classifier import classify_document
from validator.rules import DocumentValidator
from hardware.wearm import WeArmController
from hardware.base import compute_position_at_xy, load_calibration
from hardware.kinematics import compute_stamp_pwm
from database.audit import log_action
from database import review_queue as rq
from database.template import get_template_by_code
from database.connection import get_db
from config import PAPER_DETECTION_ENABLED

logger = logging.getLogger(__name__)

_PAPER_THRESHOLD = 0.3


def _has_paper(image_path: str) -> bool:
    img = cv2.imread(image_path)
    if img is None:
        return False
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    white_ratio = np.sum(gray > 180) / gray.size
    return white_ratio > _PAPER_THRESHOLD


class DocumentProcessor:
    def __init__(self):
        from vision.camera import SharedCamera

        self.camera = SharedCamera.get_instance()
        self.arm = WeArmController()
        self.validator = DocumentValidator()
        logger.info("DocumentProcessor 已初始化")

    def process(self, operator_id: str) -> dict:
        before_img = self.camera.capture_timestamped("before")
        logger.info(f"[{operator_id}] 已拍摄图片: {before_img}")

        if PAPER_DETECTION_ENABLED and not _has_paper(before_img):
            logger.info(f"[{operator_id}] 未检测到纸张，跳过盖章")
            return {"status": "rejected", "errors": ["未检测到纸张"], "warnings": []}

        # QR 扫描 → 识别文档类型
        qr_content, doc_type = scan_qr(before_img)
        logger.info(f"[{operator_id}] QR: {qr_content}, 类型: {doc_type}")

        # OCR 识别（带位置信息）
        fields, full_text, boxes = extract_fields_with_positions(before_img)
        logger.info(f"[{operator_id}] 识别字段: {fields}")

        # 自动分类（QR 未识别具体类型时）
        if doc_type == "general" or doc_type is None:
            classified_code, confidence = classify_document(full_text, fields)
            if classified_code:
                doc_type = classified_code
                logger.info(
                    f"[{operator_id}] 自动分类为: {doc_type} (置信度: {confidence:.2f})"
                )
            else:
                doc_type = "pending"
                logger.info(f"[{operator_id}] 无法自动分类，标记为 pending")

        # 确定模板后，用模板的 ocr_pattern 重新提取字段
        if doc_type != "pending":
            fields = extract_fields_by_template(full_text, doc_type)
            logger.info(f"[{operator_id}] 模板提取字段: {fields}")

        if doc_type == "pending":
            pending_msg = "无法自动识别文件类型，请管理员手动分类"
            queue_id = rq.add_to_queue(
                operator_id, "pending", fields, [pending_msg], before_img, full_text
            )
            log_action(
                operator_id,
                "pending",
                qr_content,
                fields,
                "PENDING_REVIEW",
                [pending_msg],
                before_img,
                before_img,
                ocr_text=full_text,
            )
            return {
                "status": "pending_review",
                "review_id": queue_id,
                "fields": fields,
                "errors": [],
                "warnings": [pending_msg],
            }

        # 多页完整性检测
        page_ok, page_msg = check_page_completeness(before_img)
        if not page_ok:
            log_action(
                operator_id,
                doc_type,
                qr_content,
                fields,
                "REJECTED",
                [page_msg],
                before_img,
                before_img,
                ocr_text=full_text,
            )
            return {
                "status": "rejected",
                "fields": fields,
                "errors": [page_msg],
                "warnings": [],
            }

        # 规则验证
        v_result = self.validator.validate(fields, full_text, doc_type)

        if not v_result.passed:
            logger.info(f"[{operator_id}] 拒绝: {v_result.hard_errors}")
            log_action(
                operator_id,
                doc_type,
                qr_content,
                fields,
                "REJECTED",
                v_result.hard_errors,
                before_img,
                before_img,
                ocr_text=full_text,
            )
            return {
                "status": "rejected",
                "fields": fields,
                "errors": v_result.hard_errors,
                "warnings": [],
            }

        if v_result.needs_review:
            logger.info(f"[{operator_id}] 推入复审: {v_result.soft_warnings}")
            queue_id = rq.add_to_queue(
                operator_id,
                doc_type,
                fields,
                v_result.soft_warnings,
                before_img,
                full_text,
            )
            log_action(
                operator_id,
                doc_type,
                qr_content,
                fields,
                "PENDING_REVIEW",
                v_result.soft_warnings,
                before_img,
                before_img,
                ocr_text=full_text,
            )
            return {
                "status": "pending_review",
                "review_id": queue_id,
                "fields": fields,
                "errors": [],
                "warnings": v_result.soft_warnings,
            }

        # 盖章
        logger.info(f"[{operator_id}] 验证通过，开始盖章")
        self._do_stamp(before_img, boxes, doc_type)

        after_img = self.camera.capture_timestamped("after")
        log_action(
            operator_id,
            doc_type,
            qr_content,
            fields,
            "APPROVED",
            [],
            before_img,
            after_img,
            ocr_text=full_text,
        )

        logger.info(f"[{operator_id}] 盖章完成")
        return {"status": "approved", "errors": [], "warnings": []}

    def process_review_stamping(self, review_id: int, operator_id: str) -> dict:
        """复审通过后的验证盖章流程"""
        import ast
        from vision.comparator import verify_document
        from vision.ocr import extract_fields_with_positions

        with get_db() as conn:
            row = (
                conn.execute(
                    text(
                        'SELECT * FROM review_queue WHERE id=:id AND status="approved"'
                    ),
                    {"id": review_id},
                )
                .mappings()
                .one_or_none()
            )

        if not row:
            return {"status": "error", "message": "记录不存在或未批准"}

        original_img = row["image_path"]
        original_fields = (
            ast.literal_eval(row["doc_fields"]) if row["doc_fields"] else {}
        )

        new_img = self.camera.capture_timestamped("review_verify")
        logger.info(f"[{operator_id}] 复审验证拍照: {new_img}")

        if PAPER_DETECTION_ENABLED and not _has_paper(new_img):
            return {"status": "rejected", "errors": ["未检测到纸张"], "warnings": []}

        new_fields, new_full_text, boxes = extract_fields_with_positions(new_img)

        passed, messages = verify_document(
            original_img, new_img, original_fields, new_fields
        )

        if not passed:
            logger.info(f"[{operator_id}] 复审验证失败: {messages}")
            log_action(
                operator_id,
                row["doc_type"] or "review",
                None,
                new_fields,
                "REJECTED",
                messages,
                new_img,
                new_img,
                ocr_text=new_full_text,
            )
            return {
                "status": "rejected",
                "errors": messages,
                "warnings": [],
            }

        logger.info(f"[{operator_id}] 复审验证通过，开始盖章")
        self._do_stamp(new_img, boxes, row["doc_type"])

        after_img = self.camera.capture_timestamped("after")
        log_action(
            operator_id,
            row["doc_type"] or "review",
            None,
            new_fields,
            "APPROVED",
            [],
            new_img,
            after_img,
            ocr_text=new_full_text,
        )
        rq.mark_stamped(review_id)

        logger.info(f"[{operator_id}] 复审盖章完成")
        return {"status": "approved", "errors": [], "warnings": []}

    def _do_stamp(
        self, image_path: str, boxes: list | None = None, doc_type: str | None = None
    ):
        """执行盖章"""
        # TODO: 恢复智能定位后取消注释下方代码
        # cal = load_calibration()
        # img = cv2.imread(image_path)
        # img_h, img_w = img.shape[:2] if img is not None else (0, 0)
        #
        # tpl = get_template_by_code(doc_type) if doc_type else None
        # requires_stamp = tpl.get("requires_stamp", 1) if tpl else 1
        # if not requires_stamp:
        #     logger.info(f"模板 {doc_type} 不需要盖章，跳过")
        #     return
        #
        # stamp_keywords = None
        # if tpl and tpl.get("stamp_keywords"):
        #     stamp_keywords = [
        #         k.strip() for k in tpl["stamp_keywords"].split(",") if k.strip()
        #     ]
        #
        # if boxes:
        #     from vision.ocr import find_stamp_target_pixel
        #     stamp_pos = find_stamp_target_pixel(boxes, keywords=stamp_keywords)
        #     if stamp_pos and cal:
        #         pwms = compute_stamp_pwm(stamp_pos[0], stamp_pos[1], img_w, img_h, cal)
        #         if pwms:
        #             logger.info(f"IK 盖章 PWM: {pwms}")
        #             self.arm.stamp_at(pwms)
        #             return
        #
        # if cal.get("corners") and boxes:
        #     from vision.ocr import find_stamp_target
        #     stamp_pos = find_stamp_target(boxes, keywords=stamp_keywords)
        #     if stamp_pos:
        #         logger.info(f"标定盖章位置 (归一化): x={stamp_pos[0]:.3f}, y={stamp_pos[1]:.3f}")
        #         pwms = compute_position_at_xy(stamp_pos[0], stamp_pos[1], cal)
        #         logger.info(f"标定盖章 PWM: {pwms}")
        #         self.arm.stamp_at(pwms)
        #         return
        #
        # if tpl and tpl.get("stamp_position"):
        #     try:
        #         parts = tpl["stamp_position"].split(",")
        #         nx, ny = float(parts[0]), float(parts[1])
        #         px, py = int(nx * img_w), int(ny * img_h)
        #         logger.info(f"模板预设盖章位置: ({nx:.2f},{ny:.2f}) → 像素({px},{py})")
        #         if cal:
        #             pwms = compute_stamp_pwm(px, py, img_w, img_h, cal)
        #             if pwms:
        #                 self.arm.stamp_at(pwms)
        #                 return
        #     except Exception as e:
        #         logger.warning(f"模板盖章位置解析失败: {e}")
        #
        # logger.warning("所有定位方案均失败，使用默认盖章序列")
        # self.arm.stamp_sequence()

        logger.info("[stamp] 使用固定盖章序列")
        self.arm.stamp_sequence()

    def shutdown(self):
        from vision.camera import SharedCamera

        SharedCamera.reset()
        self.arm.close()


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from database.models import init_db
    from database.seed import seed_demo_data, seed_default_templates

    init_db()
    seed_demo_data()
    seed_default_templates()
    print("数据库已初始化")
    print("演示账号: admin / admin123")
    print()

    from api.main import start

    start()
