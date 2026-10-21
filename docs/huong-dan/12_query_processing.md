# 12. Query processing: Join→Filter so với Filter→Join

> **Trạng thái:** ✅ Hoàn thành ngày 13/10/2026 trên dữ liệu thật.
> Báo cáo: `docs/bao-cao/12_query_processing.md`

## 1. Mục tiêu

Minh họa **predicate pushdown**, tức giảm dữ liệu trước khi join, theo đúng yêu cầu của plan (mục 9.3): so sánh Query 1 (Join → Filter) với Query 2 (Filter → Join) về **thời gian chạy**, **số bản ghi được xử lý** và **kết quả**.

## 2. Thiết kế thí nghiệm

**Truy vấn:** "Tốc độ trung bình các tuyến ở **Queens** trong những giờ **trời mưa** của **tháng 3/2024**".

```
speeds_clean (9.048.108 bản ghi)  ⨝  links (125 tuyến → lấy quận)  ⨝  weather (43.915 trạm × giờ → lấy thời tiết)
```

- **Q1 (Join → Filter):** join cả 3 bảng rồi mới lọc quận, thời tiết, tháng.
- **Q2 (Filter → Join):** lọc từng bảng trước (tốc độ: tháng 3; tuyến: Queens; thời tiết: Queens + Rain + tháng 3) rồi mới join.

**Vấn đề:** Spark có bộ tối ưu **Catalyst** tự động đẩy filter xuống trước join. Nếu chỉ chạy Q1 và Q2 thì Catalyst sẽ viết lại Q1 cho giống Q2, và thí nghiệm không chứng minh được gì. Vì vậy thí nghiệm có 2 phần:

| Thí nghiệm | Mục đích |
|---|---|
| **A. Catalyst bật** (thực tế) | Chứng minh Catalyst tự làm predicate pushdown |
| **B. Tắt các quy tắc đẩy filter** | Buộc Spark làm đúng thứ tự đã viết, để **đo được giá trị thật** của predicate pushdown |

**Các thiết lập để đo cho đúng:**

- **Tắt broadcast join** (`autoBroadcastJoinThreshold = -1`) để Spark dùng sort-merge join. Khi đó chi phí join tỉ lệ với số dòng đi vào join, giống trên cluster nhiều máy.
- **Mỗi lần đo dựng DataFrame mới**, lấy cả thời gian lần đầu và tốt nhất trong 3 lần (xem hướng dẫn 11, mục 6).
- **Tự kiểm tra plan:** script đọc optimized plan để xác định điều kiện lọc nằm **trên** hay **dưới** phép Join, không suy đoán.

## 3. Thực hiện

```bash
python -m spark_jobs.s12_query_processing
```

Thời gian chạy khoảng 1 phút 50 giây (gồm 12 lần chạy truy vấn có join).

## 4. Kết quả

### 4.1. Thí nghiệm A và B

| Thí nghiệm | Truy vấn | Điều kiện lọc nằm ở | Dòng tốc độ vào join | Lần đầu | Tốt nhất |
|---|---|---|---|---|---|
| A. Catalyst bật | Q1: Join → Filter | **dưới** Join | 800.924 | 4,17 s | **3,87 s** |
| A. Catalyst bật | Q2: Filter → Join | dưới Join | 800.924 | 4,08 s | **3,79 s** |
| B. Tắt 5 quy tắc | Q1: Join → Filter | **trên** Join | **9.048.108** | 9,20 s | **8,51 s** |
| B. Tắt 5 quy tắc | Q2: Filter → Join | dưới Join | 800.924 | 2,40 s | **2,11 s** |

**Kết quả của cả 4 lần chạy giống hệt nhau:** 21.167 bản ghi, 55,3 km/h. Thứ tự phép toán không làm thay đổi kết quả, chỉ thay đổi chi phí.

**Nhận xét:**

