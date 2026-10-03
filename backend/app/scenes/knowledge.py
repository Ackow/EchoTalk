"""场景知识资料：源文件本地存储 + 解析分块入库（设计稿场景包方案 §5.4/§6）。

源文件存 backend/storage/scenes/{scene_id}/knowledge/，元数据存 documents/chunks 表。
向量索引为运行时产物（阶段 3 Hybrid RAG），本模块只负责源文件与分块——
导入导出携带源文件，索引用当前 embedding 重建，与模型版本解耦。
"""
import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sqlalchemy.orm import Session

from app.models import Chunk, Document, Scene
from app.scenes import lightrag_service as lightrag_svc
from app.scenes.errors import SceneNotFoundError, SceneUnsupportedFileError

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend 目录：本文件向上两级
load_dotenv(BACKEND_DIR / ".env", override=False)  # 与 config.py 一致：不覆盖已有环境变量

# 内置场景包自带资料的源文件目录（随代码分发，seed 时物化到 storage 与数据库）
CONTENT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "content" / "scenes" / "knowledge"

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

# 分节可见性标记（沿用 1.0 约定）：写在标题行内，解析后从标题中清理。
#   [user] / [用户]        → 该分节对用户可见
#   [ai] / [仅ai] / [仅 ai] → 该分节仅 AI 检索可见
_HEADING_VISIBILITY_RE = re.compile(
    r"\[\s*(user|用户|ai|仅\s*ai)\s*\]", re.IGNORECASE
)

# 文件名可见性前缀（沿用 1.0）：user_xxx.md 整文件用户可见；ai_xxx.md 整文件仅 AI。
_FILENAME_USER_PREFIXES = ("user_", "user-")
_FILENAME_AI_PREFIXES = ("ai_", "ai-")


def filename_visibility(filename: str) -> str | None:
    """文件名前缀 → 整文件可见性缺省（user_ / ai_ 前缀）；无前缀返回 None。"""
    name = Path(filename).name.lower()
    if name.startswith(_FILENAME_USER_PREFIXES):
        return "user"
    if name.startswith(_FILENAME_AI_PREFIXES):
        return "ai_only"
    return None


def _heading_visibility(heading_text: str) -> tuple[str | None, str]:
    """从标题文本提取可见性标记；返回 (visibility 或 None, 清理后的标题)。"""
    visibility = None
    match = _HEADING_VISIBILITY_RE.search(heading_text)
    if match:
        token = match.group(1).lower().replace(" ", "")
        visibility = "user" if token in ("user", "用户") else "ai_only"
    cleaned = _HEADING_VISIBILITY_RE.sub("", heading_text).strip()
    return visibility, cleaned


def parse_sections(filename: str, raw: str) -> list[tuple[str, str, str | None]]:
    """把文本解析为 (分节名, 分节文本, 分节可见性) 列表。

    Markdown 按 # 标题分节；无标题的 txt 以文件名（去扩展名）作为唯一分节。
    标题行内的 [user]/[ai] 标记决定该分节的可见性（None = 继承文件级缺省），
    标记本身会从分节名中清理掉。
    """
    if not _HEADING_RE.search(raw):  # 无标题：整个文件一个分节
        return [[Path(filename).stem, raw.strip(), None]]
    sections: list[tuple[str, str, str | None]] = []
    matches = list(_HEADING_RE.finditer(raw))
    head = raw[: matches[0].start()].strip()  # 首个标题前的引导文本
    if head:
        sections.append([Path(filename).stem, head, None])
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        visibility, name = _heading_visibility(match.group(2).strip())
        sections.append([name, raw[match.end():end].strip(), visibility])
    return [(name, text, vis) for name, text, vis in sections if text]


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


