# Big Data Integration and Statistical Analysis System for Urban Traffic Data

Hệ thống tích hợp dữ liệu giao thông New York (tốc độ và lưu lượng) với dữ liệu thời tiết, xử lý quy mô lớn bằng PySpark, phân tích thống kê và phát hiện bất thường, cung cấp kết quả qua FastAPI và dashboard.

- **Định hướng:** `docs/ke_hoach_du_an.md`
- **Lộ trình và hướng dẫn từng bước:** `docs/huong-dan/00_lo_trinh_tong_the.md`
- **Data contract:** `docs/data_contract.md`

## Mã nguồn và dữ liệu

- **Mã nguồn:** https://github.com/hoangductudhbk-hub/Big_Data_2026A
- **Dữ liệu gốc New York 2024 (khoảng 1,2 GB):** [Google Drive](https://drive.google.com/drive/folders/1dQq9kATcZ4wKA_DBr2S8nlsjQdZNfEy-?usp=sharing)
  Tải về và đặt vào thư mục `data/raw/` để chạy lại pipeline từ đầu (hoặc tải lại trực tiếp từ nguồn bằng `tai_du_lieu.bat`).
- **Chạy nhanh không cần dữ liệu gốc:** dữ liệu đã xử lý (`data/interim`, `data/processed`, dạng Parquet) có sẵn trong repo. Clone về là chạy được ngay Phase 2 (Spark), Phase 3 (`chay_phase3.bat` hoặc `docker compose`) và dashboard; dữ liệu gốc chỉ cần khi muốn chạy lại Phase 1 từ đầu.
- **Hồ sơ nộp bài** (báo cáo, slide, kịch bản demo): thư mục [`NOP_BAI/`](NOP_BAI/)

## Chạy nhanh

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements-data.txt

python -m pytest                                       # test Phase 0–1
python scripts/generate_mock_integrated.py             # mock dataset cho Phase 2
python -m data_integration.collect.run_all             # tải dữ liệu thật (bước 05)
```

Phase 2 (PySpark, Linux/WSL2): `bash scripts/run_phase2.sh` — xem `docs/huong-dan/11_pyspark_co_ban.md`.

Phase 3 (PostgreSQL + FastAPI + dashboard):

```bash
chay_phase3.bat                                   # Windows, cần Docker Desktop cho PostgreSQL
bash scripts/chay_phase3.sh                       # Linux/WSL2, PostgreSQL đã chạy (đặt DATABASE_URL)
docker compose up -d --build && docker compose run --rm api python -m app.etl.load_processed   # toàn bộ bằng Docker
```

Mở `http://localhost:8000` (dashboard) và `http://localhost:8000/docs` (API). Chi tiết: `backend/README.md`.
Tổng kết theo Definition of Done: `docs/huong-dan/22_tong_ket.md`.
