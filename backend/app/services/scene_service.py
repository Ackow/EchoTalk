"""场景包业务服务（服务层）：权限校验、生命周期、导入导出与社区互动的编排。

控制器层（endpoints/scenes.py）只解析请求与格式化响应；
所有业务规则集中在此，供 API 与未来其他入口（CLI、任务队列）复用。
"""
import copy
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import Chunk, Document, Scene, User
from app.scenes import knowledge as knowledge_svc
from app.scenes import graph as graph_svc
from app.scenes import packaging, registry, social
from app.scenes.errors import (
    SceneBuiltinReadonlyError,
    SceneIdConflictError,
    SceneNotFoundError,
)


# ---- 加载与权限 ------------------------------------------------------------

def load_scene(db: Session, scene_id: str) -> Scene:
    """按 id 加载场景；不存在抛 404。"""
    if not scene_id:
        raise SceneNotFoundError(scene_id)
    row = db.get(Scene, scene_id)
    if row is None:
        raise SceneNotFoundError(scene_id)
    return row


def ensure_visible(row: Scene, user: User | None) -> None:
    """可见性：builtin 全员；本人全部；他人仅 published。"""
    if not social.visible_to(row, user.id if user else None):
        raise SceneNotFoundError(row.id)


def ensure_writable(row: Scene, user: User) -> None:
    """可写性：builtin 只读；custom/imported 仅作者本人。"""
    if row.source == "builtin":
        raise SceneBuiltinReadonlyError(row.id)
    if row.author_id != user.id:
        raise AppError("只能修改自己创建的场景", code="SCENE_FORBIDDEN", status_code=403)


def validate(data: dict[str, Any]):
    """干跑校验（编辑器实时反馈）；非法时抛 422（含字段级详情）。"""
    return registry.validate(data)


# ---- 列表与详情 -------------------------------------------------------------

def list_scenes(db: Session, user: User | None) -> list[dict[str, Any]]:
    """可见场景列表：builtin + 本人全部 + 他人已发布；附带社区统计。"""
    rows = db.query(Scene).order_by(Scene.source, Scene.created_at).all()
    visible = [row for row in rows if social.visible_to(row, user.id if user else None)]
    stats = social.stats_map(db, [row.id for row in visible], user.id if user else None)
    items = []
    for row in visible:
        summary = registry.summary(row)
        summary["stats"] = stats.get(row.id)
        items.append(summary)
    return items


