# 05. Thu thập dữ liệu

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026. Đã tải đủ 3 nguồn cho cả năm 2024. Số dòng của từng file khớp đúng với số dòng API báo.

## 1. Mục tiêu

Tải dữ liệu gốc của 3 nguồn trong phạm vi năm 2024 về `data/raw/`, **giữ nguyên dữ liệu gốc**: mọi cột lưu dạng chuỗi, không sửa, không lọc.

## 2. Giải trình

| Quyết định | Lý do |
|---|---|
| Tầng raw giữ nguyên, đọc mọi cột dạng chuỗi | Không làm mất thông tin trước bước profiling. Nếu ép `speed` sang số ngay thì không còn biết giá trị gốc bị lỗi ra sao |
| Tải speeds **theo từng tháng** | Khoảng 1 triệu dòng/tháng. Chia nhỏ để nếu mạng lỗi thì chỉ hỏng 1 tháng, chạy lại sẽ bỏ qua các tháng đã xong |
| Phân trang 50.000 dòng/lần, sắp xếp theo `:id` | Sắp xếp theo khóa ổn định thì các trang không trùng và không sót dòng. Nhờ đó cũng **nối tiếp được** khi bị ngắt giữa chừng |
| Đếm trước bằng `count(*)` rồi so với số dòng tải được | Đảm bảo **tải đủ dữ liệu**. Nếu thiếu, script báo lỗi và không đánh dấu file là hoàn thành |
| Ghi ra file `.part`, chỉ đổi tên khi đã xong | File chính chỉ xuất hiện khi đã tải trọn vẹn (ghi kiểu atomic) |
| Bỏ các cột polyline khỏi bản ghi speeds, tải riêng `links.csv` | `link_points` dài hàng trăm ký tự và lặp lại ở mọi bản ghi. Tách thông tin tĩnh của tuyến khỏi dữ liệu đo, đúng tinh thần chuẩn hóa dữ liệu |
| Thời tiết lấy theo `unixtime` + GMT, xin thêm 1 ngày ở mỗi đầu, rồi cắt lại theo giờ New York | Open-Meteo dùng **một độ lệch múi giờ cố định** cho cả khoảng ngày, nên sẽ sai giờ một nửa năm do giờ mùa hè. Xin dư mỗi đầu 1 ngày để bao trọn năm 2024 theo giờ địa phương (xem vấn đề số 8) |
| Thử lại tự động khi gặp lỗi 429/5xx hoặc mất kết nối | API công khai có giới hạn tốc độ, đường truyền qua VPN đôi lúc bị ngắt. Script chờ tăng dần 2s, 4s, 8s… tối đa 6 lần |
| Đã có file thì không gọi API | Chạy lại được bất cứ lúc nào, kể cả khi không có VPN |

## 3. Chuẩn bị

1. Máy Windows có Python 3.11 trở lên. Không cần Java cho bước này.
2. **Mạng truy cập được NYC Open Data.** Từ Việt Nam bị chặn (xem vấn đề số 2), nên phải **bật VPN cho toàn máy** với máy chủ ở nước ngoài. Đã dùng thành công Proton VPN bản miễn phí, máy chủ Romania và Hà Lan.
3. Ổ đĩa trống ít nhất 2 GB.
4. *(Không bắt buộc)* App token miễn phí của NYC Open Data, đặt vào biến môi trường `NYC_APP_TOKEN`. Lần chạy thực tế không dùng token và không bị giới hạn tốc độ.

## 4. Thực hiện

### Cách 1 (Windows): double-click `tai_du_lieu.bat`

File này tự làm 4 việc:

1. Tìm Python trên máy.
2. Tạo môi trường ảo `.venv`.
3. Cài 2 thư viện trong `requirements-collect.txt` (`requests`, `pandas`).
4. Chạy `python -m data_integration.collect.run_all`.

Log được lưu tại `data\raw\collect_log.txt`.

