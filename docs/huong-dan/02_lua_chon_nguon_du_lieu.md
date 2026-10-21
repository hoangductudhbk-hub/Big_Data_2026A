# 02. Lựa chọn và giải trình nguồn dữ liệu

## 1. Mục tiêu

Chọn các nguồn dữ liệu đáp ứng yêu cầu của đề bài (`Projects.pdf`: dữ liệu thỏa mãn tối thiểu **3V: Volume – Velocity – Variety**) và yêu cầu của plan (`Big_Data_Project_Plan.md`: 2–3 nguồn có schema khác nhau, gồm giao thông, thời tiết và đường).

## 2. Các phương án đã cân nhắc

| Phương án | Ưu điểm | Nhược điểm | Kết luận |
|---|---|---|---|
| Giao thông Hà Nội | Gần bối cảnh Việt Nam | Không có dữ liệu cảm biến giao thông công khai, phải tự sinh số liệu | Loại |
| Mô phỏng hoàn toàn | Chủ động | Không phải dữ liệu thật, khó bảo vệ phần phân tích | Loại |
| **NYC Open Data + Open-Meteo** | Dữ liệu thật, rất lớn, cập nhật liên tục, nhiều nguồn khác schema | Bối cảnh nước ngoài | **Chọn** |

> Các ví dụ trong plan như "Cau Giay" hay "Nguyen Trai" chỉ mang tính minh họa. Phương pháp (profiling, cleaning, schema alignment, record linkage...) được giữ nguyên, chỉ thay dữ liệu Hà Nội bằng dữ liệu New York. Các "quận" (district) tương ứng với 5 borough của New York: Manhattan, Brooklyn, Queens, Bronx, Staten Island.

## 3. Mô tả các nguồn đã chọn

Mọi thông tin dưới đây đã được kiểm tra trực tiếp qua API vào ngày 13/10/2026.

### Nguồn 1: NYC DOT Traffic Speeds

- **Mã dataset:** `i4gi-tjb9`. API: `https://data.cityofnewyork.us/resource/i4gi-tjb9.json`
- **Nội dung:** tốc độ trung bình của xe trên từng tuyến đường (link), đo bằng cảm biến của Sở Giao thông New York.
- **Quy mô:** khoảng **104 triệu dòng** theo metadata của dataset. Dữ liệu tập trung từ năm 2018 tới nay, tần suất cập nhật được ghi là *"several times per minute"*.
- **Các cột chính:**

| Cột | Ví dụ | Ý nghĩa |
|---|---|---|
| `id` | 211 | Mã cảm biến |
| `speed` | 32.31 | Tốc độ, **đơn vị dặm/giờ (mph)** |
| `travel_time` | 505 | Thời gian đi hết link (giây) |
| `status` | 0 | Trạng thái bản ghi |
| `data_as_of` | 2026-10-07T14:41:07.000 | Thời điểm đo (giờ New York) |
| `link_id` | 4362250 | Mã tuyến đường |
| `link_points` | "40.78795,-73.790191 ..." | Chuỗi tọa độ lat,lon của tuyến |
| `borough` | Queens | Quận |
| `link_name` | CVE NB GCP - WILLETS PT BLVD | Tên tuyến, **viết tắt nhiều** |

### Nguồn 2: NYC Automated Traffic Volume Counts

- **Mã dataset:** `7ym2-wayt`. API: `https://data.cityofnewyork.us/resource/7ym2-wayt.json`
- **Nội dung:** số xe đếm tự động theo từng **15 phút** trên các đoạn phố, trong các đợt khảo sát.
- **Quy mô:** khoảng **1,9 triệu dòng**, từ năm 2000 đến 2026. Năm 2024 có 95.203 dòng.
- **Các cột chính:**

