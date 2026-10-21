# 07. Data cleaning

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên toàn bộ dữ liệu thật.
> Báo cáo đầy đủ: `docs/bao-cao/07_cleaning.md` · Số liệu: `docs/bao-cao/07_cleaning.json`

## 1. Mục tiêu

Biến dữ liệu raw (mọi cột là chuỗi, còn lỗi) thành dữ liệu **đúng kiểu, đúng đơn vị, không còn bản ghi lỗi**, lưu dạng Parquet ở `data/interim/`. Mọi quy tắc làm sạch đều **dựa trên số liệu profiling** ở bước 06 (mục 5.2 của hướng dẫn 06).

## 2. Giải trình

### 2.1. Nguyên tắc

| Nguyên tắc | Áp dụng |
|---|---|
| **Mọi quy tắc phải có căn cứ** | Mỗi quy tắc trong báo cáo đều chỉ rõ con số profiling làm căn cứ |
| **Ghi sổ minh bạch** | Lớp `CleaningLog` ghi lại từng quy tắc: bao nhiêu dòng bị ảnh hưởng, xử lý thế nào. Báo cáo được sinh tự động từ sổ này, nên không thể "làm sạch âm thầm" |
| **Phân biệt "loại bỏ" và "gắn cờ"** | Chỉ loại bỏ bản ghi **chắc chắn sai**, ví dụ cảm biến báo lỗi. Bản ghi **bất thường nhưng có thể đúng** (vol = 0, vol rất lớn) thì giữ lại và gắn cờ. Việc phát hiện bất thường là nhiệm vụ của bước 17; nếu xóa ngay ở đây thì bước 17 không còn gì để phát hiện |
| **Không bịa dữ liệu** | 22 ngày nguồn tốc độ mất dữ liệu được **đánh dấu**, không nội suy. Nội suy cho khoảng trống 15 ngày là tạo ra dữ liệu giả |
| **Chưa thay viết tắt** | Ở bước này chỉ viết hoa và bỏ khoảng trắng thừa. Việc đổi `AVE → AVENUE` thuộc schema alignment và record linkage (bước 08–09), để tách bạch "sửa lỗi" với "thống nhất ngữ nghĩa" |
| **Raw không bị sửa** | Ghi ra `data/interim/`. Muốn làm lại thì chạy lại từ raw |

### 2.2. Các quyết định quan trọng

| Quyết định | Lý do |
|---|---|
| Loại **toàn bộ** `status = -101`, kể cả khi speed khác 0 | Bước 06 cho thấy phân bố tốc độ của nhóm này lệch hẳn (trung vị 23,6 so với 41,6 mph) và có tuyến hỏng 100% |
| Bản ghi lưu lượng trùng khóa thì lấy **trung bình** | 2 đợt khảo sát đo cùng chỗ cùng lúc nhưng ra 2 số khác nhau. Không có căn cứ để tin đợt nào hơn |
| Thời tiết trùng giờ (ngày lùi giờ) thì gộp: số đo lấy trung bình, `weather_code` lấy giá trị **lớn hơn** | Mã WMO lớn hơn nghĩa là thời tiết xấu hơn. Chọn hướng thận trọng khi phân tích tác động của thời tiết |
| `link_points` dài đúng 255 ký tự thì **luôn bỏ cặp tọa độ cuối** | Socrata cắt chuỗi ở 255 ký tự. Cặp bị cắt có thể vẫn đúng định dạng (`-73.9351` thành `-73.93`) nhưng lệch tới khoảng 400 m. Phát hiện khi đối chiếu số tuyến bị cắt: 68 tuyến, không phải khoảng 10% như ước tính ban đầu |
| Tọa độ lưu lượng đổi EPSG:2263 → WGS84 bằng `pyproj` | Hệ tọa độ chung của contract |
| Tốc độ lưu cả mph và km/h | km/h theo contract; giữ mph để đối chiếu với nguồn gốc |

## 3. Thực hiện

```bash
# Windows: double-click chay_buoc_07_cleaning.bat
python -m data_integration.cleaning.run
```

| File | Vai trò |
|---|---|
| `data_integration/cleaning/common.py` | Chuẩn hóa tên quận và chữ, đọc `link_points`, `CleaningLog` |
| `data_integration/cleaning/weather.py` | Ép kiểu, gộp giờ trùng, đổi mã WMO, đổi tên cột theo contract |
| `data_integration/cleaning/volume.py` | Dựng timestamp, đổi tọa độ, gộp trùng khóa, gắn cờ ngoại lai |
| `data_integration/cleaning/speeds.py` | Lọc bản ghi lỗi, đổi đơn vị, làm sạch danh mục tuyến, tính độ phủ theo ngày |
| `data_integration/cleaning/run.py` | Chạy cả 3 nguồn (tốc độ xử lý từng tháng), ghi Parquet và báo cáo |
| `tests/test_cleaning.py` | 7 test |

## 4. Kết quả (chạy thực tế)

### 4.1. Tổng quan

