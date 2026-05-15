import logging
import secrets
import json
import base64
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import get_session
from database.connection import get_db


def _gpt4v_extract(image_path: str) -> dict:
    """使用 GLM-4V 识别图片中的请假条字段"""
    from openai import OpenAI
    from config import VLM_API_KEY, VLM_BASE_URL, VLM_MODEL

    client = OpenAI(
        api_key=VLM_API_KEY,
        base_url=VLM_BASE_URL,
    )

    with open(image_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")

    prompt = """你是一请假条识别助手。请仔细看这张请假条图片，提取以下字段信息，以JSON格式返回：
- application_id: 申请编号（如有）
- student_name: 学生姓名
- student_id: 学号
- dept: 院系（可有可无）
- leave_type: 请假类型（事假/病假/其他）
- start_date: 开始日期（格式YYYY-MM-DD）
- end_date: 结束日期（格式YYYY-MM-DD）
- reason: 请假原因

要求：
1. 只返回JSON，不要有其他文字
2. 日期如果不是标准格式请转换为 YYYY-MM-DD
3. 如果某个字段完全无法识别，设为 null
4. 识别要严格准确，特别注意学号和姓名的对应关系"""
    try:
        response = client.chat.completions.create(
            model=VLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = response.choices[0].message.content.strip()
        if "{" in text and "}" in text:
            json_str = text[text.index("{") : text.rindex("}") + 1]
            return json.loads(json_str)
        else:
            logging.warning(f"[glm4v] 返回不是JSON格式: {text}")
            return {}
    except Exception as e:
        logging.error(f"[glm4v] GLM-4V 调用失败: {e}")
        return {}


router = APIRouter(tags=["stamp"])

_processor = None


def get_processor():
    global _processor
    if _processor is None:
        from main import DocumentProcessor

        _processor = DocumentProcessor()
    return _processor


@router.post("/stamp")
def stamp(session: dict = Depends(get_session)):
    try:
        logging.info("[stamp] 开始处理，用户: %s", session["username"])
        result = get_processor().process(session["username"])
        return result
    except Exception as e:
        logging.exception("[stamp] 处理文件时出错")
        raise HTTPException(500, str(e))


@router.post("/stamp/leave")
def stamp_leave(session: dict = Depends(get_session)):
    """扫描请假条并核验盖章（SSE 流式）"""
    from vision.camera import SharedCamera
    from vision.qr_scanner import scan_qr
    from validator.leave_validator import verify_leave_application
    from database.audit import log_action
    from config import SIMULATION_MODE

    operator_id = session["username"]

    def event_stream():
        yield _sse("log", "开始处理请假条盖章...")
        try:
            # 1. 拍照
            yield _sse("log", "正在拍照...")
            camera = SharedCamera.get_instance()
            before_img = camera.capture_timestamped("leave_before")
            yield _sse("log", f"拍照完成: {before_img}")

            # 2. 二维码扫描
            yield _sse("log", "正在扫描二维码...")
            qr_content, doc_type = scan_qr(before_img)
            if not qr_content:
                yield _sse("result", json.dumps({
                    "success": False, "decision": "REJECT", "risk_score": 70,
                    "errors": ["未扫描到二维码"], "checks": [], "warnings": [],
                }))
                return

            yield _sse("log", f"二维码识别成功: {qr_content[:50]}...")

            # 3. 二维码解析
            yield _sse("log", "正在解析二维码内容...")
            try:
                qr_data = json.loads(qr_content)
            except Exception:
                yield _sse("result", json.dumps({
                    "success": False, "decision": "REJECT", "risk_score": 70,
                    "errors": ["二维码内容解析失败"], "checks": [], "warnings": [],
                }))
                return

            if "application_id" not in qr_data:
                yield _sse("result", json.dumps({
                    "success": False, "decision": "REJECT", "risk_score": 70,
                    "errors": ["二维码不是请假条二维码"], "checks": [], "warnings": [],
                }))
                return

            application_id = qr_data.get("application_id", "")
            yield _sse("log", f"申请编号: {application_id}")

            # 4. OCR 识别（GLM-4V）
            yield _sse("log", "正在调用 GLM-4V 识别请假条内容（可能需要几秒）...")
            extracted_fields = _gpt4v_extract(before_img)
            if not extracted_fields:
                yield _sse("result", json.dumps({
                    "success": False, "decision": "REJECT", "risk_score": 70,
                    "errors": ["视觉模型识别失败"], "checks": [], "warnings": [],
                }))
                return

            fields_summary = ", ".join(
                f"{k}={v}" for k, v in extracted_fields.items() if v
            )
            yield _sse("log", f"识别完成: {fields_summary}")

            ocr_confidence = 0.95 if len(extracted_fields) >= 4 else 0.75
            full_text = str(extracted_fields)


            # 5. 核验
            yield _sse("log", "正在核验请假信息...")
            verification_result = verify_leave_application(
                qr_content, extracted_fields, ocr_confidence
            )
            vresult_dict = verification_result.to_dict()
            yield _sse("log", f"核验结果: {vresult_dict['decision']}")

            # 6. 创建 StampTask
            task_id = (
                f"STAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
            )
            now = datetime.now().isoformat()

            with get_db() as conn:
                from sqlalchemy import text

                conn.execute(
                    text("""
                    INSERT INTO stamp_tasks
                    (task_id, application_id, operator_id, doc_type, status, decision,
                     risk_score, before_img, qr_content, extracted_fields,
                     verification_result, created_at, updated_at)
                    VALUES
                    (:task_id, :application_id, :operator_id, 'leave', 'CREATED',
                     :decision, :risk_score, :before_img, :qr_content,
                     :extracted_fields, :verification_result, :created_at, :updated_at)
                """),
                    {
                        "task_id": task_id,
                        "application_id": application_id,
                        "operator_id": operator_id,
                        "decision": vresult_dict["decision"],
                        "risk_score": vresult_dict["risk_score"],
                        "before_img": before_img,
                        "qr_content": qr_content,
                        "extracted_fields": json.dumps(
                            extracted_fields, ensure_ascii=False
                        ),
                        "verification_result": json.dumps(vresult_dict, ensure_ascii=False),
                        "created_at": now,
                        "updated_at": now,
                    },
                )

                for check in vresult_dict.get("checks", []):
                    conn.execute(
                        text("""
                        INSERT INTO verification_results
                        (task_id, check_name, result, score, reason, created_at)
                        VALUES (:task_id, :check_name, :result, :score, :reason, :created_at)
                    """),
                        {
                            "task_id": task_id,
                            "check_name": check["name"],
                            "result": check["result"],
                            "score": check["score"],
                            "reason": check["reason"],
                            "created_at": now,
                        },
                    )

            # 7. 决策处理
            decision = vresult_dict["decision"]
            after_img = None

            if decision == "PASS":
                yield _sse("log", "核验通过，准备盖章...")
                pre_stamp_img = camera.capture_timestamped("leave_pre_stamp")
                if _paper_moved(before_img, pre_stamp_img):
                    decision = "REVIEW"
                    vresult_dict["decision"] = "REVIEW"
                    vresult_dict["warnings"].append(
                        "盖章前检测到纸张位置移动，进入人工复审"
                    )
                    yield _sse("log", "检测到纸张移动，转为人工复审")
                else:
                    if not SIMULATION_MODE:
                        yield _sse("log", "正在执行机械臂盖章...")
                        _do_leave_stamp(before_img)
                        yield _sse("log", "机械臂盖章完成")
                    else:
                        yield _sse("log", "仿真模式，跳过机械臂")
                    after_img = camera.capture_timestamped("leave_after")
                    yield _sse("log", "盖章后拍照完成")
                    _update_stamp_task(task_id, "STAMPED", "PASS", before_img, after_img)
                    _mark_leave_stamped(application_id, operator_id)

            elif decision == "REVIEW":
                yield _sse("log", "进入人工复审队列...")
                with get_db() as conn:
                    conn.execute(
                        text("""
                        INSERT INTO review_queue
                        (timestamp, operator_id, doc_type, doc_fields, ocr_text, warnings, image_path, status)
                        VALUES (:timestamp, :operator_id, 'leave', :doc_fields, :ocr_text, :warnings, :image_path, 'pending')
                    """),
                        {
                            "timestamp": now,
                            "operator_id": operator_id,
                            "doc_fields": json.dumps(extracted_fields, ensure_ascii=False),
                            "ocr_text": full_text,
                            "warnings": json.dumps(
                                vresult_dict.get("warnings", []), ensure_ascii=False
                            ),
                            "image_path": before_img,
                        },
                    )
                _update_stamp_task(task_id, "REVIEW", decision, before_img, None)

            elif decision == "REJECT":
                yield _sse("log", "核验未通过，拒绝盖章")
                _update_stamp_task(task_id, "REJECT", decision, before_img, None)

            # 8. 审计日志
            log_action(
                operator_id=operator_id,
                doc_type="leave",
                qr_content=qr_content,
                doc_fields=extracted_fields,
                result=decision,
                errors=vresult_dict.get("errors", []),
                before_img=before_img,
                after_img=after_img,
                ocr_text=full_text,
            )

            yield _sse("log", "处理完成")
            yield _sse("result", json.dumps({
                "success": decision in ("PASS", "REVIEW"),
                "task_id": task_id,
                "application_id": application_id,
                "decision": decision,
                "risk_score": vresult_dict["risk_score"],
                "checks": vresult_dict["checks"],
                "errors": vresult_dict["errors"],
                "warnings": vresult_dict["warnings"],
                "before_img": before_img,
                "after_img": after_img,
            }))

        except Exception as e:
            logging.exception("[stamp/leave] 处理时出错")
            yield _sse("log", f"处理出错: {e}")
            yield _sse("result", json.dumps({
                "success": False, "decision": "REJECT", "risk_score": 70,
                "errors": [str(e)], "checks": [], "warnings": [],
            }))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/review/{review_id}/stamp")
def review_stamp(review_id: int, session: dict = Depends(get_session)):
    try:
        result = get_processor().process_review_stamping(review_id, session["username"])
        return result
    except Exception as e:
        logging.exception("复审盖章失败")
        raise HTTPException(500, str(e))


# ─── 辅助函数 ─────────────────────────────────────────────────────────────────


def _ocr_with_boxes(image_path: str):
    """OCR 识别，返回 (fields, full_text, boxes)"""
    from vision.ocr import extract_fields_with_positions

    try:
        fields, full_text, boxes = extract_fields_with_positions(image_path)
    except Exception:
        from vision.ocr import extract_fields

        fields, full_text = extract_fields(image_path)
        boxes = []
    return fields, full_text, boxes


def _estimate_ocr_confidence(fields: dict, full_text: str) -> float:
    """粗略估计 OCR 置信度"""
    if not full_text:
        return 0.3
    # 有足够字段且文本长度足够，认为置信度较高
    filled = sum(1 for v in fields.values() if v)
    if filled >= 4 and len(full_text) > 50:
        return 0.9
    elif filled >= 2:
        return 0.7
    return 0.5


def _paper_moved(img1_path: str, img2_path: str, threshold: float = 0.7) -> bool:
    """检测纸张是否明显移动"""
    try:
        import cv2
        import numpy as np

        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        if img1 is None or img2 is None:
            return False
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        moved_ratio = np.sum(diff > 30) / diff.size
        return bool(moved_ratio > (1 - threshold))
    except Exception:
        return False


def _update_stamp_task(
    task_id: str,
    status: str,
    decision: str,
    before_img: str | None,
    after_img: str | None,
):
    from database.connection import get_db
    from sqlalchemy import text

    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            text("""
            UPDATE stamp_tasks
            SET status=:status, decision=:decision,
                before_img=COALESCE(:before_img, before_img),
                after_img=COALESCE(:after_img, after_img),
                updated_at=:updated_at
            WHERE task_id=:task_id
        """),
            {
                "task_id": task_id,
                "status": status,
                "decision": decision,
                "before_img": before_img,
                "after_img": after_img,
                "updated_at": now,
            },
        )


def _mark_leave_stamped(application_id: str, operator_id: str):
    from database.connection import get_db
    from sqlalchemy import text

    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            text("""
            UPDATE leave_applications
            SET status='STAMPED', stamped_at=:stamped_at, updated_at=:updated_at
            WHERE application_id=:application_id
        """),
            {
                "application_id": application_id,
                "stamped_at": now,
                "updated_at": now,
            },
        )


def _do_leave_stamp(image_path: str):
    """请假条盖章（调用机械臂）"""
    from api.calibration import get_arm

    logging.info("[stamp/leave] 执行固定盖章序列")
    get_arm().stamp_sequence()