| Cột | Ví dụ | Ý nghĩa |
|---|---|---|
| `requestid` | 12512 | Mã đợt khảo sát |
| `boro` | Queens | Quận (tên cột khác nguồn 1) |
| `yr`, `m`, `d`, `hh`, `mm` | 2013, 3, 7, 4, 15 | Thời gian **tách thành 5 cột** |
| `vol` | 5 | Số xe trong 15 phút |
| `segmentid` | 55135 | Mã đoạn phố |
| `wktgeom` | POINT (1035363.4 185093.4) | Tọa độ hệ **NY State Plane (feet)**, không phải lat/lon |
| `street`, `fromst`, `tost` | 122 PL, SUTTER AV, ROCKAWAY BLVD | Tên phố và đoạn từ–đến |
| `direction` | SB | Hướng xe |

### Nguồn 3: Open-Meteo Historical Weather API

- **API:** `https://archive-api.open-meteo.com/v1/archive`. Miễn phí cho mục đích phi thương mại, không cần tài khoản.
- **Biến lấy theo giờ:** `temperature_2m` (°C), `precipitation`, `rain` (mm), `snowfall` (cm), `weather_code` (mã WMO).
- **Vị trí:** 5 điểm đại diện cho 5 quận của New York. Gọi một lần cho nhiều tọa độ được.

## 4. Tính không đồng nhất giữa các nguồn

Đây là lý do cần làm Data Integration:

| Khía cạnh | Speeds | Volume | Weather |
|---|---|---|---|
| Đại lượng | Tốc độ (mph) | Số xe/15 phút | Nhiệt độ, mưa |
| Thời gian | Chuỗi ISO, khoảng vài phút | 5 cột số rời, đúng 15 phút | Mỗi giờ |
| Vị trí | lat/lon (WGS84) | State Plane EPSG:2263 (feet) | lat/lon điểm đại diện |
| Tên quận | cột `borough` | cột `boro` | không có, phải suy từ tọa độ |
| Tên đường | `link_name`, viết tắt (`CVE NB GCP`) | `street` (`122 PL`, `ROCKAWAY BLVD`) | không có |
| Khóa định danh | `link_id` | `segmentid` | không có |

→ **Schema heterogeneity** (khác tên và cấu trúc cột) và **data heterogeneity** (khác đơn vị, định dạng, hệ tọa độ, cách viết tên) đều có, đúng với nội dung lý thuyết môn học.

## 5. Đánh giá 3V

| V | Thể hiện trong project |
|---|---|
| **Volume** | Nguồn Speeds khoảng 104 triệu dòng. Chỉ riêng giai đoạn nghiên cứu cũng đã hơn 10 triệu dòng, đủ để làm scalability benchmark ở bước 14 |
| **Velocity** | Nguồn Speeds được cập nhật vài lần mỗi phút. Có thể minh họa thêm bằng việc tải dữ liệu gia tăng (incremental) theo `data_as_of` |
| **Variety** | 3 nguồn, 3 schema, 2 hệ tọa độ, 3 độ chi tiết thời gian, 2 định dạng JSON/CSV |

Ngoài ra còn có **Veracity** (độ tin cậy): đã phát hiện ngay bản ghi có `data_as_of = 1930-12-09`, và nhiều bản ghi `speed = 0, travel_time = 0` với `status` âm. Bước 06 (profiling) sẽ thống kê đầy đủ các lỗi này.

## 6. Phạm vi nghiên cứu

- **Thời gian:** cả năm **2024** (01/01/2024 – 31/12/2024).
  - Là năm trọn vẹn gần nhất mà cả hai nguồn giao thông đều có dữ liệu.
  - Có đủ 4 mùa, gồm tuyết mùa đông và mưa bão mùa hè, để phân tích tác động của thời tiết.
  - Phạm vi chỉ là tham số trong script, thay đổi được khi cần.
- **Không gian:** toàn bộ 5 quận của New York.

## 7. Kiểm tra

- [ ] Mở được 2 URL API ở mục 3 trên trình duyệt (thêm `?$limit=5` vào cuối URL).
- [ ] Hiểu được bảng không đồng nhất ở mục 4. Đây là nội dung chính khi trình bày phần Data Integration.
