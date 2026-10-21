# 13. Exact vs Approximate processing

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật (9.048.108 bản ghi tốc độ).
> Báo cáo: `docs/bao-cao/13_approximate.md`

## 1. Mục tiêu

Theo plan (mục 10): so sánh **kết quả chính xác** (tính trên toàn bộ dữ liệu) với **kết quả xấp xỉ** (tính trên mẫu, hoặc bằng thuật toán xấp xỉ) theo 4 tiêu chí: **thời gian, giá trị chính xác, giá trị xấp xỉ, sai số tương đối**.

## 2. Thiết kế thí nghiệm

| Phần | Câu hỏi | Phương pháp xấp xỉ |
|---|---|---|
| A | Tốc độ trung bình mỗi quận? | Lấy mẫu ngẫu nhiên (Bernoulli) 0,1% / 1% / 5% / 10% / 30%, **mỗi tỉ lệ 5 seed** |
| B | Lấy mẫu tiết kiệm bao nhiêu thời gian? | Mẫu lấy tại chỗ so với mẫu dựng sẵn |
| C | Có bao nhiêu cặp (tuyến, giờ) khác nhau? | `approx_count_distinct`: thuật toán **HyperLogLog++** |
| D | Trung vị tốc độ mỗi quận? | `percentile_approx`: thuật toán phân vị xấp xỉ có sai số giới hạn |

**Vì sao mỗi tỉ lệ chạy 5 seed?** Một lần lấy mẫu có thể "may" hoặc "xui". Chạy nhiều seed mới đo được sai số **điển hình** và sai số **xấu nhất**.

**Khoảng tin cậy 95%:** theo định lý giới hạn trung tâm, trung bình mẫu có sai số chuẩn là `s/√n`. Khoảng `mean ± 1,96·s/√n` phải chứa giá trị đúng khoảng 95% số lần. Thí nghiệm kiểm tra điều này trên dữ liệu thật.

## 3. Thực hiện

```bash
python -m spark_jobs.s13_approximate
```

Thời gian chạy khoảng 70 giây.

## 4. Kết quả

### 4.1. Sai số của trung bình mẫu

Giá trị đúng trên 9.048.108 bản ghi: Staten Island 79,57 · Queens 62,35 · Bronx 62,09 · Brooklyn 54,85 · Manhattan 40,79 km/h.

| Tỉ lệ mẫu | Cỡ mẫu TB / quận | Sai số TB | Sai số lớn nhất | KTC 95% chứa giá trị đúng |
|---|---|---|---|---|
| 0,1% | 1.805 | 0,69% | 1,88% | 100% |
| 1% | 18.104 | 0,37% | 1,06% | 96% |
| 5% | 90.369 | 0,12% | 0,50% | 96% |
| 10% | 180.988 | 0,10% | 0,30% | 100% |
| 30% | 542.793 | 0,05% | 0,29% | 92% |

**Nhận xét:**

1. **Chỉ với 0,1% dữ liệu (khoảng 9 nghìn bản ghi), sai số trung bình đã dưới 0,7%.** Với câu hỏi "quận nào chậm nhất", mẫu 0,1% cho thứ hạng giống hệt kết quả chính xác.
2. **Sai số giảm theo √n:**
   - Tăng cỡ mẫu từ 1% lên 10% (gấp 10 lần) thì sai số giảm 3,74 lần, gần với lý thuyết √10 ≈ 3,16.
   - Từ 0,1% lên 1% chỉ giảm 1,87 lần. Với 25 ước lượng mỗi tỉ lệ, sai số trung bình còn dao động ngẫu nhiên, cần nhiều seed hơn để tỉ số hội tụ.
   - Hệ quả thực tế: **muốn sai số giảm một nửa thì phải tăng cỡ mẫu 4 lần.**
3. **Khoảng tin cậy 95% đúng như lý thuyết:** chứa giá trị đúng ở 92–100% số lần, trung bình 96,8%. Như vậy kết quả xấp xỉ **có thể đi kèm mức độ tin cậy**, đó là ưu điểm lớn của lấy mẫu ngẫu nhiên.
4. **Quận có phương sai lớn thì sai số lớn hơn:** ở mẫu 0,1%, Manhattan và Bronx sai số 0,93%, còn Staten Island 0,47%. Tốc độ ở Manhattan dao động mạnh (tắc nghẽn), nên cùng cỡ mẫu sẽ ước lượng kém chính xác hơn.

### 4.2. Thời gian

