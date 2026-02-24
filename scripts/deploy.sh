#!/usr/bin/env bash
set -euo pipefail

# Protogen 部署腳本 — 從 Windows 同步到 Raspberry Pi
# 用法: bash scripts/deploy.sh [--install] [--restart]
#   --install   首次部署時建立 venv 並安裝依賴
#   --restart   部署後重啟 systemd service

PI_HOST="andy@192.168.1.103"
PI_DIR="~/andy-protogen"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse flags
DO_INSTALL=false
DO_RESTART=false
for arg in "$@"; do
    case "$arg" in
        --install) DO_INSTALL=true ;;
        --restart) DO_RESTART=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo "==> Packaging project..."
TMPFILE="$(mktemp /tmp/protogen-deploy-XXXXXX.tar.gz)"
git -C "$PROJECT_DIR" archive --format=tar HEAD | gzip > "$TMPFILE"
SIZE=$(du -h "$TMPFILE" | cut -f1)
echo "    Archive: $SIZE"

echo "==> Uploading to $PI_HOST..."
scp -q "$TMPFILE" "$PI_HOST:/tmp/protogen-deploy.tar.gz"
rm "$TMPFILE"

echo "==> Extracting on Pi..."
ssh "$PI_HOST" "mkdir -p $PI_DIR && cd $PI_DIR && tar xzf /tmp/protogen-deploy.tar.gz && rm /tmp/protogen-deploy.tar.gz"

# Fix Windows CRLF line endings in shell scripts
echo "==> Fixing CRLF line endings..."
ssh "$PI_HOST" "find $PI_DIR/scripts $PI_DIR/systemd -type f -exec sed -i 's/\r$//' {} +"

# Override mock to false for Pi
echo "==> Setting display.mock=false..."
ssh "$PI_HOST" "sed -i 's/mock: true/mock: false/' $PI_DIR/config.yaml"

if $DO_INSTALL; then
    echo "==> Installing dependencies (this may take a while)..."
    ssh "$PI_HOST" "cd $PI_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[rpi,web,monitoring]'" 2>&1 | tail -5
fi

if $DO_RESTART; then
    echo "==> Restarting protogen service..."
    ssh -t "$PI_HOST" "sudo systemctl restart protogen.service && sudo systemctl status protogen.service --no-pager" || true
fi

echo "==> Done!"
ssh "$PI_HOST" "cd $PI_DIR && source .venv/bin/activate && python --version && echo 'Files:' && ls"
