#!/usr/bin/env bash
# Chạy lại toàn bộ Phase 2 (bước 11–17) trên dữ liệu thật. Cần đã có kết quả Phase 1 (bước 07–10).
# Cách dùng (Linux / WSL2 / máy ảo):   bash scripts/run_phase2.sh
# Bước 14 lâu nhất (~6–7 phút); muốn bỏ qua: SKIP_BENCH=1 bash scripts/run_phase2.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python}
run() { echo; echo "=== $* ==="; "$PY" -m "$@"; }

run spark_jobs.s11_basic
run spark_jobs.s12_query_processing
run spark_jobs.s13_approximate
if [ "${SKIP_BENCH:-0}" != "1" ]; then
  run spark_jobs.s14_scalability
fi
run spark_jobs.s15_statistics
run spark_jobs.s16_weather_impact
run spark_jobs.s17_anomaly
# Kiểm chứng Z-score trên mock có đáp án
"$PY" scripts/generate_mock_integrated.py
INTEGRATED_PATH=data/mock/integrated_traffic run spark_jobs.s17_anomaly --validate
echo; echo "Xong Phase 2. Báo cáo: docs/bao-cao/11_*.md … 17_*.md · Kết quả: data/processed/analytics/"
