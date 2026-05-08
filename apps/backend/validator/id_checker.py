from sqlalchemy import text
from database.connection import get_db


def verify_id(id_number: str, name: str) -> tuple[bool, str]:
    """在 personnel 表中验证 ID 号与姓名是否匹配。"""
    if not id_number:
        return False, 'ID号为空，无法验证'

    with get_db() as conn:
        row = conn.execute(text(
            'SELECT name FROM personnel WHERE id_number = :id'
        ), {'id': id_number}).fetchone()

    if row is None:
        return False, f'ID号 {id_number} 不在系统人员记录中'

    db_name = row[0]
    if name and db_name != name:
        return False, f'ID号对应姓名为「{db_name}」，与填写的「{name}」不符'

    return True, 'OK'
