# Data contract: `integrated_traffic`

**Phiên bản:** 1.0.0
**Nguồn sự thật:** `common/contract.py`. File này được sinh từ code, nên khi sửa contract thì sửa code trước rồi cập nhật lại file này.

## 1. Vai trò

`integrated_traffic` là **đầu ra của Phase 1** và **đầu vào của Phase 2**. Hai phase chỉ giao tiếp với nhau qua schema này. Nhờ vậy người làm PySpark có thể bắt đầu bằng mock dataset rồi thay bằng dữ liệu thật mà không phải sửa code.

## 2. Độ chi tiết (grain)

**Mỗi dòng = một đường × một giờ.**

- Khóa chính: `('road_id', 'timestamp')`, không được trùng.
- `timestamp` luôn tròn giờ (phút = giây = 0) và là giờ **địa phương New York**, không kèm múi giờ.

## 3. Các cột

| Cột | Kiểu | Null | Đơn vị | Miền giá trị | Mô tả |
|---|---|---|---|---|---|
| `road_id` | string | không | - |  | Mã đường thống nhất sau record linkage. 'L<link_id>' nếu đường có cảm biến tốc độ, 'S<segmentid>' nếu chỉ có điểm đếm lưu lượng |
| `road_name` | string | không | - |  | Tên đường đã chuẩn hóa (chữ in hoa, bỏ viết tắt) |
| `district` | string | không | - | Manhattan, Brooklyn, Queens, Bronx, Staten Island | Quận (borough) của New York |
| `latitude` | double | không | độ (WGS84) | 40.45 – 40.95 | Vĩ độ điểm đại diện của đường |
| `longitude` | double | không | độ (WGS84) | -74.3 – -73.65 | Kinh độ điểm đại diện của đường |
| `timestamp` | timestamp | không | giờ New York |  | Thời điểm BẮT ĐẦU khung 1 giờ, giờ địa phương America/New_York, không kèm múi giờ |
| `vehicle_count` | long | có | xe/giờ | 0 – 20000 | Tổng số xe trong giờ (cộng 4 khung 15 phút, mọi hướng). Null nếu đường không có điểm đếm |
| `avg_speed` | double | có | km/h | 0 – 160 | Tốc độ trung bình trong giờ (đã đổi từ mph). Null nếu đường không có cảm biến tốc độ |
| `temperature` | double | có | °C | -40 – 50 | Nhiệt độ không khí 2m |
| `rainfall` | double | có | mm | 0 – 200 | Lượng mưa trong giờ (không gồm tuyết) |
| `snowfall` | double | có | cm | 0 – 50 | Lượng tuyết rơi trong giờ |
| `weather_condition` | string | có | - | Clear, Cloudy, Fog, Drizzle, Rain, Snow, Thunderstorm | Nhóm thời tiết suy ra từ mã WMO |
| `weather_station_id` | string | có | - |  | Điểm thời tiết đã ghép (theo quận) |
| `source` | string | không | - | speeds, volume, speeds+volume | Nguồn đóng góp cho bản ghi |

## 4. Ràng buộc nghiệp vụ

1. Mỗi dòng phải có **ít nhất một** trong hai cột `vehicle_count` hoặc `avg_speed`.
2. `source` cho biết dòng được tạo từ nguồn nào:
   - `speeds`: chỉ có tốc độ.
   - `volume`: chỉ có lưu lượng.
   - `speeds+volume`: đường được record linkage nối giữa hai nguồn và có dữ liệu của cả hai trong cùng giờ.
3. Các cột thời tiết được ghép theo `district` và `timestamp`. Có thể null nếu thiếu dữ liệu thời tiết.

## 5. Lưu trữ

- Định dạng **Parquet**, thư mục `data/processed/integrated_traffic/`.
- Chia partition theo tháng: `year=YYYY/month=MM/`. Spark đọc lại sẽ có thêm 2 cột `year`, `month`, và lọc theo thời gian sẽ bỏ qua được các thư mục không liên quan (partition pruning).

## 6. Kiểm tra dữ liệu theo contract

```python
from common.contract import validate_pandas
errors = validate_pandas(df)   # [] nghĩa là dữ liệu hợp lệ
```
