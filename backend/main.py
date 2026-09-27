import uvicorn
from app.core.config import API_BIND_HOST, API_BIND_PORT

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=API_BIND_HOST, port=API_BIND_PORT, reload=True)
