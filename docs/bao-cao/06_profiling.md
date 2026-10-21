# Báo cáo Data Profiling (bước 06)

Sinh tự động bởi `python -m data_integration.profiling.run` lúc 2026-10-13 15:08.
Phạm vi: 2024-01-01 → 2024-12-31.

| Nguồn | File | Số dòng | Thời gian chạy |
|---|---|---|---|
| Nguồn 3 — Thời tiết (Open-Meteo) | open_meteo_2024-01-01_2024-12-31.csv | 43,920 | 0.4s |
| Nguồn 2 — Lưu lượng (Automated Traffic Volume Counts) | volume_2024.csv | 95,203 | 1.4s |
| Nguồn 1 — Tốc độ (DOT Traffic Speeds) | speeds_2024-01.csv, speeds_2024-02.csv, speeds_2024-03.csv, … | 11,970,346 | 32.8s |

## Nguồn 3 — Thời tiết (Open-Meteo)

### Kiểm tra chất lượng

| Kiểm tra | Số bản ghi | Tỉ lệ | Ghi chú |
|---|---|---|---|
| Số giờ của OM_BRONX | 8,784 |  | kỳ vọng 8,784 |
| Số giờ của OM_BROOKLYN | 8,784 |  | kỳ vọng 8,784 |
| Số giờ của OM_MANHATTAN | 8,784 |  | kỳ vọng 8,784 |
| Số giờ của OM_QUEENS | 8,784 |  | kỳ vọng 8,784 |
| Số giờ của OM_STATEN_ISLAND | 8,784 |  | kỳ vọng 8,784 |
| time_utc không đọc được | 0 | 0.000% |  |
| Trùng (station, time_utc) | 0 | 0.000% |  |
| Trùng (station, time_local) | 10 | 0.023% | Do lùi giờ mùa đông: 01:00 xuất hiện 2 lần (2024-11-03 01:00) |
| Giờ địa phương nằm ngoài phạm vi nghiên cứu | 0 | 0.000% | phạm vi 2024-01-01 00:00 → 2024-12-31 23:00 |
| Giờ địa phương bị thiếu (tính cả 5 trạm) | 5 |  | Ngày đổi giờ 10/03 không có 02:00 nên mỗi trạm thiếu 1 giờ là bình thường |
| Khoảng trống giữa 2 giờ liên tiếp (theo UTC) | 0 | 0.000% |  |
| temperature_2m rỗng/không phải số | 0 | 0.000% |  |
| precipitation rỗng/không phải số | 0 | 0.000% |  |
| rain rỗng/không phải số | 0 | 0.000% |  |
| snowfall rỗng/không phải số | 0 | 0.000% |  |
| weather_code rỗng/không phải số | 0 | 0.000% |  |
| temperature_2m ngoài [-40, 50] °C | 0 | 0.000% |  |
| Lượng mưa/tuyết âm | 0 | 0.000% |  |
| rain > precipitation (mâu thuẫn) | 0 | 0.000% | precipitation = rain + showers + tuyết quy ra nước |

### Mô tả từng cột

