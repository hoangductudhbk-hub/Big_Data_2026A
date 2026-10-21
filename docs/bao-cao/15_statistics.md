# Báo cáo bước 15 — Statistical analysis

Sinh tự động lúc 2026-10-13 16:25 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.


## Tổng quan

Bảng `integrated_traffic`: 805,780 dòng. Thống kê bỏ qua giá trị null: `avg_speed` chỉ có ở nguồn tốc độ, `vehicle_count` chỉ có ở nguồn lưu lượng.
| metric | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| avg_speed | 789,403 | 60.99 | 26.00 | 1.00 | 156.99 | 67.00 |
| vehicle_count | 16,530 | 527.34 | 702.27 | 0.00 | 7,266.00 | 300.00 |


## Theo giờ trong ngày (ngày thường / cuối tuần)

| hour | avg_speed_Cuối tuần | avg_speed_Ngày thường | vehicle_count_Cuối tuần | vehicle_count_Ngày thường |
|---|---|---|---|---|
| 0 | 67.20 | 69.80 | 343.70 | 281.20 |
| 1 | 70.50 | 72.80 | 259.00 | 177.90 |
| 2 | 72.70 | 75.70 | 202.90 | 124.80 |
| 3 | 74.60 | 78.30 | 172.50 | 110.90 |
| 4 | 76.50 | 79.80 | 165.50 | 165.10 |
| 5 | 78.60 | 75.30 | 161.80 | 320.60 |
| 6 | 78.30 | 62.50 | 214.60 | 553.40 |
| 7 | 75.90 | 55.60 | 304.50 | 752.60 |
| 8 | 72.20 | 52.40 | 392.50 | 757.50 |
| 9 | 68.30 | 53.80 | 472.10 | 696.90 |
| 10 | 63.90 | 54.30 | 539.90 | 668.20 |
| 11 | 59.40 | 54.70 | 581.60 | 676.00 |
| 12 | 56.90 | 55.50 | 626.50 | 694.70 |
| 13 | 54.80 | 54.80 | 648.10 | 729.10 |
| 14 | 53.10 | 51.30 | 665.10 | 782.70 |
| 15 | 52.00 | 46.60 | 682.20 | 812.30 |
| 16 | 51.30 | 44.10 | 673.20 | 822.80 |
| 17 | 50.80 | 44.20 | 652.90 | 823.80 |
| 18 | 52.30 | 48.40 | 633.80 | 775.10 |
| 19 | 54.90 | 56.60 | 589.60 | 697.70 |
| 20 | 57.40 | 62.50 | 540.80 | 620.20 |
| 21 | 60.80 | 65.50 | 475.50 | 545.50 |
| 22 | 63.90 | 65.90 | 419.80 | 481.60 |
| 23 | 67.30 | 66.30 | 364.40 | 409.40 |

Ngày thường: tốc độ thấp nhất lúc 16h (44.1 km/h), cao nhất lúc 4h (79.8 km/h). Lưu lượng cao nhất lúc 17h (824 xe/giờ).

## Theo thứ trong tuần

**avg_speed**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| 1-CN | 112,681 | 65.10 | 25.30 | 1.40 | 133.58 | 72.16 |
| 2-T2 | 115,183 | 62.23 | 25.71 | 2.00 | 156.50 | 68.74 |
| 3-T3 | 111,708 | 60.29 | 26.13 | 1.00 | 156.99 | 66.16 |
| 4-T4 | 110,511 | 59.32 | 26.26 | 1.66 | 156.99 | 64.99 |
| 5-T5 | 112,629 | 58.66 | 26.46 | 1.00 | 139.39 | 64.16 |
| 6-T6 | 113,176 | 58.92 | 26.18 | 1.00 | 149.99 | 64.07 |
| 7-T7 | 113,515 | 62.34 | 25.31 | 1.00 | 127.99 | 68.33 |

**vehicle_count**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| 1-CN | 2,515 | 430.93 | 524.23 | 0.00 | 4,095.00 | 245.00 |
| 2-T2 | 2,235 | 469.62 | 559.72 | 1.00 | 4,409.00 | 290.00 |
| 3-T3 | 2,397 | 612.88 | 891.98 | 0.00 | 7,266.00 | 327.00 |
| 4-T4 | 2,350 | 600.48 | 859.78 | 0.00 | 6,638.00 | 323.00 |
| 5-T5 | 2,267 | 615.62 | 846.53 | 0.00 | 6,307.00 | 321.00 |
| 6-T6 | 2,211 | 502.50 | 545.06 | 0.00 | 4,230.00 | 325.00 |
| 7-T7 | 2,555 | 468.39 | 541.55 | 0.00 | 4,263.00 | 279.00 |


