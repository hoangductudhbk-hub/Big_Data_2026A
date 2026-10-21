#!/usr/bin/env bash
# ============================================================
#  Buoc 05 - Tai du lieu: thoi tiet (Open-Meteo), luu luong va toc do (NYC Open Data)
#  Luu y: Can bat VPN neu chay tu Viet Nam vi NYC Open Data chan IP Viet Nam.
# ============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== 1. Kiem tra Python tren Linux ==="
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "[LOI] Chua cai Python 3. Hay cai bang: sudo apt update && sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
"$PY" --version

if [ ! -f ".venv/bin/python" ]; then
    echo "=== 2. Tao moi truong ao .venv ==="
    "$PY" -m venv .venv
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"

echo "=== 3. Cai dat thu vien can thiet ==="
"$VENV_PY" -m pip install -q --disable-pip-version-check -r requirements-collect.txt

echo ""
echo "=== 4. Bat dau tai du lieu (speeds, volume, weather) ==="
echo "Log duoc luu tai data/raw/collect_log.txt"
echo ""

"$VENV_PY" -m data_integration.collect.run_all

echo ""
echo "===== HOAN TAT TAI DU LIEU ====="