| Cột | Rỗng | % rỗng | Distinct | % là số | Min | Median | Max | Giá trị phổ biến |
|---|---|---|---|---|---|---|---|---|
| `station_id` | 0 | 0.00 | 5 | 0.0 |  |  |  | `OM_MANHATTAN` (8,784), `OM_BROOKLYN` (8,784), `OM_QUEENS` (8,784) |
| `time_utc` | 0 | 0.00 | 8,784 | 0.0 |  |  |  | `2024-12-31 12:00:00` (5), `2024-12-31 11:00:00` (5), `2024-12-31 10:00:00` (5) |
| `time_local` | 0 | 0.00 | 8,783 | 0.0 |  |  |  | `2024-11-03 01:00:00` (10), `2024-08-31 19:00:00` (5), `2024-08-31 20:00:00` (5) |
| `temperature_2m` | 0 | 0.00 | 497 | 100.0 | -14.50 | 13.30 | 36.30 | `8.5` (190), `9.7` (188), `22.4` (187) |
| `precipitation` | 0 | 0.00 | 126 | 100.0 | 0.00 | 0.00 | 21.40 | `0.0` (37,483), `0.1` (1,722), `0.2` (910) |
| `rain` | 0 | 0.00 | 126 | 100.0 | 0.00 | 0.00 | 21.40 | `0.0` (37,880), `0.1` (1,625), `0.2` (862) |
| `snowfall` | 0 | 0.00 | 34 | 100.0 | 0.00 | 0.00 | 2.87 | `0.0` (43,376), `0.07` (165), `0.14` (82) |
| `weather_code` | 0 | 0.00 | 13 | 100.0 | 0.00 | 2.00 | 75.00 | `0` (15,570), `3` (14,718), `1` (4,167) |
| `district` | 0 | 0.00 | 5 | 0.0 |  |  |  | `Manhattan` (8,784), `Brooklyn` (8,784), `Queens` (8,784) |
| `grid_latitude` | 0 | 0.00 | 5 | 100.0 | 40.60 | 40.74 | 40.88 | `40.808434` (8,784), `40.667835` (8,784), `40.738136` (8,784) |
| `grid_longitude` | 0 | 0.00 | 5 | 100.0 | -74.09 | -73.94 | -73.79 | `-74.0199` (8,784), `-73.93768` (8,784), `-73.78723` (8,784) |

### Phân bố nhóm thời tiết (sau khi map mã WMO)

| condition | so_gio | ma_wmo | ti_le_% |
|---|---|---|---|
| Clear | 19,737 | 0,1 | 44.94 |
| Cloudy | 17,746 | 2,3 | 40.41 |
| Drizzle | 4,638 | 51,53,55 | 10.56 |
| Rain | 1,255 | 61,63,65 | 2.86 |
| Snow | 544 | 71,73,75 | 1.24 |

### Khí hậu theo tháng (trung bình 5 quận)

| month | nhiet_do_tb | mua_mm | tuyet_cm |
|---|---|---|---|
| 2024-01 | 1.50 | 149.10 | 12.00 |
| 2024-02 | 2.20 | 32.80 | 22.60 |
| 2024-03 | 7.00 | 219.90 | 0.10 |
| 2024-04 | 10.50 | 112.80 | 0.10 |
| 2024-05 | 16.70 | 96.50 | 0.00 |
| 2024-06 | 22.80 | 84.00 | 0.00 |
| 2024-07 | 25.20 | 103.70 | 0.00 |
| 2024-08 | 23.20 | 165.00 | 0.00 |
| 2024-09 | 19.60 | 27.10 | 0.00 |
| 2024-10 | 14.90 | 7.10 | 0.00 |
| 2024-11 | 10.10 | 86.10 | 0.50 |
| 2024-12 | 2.20 | 98.90 | 5.90 |

## Nguồn 2 — Lưu lượng (Automated Traffic Volume Counts)

### Kiểm tra chất lượng