> ⚠️ **Không bấm chuột vào bên trong cửa sổ cmd khi đang chạy.** Windows bật chế độ chọn chữ (QuickEdit), thanh tiêu đề hiện "Select", và chương trình **tạm dừng** cho đến khi nhấn Esc (xem vấn đề số 5).

### Cách 2: dòng lệnh

```bash
python -m data_integration.collect.run_all              # cả 3 nguồn
python -m data_integration.collect.fetch_weather        # từng nguồn riêng
python -m data_integration.collect.fetch_volume
python -m data_integration.collect.fetch_speeds --months 2024-01
```

Bị ngắt giữa chừng thì **chạy lại đúng lệnh cũ**. Các file đã xong được bỏ qua, file đang dở (`.part`) được nối tiếp từ trang cuối cùng đã ghi trọn vẹn.

### Mã nguồn

| File | Vai trò |
|---|---|
| `data_integration/config.py` | Phạm vi thời gian, mã dataset, tọa độ 5 điểm thời tiết, đường dẫn |
| `data_integration/collect/http_utils.py` | GET có thử lại, ghi nội dung lỗi vào log |
| `data_integration/collect/socrata.py` | Đếm, phân trang, ghi `.part`, nối tiếp, kiểm tra đủ dòng |
| `data_integration/collect/fetch_weather.py` | Open-Meteo → `data/raw/weather/` |
| `data_integration/collect/fetch_volume.py` | Volume Counts → `data/raw/volume/volume_2024.csv` |
| `data_integration/collect/fetch_speeds.py` | Speeds → `data/raw/speeds/speeds_2024-MM.csv` + `links.csv` |
| `tests/test_collect.py` | 8 test: giờ mùa hè, cắt theo giờ địa phương, phân trang, phát hiện thiếu dòng, nối tiếp file dở |

## 5. Kết quả (chạy thực tế ngày 13/10/2026)

### 5.1. Dữ liệu đã tải

| Nguồn | File | Số dòng | Dung lượng | Thời gian tải |
|---|---|---|---|---|
| Thời tiết | `weather/open_meteo_2024-01-01_2024-12-31.csv` | 43.920 (5 trạm × 8.784 giờ) | 4,4 MB | khoảng 6 giây |
| Lưu lượng | `volume/volume_2024.csv` | 95.203 | 12,8 MB | 18 giây |
| Danh mục tuyến | `speeds/links.csv` | 124 tuyến | 38 KB | 50 giây (12 lượt gọi) |
| Tốc độ | `speeds/speeds_2024-01.csv` … `speeds_2024-12.csv` | **11.970.346** | **1,19 GB** | **49 phút** |
| **Tổng** | | **12.109.469** | **1,2 GB** | |

Chi tiết tốc độ theo tháng (số dòng tải được = số dòng API báo):

| Tháng | Số dòng | | Tháng | Số dòng |
|---|---|---|---|---|
| 01 | 996.717 | | 07 | 1.052.885 |
| 02 | **606.855** | | 08 | 1.007.758 |
| 03 | 1.054.554 | | 09 | 1.052.806 |
| 04 | 1.056.771 | | 10 | 1.088.596 |
| 05 | 1.082.408 | | 11 | 1.053.440 |
| 06 | 1.041.105 | | 12 | 876.451 |

Tháng 2 ít hơn hẳn các tháng khác (khoảng 60%). Danh mục tuyến lấy mẫu lúc 12:00 ngày 01/02 cũng trả về 0 bản ghi. Bước 06 xác định chính xác các ngày bị mất dữ liệu.

Tốc độ tải: khoảng 50.000 dòng mỗi 6–10 giây, tức khoảng 4–5 phút một tháng.

### 5.2. Kiểm tra số dòng

Đếm số dòng của từng file (`wc -l` trừ dòng tiêu đề) cho kết quả **khớp 100%** với `count(*)` của API ở cả 14 file. Không còn file `.part` nào.

### 5.3. Test

