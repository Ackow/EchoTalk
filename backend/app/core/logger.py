import os
import sys
import logging
from app.core.config import settings

class SafeStreamHandler(logging.StreamHandler):
    """
    Windows 控制台安全输出 Handler，防止由于编码不支持（如 GBK 终端输出特殊字符）而导致 crash。
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                encoding = getattr(stream, 'encoding', None) or 'gbk'
                safe_msg = msg.encode(encoding, errors='replace').decode(encoding)
                stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# 创建并配置全局 logger
logger = logging.getLogger("echotalk")
logger.setLevel(logging.INFO)

# 避免在多次导入或 reload 时重复添加 handlers
if not logger.handlers:
    # 统一的日志输出格式
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. 控制台安全输出 Handler
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 写入本地日志文件的 TimedRotatingFileHandler (按日期切分，保留最多10个日志文件)
    log_dir = os.path.join(settings.writeable_base_dir, "logs")
    log_file_path = os.path.join(log_dir, "echotalk.log")
    try:
        # 确保 logs 目录存在
        os.makedirs(log_dir, exist_ok=True)
        from logging.handlers import TimedRotatingFileHandler
        file_handler = TimedRotatingFileHandler(
            log_file_path,
            when='D',           # D=按天切割日志
            interval=1,         # 间隔1天生成新日志
            backupCount=10,     # 最多保留10天历史日志，自动删除老旧文件
            encoding='utf-8',   # 文件强制utf8存储，无中文乱码
            delay=True          # 延迟创建文件：第一条日志产生时才新建log文件，空跑不生成空白日志
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 防止因权限不足或只读路径等原因导致程序崩溃
        print(f"[Logger Warning] 无法创建日志文件 Handler ({log_file_path}): {e}", file=sys.stderr)

def log_api_call(
    api_type: str, 
    provider: str, 
    url: str, 
    model: str, 
    action: str, 
    status: str = "pending", 
    extra_info: str = None
):
    """
    格式化输出 API 调用日志提示，让用户/开发者在控制台和日志文件一眼能够识别调用了哪个 API。
    支持 "pending"（开始）、"success"（成功）、"failed"（失败）三种状态。
    """
    border = "=" * 55
    lines = []
    
    if status == "pending":
        lines.append(border)
        lines.append("【API 调用提示 - 发起请求 >>>】")
        lines.append(f"  * 调用类型  : {api_type}")
        lines.append(f"  * 核心提供商: {provider}")
        lines.append(f"  * 接口端点  : {url}")
        lines.append(f"  * 请求模型  : {model}")
        lines.append(f"  * 业务动作  : {action}")
        if extra_info:
            lines.append(f"  * 附加参数  : {extra_info}")
        lines.append(border)
    elif status == "success":
        lines.append(border)
        lines.append("【API 调用提示 - 请求成功 [OK]】")
        lines.append(f"  * 调用类型  : {api_type}")
        lines.append(f"  * 提供商/端点: {provider} ({url})")
        lines.append(f"  * 模型版本  : {model}")
        if extra_info:
            lines.append(f"  * 响应概要  : {extra_info}")
        lines.append(border)
    elif status == "failed":
        lines.append(border)
        lines.append("【API 调用提示 - 调用异常 [FAIL]】")
        lines.append(f"  * 调用类型  : {api_type}")
        lines.append(f"  * 提供商/端点: {provider} ({url})")
        lines.append(f"  * 异常原因  : {extra_info}")
        lines.append(border)

    if lines:
        # 在多行日志块前面追加一个换行，使得多行块在控制台和文件中更容易区分
        log_content = "\n" + "\n".join(lines)
        if status == "failed":
            logger.error(log_content)
        else:
            logger.info(log_content)