| Kiểm tra | Số bản ghi | Tỉ lệ | Ghi chú |
|---|---|---|---|
| Thời gian (yr,m,d,hh,mm) không hợp lệ | 0 | 0.000% |  |
| Phút không thuộc {0,15,30,45} | 0 | 0.000% |  |
| Giờ ngoài 0–23 | 0 | 0.000% |  |
| vol rỗng/không phải số | 0 | 0.000% |  |
| vol âm | 0 | 0.000% |  |
| vol = 0 | 1,292 | 1.357% | Có thể hợp lệ (ban đêm, đường nhỏ) |
| vol ngoại lai mạnh (ngoài Q1−3·IQR … Q3+3·IQR) | 2,390 | 2.510% | ngưỡng trên ≈ 394 xe/15 phút |
| Trùng toàn bộ dòng | 0 | 0.000% |  |
| Trùng khóa (segmentid, direction, thời gian) | 379 | 0.398% |  |
| …trong đó khác giá trị vol (mâu thuẫn) | 379 | 0.398% | Nhiều đợt khảo sát (requestid) đo cùng đoạn, cùng lúc |
| boro rỗng | 0 | 0.000% |  |
| street rỗng | 0 | 0.000% |  |
| segmentid rỗng | 0 | 0.000% |  |
| wktgeom rỗng | 0 | 0.000% |  |
| direction rỗng | 0 | 0.000% |  |
| wktgeom không đọc được dạng POINT(x y) | 0 | 0.000% |  |
| Tọa độ (sau khi đổi EPSG:2263 → WGS84) nằm ngoài New York | 0 | 0.000% |  |
| street: cùng tên nhưng khác chữ hoa/thường | 0 |  | số tên có từ 2 cách viết trở lên, ví dụ 'Dead End' / 'Dead end' |
| fromst: cùng tên nhưng khác chữ hoa/thường | 1 |  | số tên có từ 2 cách viết trở lên, ví dụ 'Dead End' / 'Dead end' |
| tost: cùng tên nhưng khác chữ hoa/thường | 1 |  | số tên có từ 2 cách viết trở lên, ví dụ 'Dead End' / 'Dead end' |
| segmentid có nhiều hơn 1 tọa độ | 1 |  |  |
| Khung 15 phút bị thiếu bên trong các đợt đếm | 980 | 1.023% | so với số khung kỳ vọng từ lúc bắt đầu đến lúc kết thúc mỗi đợt |

### Mô tả từng cột

| Cột | Rỗng | % rỗng | Distinct | % là số | Min | Median | Max | Giá trị phổ biến |
|---|---|---|---|---|---|---|---|---|
| `requestid` | 0 | 0.00 | 38 | 100.0 | 36,741.00 | 37,574.00 | 38,782.00 | `37574` (17,084), `38108` (10,560), `36741` (10,535) |
| `boro` | 0 | 0.00 | 5 | 0.0 |  |  |  | `Brooklyn` (33,663), `Queens` (27,465), `Manhattan` (21,772) |
| `yr` | 0 | 0.00 | 1 | 100.0 | 2,024.00 | 2,024.00 | 2,024.00 | `2024` (95,203) |
| `m` | 0 | 0.00 | 10 | 100.0 | 1.00 | 5.00 | 12.00 | `3` (17,978), `6` (14,943), `5` (12,757) |
| `d` | 0 | 0.00 | 31 | 100.0 | 1.00 | 14.00 | 31.00 | `9` (4,896), `10` (4,896), `8` (4,704) |
| `hh` | 0 | 0.00 | 24 | 100.0 | 0.00 | 12.00 | 23.00 | `7` (3,972), `13` (3,968), `20` (3,968) |
| `mm` | 0 | 0.00 | 4 | 100.0 | 0.00 | 15.00 | 45.00 | `30` (23,804), `0` (23,802), `15` (23,801) |
| `vol` | 0 | 0.00 | 1,394 | 100.0 | 0.00 | 57.00 | 2,187.00 | `0` (1,292), `5` (1,271), `6` (1,238) |
| `segmentid` | 0 | 0.00 | 104 | 100.0 | 21,327.00 | 76,594.00 | 9,014,587 | `9000515` (2,688), `57162` (2,688), `71036` (2,688) |
| `wktgeom` | 0 | 0.00 | 105 | 0.0 |  |  |  | `POINT (1041074.973834683 ` (2,688), `POINT (1038800.1226020441` (2,688), `POINT (1007807.3102189016` (2,688) |
| `street` | 0 | 0.00 | 85 | 0.0 |  |  |  | `LINDEN BOULEVARD` (4,416), `NORTHERN BOULEVARD` (3,072), `160 STREET` (2,688) |
| `fromst` | 0 | 0.00 | 86 | 0.0 |  |  |  | `Dead End` (9,866), `Harlem River Shoreline` (5,376), `14 Street/canarsie Line` (4,222) |
| `tost` | 0 | 0.00 | 78 | 0.0 |  |  |  | `Dead end` (15,154), `Harlem River Shoreline` (6,624), `Dead End` (2,892) |
| `direction` | 0 | 0.00 | 4 | 0.0 |  |  |  | `NB` (25,705), `SB` (24,095), `EB` (23,610) |

