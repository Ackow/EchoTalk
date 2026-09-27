import os
import re
from typing import List, Dict, Union
from pypdf import PdfReader

# ──────────────────────────────────────────────
# 分块输出格式：
# 返回 List[Dict]，每个分块包含:
#   {
#       "section": str,      # 节名称（如 "menu", "barista_workflow", "general"）
#       "content": str,      # 分块文本内容
#       "visibility": str    # "user" 或 "ai_only"（默认 ai_only，后续可调）
#   }
# ──────────────────────────────────────────────

# Markdown 标题正则（仅匹配二级标题，避免三级子标题拆分导致重复标题与表格破损）
HEADING_PATTERN = re.compile(r'^(##)\s+(.+)$', re.MULTILINE)

# 用于检测节类别的关键词映射
SECTION_KEYWORDS: Dict[str, List[str]] = {
    "menu": ["$", "price", "menu", "espresso", "latte", "cappuccino", "americano",
             "cold brew", "matcha", "chai latte", "hot chocolate", "breakfast",
             "bakery", "muffin", "bagel", "avocado toast", "surcharge", "pricing",
             "菜单", "价格", "价目", "点餐", "套餐"],
    "customization": ["tall", "grande", "venti", "size", "milk options", "oat milk",
                      "almond milk", "soy milk", "sweetener", "syrup", "half-sweet",
                      "ice levels", "temperature", "customization", "surcharges",
                      "定制", "规格", "杯型", "冰度", "糖度", "加冰"],
    "barista_workflow": ["barista", "workflow", "greeting", "upsell", "dine-in",
                         "to-go", "payment", "queue", "inventory", "out of stock",
                         "barista action", "service workflow", "steps",
                         "流程", "收银", "话术", "工作流", "动作", "服务规范"],
    "vocabulary": ["how to ask", "how to order", "vocabulary", "can i get",
                   "i'd like", "could i have", "terminology", "slang", "oral practice",
                   "常用词汇", "口语表达", "表达", "词汇"],
    "interview": ["interview", "candidate", "behavioral", "technical", "frontend",
                  "react", "vue", "javascript", "star method", "tell me about yourself",
                  "面试", "候选人", "自我介绍", "提问"],
    "meeting": ["meeting", "agenda", "deadline", "milestone", "sprint",
                "retrospective", "blocker", "sync", "alignment",
                "会议", "议程", "议题", "同步"],
}

# 默认对用户可见的节
USER_VISIBLE_SECTIONS = {"menu", "customization", "vocabulary", "interview_questions"}


class RecursiveTextSplitter:
    """
    纯 Python 实现的递归文本切片器。
    模拟 LangChain 的 RecursiveCharacterTextSplitter 逻辑，
    使用一组分隔符优先按段落、句子、词组进行递归切分，保证语义连贯性，避免截断关键句子。
    """
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 递归切分分隔符优先级：段落 -> 换行 -> 中文句尾 -> 英文句尾 -> 空格 -> 单字
        self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def _get_safe_overlap(self, text: str) -> str:
        """
        在重叠区边界寻找一个安全的单词/句子截断点（如空格、换行、中英文标点）。
        避免切出的分块开头出现半个单词或半句话。
        """
        if len(text) <= self.chunk_overlap:
            return text

        # 提取末尾重叠长度的候选串
        candidate = text[-self.chunk_overlap:]

        # 定义合法边界字符（空格、换行、中英文常用标点）
        boundaries = [' ', '\n', '\r', '。', '！', '？', '.', '!', '?', ';', '；', ',', '，']

        # 检查候选串的前 20 个字符，寻找第一个边界符号
        first_boundary = -1
        for i in range(min(20, len(candidate))):
            if candidate[i] in boundaries:
                first_boundary = i
                break

        if first_boundary != -1:
            # 丢弃第一个边界符号左侧的残缺字符，从完整单词或句子开始
            return candidate[first_boundary + 1:]
        return candidate

    def split_text(self, text: str) -> List[str]:
        return self._split_recursive(text, self.separators)

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        # 如果当前文本已经小于设定的分块大小，则无需再切
        if len(text) <= self.chunk_size:
            return [text]

        # 找到第一个在文本中存在的分隔符
        separator = ""
        next_separators = []
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                next_separators = separators[i:]
                break
            if sep in text:
                separator = sep
                next_separators = separators[i+1:]
                break

        # 按找到的分隔符拆分文本
        splits = text.split(separator) if separator != "" else list(text)

        # 将拆分后的小分块组合成符合大小和重叠要求的最终块
        chunks = []
        current_chunk = ""

        for split in splits:
            item = split + separator
            # 如果当前合并块大小未超过上限，继续累加
            if len(current_chunk) + len(item) <= self.chunk_size:
                current_chunk += item
            else:
                # 块溢出了，保存当前块
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # 创建新块，并保留重叠长度的尾部作为重叠区 (Overlap)
                current_chunk = self._get_safe_overlap(current_chunk) + item

        if current_chunk:
            chunks.append(current_chunk.strip())

        # 递归检查：如果某些合并后的块依然超过大小，使用剩余更细粒度的分隔符继续切分
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size and next_separators:
                final_chunks.extend(self._split_recursive(chunk, next_separators))
            else:
                final_chunks.append(chunk)

        return [c for c in final_chunks if c.strip()]


