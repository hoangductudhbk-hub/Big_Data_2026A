# 19. API FastAPI: truy vấn, thống kê, bất thường, import

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026. 22 test đạt trên PostgreSQL 16 (21 test + 1 bỏ qua trên SQLite).
> Code: `backend/app/api/routes/`, `backend/app/services/`, `backend/tests/` · Tài liệu tương tác: `http://localhost:8000/docs`

## 1. Mục tiêu

Theo plan (mục 14.2): cung cấp API cho dữ liệu và kết quả phân tích:

```
GET /health   GET /traffic   GET /traffic/{id}   GET /weather   GET /roads
GET /statistics   GET /anomalies   POST /import/traffic   POST /import/weather
```

## 2. Danh sách endpoint

Tất cả nằm dưới tiền tố `/api/v1` (đánh số phiên bản để sau này đổi API mà không làm hỏng client cũ). Riêng `GET /health` có thêm ở gốc, đúng như plan ghi.

| Nhóm | Endpoint | Chức năng |
|---|---|---|
| health | `GET /health`, `GET /api/v1/health/db` | Server sống; kết nối DB và phiên bản schema Alembic |
| roads | `GET /roads` | Danh mục đường; lọc `district`, `has_speed`, `has_volume`, tìm `q` |
| | `GET /roads/{road_id}` | Một đường + thống kê tóm tắt (tốc độ, lưu lượng, số bất thường) |
| | `POST /roads` | Thêm đường (kiểm tra quận hợp lệ, tọa độ trong khung New York) |
| traffic | `GET /traffic` | Bản ghi `integrated_traffic`; lọc `road_id, district, source, weather_condition, start, end`; phân trang |
| | `GET /traffic/{id}` | Một bản ghi |
| | `GET /traffic/timeseries` | Gộp theo `hour/day/week/month` để vẽ biểu đồ |
| weather | `GET /weather`, `GET /weather/{id}`, `GET /weather/stations` | Thời tiết theo giờ, các điểm đo |
| statistics | `GET /statistics?dimension=&metric=` | Thống kê **Spark tính sẵn** (bước 15) |
| | `GET /statistics/dimensions` | Các chiều có sẵn |
| | `GET /statistics/summary` | Số liệu tổng quan cho dashboard |
| | `GET /statistics/daily` | Chuỗi theo ngày |
| | `GET /statistics/weather-impact` | Kết quả bước 16 |
| | `GET /statistics/live?group_by=&start=&end=` | Thống kê **tính trực tiếp bằng SQL**, chọn được khoảng thời gian |
| anomalies | `GET /anomalies` | Lọc `metric, road_id, district, direction, min_abs_z, start, end`; sắp theo \|z\| hoặc thời gian |
| | `GET /anomalies/summary`, `GET /anomalies/daily`, `GET /anomalies/{id}` | Tóm tắt, theo ngày, chi tiết |
| import | `POST /import/traffic`, `POST /import/weather` | Nhập JSON theo contract |
| | `POST /import/traffic/file`, `POST /import/weather/file` | Nhập file CSV / JSON / Parquet |
| | `POST /import/spark-results` | Nạp lại kết quả Spark sau khi chạy lại Phase 2 |
| | `GET /import/logs` | Nhật ký nạp |

## 3. Giải trình các quyết định chính

### 3.1. Hai loại thống kê: Spark tính sẵn và SQL trực tiếp

- `GET /statistics` đọc bảng do **Spark** tính trên toàn bộ năm. Trả lời gần như tức thì (khoảng 10 ms), dùng cho dashboard.
- `GET /statistics/live` tính bằng **SQL** khi được gọi (khoảng 0,4 giây trên 805 nghìn dòng). Endpoint này cho phép lọc theo khoảng thời gian bất kỳ, điều mà bảng tính sẵn không làm được.

Đây chính là sự đánh đổi "tính trước (batch) và tính khi cần (on-demand)" của các hệ thống Big Data. Endpoint `live` còn có vai trò **kiểm tra chéo**: không lọc gì thì kết quả phải trùng với Spark (bước 18, mục 4).

### 3.2. Import: kiểm tra từng dòng theo contract

`POST /import/traffic` không tin dữ liệu gửi lên. Mỗi dòng được kiểm tra bằng **cùng quy tắc** với Phase 1 và database (`common/contract.py`):

| Quy tắc | Ví dụ lỗi trả về |
|---|---|
| Giá trị trong khoảng của contract | `avg_speed=250.0 lớn hơn 160 km/h` |
| `timestamp` là đầu giờ (contract dùng khung 1 giờ) | `timestamp phải là đầu giờ (vd 2024-03-01T08:00:00)…` |
| Có ít nhất một số đo | `phải có ít nhất một trong avg_speed hoặc vehicle_count` |
| Đường mới phải kèm thông tin | `road_id 'ZZ' chưa có trong danh mục đường: phải gửi kèm [...]` |
| `source` khớp với dữ liệu | `source='speeds' mâu thuẫn với dữ liệu…` |
| Không trùng khóa trong cùng lần gửi | `trùng khóa (road_id, timestamp) với dòng 1…` |

