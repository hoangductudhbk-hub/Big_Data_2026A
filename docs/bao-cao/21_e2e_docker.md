# Báo cáo bước 21 — Kiểm tra end-to-end

Sinh tự động lúc 2026-10-14 06:15 · API `http://localhost:8000` · dữ liệu `D:\BigData\Big_Data_2026A\data`

**Kết quả: 18/18 kiểm tra đạt.**

| Kiểm tra | Endpoint | HTTP | ms | Kết quả | Chi tiết |
|---|---|---|---|---|---|
| API sống | `GET /health` | 200 | 146 | ĐẠT | status ok |
| Database + schema Alembic | `GET /api/v1/health/db` | 200 | 42 | ĐẠT | postgresql · revision 0001_contract_v1 |
| Số bản ghi DB = số dòng Parquet integrated_traffic | `GET /api/v1/statistics/summary` | 200 | 2464 | ĐẠT | DB 805,780 · Parquet 805,780 |
| Số đường DB = số road_id trong Parquet | `GET /api/v1/statistics/summary` | 200 | 844 | ĐẠT | 211 đường |
| Số bất thường DB = Parquet của bước 17 | `GET /api/v1/anomalies?page_size=1` | 200 | 75 | ĐẠT | 13,678 bản ghi |
| Spark (bước 15) = SQL trực tiếp trên PostgreSQL | `GET /api/v1/statistics/live?group_by=district` | 200 | 781 | ĐẠT | mean, median, n của 5 quận khớp đến 0,01 |
| GET /roads | `GET /api/v1/roads?page_size=5` | 200 | 16 | ĐẠT | 227 đường |
| GET /traffic (lọc + phân trang) | `GET /api/v1/traffic?road_id=L4616337&start=2024-03-01&end=2024-03-02` | 200 | 36 | ĐẠT | 24 bản ghi ngày 01/03/2024 |
| GET /traffic/{id} | `GET /api/v1/traffic/1172543` | 200 | 29 | ĐẠT | đúng bản ghi |
| GET /traffic/timeseries | `GET /api/v1/traffic/timeseries?bucket=month` | 200 | 233 | ĐẠT | 12 tháng |
| GET /weather | `GET /api/v1/weather?page_size=1` | 200 | 56 | ĐẠT | 43,915 giờ |
| GET /statistics | `GET /api/v1/statistics?dimension=hour` | 200 | 87 | ĐẠT | 48 dòng |
| GET /statistics/weather-impact | `GET /api/v1/statistics/weather-impact` | 200 | 107 | ĐẠT | 24 nhóm |
| GET /anomalies/summary | `GET /api/v1/anomalies/summary` | 200 | 104 | ĐẠT | đường nhiều nhất: WEST SHORE EXPRESSWAY |
| Lỗi 404 có định dạng thống nhất | `GET /api/v1/traffic/0` | 404 | 126 | ĐẠT | Không tìm thấy bản ghi giao thông id=0 |
| Lỗi 422 khi tham số sai | `GET /api/v1/traffic?page_size=0` | 422 | 24 | ĐẠT | query.page_size |
| POST /import/traffic từ chối dữ liệu sai contract | `POST /api/v1/import/traffic?all_or_nothing=true` | 422 | 270 | ĐẠT | avg_speed=999.0 lớn hơn 160 km/h |
| Dashboard được phục vụ | `GET /dashboard/` | 200 | 39 | ĐẠT | trả về trang HTML có app.js |
