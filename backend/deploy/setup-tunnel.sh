#!/usr/bin/env bash
# EchoTalk 2.0 Cloudflare Tunnel 一键安装与服务注册脚本（免备案 HTTPS 方案）
# 用法：
#   CF_TUNNEL_TOKEN="你的Token" sudo -E bash setup-tunnel.sh
#   或：sudo bash setup-tunnel.sh "你的Token"
#
# 前置准备（在 Cloudflare Zero Trust 控制台操作，约 1 分钟）：
#   1. 进入 Zero Trust -> Networks -> Tunnels -> Create a tunnel -> 选择 Cloudflared
#   2. 复制页面给出的 Tunnel Token（形如 eyJh...）
#   3. 在 Public Hostname 添加一条规则：
#      - Subdomain / Domain: api.your-domain.com
#      - Service Type: HTTP
#      - URL: 127.0.0.1:8000
set -euo pipefail

TOKEN="${1:-${CF_TUNNEL_TOKEN:-}}"

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ 请使用 sudo 运行此脚本，例如：CF_TUNNEL_TOKEN=... sudo -E bash $0" >&2
  exit 1
fi

echo "==> [1/3] 检查并安装 cloudflared"
if ! command -v cloudflared > /dev/null 2>&1; then
  ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m)"
  case "$ARCH" in
    amd64|x86_64) DEB_ARCH="amd64" ;;
    arm64|aarch64) DEB_ARCH="arm64" ;;
    *)
      echo "❌ 暂不支持的架构：$ARCH" >&2
      exit 1
      ;;
  esac
  TMP_DEB="/tmp/cloudflared-linux-${DEB_ARCH}.deb"
  echo "    正在下载 cloudflared (${DEB_ARCH})..."
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${DEB_ARCH}.deb" -o "$TMP_DEB"
  dpkg -i "$TMP_DEB"
  rm -f "$TMP_DEB"
fi
cloudflared --version

if [ -z "$TOKEN" ]; then
  echo ""
  echo "⚠ 未传入 CF_TUNNEL_TOKEN，已完成 cloudflared 安装。"
  echo "  拿到 Cloudflare Zero Trust 控制台的 Token 后执行："
  echo "    sudo cloudflared service install <你的CF_TUNNEL_TOKEN>"
  exit 0
fi

echo "==> [2/3] 注册 cloudflared systemd 常驻服务"
if systemctl list-unit-files | grep -q '^cloudflared\.service'; then
  echo "    检测到已存在 cloudflared.service，先卸载旧配置再重新注册..."
  cloudflared service uninstall || true
fi
cloudflared service install "$TOKEN"

echo "==> [3/3] 启动并验证 cloudflared 服务"
systemctl enable --now cloudflared
systemctl --no-pager --full status cloudflared | head -n 15

echo ""
echo "✅ Cloudflare Tunnel 已运行！请在 Cloudflare Tunnel 控制台确认 Public Hostname 指向："
echo "   http://127.0.0.1:8000"
