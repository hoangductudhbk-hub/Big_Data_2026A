# Big Data Integration and Statistical Analysis System for Urban Traffic Data

Hệ thống tích hợp dữ liệu giao thông New York (tốc độ và lưu lượng) với dữ liệu thời tiết, xử lý quy mô lớn bằng PySpark, phân tích thống kê và phát hiện bất thường, cung cấp kết quả qua FastAPI và dashboard.

- **Định hướng:** `docs/ke_hoach_du_an.md`
- **Lộ trình và hướng dẫn từng bước:** `docs/huong-dan/00_lo_trinh_tong_the.md`
- **Data contract:** `docs/data_contract.md`

## Trạng thái và bàn giao (14/10/2026)


- **Đã xong Phase 0–3 (bước 01–22)**, chạy trên dữ liệu thật NYC 2024. Definition of Done: 17/17 (`docs/huong-dan/22_tong_ket.md`).
- **Việc còn lại cho người làm tiếp:** `docs/huong-dan/23_viec_con_lai.md` (rà nhãn record linkage, chuẩn bị bảo vệ).
- **Dữ liệu đã xử lý CÓ trên Git** (`data/interim`, `data/processed`, khoảng 50 MB Parquet): clone về là chạy được ngay Phase 2 (Spark), Phase 3 (`chay_phase3.bat` hoặc `docker compose`) và dashboard. **Dữ liệu gốc `data/raw` (1,2 GB) KHÔNG có** vì GitHub chặn file > 100 MB; chỉ cần khi muốn chạy lại Phase 1 từ đầu: tải lại theo `docs/huong-dan/05_thu_thap_du_lieu.md` (cần VPN nếu ở Việt Nam).
- Mỗi bước có file hướng dẫn riêng trong `docs/huong-dan/` (mục tiêu, giải trình, lệnh chạy, kết quả, lỗi đã gặp) và báo cáo số liệu trong `docs/bao-cao/`.

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
