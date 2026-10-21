# Báo cáo bước 16 — Tác động của thời tiết lên giao thông

Sinh tự động lúc 2026-10-13 22:30 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.

Bản ghi tốc độ dùng để phân tích: 785,767 (đã bỏ ngày mất dữ liệu và các ô đường × giờ × loại ngày có < 10 giờ khô).

## A. Tốc độ theo điều kiện thời tiết: so sánh thô và có kiểm soát

`thay_doi_tho_pct`: so với trung bình nhóm Clear (cách so sánh ở bước 15). `thay_doi_kiem_soat_pct`: so với chính đường đó, cùng giờ, cùng loại ngày, lúc khô ráo (baseline cả năm). `kiem_soat_them_thang_pct`: như trên nhưng baseline lấy trong CÙNG THÁNG (kiểm soát thêm mùa). Ngày lễ được xếp vào loại ngày cuối tuần.
| weather_condition | n | so_ngay | tb_tho | thay_doi_tho_pct | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct | ktc95_pct |
|---|---|---|---|---|---|---|---|
| Clear | 353,216 | 303 | 61.63 | 0.00 | -0.44 | -0.46 | 0.09 |
| Cloudy | 315,209 | 327 | 61.23 | -0.64 | 0.49 | 0.52 | 0.09 |
| Drizzle | 83,330 | 193 | 58.32 | -5.36 | -2.66 | -2.35 | 0.18 |
| Rain | 23,421 | 96 | 57.55 | -6.61 | -4.79 | -4.56 | 0.36 |
| Snow | 10,591 | 27 | 61.97 | 0.57 | 5.79 | -0.07 | 0.77 |


## B. Tốc độ theo lượng mưa (giờ không có tuyết)

| rain_bin | n | so_ngay | tb_tho | thay_doi_tho_pct | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct | ktc95_pct |
|---|---|---|---|---|---|---|---|
| 0. Không mưa | 668,425 | 344 | 61.44 | 0.00 | 0.00 | 0.00 | 0.07 |
| 1. 0–0,5 mm/h (rất nhẹ) | 65,466 | 192 | 58.72 | -4.42 | -2.15 | -1.57 | 0.21 |
| 2. 0,5–2 mm/h (nhẹ) | 26,249 | 124 | 56.77 | -7.59 | -4.83 | -5.14 | 0.32 |
| 3. 2–5 mm/h (vừa) | 11,082 | 77 | 57.70 | -6.09 | -5.19 | -4.74 | 0.57 |
| 4. > 5 mm/h (to) | 3,954 | 41 | 59.15 | -3.72 | -2.22 | -3.17 | 0.83 |


## C. Mưa trong giờ cao điểm và ngoài cao điểm

| period | is_rain | n | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct |
|---|---|---|---|---|
| Cao điểm ngày thường | Không mưa / mưa rất nhẹ | 127,886 | -0.42 | -0.42 |
| Cao điểm ngày thường | Mưa > 0,5 mm/h | 7,107 | -7.44 | -8.42 |
| Ngoài cao điểm | Không mưa / mưa rất nhẹ | 606,005 | -0.14 | -0.08 |
| Ngoài cao điểm | Mưa > 0,5 mm/h | 34,178 | -4.10 | -4.09 |


## D. Tốc độ theo lượng tuyết

| snow_bin | n | so_ngay | tb_tho | thay_doi_tho_pct | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct | ktc95_pct |
|---|---|---|---|---|---|---|---|
| 0. Không tuyết | 775,176 | 344 | 60.99 | 0.00 | -0.43 | -0.39 | 0.06 |
| 1. 0–0,5 cm/h | 8,678 | 26 | 61.71 | 1.18 | 4.50 | -2.14 | 0.78 |
| 2. 0,5–1 cm/h | 907 | 10 | 64.23 | 5.32 | 5.08 | 2.05 | 2.82 |
| 3. > 1 cm/h | 1,006 | 3 | 62.24 | 2.06 | 17.55 | 15.10 | 3.73 |

**Các giờ có tuyết rơi vào lúc nào, ở đâu?** (so với mọi giờ khác). `baseline_tb` là tốc độ bình thường của đúng các ô (đường × giờ × loại ngày) đó lúc khô ráo:
| grp | n | pct_0h_6h | pct_cuoi_tuan | pct_cao_diem | pct_staten_island | pct_manhattan | baseline_tb |
|---|---|---|---|---|---|---|---|
| Mọi giờ khác | 775,176 | 23.40 | 32.20 | 17.40 | 17.90 | 17.50 | 61.26 |
| Giờ có tuyết | 10,591 | 27.30 | 39.00 | 15.80 | 17.00 | 20.80 | 61.86 |

