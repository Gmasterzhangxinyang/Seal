"""Dify 工作流客户端 — 请假条 AI 审批 + 语音模块"""

import requests
import logging
import json
import io

from config import DIFY_API_KEY, DIFY_VOICE_CHAT_APP_ID, DIFY_VOICE_TTS_APP_ID

logger = logging.getLogger(__name__)


class DifyLeaveWorkflow:
    """调用 Dify 请假条审批工作流（blocking 模式）"""

    BASE_URL = "https://api.dify.ai/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or DIFY_API_KEY

    def approve(self, start_date: str, end_date: str, reason: str) -> dict:
        """调用 Dify 工作流，返回 {approval_result, comment}"""
        url = f"{self.BASE_URL}/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": {
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
            },
            "response_mode": "blocking",
            "user": "mec202_system",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data", {}).get("status") == "failed":
            error_msg = data.get("data", {}).get("error", "")
            raise Exception(f"Dify 工作流执行失败: {error_msg}")
        outputs = data.get("data", {}).get("outputs", {})
        return {
            "approval_result": outputs.get("approval_result") or outputs.get("result"),
            "comment": outputs.get("comment"),
        }


def call_dify_approval(start_date: str, end_date: str, reason: str) -> dict:
    """便捷包装，内部捕获异常"""
    try:
        return DifyLeaveWorkflow().approve(start_date, end_date, reason)
    except Exception as e:
        logger.error(f"[dify] 调用审批工作流失败: {e}")
        return {"approval_result": None, "comment": f"AI 审批调用失败: {e}"}


# ─── 语音模块 Dify 客户端 ──────────────────────────────────────────────────────


class DifyVoiceWorkflow:
    """调用 Dify 语音问答工作流（带文件上传）"""

    BASE_URL = "https://api.dify.ai/v1"

    def __init__(self, app_id: str = None):
        # 语音问答的 app_id 也用作 API key
        self.app_id = app_id or DIFY_VOICE_CHAT_APP_ID
        self.api_key = self.app_id

    def _convert_to_mp3(self, audio_bytes: bytes, filename: str) -> bytes:
        """将音频转为 MP3 格式"""
        import subprocess, tempfile, os
        suffix = '.webm' if filename.endswith('.webm') else '.wav'
        tmp_in = tempfile.mktemp(suffix=suffix)
        tmp_out = tempfile.mktemp(suffix='.mp3')
        with open(tmp_in, 'wb') as f:
            f.write(audio_bytes)
        subprocess.run([
            'ffmpeg', '-y', '-f', 'wav' if suffix == '.wav' else 'webm',
            '-i', tmp_in, '-f', 'mp3', tmp_out
        ], capture_output=True, timeout=30)
        with open(tmp_out, 'rb') as f:
            result = f.read()
        os.unlink(tmp_in)
        os.unlink(tmp_out)
        return result

    def _upload_file_to_dify(self, audio_bytes: bytes, filename: str) -> str:
        """先上传文件到 Dify，获取 file_id"""
        url = f"{self.BASE_URL}/files/upload"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        # 先转 MP3 再上传
        mp3_bytes = self._convert_to_mp3(audio_bytes, filename)
        files = {
            "file": ("voice.mp3", mp3_bytes, "audio/mpeg"),
        }
        data = {
            "user": "mec202_voice",
        }
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        return result.get("id", "")

    def chat(self, audio_bytes: bytes, filename: str = "voice.mp3") -> dict:
        """调用语音问答工作流，传入音频文件，返回 tool_id + comment"""
        file_id = self._upload_file_to_dify(audio_bytes, filename)

        url = f"{self.BASE_URL}/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": {
                "voice": {
                    "transfer_method": "local_file",
                    "upload_file_id": file_id,
                    "type": "audio",
                }
            },
            "response_mode": "blocking",
            "user": "mec202_voice",
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        result = resp.json()

        if result.get("data", {}).get("status") == "failed":
            raise Exception(f"语音问答工作流失败: {result.get('data', {}).get('error')}")

        outputs = result.get("data", {}).get("outputs", {})

        tool_id = outputs.get("tool_id")
        comment = outputs.get("comment")

        if isinstance(tool_id, dict):
            tool_id = tool_id.get("tool_id") or tool_id.get("number") or tool_id
        if isinstance(comment, dict):
            comment = comment.get("comment") or comment.get("text") or comment

        return {
            "tool_id": tool_id,
            "comment": comment,
        }


class DifyVoiceTTS:
    """调用 Dify voice.yml 工作流生成 TTS"""

    BASE_URL = "https://api.dify.ai/v1"

    def __init__(self, app_id: str = None):
        # voice TTS 的 app_id 也用作 API key
        self.app_id = app_id or DIFY_VOICE_TTS_APP_ID
        self.api_key = self.app_id

    def text_to_speech(self, text: str) -> bytes:
        """调用 voice.yml 工作流，输入文字，输出 TTS 音频二进制"""
        url = f"{self.BASE_URL}/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": {"text": text},
            "response_mode": "blocking",
            "workflow_id": self.app_id,
            "user": "mec202_tts",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        if result.get("data", {}).get("status") == "failed":
            raise Exception(f"TTS 工作流失败: {result.get('data', {}).get('error')}")

        files = result.get("data", {}).get("outputs", {}).get("voice", [])
        if files:
            first_file = files[0]
            if isinstance(first_file, dict) and first_file.get("url"):
                audio_resp = requests.get(first_file["url"], timeout=30)
                audio_resp.raise_for_status()
                return audio_resp.content
            elif isinstance(first_file, str) and first_file.startswith("http"):
                audio_resp = requests.get(first_file, timeout=30)
                audio_resp.raise_for_status()
                return audio_resp.content

        raise Exception("TTS 工作流未返回音频文件")


def call_dify_voice_chat(audio_bytes: bytes, filename: str = "voice.mp3") -> dict:
    """便捷包装：调用语音问答工作流"""
    try:
        return DifyVoiceWorkflow().chat(audio_bytes, filename)
    except Exception as e:
        logger.error(f"[dify] 语音问答调用失败: {e}")
        return {"tool_id": None, "comment": f"语音理解失败: {e}"}


def call_dify_tts(text: str) -> bytes | None:
    """便捷包装：调用 voice.yml 生成 TTS，返回音频二进制或 None"""
    try:
        return DifyVoiceTTS().text_to_speech(text)
    except Exception as e:
        logger.error(f"[dify] TTS 调用失败: {e}")
        return None