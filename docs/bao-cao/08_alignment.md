# Báo cáo Schema Alignment (bước 08)

Sinh tự động lúc 2026-10-13 15:24.

## 1. Thử nghiệm schema matching tự động

| matcher | nguong | predicted | correct | ground_truth | precision | recall | f1 |
|---|---|---|---|---|---|---|---|
| name | 0.3 | 21 | 10 | 23 | 0.476 | 0.435 | 0.455 |
| name | 0.4 | 14 | 10 | 23 | 0.714 | 0.435 | 0.541 |
| name | 0.5 | 12 | 8 | 23 | 0.667 | 0.348 | 0.457 |
| name | 0.6 | 7 | 5 | 23 | 0.714 | 0.217 | 0.333 |
| name | 0.7 | 3 | 3 | 23 | 1.0 | 0.13 | 0.231 |
| name+synonym | 0.3 | 32 | 23 | 23 | 0.719 | 1.0 | 0.836 |
| name+synonym | 0.4 | 27 | 23 | 23 | 0.852 | 1.0 | 0.92 |
| name+synonym | 0.5 | 27 | 23 | 23 | 0.852 | 1.0 | 0.92 |
| name+synonym | 0.6 | 26 | 23 | 23 | 0.885 | 1.0 | 0.939 |
| name+synonym | 0.7 | 25 | 22 | 23 | 0.88 | 0.957 | 0.917 |

Kết quả chi tiết (ngưỡng 0,5) — chỉ dùng tên:

| cot_nguon | cot_dich | diem |
|---|---|---|
| speeds.id | road_id | 0.5 |
| speeds.speed | avg_speed | 0.556 |
| speeds.link_name | road_name | 0.556 |
| volume.street | district | 0.5 |
| weather.station_id | weather_station_id | 0.667 |
| weather.temperature_2m | temperature | 0.786 |
| weather.rain | rainfall | 0.5 |
| weather.snowfall | snowfall | 1.0 |
| weather.weather_code | weather_condition | 0.647 |
| weather.district | district | 1.0 |
| weather.grid_latitude | latitude | 0.615 |
| weather.grid_longitude | longitude | 0.643 |

## 2. Ánh xạ GAV

| target | speeds | volume | weather | note |
|---|---|---|---|---|
| road_id | concat('L', link_id) | concat('S', segmentid) nếu không nối được với link | — | Quyết định ở bước 09 (record linkage) |
| road_name | normalize(main_road(link_name)) | normalize(street) | — | Mở rộng viết tắt: BQE → BROOKLYN QUEENS EXPRESSWAY, AVE → AVENUE |
| district | normalize_district(borough) | normalize_district(boro) | district của trạm | 5 giá trị chuẩn |
| latitude / longitude | mean(link_points) | EPSG:2263→4326(wktgeom) | — | WGS84 |
| timestamp | date_trunc('hour', data_as_of) | make_timestamp(yr, m, d, hh) | time_local | Giờ New York, tròn giờ |
| avg_speed | AVG(speed) × 1.609344 theo (link, giờ) | — | — | chỉ status = 0 |
| vehicle_count | — | SUM(vol) theo (segment, giờ), mọi hướng | — | chỉ giờ có đủ 4 khung 15' ở mọi hướng |
| temperature | — | — | temperature_2m | °C |
| rainfall | — | — | rain | mm |
| snowfall | — | — | snowfall | cm |
| weather_condition | — | — | wmo_to_condition(weather_code) | 7 nhóm |
| weather_station_id | — | — | station_id |  |
| source | 'speeds' | 'volume' | — | 'speeds+volume' nếu đường được nối và cùng giờ có cả 2 |

## 3. Quy đổi về đường × giờ

| Nguồn | Vào | Ra |
|---|---|---|
| Tốc độ | 9,048,108 bản ghi (~5 phút) | 789,403 (link, giờ) |
| Lưu lượng | 94,824 khung 15' | 16,530 (đoạn, giờ) đầy đủ; loại 164 giờ thiếu khung/hướng |
| Thời tiết | 43,915 | 43,915 (trạm, giờ) |

