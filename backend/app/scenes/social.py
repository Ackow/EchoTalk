"""场景发布与社区统计：本地私有为默认，发布后全员可见可下载（v1.2 增补需求）。

- 发布是轻量分享：把已有的包标记为 published，其他用户浏览/导出 ZIP 自行导入。
- 统计：点赞/收藏按用户去重（scene_user_stats），下载按导出次数累计（scene_stats）。
"""
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.timeutil import utcnow
from app.models import Scene, SceneStats, SceneUserStat


# ---- 可见性 ----------------------------------------------------------------

def visible_to(row: Scene, user_id: int | None) -> bool:
    """列表/详情可见性：builtin 全员；本人全部；他人仅 published。"""
    if row.source == "builtin" or row.author_id == user_id:
        return True
    return row.status == "published"


# ---- 发布 / 取消发布 ---------------------------------------------------------

def publish(db: Session, row: Scene) -> Scene:
    """发布自定义场景：status → published。"""
    if row.source == "builtin":
        raise AppError("内置场景始终公开，无需发布", code="SCENE_BUILTIN_READONLY", status_code=409)
    row.status = "published"
    if row.published_at is None:
        row.published_at = utcnow()
    db.commit()
    return row


def unpublish(db: Session, row: Scene) -> Scene:
    """取消发布：回到本地私有；已有统计保留（再次发布可继续累计）。"""
    if row.source == "builtin":
        raise AppError("内置场景始终公开，不可下架", code="SCENE_BUILTIN_READONLY", status_code=409)
    row.status = "private"
    db.commit()
    return row


# ---- 统计 ------------------------------------------------------------------

def get_or_create_stats(db: Session, scene_id: str) -> SceneStats:
    """取场景统计行；不存在则惰性创建（builtin 首次被点赞时）。"""
    stats = db.get(SceneStats, scene_id)
    if stats is None:
        stats = SceneStats(scene_id=scene_id)
        db.add(stats)
        db.flush()
    return stats


def stats_map(db: Session, scene_ids: list[str], user_id: int | None) -> dict[str, dict[str, Any]]:
    """批量取统计 + 当前用户互动态：列表页一次查询，避免逐行 N+1。"""
    if not scene_ids:
        return {}
    stats_rows = db.query(SceneStats).filter(SceneStats.scene_id.in_(scene_ids)).all()
    stats_by_id = {s.scene_id: s for s in stats_rows}
    mine: dict[str, SceneUserStat] = {}
    if user_id is not None:
        rows = (
            db.query(SceneUserStat)
            .filter(SceneUserStat.scene_id.in_(scene_ids), SceneUserStat.user_id == user_id)
            .all()
        )
        mine = {r.scene_id: r for r in rows}
    result: dict[str, dict[str, Any]] = {}
    for scene_id in scene_ids:
        stats = stats_by_id.get(scene_id)
        interaction = mine.get(scene_id)
        result[scene_id] = {
            "likes": stats.likes if stats else 0,
            "downloads": stats.downloads if stats else 0,
            "favorites": stats.favorites if stats else 0,
            "liked": bool(interaction.liked) if interaction else False,
            "favorited": bool(interaction.favorited) if interaction else False,
        }
    return result


def toggle_like(db: Session, scene_id: str, user_id: int) -> dict[str, Any]:
    """切换点赞：已赞则取消；返回最新计数与状态。"""
    stats = get_or_create_stats(db, scene_id)
    record = _get_or_create_interaction(db, scene_id, user_id)
    if record.liked:
        record.liked = 0
        stats.likes = max(0, stats.likes - 1)
    else:
        record.liked = 1
        stats.likes += 1
    db.commit()
    return {"liked": bool(record.liked), "likes": stats.likes}


def toggle_favorite(db: Session, scene_id: str, user_id: int) -> dict[str, Any]:
    """切换收藏：已收藏则取消；返回最新计数与状态。"""
    stats = get_or_create_stats(db, scene_id)
    record = _get_or_create_interaction(db, scene_id, user_id)
    if record.favorited:
        record.favorited = 0
        stats.favorites = max(0, stats.favorites - 1)
    else:
        record.favorited = 1
        stats.favorites += 1
    db.commit()
    return {"favorited": bool(record.favorited), "favorites": stats.favorites}


def count_download(db: Session, scene_id: str) -> None:
    """导出即计数：作者本人的导出不计入下载量。"""
    stats = get_or_create_stats(db, scene_id)
    stats.downloads += 1
    db.commit()


def _get_or_create_interaction(db: Session, scene_id: str, user_id: int) -> SceneUserStat:
    """取用户互动记录；不存在则惰性创建。"""
    record = (
        db.query(SceneUserStat)
        .filter(SceneUserStat.scene_id == scene_id, SceneUserStat.user_id == user_id)
        .first()
    )
    if record is None:
        record = SceneUserStat(scene_id=scene_id, user_id=user_id)
        db.add(record)
        db.flush()
    return record
