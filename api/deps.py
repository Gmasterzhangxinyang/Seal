from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import TimestampSigner
from config import SECRET_KEY

signer = TimestampSigner(SECRET_KEY)
SESSION_COOKIE = "stamp_session"


def get_session(request: Request) -> dict:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(401, "未登录")
    try:
        data = signer.unsign(cookie, max_age=86400 * 7)
        parts = data.decode().split("|")
        return {"username": parts[0], "role": parts[1]}
    except Exception:
        raise HTTPException(401, "登录已过期")


def set_session(response: Response, username: str, role: str):
    token = signer.sign(f"{username}|{role}").decode()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=86400 * 7, samesite="lax")


def require_role(*roles: str):
    def checker(session: dict = Depends(get_session)):
        if session["role"] not in roles:
            raise HTTPException(403, "权限不足")
        return session
    return checker
