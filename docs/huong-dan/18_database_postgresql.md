# 18. Database PostgreSQL theo data contract và nạp kết quả Spark

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026. Đã chạy trên PostgreSQL 16 ở hai nơi: môi trường phát triển và máy ảo của nhóm.
> Code: `backend/app/models/`, `backend/migrations/versions/0001_schema_contract_v1.py`, `backend/app/etl/load_processed.py`

## 1. Mục tiêu

Theo plan (mục 14.1 và 14.3): đưa kết quả Phase 1 (`integrated_traffic`) và Phase 2 (thống kê, tác động thời tiết, bất thường) vào **PostgreSQL**, quản lý schema bằng **SQLAlchemy + Alembic**:

```
Phase 1 → integrated_traffic (Parquet) ─┐
Phase 2 → analytics/*.parquet ──────────┼──► load_processed ──► PostgreSQL ──► FastAPI
Bước 07 → weather_clean, roads ─────────┘
```

## 2. Giải trình thiết kế

### 2.1. Vì sao phải viết lại backend có sẵn

Thư mục `backend/` có sẵn một khung FastAPI (do thành viên phụ trách Phase 3 dựng trước khi có dữ liệu). Khi đối chiếu với data contract (bước 03) và dữ liệu thật, khung này có 4 điểm không tương thích:

| Khung cũ | Dữ liệu thật / contract | Hậu quả nếu giữ nguyên |
|---|---|---|
| `traffic_records.vehicle_count` và `avg_speed` đều **NOT NULL** | 98% bản ghi chỉ có tốc độ, 2% chỉ có lưu lượng (null là "nguồn không đo") | Không nạp được dòng nào |
| `timestamp` **có múi giờ** | Contract: giờ địa phương New York **không múi giờ** | Lệch 4–5 giờ khi so với Spark |
| Không có `snowfall`, `weather_station_id`, `source` | Có trong contract | Mất thông tin, không phân tích lại được |
| Không có bảng `statistics`, `anomalies` | Plan yêu cầu | Không có chỗ chứa kết quả Phase 2 |

Nhóm giữ **công nghệ và cấu trúc thư mục** (FastAPI, SQLAlchemy, Alembic, `app/api/routes`, `app/models`, `app/schemas`), nhưng viết lại models và routes theo contract.

### 2.2. Các bảng

| Bảng | Nguồn | Số dòng | Vai trò |
|---|---|---|---|
| `roads` | `processed/roads.parquet` (bước 09) | 227 | Danh mục đường sau record linkage |
| `integrated_traffic` | `processed/integrated_traffic/` (bước 10) | 805.780 | **Đúng 14 cột của contract** + khóa `id` |
| `weather_records` | `interim/weather_clean.parquet` (bước 07) | 43.915 | Thời tiết theo giờ × 5 điểm đo |
| `statistics` | `analytics/statistics.parquet` (bước 15) | 419 | Bảng dài: (chiều, nhóm, chỉ số) → count/mean/std/min/max/median |
| `daily_stats` | bước 15 | 358 | Chuỗi theo ngày + cờ mất dữ liệu |
| `weather_impact` | bước 16 | 24 | % thay đổi thô và có kiểm soát |
| `anomalies` | bước 17 | 13.678 | Bản ghi \|z\| > 3, đúng các cột plan yêu cầu + ngữ cảnh |
| `anomaly_daily` | bước 17 | 349 | Số bất thường theo ngày |
| `import_logs` | loader + API | — | Nhật ký mọi lần nạp: nguồn, số dòng, trạng thái |

**So với danh sách của plan:**

- `traffic_records` và `processed_traffic_records` không tách thành bảng riêng. Plan cho phép điều này nếu có lý do: `integrated_traffic` **chính là** bản ghi giao thông sau tích hợp, và mọi kết quả xử lý đã nằm ở `statistics` và `anomalies`. Hai bảng nữa chỉ là bản sao của cùng dữ liệu.
- Bảng `integrated_traffic` giữ cả `road_name`, `district`, tọa độ (không chuẩn hóa hẳn sang `roads`), vì contract định nghĩa bảng này như vậy. Nhờ vậy dữ liệu trong database **giống hệt** file Parquet mà Spark đọc, kiểm tra chéo được từng dòng.

### 2.3. Ràng buộc sinh tự động từ data contract

Các ràng buộc `CHECK` của `integrated_traffic` **không viết tay**. Hàm `contract_checks()` đọc `common/contract.py` và sinh ra:

```sql
CONSTRAINT ck_integrated_traffic_avg_speed CHECK (avg_speed IS NULL OR (avg_speed >= 0 AND avg_speed <= 160)),
CONSTRAINT ck_integrated_traffic_district  CHECK (district IN ('Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island')),
CONSTRAINT ck_integrated_traffic_source    CHECK (source IN ('speeds', 'volume', 'speeds+volume')), ...
CONSTRAINT uq_integrated_traffic_road_ts   UNIQUE (road_id, timestamp)     -- khóa chính của contract
```

