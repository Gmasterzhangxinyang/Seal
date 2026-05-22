from contextlib import contextmanager
from sqlalchemy import create_engine
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)


@contextmanager
def get_db():
    """上下文管理器，自动 commit/rollback。"""
    with engine.connect() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