1. **Khi tắt pushdown, Join → Filter chậm hơn Filter → Join 4,0 lần** (8,51 s so với 2,11 s). Nguyên nhân là Q1 phải đưa **9 triệu dòng** vào join (shuffle và sắp xếp), trong khi Q2 chỉ đưa **800 nghìn dòng**, ít hơn 11 lần.
2. **Khi Catalyst bật, Q1 và Q2 chạy như nhau** (3,87 s và 3,79 s). Catalyst đã tự viết lại Q1: điều kiện lọc được đẩy xuống dưới Join. Đây là lý do trong thực tế người dùng không cần tự sắp xếp thứ tự filter/join khi dùng DataFrame hoặc SQL.
3. **Catalyst có nhiều quy tắc chồng lớp.** Lần thử đầu chỉ tắt `PushDownPredicates` thì filter **vẫn bị đẩy xuống** một phần. `InferFiltersFromConstraints` tự suy ra thêm điều kiện, còn `PushPredicateThroughJoin`/`PushPredicateThroughNonJoin` đẩy tiếp. Phải tắt cả 5 quy tắc (`PushDownPredicates`, `PushPredicateThroughJoin`, `PushPredicateThroughNonJoin`, `CombineFilters`, `InferFiltersFromConstraints`) thì filter mới nằm hẳn trên Join.
4. **Một quan sát cần nói thẳng:** Q2 khi tắt các quy tắc (2,11 s) lại *nhanh hơn* khi bật Catalyst (3,79 s). Tối ưu hóa dựa trên quy tắc không phải lúc nào cũng cho kế hoạch tốt nhất. *Giả thuyết (chưa kiểm chứng):* khi đẩy điều kiện tháng 3 qua phép chiếu, Catalyst phải tính `date_trunc(timestamp)` trên mọi dòng trước khi lọc, đồng thời thêm các phép lọc `isnotnull` suy diễn. Để kiểm chứng cần so sánh chi tiết physical plan và các chỉ số trên Spark UI.

### 4.2. Thí nghiệm C: đọc Parquet

| Cách đọc `speeds_clean` | Số dòng | Tốt nhất | PartitionFilters | PushedFilters |
|---|---|---|---|---|
| Không lọc | 9.048.108 | 0,23 s | — | — |
| **Lọc cột partition** `month = '2024-03'` | 800.924 | **0,08 s** | `month = 2024-03` | — |
| Lọc cột `timestamp` (hằng kiểu TIMESTAMP_NTZ) | 800.924 | 0,27 s | — | `GreaterThanOrEqual(timestamp, 2024-03-01)…` |
| Lọc cột `timestamp` (hằng là chuỗi) | 800.924 | 0,29 s | — | như trên |
| Lọc cột `timestamp`, tắt Parquet pushdown | 800.924 | 0,28 s | — | như trên |

**Nhận xét:**

- **Partition pruning** nhanh hơn 3 lần (0,08 s so với 0,23 s). Spark chỉ mở thư mục `month=2024-03`, bỏ qua 11 thư mục còn lại mà không cần đọc file. Đây là lý do `integrated_traffic` được chia partition theo `year/month` (data contract, bước 03).
- **Lọc theo cột thường** không nhanh hơn ở quy mô này, dù filter đã được đẩy xuống Parquet. Mỗi tháng là một file với ít row group, nên Spark vẫn phải mở cả 12 file và đọc footer của chúng. Chi phí cố định này lấn át phần tiết kiệm. Pushdown xuống Parquet phát huy tác dụng khi file lớn, có nhiều row group, và dữ liệu được sắp xếp theo cột lọc.
- So sánh với chuỗi `'2024-03-01'` vẫn được đẩy xuống, vì Spark 3.5 ép kiểu **hằng số** sang timestamp chứ không ép kiểu **cột**. Nếu ép kiểu cột thì sẽ mất pushdown.
- Dòng "TẮT Parquet pushdown" vẫn hiện `PushedFilters` trong plan. Spark vẫn liệt kê bộ lọc, nhưng trình đọc Parquet không dùng thống kê để bỏ qua dữ liệu.

## 5. Kết luận cho phần giải trình

| Câu hỏi của plan | Trả lời bằng số liệu |
|---|---|
| Thời gian chạy | Không có pushdown: Join→Filter 8,51 s, Filter→Join 2,11 s (chậm hơn **4 lần**) |
| Số bản ghi được xử lý | 9.048.108 so với 800.924 dòng đi vào join (nhiều hơn **11 lần**) |
| Kết quả cuối | **Giống hệt nhau** (21.167 bản ghi, 55,3 km/h) |
| Thực tế với Spark | Catalyst tự đẩy filter xuống nên Q1 ≈ Q2 (3,87 so với 3,79 s). Người dùng được hưởng predicate pushdown mà không phải làm gì |

## 6. Vấn đề gặp phải

| Vấn đề | Cách xử lý |
|---|---|
| Lần chạy đầu: mọi truy vấn khoảng 0,03 s, kể cả join 9 triệu dòng | Lỗi đo do dùng lại DataFrame (skipped stages). Đổi sang `measure(build)`, dựng DataFrame mới mỗi lần |
| Chỉ tắt `PushDownPredicates` nhưng filter vẫn bị đẩy xuống | Thăm dò từng tổ hợp quy tắc, xác định cần tắt đủ 5 quy tắc |
| `F.expr(...)` ở cấp module báo `AssertionError` | Hằng số TIMESTAMP_NTZ phải tạo sau khi SparkSession đã khởi động |
| Ghi đè file trực tiếp lên ổ D: đôi khi máy ảo vẫn thấy bản cũ | Đồng bộ code bằng file zip rồi giải nén, sau đó kiểm tra nội dung (`grep`) trước khi chạy |