| Cách tính | Lần đầu | Tốt nhất |
|---|---|---|
| Exact: đọc Parquet + tính trên 100% | 0,76 s | 0,61 s |
| Mẫu 1% **tại chỗ**: đọc Parquet + lấy mẫu + tính | 0,42 s | 0,32 s |
| Exact trên dữ liệu đã cache | 0,80 s | 0,43 s |
| **Mẫu 1% dựng sẵn** (đã cache) | 0,19 s | **0,16 s** |

**Nhận xét quan trọng:** lấy mẫu tại chỗ chỉ nhanh hơn khoảng 2 lần, chứ không nhanh hơn 100 lần dù chỉ dùng 1% dữ liệu. Lấy mẫu Bernoulli (`df.sample()`) **vẫn phải đọc toàn bộ dữ liệu** để quyết định giữ hay bỏ từng dòng. Phần tiết kiệm chỉ đến từ các bước sau (gom nhóm, shuffle). Muốn nhanh thật sự phải **dựng mẫu sẵn một lần, dùng nhiều lần**. Các hệ thống truy vấn xấp xỉ như BlinkDB đều làm như vậy.

### 4.3. Đếm phần tử khác nhau: HyperLogLog

| Phương pháp | Kết quả | Sai số | Thời gian |
|---|---|---|---|
| `countDistinct` (chính xác) | **789.403** | 0 | 10,67 s |
| `approx_count_distinct`, rsd = 0,05 | 857.497 | 8,63% | 7,93 s |
| `approx_count_distinct`, rsd = 0,01 | 791.598 | **0,28%** | 8,10 s |

789.403 khớp đúng với số dòng (tuyến, giờ) của bước 08. Đây là một bước tự kiểm tra chéo giữa Phase 1 và Phase 2.

- `rsd` (relative standard deviation) là **độ lệch chuẩn** tương đối mong đợi, không phải giới hạn trên của sai số. Với rsd = 0,05, sai số 8,63% tương đương khoảng 1,7 lần độ lệch chuẩn, vẫn nằm trong phạm vi có thể xảy ra.
- **Thời gian không chênh lệch nhiều**, vì phần lớn thời gian dùng để dựng chuỗi khóa `link_id|giờ` cho 9 triệu dòng. Ưu điểm thật sự của HyperLogLog là **bộ nhớ cố định vài KB** bất kể có bao nhiêu phần tử, và các bản phác thảo (sketch) **gộp được** giữa các partition. Đếm chính xác thì phải giữ toàn bộ 789 nghìn khóa trong bộ nhớ và shuffle chúng. Ở quy mô hàng tỷ phần tử, đây là khác biệt giữa "chạy được" và "hết bộ nhớ".

### 4.4. Trung vị

Trung vị chính xác: Staten Island 87 · Queens 71 · Bronx 71 · Brooklyn 65 · Manhattan 41 km/h.

| Phương pháp | Thời gian | Sai số lớn nhất |
|---|---|---|
| `percentile` (chính xác) | **1,17 s** | 0 |
| `percentile_approx`, accuracy = 100 | 2,08 s | 1,55% |
| `percentile_approx`, accuracy = 10.000 | 3,42 s | 0 |

**Ở quy mô này, bản chính xác lại nhanh hơn.** Mỗi quận có 0,6–3,4 triệu giá trị, đủ để đưa hết vào bộ nhớ và sắp xếp. Thuật toán xấp xỉ có chi phí cố định để duy trì cấu trúc tóm tắt. Lợi thế của `percentile_approx` chỉ xuất hiện khi số giá trị mỗi nhóm vượt quá bộ nhớ, hoặc khi cần tính trên dữ liệu dạng luồng. Kết quả này được báo cáo trung thực thay vì giả định "xấp xỉ thì luôn nhanh hơn".

## 5. Kết luận cho phần giải trình

| Tiêu chí plan yêu cầu | Kết quả |
|---|---|
| Giá trị chính xác vs xấp xỉ | Mẫu 1%: sai số TB 0,37%; mẫu 0,1%: 0,69%; HyperLogLog rsd 0,01: 0,28% |
| Sai số tương đối | Giảm theo √n; khoảng tin cậy 95% đúng ở 96,8% số lần |
| Thời gian | Lấy mẫu tại chỗ chỉ nhanh hơn khoảng 2 lần (vẫn phải quét toàn bộ); mẫu dựng sẵn nhanh hơn khoảng 3–4 lần |
| Khi nào nên dùng xấp xỉ | Khi cần trả lời nhanh và chấp nhận sai số dưới 1% (dashboard, khám phá dữ liệu); khi dữ liệu vượt bộ nhớ (đếm phân biệt, phân vị trên hàng tỷ dòng) |
