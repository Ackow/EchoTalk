import os
import sys

# 将 backend 目录添加到 Python 路径中，以便能够导入 app 包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document import extract_text_from_file, get_document_chunks

# 测试文件目录 — 知识库种子文件已迁移至 app/data/rag_seeds/
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data", "rag_seeds")

def test_document_extraction_and_splitting():
    """
    测试文档解析与分块切片功能是否正常，覆盖不同场景的测试资料
    """
    test_files = [
        {"name": "interview_prep.txt", "label": "软件工程师面试资料"},
        {"name": "cafe_menu.txt", "label": "咖啡厅点单资料"},
        {"name": "meeting_brief.txt", "label": "产品发布同步会资料"}
    ]

    print("--- [文档解析与递归切片测试开始] ---")

    for file_info in test_files:
        file_path = os.path.join(DATA_DIR, file_info["name"])
        
        # 1. 验证文件存在性
        assert os.path.exists(file_path), f"测试文件不存在: {file_info['name']}"
        
        # 2. 提取文本并验证非空
        raw_text = extract_text_from_file(file_path)
        print(f"\n[读取文件] {file_info['label']} ({file_info['name']})")
        print(f"原始字数: {len(raw_text)}")
        assert len(raw_text) > 0, "文本提取内容不能为空！"
        
        # 3. 对文本执行切片分块（设置 chunk_size = 300, overlap = 50）
        chunk_size = 300
        chunk_overlap = 50
        chunks = get_document_chunks(
            file_path, 
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap, 
            keep_user_sections_whole=False
        )
        
        print(f"切片数量: {len(chunks)} 个分块")
        assert len(chunks) > 0, "分块切割结果不能为空！"
        
        # 4. 验证每一块大小都不超出上限，并且打印分块演示
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= chunk_size, f"分块 {i} 长度超过限制: {len(chunk)}"
            print(f"-> 第{i}个分块内容 (长度 {len(chunk)}):\n" + "=" * 40)
            print(chunk)
            print("=" * 40)
            # if i == 0:
            #     print(f"-> 演示首个分块内容 (长度 {len(chunk)}):\n" + "=" * 40)
            #     print(chunk)
            #     print("=" * 40)
                
    print("\n[SUCCESS] 文档读取与递归分块算法全部通过测试！")

def test_gb18030_emoji_document():
    """
    测试能够成功解析包含 Emoji 的 GB18030 / GBK 编码的文件
    """
    test_text = "这是一份包含表情符号😊和稀有字的文档。"
    temp_file = os.path.join(DATA_DIR, "temp_gb18030_emoji.txt")
    
    try:
        # 以 gb18030 编码写入
        with open(temp_file, "w", encoding="gb18030") as f:
            f.write(test_text)
            
        # 调用解析函数
        parsed_text = extract_text_from_file(temp_file)
        assert parsed_text == test_text, f"解析内容不一致！期望: {test_text}, 实际: {parsed_text}"
        print("[SUCCESS] 成功解析包含 Emoji 的 GB18030 编码文件！")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_custom_display_title_parsing():
    """
    测试能够成功解析标题中的可见性和自定义中文名称标签，并进行内容清理
    """
    test_text = "## Test Section [user] [chinese:自定义中文标题]\n\nThis is some test content."
    temp_file = os.path.join(DATA_DIR, "temp_custom_title_test.txt")
    
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(test_text)
            
        chunks = get_document_chunks(temp_file, keep_user_sections_whole=True)
        assert len(chunks) == 1, "切片数量应该为 1"
        chunk = chunks[0]
        
        # 验证字段
        assert chunk["visibility"] == "user", f"可见性期望为 user，实际为: {chunk['visibility']}"
        assert chunk["title"] == "自定义中文标题", f"中文标题期望为 自定义中文标题，实际为: {chunk['title']}"
        
        # 验证标题清理，内容中不应当包含 [user] 和 [chinese:...]
        assert "[user]" not in chunk["content"], "内容中不应包含 [user] 标签"
        assert "chinese" not in chunk["content"], "内容中不应包含 [chinese] 标签"
        assert "## Test Section" in chunk["content"], "内容中应包含清理后的标题"
        print("[SUCCESS] 成功解析并清理标题中的自定义中文显示标题标签！")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    try:
        test_document_extraction_and_splitting()
        test_gb18030_emoji_document()
        test_custom_display_title_parsing()
    except AssertionError as e:
        print(f"\n[FAIL] 测试发生错误: {e}")
        sys.exit(1)
