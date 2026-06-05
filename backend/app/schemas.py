from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- 用户（User）相关模式 ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- 场景（Scene）相关模式 ---
class SceneBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str = "custom"
    default_params: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: str

class SceneCreate(SceneBase):
    pass

class SceneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    default_params: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    rag_metadata: Optional[List[Dict[str, Any]]] = None

class SceneResponse(SceneBase):
    rag_metadata: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True


# --- 会话单轮明细（Dialogue Turn）相关模式 ---
class DialogueTurnResponse(BaseModel):
    id: int
    dialogue_history_id: int
    role: str
    timestamp: datetime
    text: str
    audio_url: Optional[str] = None
    pronunciation_score: Optional[Dict[str, Any]] = None
    grammar_correction: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# --- 会话历史（Dialogue History）相关模式 ---
class DialogueHistoryBase(BaseModel):
    user_id: int
    scene_id: str

class DialogueStartRequest(DialogueHistoryBase):
    custom_params: Optional[Dict[str, Any]] = None # 会话开始时可定制的动态参数，会覆盖场景默认值

class DialogueHistoryResponse(BaseModel):
    id: int
    user_id: int
    scene_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    overall_score: Optional[float] = None
    turns: List[DialogueTurnResponse] = []

    class Config:
        from_attributes = True
