import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import engine, Base, get_db
from app.models import Scene, User
from app.core.config import settings
from app.api.api import api_router

# 首次启动自动创建 SQLite 所有数据表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EchoTalk API",
    description="云音口语（EchoTalk）英语口语练习工具后端服务",
    version="1.0.0"
)

# 挂载本地音频静态文件目录（供七牛云上传异常或离线开发时回退播放）
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "..", "static")
os.makedirs(os.path.join(static_dir, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 配置 CORS 跨域规则，允许桌面端本地 Electron 页面调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 桌面应用一般使用宽松的跨域，也可以在生产阶段限制为特定的 electron 协议
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载聚合后的业务 API 路由，所有路径前缀统一为 /api
app.include_router(api_router, prefix="/api")

def seed_default_scenes(db: Session):
    """
    预置种子数据：自动注册面试、点餐、同步会议等三大开箱即用口语练习场景
    """
    default_scenes = [
        {
            "id": "interview",
            "name": "软件工程师面试 (Job Interview)",
            "description": "模拟外企软件工程师英文技术面试，考察专业术语、沟通能力与逻辑表达。",
            "category": "interview",
            "default_params": {
                "personality": "professional and slightly strict",
                "company_name": "Global Tech Inc.",
                "job_title": "Senior Frontend Developer",
                "interviewer_name": "Sarah"
            },
            "system_prompt": "You are Sarah, a professional and slightly strict Senior engineering manager at Global Tech Inc. You are conducting an English interview for a Senior Frontend Developer position. The candidate is the user. Speak naturally as an interviewer, keep your questions clear, ask one technical or behavioral question at a time. Keep your turns concise (1-2 sentences). Start by welcoming the candidate and asking them to briefly introduce themselves."
        },
        {
            "id": "ordering",
            "name": "繁忙咖啡厅点餐 (Cafe Ordering)",
            "description": "在纽约街头咖啡馆点一份早餐与咖啡，练习日常口语、定制化订单与结账表达。",
            "category": "ordering",
            "default_params": {
                "personality": "friendly but busy",
                "store_name": "Metro Cafe",
                "cashier_name": "Leo"
            },
            "system_prompt": "You are Leo, a busy but friendly barista at Metro Cafe in New York. The customer (user) wants to order coffee or breakfast. Speak naturally, ask for preferences (size, milk type, sugar, dine-in or to-go). Keep responses very brief (1 sentence) to match the fast-paced environment. Start by greeting the customer warmly and asking what they would like today."
        },
        {
            "id": "meeting",
            "name": "产品发布会同步会议 (Business Meeting)",
            "description": "参与跨国项目组的产品发布准备会议，讨论进度延误、解决方案与任务分工。",
            "category": "meeting",
            "default_params": {
                "personality": "result-oriented and collaborative",
                "chairperson_name": "David",
                "topic": "Frontend delay for the Q3 product launch"
            },
            "system_prompt": "You are David, the Product Manager leading a product alignment alignment meeting. The user is a frontend developer on the team. We are discussing the Q3 product launch delay. Speak professionally, ask questions about their progress, blockages, and ask for an updated estimation. Keep your replies concise (1-2 sentences) and collaborative. Start the meeting by greeting the developer and stating the agenda."
        }
    ]

    for scene_data in default_scenes:
        existing = db.query(Scene).filter(Scene.id == scene_data["id"]).first()
        if not existing:
            scene = Scene(
                id=scene_data["id"],
                name=scene_data["name"],
                description=scene_data["description"],
                category=scene_data["category"],
                default_params=scene_data["default_params"],
                system_prompt=scene_data["system_prompt"],
                rag_metadata=[]
            )
            db.add(scene)
    db.commit()

# 在服务启动时自动初始化表与种子场景数据
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        seed_default_scenes(db)
        
        # 预注册一个默认的本地测试用户
        test_user = db.query(User).filter(User.username == "default_user").first()
        if not test_user:
            db.add(User(username="default_user"))
            db.commit()
    except Exception as e:
        print(f"[种子填充异常] 数据初始化失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # 本地启动端口设为 8000
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
