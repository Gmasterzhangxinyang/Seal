"""语音模块 — 全部基于 Dify 工作流"""

import hashlib
import logging
import os
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger(__name__)

# TTS 缓存目录（预生成固定回复音频，避免每次调 Dify TTS）
TTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), "tts_cache")
os.makedirs(TTS_CACHE_DIR, exist_ok=True)

# 固定回复文本 → 预生成 TTS（工具 1-4）
FIXED_TTS_TEXTS = {
    1: "好的，机械臂已回到中位",
    2: "好的，机械臂正在移动",
    3: "好的，手腕抬起又放下啦",
    4: "好的，现在开始盖章",
}


def _text_cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _get_cached_tts_audio(text: str) -> bytes | None:
    """从缓存获取 TTS 音频，缓存不存在则返回 None"""
    key = _text_cache_key(text)
    path = os.path.join(TTS_CACHE_DIR, f"{key}.wav")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


def _cache_tts_audio(text: str, audio: bytes):
    """写入 TTS 缓存"""
    key = _text_cache_key(text)
    path = os.path.join(TTS_CACHE_DIR, f"{key}.wav")
    with open(path, "wb") as f:
        f.write(audio)


def _prewarm_tts_cache():
    """后台预生成固定回复的 TTS 缓存"""
    def _generate():
        from utils.dify_client import call_dify_tts
        logger.info("[voice] 开始预热 TTS 缓存...")
        for tool_id, text in FIXED_TTS_TEXTS.items():
            if _get_cached_tts_audio(text):
                logger.info(f"[voice] TTS 缓存已存在: tool_id={tool_id}")
                continue
            try:
                audio = call_dify_tts(text)
                if audio:
                    _cache_tts_audio(text, audio)
                    logger.info(f"[voice] TTS 缓存预生成成功: tool_id={tool_id}")
            except Exception as e:
                logger.warning(f"[voice] TTS 预生成失败 tool_id={tool_id}: {e}")
        logger.info("[voice] TTS 缓存预热完成")

    threading.Thread(target=_generate, daemon=True).start()


# 启动时预热 TTS 缓存（后台，不阻塞）
_prewarm_tts_cache()


def _execute_hardware(tool_id: int, comment: str):
    """后台线程执行机械臂动作，不阻塞主线程"""
    from api.calibration import get_arm
    from hardware.wearm import PWM_MID
    import time

    try:
        if tool_id == 1:  # arm_home
            get_arm().move_to({i: PWM_MID[i] for i in range(6)}, 1200)
            logger.info("[voice] arm_home 执行完成")

        elif tool_id == 2:  # arm_move
            logger.info(f"[voice] arm_move: {comment}")

        elif tool_id == 3:  # arm_greet
            # 回中位 → 抬手 → 鞠躬（向左）→ 抬手 → 鞠躬（中）→ 抬手 → 鞠躬（向右）→ 回中位
            get_arm().move_to({i: PWM_MID[i] for i in range(6)}, 600)
            time.sleep(0.4)

            def _wave():
                get_arm().move_single(3, 2200, 300)
                time.sleep(0.2)
                get_arm().move_single(3, PWM_MID[3], 300)

            _wave()
            time.sleep(0.2)
            get_arm().move_single(0, 1320, 250)
            time.sleep(0.25)
            _wave()
            time.sleep(0.2)
            get_arm().move_single(0, 1480, 250)
            time.sleep(0.25)
            _wave()
            time.sleep(0.2)
            get_arm().move_single(0, 1680, 250)
            time.sleep(0.25)
            _wave()
            time.sleep(0.2)
            get_arm().move_to({i: PWM_MID[i] for i in range(6)}, 600)
            logger.info("[voice] arm_greet 执行完成")

        elif tool_id == 4:  # stamp_leave_check
            from api.stamp import _do_leave_stamp
            _do_leave_stamp("")
            logger.info("[voice] stamp_leave_check 执行完成")
    except Exception as e:
        logger.error(f"[voice] 机械臂执行失败: {e}")


def _summarize_text(raw_text: str, task_hint: str) -> str:
    """用 LLM 将原始查询数据总结成自然语言，返回简短口语化回复"""
    try:
        from openai import OpenAI
        from config import CHAT_MODEL, VLM_API_KEY, VLM_BASE_URL

        client = OpenAI(api_key=VLM_API_KEY or "EMPTY", base_url=VLM_BASE_URL or "https://open.bigmodel.cn/api/paas/v4")
        prompt = (
            f"你是机械臂语音助手小臂的查询总结助手。{task_hint}结果如下，"
            f"请用简短、口语化、自然的语言（50字以内）总结给用户：\n\n{raw_text}"
        )
        response = client.chat.completions.create(
            model=CHAT_MODEL or "glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"[voice] LLM总结: {summary}")
        return summary
    except Exception as e:
        logger.warning(f"[voice] LLM总结失败，回退原始文本: {e}")
        return raw_text


def _execute_tool(tool_id: int, comment: str) -> str:
    """根据 tool_id 执行机械臂动作或查询数据库，返回查询结果"""
    if tool_id in (1, 2, 3, 4):
        # 机械臂动作：后台执行，不阻塞，立即返回
        threading.Thread(target=_execute_hardware, args=(tool_id, comment), daemon=True).start()
        return FIXED_TTS_TEXTS.get(tool_id, "好的")

    elif tool_id == 5:  # query_leave_history
        import re
        from sqlalchemy import text
        from database.connection import get_db
        # 从 comment 中提取中文姓名
        name_match = re.search(r'[\u4e00-\u9fff]{2,4}', comment)
        name = name_match.group() if name_match else None
        with get_db() as conn:
            if name:
                rows = conn.execute(
                    text(
                        """SELECT student_name, student_id, dept, leave_type, start_date, end_date, status, created_at
                           FROM leave_applications WHERE student_name = :name
                           ORDER BY id DESC LIMIT 10"""
                    ),
                    {"name": name},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """SELECT student_name, student_id, dept, leave_type, start_date, end_date, status, created_at
                           FROM leave_applications ORDER BY id DESC LIMIT 10"""
                    ),
                ).fetchall()
        if not rows:
            return f"没有找到{'的请假记录' if name else '请假记录'}"
        # 统计请假次数
        leave_count = len(rows)
        name_in_record = rows[0][0]
        student_id = rows[0][1] or "未知"
        dept = rows[0][2] or "未知部门"
        # 格式化每条记录
        lines = [f"{r[3]}，{r[4]}到{r[5]}，状态：{r[6]}" for r in rows]
        raw = f"姓名：{name_in_record}，学号：{student_id}，部门：{dept}，共请假{leave_count}次；" + "；".join(lines)
        return _summarize_text(raw, "请假记录查询")

    elif tool_id == 6:  # query_audit_logs
        from sqlalchemy import text
        from database.connection import get_db
        with get_db() as conn:
            rows = conn.execute(
                text(
                    """SELECT timestamp, operator_id, doc_type, result
                       FROM audit_log WHERE result IN ('APPROVED', 'STAMPED')
                       ORDER BY id DESC LIMIT 10"""
                ),
            ).fetchall()
        if not rows:
            return "近期没有盖章成功记录"
        lines = [f"{r[0]}，{r[1]}，{r[2] or '未知'}，结果：{r[3]}" for r in rows]
        raw = "盖章成功记录：" + "；".join(lines)
        return _summarize_text(raw, "盖章记录查询")

    return "未知动作"


