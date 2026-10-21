# 21. Chạy toàn hệ thống end-to-end

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026. Kiểm tra end-to-end **18/18 đạt** trên máy ảo của nhóm.
> Báo cáo: `docs/bao-cao/21_e2e.md` · Script: `scripts/e2e_check.py`

## 1. Mục tiêu

Chứng minh toàn bộ luồng của plan (mục 17) chạy được liền mạch trên dữ liệu thật:

```
NYC Open Data + Open-Meteo ─► Phase 1 (pandas) ─► integrated_traffic.parquet
                                                         │
                                       Phase 2 (PySpark) ─► analytics/*.parquet
                                                         │
                                        load_processed ─► PostgreSQL ─► FastAPI ─► Dashboard
```

## 2. Thứ tự chạy từ đầu

| # | Việc | Lệnh | Thời gian thực tế |
|---|---|---|---|
| 1 | Tải dữ liệu (cần VPN nếu ở Việt Nam, xem bước 05) | `tai_du_lieu.bat` hoặc `python -m data_integration.collect.run_all` | khoảng 1–2 giờ (1,2 GB) |
| 2 | Profiling → cleaning → alignment → linkage → tích hợp | `chay_buoc_06…10_*.bat`, hoặc `python -m data_integration.{profiling,cleaning,alignment,linkage}.run` rồi `python -m data_integration.integrate` | vài phút (ước tính, chưa đo trọn một lần chạy liền) |
| 3 | Phase 2: Spark bước 11–17 | `bash scripts/run_phase2.sh` (Linux/WSL) | khoảng 13 phút (cộng thời gian từng bước 11–17 đã đo; riêng benchmark khoảng 7 phút) |
| 4 | Tạo bảng PostgreSQL | `cd backend && alembic upgrade head` | vài giây |
| 5 | Nạp kết quả vào PostgreSQL | `python -m app.etl.load_processed` | 17 giây |
| 6 | Chạy API + dashboard | `uvicorn app.main:app` → mở `http://localhost:8000` | — |
| 7 | Kiểm tra end-to-end | `python scripts/e2e_check.py --report docs/bao-cao/21_e2e.md` | 3 giây |

Bước 4–6 gói sẵn trong một lệnh:

- **Windows** (PostgreSQL bằng Docker Desktop): `chay_phase3.bat`
- **Linux / WSL2 / máy ảo** (PostgreSQL đã chạy): `bash scripts/chay_phase3.sh`
- **Toàn bộ bằng Docker:**

  ```bash
  docker compose up -d --build                                   # PostgreSQL + API (tự chạy alembic)
  docker compose run --rm api python -m app.etl.load_processed   # nạp ./data vào database
  ```

## 3. Kiểm tra end-to-end làm gì

`scripts/e2e_check.py` không chỉ kiểm tra "API trả về 200". Nó **đối chiếu số liệu giữa ba tầng độc lập**:

| Tầng | Cách đọc |
|---|---|
| File Parquet của Phase 1–2 | pandas đọc trực tiếp |
| PostgreSQL qua API | HTTP |
| SQL tính lại trên database | `GET /statistics/live` |

**Kết quả trên máy ảo của nhóm** (PostgreSQL 16.2, Python 3.10):

| Kiểm tra | Kết quả |
|---|---|
| Số bản ghi DB = số dòng Parquet `integrated_traffic` | 805.780 = 805.780 ✅ |
| Số đường DB = số road_id trong Parquet | 211 ✅ |
| Số bất thường DB = Parquet bước 17 | 13.678 ✅ |
| **Spark (bước 15) = SQL trực tiếp trên PostgreSQL** | mean, median, n của 5 quận khớp đến 0,01 ✅ |
| 11 endpoint của plan trả dữ liệu đúng | ✅ |
| Lỗi 404 / 422 đúng định dạng thống nhất | ✅ |
| Import dữ liệu sai contract bị từ chối, nêu rõ lý do | `avg_speed=999.0 lớn hơn 160 km/h` ✅ |
| Dashboard được phục vụ | ✅ |
| **Tổng** | **18/18 đạt** |

