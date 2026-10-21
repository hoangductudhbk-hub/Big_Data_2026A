#!/usr/bin/env bash
# Chạy Phase 3 không cần Docker (Linux / WSL2 / máy ảo), khi đã có PostgreSQL đang chạy.
#   export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata
#   bash scripts/chay_phase3.sh            # tạo bảng, nạp dữ liệu, chạy API + dashboard ở cổng 8000
#   SKIP_LOAD=1 bash scripts/chay_phase3.sh   # không nạp lại dữ liệu
set -euo pipefail
cd "$(dirname "$0")/../backend"
PY=${PYTHON:-python}
echo "== 1. Tạo / cập nhật bảng (Alembic)"; "$PY" -m alembic upgrade head
if [ "${SKIP_LOAD:-0}" != "1" ]; then echo "== 2. Nạp kết quả Phase 1–2"; "$PY" -m app.etl.load_processed; fi
echo "== 3. API + dashboard: http://localhost:8000  (tài liệu API: /docs, dừng: Ctrl+C)"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