def chunk_document(filename: str, raw: str, default_visibility: str = "user") -> list[dict[str, Any]]:
    """解析 → 分节 → 分块；返回 [{section, ordinal, text, visibility}]。

    可见性优先级（沿用 1.0 的分节标记约定）：
    1. 标题行内标记 [user]/[ai]（最细粒度，作者显式标注）
    2. 文件名前缀 user_ / ai_（整文件显式约定）
    3. 文件级缺省 default_visibility（包声明 / 上传时选择的可见性）
    """
    prefix_visibility = filename_visibility(filename)
    result: list[dict[str, Any]] = []
    ordinal = 0
    for section_name, section_text, marker_visibility in parse_sections(filename, raw):
        visibility = marker_visibility or prefix_visibility or default_visibility
        for piece in _split_long_section(section_text):
            result.append({"section": section_name, "ordinal": ordinal, "text": piece, "visibility": visibility})
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
    chunks = chunk_document(filename, text, visibility)  # 分块可见性可被标题标记/文件名前缀覆盖
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
        visibility=visibility,  # 文件级缺省；分块实际可见性见 chunks.visibility
        created_at=document_time(),
    )
    db.add(document)
    db.flush()  # 取 document.id
    old_document_id = existing.id if existing is not None else None
    rows = []
    for chunk in chunks:
        row = Chunk(
            document_id=document.id,
            scene_id=scene.id,
            section=chunk["section"],
            visibility=chunk["visibility"],  # 优先级：标题标记 > 文件名前缀 > 文件级
            ordinal=chunk["ordinal"],
            text=chunk["text"],
        )
        db.add(row)
        rows.append(row)
    db.flush()  # 取各 chunk.id（提交后嵌入用）
    pending = [(row.id, row.text, "scene") for row in rows]
    db.commit()
    embed_chunks_best_effort(db, pending)  # 尽力嵌入：失败不影响上传结果
    # LightRAG 图谱索引维护（fire-and-forget）：同名更新时 document.id 变化，旧 id 需移除
    if old_document_id is not None and old_document_id != document.id:
        lightrag_svc.schedule_delete("scene", scene.id, old_document_id)
    lightrag_svc.schedule_upsert("scene", scene.id, document.id, text)
    return document


def embed_chunks_best_effort(db: Session, chunk_refs: list[tuple[int, str, str]]) -> int:
    """为分块生成并写入向量（尽力而为）：未配置 key 或上游失败时跳过。

    chunk_refs: [(chunk_id, text, kind)]，kind = 'scene' | 'personal'。
    返回写入条数；失败只记日志，由 reindex 端点补齐，绝不阻塞上传/编辑主流程。
    """
    from app.models import ChunkEmbedding, PersonalChunkEmbedding
    from app.scenes import embedding as embedding_svc

    if not chunk_refs or not embedding_svc.available():
        return 0
    try:
        vectors = embedding_svc.embed_texts([text for _, text, _ in chunk_refs])
    except Exception as exc:
        logger.warning("分块嵌入失败（可稍后 reindex 补齐）：%s", exc)
        return 0
    model = embedding_svc.config.EMBEDDING_MODEL
    for (chunk_id, _text, kind), vec in zip(chunk_refs, vectors):
        target = ChunkEmbedding if kind == "scene" else PersonalChunkEmbedding
        db.merge(target(chunk_id=chunk_id, model=model, embedding=embedding_svc.pack(vec)))
    db.commit()
    return len(vectors)


