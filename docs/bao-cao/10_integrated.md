# Báo cáo bảng tích hợp integrated_traffic (bước 10)

Sinh tự động lúc 2026-10-13 15:40 · data contract v1.0.0

## Tổng quan

- Số dòng: **805,780** · số đường: 211 · thời gian: 2024-01-01 00:00:00 → 2024-12-31 23:00:00
- Theo nguồn: {'speeds': 789250, 'volume': 16377, 'speeds+volume': 153}
- Dòng bị loại vì đường không có tọa độ: 0
- Dòng lưu lượng không gán được road_id: 0
- Dòng lấy thời tiết của giờ kế tiếp (giờ không tồn tại 02:00 ngày 10/03): 2
- Dòng không ghép được thời tiết: 0
- Kiểm tra data contract: ĐẠT (0 lỗi)

## Theo quận

| quan | dong |
|---|---|
| Queens | 298078 |
| Bronx | 165888 |
| Manhattan | 141656 |
| Staten Island | 141370 |
| Brooklyn | 58788 |

## Theo thời tiết

| thoi_tiet | dong |
|---|---|
| Clear | 361507 |
| Cloudy | 323898 |
| Drizzle | 85578 |
| Rain | 23991 |
| Snow | 10806 |

## Theo tháng

| thang | dong | duong | toc_do_tb | luu_luong_tb | nhiet_do_tb |
|---|---|---|---|---|---|
| 2024-01 | 68720 | 113 | 64.7 | 219.8 | 1.4 |
| 2024-02 | 41081 | 114 | 61.9 | 408.6 | 1.7 |
| 2024-03 | 72865 | 135 | 59.7 | 659.4 | 6.9 |
| 2024-04 | 69819 | 110 | 60.4 | 476.7 | 10.5 |
| 2024-05 | 70991 | 117 | 58.7 | 477.6 | 16.7 |
| 2024-06 | 73255 | 120 | 59.6 | 389.9 | 22.7 |
| 2024-07 | 69564 | 103 | 62.4 | None | 25.2 |
| 2024-08 | 67381 | 104 | 61.6 | None | 23.2 |
| 2024-09 | 70168 | 107 | 60.1 | 348.2 | 19.6 |
| 2024-10 | 72724 | 116 | 61.2 | 932.4 | 14.8 |
| 2024-11 | 69823 | 113 | 62.2 | 878.5 | 10.1 |
| 2024-12 | 59389 | 106 | 59.7 | 335.2 | 2.8 |

## Số giá trị null theo cột

| cot | null |
|---|---|
| road_id | 0 |
| road_name | 0 |
| district | 0 |
| latitude | 0 |
| longitude | 0 |
| timestamp | 0 |
| vehicle_count | 789250 |
| avg_speed | 16377 |
| temperature | 0 |
| rainfall | 0 |
| snowfall | 0 |
| weather_condition | 0 |
| weather_station_id | 0 |
| source | 0 |
