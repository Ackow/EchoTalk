import os
import time
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models import DialogueHistory, Scene, User, DialogueTurn
from app.schemas import DialogueHistoryResponse, DialogueStartRequest, DialogueTurnResponse
from app.services.pipeline import run_dialogue_turn_pipeline
from app.services.tts import text_to_speech
from app.services.storage import upload_audio_to_kodo

router = APIRouter()

@router.post("/start", response_model=DialogueHistoryResponse, status_code=status.HTTP_201_CREATED)
def start_dialogue(req: DialogueStartRequest, db: Session = Depends(get_db)):
    """
    启动一轮新的口语交互练习会话。如果指定了 custom_params，将覆盖默认场景的属性配置。
    并在启动时同步生成第一句场景问候语的文本及 TTS 托管语音，作为第 0 轮对话存入数据库。
    """
    # 验证场景与用户是否存在
    scene = db.query(Scene).filter(Scene.id == req.scene_id).first()
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"场景 '{req.scene_id}' 不存在"
        )
        
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{req.user_id}' 未注册"
        )

    # 创建会话历史记录
    history = DialogueHistory(
        user_id=req.user_id,
        scene_id=req.scene_id,
        turns=[]
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    # 1. 组合默认参数与传入的 custom_params 进行欢迎语参数插值渲染
    params = dict(scene.default_params or {})
    if req.custom_params:
        params.update(req.custom_params)
        
    greeting_rendered = scene.greeting_text or "Hello! Let's start practicing."
    for k, v in params.items():
        placeholder = f"{{{k}}}"
        if placeholder in greeting_rendered:
            greeting_rendered = greeting_rendered.replace(placeholder, str(v))
            
    # 2. 检查渲染后的打招呼文本是否与原场景问候语完全等值
    # 如果完全等值且数据库中已存在预合成音频地址，则直接复用，免去合成耗时以实现会话启动零延迟！
    if greeting_rendered == scene.greeting_text and scene.greeting_audio_url:
        greeting_audio_url = scene.greeting_audio_url
        print(f"[会话启动加速] 问候语文本未改变，成功直通复用预合成音轨: {greeting_audio_url}")
    else:
        # 否则 (例如因 custom_params 发生了变量替换)，降级为实时重新合成
        print(f"[会话启动降级] 问候语文本发生变量插值改变，正在实时合成定制音轨...")
        ai_audio_filename = f"greeting_{history.id}_{int(time.time())}.mp3"
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(backend_dir, "static", "audio")
        os.makedirs(temp_dir, exist_ok=True)
        local_path = os.path.join(temp_dir, ai_audio_filename)
        
        try:
            text_to_speech(greeting_rendered, local_path)
            greeting_audio_url = upload_audio_to_kodo(local_path, ai_audio_filename)
        except Exception as e:
            print(f"[问候语 TTS 合成异常警告] {str(e)}。降级为无语音。")
            greeting_audio_url = None
        finally:
            # 物理清理本地冗余文件
            if greeting_audio_url and "static/audio" not in greeting_audio_url:
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass

    # 3. 创建第 0 轮 DialogueTurn 写入数据库
    turn0 = DialogueTurn(
        dialogue_history_id=history.id,
        role="assistant",
        text=greeting_rendered,
        audio_url=greeting_audio_url,
        pronunciation_score=None,
        grammar_correction=None
    )
    db.add(turn0)
    db.commit()
    db.refresh(history)
    
    return history

@router.get("/{history_id}", response_model=DialogueHistoryResponse)
def read_dialogue(history_id: int, db: Session = Depends(get_db)):
    """
    查询指定会话的完整历史详情，包括每一轮的语音 URL、发音评分及语法纠错结果。
    """
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话记录 ID '{history_id}' 未找到"
        )
    return history

@router.get("/", response_model=List[DialogueHistoryResponse])
def list_dialogues(user_id: int, db: Session = Depends(get_db)):
    """
    获取指定用户的所有练习会话历史记录列表，按开始时间倒序排列
    """
    return db.query(DialogueHistory)\
             .filter(DialogueHistory.user_id == user_id)\
             .order_by(DialogueHistory.start_time.desc())\
             .all()

@router.post("/{history_id}/turn", response_model=List[DialogueTurnResponse])
async def create_dialogue_turn(
    history_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    处理一轮口语交互对话：上传用户音频 ➡️ ASR ➡️ RAG ➡️ 脱敏 ➡️ 并行(发音评测 + LLM 对话) ➡️ TTS ➡️ 托管上传 ➡️ 保存入库。
    返回当前发生的两轮交互（用户轮次 + AI助手轮次）的列表。
    """
    # 检查会话记录是否存在
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 ID '{history_id}' 不存在"
        )
        
    # 保存上传的音频文件至本地临时文件进行处理
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "audio", "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 保持扩展名为原始扩展名或默认 .wav
    ext = os.path.splitext(file.filename)[1] or ".wav"
    temp_file_path = os.path.join(temp_dir, f"upload_{history_id}_{int(time.time())}{ext}")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 运行 Pipeline 并获取轮次数据库记录
        user_turn, assistant_turn = await run_dialogue_turn_pipeline(db, history_id, temp_file_path)
        
        return [user_turn, assistant_turn]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline 运行失败: {str(e)}"
        )
    finally:
        # 清理临时上传的音频文件
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

@router.post("/{history_id}/settle", response_model=DialogueHistoryResponse)
def settle_dialogue(
    history_id: int,
    db: Session = Depends(get_db)
):
    """
    会话终点结算：统计语法纠错和评分汇总，更新历史表中的 overall_score 和 end_time。
    """
    history = db.query(DialogueHistory).filter(DialogueHistory.id == history_id).first()
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 ID '{history_id}' 不存在"
        )
        
    # 提取属于该会话的所有 user 轮次的发音总分
    turns = db.query(DialogueTurn).filter(
        DialogueTurn.dialogue_history_id == history_id,
        DialogueTurn.role == "user"
    ).all()
    
    scores = []
    for t in turns:
        if t.pronunciation_score and isinstance(t.pronunciation_score, dict):
            total_score = t.pronunciation_score.get("total_score")
            if total_score is not None:
                scores.append(float(total_score))
                
    # 汇总计算平均发音总分，若无则默认为 0.0
    overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    
    history.overall_score = overall_score
    history.end_time = datetime.utcnow()
    
    db.commit()
    db.refresh(history)
    
    return history
