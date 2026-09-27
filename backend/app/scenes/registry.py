"""SceneRegistry：内置种子同步、进程内缓存与包/行互转（设计稿场景包方案 §5.1）。

- 内置场景入库（source=builtin），与自定义场景同构：统一查询、统一接口。
- 内置场景只读：不可编辑/删除，「复制为自定义」后可改。
- 写操作直接失效缓存；get 每次读缓存、未命中回源 DB，编辑即时生效。
"""
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models import Scene
from app.scenes.errors import SceneInvalidPackageError
from app.scenes.schema import DIFFICULTY_LEVELS, ScenePackage, SceneValidationError, normalize_difficulty

logger = logging.getLogger("echotalk")

CONTENT_DIR = Path(__file__).resolve().parents[1] / "content" / "scenes"  # 内置种子目录
APP_VERSION = "2.0.0"

# 进程内缓存：scene_id → ScenePackage（写操作后整体失效，量级小、实现最简单）
_cache: dict[str, ScenePackage] = {}


def invalidate_cache(scene_id: str | None = None) -> None:
    """失效缓存：写操作后调用；传 scene_id 只失效单个，否则全清。"""
    if scene_id is None:
        _cache.clear()
    else:
        _cache.pop(scene_id, None)


# ---- 校验入口 --------------------------------------------------------------

def validate(data: dict[str, Any]) -> ScenePackage:
    """校验包数据并返回 ScenePackage；失败转 SceneInvalidPackageError。

    注意：model_validator 抛出的 SceneValidationError 会被 Pydantic 包进
    ValidationError.errors()[i]["ctx"]["error"]，此处负责解包还原字段级错误。
    """
    try:
        return ScenePackage.model_validate(data)
    except SceneValidationError as exc:  # 直接调用（非 Pydantic 通道）时
        raise SceneInvalidPackageError(
            str(exc),
            details=[{"field": path, "message": reason} for path, reason in exc.errors],
        ) from exc
    except ValidationError as exc:
        for error in exc.errors():  # 解包：优先还原跨字段校验的语义错误
            inner = (error.get("ctx") or {}).get("error")
            if isinstance(inner, SceneValidationError):
                raise SceneInvalidPackageError(
                    str(inner),
                    details=[{"field": path, "message": reason} for path, reason in inner.errors],
                ) from exc
        details = [  # 普通字段错误：类型 / 枚举 / 长度等（剥掉 Pydantic 的 "Value error, " 前缀）
            {"field": ".".join(str(part) for part in error["loc"]),
             "message": error["msg"].removeprefix("Value error, ")}
            for error in exc.errors()
        ]
        raise SceneInvalidPackageError(f"场景包校验失败（{len(details)} 处）", details=details) from exc


# ---- 种子同步 --------------------------------------------------------------

def _migrate_difficulties(db: Session) -> None:
    """一次性迁移：历史难度值（CEFR / 中文三档）归一为五级英文枚举。

    同时刷新冗余列与 package_json 内的 meta.difficulty，保证两处一致。
    已是合法枚举的行原样跳过，幂等可重复执行。
    """
    valid = set(DIFFICULTY_LEVELS)
    rows = db.scalars(select(Scene)).all()
    changed = 0
    for row in rows:
        if row.difficulty and row.difficulty not in valid:
            row.difficulty = normalize_difficulty(row.difficulty)
            data = dict(row.package_json or {})
            meta = dict(data.get("meta") or {})
            if meta.get("difficulty"):
                meta["difficulty"] = row.difficulty
                data["meta"] = meta
                row.package_json = data
            changed += 1
    if changed:
        db.commit()
        logger.info("难度五级化迁移：%d 行历史值已归一", changed)


def sync_seeds(db: Session) -> int:
    """启动时把 content/scenes/*.yaml 同步入库；返回同步的包数量。

    已存在且未被应用更新过的内置行按 meta.version 判断是否刷新；
    内置场景只读、不可被用户改动，因此无「覆盖用户改动」风险。
    """
    _migrate_difficulties(db)
    synced = 0
    for path in sorted(CONTENT_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            package = validate(data)
        except SceneInvalidPackageError:
            logger.exception("内置场景包种子校验失败：%s", path.name)
            continue

        row = db.get(Scene, package.meta.id)
        if row is None:
            row = Scene(
                id=package.meta.id,
                name=package.meta.name,
                description=package.meta.description,
                category=package.meta.category,
                mode=package.meta.mode,
                difficulty=package.meta.difficulty,
                source="builtin",
                pkg_version=package.meta.version,
                author_id=None,
                greeting_text=package.prompt.greeting,
                domain_keywords=(package.guardrails.off_topic or {}).get("domain_keywords"),
                package_json=data,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(row)
            _cache[package.meta.id] = package
            synced += 1
        elif row.source == "builtin" and package.meta.version > (row.pkg_version or 0):
            # 应用升级：按版本号刷新未被删除的内置行
            apply_package(row, package, data)
            db.add(row)
            _cache[package.meta.id] = package
            synced += 1
    db.commit()
    return synced


# ---- 行 ↔ 包互转 -----------------------------------------------------------

def apply_package(row: Scene, package: ScenePackage, data: dict[str, Any]) -> None:
    """把校验通过的包写入行冗余列。

    package_json 存**校验后模型的完整 dump**（而非原始请求 dict）：
    默认值（category/mode/version 等）显式落库，读写两端结构一致，
    编辑回显与导出 ZIP 不会因缺字段出现空下拉/不完整包。
    """
    row.name = package.meta.name
    row.description = package.meta.description
    row.category = package.meta.category
    row.mode = package.meta.mode
    row.difficulty = package.meta.difficulty
    row.package_json = package.model_dump(mode="json", exclude_none=True)
    row.pkg_version = package.meta.version
    row.greeting_text = package.prompt.greeting
    row.domain_keywords = (package.guardrails.off_topic or {}).get("domain_keywords")
    row.updated_at = utcnow()


def row_to_package(row: Scene) -> ScenePackage:
    """从数据库行恢复 ScenePackage（缓存优先；脏数据抛 422 而非中断服务）。"""
    package = _cache.get(row.id)
    if package is not None:
        return package
    package = validate(row.package_json)  # 运行时再校验一次（§5.2 防脏数据）
    _cache[row.id] = package
    return package


def summary(row: Scene) -> dict[str, Any]:
    """SceneSummary：场景卡与列表所需的摘要字段（§5.1）。"""
    try:
        package = row_to_package(row)
        knowledge_count = len(package.knowledge.files)
        objective_count = len(package.objectives)
        tags = package.meta.tags
        roles = [{"id": r.id, "display_name": r.display_name, "title": r.title, "backstage": r.backstage} for r in package.roles]
        stage_count = len(package.stages)
    except SceneInvalidPackageError:  # 脏数据兜底：摘要仍可用行冗余列渲染
        knowledge_count = 0
        objective_count = 0
        tags = []
        roles = []
        stage_count = 0
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "category": row.category,
        "mode": row.mode,
        "difficulty": row.difficulty,
        "source": row.source,
        "status": row.status or ("published" if row.source == "builtin" else "private"),  # builtin 恒为公开
        "author_id": row.author_id,  # 「我的场景」筛选依据
        "author_name": row.author.username if row.author is not None else None,  # 卡片作者署名
        "cover_path": row.cover_path,  # 封面图相对路径（前端拼 URL）
        "tags": tags,
        "knowledge_count": knowledge_count,
        "objective_count": objective_count,
        "stage_count": stage_count,
        "roles": roles,
        "has_greeting_audio": bool(row.greeting_audio_path),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
