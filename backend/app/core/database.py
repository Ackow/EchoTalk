"""数据库引擎与请求级事务会话。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

# 连接池保活：探测失效连接并定期回收，避免 MySQL 空闲断连后报错。
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)  # 会话工厂：每个请求新建一个事务会话
Base = declarative_base()  # ORM 模型基类：models.py 中所有表继承它


def get_db():
    """FastAPI 依赖：请求期间提供数据库会话，结束时自动关闭。"""
    db = SessionLocal()
    try:
        yield db  # 请求处理期间交出会话
    finally:
        db.close()  # 请求结束无论成败都归还连接
