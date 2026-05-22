from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database.connection import get_db
from api.deps import require_role

router = APIRouter(prefix="/users", tags=["users"])


class UserItem(BaseModel):
    username: str
    email: str
    role: str
    created_at: str


@router.get("")
def list_users(session: dict = Depends(require_role("admin"))):
    with get_db() as conn:
        rows = conn.execute(
            text(
                "SELECT username, email, role, created_at FROM users ORDER BY created_at"
            )
        ).fetchall()
    return [
        UserItem(username=r[0], email=r[1], role=r[2], created_at=r[3]).model_dump()
        for r in rows
    ]


@router.delete("/{username}")
def delete_user(username: str, session: dict = Depends(require_role("admin"))):
    if username == session["username"]:
        raise HTTPException(400, "不能删除自己")
    with get_db() as conn:
        result = conn.execute(
            text("DELETE FROM users WHERE username=:u"), {"u": username}
        )
        if result.rowcount == 0:
            raise HTTPException(404, "用户不存在")
    return {"status": "ok"}
