# Báo cáo bước 17 — Anomaly detection bằng Z-score (mock)

Sinh tự động lúc 2026-10-14 05:33 · Spark 4.0.1 · local[*] (2 nhân) · dữ liệu `data/mock/integrated_traffic`.


## So sánh hai cách tính Z-score

Ngưỡng |z| > 3. Nếu dữ liệu phân phối chuẩn, tỉ lệ kỳ vọng là 0,27%. `trong_gio_cao_diem_pct`: % bất thường rơi vào 7–9h, 16–18h ngày thường.
| metric | phuong_phap | ban_ghi | duoc_cham_z | bat_thuong | ti_le_pct | thap_bat_thuong | cao_bat_thuong | trong_gio_cao_diem_pct |
|---|---|---|---|---|---|---|---|---|
| avg_speed | Toàn cục theo đường | 1,170,662 | 1,170,662 | 22 | 0.00 | 22 | 0 | 95.50 |
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 1,170,662 | 1,170,662 | 11,906 | 1.02 | 11,487 | 419 | 9.70 |
| vehicle_count | Toàn cục theo đường | 791,922 | 791,922 | 450 | 0.06 | 0 | 450 | 29.60 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 791,922 | 791,922 | 6,188 | 0.78 | 812 | 5,376 | 8.80 |


## Kiểm chứng trên mock: so với bất thường đã cài sẵn

| metric | phuong_phap | nguong | cai_san | bao | dung | precision | recall | f1 | bao_thua_luc_mua_tuyet_pct |
|---|---|---|---|---|---|---|---|---|---|
| avg_speed | Toàn cục theo đường | 3.00 | 1,205 | 22 | 22 | 1.00 | 0.02 | 0.04 | 0.00 |
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 3.00 | 1,205 | 11,906 | 1,175 | 0.10 | 0.97 | 0.18 | 95.10 |
| vehicle_count | Toàn cục theo đường | 3.00 | 746 | 450 | 450 | 1.00 | 0.60 | 0.75 | 0.00 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 3.00 | 746 | 6,188 | 746 | 0.12 | 1.00 | 0.21 | 17.30 |

`bao_thua_luc_mua_tuyet_pct`: trong các bản ghi bị báo nhưng KHÔNG phải bất thường cài sẵn, bao nhiêu % rơi vào giờ có mưa/tuyết (mock cố ý làm xe chậm khi mưa/tuyết, xem bước 04).
**Tăng ngưỡng |z| (cách theo ngữ cảnh):**
| metric | phuong_phap | nguong | cai_san | bao | dung | precision | recall | f1 | bao_thua_luc_mua_tuyet_pct |
|---|---|---|---|---|---|---|---|---|---|
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 3.00 | 1,205 | 11,906 | 1,175 | 0.10 | 0.97 | 0.18 | 95.10 |
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 4.00 | 1,205 | 2,094 | 1,125 | 0.54 | 0.93 | 0.68 | 98.30 |
| avg_speed | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 5.00 | 1,205 | 1,112 | 1,075 | 0.97 | 0.89 | 0.93 | 97.30 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 3.00 | 746 | 6,188 | 746 | 0.12 | 1.00 | 0.21 | 17.30 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 4.00 | 746 | 879 | 745 | 0.85 | 1.00 | 0.92 | 26.10 |
| vehicle_count | Theo ngữ cảnh, leave-one-out (đường × giờ × loại ngày) | 5.00 | 746 | 752 | 745 | 0.99 | 1.00 | 0.99 | 28.60 |


## 10 bất thường tốc độ (km/h) mạnh nhất

| road_id | road_name | district | timestamp | value | expected | z_score | weather_condition |
|---|---|---|---|---|---|---|---|
| L4000122 | 47 ROAD | Manhattan | 2024-10-22 13:00:00 | 7.06 | 31.04 | -10.45 | Rain |
| L4000129 | 37 STREET | Queens | 2024-05-07 12:00:00 | 7.21 | 44.88 | -10.29 | Thunderstorm |
| L4000076 | 145 STREET | Manhattan | 2024-10-25 14:00:00 | 8.41 | 39.93 | -10.24 | Clear |
| L4000009 | 38 AVENUE | Brooklyn | 2024-08-22 12:00:00 | 9.03 | 43.70 | -10.05 | Rain |
| L4000069 | 68 BOULEVARD | Brooklyn | 2024-04-24 15:00:00 | 12.18 | 49.49 | -10.03 | Clear |
| L4000171 | 112 AVENUE | Brooklyn | 2024-11-12 13:00:00 | 15.12 | 77.06 | -10.01 | Rain |
| L4000138 | 8 ROAD | Queens | 2024-12-23 20:00:00 | 12.48 | 55.62 | -9.83 | Rain |
| L4000188 | 157 EXPRESSWAY | Queens | 2024-01-29 21:00:00 | 6.63 | 34.48 | -9.79 | Snow |
| L4000120 | 121 ROAD | Queens | 2024-11-14 23:00:00 | 15.79 | 61.26 | -9.77 | Cloudy |
| L4000118 | 7 PARKWAY | Brooklyn | 2024-10-11 11:00:00 | 16.60 | 75.04 | -9.77 | Rain |


## 10 bất thường lưu lượng (xe/giờ) mạnh nhất