| Nguồn | Vào | Ra | Giữ lại | Thời gian |
|---|---|---|---|---|
| Thời tiết | 43.920 | 43.915 | 100,0% | 0,3 giây |
| Lưu lượng | 95.203 | 94.824 | 99,6% | 1,2 giây |
| Tốc độ | 11.970.346 | **9.048.108** | **75,6%** | 29,6 giây |
| Danh mục tuyến | 124 | 125 | | 0,1 giây |

Dung lượng sau làm sạch: **40 MB Parquet** (raw là 1,2 GB CSV). Parquet nhỏ hơn khoảng 30 lần nhờ lưu kiểu số thay vì chuỗi và nén theo cột.

### 4.2. Đầu ra

| File | Nội dung | Khóa |
|---|---|---|
| `data/interim/weather_clean.parquet` | station_id, district, timestamp, temperature, precipitation, rainfall, snowfall, weather_code, weather_condition | (station_id, timestamp) |
| `data/interim/volume_clean.parquet` | segmentid, direction, street, fromst, tost, district, latitude, longitude, timestamp (15'), vol, n_requests, flag_outlier, flag_zero | (segmentid, direction, timestamp) |
| `data/interim/speeds_clean/month=YYYY-MM/` | link_id, timestamp, speed_mph, speed_kmh, travel_time_s | (link_id, timestamp) |
| `data/interim/links_clean.parquet` | link_id, link_name, link_name_raw, district, latitude, longitude, start/end lat/lon, n_points | link_id |
| `data/interim/speeds_coverage_daily.parquet` | date, coverage_pct, is_outage | date |

### 4.3. Chi tiết theo nguồn

**Tốc độ:**

- Loại 2.922.227 bản ghi `status = -101` (24,41%). Mọi bản ghi speed = 0 đều thuộc nhóm này, nên quy tắc "speed ≤ 0" phía sau không còn phải loại thêm dòng nào.
- Loại 11 bản ghi > 100 mph. Ở bước 06 có 87 bản ghi như vậy, 76 bản ghi còn lại đã nằm sẵn trong nhóm `-101`.
- Không có bản ghi trùng.
- Tỉ lệ giữ lại ổn định 72,7–78,0% ở mọi tháng. Tốc độ trung bình sau làm sạch là 59–65 km/h, hợp lý vì phần lớn tuyến là cao tốc và cầu.
- Đánh dấu 22 ngày mất dữ liệu: 29/01–12/02, 12/03, 25/08, 24–28/12.

**Lưu lượng:**

- Gộp 379 cặp trùng khóa.
- Viết hoa toàn bộ `fromst` và `tost` (100% dòng bị đổi vì nguồn ghi kiểu `Dead End`, `Harlem River Shoreline`, trong khi `street` vốn đã viết hoa).
- Thống nhất tọa độ cho 1 đoạn có 2 tọa độ (1.728 dòng).
- Gắn cờ 2.083 dòng ngoại lai (ngưỡng 390 xe/15 phút) và 1.292 dòng vol = 0.
- Sau làm sạch: trung vị 57 xe/15 phút, trung bình 92,4, lớn nhất 2.187.

**Thời tiết:** chỉ gộp 10 dòng trùng giờ thành 5 (ngày lùi giờ). Mỗi trạm còn 8.783 giờ, đúng bằng số mốc giờ địa phương thực có của năm 2024.

**Danh mục tuyến:**

- Bổ sung 1 tuyến có trong bản ghi nhưng thiếu trong `links.csv`; tuyến này không có tọa độ.
- Viết hoa 51 tên tuyến (41%).
- Bỏ cặp tọa độ cuối bị cắt ở 68 tuyến.
- 124/125 tuyến có tọa độ đại diện, trung bình 10,1 điểm mỗi tuyến.

## 5. Kiểm tra

- [x] `python -m pytest -q` → 22 passed, trên cả pandas 3.0 (Windows) và pandas 2.3 (máy ảo Linux)
- [x] Đọc lại được 9.048.108 dòng tốc độ, timestamp từ 2024-01-01 00:03 đến 2024-12-31 23:58
- [x] Tọa độ tuyến hợp lý (ví dụ Lincoln Tunnel: 40,76 / −74,006)

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Ước tính ban đầu "khoảng 10% `link_points` bị cắt" là sai, thực tế là 55% | Ước tính ban đầu chỉ kiểm tra chuỗi có kết thúc bằng chữ số hay không. Báo cáo cleaning đếm theo độ dài 255 mới cho số đúng. Code được sửa để luôn bỏ cặp cuối, có test cho trường hợp cặp bị cắt nhưng vẫn đúng định dạng |
| `PermissionError` khi xóa thư mục kết quả cũ trên ổ D: | Thư mục làm việc không cho xóa file. Đổi sang **ghi đè từng file**, không xóa cả thư mục |
| Tiến trình chạy nền bị dừng khi phiên terminal kết thúc | Chạy trực tiếp. Toàn bộ bước chỉ mất khoảng 32 giây |
