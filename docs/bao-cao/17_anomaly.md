# Báo cáo bước 17 — Anomaly detection bằng Z-score

Sinh tự động lúc 2026-10-13 22:34 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.


## So sánh hai cách tính Z-score

Ngưỡng |z| > 3. Nếu dữ liệu phân phối chuẩn, tỉ lệ kỳ vọng là 0,27%. `trong_gio_cao_diem_pct`: % bất thường rơi vào 7–9h, 16–18h ngày thường.
| metric | phuong_phap | ban_ghi | duoc_cham_z | bat_thuong | ti_le_pct | thap_bat_thuong | cao_bat_thuong | trong_gio_cao_diem_pct |
|---|---|---|---|---|---|---|---|---|
| avg_speed | Toàn cục theo đường | 789,403 | 789,403 | 7,726 | 0.98 | 7,084 | 642 | 36.10 |
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 789,403 | 788,360 | 13,503 | 1.71 | 11,509 | 1,994 | 13.40 |
| vehicle_count | Toàn cục theo đường | 16,530 | 16,530 | 12 | 0.07 | 0 | 12 | 58.30 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 16,530 | 3,952 | 175 | 4.43 | 57 | 118 | 25.70 |


## 10 bất thường tốc độ (km/h) mạnh nhất

| road_id | road_name | district | timestamp | value | expected | z_score | weather_condition |
|---|---|---|---|---|---|---|---|
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 2024-06-23 21:00:00 | 7.49 | 96.96 | -30.37 | Cloudy |
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 2024-06-23 22:00:00 | 4.99 | 97.88 | -30.06 | Cloudy |
| L4616193 | STATEN ISLAND EXPRESSWAY | Staten Island | 2024-09-26 02:00:00 | 2.00 | 90.99 | -29.06 | Cloudy |
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 2024-06-22 23:00:00 | 5.49 | 99.11 | -26.82 | Clear |
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 2024-07-01 06:00:00 | 6.98 | 100.98 | -26.68 | Clear |
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 2024-06-29 07:00:00 | 6.48 | 102.66 | -26.63 | Cloudy |
| L4616193 | STATEN ISLAND EXPRESSWAY | Staten Island | 2024-09-26 01:00:00 | 2.50 | 90.72 | -25.64 | Cloudy |
| L4616267 | CROSS BRONX EXPRESSWAY | Bronx | 2024-02-17 00:00:00 | 5.49 | 86.71 | -22.45 | Snow |
| L4362342 | LONG ISLAND EXPRESSWAY | Queens | 2024-10-03 04:00:00 | 14.81 | 93.21 | -21.43 | Cloudy |
| L4616228 | I 87 NEW YORK STATE THRUWAY | Bronx | 2024-08-06 20:00:00 | 12.74 | 91.84 | -21.27 | Drizzle |


## 10 bất thường lưu lượng (xe/giờ) mạnh nhất

| road_id | road_name | district | timestamp | value | expected | z_score | weather_condition |
|---|---|---|---|---|---|---|---|
| S31005 | DEKALB AVENUE | Brooklyn | 2024-12-06 17:00:00 | 439.00 | 361.50 | 23.26 | Clear |
| S146686 | BOSTON ROAD | Bronx | 2024-03-19 07:00:00 | 973.00 | 672.88 | 13.17 | Clear |
| S256338 | COOPER AVENUE | Queens | 2024-04-26 02:00:00 | 88.00 | 38.44 | 10.01 | Clear |
| S48507 | DECATUR STREET | Brooklyn | 2024-04-17 08:00:00 | 315.00 | 152.38 | 10.01 | Cloudy |
| S22652 | UNION STREET BRIDGE | Brooklyn | 2024-06-01 16:00:00 | 389.00 | 232.50 | 7.76 | Clear |
| S105839 | 3 AVENUE | Brooklyn | 2024-04-05 01:00:00 | 204.00 | 83.25 | 7.54 | Cloudy |
| S22652 | UNION STREET BRIDGE | Brooklyn | 2024-05-31 00:00:00 | 102.00 | 47.89 | 6.92 | Cloudy |
| S31164 | MARCY AVENUE | Brooklyn | 2024-12-09 03:00:00 | 74.00 | 45.83 | 6.76 | Cloudy |
| S31005 | DEKALB AVENUE | Brooklyn | 2024-12-06 02:00:00 | 79.00 | 50.00 | 6.48 | Cloudy |
| S30999 | NOSTRAND AVENUE | Brooklyn | 2024-12-06 02:00:00 | 352.00 | 189.33 | 6.39 | Cloudy |


## Những ngày bất thường của cả thành phố (tốc độ)

