# Báo cáo Data Cleaning (bước 07)

Sinh tự động bởi `python -m data_integration.cleaning.run` lúc 2026-10-13 15:18.

## Tổng quan

| Nguồn | Vào | Ra | Giữ lại | Thời gian |
|---|---|---|---|---|
| weather | 43,920 | 43,915 | 100.0% | 0.3s |
| volume | 95,203 | 94,824 | 99.6% | 1.2s |
| speeds | 11,970,346 | 9,048,108 | 75.6% | 29.6s |
| links | 124 | 125 | 100.8% | 0.1s |

## Thời tiết

Số dòng vào: **43,920** → số dòng ra: **43,915**

| # | Quy tắc | Số dòng bị ảnh hưởng | % so với đầu vào | Xử lý | Ghi chú |
|---|---|---|---|---|---|
| 1 | Thiếu thời gian, quận hoặc chỉ số đo | 0 | 0.00% | loại bỏ |  |
| 2 | Nhiệt độ ngoài [-40, 50] °C hoặc mưa/tuyết âm | 0 | 0.00% | loại bỏ |  |
| 3 | Trùng (trạm, giờ địa phương) do lùi giờ 03/11 | 10 | 0.02% | gộp 2 → 1 | Số đo lấy trung bình; weather_code lấy giá trị lớn hơn (thời tiết xấu hơn) |
| 4 | Mã WMO không thuộc nhóm nào | 0 | 0.00% | giữ lại, weather_condition = null |  |
| 5 | Đổi tên cột theo contract | 43,915 | 99.99% | đổi tên | temperature_2m → temperature, rain → rainfall, time_local → timestamp |

## Lưu lượng

Số dòng vào: **95,203** → số dòng ra: **94,824**

| # | Quy tắc | Số dòng bị ảnh hưởng | % so với đầu vào | Xử lý | Ghi chú |
|---|---|---|---|---|---|
| 1 | Thời gian không hợp lệ, phút lệch lưới 15', vol rỗng hoặc âm | 0 | 0.00% | loại bỏ |  |
| 2 | Tên quận không thuộc 5 quận chuẩn | 0 | 0.00% | loại bỏ |  |
| 3 | Chuẩn hóa chữ hoa và khoảng trắng: street | 0 | 0.00% | sửa |  |
| 4 | Chuẩn hóa chữ hoa và khoảng trắng: fromst | 95,203 | 100.00% | sửa |  |
| 5 | Chuẩn hóa chữ hoa và khoảng trắng: tost | 95,203 | 100.00% | sửa |  |
| 6 | Chuẩn hóa chữ hoa và khoảng trắng: direction | 0 | 0.00% | sửa |  |
| 7 | wktgeom không đọc được | 0 | 0.00% | loại bỏ |  |
| 8 | Đổi tọa độ EPSG:2263 (feet) → WGS84 (lat/lon) | 95,203 | 100.00% | chuyển đổi | dùng pyproj |
| 9 | Đoạn có nhiều hơn 1 tọa độ | 1,728 | 1.82% | thống nhất về tọa độ trung bình của đoạn |  |
| 10 | Trùng (đoạn, hướng, thời điểm) từ nhiều đợt khảo sát | 379 | 0.40% | gộp: vol = trung bình làm tròn | Profiling: 379 cặp, tất cả đều khác giá trị |
| 11 | vol ngoại lai mạnh (Tukey k=3) | 2,083 | 2.19% | GIỮ LẠI, gắn cờ flag_outlier | ngưỡng [-254, 390] xe/15 phút; có thể là đại lộ đông thật |
| 12 | vol = 0 | 1,292 | 1.36% | GIỮ LẠI, gắn cờ flag_zero |  |

Thống kê `vol` sau làm sạch (xe/15 phút): count=94,824.0, mean=92.4, std=136.7, min=0.0, 25%=22.0, 50%=57.0, 75%=114.0, max=2,187.0

## Tốc độ

Số dòng vào: **11,970,346** → số dòng ra: **9,048,108**