def extract_text_from_pdf(file_path: str) -> str:
    """
    使用 pypdf 从 PDF 文件中提取纯文本。
    """
    reader = PdfReader(file_path)
    text_content = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_content.append(text)
    return "\n".join(text_content)


def extract_text_from_txt_or_md(file_path: str) -> str:
    """
    读取 TXT 或 Markdown 文件的纯文本内容（包含 UTF-8、GB18030 和 GBK 编码容错机制）。
    """
    encodings = ["utf-8", "gb18030", "gbk", "utf-16"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # 兜底方案
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        pass

    raise UnicodeDecodeError(
        "utf-8", b"", 0, 0, f"无法以支持的编码读取文件: {os.path.basename(file_path)}"
    )


def extract_text_from_file(file_path: str) -> str:
    """
    统一文档提取入口：根据文件后缀名调用 PDF 提取或文本流读取。
    """
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".txt", ".md", ".markdown"]:
        return extract_text_from_txt_or_md(file_path)
    else:
        raise ValueError(f"暂不支持的文件格式: {ext}。请上传 PDF, TXT 或 Markdown 文档。")


def _detect_section_from_heading(heading_text: str) -> str:
    """
    根据 Markdown 标题文本判断其所属的节类别。
    """
    h_lower = heading_text.lower()

    for section_name, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in h_lower:
                return section_name

    return "general"


def _detect_section_from_content(content: str) -> str:
    """
    根据文本内容的关键词检测所属节类别（用于没有标题的纯文本段落）。
    """
    c_lower = content.lower()

    for section_name, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in c_lower:
                return section_name

    return "general"


