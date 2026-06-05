import sys
import uvicorn

# 根目录入口包装器，启动位于 app/main.py 的标准架构 FastAPI 实例
if __name__ == "__main__":
    is_frozen = getattr(sys, 'frozen', False)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=not is_frozen)
