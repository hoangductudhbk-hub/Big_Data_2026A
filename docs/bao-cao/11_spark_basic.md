# Báo cáo bước 11 — PySpark cơ bản

Sinh tự động lúc 2026-10-13 16:01 · Spark 3.5.3 · local[*] (2 nhân) · dữ liệu `data/processed/integrated_traffic`.

## 1. Lazy evaluation

Khai báo filter → withColumn → groupBy (transformation): **149.7 ms** — Spark chỉ dựng kế hoạch.
Gọi `collect()` (action): **2.62 s** — lúc này Spark mới đọc dữ liệu và tính.

## 2. select + filter

BQE, 7–9h ngày thường: 3,951 / 805,780 dòng sau filter.
| toc_do_tb_kmh | so_tuyen |
|---|---|
| 40.40 | 7 |

Filter trên cột của Parquet được đẩy xuống lớp đọc file (`PushedFilters` trong plan):
```text
+- FileScan parquet [road_id#0,road_name#1,timestamp#5,avg_speed#7,weather_condition#11,year#14,month#15] Batched: true, DataFilters: [isnotnull(road_name#1), isnotnull(timestamp#5), StartsWith(road_name#1, BROOKLYN QUEENS EXPRESSW..., Format: Parquet, Location: InMemoryFileIndex(1 paths)[file:/sessions/rcw-014rjtz4khfbd6tgazz8jblb/mnt/BigData/Big_Data_2026A..., PartitionFilters: [], PushedFilters: [IsNotNull(road_name), IsNotNull(timestamp), StringStartsWith(road_name,BROOKLYN QUEENS EXPRESSWA..., ReadSchema: struct<road_id:string,road_name:string,timestamp:timestamp_ntz,avg_speed:double,weather_condition...
```


## 3. join (9.048.108 bản ghi tốc độ ⨝ 125 tuyến)

| district | so_ban_ghi | toc_do_tb_kmh |
|---|---|---|
| Bronx | 1,910,929 | 62.10 |
| Brooklyn | 622,966 | 54.80 |
| Manhattan | 1,468,656 | 40.80 |
| Queens | 3,368,987 | 62.40 |
| Staten Island | 1,676,570 | 79.60 |

| Chiến lược | Plan | Lần đầu | Tốt nhất / 3 lần |
|---|---|---|---|
| Broadcast (mặc định: bảng nhỏ < 10 MB) | BroadcastHashJoin | 1.68 s | 1.27 s |
| Sort-merge (tắt broadcast) | SortMergeJoin | 5.63 s | 4.19 s |

## 4. groupBy + aggregation: hồ sơ theo giờ

| loai_ngay | hour | toc_do_tb_kmh | luu_luong_tb | n_toc_do | n_luu_luong |
|---|---|---|---|---|---|
| cuối tuần | 3 | 74.60 | 173.00 | 8,785 | 210 |
| cuối tuần | 6 | 78.30 | 215.00 | 9,290 | 209 |
| cuối tuần | 8 | 72.20 | 393.00 | 9,542 | 211 |
| cuối tuần | 12 | 56.90 | 627.00 | 9,572 | 212 |
| cuối tuần | 17 | 50.80 | 653.00 | 9,709 | 211 |
| cuối tuần | 20 | 57.40 | 541.00 | 9,583 | 212 |
| cuối tuần | 23 | 67.30 | 364.00 | 9,353 | 210 |
| ngày thường | 3 | 78.30 | 111.00 | 20,850 | 478 |
| ngày thường | 6 | 62.50 | 553.00 | 23,755 | 477 |
| ngày thường | 8 | 52.40 | 758.00 | 24,041 | 475 |
| ngày thường | 12 | 55.50 | 695.00 | 24,236 | 478 |
| ngày thường | 17 | 44.20 | 824.00 | 24,181 | 478 |
| ngày thường | 20 | 62.50 | 620.00 | 23,851 | 478 |
| ngày thường | 23 | 66.30 | 409.00 | 23,391 | 478 |


## 5. sort: 10 tuyến chậm nhất giờ cao điểm chiều

| road_id | road_name | district | toc_do_tb_kmh | so_gio |
|---|---|---|---|---|
| L4616337 | 11 AVENUE | Manhattan | 5.30 | 204 |
| L4616338 | 12 AVENUE | Manhattan | 5.40 | 203 |
| L4616340 | BROOKLYN QUEENS EXPRESSWAY | Manhattan | 6.80 | 735 |
| L4616223 | GOWANUS EXPRESSWAY | Brooklyn | 8.80 | 738 |
| L4620314 | MAJOR DEEGAN EXPRESSWAY | Bronx | 12.00 | 736 |
| L4616357 | BELT PARKWAY | Queens | 12.10 | 711 |
| L4616271 | BROOKLYN QUEENS EXPRESSWAY | Brooklyn | 13.60 | 641 |
| L4620330 | MAJOR DEEGAN EXPRESSWAY | Bronx | 13.80 | 737 |
| L4620332 | CROSS BRONX EXPRESSWAY | Bronx | 15.70 | 737 |
| L4620331 | CROSS BRONX EXPRESSWAY | Bronx | 15.90 | 722 |


## 6. Spark SQL

Truy vấn bước 4 viết bằng SQL cho kết quả **trùng khớp** với DataFrame API (48 dòng) — cả hai cùng đi qua bộ tối ưu Catalyst.

## 7. cache

| Truy vấn: đếm bản ghi < 30 km/h theo tuyến | Thời gian (tốt nhất / 3 lần, DataFrame dựng mới mỗi lần) |
|---|---|
| Không cache (mỗi lần đọc lại Parquet và lọc) | 0.52 s |
| Phần đã lọc được cache trong bộ nhớ | 0.18 s |
