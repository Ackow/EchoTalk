"""个人工作区资料接口（阶段二）：跨场景资料的上传 / 管理 / 分块 / 源文件编辑。

全部端点要求登录，owner 隔离（只能看到与操作自己的资料）；
个人资料不做 ai/user 可见性区分（全部对用户可见），接口层无可见性参数。
"""
from typing import Any

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models import User
from app.services import scene_service

router = APIRouter(prefix="/knowledge/personal", tags=["个人资料"])


@router.get("")
def list_personal_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料文件级概览（含分节分组）。"""
    return scene_service.personal_overview(db, user)


@router.post("", status_code=201)
async def upload_personal_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传个人资料：解析 → 分块 → 入库（同名覆盖即更新）。"""
    document = scene_service.upload_personal(db, user, file.filename, await file.read(), file.content_type)
    return document


@router.get("/search")
def search_personal_knowledge(
    q: str,
    top_k: int = 4,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料混合检索：ngram 全文关键词 + 向量余弦（RRF 融合）。"""
    if not q.strip():
        raise AppError("检索词不能为空", code="SCENE_UNSUPPORTED_FILE")
    return scene_service.search_personal_knowledge(db, user, q.strip(), max(1, min(top_k, 20)))


@router.post("/reindex")
def reindex_personal_knowledge(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为本人个人资料分块补建向量。"""
    return scene_service.reindex_personal_knowledge(db, user)


@router.get("/lightrag")
def lightrag_personal_knowledge(
    q: str,
    mode: str = "mix",
    top_k: int = 6,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料图谱检索（LightRAG）：返回实体/关系/分块检索上下文，不生成答案。"""
    if not q.strip():
        raise AppError("检索词不能为空", code="SCENE_UNSUPPORTED_FILE")
    try:
        context = scene_service.lightrag_personal_query(db, user, q.strip(), mode, max(1, min(top_k, 20)))
    except ValueError as exc:
        raise AppError(str(exc), code="SCENE_UNSUPPORTED_FILE") from exc
    return {"query": q.strip(), "mode": mode, "context": context}


@router.post("/lightrag/rebuild")
def lightrag_personal_rebuild(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全量重建本人个人资料图谱索引（后台执行：LLM 实体抽取耗时数十秒/篇）。"""
    return scene_service.lightrag_personal_rebuild(db, user)


@router.get("/graph")
def get_personal_graph(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料实体关系图谱（规则抽取，与场景图谱同一套逻辑）。"""
    return scene_service.personal_graph(db, user)


@router.get("/documents/{document_id}/chunks")
def get_personal_chunks(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料的分块明细（只读）。"""
    return scene_service.personal_chunks(db, user, document_id)


@router.get("/documents/{document_id}/source")
def get_personal_source(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """个人资料源文件全文（文本类可编辑，pdf 返回 editable=false）。"""
    return scene_service.personal_source(db, user, document_id)


@router.put("/documents/{document_id}/source")
async def put_personal_source(
    document_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑个人资料源文件并重新解析分块。"""
    try:
        data = await request.json()
    except Exception as exc:
        raise AppError("请求体不是有效的 JSON") from exc
    text = data.get("text") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise AppError("text 不能为空", code="SCENE_UNSUPPORTED_FILE")
    return scene_service.update_personal_source(db, user, document_id, text.strip())


@router.delete("/documents/{document_id}")
def remove_personal_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除个人资料（源文件与分块一并清除）。"""
    return scene_service.delete_personal(db, user, document_id)