def reindex_scene(db: Session, scene_id: str) -> int:
    """为场景中缺失向量的分块补嵌（上传时嵌入失败 / 换模型后的全量重建入口）。"""
    from app.models import Chunk, ChunkEmbedding

    rows = (
        db.query(Chunk)
        .outerjoin(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
        .filter(Chunk.scene_id == scene_id, ChunkEmbedding.id.is_(None))
        .all()
    )
    return embed_chunks_best_effort(db, [(row.id, row.text, "scene") for row in rows])


def reindex_personal(db: Session, user_id: int) -> int:
    """为本人全部个人资料中缺失向量的分块补嵌。"""
    from app.models import PersonalChunk, PersonalChunkEmbedding, PersonalDocument

    rows = (
        db.query(PersonalChunk)
        .join(PersonalDocument, PersonalDocument.id == PersonalChunk.document_id)
        .outerjoin(PersonalChunkEmbedding, PersonalChunkEmbedding.chunk_id == PersonalChunk.id)
        .filter(PersonalDocument.owner_id == user_id, PersonalChunkEmbedding.id.is_(None))
        .all()
    )
    return embed_chunks_best_effort(db, [(row.id, row.text, "personal") for row in rows])


def document_time():
    """统一时间来源（避免循环导入的懒加载封装）。"""
    from app.core.timeutil import utcnow

    return utcnow()


def seed_builtin_documents(db: Session, scene: Scene, package) -> int:
    """把内置场景包声明的知识资料物化为 storage 文件 + documents/chunks（幂等）。

    场景包 YAML 只声明 knowledge.files 清单（path/visibility），内容源文件
    位于 content/scenes/knowledge/{scene_id}/；种子同步时若该文件尚无
    Document 记录则入库，已有记录则跳过（保留用户的分节可见性调整）。
    返回本次新物化的文件数。
    """
    seeded = 0
    for meta in package.knowledge.files:
        filename = Path(meta.path).name  # path 相对 knowledge/ 目录，取文件名落盘
        existing = db.query(Document).filter(Document.scene_id == scene.id, Document.filename == filename).first()
        if existing is not None:
            continue
        source = CONTENT_KNOWLEDGE_DIR / scene.id / filename
        if not source.exists():
            logger.warning("内置场景 %s 声明的资料缺少源文件：%s", scene.id, meta.path)
            continue
        add_document(db, scene, filename, source.read_bytes(), "text/markdown", meta.visibility)
        seeded += 1
    return seeded


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
    lightrag_svc.schedule_delete("scene", scene_id, document_id)  # 图谱索引同步清理
    return document


def list_documents(db: Session, scene_id: str) -> list[Document]:
    """场景资料元数据列表。"""
    return db.query(Document).filter(Document.scene_id == scene_id).order_by(Document.id).all()


def document_overview(db: Session, scene_id: str) -> list[dict[str, Any]]:
    """文件级资料概览：文件元数据 + 按文件分组的分节（知识工作区管理界面数据源）。"""
    documents = list_documents(db, scene_id)
    by_doc: dict[int, dict[str, dict[str, Any]]] = {}
    for row in db.query(Chunk).filter(Chunk.scene_id == scene_id).order_by(Chunk.id):
        agg = by_doc.setdefault(row.document_id, {}).setdefault(
            row.section or "_",
            {"section": row.section or "_", "visibility": row.visibility, "chunk_count": 0, "preview": ""},
        )
        agg["chunk_count"] += 1
        if not agg["preview"] and row.text:
            agg["preview"] = row.text[:120]
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "chunk_count": doc.chunk_count,
            "visibility": doc.visibility,
            "owner_id": doc.owner_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "sections": list(by_doc.get(doc.id, {}).values()),
        }
        for doc in documents
    ]


def list_document_chunks(db: Session, scene_id: str, document_id: int) -> list[dict[str, Any]]:
    """资料的分块明细（含正文全文，只读）：知识工作区查看数据源。编辑走源文件。"""
    rows = (
        db.query(Chunk)
        .filter(Chunk.scene_id == scene_id, Chunk.document_id == document_id)
        .order_by(Chunk.id)
        .all()
    )
    return [
        {
            "id": row.id,
            "section": row.section or "_",
            "ordinal": row.ordinal,
            "visibility": row.visibility,
            "text": row.text,
        }
        for row in rows
    ]


# 源文件文本可编辑的扩展名（pdf 为二进制提取结果，不支持文本回写）
EDITABLE_SOURCE_EXTENSIONS = {".md", ".markdown", ".txt"}


def read_document_source(db: Session, scene_id: str, document_id: int) -> dict[str, Any]:
    """资料源文件全文：知识工作区源文件编辑数据源（pdf 返回 editable=False）。"""
    document = (
        db.query(Document)
        .filter(Document.scene_id == scene_id, Document.id == document_id)
        .first()
    )
    if document is None:
        raise SceneNotFoundError(f"{scene_id}/knowledge/{document_id}")
    suffix = Path(document.filename).suffix.lower()
    if suffix not in EDITABLE_SOURCE_EXTENSIONS:
        return {"id": document.id, "filename": document.filename, "editable": False, "text": ""}
    path = knowledge_dir(scene_id) / document.filename
    if not path.exists():
        raise SceneNotFoundError(f"{scene_id}/knowledge/{document_id}/source")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SceneUnsupportedFileError(f"源文件不是有效的 UTF-8 文本：{document.filename}") from exc
    return {"id": document.id, "filename": document.filename, "editable": True, "text": text}


