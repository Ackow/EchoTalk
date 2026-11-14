"""时间工具：全项目统一的时间获取入口（北京时间 UTC+8）。"""
from datetime import datetime, timedelta, timezone

_CN_TZ = timezone(timedelta(hours=8))


def utcnow() -> datetime:
    """当前北京时间（UTC+8，无时区标记），与数据库 DateTime 列的 naive 存储格式一致。"""
    return datetime.now(_CN_TZ).replace(tzinfo=None)