## Theo tháng

**avg_speed**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| 2024-01 | 67,184 | 64.68 | 24.62 | 1.50 | 137.00 | 71.58 |
| 2024-02 | 40,113 | 61.86 | 25.56 | 1.90 | 133.37 | 69.16 |
| 2024-03 | 69,805 | 59.70 | 25.92 | 1.00 | 136.88 | 66.00 |
| 2024-04 | 68,596 | 60.41 | 25.87 | 1.00 | 139.99 | 67.34 |
| 2024-05 | 68,773 | 58.68 | 26.38 | 2.00 | 156.99 | 63.74 |
| 2024-06 | 70,026 | 59.64 | 26.58 | 1.00 | 156.99 | 65.07 |
| 2024-07 | 69,564 | 62.41 | 25.48 | 1.83 | 141.99 | 68.33 |
| 2024-08 | 67,381 | 61.61 | 25.27 | 1.00 | 136.24 | 66.83 |
| 2024-09 | 69,592 | 60.08 | 26.71 | 1.40 | 131.20 | 65.66 |
| 2024-10 | 71,173 | 61.20 | 26.43 | 1.00 | 134.24 | 66.66 |
| 2024-11 | 68,671 | 62.18 | 26.11 | 1.08 | 127.49 | 67.66 |
| 2024-12 | 58,525 | 59.71 | 26.23 | 1.67 | 154.99 | 64.33 |

**vehicle_count**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| 2024-01 | 1,536 | 219.81 | 174.59 | 2.00 | 824.00 | 172.50 |
| 2024-02 | 968 | 408.60 | 329.51 | 19.00 | 1,429.00 | 323.50 |
| 2024-03 | 3,156 | 659.38 | 1,014.33 | 0.00 | 7,266.00 | 358.50 |
| 2024-04 | 1,223 | 476.68 | 630.73 | 0.00 | 4,409.00 | 266.00 |
| 2024-05 | 2,218 | 477.56 | 652.30 | 9.00 | 4,451.00 | 272.00 |
| 2024-06 | 3,229 | 389.95 | 466.17 | 0.00 | 2,325.00 | 239.00 |
| 2024-09 | 576 | 348.19 | 391.78 | 0.00 | 1,359.00 | 183.50 |
| 2024-10 | 1,608 | 932.42 | 832.07 | 0.00 | 4,348.00 | 827.00 |
| 2024-11 | 1,152 | 878.46 | 754.95 | 0.00 | 2,551.00 | 741.00 |
| 2024-12 | 864 | 335.18 | 174.82 | 33.00 | 787.00 | 343.50 |


## Theo quận

**avg_speed**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| Bronx | 163,992 | 62.24 | 27.18 | 1.00 | 123.50 | 70.32 |
| Brooklyn | 52,394 | 54.85 | 25.08 | 2.99 | 94.24 | 63.33 |
| Manhattan | 138,419 | 40.49 | 19.94 | 1.00 | 156.99 | 40.91 |
| Queens | 293,324 | 62.17 | 23.11 | 1.00 | 139.99 | 69.16 |
| Staten Island | 141,274 | 79.44 | 20.42 | 1.00 | 110.74 | 86.24 |

**vehicle_count**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| Bronx | 1,896 | 496.89 | 359.02 | 11.00 | 1,668.00 | 447.50 |
| Brooklyn | 6,490 | 374.59 | 397.90 | 0.00 | 2,325.00 | 223.00 |
| Manhattan | 3,294 | 937.61 | 875.09 | 0.00 | 4,451.00 | 672.00 |
| Queens | 4,754 | 472.35 | 872.52 | 0.00 | 7,266.00 | 250.00 |
| Staten Island | 96 | 101.78 | 86.71 | 2.00 | 392.00 | 87.00 |


## Theo điều kiện thời tiết

