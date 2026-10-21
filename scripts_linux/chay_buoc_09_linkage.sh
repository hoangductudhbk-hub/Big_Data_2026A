#!/usr/bin/env bash
# ============================================================
#  Buoc 09 - Lien ket thuc the (Record linkage + Blocking).
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

echo "=== 2. Chay Record Linkage ==="
"$VENV_PY" -m data_integration.linkage.run

echo ""
echo "===== HOAN TAT. Bao cao xem tai: docs/bao-cao/09_linkage.md ====="
