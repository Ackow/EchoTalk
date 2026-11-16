#!/usr/bin/env bash
# EchoTalk 2.0 管理后台服务器 Nginx 一键配置脚本
# 用法：sudo bash /opt/echotalk/backend/deploy/setup-admin.sh [管理端端口]
#   默认管理端端口 8889；后端端口自动从 backend/.env 读取（ECHOTALK_API_PORT）。
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ 请使用 sudo 运行：sudo bash $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"
ADMIN_PORT="${1:-${ADMIN_PORT:-8889}}"
WEB_ROOT="/var/www/echotalk-admin"

API_PORT="8000"
if [ -f "$ENV_FILE" ]; then
  _p="$(grep -E '^ECHOTALK_API_PORT=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [ -n "$_p" ] && API_PORT="$_p"
fi

echo "==> [1/4] 检查并安装 Nginx"
if ! command -v nginx > /dev/null 2>&1; then
  apt-get update -y
  apt-get install -y nginx
fi

echo "==> [2/4] 准备管理端静态目录：$WEB_ROOT"
mkdir -p "$WEB_ROOT"
if [ -n "${SUDO_USER:-}" ]; then
  chown -R "${SUDO_USER}:${SUDO_USER}" "$WEB_ROOT"
fi
chmod -R 755 "$WEB_ROOT"

echo "==> [3/4] 写入 Nginx 站点配置 (监听 :${ADMIN_PORT} -> API 127.0.0.1:${API_PORT})"
cat > /etc/nginx/sites-available/echotalk-admin <<NGINX
server {
    listen ${ADMIN_PORT};
    listen [::]:${ADMIN_PORT};

    root ${WEB_ROOT};
    index index.html;
    client_max_body_size 20m;

    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/echotalk-admin /etc/nginx/sites-enabled/echotalk-admin
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> [4/4] 检查 UFW 防火墙"
if command -v ufw > /dev/null 2>&1 && ufw status | grep -q 'Status: active'; then
  ufw allow "${ADMIN_PORT}/tcp"
fi

echo ""
echo "✅ 管理端 Nginx 配置完成！"
echo "   下一步在本地电脑上传打包产物（admin/dist）："
echo "     scp -r admin/dist/* ubuntu@<服务器IP>:${WEB_ROOT}/"
echo "   并在云厂商安全组放行 ${ADMIN_PORT} 端口后访问："
echo "     http://<服务器IP>:${ADMIN_PORT}"
