"""knowledge 数据模型。"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timeutil import utcnow

class Document(Base):
    """场景知识资料表：源文件存本地 storage/scenes/{id}/knowledge/，元数据入库。"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)  # 主键：资料 ID，自增
    scene_id = Column(String(50), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属场景
    owner_id = Column(Integer, ForeignKey("users.id"))  # 上传者：内置资料为 NULL
    filename = Column(String(255), nullable=False)  # 原始文件名：导出时还原
    content_type = Column(String(100))  # MIME 类型
    chunk_count = Column(Integer, nullable=False, default=0)  # 分块数量
    visibility = Column(String(10), nullable=False, default="user")  # 文件级缺省可见性：user/ai_only
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 上传时间：UTC


class Chunk(Base):
    """知识分块表：解析后的文本块；向量索引为运行时产物（阶段 3 Hybrid RAG）。"""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)  # 主键：分块 ID，自增
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属资料
    scene_id = Column(String(50), nullable=False, index=True)  # 场景冗余：便于按场景隔离与重建
    section = Column(String(100))  # 分节名：md 标题或文件名
    visibility = Column(String(10), nullable=False, default="user")  # 分节可见性：user/ai_only
    ordinal = Column(Integer, nullable=False)  # 块序号：同一资料内从 0 递增
    text = Column(Text, nullable=False)  # 分块文本内容


class PersonalDocument(Base):
    """个人工作区资料（阶段二）：跨场景复用，按 owner 隔离，与场景资料互不隶属。"""

    __tablename__ = "personal_documents"

    id = Column(Integer, primary_key=True)  # 主键：资料 ID，自增
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属用户：工作区隔离边界
    filename = Column(String(255), nullable=False)  # 原始文件名：同名覆盖即更新
    content_type = Column(String(100))  # MIME 类型
    chunk_count = Column(Integer, nullable=False, default=0)  # 分块数量
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 上传时间：UTC


class PersonalChunk(Base):
    """个人资料分块：解析产物；个人资料不做可见性区分，全部用户可见。"""

    __tablename__ = "personal_chunks"

    id = Column(Integer, primary_key=True)  # 主键：分块 ID，自增
    document_id = Column(Integer, ForeignKey("personal_documents.id", ondelete="CASCADE"), nullable=False, index=True)  # 所属资料
    section = Column(String(100))  # 分节名：md 标题或文件名
    visibility = Column(String(10), nullable=False, default="user")  # 个人资料统一 user
    ordinal = Column(Integer, nullable=False)  # 块序号：同一资料内从 0 递增
    text = Column(Text, nullable=False)  # 分块文本内容


class ChunkEmbedding(Base):
    """场景分块向量（Hybrid RAG）：float32 小端打包存 BLOB，余弦在应用层计算。

    语料规模小（单场景几十~几百块），无需向量数据库；换嵌入模型须 reindex 全量重建。
    """

    __tablename__ = "chunk_embeddings"

    id = Column(Integer, primary_key=True)  # 主键：自增
    chunk_id = Column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)  # 分块：一对一
    model = Column(String(64), nullable=False)  # 生成模型：空间不兼容，换模型必须重刷
    embedding = Column(LargeBinary, nullable=False)  # float32 × DIM 的二进制
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 生成时间：UTC


class PersonalChunkEmbedding(Base):
    """个人分块向量：与场景分块向量同构，按 owner 的资料检索使用。"""

    __tablename__ = "personal_chunk_embeddings"

    id = Column(Integer, primary_key=True)  # 主键：自增
    chunk_id = Column(Integer, ForeignKey("personal_chunks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)  # 分块：一对一
    model = Column(String(64), nullable=False)  # 生成模型
    embedding = Column(LargeBinary, nullable=False)  # float32 × DIM 的二进制
    created_at = Column(DateTime, default=utcnow, nullable=False)  # 生成时间：UTC