**avg_speed**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| Clear | 354,102 | 61.62 | 26.22 | 1.00 | 156.99 | 67.91 |
| Cloudy | 317,289 | 61.21 | 26.09 | 1.00 | 156.99 | 67.49 |
| Drizzle | 83,924 | 58.35 | 25.42 | 1.00 | 136.24 | 63.58 |
| Rain | 23,442 | 57.53 | 24.26 | 1.50 | 110.17 | 62.99 |
| Snow | 10,646 | 61.98 | 22.03 | 1.75 | 104.08 | 67.41 |

**vehicle_count**
| group_key | n | mean | std | min | max | median |
|---|---|---|---|---|---|---|
| Clear | 7,485 | 526.26 | 634.79 | 0.00 | 7,266.00 | 294.00 |
| Cloudy | 6,677 | 540.44 | 754.27 | 0.00 | 7,242.00 | 312.00 |
| Drizzle | 1,658 | 513.00 | 776.69 | 0.00 | 5,509.00 | 298.00 |
| Rain | 549 | 500.98 | 759.03 | 0.00 | 6,307.00 | 294.00 |
| Snow | 161 | 272.20 | 253.28 | 2.00 | 2,268.00 | 230.00 |


## Theo đường

211 đường: 110 có dữ liệu tốc độ, 103 có lưu lượng. Chỉ xếp hạng tốc độ các đường có ≥ 1.000 giờ dữ liệu (109 đường).
**10 đường chậm nhất (tốc độ trung bình cả năm)**
| road_id | road_name | district | n_speed | mean_speed | std_speed |
|---|---|---|---|---|---|
| L4616337 | 11 AVENUE | Manhattan | 2,314 | 9.28 | 12.27 |
| L4616338 | 12 AVENUE | Manhattan | 2,272 | 9.85 | 15.08 |
| L4616340 | BROOKLYN QUEENS EXPRESSWAY | Manhattan | 6,735 | 11.04 | 6.06 |
| L4616357 | BELT PARKWAY | Queens | 7,807 | 17.07 | 8.22 |
| L4456494 | WEST STREET | Manhattan | 6,266 | 24.05 | 5.39 |
| L4616342 | BROOKLYN BRIDGE MANHATTAN SIDE | Manhattan | 7,952 | 24.92 | 12.13 |
| L4616324 | 12 AVENUE 45 | Manhattan | 1,900 | 25.54 | 9.21 |
| L4616223 | GOWANUS EXPRESSWAY | Brooklyn | 8,187 | 28.02 | 25.96 |
| L4329472 | LINCOLN TUNNEL | Manhattan | 5,056 | 28.55 | 11.91 |
| L4329508 | LINCOLN TUNNEL | Manhattan | 1,118 | 30.19 | 14.40 |

**10 đường nhanh nhất**
| road_id | road_name | district | n_speed | mean_speed | std_speed |
|---|---|---|---|---|---|
| L4616202 | WEST SHORE EXPRESSWAY | Staten Island | 5,477 | 95.05 | 16.41 |
| L4616212 | WEST SHORE EXPRESSWAY | Staten Island | 5,692 | 91.24 | 13.99 |
| L4616214 | WEST SHORE EXPRESSWAY | Staten Island | 5,686 | 91.21 | 12.72 |
| L4616213 | WEST SHORE EXPRESSWAY | Staten Island | 5,692 | 90.84 | 10.54 |
| L4616201 | WEST SHORE EXPRESSWAY | Staten Island | 5,679 | 88.20 | 21.59 |
| L4616246 | BRUCKNER EXPRESSWAY | Bronx | 8,201 | 87.88 | 7.79 |
| L4616199 | STATEN ISLAND EXPRESSWAY | Staten Island | 8,219 | 85.17 | 18.43 |
| L4362250 | CLEARVIEW EXPRESSWAY | Queens | 6,486 | 84.96 | 15.49 |
| L4616228 | I 87 NEW YORK STATE THRUWAY | Bronx | 7,909 | 83.80 | 22.26 |
| L4616250 | HUTCHINSON RIVER PARKWAY | Bronx | 7,362 | 83.30 | 22.54 |