**Các ngày có tuyết ≥ 1 cm** (tổng lượng tuyết cả ngày, trung bình theo đường):
| date | tuyet_cm_ngay | tuyet_max_cm_h | day_type | toc_do_ca_ngay_pct | kiem_soat_them_thang_pct |
|---|---|---|---|---|---|
| 2024-02-13 | 16.00 | 2.87 | weekday | 29.90 | 25.06 |
| 2024-01-06 | 3.90 | 2.10 | weekend | 14.83 | 0.49 |
| 2024-02-17 | 3.90 | 0.91 | weekend | 2.89 | 4.07 |
| 2024-01-16 | 3.50 | 0.56 | weekday | 8.84 | -2.31 |
| 2024-12-21 | 2.30 | 0.56 | weekend | -9.20 | -8.14 |
| 2024-01-19 | 1.70 | 0.28 | weekday | 13.99 | 3.34 |
| 2024-01-07 | 1.10 | 0.84 | weekend | 23.52 | 7.27 |
| 2024-12-05 | 1.10 | 0.84 | weekday | -5.62 | -0.07 |


## E. Tốc độ theo nhiệt độ

| temp_bin | n | so_ngay | tb_tho | thay_doi_tho_pct | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct | ktc95_pct |
|---|---|---|---|---|---|---|---|
| 1. < 0 °C | 67,325 | 57 | 66.14 | 6.81 | 3.55 | -0.69 | 0.22 |
| 2. 0–10 °C | 228,777 | 173 | 62.25 | 0.52 | 1.53 | -1.16 | 0.12 |
| 3. 10–20 °C | 251,749 | 229 | 61.93 | 0.00 | -1.58 | -0.19 | 0.10 |
| 4. 20–30 °C | 224,407 | 179 | 57.76 | -6.73 | -1.96 | 0.25 | 0.11 |
| 5. ≥ 30 °C | 13,509 | 41 | 50.98 | -17.68 | -1.82 | -0.22 | 0.49 |


## F. Lưu lượng xe theo lượng mưa

Chỉ 5,844 giờ đếm có baseline đủ 5 giờ khô. Các điểm đếm chỉ hoạt động vài ngày, nên số trận mưa quan sát được rất ít, xem cột `so_ngay`.
| rain_bin | n | so_ngay | tb_tho | thay_doi_tho_pct | thay_doi_kiem_soat_pct | kiem_soat_them_thang_pct | ktc95_pct |
|---|---|---|---|---|---|---|---|
| 0. Không mưa | 5,327 | 149 | 484.10 | 0.00 | 0.00 | 0.00 | 0.46 |
| 1. 0–0,5 mm/h (rất nhẹ) | 263 | 45 | 330.14 | -31.80 | -0.16 | 0.98 | 2.04 |
| 2. 0,5–2 mm/h (nhẹ) | 161 | 27 | 386.56 | -20.15 | -1.89 | -1.29 | 2.60 |
| 3. 2–5 mm/h (vừa) | 61 | 17 | 383.10 | -20.86 | -3.80 | -1.19 | 4.01 |
| 4. > 5 mm/h (to) | 4 | 4 | 339.00 | -29.97 | -17.98 | 5.62 | 24.59 |


## G. Hệ số tương quan Pearson

| cap_bien | pearson |
|---|---|
| rainfall – avg_speed (từng bản ghi, thô) | -0.02 |
| rainfall – speed_idx (từng bản ghi, có kiểm soát) | -0.02 |
| rainfall – speed_idx (TB toàn thành phố mỗi giờ) | -0.07 |
| snowfall – speed_idx (TB toàn thành phố mỗi giờ) | 0.07 |
| temperature – speed_idx (TB toàn thành phố mỗi giờ) | -0.19 |


## H. 8 ngày mưa nhiều nhất

| date | mua_mm_ngay | mua_max_mm_h | day_type | thay_doi_toc_do_ca_ngay_pct | kiem_soat_them_thang_pct | n |
|---|---|---|---|---|---|---|
| 2024-03-23 | 64.00 | 13.90 | weekend | 2.77 | 1.13 | 2,356 |
| 2024-11-21 | 47.50 | 7.80 | weekday | -13.65 | -12.05 | 2,327 |
| 2024-12-11 | 39.20 | 4.90 | weekday | -9.23 | -3.33 | 1,591 |
| 2024-03-09 | 36.90 | 16.10 | weekend | -5.67 | -7.97 | 2,323 |
| 2024-08-06 | 36.40 | 20.30 | weekday | -1.55 | -1.99 | 2,292 |
| 2024-01-09 | 36.10 | 8.30 | weekday | 3.59 | -6.21 | 2,373 |
| 2024-03-06 | 34.90 | 11.40 | weekday | -4.20 | -6.47 | 2,305 |
| 2024-05-27 | 30.20 | 21.40 | weekend | 9.00 | 14.96 | 2,199 |