### Phạm vi bao phủ

| chi_so | gia_tri |
|---|---|
| Số đợt khảo sát (requestid) | 38 |
| Số đoạn đường (segmentid) | 104 |
| Số tên phố (street) | 85 |
| Số ngày trung bình mỗi đợt | 7.00 |
| Ngày sớm nhất | 2024-01-06 00:00:00 |
| Ngày muộn nhất | 2024-12-11 23:45:00 |

### Số dòng theo quận (giá trị gốc của cột boro)

| boro | so_dong |
|---|---|
| Brooklyn | 33,663 |
| Queens | 27,465 |
| Manhattan | 21,772 |
| Bronx | 11,919 |
| Staten Island | 384 |

### Số dòng theo tháng

| thang | so_dong |
|---|---|
| 2024-01 | 9,888 |
| 2024-02 | 6,606 |
| 2024-03 | 17,978 |
| 2024-04 | 7,111 |
| 2024-05 | 12,757 |
| 2024-06 | 14,943 |
| 2024-09 | 4,608 |
| 2024-10 | 9,216 |
| 2024-11 | 8,640 |
| 2024-12 | 3,456 |

### Cách viết hậu tố tên phố không thống nhất (cột street)

| chuan | cach_viet_gap | so_kieu_viet |
|---|---|---|
| AVENUE | AVENUE (36954) | 1 |
| STREET | STREET (16703) | 1 |
| BOULEVARD | BOULEVARD (13612) | 1 |
| PLACE | PLACE (384) | 1 |
| ROAD | ROAD (4318) | 1 |
| PARKWAY | PARKWAY (2299) | 1 |

## Nguồn 1 — Tốc độ (DOT Traffic Speeds)

### Kiểm tra chất lượng

| Kiểm tra | Số bản ghi | Tỉ lệ | Ghi chú |
|---|---|---|---|
| speed rỗng/không phải số | 0 | 0.000% |  |
| speed âm | 0 | 0.000% |  |
| speed = 0 và travel_time = 0 (bản ghi rỗng) | 2,415,175 | 20.176% |  |
| status khác 0 | 2,922,227 | 24.412% |  |
| speed > 100 mph (bất hợp lý) | 87 | 0.001% |  |
| data_as_of không đọc được | 0 | 0.000% |  |
| data_as_of nằm ngoài tháng của file | 0 | 0.000% |  |
| Trùng toàn bộ dòng | 0 | 0.000% |  |
| Trùng khóa (link_id, data_as_of) | 0 | 0.000% |  |
| link_id không có trong links.csv | 1 | 0.000% |  |
| link_name khác với tên trong links.csv | 0 | 0.000% |  |
| Số ngày có độ phủ giờ < 50% | 22 | 6.011% |  |

### Theo tháng

| thang | so_dong | so_tuyen | khong_hop_le | ti_le_khong_hop_le_% | trung_khoa | do_phu_gio_% |
|---|---|---|---|---|---|---|
| 2024-01 | 996,717 | 122 | 218,821 | 21.95 | 0 | 85.20 |
| 2024-02 | 606,855 | 123 | 144,873 | 23.87 | 0 | 53.40 |
| 2024-03 | 1,054,554 | 123 | 253,630 | 24.05 | 0 | 91.10 |
| 2024-04 | 1,056,771 | 123 | 267,372 | 25.30 | 0 | 92.50 |
| 2024-05 | 1,082,408 | 125 | 295,473 | 27.30 | 0 | 88.00 |
| 2024-06 | 1,041,105 | 121 | 238,827 | 22.94 | 0 | 94.40 |
| 2024-07 | 1,052,885 | 121 | 254,390 | 24.16 | 0 | 90.80 |
| 2024-08 | 1,007,758 | 122 | 234,837 | 23.30 | 0 | 87.10 |
| 2024-09 | 1,052,806 | 122 | 262,237 | 24.91 | 0 | 92.90 |
| 2024-10 | 1,088,596 | 122 | 275,013 | 25.26 | 0 | 92.00 |
| 2024-11 | 1,053,440 | 122 | 265,921 | 25.24 | 0 | 93.50 |
| 2024-12 | 876,451 | 122 | 210,833 | 24.06 | 0 | 77.10 |

