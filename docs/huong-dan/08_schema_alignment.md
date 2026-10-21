# 08. Schema alignment

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/08_alignment.md` · Đầu ra: `data/interim/aligned/` (2,4 MB)

## 1. Mục tiêu

Đưa 3 nguồn có **lược đồ khác nhau** về **lược đồ trung gian** (`integrated_traffic`, bước 03):

1. Xác định cột nào của nguồn tương ứng với cột nào của lược đồ trung gian (**schema matching**).
2. Định nghĩa cách tính mỗi cột trung gian từ nguồn (**schema mapping**, theo hướng **GAV**).
3. Giải quyết **không đồng nhất về dữ liệu**: đơn vị, mức chi tiết thời gian, cách viết tên đường.

## 2. Giải trình và liên hệ lý thuyết

### 2.1. Hai loại không đồng nhất (theo bài giảng)

| Loại | Ví dụ trong project | Xử lý |
|---|---|---|
| **Schema heterogeneity**: khác tên và cấu trúc cột | `borough` / `boro` / `district`; `data_as_of` so với 5 cột `yr, m, d, hh, mm`; `speed` / `vol` | Ánh xạ GAV (mục 2.3) |
| **Data heterogeneity**: cùng ý nghĩa nhưng khác cách biểu diễn | mph và km/h; khung 5 phút, 15 phút và 1 giờ; `BQE` và `BROOKLYN QUEENS EXPWY`; `84TH ST` và `160 STREET`; `F D R DRIVE` và `FDR` | Đổi đơn vị, gộp theo giờ, chuẩn hóa tên |

### 2.2. Thử nghiệm schema matching tự động

Trước khi viết ánh xạ bằng tay, project thử xem máy **tự tìm** được bao nhiêu tương ứng. Cài đặt nằm ở `data_integration/alignment/schema_matching.py`.

- **Name matcher:** điểm = max(Jaccard trên token của tên, độ tương đồng edit distance). Đây là đúng các công thức trong bài giảng và bài tập 1. Test kiểm tra `levenshtein("hnoi", "hanoi") = 1` và `s = 0,8`.
- **Name + synonym matcher:** bổ sung một từ điển đồng nghĩa của miền, ví dụ `boro → district`, `vol → vehicle count`, `rain → rainfall`.
- Kết quả được so với **ánh xạ chuẩn** gồm 23 tương ứng do người xác định.

| Matcher | Ngưỡng | Dự đoán | Đúng | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Chỉ tên | 0,4 | 14 | 10 | 0,714 | 0,435 | 0,541 |
| Chỉ tên | 0,5 | 12 | 8 | 0,667 | **0,348** | 0,457 |
| Chỉ tên | 0,7 | 3 | 3 | 1,000 | 0,130 | 0,231 |
| Tên + đồng nghĩa | 0,5 | 27 | 23 | 0,852 | 1,000 | 0,920 |
| Tên + đồng nghĩa | 0,6 | 26 | 23 | 0,885 | 1,000 | 0,939 |

**Nhận xét:**

1. **Chỉ dựa vào tên thì tìm được chưa tới 1/3 số tương ứng** (recall 0,35 ở ngưỡng 0,5), và vẫn ghép sai, ví dụ `volume.street → district` (edit similarity 0,5) hay `speeds.id → road_id`. Tăng ngưỡng làm precision tăng nhưng recall giảm mạnh, đúng sự đánh đổi kinh điển.
2. **Từ điển đồng nghĩa nâng F1 lên 0,92, nhưng kết quả này lạc quan quá mức.** Từ điển do chính người biết đáp án soạn ra, nên thực chất là đưa tri thức con người vào hệ thống. Dù vậy vẫn còn lỗi: `travel_time → timestamp` (do token "time"), và tọa độ lưới của trạm thời tiết bị ghép vào tọa độ đường.
3. **Matcher chỉ tìm được tương ứng 1:1, không tìm được phép biến đổi.** Nó không hiểu rằng 5 cột `yr, m, d, hh, mm` phải **ghép bằng một hàm** để ra `timestamp`, hay `speed` phải **nhân 1,609344** và **lấy trung bình theo giờ**.

**Kết luận:** schema matching tự động hữu ích để *gợi ý*, nhưng ánh xạ cuối cùng phải do người định nghĩa. Project dùng **ánh xạ GAV viết tay** (mục 2.3).

### 2.3. Ánh xạ GAV

Theo hướng **Global-as-View**, mỗi cột của lược đồ trung gian được định nghĩa là một biểu thức (view) trên các nguồn. Bảng này nằm trong code (`alignment/mapping.py`) và được in ra báo cáo, nên tài liệu luôn khớp với code.

| Cột trung gian | Speeds | Volume | Weather |
|---|---|---|---|
| `road_id` | `concat('L', link_id)` | `concat('S', segmentid)` nếu không nối được với link | — |
| `road_name` | `normalize(main_road(link_name))` | `normalize(street)` | — |
| `district` | `normalize_district(borough)` | `normalize_district(boro)` | district của trạm |
| `latitude/longitude` | `mean(link_points)` | `EPSG:2263→4326(wktgeom)` | — |
| `timestamp` | `date_trunc('hour', data_as_of)` | `make_timestamp(yr, m, d, hh)` | `time_local` |
| `avg_speed` | `AVG(speed)·1.609344` theo (link, giờ), chỉ `status = 0` | — | — |
| `vehicle_count` | — | `SUM(vol)` theo (đoạn, giờ), mọi hướng, chỉ giờ đủ 4 khung | — |
| `temperature`, `rainfall`, `snowfall` | — | — | `temperature_2m`, `rain`, `snowfall` |
| `weather_condition` | — | — | `wmo_to_condition(weather_code)` |

Dạng Datalog:

```
T_speed(link, h, avg(kmh))  :- Speeds(link, t, mph, status), status = 0,
                               h = hour(t), kmh = mph * 1.609344
