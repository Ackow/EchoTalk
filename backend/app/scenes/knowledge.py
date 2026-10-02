"""场景知识资料：源文件本地存储 + 解析分块入库（设计稿场景包方案 §5.4/§6）。

源文件存 backend/storage/scenes/{scene_id}/knowledge/，元数据存 documents/chunks 表。
向量索引为运行时产物（阶段 3 Hybrid RAG），本模块只负责源文件与分块——
导入导出携带源文件，索引用当前 embedding 重建，与模型版本解耦。
"""
import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sqlalchemy.orm import Session

from app.models import Chunk, Document, Scene
from app.scenes.errors import SceneNotFoundError, SceneUnsupportedFileError

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend 目录：本文件向上两级
load_dotenv(BACKEND_DIR / ".env", override=False)  # 与 config.py 一致：不覆盖已有环境变量

# 文件存储根目录：默认 backend/storage/，可用 ECHOTALK_STORAGE_ROOT 指向数据盘等外部路径
STORAGE_ROOT = Path(os.getenv("ECHOTALK_STORAGE_ROOT", str(BACKEND_DIR / "storage"))).resolve()
ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 单文件 10 MB（§9.5）
SECTION_CHUNK_TARGET = 700  # 分块目标长度（字符）
SECTION_CHUNK_MAX = 1100  # 分块上限：超过则按段落二次切分
ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}  # 封面图格式
MAX_COVER_SIZE = 5 * 1024 * 1024  # 封面上限 5 MB


def knowledge_dir(scene_id: str) -> Path:
    """场景资料目录：按场景 id 隔离，天然限定检索与导出范围。"""
    return STORAGE_ROOT / "scenes" / scene_id / "knowledge"


def check_extension(filename: str) -> str:
    """校验扩展名：pdf/txt/md/markdown（§9.5），返回小写扩展名。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        supported = "、".join(sorted(ALLOWED_EXTENSIONS))
        raise SceneUnsupportedFileError(f"不支持的文件类型 '{suffix or filename}'，仅支持：{supported}")
    return suffix


def save_file(scene_id: str, filename: str, content: bytes) -> Path:
    """把资料源文件写入本地存储（覆盖同名文件）。"""
    check_extension(filename)
    if len(content) > MAX_FILE_SIZE:
        raise SceneUnsupportedFileError(f"文件过大（上限 10 MB）：{filename}")
    target_dir = knowledge_dir(scene_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    target.write_bytes(content)  # 同名覆盖：重复上传即更新
    return target


def delete_file(scene_id: str, filename: str) -> None:
    """删除资料源文件（不存在时静默）。"""
    target = knowledge_dir(scene_id) / filename
    if target.exists():
        target.unlink()


def remove_scene_files(scene_id: str) -> None:
    """删除场景的整个资料目录（删除场景时调用）。"""
    target = STORAGE_ROOT / "scenes" / scene_id
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


# ---- 封面图 -----------------------------------------------------------------

def save_cover(scene_id: str, filename: str, content: bytes) -> str:
    """保存封面图并返回相对路径（存 scenes.cover_path，同名旧封面按扩展名清理）。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_COVER_EXTENSIONS:
        supported = "、".join(sorted(ALLOWED_COVER_EXTENSIONS))
        raise SceneUnsupportedFileError(f"不支持的封面格式 '{suffix or filename}'，仅支持：{supported}")
    if len(content) > MAX_COVER_SIZE:
        raise SceneUnsupportedFileError("封面图片过大（上限 5 MB）")
    target_dir = STORAGE_ROOT / "scenes" / scene_id
    target_dir.mkdir(parents=True, exist_ok=True)
    for old in target_dir.glob("cover.*"):  # 扩展名可能变化：先清理旧封面
        old.unlink()
    target = target_dir / f"cover{suffix}"
    target.write_bytes(content)
    return f"scenes/{scene_id}/cover{suffix}"


def cover_file(relative_path: str) -> Path:
    """相对路径 → 本地文件路径（GET 封面端点用）。"""
    return STORAGE_ROOT / relative_path


# ---- 解析与分块 ------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def parse_sections(filename: str, raw: str) -> list[tuple[str, str]]:
    """把文本解析为 (分节名, 分节文本) 列表。

    Markdown 按 # 标题分节；无标题的 txt 以文件名（去扩展名）作为唯一分节。
    """
    if not _HEADING_RE.search(raw):  # 无标题：整个文件一个分节
        return [[Path(filename).stem, raw.strip()]]
    sections: list[tuple[str, str]] = []
    matches = list(_HEADING_RE.finditer(raw))
    head = raw[: matches[0].start()].strip()  # 首个标题前的引导文本
    if head:
        sections.append([Path(filename).stem, head])
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        sections.append([match.group(2).strip(), raw[match.end():end].strip()])
    return [(name, text) for name, text in sections if text]


