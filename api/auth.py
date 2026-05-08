import re
from datetime import datetime

from fastapi import APIRouter, Response, Depends, HTTPException
from pydantic import BaseModel
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text

from database.connection import get_db
from api.deps import get_session, set_session, require_role

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class UserInfo(BaseModel):
    username: str
    email: str
    role: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    with get_db() as conn:
        row = conn.execute(text(
            "SELECT password_hash, role FROM users WHERE username = :username"
        ), {"username": body.username}).fetchone()

    if not row or not check_password_hash(row[0], body.password):
        raise HTTPException(401, "账号或密码错误")

    set_session(response, body.username, row[1])
    return {"username": body.username, "role": row[1]}


@router.post("/register")
def register(body: RegisterRequest):
    if len(body.username) < 2 or len(body.username) > 20:
        raise HTTPException(400, "用户名长度需在 2-20 之间")
    if not EMAIL_RE.match(body.email):
        raise HTTPException(400, "邮箱格式不正确")
    if len(body.password) < 6:
        raise HTTPException(400, "密码长度不能少于 6 位")

    pw_hash = generate_password_hash(body.password)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        if conn.execute(text("SELECT 1 FROM users WHERE username=:u"), {"u": body.username}).fetchone():
            raise HTTPException(400, "用户名已存在")
        if conn.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": body.email}).fetchone():
            raise HTTPException(400, "该邮箱已注册")
        conn.execute(text(
            "INSERT INTO users (username, password_hash, email, role, created_at) "
            "VALUES (:u, :pw, :e, 'operator', :t)"
        ), {"u": body.username, "pw": pw_hash, "e": body.email, "t": now})

    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("stamp_session")
    return {"status": "ok"}


@router.get("/me")
def me(session: dict = Depends(get_session)):
    with get_db() as conn:
        row = conn.execute(text(
            "SELECT email FROM users WHERE username = :username"
        ), {"username": session["username"]}).fetchone()
    return UserInfo(
        username=session["username"],
        email=row[0] if row else "",
        role=session["role"],
    )
