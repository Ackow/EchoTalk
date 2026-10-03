"""场景包接口（控制器层）：设计稿场景包方案 §7 与 v1.2 §13 路由。

只负责解析请求、调用服务层（app/services/scene_service.py）、格式化响应，
不含业务逻辑；权限、校验、编排规则全部在服务层。
"""
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_user
from app.core.errors import AppError
from app.models import User
from app.services import scene_service

router = APIRouter(prefix="/scenes", tags=["场景包"])


async def read_package_body(request: Request) -> dict[str, Any]:
    """读取请求体中的完整包字段；非法 JSON 提前给出可解释错误。"""
    try:
        data = await request.json()
    except Exception as exc:
        raise AppError("请求体不是有效的 JSON") from exc
    if not isinstance(data, dict):
        raise AppError("请求体需要是场景包的键值映射结构")
    return data


# ---- 列表 / 模板 / 校验 / 导入（固定路径，需在 /{scene_id} 之前注册） -------

@router.get("")
def list_scenes(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """场景列表：builtin + 本人全部 + 他人已发布（游客仅 builtin）。"""
    return {"items": scene_service.list_scenes(db, user)}


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    """内置模板列表：「从模板创建」入口的数据源。"""
    return {"items": scene_service.list_templates(db)}


@router.post("/validate")
async def validate_package(request: Request):
    """干跑校验：编辑器实时反馈；成功返回 valid，失败返回 422 字段级错误。"""
    data = await read_package_body(request)
    scene_service.validate(data)
    return {"valid": True}


@router.post("/import")
async def import_scene(
    file: UploadFile = File(...),
    resolve: str | None = Query(default=None, description="冲突处理：overwrite / rename"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导入 v2 场景包 ZIP；ID 冲突时要求显式选择覆盖或改名（§8.2）。"""
    if not (file.filename or "").lower().endswith(".zip"):
        raise AppError("请上传 .zip 场景包文件")
    content = await file.read()
    row, action = scene_service.import_package(db, user, content, resolve)
    from app.scenes import registry

    return {"scene": registry.summary(row), "action": action}


@router.post("/from-template", status_code=201)
async def create_from_template(
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从内置模板复制创建自定义场景：内置只读的替代路径。"""
    return scene_service.create_from_template(db, user, payload.get("template_id"), payload.get("new_id"))


@router.post("", status_code=201)
async def create_scene(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建自定义场景：body = 完整包字段；保存前全量校验（默认本地私有）。"""
    data = await read_package_body(request)
    return scene_service.create_scene(db, user, data)


# ---- 场景详情与生命周期 -----------------------------------------------------

@router.get("/{scene_id}")
def get_scene(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """场景详情：完整包 + 资料元数据 + 社区统计（ai_only 分节内容不随详情下发）。"""
    return scene_service.get_scene(db, scene_id, user)


@router.put("/{scene_id}")
async def update_scene(
    scene_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新自定义场景：builtin 返回 409；id 不允许变更。"""
    data = await read_package_body(request)
    return scene_service.update_scene(db, user, scene_id, data)


@router.post("/{scene_id}/duplicate", status_code=201)
def duplicate_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """复制场景为自定义副本（内置场景同样可复制）。"""
    return scene_service.duplicate_scene(db, user, scene_id)


@router.delete("/{scene_id}")
def delete_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自定义场景：资料源文件与 documents/chunks 一并清除。"""
    return {"deleted": scene_service.delete_scene(db, user, scene_id)}


@router.get("/{scene_id}/export")
def export_scene(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """导出 v2 ZIP（manifest + scene.yaml + knowledge 源文件）；非作者导出计入下载量。"""
    content = scene_service.export_package(db, scene_id, user)
    filename = f"echotalk_scene_{scene_id}.zip"
    return StreamingResponse(
        iter([content]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- 封面图 -----------------------------------------------------------------

@router.post("/{scene_id}/cover", status_code=201)
async def upload_cover(
    scene_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设置场景封面（仅作者）：jpg / png / webp，上限 5 MB。"""
    relative = scene_service.set_cover(db, user, scene_id, file.filename, await file.read())
    return {"cover_path": relative}


@router.get("/{scene_id}/cover")
def get_cover(scene_id: str, db: Session = Depends(get_db)):
    """读取封面图片：无需登录，卡片/详情直接以 <img> 引用。"""
    path = scene_service.get_cover_file(db, scene_id)
    if path is None:
        raise AppError("场景未设置封面", code="SCENE_NO_COVER", status_code=404)
    return FileResponse(path)


@router.delete("/{scene_id}/cover")
def remove_cover(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除封面（仅作者）：文件与引用一并清除。"""
    removed = scene_service.remove_cover(db, user, scene_id)
    return {"removed": removed}


# ---- 发布与社区互动 ---------------------------------------------------------

@router.post("/{scene_id}/publish")
def publish_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布自定义场景：所有用户可见、可下载；作者保留编辑权。"""
    return scene_service.publish(db, user, scene_id)


@router.post("/{scene_id}/unpublish")
def unpublish_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消发布：回到本地私有，仅作者可见；统计保留。"""
    return scene_service.unpublish(db, user, scene_id)


@router.post("/{scene_id}/like")
def like_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """点赞/取消点赞（去重：一人一票）。"""
    return scene_service.like(db, user, scene_id)


@router.post("/{scene_id}/favorite")
def favorite_scene(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏/取消收藏（去重：一人一票）。"""
    return scene_service.favorite(db, user, scene_id)


# ---- 场景知识资料 -----------------------------------------------------------

@router.post("/{scene_id}/knowledge", status_code=201)
async def upload_knowledge(
    scene_id: str,
    file: UploadFile = File(...),
    visibility: str = Query(default="user", description="文件级可见性：user / ai_only"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传资料文件：解析 → 分块 → 入库（设计稿 §7 替代 1.0 的 /{id}/upload）。"""
    if visibility not in ("user", "ai_only"):
        raise AppError("visibility 必须为 user 或 ai_only", code="SCENE_UNSUPPORTED_FILE")
    document = scene_service.upload_knowledge(db, user, scene_id, file.filename, await file.read(), file.content_type, visibility)
    return {
        "id": document.id,
        "filename": document.filename,
        "chunk_count": document.chunk_count,
        "visibility": document.visibility,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


@router.get("/{scene_id}/knowledge")
def get_visible_knowledge(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """学习者可见分节内容（对话页参考面板数据源）。"""
    return scene_service.visible_knowledge(db, scene_id, user)


@router.get("/{scene_id}/knowledge/sections")
def get_section_overview(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """全分节概览（含 ai_only）：管理界面的数据源。"""
    return scene_service.section_overview(db, scene_id, user)


@router.get("/{scene_id}/knowledge/documents")
def list_scene_documents(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """资料文件级列表（含每文件分节分组）：知识工作区管理界面数据源。"""
    return scene_service.document_overview(db, scene_id, user)


@router.get("/{scene_id}/knowledge/documents/{document_id}/chunks")
def get_document_chunks(
    scene_id: str,
    document_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """资料的分块明细（含正文全文）：知识工作区查看数据源。"""
    return scene_service.document_chunks(db, scene_id, document_id, user)


@router.get("/{scene_id}/knowledge/documents/{document_id}/source")
def get_document_source(
    scene_id: str,
    document_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """资料源文件全文（文本类可编辑，pdf 返回 editable=false）：源文件编辑数据源。"""
    return scene_service.document_source(db, scene_id, document_id, user)


@router.put("/{scene_id}/knowledge/documents/{document_id}/source")
async def put_document_source(
    scene_id: str,
    document_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑源文件并重新解析分块：覆盖写盘 → 同名重建 documents/chunks（§编辑模型）。"""
    data = await read_package_body(request)
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise AppError("text 不能为空", code="SCENE_UNSUPPORTED_FILE")
    return scene_service.update_document_source(db, user, scene_id, document_id, text.strip())


@router.get("/{scene_id}/knowledge/graph")
def get_scene_graph(
    scene_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """实体关系图谱（阶段三，规则抽取）：文件-分节从属 + 跨文件分节相关边。"""
    return scene_service.scene_graph(db, scene_id, user)


@router.get("/{scene_id}/knowledge/search")
def search_scene_knowledge(
    scene_id: str,
    q: str,
    top_k: int = 4,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识混合检索：ngram 全文关键词 + 向量余弦（RRF 融合）；未配置嵌入 key 时纯关键词。"""
    if not q.strip():
        raise AppError("检索词不能为空", code="SCENE_UNSUPPORTED_FILE")
    return scene_service.search_knowledge(db, user, scene_id, q.strip(), max(1, min(top_k, 20)))


@router.post("/{scene_id}/knowledge/reindex")
def reindex_scene_knowledge(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为场景分块补建向量（上传时嵌入失败 / 换嵌入模型后的全量重建）。"""
    return scene_service.reindex_knowledge(db, user, scene_id)


@router.get("/{scene_id}/knowledge/lightrag")
def lightrag_scene_knowledge(
    scene_id: str,
    q: str,
    mode: str = "mix",
    top_k: int = 6,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """场景知识图谱检索（LightRAG）：返回实体/关系/分块检索上下文，不生成答案。"""
    if not q.strip():
        raise AppError("检索词不能为空", code="SCENE_UNSUPPORTED_FILE")
    try:
        context = scene_service.lightrag_scene_query(db, user, scene_id, q.strip(), mode, max(1, min(top_k, 20)))
    except ValueError as exc:
        raise AppError(str(exc), code="SCENE_UNSUPPORTED_FILE") from exc
    return {"query": q.strip(), "mode": mode, "context": context}


@router.post("/{scene_id}/knowledge/lightrag/rebuild")
def lightrag_scene_rebuild(
    scene_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全量重建场景图谱索引（后台执行：LLM 实体抽取耗时数十秒/篇）。"""
    return scene_service.lightrag_scene_rebuild(db, user, scene_id)


@router.patch("/{scene_id}/knowledge/sections/{section_name}")
def patch_section_visibility(
    scene_id: str,
    section_name: str,
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改分节可见性（user ↔ ai_only）。"""
    visibility = payload.get("visibility")
    if visibility not in ("user", "ai_only"):
        raise AppError("visibility 必须为 user 或 ai_only", code="SCENE_UNSUPPORTED_FILE")
    return scene_service.patch_section_visibility(db, user, scene_id, section_name, visibility)


@router.delete("/{scene_id}/knowledge/{document_id}")
def delete_knowledge(
    scene_id: str,
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除单个资料（1.0 只能全清，2.0 支持按文件删除）。"""
    document = scene_service.delete_knowledge(db, user, scene_id, document_id)
    return {"deleted": document.filename}
