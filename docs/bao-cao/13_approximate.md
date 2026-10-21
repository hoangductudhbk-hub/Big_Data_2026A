# Báo cáo bước 13 — Exact vs Approximate processing

Sinh tự động lúc 2026-10-13 16:05 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.

## A. Trung bình tốc độ theo quận: sai số theo tỉ lệ mẫu

Giá trị đúng (exact) tính trên toàn bộ 9,048,108 bản ghi:
| district | n | toc_do_tb_kmh |
|---|---|---|
| Brooklyn | 622,966 | 54.85 |
| Staten Island | 1,676,570 | 79.57 |
| Manhattan | 1,468,656 | 40.79 |
| Queens | 3,368,987 | 62.35 |
| Bronx | 1,910,929 | 62.09 |

Mỗi tỉ lệ chạy 5 seed × 5 quận = 25 ước lượng:
| ti_le_mau | mau_tb | sai_so_tb_pct | sai_so_max_pct | ci95_chua_gia_tri_dung_pct |
|---|---|---|---|---|
| 0.1% | 1,805 | 0.69 | 1.88 | 100.00 |
| 1% | 18,104 | 0.37 | 1.06 | 96.00 |
| 5% | 90,369 | 0.12 | 0.50 | 96.00 |
| 10% | 180,988 | 0.10 | 0.30 | 100.00 |
| 30% | 542,793 | 0.05 | 0.29 | 92.00 |

Tỉ số sai số 0,1% / 1% = 1.87 và 1% / 10% = 3.74 (lý thuyết √10 ≈ 3,16).
Sai số trung bình ở mẫu 0,1% theo từng quận (quận ít dữ liệu sai số lớn hơn): Manhattan 0.93%, Bronx 0.93%, Queens 0.61%, Brooklyn 0.49%, Staten Island 0.47%

## B. Thời gian: lấy mẫu tại chỗ vs mẫu dựng sẵn

| cach | first_s | best_s |
|---|---|---|
| Exact: đọc Parquet + tính trên 100% | 0.59 | 0.50 |
| Sample 1% tại chỗ: đọc Parquet + lấy mẫu + tính | 0.49 | 0.37 |
| Exact trên dữ liệu đã cache (100%) | 0.65 | 0.65 |
| Mẫu 1% dựng sẵn (cached) | 0.19 | 0.17 |


## C. Đếm số cặp (tuyến, giờ) khác nhau

| phuong_phap | ket_qua | sai_so_pct | thoi_gian_s |
|---|---|---|---|
| countDistinct (chính xác) | 789,403 | 0.00 | 10.67 |
| approx_count_distinct (HyperLogLog++, rsd=0.05) | 857,497 | 8.63 | 7.93 |
| approx_count_distinct (HyperLogLog++, rsd=0.01) | 791,598 | 0.28 | 8.10 |


## D. Trung vị tốc độ theo quận

Trung vị chính xác: Brooklyn 65.0 km/h, Staten Island 87.0 km/h, Manhattan 41.0 km/h, Queens 71.0 km/h, Bronx 71.0 km/h
| phuong_phap | thoi_gian_s | sai_so_max_pct |
|---|---|---|
| percentile (chính xác) | 1.17 | 0.00 |
| percentile_approx(accuracy=100) | 2.08 | 1.55 |
| percentile_approx(accuracy=10000) | 3.42 | 0.00 |

