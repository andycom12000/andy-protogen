#!/usr/bin/env bash
set -euo pipefail

# Protogen systemd service installer
# Run with: sudo bash scripts/install_service.sh

# Check Linux + systemd
if [[ "$(uname)" != "Linux" ]]; then
    echo "Error: This script only runs on Linux."
    exit 1
fi

if ! command -v systemctl &>/dev/null; then
    echo "Error: systemd is not available."
    exit 1
fi

# Check root
if [[ "$EUID" -ne 0 ]]; then
    echo "Error: Please run with sudo."
    exit 1
fi

# Resolve project directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_SRC="$PROJECT_DIR/systemd/protogen.service"
SERVICE_DST="/etc/systemd/system/protogen.service"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -f "$SERVICE_SRC" ]]; then
    echo "Error: Service file not found at $SERVICE_SRC"
    exit 1
fi

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "Warning: venv not found at $VENV_PYTHON"
    echo "Make sure to create it before starting the service."
fi

# Determine user (prefer 'pi', fallback to SUDO_USER)
SVC_USER="${SUDO_USER:-pi}"

echo "Installing protogen.service..."
echo "  Project: $PROJECT_DIR"
echo "  User: $SVC_USER"

# Update paths in service file and write to systemd
sed \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|" \
    -e "s|ExecStart=.*|ExecStart=$PROJECT_DIR/.venv/bin/python -m protogen.main|" \
    -e "s|User=.*|User=$SVC_USER|" \
    "$SERVICE_SRC" > "$SERVICE_DST"

systemctl daemon-reload
systemctl enable protogen.service
systemctl start protogen.service

echo "Done! Service status:"
systemctl status protogen.service --no-pager || true
