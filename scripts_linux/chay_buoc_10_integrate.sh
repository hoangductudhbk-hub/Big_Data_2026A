#!/usr/bin/env bash
# ============================================================
#  Buoc 10 - Hop nhat dataset tao integrated_traffic.parquet.
# ============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "[LOI] Chua co .venv. Hay chay bash scripts_linux/tai_du_lieu.sh truoc."
    exit 1
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"

echo "=== 1. Cai thu vien Phase 1 (Data Integration) ==="
"$VENV_PY" -m pip install -q --disable-pip-version-check -r requirements-integration.txt

echo "=== 2. Chay Hop nhat Dataset ==="
"$VENV_PY" -m data_integration.integrate

echo ""
echo "===== HOAN TAT. Bao cao xem tai: docs/bao-cao/10_integrated.md ====="
echo "Dau ra luu tai: data/processed/integrated_traffic/"
