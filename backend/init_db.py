"""显式初始化 EchoTalk 数据表并同步内置场景包种子；部署 API 时不会自动执行 DDL。"""
from app import models  # noqa: F401 注册所有模型表
from app.core.database import Base, engine, SessionLocal

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    from app.scenes.registry import sync_seeds

    with SessionLocal() as db:
        count = sync_seeds(db)
    print(f"EchoTalk 数据表已初始化，内置场景包同步 {count} 个。")