| # | Quy tắc | Số dòng bị ảnh hưởng | % so với đầu vào | Xử lý | Ghi chú |
|---|---|---|---|---|---|
| 1 | speed hoặc data_as_of không đọc được | 0 | 0.00% | loại bỏ |  |
| 2 | status = -101 (bản ghi cảm biến không hợp lệ) | 2,922,227 | 24.41% | loại bỏ | Profiling: phân bố tốc độ lệch hẳn, có tuyến hỏng 100% |
| 3 | speed ≤ 0 với status = 0 | 0 | 0.00% | loại bỏ |  |
| 4 | speed > 100 mph | 11 | 0.00% | loại bỏ | Bất hợp lý trong đô thị |
| 5 | Trùng (link_id, thời điểm) | 0 | 0.00% | loại bỏ bản sau |  |

### Theo tháng

| Tháng | Vào | Ra | Giữ lại | Tốc độ TB (km/h) |
|---|---|---|---|---|
| 2024-01 | 996,717 | 777,896 | 78.0% | 65.2 |
| 2024-02 | 606,855 | 461,982 | 76.1% | 62.5 |
| 2024-03 | 1,054,554 | 800,924 | 75.9% | 60.3 |
| 2024-04 | 1,056,771 | 789,399 | 74.7% | 60.9 |
| 2024-05 | 1,082,408 | 786,932 | 72.7% | 59.0 |
| 2024-06 | 1,041,105 | 802,276 | 77.1% | 60.0 |
| 2024-07 | 1,052,885 | 798,493 | 75.8% | 62.9 |
| 2024-08 | 1,007,758 | 772,921 | 76.7% | 61.9 |
| 2024-09 | 1,052,806 | 790,569 | 75.1% | 60.6 |
| 2024-10 | 1,088,596 | 813,583 | 74.7% | 61.7 |
| 2024-11 | 1,053,440 | 787,519 | 74.8% | 62.6 |
| 2024-12 | 876,451 | 665,614 | 75.9% | 60.3 |

### Ngày mất dữ liệu (độ phủ giờ < 50%)

22 / 366 ngày: 2024-01-29, 2024-01-30, 2024-01-31, 2024-02-01, 2024-02-02, 2024-02-03, 2024-02-04, 2024-02-05, 2024-02-06, 2024-02-07, 2024-02-08, 2024-02-09, 2024-02-10, 2024-02-11, 2024-02-12, 2024-03-12, 2024-08-25, 2024-12-24, 2024-12-25, 2024-12-26, 2024-12-27, 2024-12-28

Các ngày này **không bị xóa hay nội suy**. Chúng được đánh dấu trong `data/interim/speeds_coverage_daily.parquet` để các bước phân tích loại trừ khi cần.

## Danh mục tuyến

Số dòng vào: **124** → số dòng ra: **125**

| # | Quy tắc | Số dòng bị ảnh hưởng | % so với đầu vào | Xử lý | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tuyến có trong bản ghi nhưng thiếu trong links.csv | 1 | 0.81% | bổ sung (không có tọa độ) |  |
| 2 | Tên tuyến lẫn chữ thường | 51 | 41.13% | viết hoa |  |
| 3 | link_points bị cắt ở 255 ký tự (giới hạn Socrata) | 68 | 54.84% | bỏ cặp tọa độ cuối bị cụt |  |
| 4 | Tuyến không có tọa độ hợp lệ trong New York | 1 | 0.81% | giữ lại, tọa độ = null |  |
| 5 | Tọa độ đại diện = trung bình các điểm của tuyến | 124 | 100.00% | tính mới |  |

| Chỉ số | Giá trị |
|---|---|
| Số tuyến | 125 |
| Có tọa độ | 124 |
| Số điểm tọa độ trung bình mỗi tuyến | 10.1 |
| Phân bố theo quận | {'Queens': 37, 'Manhattan': 26, 'Staten Island': 25, 'Bronx': 24, 'Brooklyn': 13} |
