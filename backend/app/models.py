from sqlalchemy import Column, Boolean, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    """
    用户表：记录口语练习用户的基本信息。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False) # 用户名
    created_at = Column(DateTime, default=datetime.utcnow) # 创建时间

    # 关联关系
    dialogues = relationship("DialogueHistory", back_populates="user")


class Scene(Base):
    """
    场景表：记录口语演练场景配置（如面试、点餐等），支持热插拔插件与RAG知识库配置。
    """
    __tablename__ = "scenes"

    id = Column(String(50), primary_key=True, index=True) # 场景ID (例如 'interview', 'ordering')
    name = Column(String(100), nullable=False) # 场景名称
    description = Column(Text, nullable=True) # 场景描述
    category = Column(String(50), default="custom") # 场景分类
    
    # 动态参数：天气、对方性格、对话限制等
    default_params = Column(JSON, default=dict)
    
    # AI 角色的初始 System Prompt
    system_prompt = Column(Text, nullable=False)
    
    # RAG 文档库元数据：记录用户上传的文件列表信息
    rag_metadata = Column(JSON, default=list)
    
    # 场景的第一句打招呼首发文本，用于持久化问候语
    greeting_text = Column(Text, nullable=True, default="Hello! Let's start practicing.")
    
    # 场景的第一句打招呼首发音频托管地址，预先生成好以加速会话启动
    greeting_audio_url = Column(String(255), nullable=True)

    # 关联关系
    dialogues = relationship("DialogueHistory", back_populates="scene")


class DialogueHistory(Base):
    """
    会话历史表：记录每一次练习会话的整体评估和时间段。
    """
    __tablename__ = "dialogue_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # 外键关联用户
    scene_id = Column(String(50), ForeignKey("scenes.id"), nullable=False) # 外键关联场景
    start_time = Column(DateTime, default=datetime.utcnow) # 开始时间
    end_time = Column(DateTime, nullable=True) # 结束时间
    overall_score = Column(Float, nullable=True) # 综合评分
    speaking_style = Column(String(20), nullable=True, default="colloquial") # 说话风格: 'colloquial' (口语化) 或 'formal' (书面化)
    accent = Column(String(10), nullable=True, default="us") # 发音口音: 'us' (美音) 或 'uk' (英音)
    is_finished = Column(Boolean, default=False, nullable=False) # 会话是否由 AI 判定为结束

    # 关联关系
    user = relationship("User", back_populates="dialogues")
    scene = relationship("Scene", back_populates="dialogues")
    turns = relationship("DialogueTurn", back_populates="dialogue_history", cascade="all, delete-orphan")


class DialogueTurn(Base):
    """
    对话明细表：记录单次会话中的每一轮交互（用户语音/AI回应），包括七牛云音频地址、发音评分及语法纠错。
    """
    __tablename__ = "dialogue_turns"

    id = Column(Integer, primary_key=True, index=True)
    dialogue_history_id = Column(Integer, ForeignKey("dialogue_histories.id"), nullable=False) # 关联会话ID
    
    role = Column(String(20), nullable=False) # 角色: 'user' (用户) 或 'assistant' (AI助手)
    timestamp = Column(DateTime, default=datetime.utcnow) # 对话发生时间
    
    text = Column(Text, nullable=False) # 转录出的文本
    
    audio_url = Column(String(255), nullable=True) # 七牛云 Kodo 音频存储地址 (云端回放)
    audio_url_us = Column(String(255), nullable=True) # 美式发音音频存储地址
    audio_url_uk = Column(String(255), nullable=True) # 英式发音音频存储地址
    
    # 发音测评结果 JSON：包含综合分、准确度、流利度、完整度、音素等
    pronunciation_score = Column(JSON, nullable=True)
    
    # 语法纠错与表达改进建议 JSON：包含原文错误、修改意见及理由
    grammar_correction = Column(JSON, nullable=True)

    # 关联关系
    dialogue_history = relationship("DialogueHistory", back_populates="turns")
