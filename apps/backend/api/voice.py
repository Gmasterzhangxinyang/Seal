import logging
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import Response
from pydantic import BaseModel

from api.deps import get_session

router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger(__name__)

_sessions: dict[str, list] = {}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "arm_home",
            "description": "控制机械臂回到中位（所有舵机归零）",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arm_move",
            "description": "控制机械臂移动到指定位置，servos 是 0-5 号舵机的 PWM 值（500-2500）",
            "parameters": {
                "type": "object",
                "properties": {
                    "servos": {
                        "type": "object",
                        "properties": {
                            "0": {"type": "integer", "description": "底盘 PWM"},
                            "1": {"type": "integer", "description": "大臂 PWM"},
                            "2": {"type": "integer", "description": "小臂 PWM"},
                            "3": {"type": "integer", "description": "手腕 PWM"},
                            "4": {"type": "integer", "description": "夹爪 PWM"},
                            "5": {"type": "integer", "description": "辅助 PWM"},
                        },
                    },
                },
                "required": ["servos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arm_greet",
            "description": "向观众打招呼动作：手腕（S3）抬起再放下",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stamp_leave_check",
            "description": "智能盖章：拍照→扫码→识别→核验→通过则盖章。返回核验结果供你生成回复。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_leave_history",
            "description": "查询历史请假记录。可按姓名搜索，不传姓名则返回最近 10 条记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "学生姓名（可选，不传则返回最近记录）",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_audit_logs",
            "description": "查询最近的盖章操作日志，包括操作时间、操作人、文档类型、结果等。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """你是机械臂语音助手，名叫小臂。用户通过语音和你对话。

你可以调用的工具：
- arm_home: 回中位
- arm_move: 移动到指定位置
- arm_greet: 打招呼动作
- stamp_leave_check: 智能盖章（自动拍照、扫码、核验、盖章）
- query_leave_history: 查询历史请假记录（可按姓名搜索）
- query_audit_logs: 查询最近的盖章操作日志

规则：
- 你先根据用户意图调用工具，再根据工具返回结果生成自然的语音回复
- 回复要简短自然，像朋友聊天，不要太机械
- 用户问历史记录时，用 query_leave_history 查询后自然地告诉结果
- 用户问盖章记录时，用 query_audit_logs 查询后告诉结果
- 如果盖章核验通过，你要先说"好的，我现在就盖章"，调用工具后再说"盖章完成啦"
- 如果核验不通过，用工具返回的原因自然地告诉用户为什么不能盖章
- 如果用户没放请假条或者扫不到码，提示用户放好请假条再试
- 不可重复盖章"""


class ChatRequest(BaseModel):
    session_id: str
    text: str


class ChatResponse(BaseModel):
    reply: str
    action: str | None = None
    action_description: str | None = None


def _execute_tool(name: str, arguments: dict) -> str:
    """执行工具，返回结果描述"""
    from api.calibration import get_arm
    from hardware.wearm import PWM_MID

    if name == "arm_home":
        get_arm().move_to({i: PWM_MID for i in range(6)}, 1200)
        return "机械臂已回到中位"

    elif name == "arm_move":
        servos_raw = arguments.get("servos", {})
        int_servos = {int(k): int(v) for k, v in servos_raw.items()}
        get_arm().move_to(int_servos, 1200)
        return f"机械臂已移动到指定位置 {int_servos}"

    elif name == "arm_greet":
        get_arm().move_single(3, 2200, 500)
        import time
        time.sleep(0.5)
        get_arm().move_single(3, 1500, 500)
        return "打招呼动作完成，手腕抬起又放下了"

    elif name == "stamp_leave_check":
        return _do_stamp_leave_check()

    elif name == "query_leave_history":
        return _query_leave_history(arguments.get("name"))

    elif name == "query_audit_logs":
        return _query_audit_logs()

    return "未知动作"


def _do_stamp_leave_check() -> str:
    """执行智能盖章流程，返回核验结果"""
    import time

    try:
        from vision.camera import SharedCamera
        from vision.qr_scanner import scan_qr
        from api.stamp import _gpt4v_extract, _do_leave_stamp
        from api.calibration import get_arm
        from hardware.wearm import PWM_MID
        from validator.leave_validator import verify_leave_application
        from database.audit import log_action
        from config import SIMULATION_MODE
        from datetime import datetime

        # 1. 拍照
        camera = SharedCamera.get_instance()
        before_img = camera.capture_timestamped("voice_leave")
        logger.info("[voice/stamp] 拍照完成")

        # 2. 扫码
        qr_content, _ = scan_qr(before_img)
        if not qr_content:
            return "未检测到二维码，请确保请假条上的二维码在摄像头视野内"

        # 3. 解析二维码
        try:
            qr_data = json.loads(qr_content)
        except Exception:
            return "二维码内容无法解析"

        if "application_id" not in qr_data:
            return "二维码不是请假条二维码"

        application_id = qr_data.get("application_id", "")

        # 4. GLM-4V 识别
        extracted_fields = _gpt4v_extract(before_img)
        if not extracted_fields:
            return "视觉模型识别失败，请检查请假条是否清晰"

        fields_summary = ", ".join(
            f"{k}={v}" for k, v in extracted_fields.items() if v
        )
        logger.info(f"[voice/stamp] 识别字段: {fields_summary}")

        # 5. 核验
        result = verify_leave_application(qr_content, extracted_fields, 0.95)
        decision = result.decision
        errors = result.errors
        warnings = result.warnings

        # 6. 执行盖章或返回原因
        if decision == "PASS" and not errors:
            if not SIMULATION_MODE:
                # 先回中位，确保和原始盖章按钮从同一位置出发
                get_arm().move_to({i: PWM_MID for i in range(6)}, 1200)
                time.sleep(1.2)
                _do_leave_stamp(before_img)
                logger.info("[voice/stamp] 盖章完成")
            else:
                logger.info("[voice/stamp] 仿真模式，跳过盖章")

            after_img = camera.capture_timestamped("voice_after")
            log_action(
                operator_id="voice",
                doc_type="leave",
                qr_content=qr_content,
                doc_fields=extracted_fields,
                result="APPROVED",
                errors=[],
                before_img=before_img,
                after_img=after_img,
                ocr_text=str(extracted_fields),
            )
            return f"核验通过，申请编号: {application_id}"

        else:
            reasons = errors if errors else warnings if warnings else ["核验未通过"]
            reason_str = "；".join(reasons)
            log_action(
                operator_id="voice",
                doc_type="leave",
                qr_content=qr_content,
                doc_fields=extracted_fields,
                result=decision,
                errors=reasons,
                before_img=before_img,
                after_img=None,
                ocr_text=str(extracted_fields),
            )
            return f"核验未通过（{decision}）。原因：{reason_str}"

    except Exception as e:
        logger.error(f"[voice/stamp] 智能盖章失败: {e}")
        return f"处理出错: {e}"


def _query_leave_history(name: str | None) -> str:
    """查询历史请假记录"""
    from sqlalchemy import text
    from database.connection import get_db

    try:
        with get_db() as conn:
            if name:
                rows = conn.execute(
                    text(
                        """SELECT student_name, dept, leave_type, start_date, end_date, status
                           FROM leave_applications WHERE student_name LIKE :name
                           ORDER BY id DESC LIMIT 10"""
                    ),
                    {"name": f"%{name}%"},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """SELECT student_name, dept, leave_type, start_date, end_date, status
                           FROM leave_applications ORDER BY id DESC LIMIT 10"""
                    ),
                ).fetchall()

        if not rows:
            target = f"关于{name}的" if name else ""
            return f"没有找到{target}请假记录"

        lines = []
        for r in rows:
            lines.append(
                f"{r[0]}（{r[1] or '未知部门'}）{r[2]}，{r[3]}到{r[4]}，状态：{r[5]}"
            )
        return "请假记录：\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"[voice] 查询请假记录失败: {e}")
        return "查询请假记录时出错"


def _query_audit_logs() -> str:
    """查询最近盖章操作日志"""
    from sqlalchemy import text
    from database.connection import get_db

    try:
        with get_db() as conn:
            rows = conn.execute(
                text(
                    """SELECT timestamp, operator_id, doc_type, result
                       FROM audit_log ORDER BY id DESC LIMIT 10"""
                ),
            ).fetchall()

        if not rows:
            return "暂无盖章操作记录"

        lines = []
        for r in rows:
            lines.append(f"{r[0]}，{r[1]}，{r[2] or '未知'}，结果：{r[3]}")
        return "最近盖章记录：\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"[voice] 查询审计日志失败: {e}")
        return "查询审计日志时出错"


@router.post("/chat")
def voice_chat(body: ChatRequest, session: dict = Depends(get_session)):
    """多轮语音对话 + 工具调用"""
    from openai import OpenAI
    from config import VLM_API_KEY, VLM_BASE_URL, CHAT_MODEL

    sid = body.session_id
    if sid not in _sessions:
        _sessions[sid] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
    messages = _sessions[sid]
    messages.append({"role": "user", "content": body.text})

    client = OpenAI(api_key=VLM_API_KEY, base_url=VLM_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error(f"[voice] LLM 调用失败: {e}")
        raise HTTPException(500, f"语音理解失败: {e}")

    choice = response.choices[0]
    msg = choice.message
    reply = msg.content or ""

    action = None
    action_desc = None

    # 处理工具调用
    if msg.tool_calls:
        # 把用户消息和工具调用都存入历史
        messages.append(msg.model_dump())

        tool_results = []
        for tc in msg.tool_calls:
            fname = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            action = fname
            result = _execute_tool(fname, args)
            action_desc = result
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
            logger.info(f"[voice] 工具调用: {fname} → {result}")

        messages.extend(tool_results)

        # 让 LLM 根据工具结果生成最终回复
        try:
            follow = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
            )
            reply = follow.choices[0].message.content or reply
        except Exception:
            pass

    messages.append({"role": "assistant", "content": reply})

    # 限制历史长度
    if len(messages) > 22:
        _sessions[sid] = [messages[0]] + messages[-20:]

    return ChatResponse(
        reply=reply, action=action, action_description=action_desc
    )


@router.post("/asr")
async def transcribe_audio(request: Request):
    """通过阿里云 DashScope Fun-ASR 识别上传的音频，返回文字"""
    import os, subprocess, tempfile
    from config import DASHSCOPE_API_KEY

    os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY

    if not DASHSCOPE_API_KEY:
        raise HTTPException(500, "DashScope API Key 未配置")

    try:
        body = await request.body()
        if len(body) == 0:
            raise HTTPException(400, "音频数据为空")

        # 写 webm 文件
        tmp_webm = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        tmp_webm.write(body)
        tmp_webm.close()

        # 转换 pcm
        tmp_pcm = tempfile.mktemp(suffix=".pcm")
        ffmpeg_path = "C:/Program Files/ffmpeg-6.0-full_build/bin/ffmpeg"
        subprocess.run([
            ffmpeg_path, "-y", "-i", tmp_webm.name,
            "-f", "s16le", "-ar", "16000", "-ac", "1",
            tmp_pcm
        ], capture_output=True)
        os.unlink(tmp_webm.name)

        from dashscope.audio.asr import Recognition

        result = Recognition.call(
            model="paraformer-realtime-v2",
            input=tmp_pcm,
            format="pcm",
            sample_rate=16000,
            language_hints=["zh"],
        )
        text = result.get_sentence().get("text", "") if result else ""

        try:
            os.unlink(tmp_pcm)
        except:
            pass

        logger.info(f"[voice/asr] 识别结果: {text}")
        return {"text": text}
    except Exception as e:
        logger.error(f"[voice/asr] 识别失败: {e}")
        raise HTTPException(500, f"语音识别失败: {e}")


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
def text_to_speech(body: TTSRequest):
    """通过 Fish Audio 将文本转为语音，返回 mp3 音频"""
    import httpx
    from config import FISH_AUDIO_API_KEY

    if not FISH_AUDIO_API_KEY:
        raise HTTPException(500, "Fish Audio API Key 未配置")

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.fish.audio/v1/tts",
                json={"text": body.text, "format": "mp3"},
                headers={
                    "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
                    "model": "s2-pro",
                },
            )
        if resp.status_code != 200:
            logger.error(f"[voice/tts] Fish Audio 返回 {resp.status_code}: {resp.text}")
            raise HTTPException(502, f"TTS 服务返回 {resp.status_code}")
        return Response(content=resp.content, media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[voice/tts] TTS 调用失败: {e}")
        raise HTTPException(500, f"语音合成失败: {e}")