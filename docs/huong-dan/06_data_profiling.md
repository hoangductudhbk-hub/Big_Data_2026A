# 06. Data profiling

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026, chạy trên toàn bộ dữ liệu thật (12.109.469 dòng).
> Báo cáo đầy đủ: `docs/bao-cao/06_profiling.md` · Số liệu dạng máy đọc: `docs/bao-cao/06_profiling.json`

## 1. Mục tiêu

Hiểu rõ dữ liệu **trước khi** sửa nó: schema, kiểu dữ liệu, giá trị thiếu, trùng lặp, giá trị bất hợp lệ, phân bố và độ phủ theo thời gian. Mọi quyết định ở bước 07 (cleaning) phải dựa trên số liệu đo được ở bước này, không dựa trên phỏng đoán.

## 2. Giải trình

- **Profiling trên tầng raw, đọc mọi cột dạng chuỗi.** Nếu ép kiểu ngay khi đọc thì giá trị lỗi bị biến thành NaN, và ta mất dấu vết lỗi gốc.
- **Hai lớp kiểm tra:**
  - *Kiểm tra chung cho mọi cột* (`data_integration/profiling/core.py`): số giá trị rỗng, số giá trị khác nhau, giá trị phổ biến, tỉ lệ đọc được thành số, min / median / max / phân vị.
  - *Kiểm tra theo nghiệp vụ của từng nguồn* (`data_integration/profiling/sources.py`): ví dụ "speed = 0 và travel_time = 0", "phút không thuộc {0, 15, 30, 45}", "trùng khóa nhưng khác giá trị", "giờ địa phương bị trùng do lùi giờ".
- **Ngoại lai** dùng quy tắc Tukey với ngưỡng mạnh k = 3: giá trị ngoài [Q1 − 3·IQR, Q3 + 3·IQR]. Cách này không giả định dữ liệu có phân phối chuẩn.
- **Xử lý 12 triệu dòng tốc độ theo từng file tháng** để không vượt bộ nhớ. Các thống kê như trung vị được tính trên mẫu ngẫu nhiên 100.000 dòng/tháng.
- **Profiling là một vòng lặp.** Lần chạy đầu phát hiện lỗi ở bước thu thập (thời tiết lệch 5 giờ, xem mục 5.1). Sau khi sửa và tải lại thì chạy profiling lần hai. Cũng từ lần chạy đầu mà phát sinh nhu cầu đo thêm độ phủ theo ngày và bảng đối chiếu `status`.

## 3. Thực hiện

```bash
# Windows: double-click chay_buoc_06_profiling.bat
# hoặc:
pip install -r requirements-integration.txt
python -m data_integration.profiling.run                  # cả 3 nguồn
python -m data_integration.profiling.run --source speeds  # 1 nguồn
```

| File | Vai trò |
|---|---|
| `data_integration/profiling/core.py` | Profiling chung cho từng cột, quy tắc IQR, xuất bảng Markdown |
| `data_integration/profiling/sources.py` | Kiểm tra theo nghiệp vụ của thời tiết, lưu lượng, tốc độ |
| `data_integration/profiling/run.py` | Chạy và ghi báo cáo `.md` + `.json` |
| `tests/test_profiling.py` | 4 test với dữ liệu cài sẵn lỗi đã biết số lượng |

**Thời gian chạy thực tế:** thời tiết 0,4 giây · lưu lượng 1,4 giây · tốc độ 32,8 giây cho 12 triệu dòng.

Khi viết test, test đã bắt được một lỗi logic của chính bước profiling. Lúc đếm "khung 15 phút bị thiếu", các dòng trùng và các dòng có phút lệch được đếm vào, làm che mất các khung thiếu thật. Sau đó code được sửa để chỉ đếm các mốc **duy nhất** và **đúng lưới 15 phút**.

## 4. Kết quả chính

### 4.1. Nguồn thời tiết (Open-Meteo): **chất lượng rất tốt**

| Kiểm tra | Kết quả |
|---|---|
| Số giờ mỗi trạm | 8.784 / 8.784, đủ cả 5 trạm |
| Giá trị rỗng, âm, ngoài miền | 0 |
| Giờ địa phương bị trùng | 10 dòng = 5 trạm × 2, tất cả là **01:00 ngày 03/11/2024** (ngày lùi giờ mùa đông) |
| Giờ địa phương bị thiếu | 5 = 5 trạm × 1, là **02:00 ngày 10/03/2024** (ngày chuyển sang giờ mùa hè, giờ này không tồn tại) |

