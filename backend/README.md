# Backend — NYC Traffic Big Data API (Phase 3)

FastAPI + PostgreSQL + SQLAlchemy + Alembic. Nạp kết quả Phase 1–2 (Parquet) vào PostgreSQL, cung cấp API và dashboard.
Giải trình chi tiết: `docs/huong-dan/18_database_postgresql.md` → `22_tong_ket.md`.

## Chạy nhanh

**Windows (Docker Desktop cho PostgreSQL):** ở thư mục gốc project, chạy `chay_phase3.bat`.

**Linux / WSL2 / macOS (PostgreSQL đã chạy):**

```bash
pip install -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata
bash scripts/chay_phase3.sh          # alembic upgrade → nạp dữ liệu → uvicorn
```

**Toàn bộ bằng Docker** (ở thư mục gốc):

```bash
docker compose up -d --build
docker compose run --rm api python -m app.etl.load_processed
```

Sau đó mở: dashboard `http://localhost:8000` · tài liệu API `http://localhost:8000/docs`.

## Cấu trúc

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, mount dashboard
│   ├── core/                   # config (biến môi trường), database, errors (định dạng lỗi thống nhất)
│   ├── models/                 # 9 bảng; CHECK của integrated_traffic sinh từ common/contract.py
│   ├── schemas/                # Pydantic (dữ liệu vào/ra)
│   ├── api/routes/             # health, roads, traffic, weather, statistics, anomalies, imports
│   ├── services/               # validation.py (kiểm tra theo contract), importer.py (UPSERT)
│   └── etl/load_processed.py   # nạp Parquet → PostgreSQL (COPY, 1 transaction)
├── migrations/versions/        # Alembic: 0001_contract_v1
├── dashboard/                  # HTML + JS + Chart.js/Leaflet (vendor/), phục vụ ở /dashboard/
├── examples/                   # file CSV mẫu để thử import
└── tests/                      # 22 test (SQLite mặc định; đặt TEST_DATABASE_URL để chạy trên PostgreSQL)
```

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata` | Kết nối database |
| `DATA_DIR` | `<project>/data` | Nơi đọc kết quả Phase 1–2 |
| `CORS_ORIGINS` | `*` | Origin được gọi API |
| `TEST_DATABASE_URL` | (trống → SQLite) | Database cho test. **Bị xóa sạch bảng khi chạy test** |

## Lệnh thường dùng

```bash
cd backend
alembic upgrade head                              # tạo/cập nhật bảng
python -m app.etl.load_processed                  # nạp toàn bộ (chạy lại được nhiều lần)
python -m app.etl.load_processed --only analytics # chỉ nạp lại kết quả Spark
python -m app.etl.load_processed --mock           # dùng mock dataset
uvicorn app.main:app --reload                     # chạy API
python -m pytest                                  # test
python ../scripts/e2e_check.py                    # kiểm tra end-to-end khi API đang chạy
```

## Endpoint chính (tiền tố `/api/v1`)

`GET /roads`, `/roads/{road_id}` · `GET /traffic`, `/traffic/{id}`, `/traffic/timeseries` · `GET /weather`, `/weather/stations` ·
`GET /statistics`, `/statistics/dimensions`, `/statistics/summary`, `/statistics/daily`, `/statistics/weather-impact`, `/statistics/live` ·
`GET /anomalies`, `/anomalies/summary`, `/anomalies/daily` · `POST /import/traffic`, `/import/weather` (JSON), `/import/{traffic,weather}/file` (CSV/JSON/Parquet), `/import/spark-results` · `GET /import/logs` · `GET /health`.
