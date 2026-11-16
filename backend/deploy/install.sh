#!/usr/bin/env bash
# EchoTalk 2.0 服务器交互式一键部署脚本（Ubuntu / Debian）
# 将 README 中的全部繁琐步骤整合为交互式引导，可重复运行（幂等）。
# 用法：sudo bash install.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ 请使用 sudo 或 root 运行：sudo bash $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO="https://github.com/Ackow/EchoTalk.git"
DEFAULT_SSH_REPO="git@github.com:Ackow/EchoTalk.git"

ask() {
  local prompt="$1" default="${2:-}" var
  if [ -n "$default" ]; then
    read -r -p "$prompt [$default]: " var
    echo "${var:-$default}"
  else
    read -r -p "$prompt: " var
    echo "$var"
  fi
}

ask_secret() {
  local prompt="$1" var
  read -r -s -p "$prompt: " var
  echo "" >&2
  echo "$var"
}

ask_yn() {
  local prompt="$1" default="${2:-y}" ans
  local hint="Y/n"
  [ "$default" = "n" ] && hint="y/N"
  read -r -p "$prompt [$hint]: " ans
  ans="${ans:-$default}"
  case "$ans" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

set_env_kv() {
  local file="$1" key="$2" val="$3"
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    python3 - "$file" "$key" "$val" <<'PY'
import sys
p, k, v = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(p, encoding="utf-8").read().splitlines()
out = [f"{k}={v}" if l.startswith(f"{k}=") else l for l in lines]
open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}

echo "============================================================"
echo "  EchoTalk 2.0 后端一键交互式部署向导"
echo "============================================================"

# ---- 1. 基础环境、Swap 与防火墙 ----
echo ""
echo "==> [1/8] 系统基础组件、Swap 与防火墙"
if ask_yn "是否更新 apt 并安装基础工具 (git, curl, python3)？" "y"; then
  apt-get update -y
  apt-get install -y git curl ca-certificates gnupg lsb-release python3
fi

if ! swapon --show | grep -q '/swapfile'; then
  if ask_yn "是否创建 2GB Swap（推荐 4G 以下或空闲 1-2G 内存机器开启）？" "y"; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "    ✅ 2GB Swap 已启用"
  fi
fi

# ---- 2. 选择对外暴露方式（提前确定监听地址与端口） ----
echo ""
echo "==> [2/8] 选择对外访问方式"
echo "  1) Cloudflare Tunnel（免备案推荐，后端仅监听 127.0.0.1）"
echo "  2) Nginx 反向代理 + HTTPS（需已备案域名，后端监听 127.0.0.1）"
echo "  3) 直接 IP:端口 访问（测试/内网用，后端监听 0.0.0.0）"
EXPOSE_MODE="$(ask "请选择 [1/2/3]" "1")"

DEFAULT_API_HOST="127.0.0.1"
[ "$EXPOSE_MODE" = "3" ] && DEFAULT_API_HOST="0.0.0.0"
API_HOST="$(ask "后端监听地址 ECHOTALK_API_HOST" "$DEFAULT_API_HOST")"
API_PORT="$(ask "后端监听端口 ECHOTALK_API_PORT" "8000")"
WORKERS="$(ask "uvicorn worker 数量（1-2G 可用内存建议 1）" "1")"

if command -v ufw > /dev/null 2>&1; then
  if ask_yn "是否配置 UFW 防火墙（放行 SSH/80/443，不放行 3306）？" "y"; then
    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    if [ "$EXPOSE_MODE" = "3" ]; then
      ufw allow "${API_PORT}/tcp"
    fi
    ufw --force enable
    ufw status
  fi
fi

# ---- 3. MySQL 8 安装与建库建号 ----
echo ""
echo "==> [3/8] MySQL 8 安装与数据库初始化"
DB_HOST="$(ask "MySQL 主机 ECHOTALK_DB_HOST" "127.0.0.1")"
DB_PORT="$(ask "MySQL 端口 ECHOTALK_DB_PORT" "3306")"
DB_NAME="$(ask "数据库名 ECHOTALK_DB_NAME" "echotalk")"
DB_USER="$(ask "数据库用户名 ECHOTALK_DB_USER" "echotalk_app")"

if ask_yn "是否在本机安装/配置 MySQL 8 并自动建库建号？" "y"; then
  if ! command -v mysql > /dev/null 2>&1; then
    apt-get install -y mysql-server
  fi
  systemctl enable --now mysql

  DB_PASS="$(ask_secret "请设置数据库密码（留空则自动生成 20 位随机强密码）")"
  if [ -z "$DB_PASS" ]; then
    DB_PASS="$(tr -dc 'A-Za-z0-9@#%_' < /dev/urandom | head -c 20)"
    echo "    已自动生成数据库密码：$DB_PASS"
  fi

  mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
  echo "    ✅ MySQL 库与账号就绪"
else
  DB_PASS="$(ask_secret "请输入已有数据库密码 ECHOTALK_DB_PASSWORD")"
fi

# ---- 4. 拉取代码（sparse checkout 仅 backend/） ----
echo ""
echo "==> [4/8] 拉取 EchoTalk 代码"
APP_DIR="$(ask "部署目录" "/opt/echotalk")"
BACKEND_DIR="$APP_DIR/backend"

if [ -d "$APP_DIR/.git" ]; then
  echo "    检测到 $APP_DIR 已存在仓库，执行更新..."
  git -C "$APP_DIR" sparse-checkout init --cone 2> /dev/null || true
  git -C "$APP_DIR" sparse-checkout set backend
  git -C "$APP_DIR" pull --ff-only || true
else
  echo "  选择拉取方式："
  echo "    1) 公开仓库 HTTPS 克隆（无需密钥）"
  echo "    2) 私有仓库 SSH Deploy Key（自动生成密钥）"
  echo "    3) 私有仓库 HTTPS + GitHub Token (PAT)"
  CLONE_MODE="$(ask "请选择 [1/2/3]" "1")"

  if [ "$CLONE_MODE" = "2" ]; then
    KEY_PATH="$HOME/.ssh/echotalk_deploy"
    if [ ! -f "$KEY_PATH" ]; then
      mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
      ssh-keygen -t ed25519 -C "echotalk-server-deploy" -f "$KEY_PATH" -N ""
      cat >> "$HOME/.ssh/config" <<CONF
Host github.com
  IdentityFile $KEY_PATH
  IdentitiesOnly yes
CONF
      chmod 600 "$HOME/.ssh/config"
    fi
    echo ""
    echo "请复制下方公钥添加到 GitHub 仓库 Settings -> Deploy keys："
    echo "------------------------------------------------------------"
    cat "${KEY_PATH}.pub"
    echo "------------------------------------------------------------"
    read -r -p "添加完成后按回车继续..." _
    ssh -o StrictHostKeyChecking=accept-new -T git@github.com || true
    git clone --filter=blob:none --sparse --branch main "$DEFAULT_SSH_REPO" "$APP_DIR"
  elif [ "$CLONE_MODE" = "3" ]; then
    GH_PAT="$(ask_secret "请输入 GitHub Fine-grained PAT")"
    git clone --filter=blob:none --sparse --branch main "https://${GH_PAT}@github.com/Ackow/EchoTalk.git" "$APP_DIR"
    chmod 600 "$APP_DIR/.git/config"
  else
    git clone --filter=blob:none --sparse --branch main "$DEFAULT_REPO" "$APP_DIR"
  fi
  git -C "$APP_DIR" sparse-checkout init --cone
  git -C "$APP_DIR" sparse-checkout set backend
fi

# ---- 5. 安装 uv 与同步 Python 依赖 ----
echo ""
echo "==> [5/8] 安装 uv 与 Python 3.12 依赖"
if ! command -v uv > /dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
cd "$BACKEND_DIR"
uv sync

# ---- 6. 生成与写入 .env ----
echo ""
echo "==> [6/8] 配置 backend/.env"
if [ ! -f "$BACKEND_DIR/.env" ]; then
  if [ -f "$BACKEND_DIR/deploy/.env.production.example" ]; then
    cp "$BACKEND_DIR/deploy/.env.production.example" "$BACKEND_DIR/.env"
  else
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  fi
fi
chmod 600 "$BACKEND_DIR/.env"

CORS_ORIGINS="$(ask "允许的前端来源 ECHOTALK_CORS_ORIGINS（逗号分隔，保留 null 以支持桌面端）" "http://localhost:5173,null")"

set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_DB_HOST" "$DB_HOST"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_DB_PORT" "$DB_PORT"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_DB_NAME" "$DB_NAME"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_DB_USER" "$DB_USER"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_DB_PASSWORD" "$DB_PASS"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_API_HOST" "$API_HOST"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_API_PORT" "$API_PORT"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_WORKERS" "$WORKERS"
set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_CORS_ORIGINS" "$CORS_ORIGINS"

if ask_yn "是否现在填写大模型 / 语音服务 API Key？（可跳过稍后编辑 .env）" "n"; then
  CHAT_KEY="$(ask "ECHOTALK_CHAT_API_KEY" "")"
  CHAT_MODEL="$(ask "ECHOTALK_CHAT_MODEL" "")"
  CHAT_BASE="$(ask "ECHOTALK_CHAT_API_BASE" "https://api.openai.com/v1")"
  SF_KEY="$(ask "ECHOTALK_SILICONFLOW_API_KEY (嵌入向量)" "")"
  LR_KEY="$(ask "ECHOTALK_LIGHTRAG_LLM_API_KEY (图谱抽取)" "")"
  [ -n "$CHAT_KEY" ] && set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_CHAT_API_KEY" "$CHAT_KEY"
  [ -n "$CHAT_MODEL" ] && set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_CHAT_MODEL" "$CHAT_MODEL"
  [ -n "$CHAT_BASE" ] && set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_CHAT_API_BASE" "$CHAT_BASE"
  [ -n "$SF_KEY" ] && set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_SILICONFLOW_API_KEY" "$SF_KEY"
  [ -n "$LR_KEY" ] && set_env_kv "$BACKEND_DIR/.env" "ECHOTALK_LIGHTRAG_LLM_API_KEY" "$LR_KEY"
fi

# ---- 7. 初始化数据库表与启动 systemd 服务 ----
echo ""
echo "==> [7/8] 初始化数据库表与启动服务"
ADMIN_USER="$(ask "默认管理员用户名（仅首次无管理员时创建）" "admin")"
ADMIN_PASS="$(ask_secret "默认管理员密码（留空则用 admin123456）")"
ADMIN_PASS="${ADMIN_PASS:-admin123456}"
ECHOTALK_ADMIN_USERNAME="$ADMIN_USER" ECHOTALK_ADMIN_PASSWORD="$ADMIN_PASS" uv run python init_db.py

chmod +x "$BACKEND_DIR/deploy/start-backend.sh" "$BACKEND_DIR/deploy/update.sh" "$BACKEND_DIR/deploy/setup-tunnel.sh"
cp "$BACKEND_DIR/deploy/echotalk-backend.service" /etc/systemd/system/echotalk-backend.service
systemctl daemon-reload
systemctl enable --now echotalk-backend

sleep 2
if curl -fs "http://127.0.0.1:${API_PORT}/api/ready" > /dev/null 2>&1; then
  echo "    ✅ 后端服务已就绪 (127.0.0.1:${API_PORT})"
else
  echo "    ⚠ 后端刚启动或未就绪，请检查：journalctl -u echotalk-backend -n 50"
fi

# ---- 8. 配置对外暴露（Tunnel / Nginx） ----
echo ""
echo "==> [8/8] 配置对外访问"
if [ "$EXPOSE_MODE" = "1" ]; then
  CF_TOKEN="$(ask "请输入 Cloudflare Tunnel Token（可留空稍后运行 setup-tunnel.sh）" "")"
  if [ -n "$CF_TOKEN" ]; then
    bash "$BACKEND_DIR/deploy/setup-tunnel.sh" "$CF_TOKEN"
  else
    bash "$BACKEND_DIR/deploy/setup-tunnel.sh"
  fi
elif [ "$EXPOSE_MODE" = "2" ]; then
  DOMAIN="$(ask "请输入后端 API 域名（如 api.your-domain.com）" "")"
  if [ -n "$DOMAIN" ]; then
    apt-get install -y nginx certbot python3-certbot-nginx
    cat > /etc/nginx/sites-available/echotalk <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }
}
NGINX
    ln -sf /etc/nginx/sites-available/echotalk /etc/nginx/sites-enabled/echotalk
    nginx -t && systemctl reload nginx
    if ask_yn "是否立即使用 Certbot 申请免费 HTTPS 证书？" "y"; then
      certbot --nginx -d "$DOMAIN"
    fi
  fi
fi

echo ""
echo "============================================================"
echo "  ✅ EchoTalk 2.0 部署完成！"
echo "  - 配置文件：$BACKEND_DIR/.env"
echo "  - 监听地址：${API_HOST}:${API_PORT} (workers=${WORKERS})"
echo "  - 查看日志：journalctl -u echotalk-backend -f"
echo "  - 日常更新：bash $BACKEND_DIR/deploy/update.sh"
echo "============================================================"