Phân bố thời tiết sau khi đổi mã WMO: Clear 44,9% · Cloudy 40,4% · Drizzle 10,6% · Rain 2,8% · Snow 1,2%. **Không có giờ nào là Thunderstorm.** Mã WMO lớn nhất xuất hiện là 75, vì dữ liệu lưu trữ của Open-Meteo không sinh mã giông (95–99). Bước 16 cần biết điều này.

Khí hậu 2024 hợp lý với New York: tháng 1 trung bình 1,5 °C, tháng 7 trung bình 25,2 °C. Tuyết rơi tháng 1, 2 và 12. Tháng 3 mưa nhiều nhất (220 mm).

### 4.2. Nguồn lưu lượng (Volume Counts): **sạch nhưng thưa**

| Kiểm tra | Kết quả | Ý nghĩa |
|---|---|---|
| Thời gian, phút, giờ không hợp lệ | 0 | Định dạng 5 cột rời nhưng sạch |
| `vol` rỗng hoặc âm | 0 | |
| `vol = 0` | 1.292 (1,36%) | Có thể hợp lệ (đêm khuya, đường cụt) |
| `vol` ngoại lai mạnh | 2.390 (2,51%) | Ngưỡng khoảng 394 xe/15 phút. Phần lớn là đại lộ lớn, **không loại bỏ máy móc** |
| Trùng khóa (đoạn, hướng, thời điểm) | 379, **tất cả đều khác giá trị** | 2 đợt khảo sát đo cùng chỗ cùng lúc → phải chọn hoặc gộp |
| Tọa độ sau khi đổi EPSG:2263 → WGS84 | 100% nằm trong New York | Phép đổi hệ tọa độ đúng |
| Khung 15 phút bị thiếu trong các đợt đếm | 980 (1,02%) | |
| Chữ hoa/thường không thống nhất | `fromst`, `tost`: `Dead End` / `Dead end` | Cần chuẩn hóa chữ hoa |
| Đoạn có nhiều hơn 1 tọa độ | 1 | |

**Độ bao phủ thấp:** chỉ có **38 đợt khảo sát** trên **104 đoạn phố**, mỗi đợt khoảng 7 ngày. **Không có dữ liệu tháng 7 và tháng 8.** Staten Island chỉ có 384 dòng. Đây là đặc thù của dữ liệu đếm xe theo đợt, không phải lỗi.

### 4.3. Nguồn tốc độ (Traffic Speeds): **nhiều vấn đề nhất**

| Kiểm tra | Số bản ghi | Tỉ lệ |
|---|---|---|
| `status = -101` | 2.922.227 | **24,41%** |
| …trong đó speed = 0 và travel_time = 0 | 2.415.175 | 20,18% |
| …trong đó speed khác 0 | 507.052 | 4,24% |
| speed > 100 mph | 87 | 0,001% |
| Thời gian lỗi hoặc ngoài tháng | 0 | |
| Trùng toàn bộ dòng / trùng khóa (link, thời điểm) | 0 / 0 | |
| Tuyến không có trong danh mục `links.csv` | 1 dòng | |

**Bản ghi `status = -101` không đáng tin, kể cả khi speed khác 0.** Kiểm tra thêm trên dữ liệu tháng 6:

| | `status = -101`, speed > 0 | `status = 0`, speed > 0 |
|---|---|---|
| Số bản ghi | 42.532 | 802.278 |
| Tốc độ trung vị | 23,6 mph | 41,6 mph |
| Tốc độ trung bình | 27,4 mph | 37,3 mph |

Phân bố lệch hẳn về phía tốc độ thấp. Ngoài ra có những tuyến **100% bản ghi là `-101`** trong cả tháng, tức cảm biến hỏng.

**Các khoảng ngày nguồn bị mất dữ liệu** (dưới 50% số cặp tuyến × giờ có dữ liệu):

| Từ ngày | Đến ngày | Số ngày | Độ phủ trung bình |
|---|---|---|---|
| 2024-01-29 | 2024-02-12 | 15 | 5,1% |
| 2024-03-12 | 2024-03-12 | 1 | 33,1% |
| 2024-08-25 | 2024-08-25 | 1 | 0,0% |
| 2024-12-24 | 2024-12-28 | 5 | 3,2% |

Khoảng mất dữ liệu đầu tiên giải thích vì sao tháng 2 chỉ có 606.855 dòng, và vì sao danh mục tuyến lấy mẫu ngày 01/02 trả về 0 bản ghi.