**10 đường biến động tốc độ lớn nhất (độ lệch chuẩn)**: đường hay tắc theo giờ
| road_id | road_name | district | n_speed | mean_speed | std_speed |
|---|---|---|---|---|---|
| L4616267 | CROSS BRONX EXPRESSWAY | Bronx | 8,214 | 56.01 | 33.81 |
| L4616260 | BRUCKNER EXPRESSWAY | Bronx | 8,201 | 58.38 | 29.94 |
| L4620331 | CROSS BRONX EXPRESSWAY | Bronx | 8,010 | 43.80 | 27.57 |
| L4362342 | LONG ISLAND EXPRESSWAY | Queens | 8,198 | 58.18 | 26.27 |
| L4620332 | CROSS BRONX EXPRESSWAY | Bronx | 8,181 | 42.36 | 26.12 |
| L4616223 | GOWANUS EXPRESSWAY | Brooklyn | 8,187 | 28.02 | 25.96 |
| L4616364 | LONG ISLAND EXPRESSWAY | Queens | 8,202 | 58.06 | 25.63 |
| L4616309 | CROSS BRONX EXPRESSWAY | Bronx | 8,187 | 46.74 | 25.55 |
| L4616232 | BROOKLYN QUEENS EXPRESSWAY | Brooklyn | 2,721 | 57.09 | 25.00 |
| L4616310 | CROSS BRONX EXPRESSWAY AMSTERDAM AVENUE | Bronx | 8,188 | 45.81 | 24.82 |

**10 điểm đếm có lưu lượng trung bình cao nhất** (trong 102 đường có ≥ 24 giờ đếm)
| road_id | road_name | district | n_volume | mean_volume | max_volume |
|---|---|---|---|---|---|
| S9012153 | GRAND CENTRAL PARKWAY | Queens | 72 | 4,304.70 | 7,266.00 |
| S9012150 | GRAND CENTRAL PARKWAY | Queens | 72 | 4,304.30 | 6,118.00 |
| L4616332 | FDR DRIVE | Manhattan | 72 | 2,761.40 | 4,348.00 |
| S223885 | HENRY HUDSON PARKWAY | Manhattan | 168 | 2,647.30 | 4,451.00 |
| S66377 | BORDEN AVENUE | Queens | 96 | 2,298.90 | 3,432.00 |
| S252708 | WILLIAMSBURG BRIDGE APPROACH | Manhattan | 72 | 1,925.40 | 2,827.00 |
| S252704 | WILLIAMSBURG BRIDGE APPROACH | Manhattan | 72 | 1,740.70 | 2,515.00 |
| S71036 | MACOMBS DAM BRIDGE | Manhattan | 336 | 1,553.90 | 2,551.00 |
| S72887 | UNIVERSITY HEIGHTS BRIDGE | Manhattan | 336 | 1,509.20 | 2,188.00 |
| S28962 | FLATBUSH AVENUE | Brooklyn | 168 | 1,503.50 | 2,026.00 |


## Theo ngày

358 ngày có dữ liệu, 14 ngày bị đánh dấu mất dữ liệu (độ phủ < 50%, bước 07). Trên 344 ngày còn lại:
| chi_so | mean | std | min | max | ngay_cham_nhat | ngay_nhanh_nhat |
|---|---|---|---|---|---|---|
| Tốc độ TB của ngày (km/h) | 60.95 | 3.59 | 51.11 | 72.53 | 2024-12-11 | 2024-01-07 |

**5 ngày chậm nhất**
| date | mean_speed | n_speed | temperature | rain_mm_per_day | snow_cm_per_day |
|---|---|---|---|---|---|
| 2024-12-11 | 51.11 | 1,592 | 12.90 | 38.90 | 0.00 |
| 2024-03-28 | 52.92 | 2,354 | 8.20 | 24.90 | 0.00 |
| 2024-12-16 | 52.97 | 2,324 | 6.50 | 15.70 | 0.20 |
| 2024-05-15 | 53.26 | 2,176 | 15.40 | 8.90 | 0.00 |
| 2024-11-21 | 53.65 | 2,327 | 8.50 | 47.50 | 0.10 |


## Tự kiểm tra: Manhattan / avg_speed tính lại bằng pandas

| chi_so | pandas | spark | khop |
|---|---|---|---|
| n | 138,419.00 | 138,419.00 | True |
| mean | 40.49 | 40.49 | True |
| std | 19.94 | 19.94 | True |
| median | 40.91 | 40.91 | True |