Một nguồn quy tắc duy nhất được dùng ở **ba nơi**: Phase 1 (`validate_pandas`), database (CHECK) và API import (bước 19). Sửa contract thì cả ba cùng đổi, không thể lệch nhau.

### 2.4. Loader: an toàn và chạy lại được

`python -m app.etl.load_processed` có các đặc điểm:

1. **Kiểm tra contract trước khi nạp.** File `integrated_traffic` sai contract thì dừng ngay, không ghi gì.
2. **Kiểm tra khóa ngoại trước khi nạp.** `road_id` trong `integrated_traffic` và `anomalies` phải có trong `roads`. Lỗi được báo bằng câu dễ hiểu, kèm ví dụ mã sai.
3. **Một transaction cho cả lần nạp.** Xóa dữ liệu cũ và ghi dữ liệu mới trong cùng transaction. Lỗi giữa chừng thì rollback, dữ liệu cũ còn nguyên, không bao giờ có trạng thái "nửa cũ nửa mới".
4. **Chạy lại bao nhiêu lần cũng cho cùng kết quả** (idempotent).
5. **Dùng lệnh `COPY` của PostgreSQL** thay vì INSERT từng dòng: 805.780 dòng nạp trong khoảng 14 giây.
6. **Tự đối chiếu số dòng:** sau khi ghi, đếm lại trong database và so với số dòng của file.
7. `--only analytics`: chỉ nạp lại kết quả Spark sau khi chạy lại Phase 2 (dưới 1 giây).
8. `--mock`: nạp mock dataset khi chưa có dữ liệu thật (danh mục đường suy ra từ chính dữ liệu).

## 3. Thực hiện

```bash
# PostgreSQL: Docker (docker compose up -d db) hoặc cài sẵn trên máy
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata   # Windows: set DATABASE_URL=...
alembic upgrade head                     # tạo 9 bảng + ràng buộc
python -m app.etl.load_processed         # nạp toàn bộ
```

## 4. Kết quả

```
  roads                      227 dòng  (  0.0 s)
  weather_records         43,915 dòng  (  0.3 s)
  integrated_traffic     805,780 dòng  ( 13.8 s)
  statistics                 419 dòng  (  0.0 s)
  daily_stats                358 dòng  (  0.0 s)
  weather_impact              24 dòng  (  0.0 s)
  anomalies               13,678 dòng  (  0.4 s)
  anomaly_daily              349 dòng  (  0.0 s)
Xong trong 17.1 s: 864,750 dòng vào 8 bảng.        (máy ảo của nhóm, PostgreSQL 16.2)
```

Dung lượng database sau khi nạp: khoảng 245 MB (gồm các index).

**Đối chiếu Spark và PostgreSQL:** tính lại tốc độ trung bình và trung vị theo quận bằng SQL trên database, so với bảng `statistics` do Spark tính ở bước 15:

| Quận | n | Mean (SQL) | Mean (Spark) | Median (SQL) | Median (Spark) |
|---|---|---|---|---|---|
| Bronx | 163.992 | 62,240 | 62,24 | 70,320 | 70,32 |
| Brooklyn | 52.394 | 54,850 | 54,85 | 63,330 | 63,33 |
| Manhattan | 138.419 | 40,490 | 40,49 | 40,910 | 40,91 |
| Queens | 293.324 | 62,174 | 62,174 | 69,160 | 69,16 |
| Staten Island | 141.274 | 79,439 | 79,439 | 86,240 | 86,24 |

**Khớp hoàn toàn.** Hai hệ thống độc lập (Spark đọc Parquet, PostgreSQL đọc bảng đã nạp) cho cùng kết quả, nghĩa là quá trình nạp không làm mất hay sai lệch dữ liệu.

## 5. Kiểm tra

- [x] `alembic upgrade head` tạo đủ 9 bảng trên database trống (migration `0001_contract_v1`).
- [x] Số dòng mỗi bảng = số dòng file nguồn (loader tự kiểm tra; bước 21 kiểm tra lại qua API).
- [x] Test `test_contract_violation_rolls_back`: sửa một giá trị `avg_speed = 999` trong file → loader báo lỗi contract, database giữ nguyên 144 dòng cũ.
- [x] Test `test_unknown_road_in_anomalies_is_rejected`: `road_id` lạ trong file bất thường bị phát hiện trước khi ghi.
- [x] Test `test_reload_is_idempotent`: nạp 2 lần liên tiếp cho cùng số dòng.

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Khung backend cũ không nạp được dữ liệu thật (NOT NULL, múi giờ) | Viết lại models theo contract (mục 2.1) |
| Backend cần `common/contract.py` ở thư mục gốc project | `app/__init__.py` tự thêm thư mục gốc vào `sys.path`; Docker đặt `PYTHONPATH=/srv` |
| Máy ảo không có quyền root để cài PostgreSQL | Dùng gói pip `pgserver` (có sẵn PostgreSQL 16.2) để chạy thử trên máy ảo. Trên Windows dùng Docker Desktop (`docker compose up -d db`) |
