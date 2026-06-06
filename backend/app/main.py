import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.endpoints.scenes import generate_and_upload_greeting_audio
from app.core.database import engine, Base, get_db
from app.models import Scene, User
from app.core.config import settings
from app.api.api import api_router
from app.services.tts import text_to_speech
from app.services.storage import upload_audio_to_kodo
import time
import threading

# ══════════════════════════════════════════════════════════════════════════════
# 全局初始化状态追踪器
# ══════════════════════════════════════════════════════════════════════════════
class InitStatus:
    """追踪后端首次启动的初始化进度，供前端 Splash 页面消费"""
    def __init__(self):
        self._lock = threading.Lock()
        self.phase = "pending"        # pending | schema | seeding | user | done | error
        self.message = "等待初始化..."
        self.progress = 0             # 0-100
        self.detail = ""              # 当前正在处理的具体内容
        self.is_first_launch = False  # 是否为首次启动（需要生成TTS）
        self.error = None
    
    def update(self, phase: str, message: str, progress: int, detail: str = ""):
        with self._lock:
            self.phase = phase
            self.message = message
            self.progress = min(100, max(0, progress))
            self.detail = detail
    
    def set_error(self, error_msg: str):
        with self._lock:
            self.phase = "error"
            self.error = error_msg
    
    def to_dict(self):
        with self._lock:
            return {
                "phase": self.phase,
                "message": self.message,
                "progress": self.progress,
                "detail": self.detail,
                "is_first_launch": self.is_first_launch,
                "done": self.phase == "done",
                "error": self.error,
            }

init_status = InitStatus()

# 首次启动自动创建 SQLite 所有数据表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EchoTalk API",
    description="云音口语（EchoTalk）英语口语练习工具后端服务",
    version="1.0.0"
)

# 挂载本地音频静态文件目录（供七牛云上传异常或离线开发时回退播放）
static_dir = settings.static_dir
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

def check_and_upgrade_database_schema(db: Session):
    """
    自适应数据库热升级：如果已存在的 scenes 表没有 greeting_audio_url 字段，则通过 ALTER TABLE 命令热增加该字段。
    同时，如果 dialogue_histories 表没有 speaking_style 字段，也通过 ALTER TABLE 热增加。
    """
    try:
        cursor = db.execute(text("PRAGMA table_info(scenes)"))
        columns = [row[1] for row in cursor.fetchall()]
        if "greeting_audio_url" not in columns:
            print("[数据库热升级] scenes 表缺失 greeting_audio_url 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE scenes ADD COLUMN greeting_audio_url VARCHAR(255)"))
            db.commit()
            print("[数据库热升级] scenes 表成功注入 greeting_audio_url 字段！")
            
        cursor = db.execute(text("PRAGMA table_info(dialogue_histories)"))
        dh_columns = [row[1] for row in cursor.fetchall()]
        if "speaking_style" not in dh_columns:
            print("[数据库热升级] dialogue_histories 表缺失 speaking_style 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE dialogue_histories ADD COLUMN speaking_style VARCHAR(20) DEFAULT 'colloquial'"))
            db.commit()
            print("[数据库热升级] dialogue_histories 表成功注入 speaking_style 字段！")
            
        if "accent" not in dh_columns:
            print("[数据库热升级] dialogue_histories 表缺失 accent 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE dialogue_histories ADD COLUMN accent VARCHAR(10) DEFAULT 'us'"))
            db.commit()
            print("[数据库热升级] dialogue_histories 表成功注入 accent 字段！")

        if "is_finished" not in dh_columns:
            print("[数据库热升级] dialogue_histories 表缺失 is_finished 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE dialogue_histories ADD COLUMN is_finished BOOLEAN DEFAULT 0 NOT NULL"))
            db.commit()
            print("[数据库热升级] dialogue_histories 表成功注入 is_finished 字段！")
            
        cursor = db.execute(text("PRAGMA table_info(dialogue_turns)"))
        dt_columns = [row[1] for row in cursor.fetchall()]
        if "audio_url_us" not in dt_columns:
            print("[数据库热升级] dialogue_turns 表缺失 audio_url_us 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE dialogue_turns ADD COLUMN audio_url_us VARCHAR(255)"))
            db.commit()
            print("[数据库热升级] dialogue_turns 表成功注入 audio_url_us 字段！")
            
        if "audio_url_uk" not in dt_columns:
            print("[数据库热升级] dialogue_turns 表缺失 audio_url_uk 字段，正在执行热注入...")
            db.execute(text("ALTER TABLE dialogue_turns ADD COLUMN audio_url_uk VARCHAR(255)"))
            db.commit()
            print("[数据库热升级] dialogue_turns 表成功注入 audio_url_uk 字段！")
    except Exception as e:
        print(f"[数据库热升级异常警告] 自动升级 schema 失败: {e}")