```text
python -m pytest -q
15 passed
```

## 6. Kiểm tra

- [x] Có đủ 12 file `speeds_2024-MM.csv`, không còn file `.part`.
- [x] `speeds_2024-01.csv` có 996.717 dòng.
- [x] `volume_2024.csv` có 95.203 dòng.
- [x] File thời tiết có đủ 5 `station_id`, mỗi trạm 8.784 giờ.

## 7. Các vấn đề gặp phải và cách xử lý

Đây là phần quan trọng khi giải trình: thu thập dữ liệu thật hiếm khi suôn sẻ ngay từ đầu.

| # | Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|---|
| 1 | Máy ảo Linux dùng để phát triển không gọi được API (HTTP 000) | Môi trường máy ảo chỉ cho truy cập một danh sách tên miền | Chạy script tải trực tiếp trên máy Windows của nhóm |
| 2 | **HTTP 403 Forbidden** ở mọi request tới NYC Open Data | **Nền tảng Socrata chặn IP Việt Nam.** Kiểm chứng: trang chủ `data.cityofnewyork.us` và cổng dữ liệu Chicago (cũng chạy Socrata) đều trả 403; chuyển sang mạng 5G vẫn bị; trong khi gọi từ máy chủ ở Mỹ vẫn bình thường | Bật VPN cho toàn máy (Proton VPN miễn phí). VPN chỉ áp cho trình duyệt (như VPN tích hợp trong Cốc Cốc) **không đủ**, vì script Python chạy ngoài trình duyệt |
| 3 | Đổi User-Agent không hết lỗi 403 | Máy chủ chặn theo IP chứ không theo nhãn trình duyệt | Vẫn giữ User-Agent ghi rõ là project học tập (thông lệ tốt khi gọi API công khai) |
| 4 | Log báo "yr không phải kiểu số" dù thực tế `yr` là số | Code chuyển sang so sánh chuỗi khi gặp **bất kỳ** lỗi HTTP nào, kể cả 403 | Chỉ chuyển khi lỗi là HTTP 400 (sai kiểu). Ghi nội dung phản hồi lỗi vào log |
| 5 | Script đứng im **64 phút** ở 150.000 dòng của tháng 1, không báo lỗi | Người dùng bấm vào cửa sổ cmd để chụp màn hình → Windows bật **QuickEdit Mode** và tạm dừng tiến trình | Nhấn Esc để chạy tiếp. Thêm cảnh báo vào hướng dẫn. Bổ sung khả năng **nối tiếp file dở** để không mất công tải lại |
| 6 | `ConnectionResetError (10054)` lúc 21:22 | Đường truyền VPN miễn phí bị ngắt tạm thời | Script tự thử lại sau 2 giây và chạy tiếp, không cần can thiệp |
| 7 | Chạy lại khi đã tắt VPN vẫn bị 403 dù dữ liệu đã đủ | Script vẫn gọi API để đếm dòng và lấy danh mục tuyến trước khi kiểm tra file đã có hay chưa | Kiểm tra file tồn tại **trước** khi gọi API |
| 8 | Thời tiết thiếu 5 giờ cuối ngày 31/12/2024 và thừa 5 giờ của 31/12/2023 (**phát hiện ở bước 06**) | Gọi API theo ngày UTC, trong khi phạm vi nghiên cứu tính theo giờ New York (UTC−5) | Xin thêm 1 ngày mỗi đầu rồi cắt đúng `[2024-01-01 00:00, 2024-12-31 23:00]` giờ địa phương, có test kiểm chứng. File cũ lưu tại `weather/_cu_lech_mui_gio/` để đối chiếu |

> **Bài học:** vấn đề số 8 cho thấy giá trị của bước profiling. Nếu không lập bảng thống kê theo tháng, dòng "2023-12" dư thừa sẽ không bị phát hiện, và 5 giờ cuối năm sẽ âm thầm thiếu dữ liệu thời tiết khi ghép.
