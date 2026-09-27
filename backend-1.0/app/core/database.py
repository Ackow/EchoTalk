from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 对于 SQLite 数据库，我们需要开启多线程访问支持
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# 创建 SQLAlchemy 引擎
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)

# 创建本地会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 定义声明性基类
Base = declarative_base()

# 数据库连接生成器依赖项，供 FastAPI 路由生命周期调用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
