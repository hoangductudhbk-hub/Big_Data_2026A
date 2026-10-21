"""
Ánh xạ GAV (Global-as-View): mỗi cột của lược đồ trung gian `integrated_traffic` được định nghĩa
bằng một biểu thức trên các nguồn. Đây là "tài liệu sống": aggregate.py cài đặt đúng các biểu thức này,
và báo cáo bước 08 in bảng này ra.

Dạng Datalog tương đương (xem docs/huong-dan/08_schema_alignment.md):
  T_speed(link, h, avg(kmh))      :- Speeds(link, t, mph, status), status = 0, h = hour(t), kmh = mph·1.609344
  T_volume(seg, h, sum(vol))      :- Volume(seg, dir, yr, m, d, hh, mm, vol), h = make_ts(yr, m, d, hh), đủ 4 khung
  W(district, h, temp, rain, ...) :- Weather(station, t_local, ...), h = t_local
  Integrated(road, h, ...)        :- RoadLink(road, link | seg), T_speed / T_volume, W(district(road), h, ...)
"""

GAV_MAPPING = [
    {"target": "road_id", "speeds": "concat('L', link_id)", "volume": "concat('S', segmentid) nếu không nối được với link",
     "weather": "—", "note": "Quyết định ở bước 09 (record linkage)"},
    {"target": "road_name", "speeds": "normalize(main_road(link_name))", "volume": "normalize(street)",
     "weather": "—", "note": "Mở rộng viết tắt: BQE → BROOKLYN QUEENS EXPRESSWAY, AVE → AVENUE"},
    {"target": "district", "speeds": "normalize_district(borough)", "volume": "normalize_district(boro)",
     "weather": "district của trạm", "note": "5 giá trị chuẩn"},
    {"target": "latitude / longitude", "speeds": "mean(link_points)", "volume": "EPSG:2263→4326(wktgeom)",
     "weather": "—", "note": "WGS84"},
    {"target": "timestamp", "speeds": "date_trunc('hour', data_as_of)",
     "volume": "make_timestamp(yr, m, d, hh)", "weather": "time_local", "note": "Giờ New York, tròn giờ"},
    {"target": "avg_speed", "speeds": "AVG(speed) × 1.609344 theo (link, giờ)", "volume": "—", "weather": "—",
     "note": "chỉ status = 0"},
    {"target": "vehicle_count", "speeds": "—", "volume": "SUM(vol) theo (segment, giờ), mọi hướng",
     "weather": "—", "note": "chỉ giờ có đủ 4 khung 15' ở mọi hướng"},
    {"target": "temperature", "speeds": "—", "volume": "—", "weather": "temperature_2m", "note": "°C"},
    {"target": "rainfall", "speeds": "—", "volume": "—", "weather": "rain", "note": "mm"},
    {"target": "snowfall", "speeds": "—", "volume": "—", "weather": "snowfall", "note": "cm"},
    {"target": "weather_condition", "speeds": "—", "volume": "—", "weather": "wmo_to_condition(weather_code)",
     "note": "7 nhóm"},
    {"target": "weather_station_id", "speeds": "—", "volume": "—", "weather": "station_id", "note": ""},
    {"target": "source", "speeds": "'speeds'", "volume": "'volume'", "weather": "—",
     "note": "'speeds+volume' nếu đường được nối và cùng giờ có cả 2"},
]
