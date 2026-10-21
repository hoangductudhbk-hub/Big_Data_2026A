# SLIDE THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN IT5427

**Đề tài:** Hệ thống tích hợp dữ liệu và phân tích thống kê giao thông đô thị quy mô lớn
**Thời lượng:** 12–15 phút (14 slide, khoảng 1 phút/slide) + 2–3 phút demo (`03_KICH_BAN_DEMO.md`)
**Hình minh họa:** thư mục `NOP_BAI/hinh/`

**Mã nguồn:** https://github.com/hoangductudhbk-hub/Big_Data_2026A  
**Dữ liệu gốc (1,2 GB):** [Google Drive](https://drive.google.com/drive/folders/1dQq9kATcZ4wKA_DBr2S8nlsjQdZNfEy-?usp=sharing)

> Mọi số liệu trong slide lấy từ `docs/bao-cao/` và `docs/huong-dan/`, đo trên dữ liệu thật New York 2024.

---

## Slide 1. Trang tiêu đề

**Nội dung**
- Hệ thống tích hợp dữ liệu và phân tích thống kê giao thông đô thị quy mô lớn
- *Big Data Integration and Statistical Analysis System for Urban Traffic Data*
- Học phần IT5427 – Tích hợp và Xử lý Dữ liệu lớn · GVHD: TS. Vũ Tuyết Trinh
- Nhóm 2: Nguyễn Quang Tiến (20261111M) · Hoàng Đức Tư (20261119M) · Cao Tiến Khải (20261109M) · Nguyễn Hoàng Quốc (20261110M)

**Hình:** không

**Lời thoại:** Kính chào cô và hội đồng. Nhóm em xin trình bày đồ án xây dựng một hệ thống dữ liệu lớn hoàn chỉnh cho giao thông New York năm 2024, từ thu thập, tích hợp ba nguồn dữ liệu khác nhau, xử lý bằng Spark, cho tới API và dashboard.

---

## Slide 2. Bài toán và mục tiêu

**Nội dung**
- Câu hỏi thực tế: giờ nào, đường nào tắc nhất? Thời tiết ảnh hưởng tới giao thông bao nhiêu? Ngày nào giao thông khác thường?
- Không nguồn nào một mình trả lời được, nên phải **tích hợp**
- Theo Hướng 1 của học phần: kiến trúc dữ liệu lớn có tích hợp, xử lý, phân tích và dashboard
- Phạm vi: cả năm 2024, 5 quận New York

**Hình:** `hinh/h1_kien_truc.png` (kiến trúc 3 phase)

**Lời thoại:** Hệ thống chia làm ba phase. Phase 1 tích hợp dữ liệu, Phase 2 xử lý bằng PySpark, Phase 3 lưu trữ và trực quan hóa. Ba phase giao tiếp qua một data contract cố định, nên các phần được phát triển song song mà không lệch nhau.

---

## Slide 3. Ba nguồn dữ liệu và 3V

**Nội dung**

| Nguồn | Quy mô 2024 | Đặc điểm |
|---|---|---|
| NYC DOT Traffic Speeds | 11.970.346 bản ghi, 1,19 GB | mph, 5 phút/lần, lat/lon |
| NYC Traffic Volume Counts | 95.203 bản ghi | 15 phút, tọa độ State Plane (feet) |
| Open-Meteo Weather | 5 điểm × 8.784 giờ | UTC, mã WMO |

- **Volume:** 12,1 triệu dòng gốc, 1,2 GB · **Velocity:** cập nhật vài lần mỗi phút · **Variety:** 3 lược đồ, 2 hệ tọa độ, 3 độ chi tiết thời gian
- **Veracity:** 24,41% bản ghi tốc độ không tin cậy

**Lời thoại:** Ba nguồn khác nhau ở mọi khía cạnh: tên cột, đơn vị, hệ tọa độ, độ chi tiết thời gian. Đây chính là bài toán không đồng nhất lược đồ và không đồng nhất dữ liệu trong lý thuyết tích hợp.

---

## Slide 4. Profiling và làm sạch: lỗi thật trong dữ liệu thật

**Nội dung**
- 2.922.227 bản ghi `status = -101` (24,41%): tốc độ trung vị chỉ 23,6 mph so với 41,6 mph bình thường → loại
- Chuỗi tọa độ `link_points` **bị cắt ở đúng 255 ký tự** (68 tuyến), bị cắt mà vẫn đúng định dạng nên rất khó thấy
- 22 ngày nguồn tốc độ mất dữ liệu → **đánh dấu, không xóa, không nội suy**
- Chuyển giờ mùa hè/đông (DST): giờ lặp 03/11, giờ không tồn tại 10/03
- Kết quả: 11,97 triệu → **9.048.108** bản ghi; 1,2 GB CSV → 40 MB Parquet

**Hình:** Bảng 2.2 của báo cáo (kết quả profiling)

**Lời thoại:** Nhóm làm profiling trước để quy tắc làm sạch dựa trên bằng chứng. Phát hiện đáng chú ý nhất là chuỗi tọa độ bị cắt ở 255 ký tự: nếu không xử lý, khoảng cách địa lý ở bước record linkage sẽ sai.

---

## Slide 5. Schema Alignment theo mô hình GAV ⭐

**Nội dung**
- Thử matcher tự động: chỉ dựa vào tên, recall **0,35**; thêm từ điển đồng nghĩa F1 0,94, nhưng matcher **không tìm được phép biến đổi**
- → Ánh xạ **Global-As-View** viết tay: mỗi cột trung gian là một view trên các nguồn

```
T_speed(link, h, avg(kmh)) :- Speeds(link, t, mph, status), status = 0,
                              h = hour(t), kmh = mph * 1.609344
T_volume(seg, h, sum(vol)) :- Volume(seg, ..., yr, m, d, hh, vol), complete(seg, h)
Integrated(road, h, ...)   :- RoadLink(road, link/seg), T_speed / T_volume, W(district, h)
```

- Vì sao GAV: unfolding đơn giản (materialize thành bảng), số nguồn ít và ổn định, phù hợp mô hình kho dữ liệu
- Grain: tốc độ lấy **trung bình** (đại lượng trạng thái), lưu lượng lấy **tổng** (đại lượng tích lũy)

**Lời thoại:** Matcher tự động chỉ tìm tương ứng một-một theo tên, không hiểu rằng năm cột ngày giờ phải ghép thành một timestamp hay tốc độ phải nhân hệ số rồi lấy trung bình theo giờ. Vì vậy nhóm dùng ánh xạ GAV viết tay; truy vấn trên lược đồ trung gian được trả lời bằng unfolding, ở đây thực hiện trước thành bảng integrated_traffic.

---

## Slide 6. Record Linkage: vì sao Levenshtein có precision thấp ⭐

**Nội dung**

| Luật quyết định (373 tên, 69.378 cặp) | Ghép | Đúng | Precision | Recall |
|---|---|---|---|---|
| A: Levenshtein ≥ 0,8 | 336 | 5 | **0,015** | 1,0 |
| B: A + cùng số + cùng hướng/tầng/bang | 13 | 5 | 0,385 | 1,0 |
| C: B với **OSA** (Damerau–Levenshtein), bỏ khoảng trắng, ngưỡng 0,88 | 6 | 5 | **0,833** | 1,0 |

- **Một ký tự mang toàn bộ ý nghĩa:** `40 STREET` / `90 STREET` (similarity 0,89, cách 50 dãy phố); `EAST` / `WEST 117 STREET`; `UPPER` / `LOWER LEVEL`
- Lỗi gõ phổ biến là đảo 2 ký tự (`WALKER` → `WLAKER`): Levenshtein tính 2 phép, OSA tính 1 phép

**Lời thoại:** Luật Levenshtein ban đầu ghép sai 331 trên 336 cặp, vì edit distance coi mọi ký tự như nhau, trong khi chỉ một chữ số khác là đã thành đường khác. Nhóm thêm ràng buộc nghiệp vụ và đổi sang OSA để xử lý lỗi đảo ký tự, precision tăng từ 0,015 lên 0,833 mà recall vẫn bằng 1.

---

## Slide 7. Blocking và nối hai nguồn giao thông

**Nội dung**

| Khóa blocking | Số cặp | Reduction ratio | Pair completeness |
|---|---|---|---|
| Không blocking | 69.378 | 0 | 1,000 |
| **Chữ cái đầu** (chọn) | 3.258 | **0,953** | **1,000** |
| 2 chữ cái đầu | 985 | 0,986 | 0,833 (bỏ lỡ `WALKER ~ WLAKER`) |

- Nối điểm đếm ↔ tuyến tốc độ: tên đường chính giống nhau **và** khoảng cách tới **polyline** ≤ 300 m; blocking theo quận RR 0,81
- Đo tới tâm tuyến: "cách 5,5 km"; đo tới polyline: **11,6 m**
- Trung thực: chỉ **2/104** đoạn giao nhau (tốc độ đo ở cao tốc, lưu lượng ở phố). Trên BQE: tương quan lưu lượng–tốc độ **−0,67**

**Lời thoại:** Khóa blocking hai chữ cái đầu nhanh hơn nhưng bỏ lỡ đúng lỗi gõ ở ký tự thứ hai, nên khóa blocking phải ổn định trước đúng loại lỗi cần bắt. Hai nguồn giao nhau rất ít là hiện trạng của dữ liệu, nhóm báo cáo đúng như vậy chứ không cố ghép cho nhiều.

---

## Slide 8. Bảng tích hợp và Data Contract

**Nội dung**
- `integrated_traffic`: **805.780 dòng**, 211 đường, mỗi dòng = 1 đường × 1 giờ, 14 cột, 100% có thời tiết, **0 lỗi contract**
- Data contract v1.0.0 (`common/contract.py`): kiểu, null, đơn vị, miền giá trị, khóa chính
- Một nguồn quy tắc dùng ở **5 nơi**: đầu ra Phase 1 · schema Spark · CHECK của PostgreSQL · kiểm tra import qua API · mock dataset
- → Chặn **schema drift**; Phase 2 phát triển trên mock rồi chuyển sang dữ liệu thật mà **không sửa code**

**Lời thoại:** Data contract là xương sống của hệ thống. Nhờ nó, ràng buộc trong database được sinh tự động chứ không viết tay, và dữ liệu sai lược đồ bị chặn ngay từ cửa vào, dù đến từ pipeline hay từ người dùng import.

---

## Slide 9. Spark: thí nghiệm Predicate Pushdown ⭐

**Nội dung**
- Truy vấn: tốc độ TB ở Queens, giờ mưa, tháng 3/2024; join 9 triệu bản ghi × 125 tuyến × 43.915 giờ thời tiết

| Thí nghiệm | Truy vấn | Dòng vào join | Thời gian |
|---|---|---|---|
| Catalyst bật | Join → Filter | 800.924 | 3,87 s |
| Catalyst bật | Filter → Join | 800.924 | 3,79 s |
| Tắt 5 quy tắc tối ưu | Join → Filter | **9.048.108** | **8,51 s** |
| Tắt 5 quy tắc tối ưu | Filter → Join | 800.924 | **2,11 s** |

- Không có pushdown: **chậm hơn 4,0 lần**, kết quả **giống hệt** (21.167 bản ghi, 55,3 km/h)
- Catalyst tự viết lại Q1 thành Q2; partition pruning theo tháng nhanh hơn 3 lần

**Lời thoại:** Nếu chỉ so hai truy vấn khi Catalyst bật thì chúng chạy như nhau, vì Catalyst đã tự đẩy filter xuống. Nhóm phải tắt năm quy tắc tối ưu mới đo được giá trị thật: lọc trước giảm 11 lần số dòng vào join và nhanh hơn 4 lần.

---

## Slide 10. Spark: xử lý xấp xỉ và khả năng mở rộng ⭐

**Nội dung**
- **Sampling 1%:** sai số TB **0,37%**; KTC 95% chứa giá trị đúng 96,8% số lần; sai số giảm theo √n
- **HyperLogLog:** 791.598 so với 789.403 thật, sai số **0,28%**
- Trung thực: `sample()` vẫn quét toàn bộ nên chỉ nhanh ~2 lần; `percentile_approx` chậm hơn bản chính xác ở quy mô này
- **Scalability:** 0,8 → **145 triệu dòng**, thời gian **tuyến tính** (R² ≥ 0,99), bộ nhớ **34–38 MB/task** gần như không đổi
- 145 triệu dòng Parquet (10,9 s) nhanh hơn 9,6 triệu dòng CSV (13,2 s)

**Hình:** `hinh/h3_scalability.png`

**Lời thoại:** Lấy mẫu một phần trăm cho sai số dưới nửa phần trăm và kèm được khoảng tin cậy. Khi tăng dữ liệu 16 lần, thời gian tăng tuyến tính còn bộ nhớ gần như không đổi, vì groupBy đọc theo luồng; nghĩa là hệ thống xử lý được dữ liệu lớn hơn bộ nhớ.

---

## Slide 11. Thống kê: nhịp giao thông của New York

**Nội dung**
- Thống kê count/mean/std/min/max/median theo 9 chiều, 419 dòng; kiểm tra chéo pandas = Spark
- Ngày thường: 2 đỉnh lưu lượng (7–8h, 15–17h); chậm nhất **16h (44,1 km/h)**; cuối tuần không có cao điểm sáng
- Manhattan chậm nhất (40,5 km/h), Staten Island nhanh nhất (79,4 km/h)
- Cross Bronx Expressway biến động lớn nhất (std 33,8 km/h)

**Hình:** `hinh/h2_theo_gio.png`

**Lời thoại:** Biểu đồ theo giờ cho thấy cao điểm chiều nặng hơn cao điểm sáng, và cuối tuần không có cao điểm sáng. Tốc độ và lưu lượng được vẽ thành hai biểu đồ riêng để không tạo ra tương quan giả của biểu đồ hai trục.

---

## Slide 12. Thời tiết: vì sao "tuyết làm xe chạy nhanh hơn"? ⭐

**Nội dung**

| Thời tiết | So sánh thô | Kiểm soát đường, giờ, loại ngày | Kiểm soát thêm **tháng** |
|---|---|---|---|
| Rain | −6,6% | −4,8% | **−4,6%** |
| Drizzle | −5,4% | −2,7% | **−2,4%** |
| Snow | **+0,6%** | **+5,8%** | **−0,1%** |

- **Biến gây nhiễu (confounding):** tuyết chỉ rơi tháng 1, 2, 12, mà mùa đông vốn vắng xe. So "giờ có tuyết" với "mọi giờ khác" thực chất là so mùa đông với cả năm
- Phương pháp: so mỗi bản ghi với **chính đường đó, cùng giờ, cùng loại ngày, cùng tháng, lúc khô ráo**
- Mưa giờ cao điểm: **−8,4%**, gấp đôi ngoài cao điểm; Pearson mưa–tốc độ chỉ −0,02 dù có tác động

**Hình:** `hinh/h4_thoi_tiet.png`

**Lời thoại:** So sánh thô cho kết quả vô lý là tuyết làm xe chạy nhanh hơn. Kiểm soát theo đường và giờ vẫn chưa hết, chỉ khi kiểm soát thêm theo tháng thì tác động về gần 0, tức đó là hiệu ứng mùa đông vắng xe. Còn mưa thì làm chậm thật 4,6%, và gấp đôi khi rơi vào giờ cao điểm.

---

## Slide 13. Phát hiện bất thường bằng Z-score theo ngữ cảnh

**Nội dung**
- `z = (x − mean)/std`, |z| > 3; mean/std theo **cùng đường × giờ × loại ngày**, tính **leave-one-out**
- Giới hạn toán học: |z| ≤ (n−1)/√n → ô < 11 giá trị không bao giờ vượt 3
- Kiểm chứng trên mock có đáp án: toàn cục bắt **2%**, theo ngữ cảnh bắt **97–100%**
- Dữ liệu thật: **13.678** bất thường; ngày bất thường nhất là **13/02/2024** (10,7%, bão tuyết ~16 cm, đường vắng), các ngày lễ 01/01, 04/07

**Hình:** `hinh/h5_bat_thuong.png`

**Lời thoại:** Z-score theo đường gần như mù vì tốc độ dao động mạnh trong ngày. Theo ngữ cảnh thì bắt được 97% bất thường cài sẵn, và trên dữ liệu thật thuật toán tự tìm lại ngày bão tuyết lớn nhất năm mà không cần ai chỉ trước.

---

## Slide 14. Hệ thống và kết luận

**Nội dung**
- **PostgreSQL** 9 bảng, 864.750 dòng; **FastAPI** 27 endpoint; **Dashboard** 6 tab; **Docker Compose**
- Kiểm thử: 39 unit test + 22 backend test + **18/18 end-to-end** (chạy trong Docker, nạp dữ liệu 44,4 s)
- **Definition of Done: 17/17**
- Hạn chế: 1 máy 2 nhân; 1 năm dữ liệu, 1 trận tuyết lớn; lưu lượng đếm theo đợt quá thưa
- Hướng phát triển: baseline trượt cho phát hiện bất thường, thêm dữ liệu sự cố, mô hình học máy dự báo tốc độ

**Hình:** `hinh/h6_dashboard_tongquan.png`

**Lời thoại:** Toàn bộ hệ thống chạy được bằng một lệnh Docker và đạt đủ 17 tiêu chí hoàn thành. Sau đây nhóm em xin demo trực tiếp hệ thống. Em xin cảm ơn cô và hội đồng đã lắng nghe.

---

## Phụ lục: câu hỏi có thể gặp

| Câu hỏi | Trả lời ngắn | Slide |
|---|---|---|
| Sao không dùng LAV? | GAV unfolding đơn giản, nguồn ít và ổn định, tích hợp vật lý như kho dữ liệu | 5 |
| Nhãn để tính precision lấy đâu? | Gán theo tiêu chí ghi trong `labels.py`: chỉ khác chính tả hoặc khoảng trắng là cùng đường; khác số, hướng, tầng, bang là khác đường | 6 |
| Sao chọn ngưỡng 300 m? | Điểm đếm nằm cạnh đường, sai số tọa độ và chiều ngang cao tốc; các cặp đúng cách 4,7 m và 11,6 m | 7 |
| Spark chạy 1 máy thì có gọi là Big Data? | Thí nghiệm đo được bản chất: pushdown, xấp xỉ, mở rộng tuyến tính, bộ nhớ không đổi; code chạy được trên cluster không cần sửa | 9–10 |
| Có chắc 13/02 là bão tuyết? | Dữ liệu Open-Meteo ghi khoảng 16 cm tuyết ngày đó; tốc độ cao hơn bình thường 25% | 13 |
| Sao không dùng Machine Learning? | Theo định hướng đề tài tập trung vào tích hợp và xử lý; bảng tích hợp đã sẵn đặc trưng để phát triển mô hình | 14 |