**Các chỉ số khác:**

- Tốc độ hợp lệ có trung vị 42,9 mph, p01–p99 là 3,7–63,4 mph.
- Khoảng cách giữa 2 lần đo trung vị **5 phút**.
- Có 125 tuyến. Tuyến ít nhất chỉ có 1 bản ghi, tuyến nhiều nhất có 98.347 bản ghi.
- Ngày lùi giờ 03/11: giờ 01 có 2.035 bản ghi, so với 1.464 ở các giờ khác. Như vậy chỉ thêm khoảng 39%, chứ không gấp đôi. Nguồn này không ghi hết giờ lặp lại.

**Tên tuyến viết tắt và không thống nhất ngay trong cùng một nguồn:**

| Đầy đủ | Viết tắt | Số tuyến |
|---|---|---|
| AVENUE | AVE | 51 / 34 |
| STREET | ST | 21 / 24 |
| PARKWAY | PKWY | — / 11 |
| BOULEVARD | BLVD | — / 10 |

Ngoài ra có nhiều tên cao tốc chỉ ghi dạng viết tắt: `SIE` (Staten Island Expwy), `WSE`, `CBE`, `VWE`, `FDR`, `BE`, `TBB`, `CIP`, `TNB`, `LIE`. Trong khi đó nguồn lưu lượng **luôn viết đầy đủ** (`AVENUE`, `STREET`, `BOULEVARD`).

## 5. Kết luận cho các bước sau

### 5.1. Lỗi ở bước thu thập do profiling phát hiện

Lần chạy đầu có thêm một dòng tháng **"2023-12"** trong bảng khí hậu. Nguyên nhân: thời tiết được lấy theo ngày UTC, trong khi phạm vi nghiên cứu tính theo giờ New York. Đã sửa script tải và tải lại (xem hướng dẫn 05, vấn đề số 8).

### 5.2. Quy tắc làm sạch cho bước 07

| Nguồn | Quy tắc | Căn cứ |
|---|---|---|
| Tốc độ | Giữ bản ghi `status = 0` **và** `speed > 0`. Loại `speed > 100 mph` | Mục 4.3: `-101` có phân bố lệch, có tuyến hỏng 100% |
| Tốc độ | Đánh dấu (không bịa số liệu) 4 khoảng mất dữ liệu | Không nội suy cho khoảng trống dài nhiều ngày |
| Tốc độ | Đổi mph → km/h | Data contract |
| Lưu lượng | Trùng khóa khác giá trị: lấy trung bình của các đợt | 379 cặp mâu thuẫn |
| Lưu lượng | Giữ `vol = 0` và các giá trị ngoại lai, chỉ gắn cờ | Có thể là giá trị thật, việc phát hiện bất thường để dành cho bước 17 |
| Lưu lượng | Đổi tọa độ EPSG:2263 → WGS84, viết hoa toàn bộ tên phố | Mục 4.2 |
| Thời tiết | Gộp 2 dòng 01:00 ngày 03/11 thành 1 (lấy trung bình) | Khóa (trạm, giờ) phải duy nhất |
| Mọi nguồn | Chuẩn hóa tên quận về 5 giá trị chuẩn của contract | Hiện đã khớp, nhưng vẫn cần ràng buộc |

### 5.3. Lưu ý cho record linkage (bước 09)

- Cần một **bảng chuẩn hóa từ viết tắt**: `AVE → AVENUE`, `ST → STREET`, `PKWY → PARKWAY`, `BLVD → BOULEVARD`, `EXPWY → EXPRESSWAY`, cùng tên đầy đủ của các cao tốc (`LIE → LONG ISLAND EXPRESSWAY`...).
- Nguồn tốc độ chủ yếu đo **cao tốc và cầu** (mỗi 5 phút, 125 tuyến), còn nguồn lưu lượng đo **phố nội đô** (theo đợt, 104 đoạn). Vì vậy **số cặp nối được giữa hai nguồn dự kiến không nhiều**. Bước 09 phải đo và báo cáo trung thực tỉ lệ này.
- Nên **blocking theo quận**: cả hai nguồn đều có quận, và đây là cách cắt giảm số cặp phải so sánh rõ ràng nhất.

## 6. Kiểm tra

- [x] `python -m pytest -q` → 15 passed
- [x] Có `docs/bao-cao/06_profiling.md` và `.json`
- [x] Bảng khí hậu theo tháng chỉ có 2024-01 → 2024-12 (không còn "2023-12")
