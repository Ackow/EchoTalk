#!/usr/bin/env bash
# EchoTalk 2.0 云端一键更新脚本
# 用法（服务器上）：bash /opt/echotalk/backend/deploy/update.sh
# 前提：按 deploy/README.md 完成首次部署；代码位于 /opt/echotalk；服务名 echotalk-backend
set -euo pipefail

APP_DIR="/opt/echotalk"
BACKEND_DIR="$APP_DIR/backend"
SERVICE="echotalk-backend"
BACKUP_DIR="/opt/echotalk/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB_USER="echotalk_app"
DB_NAME="echotalk"

echo "==> [1/6] 更新前备份（数据库 + storage 文件）"
mkdir -p "$BACKUP_DIR"
# 数据库备份（读取 .env 中的密码，避免明文出现在命令行）
DB_PASSWORD="$(grep -E '^ECHOTALK_DB_PASSWORD=' "$BACKEND_DIR/.env" | cut -d= -f2-)"
mysqldump -u "$DB_USER" -p"$DB_PASSWORD" --single-transaction "$DB_NAME" \
  | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"
# 文件存储备份（场景封面/知识资料等落盘文件）
if [ -d "$BACKEND_DIR/storage" ]; then
  tar -czf "$BACKUP_DIR/storage-$STAMP.tar.gz" -C "$BACKEND_DIR" storage
fi
# 清理 14 天前的备份
find "$BACKUP_DIR" -name '*.gz' -mtime +14 -delete
echo "    备份完成：$BACKUP_DIR/*-$STAMP.*"

echo "==> [2/6] 拉取最新代码"
cd "$APP_DIR"
git pull --ff-only

echo "==> [3/6] 同步依赖（uv 按 uv.lock 精确复现）"
cd "$BACKEND_DIR"
uv sync

echo "==> [4/6] 初始化新表 / 同步场景包种子（幂等，可重复执行）"
uv run python init_db.py

echo "==> [5/6] 重启服务"
sudo systemctl restart "$SERVICE"

echo "==> [6/6] 健康检查"
sleep 2
for i in 1 2 3 4 5; do
  if curl -fs http://127.0.0.1:8000/api/ready > /dev/null; then
    echo "✅ 更新完成，服务就绪：$(curl -fs http://127.0.0.1:8000/api/health)"
    exit 0
  fi
  echo "    等待服务就绪... ($i/5)"
  sleep 3
done

echo "❌ 服务未就绪，请查看日志：" >&2
echo "   journalctl -u $SERVICE -n 100 --no-pager" >&2
echo "   如需回滚：git reset --hard <上一版本号> 后重新执行本脚本" >&2
exit 1