T_volume(seg, h, sum(vol))  :- Volume(seg, dir, yr, m, d, hh, mm, vol),
                               h = make_ts(yr, m, d, hh), complete(seg, h)
W(district, h, temp, rain)  :- Weather(station, t_local, temp, rain, ...), h = t_local
Integrated(road, h, ...)    :- RoadLink(road, link/seg), T_speed / T_volume, W(district(road), h, ...)
```

Vì sao chọn **GAV** chứ không phải LAV:

- Truy vấn trên lược đồ trung gian được trả lời bằng **unfolding** đơn giản. Ở đây unfolding được thực hiện trước (materialize) thành bảng `integrated_traffic`.
- Số nguồn ít (3) và ổn định, nên nhược điểm của GAV (phải sửa ánh xạ khi thêm nguồn) không đáng kể.
- Đây cũng là cách tiếp cận của **data warehouse**: tích hợp vật lý một lần, rồi phân tích nhiều lần bằng Spark.

### 2.4. Các quyết định về mức chi tiết (grain)

| Quyết định | Lý do |
|---|---|
| Tốc độ: lấy **trung bình** các lần đo trong giờ | Tốc độ là đại lượng *trạng thái*, nên trung bình là phép gộp đúng |
| Lưu lượng: lấy **tổng** 4 khung 15' và mọi hướng | Số xe là đại lượng *tích lũy*, nên phải cộng. Tổng mọi hướng vì nguồn tốc độ không cho biết lưu lượng theo hướng |
| Lưu lượng: **chỉ giữ giờ đầy đủ** (đủ 4 khung × mọi hướng) | Cộng giờ thiếu khung sẽ làm lưu lượng **bị thấp đi một cách giả tạo**. Ví dụ thiếu 1 khung thì mất khoảng 25% số xe, và bước 17 sẽ báo nhầm là bất thường |
| Giữ cột `n_readings` (số lần đo tốc độ trong giờ) | Để bước sau biết giờ nào ít dữ liệu, ví dụ chỉ có 1 lần đo |

### 2.5. Chuẩn hóa tên đường

Code nằm ở `alignment/names.py`. Các phép chuẩn hóa:

- **Mở rộng 25 tên viết tắt cao tốc, cầu, hầm** của New York: `BQE → BROOKLYN QUEENS EXPRESSWAY`, `LIE`, `CBE`, `VWE`, `SIE`, `FDR`, `TBB`, `GWB`...
- **Mở rộng hậu tố:** `AVE/AV → AVENUE`, `ST → STREET`, `BLVD → BOULEVARD`, `PKWY → PARKWAY`, `EXPWY → EXPRESSWAY`, `PT → POINT`, `BR → BRIDGE`...
- **Xử lý trường hợp nhập nhằng:** `ST` đứng đầu tên và theo sau là chữ thì là `SAINT` (`ST JAMES PLACE → SAINT JAMES PLACE`), ngược lại là `STREET`.
- **Bỏ hậu tố số thứ tự:** `84TH → 84`, vì nguồn lưu lượng viết `160 STREET`.
- **Ghép chữ cái rời:** `F D R DRIVE → FDR DRIVE`. Có thêm bước bỏ từ lặp, vì `FDR` mở rộng thành `FDR DRIVE` nên sẽ thành `FDR DRIVE DRIVE`. Lỗi này được phát hiện khi chạy thử.
- **Bỏ chú thích trong ngoặc:** `(U/LVL)`, `(EXIT 13 NORTHERN BLVD)`.
- **Tách tên tuyến** thành *đường chính*, *hướng*, *điểm đầu/cuối*: `BQE N LEONARD STREET - 46TH STREET → (BROOKLYN QUEENS EXPRESSWAY, N, [LEONARD STREET; 46 STREET])`.

**Không sửa lỗi chính tả** có sẵn trong dữ liệu gốc (`BLLOMINGDALE`, `BLOOMUINGDALE`, `WLAKER`, `ROACKAWAY`, `ALTANTIC`, `LAFAYATTE`). Đó là việc của **so khớp xấp xỉ bằng edit distance** ở bước 09. Nếu sửa tay từng lỗi thì không thể làm được khi dữ liệu lớn.

## 3. Thực hiện

```bash
# Windows: double-click chay_buoc_08_alignment.bat
python -m data_integration.alignment.run
```

| File | Vai trò |
|---|---|
| `common/textsim.py` | Levenshtein (tự cài bằng quy hoạch động), edit similarity, Jaccard, tách token |
| `data_integration/alignment/schema_matching.py` | 2 matcher, ánh xạ chuẩn, đo precision/recall/F1 |
| `data_integration/alignment/mapping.py` | Bảng ánh xạ GAV |
| `data_integration/alignment/names.py` | Từ điển viết tắt, chuẩn hóa tên, tách tên tuyến |
| `data_integration/alignment/aggregate.py` | Gộp theo giờ, kiểm tra giờ đầy đủ, dựng bảng đường của 2 nguồn |
| `tests/test_alignment.py` | 7 test |

## 4. Kết quả (chạy thực tế)

| Nguồn | Vào | Ra (đường × giờ) |
|---|---|---|
| Tốc độ | 9.048.108 bản ghi (~5 phút/lần) | **789.403** (link, giờ) |
| Lưu lượng | 94.824 khung 15' | **16.530** (đoạn, giờ) đầy đủ. Loại 164 giờ thiếu khung hoặc thiếu hướng |
| Thời tiết | 43.915 | 43.915 (trạm, giờ) |

Tổng thời gian khoảng 4 giây. Đầu ra chỉ còn 2,4 MB Parquet.

**Kiểm tra hợp lý:**

- Số lần đo tốc độ mỗi giờ có trung vị **12**, đúng với tần suất 5 phút/lần. Giá trị lớn nhất là 24, rơi vào giờ 01:00 ngày lùi giờ 03/11 (giờ này xuất hiện hai lần).
- Tốc độ trung bình theo giờ có trung vị 67 km/h, tối đa 157 km/h.
- Lưu lượng theo giờ có trung vị 300 xe/giờ, tối đa 7.266 xe/giờ trên đại lộ lớn hai chiều.

**Chuẩn hóa tên đường:**

- Nguồn tốc độ: 125 tuyến, gom về **37 đường chính**. Có 103 tuyến có tên viết tắt được mở rộng. Đường có nhiều tuyến nhất là STATEN ISLAND EXPRESSWAY (12 tuyến), WEST SHORE EXPRESSWAY (9), BROOKLYN QUEENS EXPRESSWAY (7)...
- Nguồn lưu lượng: 104 đoạn với 85 tên phố, trong đó 8 đoạn có tên bị chuẩn hóa: `F D R DRIVE`, `UNION ST BRIDGE`, `ST JAMES PLACE`, `WILLIAMSBURG BR APPROACH`, `BROOKLYN QUEENS EXPWY ET 34 WB`, `EAST 174 ST BRIDGE`, `CITY IS BRIDGE`.

Chỉ sau khi chuẩn hóa mới thấy hai nguồn **có chung tên đường**: `FDR DRIVE` xuất hiện y hệt ở cả hai bên, còn `BROOKLYN QUEENS EXPRESSWAY` khớp với `BROOKLYN QUEENS EXPRESSWAY ET 34 WB` bên lưu lượng. Bước 09 sẽ tìm toàn bộ các cặp như vậy.

## 5. Kiểm tra

- [x] `python -m pytest -q` → 29 passed (pandas 3.0 và 2.3)
- [x] Báo cáo `docs/bao-cao/08_alignment.md` hiển thị đúng các bảng

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| `F D R DRIVE` thành `FDR DRIVE DRIVE` | Thêm bước bỏ từ lặp liền nhau sau khi mở rộng viết tắt, có test |
| Ký tự `\|` trong tên tuyến và trong biểu thức `'L' \|\| link_id` làm vỡ bảng Markdown | Đổi dấu ngăn cách điểm đầu/cuối thành `;`, viết biểu thức dạng `concat()` |
| Từ điển đồng nghĩa có thể làm kết quả thử nghiệm đẹp quá mức | Ghi rõ hạn chế này trong phần nhận xét, không trình bày F1 = 0,92 như năng lực thật của phương pháp |