def seed_rag_for_scene(db: Session, scene_id: str, scene_obj: Scene):
    """
    检查指定场景是否需要种子填充其 RAG 知识库。如果需要，则读取 tests/data 下对应的预置文件，
    解析并导入 FAISS 库，同步更新/校准 RAG 元数据（支持内容改变后的自动升级）。
    """
    # 场景与种子文件映射关系
    mapping = {
        "ordering": "cafe_menu.txt",
        "interview": "interview_prep.txt",
        "meeting": "meeting_brief.txt"
    }
    filename = mapping.get(scene_id)
    if not filename:
        return

    # 确认物理种子文件存在（位于 app/data/rag_seeds/，PyInstaller 打包时随 app 目录一并收录）
    import datetime
    import hashlib
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "rag_seeds", filename)
    if not os.path.exists(file_path):
        print(f"[RAG 种子异常] 未找到场景 '{scene_id}' 的种子文档: {file_path}")
        return

    # 计算物理文件的 MD5 哈希
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()
    except Exception as e:
        print(f"[RAG 种子异常] 无法计算文件 '{filename}' 的哈希: {e}")
        return

    # 检查是否已挂载该文件
    metadata = scene_obj.rag_metadata if scene_obj.rag_metadata else []
    existing_item = next((item for item in metadata if item.get("filename") == filename), None)
    
    # 如果已存在，且哈希值一致，直接跳过
    if existing_item and existing_item.get("file_hash") == file_hash:
        print(f"[RAG 种子检查] 场景 '{scene_id}' 的 RAG 种子文档 '{filename}' 已存在且无变化，跳过 RAG 初始化。")
        return

    # 如果存在但哈希值不一致，或者由于历史升级遗留（之前没有 file_hash 字段），则重置旧索引并重新导入
    is_upgrade = existing_item is not None
    if is_upgrade:
        print(f"[RAG 种子升级] 检测到场景 '{scene_id}' 的种子文档 '{filename}' 内容有更新（或缺失哈希标识），正在重置索引并重新填充...")
        from app.services.rag import clear_scene_knowledge
        try:
            clear_scene_knowledge(scene_id)
        except Exception as e:
            print(f"[RAG 种子升级警告] 清空旧 RAG 库失败: {e}")
        metadata = [item for item in metadata if item.get("filename") != filename]

    print(f"[RAG 种子填充] 正在为场景 '{scene_id}' 导入种子文档 '{filename}'...")
    try:
        from app.services.document import get_document_chunks
        from app.services.rag import add_documents_to_scene

        # 1. 解析并分块
        chunks = get_document_chunks(file_path)
        if not chunks:
            print(f"[RAG 种子异常] 文档 '{filename}' 解析分块为空，无法导入。")
            return

        # 2. 写入 FAISS 库并持久化索引
        add_documents_to_scene(scene_id, chunks)

        # 3. 更新元数据
        new_metadata = list(metadata)
        new_metadata = [item for item in new_metadata if item.get("filename") != filename]
        
        content_type = "text/markdown" if filename.endswith(".md") else "text/plain"
        new_metadata.append({
            "filename": filename,
            "content_type": content_type,
            "chunk_count": len(chunks),
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
            "file_hash": file_hash
        })
        
        scene_obj.rag_metadata = new_metadata
        db.add(scene_obj)
        db.commit()
        db.refresh(scene_obj)
        action_str = "升级校准" if is_upgrade else "初始化录入"
        print(f"[RAG 种子成功] 场景 '{scene_id}' 成功{action_str}种子文档 '{filename}'（共 {len(chunks)} 个分块）。")
    except Exception as e:
        db.rollback()
        print(f"[RAG 种子填充失败] 场景 '{scene_id}' 录入种子文档出现异常: {e}")


