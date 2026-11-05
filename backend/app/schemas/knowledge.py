"""练习页面使用的知识点结构，只包含允许向学习者展示的正文。"""
from pydantic import BaseModel, Field


class KnowledgeChunk(BaseModel):
    id: int
    ordinal: int
    text: str


class KnowledgeSection(BaseModel):
    name: str
    chunks: list[KnowledgeChunk] = Field(default_factory=list)


class KnowledgeDocument(BaseModel):
    id: int
    filename: str
    sections: list[KnowledgeSection] = Field(default_factory=list)


class PracticeKnowledgeResponse(BaseModel):
    scene_id: str
    documents: list[KnowledgeDocument] = Field(default_factory=list)
