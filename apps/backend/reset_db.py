"""
数据库重置脚本：删除并重建数据库，运行迁移，插入 demo 数据。

用法：
    cd apps/backend
    python reset_db.py
"""

import subprocess
import sys
from pathlib import Path

# 确保 .env 已加载
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import pymysql


def drop_and_create_db():
    print(f"[1/4] 删除并重建数据库 {DB_NAME} ...")
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
    )
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
        cur.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    conn.commit()
    conn.close()
    print("  ✓ 数据库已重建")


def run_migrations():
    print("[2/4] 运行 Alembic 迁移 ...")
    env = {**__import__("os").environ, "PYTHONUTF8": "1"}
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(Path(__file__).parent),
        capture_output=True, text=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"  ✗ 迁移失败:\n{result.stderr}")
        sys.exit(1)
    print("  ✓ 迁移完成")


def seed_data():
    print("[3/4] 插入 demo 数据 ...")
    from database.seed import seed_demo_data, seed_default_templates
    seed_demo_data()
    seed_default_templates()
    print("  ✓ demo 数据已插入")


def seed_review_queue():
    print("[4/5] 初始化 review_queue ...")
    from database.connection import get_db
    from database.models import ReviewQueue
    from sqlalchemy import select, text
    from datetime import datetime
    with get_db() as conn:
        result = conn.execute(text("SELECT 1 FROM review_queue LIMIT 1")).first()
        if not result:
            conn.execute(
                ReviewQueue.__table__.insert().values(
                    id=1,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    operator_id="system",
                )
            )
    print("  ✓ review_queue 已初始化")


if __name__ == "__main__":
    confirm = input("⚠  这将清空所有数据并重建数据库，确认继续？(y/N): ")
    if confirm.strip().lower() != "y":
        print("已取消。")
        sys.exit(0)

    drop_and_create_db()
    run_migrations()
    seed_data()
    seed_review_queue()
    print("\n✅ 数据库重置完成！")
    print("Demo 账号：")
    print("  admin      / admin123      (管理员)")
    print("  operator1  / op123         (操作员)")
    print("  reviewer1  / reviewer123   (审核员)")
