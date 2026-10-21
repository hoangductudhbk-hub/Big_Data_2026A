# 09. Record linkage + blocking

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/09_linkage.md` · Đầu ra: `data/processed/roads.parquet`, `data/interim/linkage/`

## 1. Mục tiêu

Xác định các bản ghi ở những nguồn khác nhau **cùng chỉ một thực thể ngoài đời thực**. Bước này giải 2 bài toán:

- **A. Biến thể tên đường:** các chuỗi khác nhau nhưng là cùng một con phố, ví dụ `BLOOMINGDALE ROAD`, `BLLOMINGDALE ROAD`, `BLOOMUINGDALE ROAD`.
- **B. Nối đoạn đếm lưu lượng với tuyến đo tốc độ:** điểm đếm xe nào nằm trên đúng tuyến đo tốc độ nào. Đây là điều kiện để một dòng của `integrated_traffic` có **cả** `vehicle_count` lẫn `avg_speed`.

Đầu ra là **bảng đường thống nhất** (`roads.parquet`), định nghĩa `road_id` dùng cho bước 10.

## 2. Giải trình

### 2.1. Ba thành phần của record linkage

| Thành phần | Trong project |
|---|---|
| **Độ đo tương đồng** | Levenshtein; **OSA (Damerau–Levenshtein)** có thêm phép hoán vị 2 ký tự kề nhau; khoảng cách địa lý tới đường gấp khúc |
| **Luật quyết định** | Ngưỡng + ràng buộc nghiệp vụ (cùng số, cùng hướng, cùng tầng) |
| **Blocking** | Chỉ so các cặp cùng khối (cùng chữ cái đầu, cùng quận) để giảm số phép so sánh |

### 2.2. Phát hiện chính: luật trong plan có precision chỉ 1,5%

Plan đề xuất luật "Levenshtein similarity ≥ 0,8 thì là cùng một đường". Thử trên 373 tên đường của cả hai nguồn (69.378 cặp):

| Luật | Số cặp ghép | Đúng | Precision | Recall |
|---|---|---|---|---|
| **A**: Levenshtein ≥ 0,8 (luật của plan) | 336 | 5 | **0,015** | 1,0 |
| **B**: A + cùng các con số + cùng từ chỉ hướng/tầng/bang | 13 | 5 | 0,385 | 1,0 |
| **C**: B, nhưng dùng **OSA** trên chuỗi đã bỏ khoảng trắng, ngưỡng 0,88 | 6 | 5 | **0,833** | 1,0 |

**Vì sao luật A sai nhiều?** Trong tên đường, **một ký tự có thể mang toàn bộ ý nghĩa**:

- `40 STREET` và `90 STREET`: khác 1 ký tự (similarity 0,89) nhưng cách nhau 50 dãy phố.
- `EAST 117 STREET` và `WEST 117 STREET`: hai phố khác nhau ở Manhattan.
- `... UPPER LEVEL` và `... LOWER LEVEL`: hai tầng khác nhau của cầu George Washington.

Edit distance coi mọi ký tự có trọng số như nhau, nên cần thêm **ràng buộc nghiệp vụ** (luật B).

**Vì sao cần OSA (luật C)?** Lỗi gõ phổ biến nhất là đảo 2 ký tự kề nhau, ví dụ `WALKER` thành `WLAKER`. Levenshtein tính lỗi này là 2 phép biến đổi (similarity 0,85, ngang với hai tên thật sự khác nhau như `CATON`/`WATSON`). OSA tính là 1 phép (similarity 0,92). Nhờ đó ngưỡng 0,88 tách được lỗi gõ khỏi tên khác. Bỏ khoảng trắng giúp bắt được `DE KALB` / `DEKALB`.

**Cặp sai còn lại của luật C:** `CROSS BRONX EXPRESSWAY WL LE V AMSTERDAM` / `... WU LEV ...`. Đây là tầng dưới và tầng trên viết tắt kiểu `L/LE V` và `U/LEV`, bị bước chuẩn hóa tên ghép lẫn với chữ `W` (hướng Tây). Đây là hạn chế đã biết; có thể sửa bằng cách thêm luật cho các ký hiệu tầng.

### 2.3. Blocking: đánh đổi giữa tốc độ và độ đầy đủ

| Khóa blocking | Số cặp so sánh | Reduction ratio | Pair completeness | Thời gian | Bỏ lỡ |
|---|---|---|---|---|---|
| Không blocking | 69.378 | 0 | 1,000 | 1.859 ms | |
| Chữ cái đầu | 3.258 | **0,953** | **1,000** | 110 ms | |
| 2 chữ cái đầu | 985 | 0,986 | 0,833 | 33 ms | `WALKER ~ WLAKER` |
| Chữ cái đầu + các con số | 2.054 | 0,970 | 1,000 | 104 ms | |

- **Reduction ratio (RR)** = 1 − (số cặp phải so) / (tổng số cặp): tỉ lệ công việc tiết kiệm được.
- **Pair completeness (PC)** = số cặp đúng còn tìm được / số cặp đúng khi không blocking: tỉ lệ không bị bỏ lỡ.
- Khóa "2 chữ cái đầu" giảm thêm số phép so sánh nhưng **bỏ lỡ đúng lỗi gõ ở ký tự thứ 2** (`WA` ≠ `WL`). Đây là minh họa rõ nhất cho rủi ro của blocking: **khóa blocking phải ổn định trước đúng loại lỗi cần bắt**.
- Lựa chọn: **chữ cái đầu**. Giảm 95% số phép so sánh mà không bỏ lỡ cặp nào. Với dữ liệu lớn hơn nhiều, nên dùng "chữ cái đầu + các con số" (RR 0,97).

### 2.4. Nối đoạn đếm với tuyến tốc độ

Một cặp (đoạn đếm, tuyến) là **cùng một đoạn đường** khi thỏa cả hai điều kiện:

1. **Tên đường chính giống nhau:** `max(edit similarity, tên ngắn là phần đầu của tên dài) ≥ 0,8`.
   - Dùng "phần đầu" để `BROOKLYN QUEENS EXPRESSWAY` khớp với `BROOKLYN QUEENS EXPRESSWAY ET 34 WB`.
   - **Không** dùng "chứa đủ từ", vì `BROOKLYN BRIDGE MANHATTAN SIDE` chứa đủ các từ của `MANHATTAN BRIDGE` và hai điểm này **chỉ cách nhau 486 m**, nhưng chúng là **hai cây cầu khác nhau**.
2. **Điểm đếm nằm cách đường gấp khúc của tuyến không quá 300 m.**
   - Lần thử đầu chỉ đo tới điểm đầu, điểm cuối và tâm tuyến, nên một điểm nằm giữa tuyến BQE dài vài km bị tính là "cách 5,5 km".
   - Sau khi đo tới **từng đoạn thẳng của đường gấp khúc**, khoảng cách thực là **11,6 m**.

**Tuyến chiều ngược lại (twin):** nguồn tốc độ tách mỗi chiều thành một tuyến riêng. Do chuỗi tọa độ bị cắt ở 255 ký tự (bước 07), đường gấp khúc của tuyến ngược chiều có thể không phủ tới điểm đếm. Vì vậy tuyến ngược chiều được nối theo luật: **cùng đường chính và điểm đầu/cuối đảo nhau**. Trước khi so, bỏ các từ chung chung, vì nguồn ghi `63RD - 25TH ST` ở chiều này và `25TH - 63RD ST` ở chiều kia.

**Blocking theo quận:** giảm từ 13.000 xuống 2.444 cặp (**RR 0,81**), PC = 1,0, thời gian giảm từ 1,12 giây xuống 0,27 giây.

### 2.5. Nhãn kiểm tra

Để tính precision/recall cần đáp án (`data_integration/linkage/labels.py`):

- **Tên đường:** liệt kê mọi cặp có similarity ≥ 0,70, đọc từng cặp và gán nhãn theo tiêu chí ghi trong file (chỉ khác lỗi chính tả hoặc khoảng trắng thì là cùng; khác số, hướng, tầng, bang thì là khác). Kết quả: 5 cặp đúng. Đã rà thêm khoảng 0,70–0,80 để chắc không bỏ sót.
- **Nối đường:** 2 cặp, kiểm tra bằng tên và khoảng cách trên bản đồ.

> Nhãn được gán một lượt theo tiêu chí trên; chưa có kiểm tra chéo độc lập (xem mục Hạn chế ở bước 22).

## 3. Thực hiện

```bash
# Windows: double-click chay_buoc_09_linkage.bat
python -m data_integration.linkage.run
```

| File | Vai trò |
|---|---|
| `common/textsim.py` | Thêm `osa_distance` / `osa_similarity` |
| `data_integration/linkage/geo.py` | Chiếu phẳng, khoảng cách điểm tới đường gấp khúc |
| `data_integration/linkage/name_variants.py` | 3 luật, 4 khóa blocking, gom cụm bằng union-find |
| `data_integration/linkage/road_linkage.py` | Nối đoạn với tuyến, nối tuyến ngược chiều, bảng đường thống nhất |
| `data_integration/linkage/labels.py` | Nhãn kiểm tra và tiêu chí gán nhãn |
| `tests/test_linkage.py` | 7 test |

## 4. Kết quả (chạy thực tế)

**Cụm biến thể tên đường tìm được:**

| Tên | Biến thể |
|---|---|
| BLOOMINGDALE ROAD | `BLLOMINGDALE` / `BLOOMINGDALE` / `BLOOMUINGDALE` |
| WALKER STREET | `WALKER` / `WLAKER` |
| DEKALB AVENUE | `DE KALB` / `DEKALB` |
| *(sai)* CROSS BRONX EXPWY … AMSTERDAM | tầng trên / tầng dưới |

**Các cặp đoạn đếm ↔ tuyến tốc độ:**

| Đoạn đếm | Tuyến tốc độ | Khoảng cách | Luật |
|---|---|---|---|
| 66035 `BROOKLYN QUEENS EXPWY ET 34 WB` | 4616232 `BQE S 46TH STREET - LEONARD STREET` | 11,6 m | trực tiếp |
| 66035 | 4616235 `BQE N LEONARD STREET - 46TH STREET` | | chiều ngược lại |
| 136811 `F D R DRIVE` | 4616332 `FDR S 63RD - 25TH ST` | 4,7 m | trực tiếp |
| 136811 | 4616329 `FDR N 25TH - 63RD ST` | | chiều ngược lại |

Precision = recall = **1,0** so với nhãn.

**Bảng đường thống nhất** (`data/processed/roads.parquet`): **227 đường**.

- 123 đường chỉ có tốc độ, 102 đường chỉ có lưu lượng, **2 đường có cả hai**.
- Theo quận: Queens 63, Brooklyn 52, Manhattan 49, Bronx 36, Staten Island 27.
- `road_id`: `L<link_id>` cho tuyến tốc độ. Đoạn đếm đã nối được dùng chung `road_id` với tuyến nối trực tiếp. Đoạn chưa nối được có `road_id` riêng là `S<segmentid>`.

**Giá trị của việc nối:** trên 2 đường này có **153 giờ có cả lưu lượng lẫn tốc độ**:

- BQE: 96 giờ (16–19/03/2024), **tương quan lưu lượng–tốc độ = −0,67**. Càng đông xe càng chậm, đúng với lý thuyết giao thông.
- FDR: 57 giờ (08–10/10/2024), tương quan −0,10.

Đây là loại phân tích **chỉ làm được sau khi tích hợp**, vì không nguồn nào một mình có đủ cả lưu lượng lẫn tốc độ.

## 5. Đánh giá trung thực

- **Hai nguồn giao thông giao nhau rất ít: 2/104 đoạn đếm.** Đây không phải lỗi của thuật toán. Nguồn tốc độ chủ yếu đo **cao tốc và cầu hầm** (37 đường chính), còn nguồn lưu lượng đo **phố nội đô** theo từng đợt khảo sát. Kết quả được báo cáo như hiện trạng của dữ liệu, không cố "ghép cho nhiều".
- Hệ quả cho bước 10: phần lớn dòng của `integrated_traffic` chỉ có một chỉ số giao thông (`source = speeds` hoặc `volume`). **Mọi dòng đều được ghép thời tiết**, vì thời tiết phủ toàn bộ 5 quận và mọi giờ.
- `vehicle_count` của đoạn đếm là **tổng hai chiều**, nhưng được gán vào `road_id` của tuyến tốc độ **một chiều** (tuyến nối trực tiếp). Khi phân tích quan hệ lưu lượng–tốc độ cần lưu ý điểm này.

## 6. Kiểm tra

- [x] `python -m pytest -q` → 36 passed
- [x] `roads.parquet` có 227 đường, `road_id` không trùng

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Luật Levenshtein ≥ 0,8 của plan cho 331/336 cặp sai | Thêm ràng buộc số/hướng/tầng, đổi sang OSA, đo bằng precision/recall |
| "Chứa đủ từ" ghép nhầm Brooklyn Bridge với Manhattan Bridge | Đổi sang "tên ngắn là phần đầu của tên dài" |
| Khoảng cách tới tâm tuyến sai lệch tới hàng km | Đo tới từng đoạn của đường gấp khúc |
| Tuyến FDR ngược chiều không được nối (`63 / 25 STREET` so với `25 / 63 STREET`) | Bỏ từ chung chung trước khi so điểm đầu/cuối |
