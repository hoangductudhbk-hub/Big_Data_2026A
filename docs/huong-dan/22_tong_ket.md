# 22. Tổng kết theo Definition of Done

> **Trạng thái:** ✅ Hoàn thành ngày 14/10/2026.
> Tài liệu này dùng làm **mục lục khi bảo vệ**: mỗi yêu cầu của plan → bằng chứng nằm ở đâu.

## 1. Definition of Done (plan, mục 20)

| # | Yêu cầu | Đạt | Bằng chứng (số liệu thật) | Ở đâu |
|---|---|---|---|---|
| 1 | Ít nhất 2–3 nguồn dữ liệu khác nhau | ✅ | 3 nguồn, 3 schema khác nhau: DOT Traffic Speeds (hơn 9,5 triệu bản ghi năm 2024), Traffic Volume Counts (theo 15 phút, tọa độ State Plane), Open-Meteo (5 điểm × 8.783 giờ) | Bước 02, 05 |
| 2 | Data Profiling | ✅ | Null, trùng lặp, khoảng giá trị, độ phủ thời gian của từng nguồn; phát hiện `link_points` bị cắt ở 255 ký tự | Bước 06 |
| 3 | Data Cleaning | ✅ | mph → km/h, chuẩn hóa múi giờ (gồm DST), loại trùng, đánh dấu 14 ngày mất dữ liệu (không xóa, không nội suy) | Bước 07 |
| 4 | Schema Alignment | ✅ | Schema matching (theo tên + từ đồng nghĩa, có precision/recall), ánh xạ **GAV** vào mediated schema | Bước 08 |
| 5 | Record Linkage + Blocking | ✅ | Levenshtein/OSA, blocking (reduction ratio, pair completeness), khoảng cách điểm tới polyline; luật của plan (Levenshtein ≥ 0,8) chỉ đạt precision 0,015 nên nhóm thiết kế luật mới | Bước 09 |
| 6 | Tạo được `integrated_traffic` | ✅ | 805.780 dòng, 211 đường, đạt contract 0 lỗi | Bước 10 |
| 7 | PySpark đọc và xử lý được dataset | ✅ | filter/select/join/groupBy/sort/SQL; broadcast join nhanh hơn sort-merge 3,3 lần | Bước 11 |
| 8 | Query Processing experiment | ✅ | Join→Filter chậm hơn Filter→Join **4,0 lần** khi tắt pushdown (9,0 triệu so với 0,8 triệu dòng vào join), kết quả giống hệt; Catalyst tự đẩy filter xuống | Bước 12 |
| 9 | Exact vs Approximate | ✅ | Mẫu 1%: sai số 0,37%; KTC 95% đúng 96,8% số lần; HyperLogLog sai số 0,28%; median xấp xỉ **chậm hơn** chính xác ở quy mô này (báo cáo trung thực) | Bước 13 |
| 10 | Scalability Benchmark | ✅ | 0,8 → 145 triệu dòng: thời gian tuyến tính (R² ≥ 0,99), bộ nhớ gần như không đổi (34–38 MB/task); Parquet nhanh hơn CSV 9 lần | Bước 14 |
| 11 | Statistical Analysis | ✅ | count/mean/std/min/max/median theo 9 chiều (giờ, ngày, đường, quận, thời tiết…), 419 dòng | Bước 15 |
| 12 | Simple Anomaly Detection | ✅ | Z-score theo ngữ cảnh, \|z\| > 3: 13.678 bất thường; mock: recall 97–100%; tìm lại được trận tuyết 13/02 và các ngày lễ | Bước 17 |
| 13 | Kết quả được lưu vào PostgreSQL | ✅ | 9 bảng, 864.750 dòng; ràng buộc CHECK sinh từ contract; Spark = SQL khớp hoàn toàn | Bước 18 |
| 14 | Có FastAPI | ✅ | 27 endpoint trong /api/v1 (cộng `GET /health` ở gốc), gồm đủ 9 endpoint của plan; lỗi thống nhất; 22 test đạt trên PostgreSQL | Bước 19 |
| 15 | Có Docker | ✅ | `docker compose up -d --build` chạy thật trên Windows của nhóm (14/10/2026): PostgreSQL + API trong container, nạp 864.750 dòng trong 44,4 s, kiểm tra end-to-end **18/18 đạt** | Bước 21; `docs/bao-cao/21_e2e_docker.md` |
| 16 | Tài liệu mô tả pipeline | ✅ | 22 file hướng dẫn + 14 báo cáo tự sinh + data contract | `docs/` |
| 17 | Benchmark/kết quả thực tế thay vì số liệu giả | ✅ | Mọi số liệu đo trên dữ liệu NYC 2024 thật; mock chỉ dùng để test code và kiểm chứng bước 17 | Toàn bộ `docs/bao-cao/` |

**Kết quả: 17/17 yêu cầu của Definition of Done đã đạt.**

## 2. Những kết quả "ngược kỳ vọng" (điểm mạnh khi bảo vệ)

Báo cáo trung thực các kết quả không như giả định ban đầu cho thấy nhóm **hiểu bản chất** chứ không chỉ chạy code:

| Kỳ vọng thông thường | Kết quả thật | Giải thích | Bước |
|---|---|---|---|
| Luật Levenshtein ≥ 0,8 của plan ghép đúng tên đường | Precision chỉ 0,015 | Tên đường New York rất giống nhau (`1 AVENUE`/`2 AVENUE`) | 09 |
| Hai nguồn giao thông giao nhau nhiều | Chỉ 2/104 đoạn có cả hai | Cảm biến tốc độ ở cao tốc, điểm đếm ở phố nội đô | 09–10 |
| Xấp xỉ luôn nhanh hơn chính xác | `percentile_approx` chậm hơn `percentile` | Dữ liệu mỗi nhóm vừa bộ nhớ; thuật toán xấp xỉ có chi phí cố định | 13 |
| Lấy mẫu 1% nhanh hơn 100 lần | Chỉ nhanh hơn khoảng 2 lần | `sample()` vẫn phải quét toàn bộ dữ liệu | 13 |
| Tuyết làm xe chậm | So sánh thô: tuyết làm xe **nhanh hơn** | Nhiễu do mùa: mùa đông vắng xe. Kiểm soát theo tháng → ≈ 0 | 16 |
| Trời nóng làm xe chậm 17,7% | Sau kiểm soát: dưới ±1,2% | Trời nóng trùng giờ cao điểm chiều mùa hè | 16 |
| Tương quan mưa–tốc độ thể hiện tác động | Pearson ≈ −0,02 dù mưa làm chậm 4,6% | Quan hệ phi tuyến, 86% bản ghi không có mưa | 16 |
| Z-score theo đường là đủ | Chỉ bắt 2% bất thường | Biến động theo giờ trong ngày làm std quá lớn | 17 |
| Z-score dùng được cho mọi nhóm | Ô < 11 giá trị không thể có \|z\| > 3 | Giới hạn toán học \|z\| ≤ (n−1)/√n → dùng leave-one-out | 17 |

## 3. Kiến trúc cuối cùng

```
                         RAW DATA (1,2 GB CSV + JSON)
     NYC Speeds ─┐            NYC Volume ─┐            Open-Meteo ─┐
                 └──────────────┬─────────┴──────────────┬──────────┘
          Phase 1 (pandas)      ↓                         ↓
        profiling → cleaning → alignment (GAV) → record linkage + blocking
                                ↓
                integrated_traffic.parquet  ◄── data contract v1.0.0 (common/contract.py)
                                ↓
          Phase 2 (PySpark 3.5)  query processing · exact vs approx · scalability
                                 statistics · weather impact · anomaly (Z-score)
                                ↓
                       analytics/*.parquet
                                ↓  load_processed (COPY, 1 transaction, kiểm tra contract + FK)
          Phase 3        PostgreSQL 16 (9 bảng, CHECK sinh từ contract, Alembic)
                                ↓
                        FastAPI (/api/v1, 27 endpoint, import có kiểm tra contract)
                                ↓
                        Dashboard (6 tab, Chart.js + Leaflet)
```

**Data contract là "xương sống":** cùng một file `common/contract.py` được dùng ở Phase 1 (kiểm tra đầu ra), Phase 2 (schema Spark), database (CHECK constraint), API (kiểm tra import) và mock dataset. Đây là lý do ba phase ghép vào nhau không cần sửa code: mock dataset thay bằng dữ liệu thật đúng như plan mục 15 mô tả.

## 4. Kiểm thử

| Bộ test | Số test | Kết quả |
|---|---|---|
| Phase 0–1 (`tests/`) | 39 | ✅ |
| Backend (`backend/tests/`, PostgreSQL) | 22 | ✅ |
| End-to-end (`scripts/e2e_check.py`) | 18 | ✅ |
| Kiểm chứng Z-score trên mock có đáp án | precision/recall | ✅ recall 0,97–1,00 |
| Dashboard (trình duyệt tự động, 6 tab) | — | ✅ không lỗi JavaScript |

## 5. Giới hạn và hướng phát triển

| Giới hạn | Hướng phát triển |
|---|---|
| Chạy Spark trên 1 máy 2 nhân, không đo được chi phí mạng của cluster | Chạy trên cluster nhiều máy (plan không yêu cầu) |
| Dữ liệu một năm, chỉ 1 trận tuyết lớn | Mở rộng nhiều năm để kết luận về tuyết |
| Lưu lượng xe đếm theo đợt, quá thưa cho bất thường và tác động thời tiết | Thêm nguồn đếm liên tục (ví dụ dữ liệu trạm thu phí) |
| Z-score baseline cả năm không phân biệt "sự cố" với "giai đoạn thi công" | Baseline trượt hoặc change-point detection |
| Chưa kiểm chứng nguyên nhân các bất thường | Ghép thêm dữ liệu sự cố/thi công của NYC DOT |
| Nhãn kiểm tra của record linkage chỉ gán một lượt | Kiểm tra chéo độc lập khi mở rộng dữ liệu |
## 6. Gợi ý trình bày khi bảo vệ (15 phút)

1. **Bài toán và dữ liệu** (2 phút): 3 nguồn, schema khác nhau; vì sao cần thời tiết.
2. **Data Integration** (4 phút): profiling phát hiện lỗi thật (link_points bị cắt, lệch múi giờ, DST); record linkage và lý do luật của plan không dùng được (precision 0,015).
3. **Big Data Processing** (4 phút): pushdown chậm/nhanh 4 lần; sai số giảm theo √n; benchmark tuyến tính, bộ nhớ không đổi.
4. **Phân tích** (3 phút): mưa −4,6%, giờ cao điểm −8,4%; tuyết và nhiệt độ là ví dụ về nhiễu; ngày 13/02.
5. **Demo** (2 phút): dashboard → bản đồ → bấm đường → bất thường; import một file CSV có dòng sai để thấy kiểm tra contract.