## 4. Chuẩn hóa tên đường

- Nguồn tốc độ: 125 tuyến → 37 đường chính sau chuẩn hóa; 103 tuyến có tên đường viết tắt được mở rộng
- Nguồn lưu lượng: 104 đoạn → 85 tên phố; 8 đoạn có tên bị thay đổi khi chuẩn hóa

| link_name | main_road | direction | endpoints |
|---|---|---|---|
| LINCOLN TUNNEL E SOUTH TUBE - NJ - NY | LINCOLN TUNNEL | E | SOUTH TUBE; NJ; NY |
| LINCOLN TUNNEL E CENTER TUBE NJ - NY | LINCOLN TUNNEL | E | CENTER TUBE NJ; NY |
| MLK N WALKER STREET - NJ ROUTE 169 | MARTIN LUTHER KING EXPRESSWAY | N | WALKER STREET; NJ ROUTE 169 |
| LINCOLN TUNNEL W NORTH TUBE NY - NJ | LINCOLN TUNNEL | W | NORTH TUBE NY; NJ |
| LINCOLN TUNNEL W CENTER TUBE NY - NJ | LINCOLN TUNNEL | W | CENTER TUBE NY; NJ |
| CVE NB LIE - WILLETS PT BLVD | CLEARVIEW EXPRESSWAY | NB | LONG ISLAND EXPRESSWAY; WILLETS POINT BOULEVARD |
| LIE WB LITTLE NECK PKWY - NB CIP | LONG ISLAND EXPRESSWAY | WB | LITTLE NECK PARKWAY; NB CROSS ISLAND PARKWAY |
| CVE NB GCP - WILLETS PT BLVD | CLEARVIEW EXPRESSWAY | NB | GRAND CENTRAL PARKWAY; WILLETS POINT BOULEVARD |
| LIE WB LITTLE NECK PKWY - NB CVE | LONG ISLAND EXPRESSWAY | WB | LITTLE NECK PARKWAY; NB CLEARVIEW EXPRESSWAY |
| TNB S QNS ANCHORAGE - CIP S @ TNB | THROGS NECK BRIDGE | S | QUEENS ANCHORAGE; CROSS ISLAND PARKWAY S THROGS NECK BRIDGE |
| LIE E 84TH ST - 108TH ST | LONG ISLAND EXPRESSWAY | E | 84 STREET; 108 STREET |
| FDR N - TBB E 116TH STREET - MANHATTAN TRUSS | FDR DRIVE | N | TRIBOROUGH BRIDGE E 116 STREET; MANHATTAN TRUSS |

| street | main_road |
|---|---|
| F D R DRIVE | FDR DRIVE |
| UNION ST BRIDGE | UNION STREET BRIDGE |
| ST JAMES PLACE | SAINT JAMES PLACE |
| WILLIAMSBURG BR APPROACH | WILLIAMSBURG BRIDGE APPROACH |
| WILLIAMSBURG BR APPROACH | WILLIAMSBURG BRIDGE APPROACH |
| BROOKLYN QUEENS EXPWY ET 34 WB | BROOKLYN QUEENS EXPRESSWAY ET 34 WB |
| EAST 174 ST BRIDGE | EAST 174 STREET BRIDGE |
| CITY IS BRIDGE | CITY ISLAND BRIDGE |

Đường chính phổ biến (nguồn tốc độ): STATEN ISLAND EXPRESSWAY (12), WEST SHORE EXPRESSWAY (9), BROOKLYN QUEENS EXPRESSWAY (7), VAN WYCK EXPRESSWAY (7), GOWANUS EXPRESSWAY (6), CROSS BRONX EXPRESSWAY (6), BRUCKNER EXPRESSWAY (6), FDR DRIVE (6), MAJOR DEEGAN EXPRESSWAY (5), CROSS ISLAND PARKWAY (5), LINCOLN TUNNEL (4), BRONX WHITESTONE BRIDGE (4), LONG ISLAND EXPRESSWAY (4), TRIBOROUGH BRIDGE (4), BELT PARKWAY (3)