def seed_default_scenes(db: Session):
    """
    预置种子数据：自动注册面试、点餐、同步会议等三大开箱即用口语练习场景
    """
    # 自动进行 schema 校验升级，防范外部测试或独立脚本在空库启动时缺失字段
    check_and_upgrade_database_schema(db)
    
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
            "system_prompt": "You are Sarah, an experienced, professional, and slightly strict Senior engineering manager at Global Tech Inc. You are conducting a technical and behavioral English interview for a Senior Frontend Developer position. The candidate is the user. You must behave like a real interviewer: listen carefully to the candidate's answers, follow up on their specific points, challenge their assumptions, and ask deep technical or behavioral questions. Avoid generic or overly polite filler phrases. Ask one targeted question at a time and keep your replies concise (1-2 sentences). Start by welcoming the candidate and asking them to briefly introduce themselves.",
            "greeting_text": "Hello! I am Sarah, the Senior Engineering Manager at Global Tech Inc. Thank you for coming today. Let's start the interview. Can you please introduce yourself and tell me about your experience with React Native?"
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
            "system_prompt": "You are Leo, a friendly but very busy barista at the popular Metro Cafe in New York. The customer (user) wants to order coffee or breakfast. Act like a real barista: speak naturally, be fast-paced, and ask conversational follow-ups based on what they order (e.g., asking about cup size, milk options like oat or soy, sweetener preferences, and whether it is dine-in or to-go). CRITICAL: When the customer asks for the bill or you provide the final price, you MUST calculate the total price strictly and mathematically using the menu prices provided in the RAG knowledge base (including size base prices and milk/pastry surcharges). Do not hallucinate or make up estimated prices. Keep your responses short (1-2 sentences) to keep up with the queue. Start by greeting them warmly and asking what they want today.",
            "greeting_text": "Welcome to Metro Cafe! I'm Leo, what can I get started for you today?"
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
            "system_prompt": "You are David, a result-oriented and collaborative Product Manager leading an urgent product alignment meeting. The user is a developer on the team. We are discussing a critical delay in the Q3 product launch. Act like a real manager: listen to the developer's status, ask realistic follow-ups about technical blockages or resource constraints, challenge their timeline if it is too vague, and collaboratively work out an updated estimation. Keep your tone professional, constructive, and direct. Keep your responses concise (1-2 sentences) to mimic a real business meeting. Start the meeting by greeting the team, stating the agenda, and asking the developer for their update.",
            "greeting_text": "Hi team, thanks for joining. Today we are aligning on the Q3 product launch delays. Let's start with your updates. How is the React Native frontend progress?"
        }
    ]

    # 检测是否需要生成新场景（首次启动检测）
    scenes_to_create = [s for s in default_scenes if not db.query(Scene).filter(Scene.id == s["id"]).first()]
    init_status.is_first_launch = len(scenes_to_create) > 0

    total_scenes = len(default_scenes)
    for idx, scene_data in enumerate(default_scenes):
        scene_name = scene_data["name"]
        progress_base = 20 + int((idx / total_scenes) * 60)  # 20% ~ 80%
        
        existing = db.query(Scene).filter(Scene.id == scene_data["id"]).first()
        if not existing:
            # 预生成种子场景打招呼音频
            init_status.update("seeding", f"正在为「{scene_name}」合成语音...", progress_base, f"生成场景 {idx+1}/{total_scenes}")
            greeting_audio_url = None
            greeting_text = scene_data["greeting_text"]
            if greeting_text:
                filename = f"scene_greeting_{scene_data['id']}_{int(time.time())}.mp3"
                temp_dir = settings.static_audio_dir
                os.makedirs(temp_dir, exist_ok=True)
                local_path = os.path.join(temp_dir, filename)
                try:
                    text_to_speech(greeting_text, local_path)
                    greeting_audio_url = upload_audio_to_kodo(local_path, filename)
                except Exception as e:
                    print(f"[种子场景 TTS 预生成异常] 场景 {scene_data['id']} 合成失败: {e}")
                finally:
                    if greeting_audio_url and "static/audio" not in greeting_audio_url:
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except Exception:
                                pass

            scene = Scene(
                id=scene_data["id"],
                name=scene_data["name"],
                description=scene_data["description"],
                category=scene_data["category"],
                default_params=scene_data["default_params"],
                system_prompt=scene_data["system_prompt"],
                greeting_text=greeting_text,
                greeting_audio_url=greeting_audio_url,
                rag_metadata=[]
            )
            db.add(scene)
            db.commit()
            db.refresh(scene)
            
            # 初始化录入场景对应的 RAG 知识库
            seed_rag_for_scene(db, scene.id, scene)
            
            init_status.update("seeding", f"「{scene_name}」已就绪 ✓", progress_base + 15, f"完成场景 {idx+1}/{total_scenes}")
        else:
            init_status.update("seeding", f"校验「{scene_name}」...", progress_base + 10, f"检查场景 {idx+1}/{total_scenes}")
            # 如果系统提示词或问候语与预置种子不一致，进行自动校准更新，确保用户获得最佳体验
            if existing.system_prompt != scene_data["system_prompt"] or existing.greeting_text != scene_data["greeting_text"]:
                print(f"[种子自动更新] 场景 '{existing.id}' 配置与种子不一致，正在执行升级校准...")
                existing.name = scene_data["name"]
                existing.description = scene_data["description"]
                existing.system_prompt = scene_data["system_prompt"]
                existing.greeting_text = scene_data["greeting_text"]
                init_status.update("seeding", f"正在升级「{scene_name}」语音...", progress_base + 5, "重新合成问候语")
                # 重新预合成打招呼语音
                existing.greeting_audio_url = generate_and_upload_greeting_audio(existing.id, scene_data["greeting_text"])
                db.add(existing)
                db.commit()
                db.refresh(existing)
            # 如果存在但缺失问候语音频 (针对老库热升级的兼容性填充)
            elif not existing.greeting_audio_url and existing.greeting_text:
                print(f"[种子自动修复] 场景 '{existing.id}' 缺少问候语音频，正在执行补偿生成...")
                filename = f"scene_greeting_{existing.id}_{int(time.time())}.mp3"
                temp_dir = settings.static_audio_dir
                os.makedirs(temp_dir, exist_ok=True)
                local_path = os.path.join(temp_dir, filename)
                try:
                    init_status.update("seeding", f"正在修复「{scene_name}」语音...", progress_base + 5, "补偿生成问候语")
                    text_to_speech(existing.greeting_text, local_path)
                    existing.greeting_audio_url = upload_audio_to_kodo(local_path, filename)
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)
                    print(f"[种子自动修复] 场景 '{existing.id}' 问候语语音已完美填充！")
                except Exception as e:
                    print(f"[种子补偿生成异常] 场景 {existing.id} 合成失败: {e}")
                finally:
                    if existing.greeting_audio_url and "static/audio" not in existing.greeting_audio_url:
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except Exception:
                                pass
                                
            # 种子检测与增量填充该场景的 RAG 知识库
            seed_rag_for_scene(db, existing.id, existing)
    db.commit()

