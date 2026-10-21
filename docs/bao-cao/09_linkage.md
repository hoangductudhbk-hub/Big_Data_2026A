# Báo cáo Record Linkage (bước 09)

Sinh tự động lúc 2026-10-13 15:34.

## A. Biến thể tên đường (373 tên của cả 2 nguồn, 69,378 cặp)

### Luật quyết định (so mọi cặp, đánh giá bằng nhãn kiểm tra tay)

| luat | so_cap_ghep | dung | precision | recall | cap_sai_vi_du |
|---|---|---|---|---|---|
| A: Levenshtein ≥ 0,8 (plan) | 336 | 5 | 0.015 | 1.0 | 1 AVENUE ~ 109 AVENUE; 1 AVENUE ~ 11 AVENUE; 1 AVENUE ~ 111 AVENUE; 1 AVENUE ~ 12 AVENUE |
| B: A + cùng số + cùng hướng/tầng | 13 | 5 | 0.385 | 1.0 | ARDEN AVENUE ~ BORDEN AVENUE; CATON AVENUE ~ WATSON AVENUE; COLLEGE POINT BOULEVARD ~ WILLETS POINT BOULEVARD; CROSS BRONX EXPRESSWAY AMSTERDAM AVENUE ~ CROSS BRONX EXPRESSWAY WL LE V AMSTERDAM AVENUE |
| C: B + OSA không khoảng trắng ≥ 0,88 | 6 | 5 | 0.833 | 1.0 | CROSS BRONX EXPRESSWAY WL LE V AMSTERDAM AVENUE ~ CROSS BRONX EXPRESSWAY WU LEV AMSTERDAM AVENUE |

### Blocking (với luật C)

| blocking | so_cap_so_sanh | reduction_ratio | pair_completeness | thoi_gian_ms | bo_lo |
|---|---|---|---|---|---|
| Không blocking (so mọi cặp) | 69378 | 0.0 | 1.0 | 1765.6 |  |
| Chữ cái đầu | 3258 | 0.953 | 1.0 | 104.8 |  |
| 2 chữ cái đầu | 985 | 0.9858 | 0.833 | 37.4 | WALKER STREET ~ WLAKER STREET |
| Chữ cái đầu + các con số | 2054 | 0.9704 | 1.0 | 101.7 |  |

### Cụm biến thể tìm được (luật C, blocking theo chữ cái đầu)

| ten_chuan | bien_the | so_bien_the |
|---|---|---|
| BLOOMUINGDALE ROAD | BLLOMINGDALE ROAD / BLOOMINGDALE ROAD / BLOOMUINGDALE ROAD | 3 |
| CROSS BRONX EXPRESSWAY WL LE V AMSTERDAM AVENUE | CROSS BRONX EXPRESSWAY WL LE V AMSTERDAM AVENUE / CROSS BRONX EXPRESSWAY WU LEV AMSTERDAM AVENUE | 2 |
| DE KALB AVENUE | DE KALB AVENUE / DEKALB AVENUE | 2 |
| WALKER STREET | WALKER STREET / WLAKER STREET | 2 |

## B. Nối đoạn đếm lưu lượng ↔ tuyến đo tốc độ

### Blocking

| cach | so_cap | reduction_ratio | pair_completeness | thoi_gian_s | so_cap_noi |
|---|---|---|---|---|---|
| Không blocking | 13000 | 0.0 | 1.0 | 1.12 | 2 |
| Blocking theo quận | 2444 | 0.812 | 1.0 | 0.26 | 2 |

### Kết quả so với nhãn

| predicted | true | correct | precision | recall |
|---|---|---|---|---|
| 2 | 2 | 2 | 1.0 | 1.0 |

### Các cặp đã nối

| segmentid | link_id | name_score | distance_m | rule | link_name | street |
|---|---|---|---|---|---|---|
| 66035 | 4616232 | 1.0 | 11.6 | direct | BQE S 46TH STREET - LEONARD STREET | BROOKLYN QUEENS EXPWY ET 34 WB |
| 136811 | 4616332 | 1.0 | 4.7 | direct | FDR S 63RD - 25TH ST | F D R DRIVE |
| 66035 | 4616235 | 1.0 | nan | twin (chiều ngược lại) | BQE N LEONARD STREET - 46TH STREET | BROOKLYN QUEENS EXPWY ET 34 WB |
| 136811 | 4616329 | 1.0 | nan | twin (chiều ngược lại) | FDR N 25TH - 63RD ST | F D R DRIVE |

## C. Bảng đường thống nhất (data/processed/roads.parquet)

| roads | speed_only | volume_only | both | by_district |
|---|---|---|---|---|
| 227 | 123 | 102 | 2 | {'Queens': 63, 'Brooklyn': 52, 'Manhattan': 49, 'Bronx': 36, 'Staten Island': 27} |
