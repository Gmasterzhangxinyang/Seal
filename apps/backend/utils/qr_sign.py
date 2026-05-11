import hmac
import hashlib
import base64
import json
import secrets
from config import SECRET_KEY

_ALGORITHM = 'sha256'


def create_leave_qr_payload(application_id: str, student_id: str) -> dict:
    """生成请假条二维码 payload，包含防篡改签名"""
    payload = {
        'application_id': application_id,
        'student_id': student_id,
        'nonce': secrets.token_hex(8),
    }
    sig = _sign_payload(payload)
    payload['sig'] = sig
    return payload


def _sign_payload(payload: dict) -> str:
    """对 payload 生成 HMAC-SHA256 签名"""
    data = f"{payload['application_id']}:{payload['student_id']}"
    sig = hmac.new(
        SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(sig).decode()


def verify_qr_payload(payload: dict) -> bool:
    """验证二维码 payload 是否被篡改"""
    if not isinstance(payload, dict):
        return False
    if 'application_id' not in payload or 'student_id' not in payload:
        return False
    stored_sig = payload.get('sig')
    if not stored_sig:
        return False

    recalculated = _sign_payload(payload)
    return hmac.compare_digest(stored_sig, recalculated)


def qr_payload_to_string(payload: dict) -> str:
    """将 payload 序列化为字符串用于二维码"""
    return json.dumps(payload, separators=(',', ':'))


def qr_string_to_payload(qr_string: str) -> dict:
    """从二维码字符串反序列化 payload"""
    try:
        return json.loads(qr_string)
    except Exception:
        return {}