class TTSRequest(BaseModel):
    text: str


@router.post("/chat")
async def voice_chat(request: Request):
    """接收前端录音，转发给 Dify 语音问答工作流，返回 tool_id + comment"""
    try:
        form = await request.form()
        audio_file = form.get("audio")
        if not audio_file:
            raise HTTPException(400, "未找到音频文件")

        audio_bytes = await audio_file.read()

        from utils.dify_client import call_dify_voice_chat

        result = call_dify_voice_chat(audio_bytes, audio_file.filename or "voice.mp3")

        tool_id = result.get("tool_id")
        comment = result.get("comment", "")

        # 执行对应的机械臂动作或查询数据库
        audio_b64 = None
        if tool_id in (1, 2, 3, 4, 5, 6):
            try:
                query_result = _execute_tool(tool_id, comment)
                logger.info(f"[voice] tool_id={tool_id}, query_result={query_result[:50] if query_result else None}")
                # tool_id 5-6 用真实查询结果覆盖 comment
                if tool_id in (5, 6) and query_result:
                    comment = query_result
                # tool_id 1-4 直接返回缓存的 TTS 音频，前端不用再调 /tts
                if tool_id in (1, 2, 3, 4):
                    cached = _get_cached_tts_audio(comment)
                    logger.info(f"[voice] cache lookup for '{comment}': {'HIT' if cached else 'MISS'}")
                    if cached:
                        import base64
                        audio_b64 = base64.b64encode(cached).decode()
                    else:
                        # 缓存未命中，同步调 Dify TTS 并缓存
                        from utils.dify_client import call_dify_tts
                        try:
                            audio = call_dify_tts(comment)
                            if audio:
                                _cache_tts_audio(comment, audio)
                                audio_b64 = base64.b64encode(audio).decode()
                                logger.info(f"[voice] TTS generated and cached for '{comment}'")
                        except Exception as e:
                            logger.warning(f"[voice] TTS generate failed: {e}")
            except Exception as e:
                logger.error(f"[voice] 执行工具失败: {e}")

        return {
            "tool_id": tool_id,
            "comment": comment,
            "audio": audio_b64,  # 有值时前端直接播放，跳过 /tts 调用
        }
    except Exception as e:
        logger.error(f"[voice/chat] 处理失败: {e}")
        return {"tool_id": None, "comment": None, "error": str(e)}


@router.post("/tts")
def text_to_speech(body: TTSRequest):
    """通过 Dify voice.yml TTS 工作流将文本转为语音，返回音频"""
    # 优先从缓存返回（tool_id 1-4 的固定回复已预缓存）
    cached = _get_cached_tts_audio(body.text)
    if cached:
        return Response(content=cached, media_type="audio/wav")

    from utils.dify_client import call_dify_tts
    audio = call_dify_tts(body.text)
    if not audio:
        raise HTTPException(500, "TTS 生成失败")
    # 写入缓存供后续使用
    _cache_tts_audio(body.text, audio)
    return Response(content=audio, media_type="audio/wav")


@router.get("/tools/query_leave_history")
def query_leave_history(name: str | None = None):
    """查询历史请假记录，供 Dify 工作流 HTTP 节点调用"""
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

        data = []
        for r in rows:
            data.append({
                "student_name": r[0],
                "dept": r[1] or "",
                "leave_type": r[2],
                "start_date": r[3],
                "end_date": r[4],
                "status": r[5],
            })
        return {"data": data}
    except Exception as e:
        logger.error(f"[voice/tools] 查询请假记录失败: {e}")
        return {"data": [], "error": str(e)}


@router.get("/tools/query_audit_logs")
def query_audit_logs():
    """查询最近盖章操作日志，供 Dify 工作流 HTTP 节点调用"""
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

        data = []
        for r in rows:
            data.append({
                "timestamp": r[0],
                "operator_id": r[1],
                "doc_type": r[2] or "",
                "result": r[3],
            })
        return {"data": data}
    except Exception as e:
        logger.error(f"[voice/tools] 查询盖章日志失败: {e}")
        return {"data": [], "error": str(e)}