### Chỉ số tổng hợp

| chi_so | gia_tri |
|---|---|
| Tốc độ hợp lệ: trung vị (mph) | 42.9 |
| Tốc độ hợp lệ: p01 – p99 (mph) | 3.7 – 63.4 |
| Khoảng cách giữa 2 lần đo: trung vị (phút) | 5.0 |
| Khoảng cách: p90 (phút) | 5.0 |
| Khoảng cách: lớn nhất trong mẫu (giờ) | 455.9 |
| Số tuyến (link_id) xuất hiện | 125 |
| Số bản ghi mỗi tuyến: ít nhất – nhiều nhất | 1 – 98,347 |

### Phân bố status

| status | so_dong |
|---|---|
| 0 | 9,048,119 |
| -101 | 2,922,227 |

### Phân bố borough (giá trị gốc)

| borough | so_dong |
|---|---|
| Queens | 3,633,555 |
| Manhattan | 2,553,858 |
| Staten Island | 2,457,480 |
| Bronx | 2,290,870 |
| Brooklyn | 1,034,583 |

### Đối chiếu status với bản ghi rỗng (speed = 0 và travel_time = 0)

| status | speed=0 & travel_time=0 | so_dong |
|---|---|---|
| -101 | không | 507,052 |
| -101 | có | 2,415,175 |
| 0 | không | 9,048,119 |

### Các khoảng ngày bị mất dữ liệu (độ phủ giờ < 50%)

| tu_ngay | den_ngay | so_ngay | do_phu_tb_% |
|---|---|---|---|
| 2024-01-29 | 2024-02-12 | 15 | 5.10 |
| 2024-03-12 | 2024-03-12 | 1 | 33.10 |
| 2024-08-25 | 2024-08-25 | 1 | 0.00 |
| 2024-12-24 | 2024-12-28 | 5 | 3.20 |

### Các từ xuất hiện nhiều trong link_name (nhiều từ viết tắt)

| tu | so_tuyen |
|---|---|
| S | 54 |
| AVENUE | 51 |
| N | 49 |
| AVE | 34 |
| W | 28 |
| ST | 24 |
| E | 23 |
| EXIT | 23 |
| STREET | 21 |
| SIE | 15 |
| MANHATTAN | 14 |
| ANCHORAGE | 13 |
| QUEENS | 12 |
| ROAD | 11 |
| PLAZA | 11 |
| WSE | 11 |
| PKWY | 11 |
| CBE | 10 |
| LEVEL | 10 |
| BLVD | 10 |
| TOLL | 10 |
| VWE | 9 |
| AMSTERDAM | 9 |
| SOUTH | 9 |
| FDR | 8 |
| BE | 8 |
| TBB | 8 |
| CIP | 8 |
| TNB | 7 |
| LIE | 7 |

### Ngày lùi giờ 03/11/2024: số bản ghi theo giờ địa phương

| gio | so_dong |
|---|---|
| 0 | 1,464 |
| 1 | 2,035 |
| 2 | 1,464 |
| 3 | 1,464 |
| 4 | 1,464 |
| 5 | 1,464 |
| 6 | 1,464 |
| 7 | 1,464 |
| 8 | 1,464 |
| 9 | 1,464 |
| 10 | 1,464 |
| 11 | 1,464 |
| 12 | 1,464 |
| 13 | 1,464 |
| 14 | 1,464 |
| 15 | 1,464 |
| 16 | 1,464 |
| 17 | 1,464 |
| 18 | 1,464 |
| 19 | 1,464 |
| 20 | 1,464 |
| 21 | 1,464 |
| 22 | 1,464 |
| 23 | 1,464 |
