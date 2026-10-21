# 14. Scalability benchmark

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/14_scalability.md` · Số liệu thô: `docs/bao-cao/14_results_{A,B,C}.json`

## 1. Mục tiêu

Theo plan (mục 10.3): chạy **cùng một processing job** trên dữ liệu có kích thước khác nhau, đo **kích thước dữ liệu, số bản ghi, thời gian chạy, bộ nhớ** để trả lời câu hỏi: *khi dữ liệu tăng thì thời gian và bộ nhớ tăng thế nào?*

## 2. Giải trình thiết kế

### 2.1. Job chuẩn

Ở mọi kích thước, job đều giống nhau: tính **count, mean, min, max** tốc độ theo nhóm *(tuyến × giờ trong ngày × ngày thường/cuối tuần)*. Đây đúng là dạng thống kê bước 15 sẽ dùng, nên benchmark đo một việc có thật trong hệ thống, không phải một phép tính giả.

### 2.2. Hai loạt dữ liệu

| Loạt | Dữ liệu | Kích thước | Vì sao |
|---|---|---|---|
| **A** | CSV gốc tải về ở bước 05: 1 / 3 / 6 / 12 tháng | 99 MB → 1,2 GB | Dữ liệu **thật**, chưa xử lý. Đúng thang "100 MB – 1 GB" plan gợi ý |
| **B** | Parquet đã làm sạch (bước 07), **nhân bản** ×1 / ×2 / ×4 / ×8 / ×16 | 9 triệu → **145 triệu** bản ghi | Dữ liệu thật chỉ có 9 triệu bản ghi/năm. Muốn biết hệ thống chịu được gấp 16 lần hay không thì phải tạo thêm dữ liệu |

**Cách nhân bản cho trung thực:**

- Mỗi bản sao đổi `link_id` thành `link_id × 100 + i`, nên số nhóm cũng tăng ×16 (5.248 → 83.968 nhóm), giống như thành phố có thêm tuyến đường mới. Nếu giữ nguyên `link_id` thì số nhóm không đổi, và bài toán dễ hơn thực tế.
- Các bản sao được **ghi thật ra đĩa** (393 MB, partition theo `rep`), không `union` trong bộ nhớ, để Spark phải đọc đúng khối lượng đó. Mỗi kích thước đọc `rep < k`, tận dụng partition pruning của bước 12.

### 2.3. Cách đo

- Mỗi kích thước chạy **3 lần**, mỗi lần **dựng DataFrame mới** (bài học ở hướng dẫn 11, mục 6). Báo cáo cả lần đầu (`first_s`) và lần nhanh nhất (`best_s`).
- **Bộ nhớ, dữ liệu đọc vào, dữ liệu shuffle** lấy từ **REST API của Spark UI** (`/api/v1/applications/.../stages`) theo job group của từng lần chạy, không ước lượng.
- **Số nhân:** chạy lại hai trường hợp lớn với `local[1]` để tính **speed-up** và **hiệu suất song song** = speed-up / số nhân.
- **Hồi quy tuyến tính** `thời gian = a + b × số triệu dòng` để kiểm tra thời gian có tăng tuyến tính hay không (R² gần 1 nghĩa là tuyến tính).

## 3. Thực hiện

```bash
python -m spark_jobs.s14_scalability --quick     # thử nhanh khoảng 1 phút: CSV 1–3 tháng, Parquet ×1–×4
python -m spark_jobs.s14_scalability             # chạy đủ khoảng 6–7 phút
```

Có thể chạy từng phần: `--part prepare | A | B | C | report`. Kết quả trung gian lưu ở `BENCH_DIR/results_*.json`, nên phần nào lỗi thì chỉ chạy lại phần đó. Lần chạy thực tế được chia như sau vì môi trường chạy thử giới hạn mỗi lệnh 3 phút:

| Phần | Việc | Thời gian thực tế |
|---|---|---|
| `prepare` | Ghi 16 bản sao Parquet (145 triệu dòng, 393 MB) | 1 phút 39 giây (chỉ chạy một lần) |
| `A` | CSV 1/3/6/12 tháng × 3 lần | 1 phút 34 giây |
| `B` | Parquet ×1…×16 × 3 lần | 1 phút 27 giây |
| `C` | `local[1]` × 2 trường hợp × 2 lần | 1 phút 13 giây |
| `report` | Gộp kết quả, hồi quy, ghi báo cáo | vài giây |

**Biến môi trường dùng khi chạy thực tế:**

```bash
export RAW_SPEEDS_PATH=~/bench/raw   # bản sao CSV trên ổ đĩa của máy ảo
export BENCH_DIR=~/bench             # nơi ghi dữ liệu nhân bản (không ghi vào thư mục project)
```

Vì sao copy CSV sang ổ của máy ảo? Thư mục project nằm trên ổ D: của Windows, được máy ảo đọc qua một lớp chia sẻ file (FUSE). Lớp này thêm độ trễ không liên quan tới Spark, làm số đo bị nhiễu. Trên WSL2 hoặc Linux thật thì không cần, cứ để mặc định `data/raw/speeds` và `data/bench`.

## 4. Kết quả

Môi trường: Spark 3.5.3, `local[2]` (2 nhân), heap driver 2 GB, máy ảo Linux 3,9 GB RAM.

### 4.1. Loạt A: CSV gốc

| Dữ liệu | Kích thước | Bản ghi | Tốt nhất | Triệu dòng/s | Bộ nhớ đỉnh mỗi task |
|---|---|---|---|---|---|
| 1 tháng | 99 MB | 817.609 | 1,29 s | 0,63 | 33,8 MB |
| 3 tháng | 264 MB | 2.153.618 | 3,59 s | 0,60 | 33,8 MB |
| 6 tháng | 579 MB | 4.664.643 | 6,55 s | 0,71 | 33,8 MB |
| 12 tháng | **1.185 MB** | **9.555.071** | **13,22 s** | 0,72 | **33,8 MB** |

(9.555.071 dòng là số dòng CSV có tốc độ > 0. Bước 07 còn loại thêm trùng lặp và giá trị bất thường, nên còn 9.048.108.)

### 4.2. Loạt B: Parquet nhân bản

| Dữ liệu | Kích thước | Bản ghi | Số nhóm | Tốt nhất | Triệu dòng/s | Bộ nhớ đỉnh mỗi task |
|---|---|---|---|---|---|---|
| ×1 | 23 MB | 9.048.108 | 5.248 | 1,43 s | 6,3 | 33,8 MB |
| ×2 | 48 MB | 18.096.216 | 10.496 | 1,57 s | 11,5 | 34,1 MB |
| ×4 | 98 MB | 36.192.432 | 20.992 | 2,58 s | 14,0 | 34,6 MB |
| ×8 | 196 MB | 72.384.864 | 41.984 | 5,23 s | 13,8 | 35,7 MB |
| ×16 | **393 MB** | **144.769.728** | 83.968 | **10,90 s** | 13,3 | **37,7 MB** |

### 4.3. Thời gian tăng tuyến tính

| Loạt | Chi phí cố định | Thời gian thêm cho mỗi triệu dòng | R² |
|---|---|---|---|
| CSV gốc | 0,39 s | **1,34 s** | 1,00 |
| Parquet | 0,32 s | **0,07 s** | 0,99 |

**Nhận xét:**

1. **Thời gian tăng tuyến tính theo kích thước dữ liệu** (R² ≥ 0,99 ở cả hai loạt). Dữ liệu gấp đôi thì thời gian gấp đôi, không tăng vọt. Đây là định nghĩa của **xử lý có khả năng mở rộng**: chi phí trên mỗi bản ghi không đổi khi dữ liệu lớn lên.
2. **Ở kích thước nhỏ, chi phí cố định chiếm phần lớn.** Parquet ×1 chỉ đạt 6,3 triệu dòng/s, còn từ ×4 trở lên đạt ổn định 13–14 triệu dòng/s. Khoảng 0,3–0,4 s mỗi job là chi phí lập kế hoạch, khởi tạo task và đọc metadata, không phụ thuộc dữ liệu. Vì vậy **benchmark trên dữ liệu quá nhỏ sẽ đánh giá thấp hệ thống**.
3. **Bộ nhớ gần như không đổi: 33,8 MB mỗi task với 99 MB CSV và 37,7 MB với 145 triệu dòng Parquet.** Lượng dữ liệu tăng 16 lần nhưng bộ nhớ chỉ tăng 12%. Lý do: phép `groupBy` của Spark đọc dữ liệu theo luồng (từng lô dòng) và chỉ giữ trong bộ nhớ **bảng băm các nhóm**. Bộ nhớ phụ thuộc vào **số nhóm**, không phụ thuộc số dòng. Phần tăng nhẹ ở loạt B đến từ số nhóm tăng 16 lần. Dữ liệu shuffle cũng rất nhỏ (dưới 1 MB), vì mỗi task gom nhóm cục bộ trước khi trao đổi (partial aggregation).
4. **Hệ quả: hệ thống xử lý được dữ liệu lớn hơn bộ nhớ.** Với heap 2 GB, job đọc 1,2 GB CSV hay 145 triệu dòng mà vẫn chỉ dùng vài chục MB bộ nhớ thực thi. Muốn xử lý 10 lần dữ liệu thì cần khoảng 10 lần thời gian (hoặc 10 lần số nhân), không cần thêm bộ nhớ.

### 4.4. CSV so với Parquet

| Định dạng | Kích thước | Bản ghi | Thời gian |
|---|---|---|---|
| CSV gốc (12 tháng) | 1.185 MB | 9.555.071 | 13,22 s |
| Parquet đã làm sạch | **23 MB** | 9.048.108 | **1,43 s** |

- **Parquet nhỏ hơn 52 lần** (chỉ giữ 3 cột cần dùng, mã hóa theo cột, nén) và **nhanh hơn 9,2 lần**.
- Tính theo bản ghi, Parquet xử lý **0,07 s/triệu dòng**, CSV mất **1,34 s/triệu dòng**, chậm hơn khoảng 19 lần. Với CSV, phần lớn thời gian dành cho việc **phân tích văn bản**: tách dấu phẩy, chuyển chuỗi thành số, phân tích chuỗi ngày giờ. Parquet lưu sẵn dạng nhị phân có kiểu.
- Kết quả rõ nhất: **145 triệu dòng Parquet (10,9 s) xử lý nhanh hơn 9,6 triệu dòng CSV (13,2 s).** Đây là lý do ở Phase 1, dữ liệu được chuyển sang Parquet ngay sau khi làm sạch (bước 07), và `integrated_traffic` được lưu ở dạng Parquet theo data contract.

### 4.5. Số nhân: song song hóa

| Dữ liệu | `local[1]` | `local[2]` | Speed-up | Hiệu suất song song |
|---|---|---|---|---|
| CSV 12 tháng | 20,51 s | 13,22 s | 1,55 | 78% |
| Parquet ×8 (72 triệu dòng) | 9,35 s | 5,23 s | **1,79** | **89%** |

- Gấp đôi số nhân thì nhanh hơn 1,55–1,79 lần. Không đạt đúng 2 lần vì có phần việc không song song hóa được (lập kế hoạch, gộp kết quả cuối ở driver, stage cuối chỉ có 1 task) và 2 nhân của máy ảo dùng chung tài nguyên với hệ điều hành. Đây là **định luật Amdahl**: phần tuần tự giới hạn mức tăng tốc.
- Parquet song song hóa tốt hơn CSV (89% so với 78%). Dữ liệu CSV gồm 12 file kích thước không đều (60–107 MB), nên có lúc một nhân đã xong việc mà phải chờ nhân còn lại.
- Với `local[1]`, bộ nhớ đỉnh mỗi task tăng lên khoảng 67–69 MB (so với 34 MB). Spark chia bộ nhớ thực thi đều cho các task đang chạy đồng thời; chỉ còn 1 task thì task đó được dùng phần lớn hơn. Bộ nhớ "đỉnh" vì vậy phản ánh cả **lượng bộ nhớ được cấp**, không chỉ lượng bắt buộc phải dùng.

## 5. Kết luận cho phần giải trình

| Yêu cầu của plan | Kết quả |
|---|---|
| Dataset size | 99 MB → 1,2 GB (CSV); 23 MB → 393 MB Parquet, tương đương khoảng 18 GB nếu ở dạng CSV gốc |
| Number of records | 0,8 triệu → 145 triệu |
| Execution time | Tăng **tuyến tính** (R² ≥ 0,99): 1,34 s/triệu dòng với CSV, 0,07 s/triệu dòng với Parquet |
| Memory | **Gần như không đổi** (34–38 MB mỗi task), phụ thuộc số nhóm chứ không phụ thuộc số dòng |
| Bài học | (1) Định dạng lưu trữ quan trọng hơn cấu hình: Parquet nhanh hơn CSV 9–19 lần. (2) Thêm nhân thì nhanh hơn nhưng không tuyệt đối (Amdahl). (3) Dữ liệu lớn hơn bộ nhớ vẫn xử lý được nhờ aggregation theo luồng |

**Giới hạn của thí nghiệm (cần nói rõ khi báo cáo):**

- Chỉ chạy trên một máy 2 nhân. Không đo được chi phí mạng khi shuffle giữa nhiều máy (plan cũng không yêu cầu hệ phân tán).
- Dữ liệu loạt B là **bản sao** của dữ liệu thật. Tỉ lệ nén và phân bố giá trị giống hệt bản gốc, nên dữ liệu thật đa dạng hơn có thể nén kém hơn một chút.
- Ở loạt B, `input_mb` (dữ liệu Spark báo đã đọc) thấp hơn kích thước file trên đĩa khoảng 37–40%. Nhóm chưa xác định được nguyên nhân chính xác, nên chỉ dùng kích thước file trên đĩa trong các kết luận.
- Ở các kích thước lớn, lần chạy đầu thường cũng là lần nhanh nhất (`first_s = best_s`). Nghĩa là không còn hiệu ứng "khởi động", và chênh lệch giữa các lần chạy chỉ là dao động nhỏ.

## 6. Kiểm tra

- [x] Số bản ghi Parquet ×1 = 9.048.108, đúng bằng số dòng sau làm sạch (bước 07)
- [x] Parquet ×k có đúng k × 9.048.108 bản ghi và k × 5.248 nhóm
- [x] Kích thước 12 tháng CSV = 1.185 MB, khớp với dung lượng `data/raw/speeds` (bước 05)
- [x] Báo cáo `14_scalability.md` sinh tự động, số liệu thô lưu trong `14_results_*.json`

## 7. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Đo bộ nhớ bằng RSS của tiến trình JVM: luôn khoảng 1,9 GB ở mọi kích thước | JVM giữ heap đã cấp và không trả lại hệ điều hành, nên RSS không phản ánh nhu cầu của job. Đổi sang đọc chỉ số `peakExecutionMemory` của từng stage qua REST API của Spark UI |
| `peakExecutionMemory` tăng tuyến tính theo dữ liệu (68 → 406 MB) | Đây là **tổng** đỉnh bộ nhớ của mọi task trong stage, nhiều file thì nhiều task. Chia cho số task thì ra con số đúng: khoảng 34 MB mỗi task và không đổi |
| Lần thử đầu so sánh `local[1]` (1 lần chạy, lạnh) với `local[2]` (tốt nhất trong 3 lần, ấm) | So sánh như vậy không công bằng. Sửa thành lấy lần tốt nhất ở cả hai bên |
| Tiến trình chạy nền bị dừng khi lệnh kết thúc, mỗi lệnh tối đa 3 phút | Chia job thành các phần `--part`, lưu kết quả trung gian ra JSON |
