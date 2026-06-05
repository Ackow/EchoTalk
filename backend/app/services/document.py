import os
import re
from typing import List
from pypdf import PdfReader

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
    读取 TXT 或 Markdown 文件的纯文本内容（包含 UTF-8 和 GBK 编码容错机制）。
    """
    encodings = ["utf-8", "gbk", "utf-16"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
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


def get_document_chunks(file_path: str, chunk_size: int = 400, chunk_overlap: int = 50) -> List[str]:
    """
    集成提取与切片：输入文档物理路径，自动读取内容并进行分块切片。
    """
    text = extract_text_from_file(file_path)
    # 清理多余空行，精简格式
    text = re.sub(r'\n{3,}', '\n\n', text)
    splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)
