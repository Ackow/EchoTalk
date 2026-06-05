import sys
import os
import uvicorn
import app.main

# 根目录入口包装器，启动位于 app/main.py 的标准架构 FastAPI 实例
if __name__ == "__main__":
    is_frozen = getattr(sys, 'frozen', False)
    port = int(os.environ.get("ECHOTALK_BACKEND_PORT", "8000"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=not is_frozen)
