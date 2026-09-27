"""显式初始化 EchoTalk 账户表；部署 API 时不会自动执行 DDL。"""
from app import models  # noqa: F401 注册所有模型表
from app.core.database import Base, engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("EchoTalk 账户表已初始化。")
