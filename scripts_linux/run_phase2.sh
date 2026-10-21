#!/usr/bin/env bash
# ============================================================
#  Phase 2 - Chay toan bo cac job PySpark (buoc 11 den 17) tren Linux.
# ============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".venv/bin/python" ]; then
    echo "[LOI] Chua co .venv. Hay cai moi truong truoc."
    exit 1
fi

VENV_PY="$ROOT_DIR/.venv/bin/python"

echo "=== 1. Cai thu vien PySpark ==="
"$VENV_PY" -m pip install -q --disable-pip-version-check -r requirements-spark.txt

echo "=== 2. Chay cac PySpark Jobs ==="
for step in 11 12 13 14 15 16 17; do
    echo "--- Chay job s${step} ---"
    case $step in
        11) "$VENV_PY" -m spark_jobs.s11_basic ;;
        12) "$VENV_PY" -m spark_jobs.s12_query_processing ;;
        13) "$VENV_PY" -m spark_jobs.s13_approximate ;;
        14) "$VENV_PY" -m spark_jobs.s14_scalability ;;
        15) "$VENV_PY" -m spark_jobs.s15_statistics ;;
        16) "$VENV_PY" -m spark_jobs.s16_weather_impact ;;
        17) "$VENV_PY" -m spark_jobs.s17_anomaly ;;
    esac
done

echo ""
echo "===== HOAN TAT TOAN BO PYSPARK JOBS (PHASE 2) ====="
echo "Ket qua luu tai: data/processed/analytics/"
