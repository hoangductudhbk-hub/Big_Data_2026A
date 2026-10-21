"""Cấu hình dùng chung cho Phase 1 (Data Integration)."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORT_DIR = PROJECT_ROOT / "docs" / "bao-cao"

# Phạm vi nghiên cứu (xem docs/huong-dan/02_lua_chon_nguon_du_lieu.md, mục 6)
STUDY_START = "2024-01-01"
STUDY_END = "2024-12-31"          # bao gồm cả ngày này

LOCAL_TZ = "America/New_York"

# NYC Open Data (Socrata)
NYC_BASE_URL = "https://data.cityofnewyork.us/resource"
SPEEDS_DATASET = "i4gi-tjb9"      # DOT Traffic Speeds
VOLUME_DATASET = "7ym2-wayt"      # Automated Traffic Volume Counts
# App token miễn phí giúp không bị giới hạn tốc độ (đăng ký tại data.cityofnewyork.us).
# Đặt vào biến môi trường: NYC_APP_TOKEN=...
NYC_APP_TOKEN = os.getenv("NYC_APP_TOKEN")

# Open-Meteo
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_HOURLY_VARS = ("temperature_2m", "precipitation", "rain", "snowfall", "weather_code")

# Điểm thời tiết đại diện cho từng quận (tọa độ trung tâm gần đúng của borough).
# Open-Meteo trả dữ liệu theo lưới khoảng 10 km, nên 1 điểm/quận là đủ chi tiết.
WEATHER_STATIONS = {
    "OM_MANHATTAN":     {"district": "Manhattan",     "latitude": 40.7831, "longitude": -73.9712},
    "OM_BROOKLYN":      {"district": "Brooklyn",      "latitude": 40.6782, "longitude": -73.9442},
    "OM_QUEENS":        {"district": "Queens",        "latitude": 40.7282, "longitude": -73.7949},
    "OM_BRONX":         {"district": "Bronx",         "latitude": 40.8448, "longitude": -73.8648},
    "OM_STATEN_ISLAND": {"district": "Staten Island", "latitude": 40.5795, "longitude": -74.1502},
}