# ══════════════════════════════════════════════════════════════════════════════
# 初始化状态查询接口（供前端 Splash 页面消费）
# ══════════════════════════════════════════════════════════════════════════════
from fastapi import APIRouter as _AR
_init_router = _AR()

@_init_router.get("/init-status")
def get_init_status():
    """返回后端初始化进度，前端 Splash 页面轮询此接口以决定何时放行"""
    return init_status.to_dict()

app.include_router(_init_router, prefix="/api", tags=["初始化状态"])

# 在服务启动时自动初始化表与种子场景数据
@app.on_event("startup")
def startup_event():
    def run_db_initialization():
        db = next(get_db())
        try:
            # 阶段 1：数据库 Schema 升级
            init_status.update("schema", "正在升级数据库结构...", 5, "检查表字段")
            check_and_upgrade_database_schema(db)
            init_status.update("schema", "数据库结构已就绪 ✓", 15, "")
            
            # 阶段 2：注入种子场景数据（含 TTS 生成，首次启动最耗时）
            init_status.update("seeding", "正在初始化练习场景...", 20, "检查种子数据")
            seed_default_scenes(db)
            init_status.update("seeding", "所有场景已就绪 ✓", 85, "")
            
            # 阶段 3：用户注册
            init_status.update("user", "正在注册默认用户...", 90, "")
            test_user = db.query(User).filter(User.username == "default_user").first()
            if not test_user:
                db.add(User(username="default_user"))
                db.commit()
            init_status.update("user", "用户已就绪 ✓", 95, "")
            
            # 全部完成
            init_status.update("done", "初始化完成，欢迎使用 EchoTalk！", 100, "")
            print("[初始化] 所有后端数据初始化完成")
        except Exception as e:
            print(f"[种子填充异常] 数据初始化失败: {e}")
            init_status.set_error(str(e))
            # 即使初始化失败，也标记为 done 让前端不会卡死
            init_status.update("done", "初始化完成（部分场景可能不可用）", 100, "")
        finally:
            db.close()

    # 使用后台线程进行数据库升级与种子场景数据生成，避免阻塞主线程启动
    threading.Thread(target=run_db_initialization, daemon=True).start()

if __name__ == "__main__":
    # 本地启动端口设为 8000
    port = int(os.environ.get("ECHOTALK_BACKEND_PORT", "8000"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