def _split_long_section(text: str) -> list[str]:
    """超长分节按空行段落累积切分，控制在目标块长附近。"""
    if len(text) <= SECTION_CHUNK_MAX:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) > SECTION_CHUNK_MAX and buffer:
            chunks.append(buffer)
            buffer = paragraph
        else:
            buffer = candidate
        if len(buffer) >= SECTION_CHUNK_TARGET and len(buffer) + 60 > SECTION_CHUNK_TARGET:
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks or [text]


def chunk_document(filename: str, raw: str) -> list[dict[str, Any]]:
    """解析 → 分节 → 分块；返回 [{section, ordinal, text}]。"""
    result: list[dict[str, Any]] = []
    ordinal = 0
    for section_name, section_text in parse_sections(filename, raw):
        for piece in _split_long_section(section_text):
            result.append({"section": section_name, "ordinal": ordinal, "text": piece})
            ordinal += 1
    return result


def extract_text_from_pdf(content: bytes) -> str:
    """从 PDF 提取文本：pypdf 可用时按页提取，否则抛可解释错误。"""
    try:
        from pypdf import PdfReader  # 延迟导入：PDF 支持可选
    except ImportError as exc:
        raise SceneUnsupportedFileError(
            "PDF 解析组件未安装，请先上传 txt/md，或安装 pypdf 后重试"
        ) from exc
    import io

    reader = PdfReader(io.BytesIO(content))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(page for page in pages if page.strip())


def load_text(filename: str, content: bytes) -> str:
    """按扩展名把文件内容解码为文本（pdf 走提取，其余按 UTF-8）。"""
    suffix = check_extension(filename)
    if suffix == ".pdf":
        return extract_text_from_pdf(content)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SceneUnsupportedFileError(f"文件不是有效的 UTF-8 文本：{filename}") from exc


# ---- 入库操作 ---------------------------------------------------------------

def add_document(
    db: Session,
    scene: Scene,
    filename: str,
    content: bytes,
    content_type: str | None,
    visibility: str,
) -> Document:
    """保存源文件 → 解析分块 → 写 documents/chunks（同名资料先删后建，幂等更新）。"""
    text = load_text(filename, content)
    chunks = chunk_document(filename, text)
    if not chunks:
        raise SceneUnsupportedFileError(f"未能从文档中解析出有效文本：{filename}")

    save_file(scene.id, filename, content)

    # 同名资料先删旧记录（chunks 随文档级联删除）
    existing = db.query(Document).filter(Document.scene_id == scene.id, Document.filename == filename).first()
    if existing is not None:
        db.delete(existing)
        db.flush()

    document = Document(
        scene_id=scene.id,
        owner_id=scene.author_id,
        filename=filename,
        content_type=content_type,
        chunk_count=len(chunks),
        visibility=visibility,
        created_at=document_time(),
    )
    db.add(document)
    db.flush()  # 取 document.id
    for chunk in chunks:
        db.add(
            Chunk(
                document_id=document.id,
                scene_id=scene.id,
                section=chunk["section"],
                visibility=visibility,  # 文件级缺省；可被 PATCH 分节接口覆盖
                ordinal=chunk["ordinal"],
                text=chunk["text"],
            )
        )
    db.commit()
    return document


def document_time():
    """统一时间来源（避免循环导入的懒加载封装）。"""
    from app.core.timeutil import utcnow

    return utcnow()


def delete_document(db: Session, scene_id: str, document_id: int) -> Document:
    """删除单个资料：源文件 + 文档与分块记录。"""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.scene_id == scene_id)
        .first()
    )
    if document is None:
        raise SceneNotFoundError(f"{scene_id}/knowledge/{document_id}")
    delete_file(scene_id, document.filename)
    db.delete(document)  # chunks 由 CASCADE 级联删除
    db.commit()
    return document


def list_documents(db: Session, scene_id: str) -> list[Document]:
    """场景资料元数据列表。"""
    return db.query(Document).filter(Document.scene_id == scene_id).order_by(Document.id).all()


def visible_sections(db: Session, scene_id: str, only_user: bool = True) -> list[dict[str, Any]]:
    """分节概览：{section, visibility, chunk_count, preview}；only_user 时仅 user 可见分节。"""
    query = db.query(Chunk).filter(Chunk.scene_id == scene_id)
    if only_user:
        query = query.filter(Chunk.visibility == "user")
    rows = query.order_by(Chunk.id).all()
    overview: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = overview.setdefault(
            row.section or "_",
            {"section": row.section or "_", "visibility": row.visibility, "chunk_count": 0, "preview": ""},
        )
        entry["chunk_count"] += 1
        if not entry["preview"] and row.text:
            entry["preview"] = row.text[:120]
    return list(overview.values())


def set_section_visibility(db: Session, scene_id: str, section: str, visibility: str) -> int:
    """修改分节可见性（user ↔ ai_only）；返回更新的分块数。"""
    rows = db.query(Chunk).filter(Chunk.scene_id == scene_id, Chunk.section == section).all()
    if not rows:
        raise SceneNotFoundError(f"{scene_id}/knowledge/sections/{section}")
    for row in rows:
        row.visibility = visibility
    db.commit()
    return len(rows)


def file_checksum(content: bytes) -> str:
    """文件 SHA-256（manifest 校验和用）。"""
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