| road_id | road_name | district | timestamp | value | expected | z_score | weather_condition |
|---|---|---|---|---|---|---|---|
| L4000032 | 94 AVENUE | Brooklyn | 2024-01-10 17:00:00 | 12,449.00 | 3,529.21 | 139.15 | Cloudy |
| S4000167 | 74 BOULEVARD | Bronx | 2024-03-08 16:00:00 | 11,599.00 | 3,319.44 | 136.71 | Cloudy |
| S4000033 | 72 ROAD | Brooklyn | 2024-05-09 18:00:00 | 12,680.00 | 3,552.20 | 136.35 | Clear |
| L4000095 | 61 ROAD | Queens | 2024-08-21 09:00:00 | 10,682.00 | 3,014.32 | 134.90 | Cloudy |
| S4000117 | 23 PARKWAY | Queens | 2024-10-09 15:00:00 | 8,967.00 | 2,531.03 | 130.07 | Clear |
| S4000125 | 36 ROAD | Brooklyn | 2024-05-17 08:00:00 | 10,881.00 | 2,920.98 | 127.49 | Clear |
| S4000125 | 36 ROAD | Brooklyn | 2024-01-10 18:00:00 | 11,144.00 | 3,130.16 | 126.94 | Clear |
| S4000142 | 57 BOULEVARD | Staten Island | 2024-01-19 17:00:00 | 9,765.00 | 2,790.27 | 125.06 | Cloudy |
| S4000007 | 69 EXPRESSWAY | Queens | 2024-04-08 16:00:00 | 7,791.00 | 2,230.21 | 124.26 | Cloudy |
| L4000119 | 9 STREET | Queens | 2024-12-02 18:00:00 | 11,466.00 | 3,287.72 | 123.87 | Clear |


## Những ngày bất thường của cả thành phố (tốc độ)

**10 ngày có tỉ lệ CHẬM bất thường cao nhất**
| date | day_type | ban_ghi | cham_bat_thuong | nhanh_bat_thuong | ti_le_bat_thuong_pct | z_tb | mua_mm_ngay | tuyet_cm_ngay |
|---|---|---|---|---|---|---|---|---|
| 2024-01-15 | weekend | 3,188 | 388 | 0 | 12.17 | -1.47 | 5.70 | 7.90 |
| 2024-01-01 | weekend | 3,189 | 305 | 0 | 9.56 | -1.39 | 8.50 | 4.20 |
| 2024-01-22 | weekday | 3,198 | 255 | 0 | 7.97 | -0.62 | 0.80 | 8.90 |
| 2024-12-19 | weekday | 3,204 | 208 | 4 | 6.62 | -0.54 | 10.10 | 4.30 |
| 2024-02-01 | weekday | 3,203 | 199 | 2 | 6.28 | -0.38 | 0.90 | 6.80 |
| 2024-12-28 | weekend | 3,192 | 188 | 0 | 5.89 | -0.53 | 10.70 | 8.10 |
| 2024-01-28 | weekend | 3,199 | 188 | 1 | 5.91 | -0.27 | 3.80 | 5.80 |
| 2024-02-12 | weekday | 3,188 | 185 | 1 | 5.83 | -0.40 | 4.60 | 4.40 |
| 2024-02-14 | weekday | 3,209 | 178 | 2 | 5.61 | -0.29 | 2.00 | 6.20 |
| 2024-02-08 | weekday | 3,198 | 175 | 0 | 5.47 | -0.47 | 6.00 | 6.50 |

**10 ngày có tỉ lệ NHANH bất thường cao nhất**
| date | day_type | ban_ghi | cham_bat_thuong | nhanh_bat_thuong | ti_le_bat_thuong_pct | z_tb | mua_mm_ngay | tuyet_cm_ngay |
|---|---|---|---|---|---|---|---|---|
| 2024-05-02 | weekday | 3,190 | 9 | 6 | 0.47 | 0.21 | 0.90 | 0.00 |
| 2024-12-06 | weekday | 3,193 | 52 | 5 | 1.79 | -0.07 | 5.70 | 1.80 |
| 2024-01-09 | weekday | 3,196 | 67 | 5 | 2.25 | 0.14 | 0.00 | 1.20 |
| 2024-02-29 | weekday | 3,205 | 16 | 5 | 0.66 | 0.21 | 0.00 | 0.30 |
| 2024-06-11 | weekday | 3,189 | 10 | 4 | 0.44 | 0.07 | 7.20 | 0.00 |
| 2024-07-16 | weekday | 3,191 | 5 | 4 | 0.28 | 0.06 | 6.30 | 0.00 |
| 2024-08-09 | weekday | 3,191 | 6 | 4 | 0.31 | 0.17 | 1.60 | 0.00 |
| 2024-03-22 | weekday | 3,194 | 7 | 4 | 0.34 | 0.07 | 3.50 | 0.20 |
| 2024-09-18 | weekday | 3,194 | 1 | 4 | 0.16 | 0.26 | 0.10 | 0.00 |
| 2024-05-01 | weekday | 3,198 | 19 | 4 | 0.72 | -0.06 | 9.90 | 0.00 |


## 10 đường có nhiều bất thường tốc độ nhất

| road_id | road_name | district | so_bat_thuong | cham | z_min |
|---|---|---|---|---|---|
| L4000165 | 29 PARKWAY | Brooklyn | 110 | 102 | -8.82 |
| L4000009 | 38 AVENUE | Brooklyn | 104 | 101 | -10.05 |
| L4000183 | 56 STREET | Brooklyn | 103 | 99 | -8.92 |
| L4000030 | 131 BOULEVARD | Queens | 103 | 103 | -8.72 |
| L4000134 | 107 EXPRESSWAY | Queens | 103 | 99 | -8.18 |
| L4000067 | 101 BOULEVARD | Brooklyn | 102 | 100 | -9.51 |
| L4000001 | 83 EXPRESSWAY | Brooklyn | 101 | 100 | -9.61 |
| L4000051 | 172 PARKWAY | Manhattan | 100 | 97 | -9.10 |
| L4000062 | 70 EXPRESSWAY | Queens | 98 | 95 | -8.62 |
| L4000034 | 53 STREET | Brooklyn | 98 | 94 | -9.60 |