def scene_detail(db: Session, row: Scene, user: User | None = None) -> dict[str, Any]:
    """详情响应：摘要 + 完整包 + 资料元数据 + 社区统计。"""
    detail = registry.summary(row)
    detail["package"] = row.package_json
    detail["documents"] = [
        {
            "id": doc.id,
            "filename": doc.filename,
            "chunk_count": doc.chunk_count,
            "visibility": doc.visibility,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in knowledge_svc.list_documents(db, row.id)
    ]
    detail["stats"] = social.stats_map(db, [row.id], user.id if user else None)[row.id]
    return detail


def get_scene(db: Session, scene_id: str, user: User | None) -> dict[str, Any]:
    """取场景详情（含可见性校验）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return scene_detail(db, row, user)


# ---- 创建 / 更新 ------------------------------------------------------------

def create_scene(db: Session, user: User, data: dict[str, Any]) -> dict[str, Any]:
    """创建自定义场景：全量校验 + ID 冲突检查后入库（默认本地私有）。"""
    package = registry.validate(data)
    if db.get(Scene, package.meta.id) is not None:
        raise SceneIdConflictError(package.meta.id, "custom")
    row = Scene(id=package.meta.id, source="custom", author_id=user.id, created_at=utcnow())
    registry.apply_package(row, package, data)
    db.add(row)
    registry.invalidate_cache()
    db.commit()
    db.refresh(row)
    return scene_detail(db, row, user)


def update_scene(db: Session, user: User, scene_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """更新自定义场景：builtin 只读、ID 不可变。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    if data.get("meta", {}).get("id") not in (None, scene_id):
        raise AppError("场景 ID 不允许修改，如需新 ID 请使用复制", code="SCENE_ID_IMMUTABLE", status_code=400)
    package = registry.validate(data)
    registry.apply_package(row, package, data)
    registry.invalidate_cache(scene_id)
    db.commit()
    db.refresh(row)
    return scene_detail(db, row, user)


def duplicate_scene(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """复制场景为自定义私有副本（含知识资料：源文件 + documents/chunks）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)

    data = copy.deepcopy(row.package_json)
    base_id = f"{row.id}_copy"
    new_id = base_id
    index = 2
    while db.get(Scene, new_id) is not None:  # 副本 ID 顺延，避免冲突
        new_id = f"{base_id}_{index}"
        index += 1
    data["meta"]["id"] = new_id
    data["meta"]["name"] = f"{row.name}（副本）"
    package = registry.validate(data)

    new_row = Scene(id=new_id, source="custom", author_id=user.id, created_at=utcnow())
    registry.apply_package(new_row, package, data)
    # 封面随场景一并复制
    if row.cover_path:
        source_cover = knowledge_svc.cover_file(row.cover_path)
        if source_cover.exists():
            target_dir = knowledge_svc.STORAGE_ROOT / "scenes" / new_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_dir.joinpath(f"cover{source_cover.suffix}").write_bytes(source_cover.read_bytes())
            new_row.cover_path = f"scenes/{new_id}/cover{source_cover.suffix}"
    db.add(new_row)
    db.flush()  # 先落 Scene 行：documents/chunks 的 FK 指向新 id，须等场景行存在（两表无 ORM relationship，单元工作不会自动排序）

    for document in knowledge_svc.list_documents(db, row.id):
        source = knowledge_svc.knowledge_dir(row.id) / document.filename
        if not source.exists():
            continue
        new_document = Document(
            scene_id=new_id,
            owner_id=user.id,
            filename=document.filename,
            content_type=document.content_type,
            chunk_count=document.chunk_count,
            visibility=document.visibility,
            created_at=utcnow(),
        )
        db.add(new_document)
        db.flush()
        target_dir = knowledge_svc.knowledge_dir(new_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir.joinpath(document.filename).write_bytes(source.read_bytes())
        for chunk in db.query(Chunk).filter(Chunk.document_id == document.id).order_by(Chunk.ordinal):
            db.add(
                Chunk(
                    document_id=new_document.id,
                    scene_id=new_id,
                    section=chunk.section,
                    visibility=chunk.visibility,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                )
            )
    registry.invalidate_cache()
    db.commit()
    db.refresh(new_row)
    return scene_detail(db, new_row, user)


def delete_scene(db: Session, user: User, scene_id: str) -> str:
    """删除自定义场景：资料源文件与 documents/chunks 一并清除。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    db.query(Chunk).filter(Chunk.scene_id == scene_id).delete()
    db.query(Document).filter(Document.scene_id == scene_id).delete()
    db.delete(row)
    knowledge_svc.remove_scene_files(scene_id)
    registry.invalidate_cache(scene_id)
    db.commit()
    return scene_id


def create_from_template(db: Session, user: User, template_id: str, new_id: str | None = None) -> dict[str, Any]:
    """从内置模板复制创建自定义场景：内置只读的替代路径。"""
    if not template_id:
        raise AppError("缺少 template_id", code="SCENE_NOT_TEMPLATE", status_code=400)
    row = load_scene(db, template_id)
    if row.source != "builtin":
        raise AppError("模板必须是内置场景", code="SCENE_NOT_TEMPLATE", status_code=400)

    data = copy.deepcopy(row.package_json)
    final_id = new_id or f"{row.id}_custom"
    data["meta"]["id"] = final_id
    data["meta"]["author"] = user.username
    if "name" in data.get("meta", {}):
        data["meta"]["name"] = f"{data['meta']['name']}（我的版本）"
    package = registry.validate(data)

    if db.get(Scene, final_id) is not None:
        raise SceneIdConflictError(final_id, "custom")
    new_row = Scene(id=final_id, source="custom", author_id=user.id, created_at=utcnow())
    registry.apply_package(new_row, package, data)
    db.add(new_row)
    registry.invalidate_cache()
    db.commit()
    db.refresh(new_row)
    return scene_detail(db, new_row, user)


# ---- 导入导出 ---------------------------------------------------------------

def import_package(
    db: Session, user: User, content: bytes, resolve: str | None
) -> tuple[Scene, str | None]:
    """导入 v2 场景包；冲突处理策略由 resolve 决定（§8.2）。"""
    return packaging.import_package(db, content, author_id=user.id, resolve=resolve)


def export_package(db: Session, scene_id: str, user: User | None) -> bytes:
    """导出 v2 ZIP；非作者导出计入下载量（作者本人不计）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    if user is None or user.id != row.author_id:
        social.count_download(db, row.id)
    return packaging.export_zip(db, row)


# ---- 模板与知识资料 ----------------------------------------------------------

def list_templates(db: Session) -> list[dict[str, Any]]:
    """内置模板摘要列表。"""
    rows = db.query(Scene).filter(Scene.source == "builtin").order_by(Scene.id).all()
    return [registry.summary(row) for row in rows]


def upload_knowledge(
    db: Session,
    user: User,
    scene_id: str,
    filename: str | None,
    content: bytes,
    content_type: str | None,
    visibility: str,
) -> Document:
    """上传资料：校验可写性后解析分块入库。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    return knowledge_svc.add_document(
        db, row, filename or "untitled.txt", content, content_type, visibility,
    )


def set_cover(db: Session, user: User, scene_id: str, filename: str | None, content: bytes) -> str:
    """设置场景封面：仅作者可操作；返回相对路径。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    relative = knowledge_svc.save_cover(scene_id, filename or "cover.png", content)
    row.cover_path = relative
    db.commit()
    return relative


def get_cover_file(db: Session, scene_id: str):
    """封面文件路径；未设置或文件缺失返回 None（调用方转 404）。"""
    row = load_scene(db, scene_id)
    if not row.cover_path:
        return None
    path = knowledge_svc.cover_file(row.cover_path)
    return path if path.exists() else None


def remove_cover(db: Session, user: User, scene_id: str) -> bool:
    """移除封面：删除文件并清空引用；未设置时返回 False。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    if not row.cover_path:
        return False
    path = knowledge_svc.cover_file(row.cover_path)
    if path.exists():
        path.unlink()
    row.cover_path = None
    db.commit()
    return True


def visible_knowledge(db: Session, scene_id: str, user: User | None) -> dict[str, Any]:
    """学习者可见分节（ai_only 不下发）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    sections = knowledge_svc.visible_sections(db, scene_id, only_user=True)
    return {"scene_id": scene_id, "has_knowledge": bool(sections), "sections": sections}


def section_overview(db: Session, scene_id: str, user: User | None) -> dict[str, Any]:
    """全分节概览（含 ai_only）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return {
        "scene_id": scene_id,
        "sections": knowledge_svc.visible_sections(db, scene_id, only_user=False),
    }


def document_overview(db: Session, scene_id: str, user: User | None) -> dict[str, Any]:
    """资料文件级概览（含每文件分节分组）：知识工作区管理界面数据源。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return {"scene_id": scene_id, "documents": knowledge_svc.document_overview(db, scene_id)}


def document_chunks(db: Session, scene_id: str, document_id: int, user: User | None) -> dict[str, Any]:
    """资料的分块明细（含正文全文）：知识工作区查看数据源。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return {
        "scene_id": scene_id,
        "document_id": document_id,
        "chunks": knowledge_svc.list_document_chunks(db, scene_id, document_id),
    }


def document_source(db: Session, scene_id: str, document_id: int, user: User | None) -> dict[str, Any]:
    """资料源文件全文（文本类可编辑）：知识工作区源文件编辑数据源。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return knowledge_svc.read_document_source(db, scene_id, document_id)


def update_document_source(db: Session, user: User, scene_id: str, document_id: int, text: str) -> dict[str, Any]:
    """编辑源文件并重新解析分块（作者可写场景）。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    document = knowledge_svc.update_document_source(db, row, document_id, text)
    return {
        "id": document.id,
        "filename": document.filename,
        "chunk_count": document.chunk_count,
        "visibility": document.visibility,
    }


def patch_section_visibility(db: Session, user: User, scene_id: str, section: str, visibility: str) -> dict[str, Any]:
    """修改分节可见性。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    updated = knowledge_svc.set_section_visibility(db, scene_id, section, visibility)
    return {"section": section, "visibility": visibility, "updated_chunks": updated}


def scene_graph(db: Session, scene_id: str, user: User | None) -> dict[str, Any]:
    """实体关系图谱（阶段三，规则抽取）：知识工作区右侧面板数据源。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return graph_svc.scene_graph(db, scene_id)


# ---- 混合检索（Hybrid RAG）：关键词 + 向量 RRF 融合 --------------------------

def search_knowledge(db: Session, user: User | None, scene_id: str, query: str, top_k: int) -> dict[str, Any]:
    """场景知识混合检索：搜索框与对话侧注入共用的数据源。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    from app.scenes import retrieval as retrieval_svc

    return retrieval_svc.search_scene(db, scene_id, query, top_k)


def reindex_knowledge(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """为场景分块补建向量（上传时嵌入失败 / 换嵌入模型后的全量重建）。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    from app.scenes import embedding as embedding_svc

    if not embedding_svc.available():
        raise AppError("未配置 ECHOTALK_SILICONFLOW_API_KEY，无法生成向量", status_code=400)
    embedded = knowledge_svc.reindex_scene(db, scene_id)
    return {"scene_id": scene_id, "model": embedding_svc.config.EMBEDDING_MODEL, "embedded": embedded}


def search_personal_knowledge(db: Session, user: User, query: str, top_k: int) -> dict[str, Any]:
    """个人资料混合检索。"""
    from app.scenes import retrieval as retrieval_svc

    return retrieval_svc.search_personal(db, user.id, query, top_k)


def reindex_personal_knowledge(db: Session, user: User) -> dict[str, Any]:
    """为本人个人资料分块补建向量。"""
    from app.scenes import embedding as embedding_svc

    if not embedding_svc.available():
        raise AppError("未配置 ECHOTALK_SILICONFLOW_API_KEY，无法生成向量", status_code=400)
    embedded = knowledge_svc.reindex_personal(db, user.id)
    return {"model": embedding_svc.config.EMBEDDING_MODEL, "embedded": embedded}


# ---- LightRAG 图谱检索（阶段 3+）：实体关系索引 ------------------------------

def _lightrag_available_or_400() -> None:
    from app.scenes import lightrag_service as lightrag_svc

    if not lightrag_svc.available():
        raise AppError(
            "LightRAG 未启用：需在 backend/.env 配置 ECHOTALK_LIGHTRAG_LLM_API_KEY（抽取 LLM）"
            "与 ECHOTALK_SILICONFLOW_API_KEY（嵌入），且 ECHOTALK_LIGHTRAG_ENABLED 不为 false",
            status_code=400,
        )


def lightrag_scene_query(db: Session, user: User | None, scene_id: str, query: str, mode: str, top_k: int) -> str:
    """场景知识图谱检索（LightRAG mix 模式，返回检索上下文而非生成答案）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    _lightrag_available_or_400()
    from app.scenes import lightrag_service as lightrag_svc

    return lightrag_svc.query("scene", scene_id, query, mode, top_k)


def lightrag_scene_rebuild(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """全量重建场景图谱索引（后台执行）。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    _lightrag_available_or_400()
    docs = _scene_source_texts(db, scene_id)
    from app.scenes import lightrag_service as lightrag_svc

    lightrag_svc.schedule_rebuild("scene", scene_id, docs)
    return {"scheduled": len(docs)}


def _scene_source_texts(db: Session, scene_id: str) -> list[tuple[int, str]]:
    """场景全部资料源文本（可编辑类读盘，pdf 用分块拼接兜底）。"""
    documents = knowledge_svc.list_documents(db, scene_id)
    result: list[tuple[int, str]] = []
    for document in documents:
        source = knowledge_svc.read_document_source(db, scene_id, document.id)
        if source.get("editable"):
            text = source["text"]
        else:  # pdf：用分块正文拼接（图谱抽取对结构不敏感）
            chunks = knowledge_svc.list_document_chunks(db, scene_id, document.id)
            text = "\n\n".join(c["text"] for c in chunks)
        if text.strip():
            result.append((document.id, text))
    return result


def _personal_source_texts(db: Session, user_id: int) -> list[tuple[int, str]]:
    """本人全部个人资料源文本（取数逻辑同上）。"""
    result: list[tuple[int, str]] = []
    for document in knowledge_svc.personal_document_overview(db, user_id):
        source = knowledge_svc.read_personal_source(db, user_id, document["id"])
        if source.get("editable"):
            text = source["text"]
        else:
            chunks = knowledge_svc.list_personal_chunks(db, user_id, document["id"])
            text = "\n\n".join(c["text"] for c in chunks)
        if text.strip():
            result.append((document["id"], text))
    return result


def lightrag_personal_query(db: Session, user: User, query: str, mode: str, top_k: int) -> str:
    """个人资料图谱检索。"""
    _lightrag_available_or_400()
    from app.scenes import lightrag_service as lightrag_svc

    return lightrag_svc.query("personal", user.id, query, mode, top_k)


def lightrag_personal_rebuild(db: Session, user: User) -> dict[str, Any]:
    """全量重建本人个人资料图谱索引（后台执行）。"""
    _lightrag_available_or_400()
    docs = _personal_source_texts(db, user.id)
    from app.scenes import lightrag_service as lightrag_svc

    lightrag_svc.schedule_rebuild("personal", user.id, docs)
    return {"scheduled": len(docs)}


# ---- 个人工作区资料（阶段二）：owner 隔离，全部要求登录 ----------------------

def personal_overview(db: Session, user: User) -> dict[str, Any]:
    """个人资料文件级概览。"""
    return {"documents": knowledge_svc.personal_document_overview(db, user.id)}


def personal_graph(db: Session, user: User) -> dict[str, Any]:
    """个人资料实体关系图谱（与场景图谱同一套抽取逻辑）。"""
    return graph_svc.personal_graph(db, user.id)


def upload_personal(db: Session, user: User, filename: str, content: bytes, content_type: str | None) -> dict[str, Any]:
    """上传个人资料（同名覆盖即更新）。"""
    document = knowledge_svc.add_personal_document(db, user.id, filename, content, content_type)
    return {
        "id": document.id,
        "filename": document.filename,
        "chunk_count": document.chunk_count,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


def personal_chunks(db: Session, user: User, document_id: int) -> dict[str, Any]:
    """个人资料分块明细（只读）。"""
    return {
        "document_id": document_id,
        "chunks": knowledge_svc.list_personal_chunks(db, user.id, document_id),
    }


def personal_source(db: Session, user: User, document_id: int) -> dict[str, Any]:
    """个人资料源文件全文。"""
    return knowledge_svc.read_personal_source(db, user.id, document_id)


def update_personal_source(db: Session, user: User, document_id: int, text: str) -> dict[str, Any]:
    """编辑个人资料源文件并重新解析。"""
    document = knowledge_svc.update_personal_source(db, user.id, document_id, text)
    return {
        "id": document.id,
        "filename": document.filename,
        "chunk_count": document.chunk_count,
    }


def delete_personal(db: Session, user: User, document_id: int) -> dict[str, Any]:
    """删除个人资料。"""
    document = knowledge_svc.delete_personal_document(db, user.id, document_id)
    return {"deleted": document.filename}


def delete_knowledge(db: Session, user: User, scene_id: str, document_id: int) -> Document:
    """删除单个资料（源文件 + 记录）。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    return knowledge_svc.delete_document(db, scene_id, document_id)


# ---- 发布与社区互动 ----------------------------------------------------------

def publish(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """发布场景：全员可见可下载。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    social.publish(db, row)
    return {
        "id": row.id,
        "status": row.status,
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }


def unpublish(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """取消发布：回到本地私有。"""
    row = load_scene(db, scene_id)
    ensure_writable(row, user)
    social.unpublish(db, row)
    return {"id": row.id, "status": row.status}


def like(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """点赞/取消（去重）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return social.toggle_like(db, row.id, user.id)


def favorite(db: Session, user: User, scene_id: str) -> dict[str, Any]:
    """收藏/取消（去重）。"""
    row = load_scene(db, scene_id)
    ensure_visible(row, user)
    return social.toggle_favorite(db, row.id, user.id)
