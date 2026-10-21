"""Test bước 10: ghép 2 nguồn giao thông + thời tiết, kết quả đạt data contract."""
import pandas as pd

from common.contract import validate_pandas
from data_integration.integrate import build


def _inputs():
    ts = pd.to_datetime(["2024-03-16 08:00", "2024-03-16 09:00"])
    speeds = pd.DataFrame({"link_id": ["1", "1", "2"], "timestamp": [ts[0], ts[1], ts[0]],
                           "avg_speed": [40.0, 30.0, 70.0], "n_readings": [12, 12, 12]})
    volume = pd.DataFrame({"segmentid": ["9", "8"], "timestamp": [ts[1], ts[0]],
                           "vehicle_count": [1500, 300], "n_dirs": [2, 1], "any_outlier": [False, False]})
    roads = pd.DataFrame({
        "road_id": ["L1", "L2", "S8"], "road_name": ["BQE", "FDR", "MAIN ST"],
        "district": ["Brooklyn", "Manhattan", "Queens"], "latitude": [40.69, 40.75, 40.72],
        "longitude": [-73.99, -73.97, -73.80], "link_id": ["1", "2", None], "segmentid": ["9", None, "8"]})
    weather = pd.DataFrame({
        "weather_station_id": ["OM_BROOKLYN"] * 2 + ["OM_MANHATTAN"] * 2 + ["OM_QUEENS"] * 2,
        "district": ["Brooklyn"] * 2 + ["Manhattan"] * 2 + ["Queens"] * 2,
        "timestamp": list(ts) * 3, "temperature": [5.0] * 6, "rainfall": [0.0, 2.0] * 3,
        "snowfall": [0.0] * 6, "weather_condition": ["Cloudy", "Rain"] * 3})
    return speeds, volume, weather, roads


def test_build_integrated():
    df, st = build(*_inputs())
    assert validate_pandas(df) == []
    assert st["rows_by_source"] == {"speeds": 2, "speeds+volume": 1, "volume": 1}
    both = df[df.source == "speeds+volume"].iloc[0]
    assert both.road_id == "L1" and both.vehicle_count == 1500 and both.avg_speed == 30.0
    assert both.weather_condition == "Rain" and both.weather_station_id == "OM_BROOKLYN"
    vol_only = df[df.source == "volume"].iloc[0]
    assert vol_only.road_id == "S8" and pd.isna(vol_only.avg_speed) and vol_only.district == "Queens"
    assert st["rows_without_weather"] == 0


def test_nonexistent_dst_hour_uses_next_hour_weather():
    speeds, volume, weather, roads = _inputs()
    volume = pd.DataFrame({"segmentid": ["8"], "timestamp": [pd.Timestamp("2024-03-10 02:00")],
                           "vehicle_count": [100], "n_dirs": [1], "any_outlier": [False]})
    weather = pd.concat([weather, pd.DataFrame({
        "weather_station_id": ["OM_QUEENS"], "district": ["Queens"], "timestamp": [pd.Timestamp("2024-03-10 03:00")],
        "temperature": [-1.0], "rainfall": [0.0], "snowfall": [0.5], "weather_condition": ["Snow"]})])
    df, st = build(speeds, volume, weather, roads)
    row = df[df.road_id == "S8"].iloc[0]
    assert row.weather_condition == "Snow" and row.temperature == -1.0
    assert st["rows_weather_from_next_hour"] == 1 and st["rows_without_weather"] == 0
