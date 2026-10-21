# Báo cáo bước 12 — Query processing: Join→Filter vs Filter→Join

Sinh tự động lúc 2026-10-13 15:59 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.

## Thí nghiệm A và B

| thi_nghiem | truy_van | vi_tri_dieu_kien_loc | dong_toc_do_vao_join | lan_dau_s | tot_nhat_s | n | avg_kmh |
|---|---|---|---|---|---|---|---|
| A. Catalyst bật | Q1: Join → Filter | dưới Join (lọc TRƯỚC khi join) | 800,924 | 4.17 | 3.87 | 21,167 | 55.30 |
| A. Catalyst bật | Q2: Filter → Join | dưới Join (lọc TRƯỚC khi join) | 800,924 | 4.08 | 3.79 | 21,167 | 55.30 |
| B. Tắt 5 quy tắc đẩy filter | Q1: Join → Filter | trên Join (lọc SAU khi join) | 9,048,108 | 9.20 | 8.51 | 21,167 | 55.30 |
| B. Tắt 5 quy tắc đẩy filter | Q2: Filter → Join | dưới Join (lọc TRƯỚC khi join) | 800,924 | 2.40 | 2.11 | 21,167 | 55.30 |

- Kết quả 4 lần chạy **giống hệt nhau**: 21,167 bản ghi, 55.3 km/h.
- A (Catalyst bật): Q1/Q2 = 1.02 lần.
- B (tắt pushdown): Q1 chậm hơn Q2 **4.0 lần**.

## Thí nghiệm C — Đọc Parquet: partition pruning và filter pushdown

| cach_doc | so_dong | first_s | best_s | PartitionFilters | PushedFilters |
|---|---|---|---|---|---|
| Không lọc | 9,048,108 | 0.31 | 0.23 | — | — |
| Cột partition: month = '2024-03' | 800,924 | 0.11 | 0.08 | isnotnull(month#1929), (month#1929 = 2024-03) | — |
| Cột timestamp, so với hằng TIMESTAMP_NTZ (đúng kiểu) | 800,924 | 0.31 | 0.27 | — | IsNotNull(timestamp), GreaterThanOrEqual(timestamp,2024-03-01T00:00), LessT |
| Cột timestamp, so với CHUỖI '2024-03-01' (sai kiểu) | 800,924 | 0.35 | 0.29 | — | IsNotNull(timestamp), GreaterThanOrEqual(timestamp,2024-03-01T00:00), LessT |
| Cột timestamp đúng kiểu, TẮT Parquet pushdown | 800,924 | 0.34 | 0.28 | — | IsNotNull(timestamp), GreaterThanOrEqual(timestamp,2024-03-01T00:00), LessT |

