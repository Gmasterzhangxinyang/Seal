import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_session
from config import AURORA_API_KEY, AURORA_CHAT_URL, AURORA_TIMEOUT_SECONDS

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

ROLE_PERMISSION_SCOPES = {
    "admin": {
        "name": "admin",
        "allowed_features": [
            "操作台盖章",
            "请假申请",
            "人工复审",
            "模板管理",
            "用户管理",
            "机械臂标定",
            "统计面板",
            "审计日志",
            "语音控制",
        ],
        "forbidden_features": [],
    },
    "reviewer": {
        "name": "reviewer",
        "allowed_features": [
            "操作台盖章",
            "请假申请提交与审批",
            "人工复审队列",
            "审计日志",
        ],
        "forbidden_features": [
            "用户管理",
            "机械臂标定",
            "统计面板",
            "模板管理",
        ],
    },
    "operator": {
        "name": "operator",
        "allowed_features": [
            "操作台盖章",
            "提交请假申请",
            "查看自己的申请状态",
        ],
        "forbidden_features": [
            "人工复审",
            "审计日志",
            "模板管理",
            "用户管理",
            "机械臂标定",
            "统计面板",
        ],
    },
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, session: dict = Depends(get_session)):
    """把当前用户问题和可信角色上下文转发给 Aurora。"""
    if not AURORA_CHAT_URL:
        raise HTTPException(500, "Aurora 智能助手地址未配置")

    username = session.get("username", "用户")
    role = session.get("role", "operator")
    permission_scope = ROLE_PERMISSION_SCOPES.get(role, ROLE_PERMISSION_SCOPES["operator"])

    payload = {
        "message": body.message,
        "user": {
            "username": username,
            "role": role,
        },
        "context": {
            "system": "MEC202 文档核验盖章系统",
            "locale": "zh-CN",
            "permission_scope": permission_scope,
            "assistant_rules": [
                "你是 MEC202 文档核验盖章系统的智能助手。",
                "请根据 user.role 和 context.permission_scope 回答。",
                "不要向用户介绍当前角色无权访问的功能细节。",
                "如果用户询问越权功能，只说明当前角色无权使用该功能。",
                "回答应简洁、专业，并尽量给出可操作步骤。",
                "如果问题与 MEC202 系统无关，请礼貌说明你主要负责 MEC202 系统使用说明。",
            ],
        },
    }

    headers = {"Content-Type": "application/json"}
    if AURORA_API_KEY:
        headers["Authorization"] = f"Bearer {AURORA_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=AURORA_TIMEOUT_SECONDS) as client:
            response = await client.post(AURORA_CHAT_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        logger.warning("[chat] Aurora 请求超时")
        raise HTTPException(504, "智能助手响应超时，请稍后重试")
    except httpx.HTTPStatusError as exc:
        logger.error("[chat] Aurora 返回错误状态: %s", exc.response.status_code)
        raise HTTPException(502, "智能助手暂时不可用，请稍后重试")
    except Exception as exc:
        logger.error("[chat] Aurora 调用失败: %s", exc)
        raise HTTPException(502, "智能助手暂时不可用，请稍后重试")

    reply = data.get("reply") or data.get("content") or data.get("message")
    if not isinstance(reply, str) or not reply.strip():
        logger.error("[chat] Aurora 响应格式异常: %s", data)
        raise HTTPException(502, "智能助手响应格式异常")

    return ChatResponse(reply=reply.strip())