Đồng thời trên cùng máy: 22 test backend (trên PostgreSQL thật) và 39 test Phase 0–1 đều đạt.

## 4. Docker

| File | Nội dung |
|---|---|
| `docker-compose.yml` (thư mục gốc) | `db`: PostgreSQL 16 (có healthcheck); `api`: build từ `backend/Dockerfile`, đợi `db` sẵn sàng, mount `./data` chỉ đọc |
| `backend/Dockerfile` | Python 3.12-slim, copy `common/` (data contract) và `backend/`; khi khởi động chạy `alembic upgrade head` rồi `uvicorn` |
| `.dockerignore` | Loại `data/` (mount vào, không đóng gói), tài liệu, file zip |

> **Docker đã chạy thật, 18/18 đạt (14/10/2026, Windows + Docker Desktop):** `docker compose up -d --build` dựng cả `db` và `api`; `docker compose run --rm api python -m app.etl.load_processed` nạp 864.750 dòng trong 44,4 giây; `scripts/e2e_check.py` đạt 18/18 (báo cáo `docs/bao-cao/21_e2e_docker.md`).
>
> **Trước đó, cùng ngày, cách chạy không qua Docker cho API:** `chay_phase3.bat` chạy thành công. PostgreSQL chạy bằng Docker Desktop (`docker compose up -d db`), nạp 864.750 dòng trong 49,2 giây, dashboard hiển thị đúng ở `http://localhost:8000`. Như vậy service `db` trong `docker-compose.yml` đã chạy được thật; riêng service `api` (build image từ `backend/Dockerfile`) chưa thử.
>
> **Cần nói rõ:** môi trường phát triển và máy ảo đều **không tải được image** từ Docker Hub (bị chặn mạng), nên `docker compose` **chưa được chạy thử** trong quá trình làm. Toàn bộ hệ thống đã chạy thật **không qua Docker** trên cùng phiên bản (PostgreSQL 16, Python 3.10/3.13). Nhóm cần chạy `docker compose up -d --build` một lần trên máy có Docker Desktop để xác nhận. Nếu có lỗi, khả năng cao nằm ở đường dẫn build (`context: .`, `dockerfile: backend/Dockerfile`) hoặc ở biến `DATA_DIR=/data`.

## 5. Chạy trên máy ảo không có quyền root

Máy ảo Linux của nhóm không có `sudo` và không chạy được tiến trình nền lâu dài, nên dùng cách sau:

```bash
pip install pgserver                         # gói có sẵn PostgreSQL 16.2
B=$(python -c "import pgserver,os;print(os.path.dirname(pgserver.__file__))")/pginstall/bin
$B/initdb -D ~/pg/data -U postgres --auth=trust -E UTF8          # một lần
$B/pg_ctl -D ~/pg/data -o "-p 5432 -k /tmp -c listen_addresses=localhost" -l ~/pg/server.log start
$B/psql -h localhost -U postgres -c "CREATE DATABASE traffic_bigdata"
export DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/traffic_bigdata
bash scripts/chay_phase3.sh
```

Trên Windows thì đơn giản hơn: cài Docker Desktop rồi chạy `chay_phase3.bat`.

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Docker Hub bị chặn ở môi trường phát triển | Kiểm chứng trước bằng cách chạy không qua Docker; sau đó nhóm chạy `docker compose` trên Windows: 18/18 đạt (mục 4) |
| Máy ảo không có quyền root để cài PostgreSQL | `pgserver` (PostgreSQL đóng gói trong pip) |
| Tiến trình nền trên máy ảo bị dừng khi lệnh kết thúc | Khởi động PostgreSQL, nạp dữ liệu, chạy API, chạy kiểm tra và tắt, tất cả trong **một** lệnh |