def _split_document_into_sections(text: str) -> List[Dict[str, str]]:
    """
    将文档按 Markdown 标题 (## 级别) 拆分为节。
    返回 [{ "heading": str, "content": str, "section": str, "visibility": Optional[str] }, ...]
    """
    # 查找所有标题位置
    heading_matches = list(HEADING_PATTERN.finditer(text))

    if not heading_matches:
        # 没有标题：整篇作为一个节
        return [{
            "heading": "",
            "content": text.strip(),
            "section": _detect_section_from_content(text),
            "visibility": None
        }]

    sections = []
    for i, match in enumerate(heading_matches):
        heading_text = match.group(2).strip()
        start = match.end()
        end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(text)
        content = text[start:end].strip()

        # 检测标题中的可见性修饰符：[user] / [用户] / [ai] / [仅ai] / [仅 ai]
        h_lower = heading_text.lower()
        heading_visibility = None
        if "[user]" in h_lower or "[用户]" in h_lower:
            heading_visibility = "user"
        elif "[ai]" in h_lower or "[仅ai]" in h_lower or "[仅 ai]" in h_lower:
            heading_visibility = "ai_only"

        # 检测标题中的中文显示名称修饰符：[chinese:XXX] / [中文:XXX]
        chinese_match = re.search(r'\[(?:chinese|中文)\s*:\s*([^\]]+)\]', heading_text, flags=re.IGNORECASE)
        heading_chinese_title = None
        if chinese_match:
            heading_chinese_title = chinese_match.group(1).strip()

        # 清理标题文本，去掉可见性标记和显示名标记，展示更干净的标题
        cleaned_heading = re.sub(r'\s*\[(user|用户|ai|仅\s*ai)\]\s*', '', heading_text, flags=re.IGNORECASE).strip()
        cleaned_heading = re.sub(r'\s*\[(?:chinese|中文)\s*:\s*[^\]]+\]\s*', '', cleaned_heading, flags=re.IGNORECASE).strip()

        section_name = _detect_section_from_heading(cleaned_heading)
        sections.append({
            "heading": cleaned_heading,
            "content": content,
            "section": section_name,
            "visibility": heading_visibility,
            "title": heading_chinese_title
        })

    return sections


def get_document_chunks(
    file_path: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
    force_visibility: str = None,
    keep_user_sections_whole: bool = True
) -> List[Dict[str, str]]:
    """
    集成提取与切片：输入文档物理路径，自动读取内容并执行分节感知的切片。

    返回结构化分块列表，每个分块为:
    {
        "section": str,       # 节名称（如 "menu", "barista_workflow", "general"）
        "content": str,       # 分块文本内容
        "visibility": str     # "user" 或 "ai_only"（根据节类型自动推断默认值）
    }
    """
    text = extract_text_from_file(file_path)
    # 清理多余空行，精简格式
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 1. 先按 Markdown 标题拆分节
    sections = _split_document_into_sections(text)

    # 检测文件名自动可见性分类前缀
    filename = os.path.basename(file_path).lower()
    filename_visibility = None
    if filename.startswith("user_") or filename.startswith("user-"):
        filename_visibility = "user"
    elif filename.startswith("ai_") or filename.startswith("ai-"):
        filename_visibility = "ai_only"

    structured_chunks = []
    for sec in sections:
        sec_name = sec["section"]
        sec_content = sec["content"]

        if not sec_content:
            continue

        # 确定可见性规则优先级：
        # 1. 显式接口参数 (force_visibility)
        # 2. 文件名前缀 (filename_visibility)
        # 3. 章节标题修饰符 (sec.get("visibility"))
        # 4. 根据节类别默认推断
        if force_visibility in ("user", "ai_only"):
            final_visibility = force_visibility
        elif filename_visibility is not None:
            final_visibility = filename_visibility
        elif sec.get("visibility") is not None:
            final_visibility = sec["visibility"]
        else:
            is_user_visible = sec_name in USER_VISIBLE_SECTIONS
            final_visibility = "user" if is_user_visible else "ai_only"

        # 提取节标题 + 内容作为基础文本
        heading_prefix = f"## {sec['heading']}\n\n" if sec["heading"] else ""
        full_text = heading_prefix + sec_content

        # 如果启用 keep_user_sections_whole 且该章节对用户可见，则使用超大窗口（不切片），防止表格损坏与标题重复
        if keep_user_sections_whole and final_visibility == "user":
            current_chunk_size = 10000
            current_overlap = 0
        else:
            current_chunk_size = chunk_size
            current_overlap = chunk_overlap

        # 对本节内容进行递归切片
        splitter = RecursiveTextSplitter(chunk_size=current_chunk_size, chunk_overlap=current_overlap)
        text_chunks = splitter.split_text(full_text)

        for tc in text_chunks:
            if tc.strip():
                structured_chunks.append({
                    "section": sec_name,
                    "content": tc,
                    "visibility": final_visibility,
                    "title": sec.get("title")
                })

    return structured_chunks
