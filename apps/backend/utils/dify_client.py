"""Dify 工作流客户端 — 请假条 AI 审批"""

import requests
import logging

from config import DIFY_API_KEY

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
            "workflow_id": self.api_key,
            "user": "mec202_system",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # 检查工作流是否执行成功
        if data.get("data", {}).get("status") == "failed":
            error_msg = data.get("data", {}).get("error", "")
            raise Exception(f"Dify 工作流执行失败: {error_msg}")
        outputs = data.get("data", {}).get("outputs", {})
        # 映射 Dify 输出字段到我们的格式
        # Dify 可能返回 result 或 approval_result
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