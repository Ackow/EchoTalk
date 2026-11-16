#!/usr/bin/env bash
# EchoTalk 2.0 服务器首次初始化脚本（只拉取仓库中的 backend/ 目录）
# 用法：bash server-init.sh [部署目录]
#   默认部署目录 /opt/echotalk；已克隆过则自动跳过克隆，可重复执行（幂等）。
# 前提：SSH Deploy Key 或 PAT 已按 deploy/README.md §2.1 配好，能访问 GitHub。
set -euo pipefail

REPO="${REPO_URL:-git@github.com:Ackow/EchoTalk.git}"
APP_DIR="${1:-/opt/echotalk}"
BACKEND_DIR="$APP_DIR/backend"
BRANCH="main"
PLACEHOLDER="replace-with-strong-password"

echo "==> [1/5] 检查 uv"
if ! command -v uv > /dev/null 2>&1; then
  echo "    未安装 uv，正在安装..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

echo "==> [2/5] 拉取代码（sparse checkout，仅 backend/）"
if [ -d "$APP_DIR/.git" ]; then
  echo "    $APP_DIR 已存在仓库，跳过克隆"
  cd "$APP_DIR"
else
  git clone --filter=blob:none --sparse --branch "$BRANCH" "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi
# 确保 sparse 只含 backend/（对全量克隆过的仓库也生效）
git sparse-checkout init --cone 2> /dev/null || true
git sparse-checkout set backend
echo "    当前检出内容：$(ls "$APP_DIR" | tr '\n' ' ')"

echo "==> [3/5] 同步 Python 依赖（uv 按 uv.lock 精确复现，Python 3.12）"
cd "$BACKEND_DIR"
uv sync

echo "==> [4/5] 准备 .env 配置"
if [ ! -f .env ]; then
  cp deploy/.env.production.example .env
  chmod 600 .env
  echo "    已生成 .env，请立即编辑："
  echo "      nano $BACKEND_DIR/.env"
  echo "      必改项：ECHOTALK_DB_PASSWORD / ECHOTALK_CORS_ORIGINS"
  NEED_ENV=1
elif grep -q "$PLACEHOLDER" .env; then
  echo "    ⚠ .env 中数据库密码仍是占位符，请编辑 $BACKEND_DIR/.env 后重新运行本脚本"
  NEED_ENV=1
else
  echo "    .env 已配置"
  NEED_ENV=0
fi

echo "==> [5/5] 初始化数据表与场景包种子"
if [ "$NEED_ENV" = "1" ]; then
  echo "    跳过（.env 未就绪）。编辑好 .env 后重新运行本脚本即可完成初始化。"
else
  uv run python init_db.py
fi

if [ -n "${CF_TUNNEL_TOKEN:-}" ]; then
  echo ""
  echo "==> [可选] 检测到 CF_TUNNEL_TOKEN，正在配置 Cloudflare Tunnel..."
  sudo -E bash "$BACKEND_DIR/deploy/setup-tunnel.sh" "$CF_TUNNEL_TOKEN"
fi

API_PORT="8000"
if [ -f "$BACKEND_DIR/.env" ]; then
  _p="$(grep -E '^ECHOTALK_API_PORT=' "$BACKEND_DIR/.env" | tail -n 1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [ -n "$_p" ] && API_PORT="$_p"
fi

cat <<NEXT

============================================================
初始化完成。后续步骤：

  1. 若 .env 刚生成：编辑数据库密码、端口和 CORS 后重新运行本脚本
  2. 安装后端 systemd 常驻服务：
       sudo cp deploy/echotalk-backend.service /etc/systemd/system/
       sudo systemctl daemon-reload && sudo systemctl enable --now echotalk-backend
  3. 对外提供 HTTPS（二选一）：
       - 免备案方案（推荐）：配置 Cloudflare Tunnel 暴露 https://api.your-domain.com -> 127.0.0.1:${API_PORT}
           CF_TUNNEL_TOKEN="你的Token" sudo -E bash /opt/echotalk/backend/deploy/setup-tunnel.sh
       - 已备案方案：安装 Nginx + Certbot（见 deploy/README.md，proxy_pass 端口同步为 ${API_PORT}）
  4. 以后每次更新代码，只需在服务器上执行：
       bash /opt/echotalk/backend/deploy/update.sh
============================================================
NEXT
