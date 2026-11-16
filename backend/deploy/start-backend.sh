#!/usr/bin/env bash
# EchoTalk 2.0 后端启动包装脚本：统一从 backend/.env 读取监听地址、端口与 worker 数
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"

get_env() {
  local key="$1"
  local fallback="$2"
  if [ -f "$ENV_FILE" ]; then
    local val
    val="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -n "$val" ]; then
      echo "$val"
      return
    fi
  fi
  echo "$fallback"
}

API_HOST="$(get_env ECHOTALK_API_HOST 127.0.0.1)"
API_PORT="$(get_env ECHOTALK_API_PORT 8000)"
WORKERS="$(get_env ECHOTALK_WORKERS 1)"

cd "$BACKEND_DIR"
exec "$BACKEND_DIR/.venv/bin/python" -m uvicorn app.main:app \
  --host "$API_HOST" \
  --port "$API_PORT" \
  --workers "$WORKERS"
