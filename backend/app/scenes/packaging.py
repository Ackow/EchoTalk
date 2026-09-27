"""场景包导入导出：v2 ZIP = manifest.json + scene.yaml + knowledge/ 源文件（§8）。

不携带任何向量索引或数据库 dump；旧 1.0 格式（scene_config.json + FAISS）一律拒绝。
"""
import io
import json
import zipfile
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models import Scene
from app.scenes import knowledge as knowledge_svc
from app.scenes import registry
from app.scenes.errors import SceneInvalidPackageError, ScenePackageIncompatibleError
from app.scenes.registry import APP_VERSION
from app.scenes.schema import ScenePackage

MANIFEST_FORMAT = "echotalk-scene"
MANIFEST_VERSION = 2


# ---- 导出 ------------------------------------------------------------------

def export_zip(db: Session, row: Scene) -> bytes:
    """导出场景为 v2 ZIP：manifest（含校验和）+ scene.yaml + knowledge/ 源文件。"""
    package = registry.row_to_package(row)
    data = row.package_json  # 原始字典（保持 YAML 顺序与注释外的原貌）
    scene_yaml = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

    checksums: dict[str, str] = {"scene.yaml": knowledge_svc.file_checksum(scene_yaml.encode("utf-8"))}
    files: list[str] = ["scene.yaml"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("scene.yaml", scene_yaml)
        # 资料源文件：user 与 ai_only 都导出（可见性是作者的教学设计，非用户隐私）
        for document in knowledge_svc.list_documents(db, row.id):
            source = knowledge_svc.knowledge_dir(row.id) / document.filename
            if not source.exists():
                continue  # 存储缺失时跳过而不中断导出
            arcname = f"knowledge/{document.filename}"
            content = source.read_bytes()
            zf.writestr(arcname, content)
            files.append(arcname)
            checksums[arcname] = knowledge_svc.file_checksum(content)

        manifest = {
            "format": MANIFEST_FORMAT,
            "version": MANIFEST_VERSION,
            "scene_id": row.id,
            "min_app": package.meta.compat.get("min_app", "2.0.0"),
            "files": files,
            "checksums": checksums,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue()


# ---- 导入 ------------------------------------------------------------------

def _reject_old_package(names: list[str]) -> None:
    """旧 1.0 包特征：scene_config.json / *.index —— 不做兼容，给出可解释原因。"""
    if "scene_config.json" in names or any(n.endswith(".index") for n in names):
        raise SceneInvalidPackageError(
            "这是 1.0 旧格式的场景包（scene_config.json / FAISS 索引）。"
            "2.0 不提供旧包导入：请使用 2.0 导出的包（manifest.json + scene.yaml）或从模板重新创建。"
        )


def parse_zip(db: Session, content: bytes) -> tuple[ScenePackage, dict[str, bytes], dict[str, Any]]:
    """解析并校验 ZIP：返回 (ScenePackage, knowledge 文件内容表, manifest)。

    任何结构问题都抛 SceneInvalidPackageError（附可解释原因）；
    版本不满足抛 ScenePackageIncompatibleError。
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise SceneInvalidPackageError("不是有效的 ZIP 文件") from exc

    names = zf.namelist()
    _reject_old_package(names)

    if "scene.yaml" not in names:
        raise SceneInvalidPackageError("包内缺少必需的 scene.yaml")
    try:
        data = yaml.safe_load(zf.read("scene.yaml").decode("utf-8"))
    except yaml.YAMLError as exc:
        raise SceneInvalidPackageError(f"scene.yaml 不是有效的 YAML：{exc}") from exc
    if not isinstance(data, dict):
        raise SceneInvalidPackageError("scene.yaml 内容需要是键值映射结构")

    package = registry.validate(data)  # Pydantic + 表达式 dry-run 全量校验

    # manifest 检查：存在则校验格式与 checksums；缺失时允许（scene.yaml 是唯一必需文件）
    manifest: dict[str, Any] = {}
    if "manifest.json" in names:
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SceneInvalidPackageError("manifest.json 不是有效的 JSON") from exc
        if manifest.get("format") != MANIFEST_FORMAT:
            raise SceneInvalidPackageError(f"包格式不受支持：{manifest.get('format')!r}（需要 {MANIFEST_FORMAT!r}）")
        if manifest.get("version", 2) != MANIFEST_VERSION:
            raise SceneInvalidPackageError(f"包结构版本不受支持：v{manifest.get('version')}")
        for filename, expected in (manifest.get("checksums") or {}).items():
            if filename not in names:
                continue
            actual = knowledge_svc.file_checksum(zf.read(filename))
            if actual != expected:
                raise SceneInvalidPackageError(f"文件校验和不匹配：{filename}（包可能已损坏或被篡改）")

    # 应用版本兼容检查
    min_app = package.meta.compat.get("min_app") or manifest.get("min_app") or "2.0.0"
    if _version_tuple(min_app) > _version_tuple(APP_VERSION):
        raise ScenePackageIncompatibleError(
            f"场景包要求应用版本 ≥ {min_app}，当前为 {APP_VERSION}"
        )

    # 收集 knowledge/ 源文件内容（导入时入库分块）
    knowledge_files: dict[str, bytes] = {}
    for name in names:
        if name.startswith("knowledge/") and not name.endswith("/"):
            filename = name.removeprefix("knowledge/")
            if "/" in filename or filename.startswith("."):
                continue  # 只取一层目录内的文件，忽略子目录与隐藏文件
            knowledge_files[filename] = zf.read(name)
    return package, knowledge_files, manifest


def _version_tuple(version: str) -> tuple[int, ...]:
    """'2.1.0' → (2, 1, 0)：用于 min_app 兼容比较。"""
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def import_package(
    db: Session,
    content: bytes,
    *,
    author_id: int | None,
    resolve: str | None,
) -> tuple[Scene, str | None]:
    """导入场景包：校验 → 冲突处理 → 写库 + 资料入库。

    resolve: None（冲突时抛 409）/ overwrite（覆盖同 id 自定义场景）/ rename（自动改名）。
    返回 (场景行, action)，action ∈ {created, overwritten, renamed}。
    """
    package, knowledge_files, _ = parse_zip(db, content)
    scene_id = package.meta.id

    existing = db.get(Scene, scene_id)
    action = "created"
    if existing is not None:
        if existing.source == "builtin":
            # 内置 ID 不可覆盖：resolve=rename 时自动改名，否则要求用户改名（§8.2）
            if resolve != "rename":
                raise_scene_conflict(existing)
            scene_id = _next_available_id(db, scene_id)
            package.meta.id = scene_id
            package = registry.validate(package.model_dump())
            action = "renamed"
        elif resolve is None:
            raise_scene_conflict(existing)
        elif resolve == "rename":
            scene_id = _next_available_id(db, scene_id)
            package.meta.id = scene_id  # 改名后整体校验一次（meta.id 变更不影响其他规则）
            package = registry.validate(package.model_dump())
            action = "renamed"
        elif resolve == "overwrite":
            if existing.author_id is not None and existing.author_id != author_id:
                raise_scene_conflict(existing)  # 只能覆盖自己的场景
            # 覆盖：清空旧资料，重建
            knowledge_svc.remove_scene_files(scene_id)
            from app.models import Chunk, Document

            db.query(Chunk).filter(Chunk.scene_id == scene_id).delete()
            db.query(Document).filter(Document.scene_id == scene_id).delete()
            action = "overwritten"
        else:
            raise SceneInvalidPackageError(f"未知的冲突解决方式：{resolve!r}（可用 overwrite / rename）")

    data = package.model_dump()
    if existing is not None and action == "overwritten":
        row = existing
        registry.apply_package(row, package, data)
        row.source = "imported"
        row.author_id = author_id
    else:
        row = Scene(
            id=scene_id,
            source="imported",
            author_id=author_id,
            created_at=row_time(),
        )
        registry.apply_package(row, package, data)
        db.add(row)
    db.flush()

    # 资料入库：按包内声明决定文件级可见性（缺省 user）
    visibility_by_path = {f.path: f.visibility for f in package.knowledge.files}
    for filename, file_content in knowledge_files.items():
        visibility = visibility_by_path.get(filename, "user")
        try:
            knowledge_svc.add_document(
                db, row, filename, file_content, None, visibility,
            )
        except SceneInvalidPackageError:
            raise
        except Exception:  # 单个资料失败不阻断导入（记录后跳过）
            import logging

            logging.getLogger("echotalk").exception("导入资料失败：%s / %s", scene_id, filename)

    registry.invalidate_cache()
    db.commit()
    db.refresh(row)
    return row, action


def raise_scene_conflict(existing: Scene) -> None:
    """按现有场景来源抛出对应冲突错误。"""
    from app.scenes.errors import SceneIdConflictError

    raise SceneIdConflictError(existing.id, existing.source)


def _next_available_id(db: Session, base_id: str) -> str:
    """生成可用改名 ID：base_2、base_3 …"""
    candidate = f"{base_id}_2"
    index = 2
    while db.get(Scene, candidate) is not None:
        index += 1
        candidate = f"{base_id}_{index}"
    return candidate


def row_time():
    """统一时间来源（懒加载封装）。"""
    from app.core.timeutil import utcnow

    return utcnow()
