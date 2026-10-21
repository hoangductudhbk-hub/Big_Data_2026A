import pandas as pd

from common.contract import COLUMN_NAMES, validate_pandas, wmo_to_condition


def _valid_row(**overrides):
    row = {
        "road_id": "L4362250",
        "road_name": "CROSS ISLAND EXPRESSWAY",
        "district": "Queens",
        "latitude": 40.78,
        "longitude": -73.79,
        "timestamp": pd.Timestamp("2024-03-01 08:00"),
        "vehicle_count": 1200,
        "avg_speed": 55.3,
        "temperature": 5.2,
        "rainfall": 0.0,
        "snowfall": 0.0,
        "weather_condition": "Cloudy",
        "weather_station_id": "OM_QUEENS",
        "source": "speeds+volume",
    }
    row.update(overrides)
    return row


def test_valid_dataframe_has_no_errors():
    df = pd.DataFrame([_valid_row(), _valid_row(timestamp=pd.Timestamp("2024-03-01 09:00"))])
    assert list(df.columns) == list(COLUMN_NAMES)
    assert validate_pandas(df) == []


def test_detects_bad_values():
    df = pd.DataFrame([
        _valid_row(district="Hanoi"),
        _valid_row(timestamp=pd.Timestamp("2024-03-01 08:15"), avg_speed=-5),
        _valid_row(timestamp=pd.Timestamp("2024-03-01 10:00"), vehicle_count=None, avg_speed=None),
    ])
    errors = " | ".join(validate_pandas(df))
    assert "district" in errors
    assert "không tròn giờ" in errors
    assert "avg_speed" in errors
    assert "thiếu cả vehicle_count" in errors


def test_detects_duplicate_primary_key():
    df = pd.DataFrame([_valid_row(), _valid_row()])
    assert any("trùng" in e for e in validate_pandas(df))


def test_wmo_mapping():
    assert wmo_to_condition(0) == "Clear"
    assert wmo_to_condition(3) == "Cloudy"
    assert wmo_to_condition(63) == "Rain"
    assert wmo_to_condition(81) == "Rain"
    assert wmo_to_condition(73) == "Snow"
    assert wmo_to_condition(95) == "Thunderstorm"
    assert wmo_to_condition(None) is None