**10 ngày có tỉ lệ CHẬM bất thường cao nhất**
| date | day_type | ban_ghi | cham_bat_thuong | nhanh_bat_thuong | ti_le_bat_thuong_pct | z_tb | mua_mm_ngay | tuyet_cm_ngay | do_phu_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2024-02-17 | weekend | 2,394 | 134 | 9 | 5.97 | -0.28 | 0.00 | 3.90 | 92.60 |
| 2024-01-29 | weekday | 876 | 45 | 1 | 5.25 | -0.34 | 1.70 | 0.00 | 34.50 |
| 2024-12-13 | weekday | 2,291 | 117 | 1 | 5.15 | -0.55 | 0.00 | 0.00 | 93.80 |
| 2024-01-01 | weekend | 2,325 | 110 | 55 | 7.10 | 0.42 | 0.10 | 0.00 | 92.30 |
| 2024-12-21 | weekend | 2,311 | 106 | 0 | 4.59 | -0.65 | 0.00 | 2.30 | 94.60 |
| 2024-10-05 | weekend | 2,317 | 105 | 2 | 4.62 | -0.39 | 0.30 | 0.00 | 92.90 |
| 2024-07-04 | weekend | 2,259 | 101 | 67 | 7.44 | 0.33 | 3.20 | 0.00 | 91.50 |
| 2024-07-07 | weekend | 2,237 | 96 | 6 | 4.56 | -0.09 | 0.40 | 0.00 | 90.60 |
| 2024-12-14 | weekend | 2,283 | 97 | 1 | 4.29 | -0.45 | 0.00 | 0.00 | 93.50 |
| 2024-06-19 | weekend | 2,332 | 97 | 12 | 4.67 | -0.29 | 0.00 | 0.00 | 94.60 |

**10 ngày có tỉ lệ NHANH bất thường cao nhất**
| date | day_type | ban_ghi | cham_bat_thuong | nhanh_bat_thuong | ti_le_bat_thuong_pct | z_tb | mua_mm_ngay | tuyet_cm_ngay | do_phu_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2024-02-13 | weekday | 2,346 | 45 | 207 | 10.74 | 0.75 | 0.90 | 16.00 | 90.50 |
| 2024-01-07 | weekend | 2,367 | 12 | 91 | 4.35 | 0.69 | 5.40 | 1.10 | 93.20 |
| 2024-07-04 | weekend | 2,259 | 101 | 67 | 7.44 | 0.33 | 3.20 | 0.00 | 91.50 |
| 2024-07-05 | weekday | 2,274 | 93 | 66 | 6.99 | 0.37 | 5.40 | 0.00 | 92.30 |
| 2024-01-01 | weekend | 2,325 | 110 | 55 | 7.10 | 0.42 | 0.10 | 0.00 | 92.30 |
| 2024-01-03 | weekday | 2,351 | 64 | 46 | 4.68 | 0.46 | 0.00 | 0.00 | 92.50 |
| 2024-01-02 | weekday | 2,319 | 86 | 39 | 5.39 | 0.38 | 0.00 | 0.00 | 91.50 |
| 2024-01-16 | weekday | 2,433 | 97 | 39 | 5.59 | -0.14 | 4.20 | 3.50 | 96.10 |
| 2024-01-06 | weekend | 2,375 | 12 | 38 | 2.11 | 0.45 | 7.60 | 4.00 | 93.60 |
| 2024-01-04 | weekday | 2,386 | 21 | 33 | 2.26 | 0.57 | 0.10 | 0.10 | 93.80 |


## 10 đường có nhiều bất thường tốc độ nhất

| road_id | road_name | district | so_bat_thuong | cham | z_min |
|---|---|---|---|---|---|
| L4616201 | WEST SHORE EXPRESSWAY | Staten Island | 363 | 363 | -6.04 |
| L4616225 | TRIBOROUGH BRIDGE | Queens | 246 | 246 | -9.68 |
| L4456478 | BRUCKNER EXPRESSWAY | Queens | 230 | 230 | -6.95 |
| L4456477 | MAJOR DEEGAN EXPRESSWAY | Queens | 224 | 224 | -7.20 |
| L4616192 | STATEN ISLAND EXPRESSWAY | Staten Island | 212 | 212 | -17.93 |
| L4456481 | TRIBOROUGH BRIDGE | Queens | 209 | 209 | -7.81 |
| L4616252 | BRONX RIVER PARKWAY | Bronx | 203 | 194 | -11.63 |
| L4362244 | CLEARVIEW EXPRESSWAY | Queens | 200 | 155 | -10.78 |
| L4616229 | BROOKLYN QUEENS EXPRESSWAY | Brooklyn | 198 | 198 | -10.04 |
| L4616253 | CROSS BRONX EXPRESSWAY | Bronx | 197 | 197 | -12.40 |

