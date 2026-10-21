# 10. Tạo bảng tích hợp `integrated_traffic`

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026. **Kết thúc Phase 1 (Data Integration).**
> Báo cáo: `docs/bao-cao/10_integrated.md` · Đầu ra: `data/processed/integrated_traffic/` (6,5 MB, 12 partition)

## 1. Mục tiêu

Ghép 3 nguồn đã được làm sạch (bước 07), chuẩn hóa (bước 08) và nối đường (bước 09) thành **một bảng duy nhất đúng data contract** (bước 03). Đây là đầu ra chính của Phase 1 và là đầu vào của Phase 2.

## 2. Giải trình

### 2.1. Thứ tự phép ghép

```
T_speed  (link, giờ)   ┐
                       ├─ FULL OUTER JOIN theo (road_id, timestamp)  ─┐
T_volume (đoạn, giờ)   ┘   road_id lấy từ bảng roads (bước 09)        │
                                                                      ├─ LEFT JOIN thời tiết theo (district, timestamp)
                                                                      ┘
```

| Phép ghép | Vì sao |
|---|---|
| **FULL OUTER JOIN** 2 nguồn giao thông | Giữ cả dòng chỉ có 1 nguồn. Nếu dùng INNER JOIN thì chỉ còn 153 dòng có cả hai nguồn, mất 99,98% dữ liệu |
| **LEFT JOIN** thời tiết | Thời tiết là thông tin *bổ sung*. Thiếu thời tiết thì dòng giao thông vẫn được giữ |
| Ghép thời tiết theo **(quận, giờ)** | Mỗi quận có 1 điểm thời tiết (bước 05). Tức là gán điểm thời tiết gần nhất theo đơn vị hành chính |
| Cột `source` | Đánh dấu dòng đến từ nguồn nào (truy vết nguồn gốc, data lineage), để Phase 2 lọc đúng khi phân tích |

### 2.2. Ca đặc biệt: giờ không tồn tại

Ngày **10/03/2024** New York chuyển sang giờ mùa hè, đồng hồ nhảy từ 01:59 lên 03:00, nên **02:00 không tồn tại**.

- Nguồn tốc độ xử lý đúng: không có bản ghi nào ở giờ 2.
- Nguồn lưu lượng có **2 bản ghi lúc 02:00**: máy đếm vẫn ghi theo đồng hồ giờ chuẩn.
- 02:xx giờ chuẩn chính là 03:xx giờ mùa hè, nên hai dòng này được **lấy thời tiết của giờ kế tiếp**, có test riêng cho trường hợp này.

Cùng với ngày lùi giờ 03/11 (bước 06–07), đây là ví dụ thực tế cho thấy **thời gian là một nguồn không đồng nhất** cần xử lý cẩn thận khi tích hợp.

### 2.3. Kiểm tra theo data contract trước khi ghi

Script gọi `validate_pandas()` của contract. Hàm này kiểm tra đủ cột, kiểu dữ liệu, null, miền giá trị, timestamp tròn giờ, khóa chính không trùng, và mỗi dòng có ít nhất một chỉ số giao thông. **Nếu có lỗi, script dừng và không ghi gì**, để không làm hỏng đầu vào của Phase 2.

## 3. Thực hiện

```bash
# Windows: double-click chay_buoc_10_integrate.bat
python -m data_integration.integrate
```

| File | Vai trò |
|---|---|
| `data_integration/integrate.py` | Ghép, kiểm tra contract, ghi Parquet chia partition, báo cáo |
| `tests/test_integrate.py` | 2 test: ghép đúng 3 loại `source`, giờ không tồn tại |

**Chạy lại toàn bộ Phase 1 từ đầu** (sau khi đã có `data/raw/`):

```bash
python -m data_integration.profiling.run
python -m data_integration.cleaning.run
python -m data_integration.alignment.run
python -m data_integration.linkage.run
python -m data_integration.integrate
```

Tổng thời gian khoảng **1,5 phút** cho 12 triệu dòng raw.

## 4. Kết quả (chạy thực tế)

