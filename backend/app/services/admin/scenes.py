"""管理端全量场景管理：查询、详情、更新、发布下架与批量删除。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import Document, PracticeSession, Scene, SceneStats
from app.scenes.registry import validate


def list_scenes(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    mode: str | None = None,
    source: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询全平台场景（含私有、已发布、内置、自定义）。"""
    conditions = []
    if q and q.strip():
        kw = f"%{q.strip()}%"
        conditions.append(or_(Scene.id.ilike(kw), Scene.name.ilike(kw), Scene.description.ilike(kw)))
    if category:
        conditions.append(Scene.category == category)
    if mode:
        conditions.append(Scene.mode == mode)
    if source:
        conditions.append(Scene.source == source)
    if status:
        conditions.append(Scene.status == status)

    total = db.scalar(select(func.count()).select_from(Scene).where(*conditions)) or 0
    rows = db.execute(
        select(Scene, SceneStats)
        .outerjoin(SceneStats, SceneStats.scene_id == Scene.id)
        .where(*conditions)
        .order_by(Scene.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    scene_ids = [s.id for s, _ in rows]
    doc_counts: dict[str, int] = {}
    session_counts: dict[str, int] = {}
    if scene_ids:
        doc_counts = dict(
            db.execute(
                select(Document.scene_id, func.count()).where(Document.scene_id.in_(scene_ids)).group_by(Document.scene_id)
            ).all()
        )
        session_counts = dict(
            db.execute(
                select(PracticeSession.scene_id, func.count())
                .where(PracticeSession.scene_id.in_(scene_ids))
                .group_by(PracticeSession.scene_id)
            ).all()
        )

    items = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description or "",
            "category": s.category,
            "mode": s.mode,
            "difficulty": s.difficulty,
            "source": s.source,
            "status": s.status,
            "author_id": s.author_id,
            "author_name": s.author.username if s.author else "系统内置",
            "cover_url": f"/api/scenes/{s.id}/cover" if s.cover_path else None,
            "likes": st.likes if st else 0,
            "downloads": st.downloads if st else 0,
            "favorites": st.favorites if st else 0,
            "document_count": doc_counts.get(s.id, 0),
            "session_count": session_counts.get(s.id, 0),
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s, st in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_scene_detail(db: Session, scene_id: str) -> dict:
    """获取场景完整详情，包含 package_json 与关联文档。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)
    stats = db.get(SceneStats, scene_id)
    docs = db.scalars(select(Document).where(Document.scene_id == scene_id).order_by(Document.id.desc())).all()
    session_count = db.scalar(select(func.count()).select_from(PracticeSession).where(PracticeSession.scene_id == scene_id)) or 0
    return {
        "id": scene.id,
        "name": scene.name,
        "description": scene.description or "",
        "category": scene.category,
        "mode": scene.mode,
        "difficulty": scene.difficulty,
        "source": scene.source,
        "status": scene.status,
        "published_at": scene.published_at,
        "author_id": scene.author_id,
        "author_name": scene.author.username if scene.author else "系统内置",
        "cover_url": f"/api/scenes/{scene.id}/cover" if scene.cover_path else None,
        "greeting_text": scene.greeting_text,
        "domain_keywords": scene.domain_keywords or [],
        "package_json": scene.package_json,
        "stats": {
            "likes": stats.likes if stats else 0,
            "downloads": stats.downloads if stats else 0,
            "favorites": stats.favorites if stats else 0,
            "session_count": session_count,
        },
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "content_type": d.content_type,
                "chunk_count": d.chunk_count,
                "visibility": d.visibility,
                "created_at": d.created_at,
            }
            for d in docs
        ],
        "created_at": scene.created_at,
        "updated_at": scene.updated_at,
    }


def update_scene(db: Session, scene_id: str, data: dict) -> dict:
    """管理员更新场景信息或发布状态。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)

    pkg = dict(scene.package_json or {})
    if data.get("package_json") is not None:
        validated = validate(data["package_json"])
        pkg = validated.model_dump(mode="json")
        scene.package_json = pkg
        scene.name = validated.meta.name
        scene.description = validated.meta.description
        scene.category = validated.meta.category
        scene.mode = validated.meta.mode
        scene.difficulty = validated.meta.difficulty
    else:
        meta = dict(pkg.get("meta") or {})
        for field in ("name", "description", "category", "mode", "difficulty"):
            if data.get(field) is not None:
                setattr(scene, field, data[field])
                meta[field] = data[field]
        pkg["meta"] = meta
        scene.package_json = pkg

    if data.get("status") is not None:
        if scene.source == "builtin" and data["status"] != "published":
            raise AppError("系统内置场景恒为公开状态，不可下架", code="BUILTIN_PROTECTED", status_code=400)
        scene.status = data["status"]
        scene.published_at = utcnow() if data["status"] == "published" else None

    db.commit()
    db.refresh(scene)
    return get_scene_detail(db, scene.id)


def delete_scene(db: Session, scene_id: str) -> None:
    """管理员删除非内置场景。"""
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise AppError("场景不存在", code="SCENE_NOT_FOUND", status_code=404)
    if scene.source == "builtin":
        raise AppError("内置场景受保护，不允许删除", code="BUILTIN_PROTECTED", status_code=400)
    db.delete(scene)
    db.commit()


def batch_update_scenes_status(db: Session, scene_ids: list[str], status: str) -> dict:
    """批量发布或下架场景（内置场景不可下架）。"""
    unique_ids = list(dict.fromkeys(scene_ids))
    now = utcnow() if status == "published" else None
    q = db.query(Scene).filter(Scene.id.in_(unique_ids))
    if status != "published":
        q = q.filter(Scene.source != "builtin")
    updated = q.update({"status": status, "published_at": now}, synchronize_session=False)
    db.commit()
    return {"updated": updated}


def batch_delete_scenes(db: Session, scene_ids: list[str]) -> dict:
    """批量删除非内置场景（自动跳过内置场景）。"""
    unique_ids = list(dict.fromkeys(scene_ids))
    scenes = db.scalars(select(Scene).where(Scene.id.in_(unique_ids))).all()
    deleted = 0
    skipped_builtin = 0
    for scene in scenes:
        if scene.source == "builtin":
            skipped_builtin += 1
            continue
        db.delete(scene)
        deleted += 1
    db.commit()
    return {"deleted": deleted, "skipped_builtin": skipped_builtin}
