"""时间工具：全项目统一的时间获取入口。"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """当前 UTC 时间（无时区标记），与数据库 DateTime 列的 naive 存储格式一致。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