| Chỉ số | Giá trị |
|---|---|
| Số dòng | **805.780** |
| Số đường | 211 |
| Thời gian | 2024-01-01 00:00 → 2024-12-31 23:00 |
| `source = speeds` | 789.250 |
| `source = volume` | 16.377 |
| `source = speeds+volume` | 153 |
| Dòng có thời tiết | **100%** (2 dòng lấy thời tiết của giờ kế tiếp) |
| Kiểm tra contract | **ĐẠT, 0 lỗi** |
| Dung lượng | 6,5 MB Parquet, 12 partition theo tháng |

**Theo quận:** Queens 298.078 · Bronx 165.888 · Manhattan 141.656 · Staten Island 141.370 · Brooklyn 58.788.

**Theo thời tiết:** Clear 361.507 · Cloudy 323.896 · Drizzle 85.578 · Rain 23.991 · Snow 10.806.

**Tháng 7 và 8 không có lưu lượng**, vì không có đợt khảo sát nào (bước 06). Tốc độ trung bình theo tháng ổn định ở 58–65 km/h.

### 4.1. Kiểm tra bằng PySpark (cam kết với Phase 2)

| Kiểm tra | Kết quả |
|---|---|
| Spark đọc được, schema khớp contract | ✅ không lệch kiểu cột nào |
| **Schema dữ liệu thật == schema mock dataset** | ✅ `True`. Phase 2 chỉ cần đổi đường dẫn `data/mock/` → `data/processed/` |
| Partition pruning: `filter("month = 7")` | ✅ đọc 69.564 dòng của tháng 7 mà không quét các tháng khác |

### 4.2. Xem trước kết quả cho Phase 2

Tốc độ trung bình giờ cao điểm sáng (7–9h) ngày thường, theo thời tiết, tính trên dữ liệu thật:

| Thời tiết | Số dòng | km/h |
|---|---|---|
| Cloudy | 29.164 | 55,2 |
| Snow | 1.123 | 54,3 |
| Clear | 33.107 | 53,7 |
| Rain | 1.558 | 51,0 |
| Drizzle | 7.053 | 50,2 |

Trời mưa và mưa phùn làm tốc độ giảm khoảng 5–7% so với trời quang. Tuyết lại *không* làm giảm tốc độ, một hiện tượng cần phân tích kỹ ở bước 16 (có thể do biến gây nhiễu, như đã gặp ở mock dataset, bước 04). Đây mới là so sánh thô, chưa kiểm soát theo tuyến đường và mùa.

## 5. Lưu ý cho Phase 2

1. **Đọc dữ liệu:**

```python
from common.contract import spark_schema
df = spark.read.parquet("data/processed/integrated_traffic")   # có thêm 2 cột year, month
```

2. **Ngày mất dữ liệu tốc độ** (22 ngày) nằm ở `data/processed/coverage_daily.parquet` (`is_outage = True`). Nên loại các ngày này khi so sánh theo thời gian.
3. **Lọc theo `source`** khi phân tích:
   - Tốc độ: `avg_speed IS NOT NULL`
   - Lưu lượng: `vehicle_count IS NOT NULL`
   - Quan hệ lưu lượng–tốc độ: `source = 'speeds+volume'` (153 dòng, 2 đường)
4. **Quy mô:** `integrated_traffic` đã gộp theo giờ nên chỉ còn 805.780 dòng. Bước 14 (scalability benchmark) nên chạy trên `data/interim/speeds_clean/` (9 triệu dòng) và `data/raw/speeds/` (12 triệu dòng, 1,2 GB CSV), hoặc nhân bản có kiểm soát, để đo được tác động của kích thước dữ liệu.

## 6. Kiểm tra

- [x] `python -m pytest -q` → 38 passed
- [x] `docs/bao-cao/10_integrated.md`: contract ĐẠT, 0 dòng thiếu thời tiết
- [x] Spark đọc được, schema giống hệt mock

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| 2 dòng lưu lượng lúc 02:00 ngày 10/03 không ghép được thời tiết | Nhận diện là giờ không tồn tại do chuyển sang giờ mùa hè, lấy thời tiết của giờ kế tiếp, có test |
| Ghi báo cáo JSON lỗi vì `NA` làm khóa của dict | Thay `NA` bằng nhãn "(thiếu)" trước khi thống kê |
| Không xóa được thư mục cũ trên ổ D: khi ghi lại | Ghi đè theo tên file cố định (`part-{i}.parquet`, `overwrite_or_ignore`) |