def update_document_source(db: Session, scene: Scene, document_id: int, text: str) -> Document:
    """编辑源文件并重新解析：覆盖写盘 → 同名重建 documents/chunks。

    分块是解析产物，编辑必须落在源文件上；重新解析后标题行 [user]/[ai]
    标记与文件名前缀重新生效（界面上对分节可见性的人工调整会被重置）。
    """
    document = (
        db.query(Document)
        .filter(Document.scene_id == scene.id, Document.id == document_id)
        .first()
    )
    if document is None:
        raise SceneNotFoundError(f"{scene.id}/knowledge/{document_id}")
    suffix = Path(document.filename).suffix.lower()
    if suffix not in EDITABLE_SOURCE_EXTENSIONS:
        raise SceneUnsupportedFileError("PDF 源文件不支持文本编辑，请删除后重新上传")
    if not text.strip():
        raise SceneUnsupportedFileError("源文件内容不能为空")
    # add_document 对同名资料先删后建（chunks 级联重建），并覆盖写盘
    return add_document(db, scene, document.filename, text.encode("utf-8"), document.content_type, document.visibility)


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


# ---- 个人工作区资料（阶段二）：跨场景复用，owner 隔离 -----------------------

def personal_dir(user_id: int) -> Path:
    """个人资料目录：按用户隔离，与场景资料（scenes/{id}/）互不混杂。"""
    return STORAGE_ROOT / "personal" / str(user_id) / "knowledge"


def add_personal_document(
    db: Session,
    user_id: int,
    filename: str,
    content: bytes,
    content_type: str | None,
) -> "PersonalDocument":
    """上传个人资料：保存源文件 → 解析分块 → 入库（同名覆盖即更新）。

    个人资料不做 ai/user 可见性区分：全部分块对用户可见，
    标题行 [user]/[ai] 标注仅从标题中清理，不改变可见性。
    """
    from app.models import PersonalChunk, PersonalDocument

    filename = Path(filename).name  # 防路径穿越：只取文件名部分
    check_extension(filename)
    if len(content) > MAX_FILE_SIZE:
        raise SceneUnsupportedFileError(f"文件过大（上限 10 MB）：{filename}")
    text = load_text(filename, content)
    chunks = chunk_document(filename, text, "user")
    if not chunks:
        raise SceneUnsupportedFileError(f"未能从文档中解析出有效文本：{filename}")
    for chunk in chunks:
        chunk["visibility"] = "user"  # 个人资料统一用户可见：标注不生效，仅被清理

    target_dir = personal_dir(user_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_bytes(content)

    existing = db.query(PersonalDocument).filter(
        PersonalDocument.owner_id == user_id, PersonalDocument.filename == filename
    ).first()
    old_document_id = existing.id if existing is not None else None
    if existing is not None:
        db.delete(existing)  # personal_chunks 随 CASCADE 级联删除
        db.flush()

    document = PersonalDocument(
        owner_id=user_id,
        filename=filename,
        content_type=content_type,
        chunk_count=len(chunks),
        created_at=document_time(),
    )
    db.add(document)
    db.flush()
    rows = []
    for chunk in chunks:
        row = PersonalChunk(
            document_id=document.id,
            section=chunk["section"],
            visibility=chunk["visibility"],  # 个人资料统一 user（写入前已强制）
            ordinal=chunk["ordinal"],
            text=chunk["text"],
        )
        db.add(row)
        rows.append(row)
    db.flush()  # 取各 chunk.id（提交后嵌入用）
    pending = [(row.id, row.text, "personal") for row in rows]
    db.commit()
    embed_chunks_best_effort(db, pending)
    # LightRAG 图谱索引维护（fire-and-forget）：同名更新时 document.id 变化，旧 id 需移除
    if old_document_id is not None and old_document_id != document.id:
        lightrag_svc.schedule_delete("personal", user_id, old_document_id)
    lightrag_svc.schedule_upsert("personal", user_id, document.id, text)
    return document


def _load_personal_document(db: Session, user_id: int, document_id: int) -> "PersonalDocument":
    """按 owner 装载个人资料：越权与不存在同报 404（不泄露存在性）。"""
    from app.models import PersonalDocument

    row = db.query(PersonalDocument).filter(
        PersonalDocument.id == document_id, PersonalDocument.owner_id == user_id
    ).first()
    if row is None:
        raise SceneNotFoundError(f"personal/{document_id}")
    return row


def personal_document_overview(db: Session, user_id: int) -> list[dict[str, Any]]:
    """个人资料文件级概览（含分节分组）：知识工作区个人页数据源。"""
    from app.models import PersonalChunk, PersonalDocument

    documents = db.query(PersonalDocument).filter(
        PersonalDocument.owner_id == user_id
    ).order_by(PersonalDocument.id).all()
    by_doc: dict[int, dict[str, dict[str, Any]]] = {}
    for row in db.query(PersonalChunk).join(PersonalDocument).filter(
        PersonalDocument.owner_id == user_id
    ).order_by(PersonalChunk.id):
        agg = by_doc.setdefault(row.document_id, {}).setdefault(
            row.section or "_",
            {"section": row.section or "_", "visibility": row.visibility, "chunk_count": 0, "preview": ""},
        )
        agg["chunk_count"] += 1
        if not agg["preview"] and row.text:
            agg["preview"] = row.text[:120]
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "chunk_count": doc.chunk_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "sections": list(by_doc.get(doc.id, {}).values()),
        }
        for doc in documents
    ]


