# 03. Data contract `integrated_traffic`

## 1. Mục tiêu

Chốt **schema chuẩn** của bộ dữ liệu tích hợp trước khi viết bất kỳ code xử lý nào. Đây là việc đầu tiên của Phase 0 trong plan ("Xác định schema chuẩn mà Phase 1 phải cung cấp cho Phase 2").

Đầu ra:
- `common/contract.py`: contract dạng code, gồm danh sách cột, kiểu, miền giá trị, hàm kiểm tra và schema cho Spark/Arrow.
- `docs/data_contract.md`: contract dạng tài liệu, sinh từ code.
- `tests/test_contract.py`: test cho hàm kiểm tra.

## 2. Giải trình

### 2.1. Vì sao cần contract

Trong lý thuyết tích hợp dữ liệu, contract chính là **lược đồ trung gian (mediated schema)**: một lược đồ chung mà mọi nguồn đều phải ánh xạ vào. Ánh xạ ở project này đi theo hướng **GAV (Global-as-View)**: mỗi cột của `integrated_traffic` được định nghĩa bằng một biểu thức trên các nguồn.

| Cột trong contract | Định nghĩa từ nguồn (GAV) |
|---|---|
| `avg_speed` | AVG(`speeds.speed`) × 1.609344, nhóm theo link và giờ |
| `vehicle_count` | SUM(`volume.vol`) của 4 khung 15 phút, nhóm theo segment và giờ |
| `timestamp` | `date_trunc('hour', speeds.data_as_of)` hoặc `make_timestamp(yr, m, d, hh)` |
| `district` | `speeds.borough` / `volume.boro`, chuẩn hóa về 5 tên chuẩn |
| `latitude, longitude` | Trung điểm của `link_points`, hoặc `wktgeom` đổi từ EPSG:2263 sang WGS84 |
| `temperature, rainfall, snowfall, weather_condition` | Open-Meteo, ghép theo quận và giờ |

Contract còn giúp hai người làm song song: Người 3 dùng mock dataset để viết PySpark, Người 2 làm dữ liệu thật. Khi ghép lại, Người 3 không phải sửa code.

### 2.2. Các quyết định thiết kế

| Quyết định | Lý do |
|---|---|
| **Grain = đường × giờ** | Hai nguồn giao thông có tần suất khác nhau (vài phút và 15 phút), còn thời tiết đo theo giờ. Giờ là mức chi tiết chung nhỏ nhất mà cả 3 nguồn cùng có |
| **Tốc độ dùng km/h** | Chuẩn hóa đơn vị. Nguồn gốc dùng mph, khi đổi nhân với `MPH_TO_KMH = 1.609344` |
| **Tọa độ dùng WGS84 (lat/lon)** | Hệ chung để vẽ bản đồ trên dashboard và để tính khoảng cách khi làm record linkage |
| **`timestamp` là giờ New York, không kèm múi giờ** | Phân tích giờ cao điểm cần giờ địa phương (8h sáng ở New York). Dùng kiểu `TimestampNTZ` của Spark để kết quả không bị lệch theo múi giờ của máy chạy |
| **`vehicle_count` và `avg_speed` cho phép null** | Không phải đường nào cũng có cả hai loại cảm biến. Ép giá trị 0 vào sẽ làm sai thống kê, nên để null là trung thực hơn |
| **Thêm cột `source`** | Truy vết nguồn gốc (data lineage), và biết dòng nào thực sự được ghép từ 2 nguồn |
| **Thêm cột `snowfall`** | New York có tuyết, và tuyết ảnh hưởng mạnh tới giao thông. Plan gốc chỉ có `rainfall` vì lấy ví dụ Hà Nội |
| **`weather_condition` có 7 nhóm** | Mã WMO có hơn 25 giá trị, quá chi tiết để thống kê. Gom lại thành 7 nhóm có ý nghĩa: Clear, Cloudy, Fog, Drizzle, Rain, Snow, Thunderstorm |

### 2.3. So với ví dụ trong plan

Plan gợi ý 8 cột: `road_id, timestamp, vehicle_count, avg_speed, temperature, rainfall, weather_condition, district`. Contract giữ **đủ cả 8 cột** và bổ sung thêm 6 cột: `road_name, latitude, longitude, snowfall, weather_station_id, source`. Các cột bổ sung phục vụ dashboard (bản đồ), phân tích tuyết và truy vết nguồn gốc.

## 3. Thực hiện

1. Viết `common/contract.py`, gồm:
   - Danh sách cột `INTEGRATED_TRAFFIC`. Mỗi cột có tên, kiểu, cho phép null hay không, đơn vị, miền giá trị và mô tả.
   - Hàm `wmo_to_condition(code)` đổi mã WMO sang nhóm thời tiết.
   - Hàm `spark_schema()` và `arrow_schema()` để Spark và pandas dùng cùng một schema.
   - Hàm `validate_pandas(df)` kiểm tra: đủ cột, null, kiểu, miền giá trị, timestamp tròn giờ, mỗi dòng có ít nhất một chỉ số giao thông, khóa chính không trùng.
2. Sinh `docs/data_contract.md` từ code để tài liệu luôn khớp với code.
3. Viết test và chạy:

```bash
python -m pytest -q tests/test_contract.py
```

## 4. Kết quả

```text
4 passed
```

Schema Spark được sinh ra:

```text
struct<road_id:string,road_name:string,district:string,latitude:double,longitude:double,
timestamp:timestamp_ntz,vehicle_count:bigint,avg_speed:double,temperature:double,rainfall:double,
snowfall:double,weather_condition:string,weather_station_id:string,source:string>
```

## 5. Kiểm tra

- [ ] `pytest tests/test_contract.py` pass.
- [ ] Mở `docs/data_contract.md`, đọc và hiểu được từng cột.
- [ ] Cả nhóm đồng ý với contract trước khi sang bước 04.

## 6. Cách dùng ở các bước sau

```python
# Phase 1: kiểm tra trước khi xuất integrated_traffic
from common.contract import validate_pandas
assert validate_pandas(df) == []

# Phase 2: đọc dữ liệu với schema cố định
from common.contract import spark_schema
df = spark.read.schema(spark_schema()).parquet("data/processed/integrated_traffic")
```
