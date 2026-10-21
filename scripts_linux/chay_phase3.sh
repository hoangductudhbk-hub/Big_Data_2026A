#!/usr/bin/env bash
# ============================================================
#  Buoc 18-21 - Chay Phase 3 tren Linux:
#  1. Khoi dong PostgreSQL (Docker hoac PostgreSQL local)
#  2. Tao bang bang Alembic
#  3. Nap ket qua Parquet vao Database
#  4. Bat FastAPI va Dashboard o cong 8000
# ============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "[THONG BAO] Chua co .venv. Dang tao .venv..."
    python3 -m venv .venv
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"

echo "=== 1. Kiem tra va cai thu vien Backend ==="
"$VENV_PY" -m pip install -q --disable-pip-version-check -r backend/requirements.txt

echo "=== 2. Khoi dong PostgreSQL bang Docker Compose ==="
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    docker compose up -d db
    echo "Doi PostgreSQL san sang trong 5 giay..."
    sleep 5
else
    echo "[CANH BAO] Khong tim thay Docker Compose. Dam bao PostgreSQL da duoc bat tai cong 5432."
fi

export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata"

cd "$ROOT_DIR/backend"

echo "=== 3. Chay Migration Alembic (tao cac bang CSDL) ==="
"$VENV_PY" -m alembic upgrade head

echo "=== 4. Nap du lieu processed Parquet vao PostgreSQL ==="
"$VENV_PY" -m app.etl.load_processed

echo ""
echo "============================================================"
echo "  DASHBOARD: http://localhost:8000"
echo "  SWAGGER API DOCS: http://localhost:8000/docs"
echo "  Nhan Ctrl + C de dung server"
echo "============================================================"
echo ""

exec "$VENV_PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
