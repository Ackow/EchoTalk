"""多角色辩论会话与轮次数据模型。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.core.database import Base
from app.core.timeutil import utcnow


class DebateTopic(Base):
    """辩题库：包含内置辩题与用户/管理员创建的自定义辩题。"""

    __tablename__ = "debate_topics"

    id = Column(String(64), primary_key=True)
    title_zh = Column(String(180), nullable=False)
    motion_en = Column(Text, nullable=False)
    category = Column(String(32), nullable=False, default="tech", index=True)
    category_label = Column(String(48), nullable=False, default="科技伦理")
    difficulty = Column(String(24), nullable=False, default="intermediate")
    difficulty_label = Column(String(24), nullable=False, default="进阶")
    duration = Column(String(32), nullable=False, default="8 分钟")
    pro_summary = Column(Text, nullable=False, default="")
    con_summary = Column(Text, nullable=False, default="")
    background_context = Column(Text, nullable=False, default="")
    key_expressions = Column(JSON, nullable=False, default=list)
    default_style = Column(String(24), nullable=False, default="balanced")
    scene_type = Column(String(24), nullable=False, default="debate")  # debate | panel
    user_role_label = Column(String(64), nullable=False, default="候选人 / 主讲人")
    roles_config = Column(JSON, nullable=False, default=list)
    stages_config = Column(JSON, nullable=False, default=list)
    opponent_name = Column(String(64), nullable=False, default="Sonia")
    opponent_title = Column(String(64), nullable=False, default="对手辩手")
    opponent_persona = Column(Text, nullable=False, default="")
    opponent_voice = Column(String(32), nullable=False, default="sonia")
    opponent_avatar_id = Column(String(32), nullable=False, default="sarah_2d")
    knowledge_doc_ids = Column(JSON, nullable=False, default=list)
    cover_path = Column(String(512), nullable=True)
    tools_config = Column(JSON, nullable=False, default=list)
    status = Column(String(24), nullable=False, default="private")  # private | published
    likes_count = Column(Integer, nullable=False, default=0)
    favorites_count = Column(Integer, nullable=False, default=0)
    is_builtin = Column(Boolean, nullable=False, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class DebateTopicReaction(Base):
    """辩题社区互动记录（点赞与收藏）。"""

    __tablename__ = "debate_topic_reactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String(64), ForeignKey("debate_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)  # like | favorite
    created_at = Column(DateTime, nullable=False, default=utcnow)


class DebateSession(Base):
    """多角色辩论会话：记录辩题、立场、实时胜率、四维能力分与最终裁决。"""

    __tablename__ = "debate_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(String(64), nullable=False, index=True)
    topic_title = Column(String(180), nullable=False)
    motion_en = Column(Text, nullable=False)
    category = Column(String(32), nullable=False, default="tech")
    difficulty = Column(String(24), nullable=False, default="intermediate")
    scene_type = Column(String(24), nullable=False, default="debate")  # debate | panel
    user_side = Column(String(8), nullable=False, default="pro")  # pro | con
    difficulty_level = Column(String(24), nullable=False, default="balanced")  # supportive | balanced | sharp
    stage_index = Column(Integer, nullable=False, default=0)
    turn_count = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="active")  # active | finished
    win_rate = Column(Integer, nullable=False, default=54)
    combo_count = Column(Integer, nullable=False, default=1)
    scores_json = Column(JSON, nullable=False)
    verdict_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class DebateTurn(Base):
    """辩论发言轮次：包含主持人、我方、对手辩手与特邀评委发言。"""

    __tablename__ = "debate_turns"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("debate_sessions.id"), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False, default=1)
    stage_label = Column(String(48), nullable=False, default="开篇立论")
    role = Column(String(20), nullable=False)  # moderator | interviewer | user | opponent | judge
    speaker = Column(String(64), nullable=False)
    role_title = Column(String(64), nullable=False, default="")
    avatar_id = Column(String(32), nullable=False, default="")
    voice_style = Column(String(32), nullable=False, default="brian")
    is_voice = Column(Boolean, nullable=False, default=False)
    duration = Column(Integer, nullable=True)
    en_text = Column(Text, nullable=False)
    zh_text = Column(Text, nullable=False, default="")
    evaluation_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