**Tiện lợi cho người gửi:**

- Đường đã có trong danh mục thì không cần gửi tên, quận, tọa độ (tự bổ sung).
- `source` tự suy ra nếu bỏ trống.
- `timestamp` có múi giờ (ví dụ `…Z`) được đổi sang giờ New York, đúng contract.

**Ghi dữ liệu:**

- **UPSERT** theo `(road_id, timestamp)`: gửi lại cùng dữ liệu không tạo bản trùng, gửi giá trị mới thì ghi đè.
- Kết quả trả về số dòng thêm mới, cập nhật, bị từ chối, kèm **lý do theo từng dòng**.
- `all_or_nothing=true`: chỉ cần 1 dòng lỗi là không ghi gì (trả 422).
- Mỗi lần import được ghi vào `import_logs`.

### 3.3. Lỗi có một định dạng duy nhất

```json
{"error": {"status": 404, "type": "not_found", "message": "Không tìm thấy bản ghi giao thông id=0", "details": null}}
```

| Tình huống | HTTP | type |
|---|---|---|
| Tham số sai kiểu, ngoài giới hạn (`page_size=0`) | 422 | `validation_error` (kèm tên trường) |
| Logic sai (`start ≥ end`, `dimension` không tồn tại) | 400 | `bad_request` (kèm danh sách giá trị hợp lệ) |
| Không tìm thấy | 404 | `not_found` |
| Vi phạm ràng buộc database | 409 | `conflict` |
| Database không chạy | 503 | `service_unavailable` (gợi ý cách khắc phục) |
| Lỗi không lường trước | 500 | `internal_error` (không lộ chi tiết nội bộ) |

### 3.4. Phân trang và giới hạn

- Mọi danh sách đều phân trang (`page`, `page_size` ≤ 1000) và trả về `total`.
- `timeseries` theo giờ chỉ cho phép khi lọc theo 1 đường hoặc ≤ 31 ngày, để tránh truy vấn quá lớn.
- Import tối đa 100.000 dòng mỗi lần (413 nếu vượt).

## 4. Thực hiện

```bash
cd backend
uvicorn app.main:app --reload                 # http://localhost:8000/docs
python -m pytest                              # 21 test trên SQLite, không cần PostgreSQL
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_test python -m pytest   # đủ 22 test
```

**Test đi qua đúng đường nạp thật.** `conftest.py` sinh một bộ dữ liệu nhỏ đúng contract (3 đường × 48 giờ, thời tiết, bảng analytics), nạp bằng **chính** `load_processed`, rồi gọi API qua HTTP. Nhờ vậy test kiểm tra cả loader, database và API cùng lúc.

| File test | Nội dung |
|---|---|
| `test_load.py` (4) | Số dòng, nạp lại idempotent, rollback khi sai contract, phát hiện road_id lạ |
| `test_api.py` (10) | Lọc, phân trang, 404/400/422, thống kê, bất thường, tính năng chỉ có trên PostgreSQL |
| `test_import.py` (8) | Import một phần, upsert idempotent, đổi múi giờ, all_or_nothing, trùng khóa, file CSV, thời tiết, nạp lại Spark |

## 5. Kết quả

- **22/22 test đạt** trên PostgreSQL 16.2 (máy ảo của nhóm) và PostgreSQL 16.15 (môi trường phát triển).
- Thời gian phản hồi trên dữ liệu thật (bước 21): đa số endpoint 3–30 ms; `statistics/live` khoảng 0,4 s; `statistics/summary` khoảng 0,4 s (đếm 805 nghìn dòng).
- Ví dụ import file `backend/examples/import_traffic_mau.csv` (6 dòng): thêm mới 4, từ chối 2 (một dòng không phải đầu giờ, một dòng tốc độ 250 km/h), tự tạo đường mới `S900001`.

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| `GET /roads/{id}` lỗi 500 lần đầu | Pydantic yêu cầu trường `stats` khi chuyển từ ORM. Tạo phần thông tin đường trước rồi gắn `stats` sau |
| Test chạy theo thứ tự chữ cái: test import làm thay đổi số dòng mà test loader kiểm tra | Test loader nạp lại dữ liệu trước khi đếm |
| SQLite không có `stddev`, `percentile_cont`, `date_trunc` | Test các tính năng này đánh dấu `pg_only`, chạy khi có `TEST_DATABASE_URL` |