def list_personal_chunks(db: Session, user_id: int, document_id: int) -> list[dict[str, Any]]:
    """个人资料的分块明细（只读）。"""
    from app.models import PersonalChunk

    _load_personal_document(db, user_id, document_id)
    rows = (
        db.query(PersonalChunk)
        .filter(PersonalChunk.document_id == document_id)
        .order_by(PersonalChunk.id)
        .all()
    )
    return [
        {"id": row.id, "section": row.section or "_", "ordinal": row.ordinal, "visibility": row.visibility, "text": row.text}
        for row in rows
    ]


def read_personal_source(db: Session, user_id: int, document_id: int) -> dict[str, Any]:
    """个人资料源文件全文（文本类可编辑，pdf 返回 editable=False）。"""
    document = _load_personal_document(db, user_id, document_id)
    suffix = Path(document.filename).suffix.lower()
    if suffix not in EDITABLE_SOURCE_EXTENSIONS:
        return {"id": document.id, "filename": document.filename, "editable": False, "text": ""}
    path = personal_dir(user_id) / document.filename
    if not path.exists():
        raise SceneNotFoundError(f"personal/{document_id}/source")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SceneUnsupportedFileError(f"源文件不是有效的 UTF-8 文本：{document.filename}") from exc
    return {"id": document.id, "filename": document.filename, "editable": True, "text": text}


def update_personal_source(db: Session, user_id: int, document_id: int, text: str) -> "PersonalDocument":
    """编辑个人资料源文件并重新解析（同名重建，document.id 变化）。"""
    document = _load_personal_document(db, user_id, document_id)
    suffix = Path(document.filename).suffix.lower()
    if suffix not in EDITABLE_SOURCE_EXTENSIONS:
        raise SceneUnsupportedFileError("PDF 源文件不支持文本编辑，请删除后重新上传")
    if not text.strip():
        raise SceneUnsupportedFileError("源文件内容不能为空")
    return add_personal_document(db, user_id, document.filename, text.encode("utf-8"), document.content_type)


def delete_personal_document(db: Session, user_id: int, document_id: int) -> "PersonalDocument":
    """删除个人资料：源文件 + 记录。"""
    from app.models import PersonalDocument

    document = _load_personal_document(db, user_id, document_id)
    target = personal_dir(user_id) / document.filename
    if target.exists():
        target.unlink()
    db.delete(document)  # personal_chunks 由 CASCADE 级联删除
    db.commit()
    lightrag_svc.schedule_delete("personal", user_id, document_id)  # 图谱索引同步清理
    return document
