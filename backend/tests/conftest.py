"""Test backend trên một bộ dữ liệu nhỏ, đúng data contract, đi qua ĐÚNG đường nạp thật (load_processed).

Mặc định dùng SQLite trong bộ nhớ (chạy được ở mọi máy). Đặt biến môi trường
    TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/traffic_test
để chạy trên PostgreSQL thật (bật thêm các test cần hàm riêng của PostgreSQL: timeseries, stddev, median).
CẢNH BÁO: database test sẽ bị xóa sạch bảng.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app  # noqa: F401
from app.core.config import settings
from app.core.database import get_db
from app.etl.load_processed import load
from app.main import app as fastapi_app
from app.models import Base
from common.contract import COLUMN_NAMES

TEST_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")
IS_PG = TEST_URL.startswith("postgresql")
pg_only = pytest.mark.skipif(not IS_PG, reason="cần PostgreSQL (đặt TEST_DATABASE_URL)")

ROADS = [("L1", "BROOKLYN QUEENS EXPRESSWAY", "Brooklyn", 40.69, -73.99, True, False),
         ("L2", "WEST SHORE EXPRESSWAY", "Staten Island", 40.58, -74.19, True, True),
         ("S3", "FLATBUSH AVENUE", "Brooklyn", 40.68, -73.97, False, True)]


def make_data(root: Path) -> Path:
    """data/ thu nhỏ: 3 đường × 48 giờ, thời tiết, và các bảng analytics."""
    proc, interim, ana = root / "processed", root / "interim", root / "processed" / "analytics"
    for p in (proc, interim, ana):
        p.mkdir(parents=True, exist_ok=True)
    hours = pd.date_range("2024-03-01", periods=48, freq="h")
    rng = np.random.default_rng(0)
    roads = pd.DataFrame(ROADS, columns=["road_id", "road_name", "district", "latitude", "longitude",
                                         "has_speed", "has_volume"])
    roads.to_parquet(proc / "roads.parquet")
    rows = []
    for r in ROADS:
        for h in hours:
            spd = round(float(rng.uniform(20, 90)), 2) if r[5] else None
            vol = int(rng.integers(50, 900)) if r[6] else None
            rows.append({"road_id": r[0], "road_name": r[1], "district": r[2], "latitude": r[3], "longitude": r[4],
                         "timestamp": h, "vehicle_count": vol, "avg_speed": spd, "temperature": 5.0,
                         "rainfall": 1.2 if h.hour == 8 else 0.0, "snowfall": 0.0,
                         "weather_condition": "Rain" if h.hour == 8 else "Clear",
                         "weather_station_id": f"OM_{r[2].upper().replace(' ', '_')}",
                         "source": "speeds+volume" if spd is not None and vol is not None
                         else ("speeds" if spd is not None else "volume")})
    it = pd.DataFrame(rows)[list(COLUMN_NAMES)]
    it["vehicle_count"] = it["vehicle_count"].astype("Int64")
    it["timestamp"] = it["timestamp"].astype("datetime64[us]")
    (proc / "integrated_traffic").mkdir(exist_ok=True)
    it.to_parquet(proc / "integrated_traffic" / "part-0.parquet")
    w = pd.DataFrame([{"station_id": f"OM_{d.upper().replace(' ', '_')}", "district": d, "timestamp": h,
                       "temperature": 5.0, "precipitation": 0.0, "rainfall": 0.0, "snowfall": 0.0, "weather_code": 0,
                       "weather_condition": "Clear"} for d in ("Brooklyn", "Staten Island") for h in hours])
    w.to_parquet(interim / "weather_clean.parquet")
    pd.DataFrame([{"dimension": "district", "group_key": "Brooklyn", "metric": "avg_speed", "n": 48, "mean": 55.0,
                   "std": 20.0, "min": 20.0, "max": 90.0, "median": 54.0},
                  {"dimension": "hour", "group_key": "08h", "metric": "avg_speed", "n": 4, "mean": 40.0,
                   "std": 5.0, "min": 35.0, "max": 45.0, "median": 40.0}]).to_parquet(ana / "statistics.parquet")
    pd.DataFrame([{"date": "2024-03-01", "n_speed": 48, "mean_speed": 55.0, "n_volume": 48, "mean_volume": 400.0,
                   "temperature": 5.0, "rain_mm_per_day": 2.4, "snow_cm_per_day": 0.0, "coverage_pct": 100.0,
                   "is_outage": False}]).to_parquet(ana / "daily_stats.parquet")
    pd.DataFrame([{"chieu": "weather_condition", "nhom": "Rain", "n": 4, "so_ngay": 2, "tb_tho": 50.0,
                   "thay_doi_tho_pct": -6.6, "thay_doi_kiem_soat_pct": -4.8, "kiem_soat_them_thang_pct": -4.6,
                   "ktc95_pct": 0.4}]).to_parquet(ana / "weather_impact.parquet")
    pd.DataFrame([{"road_id": "L1", "timestamp": hours[8], "metric": "avg_speed", "value": 5.0, "expected": 60.0,
                   "std": 10.0, "z_score": -5.5, "is_anomaly": True, "direction": "thấp bất thường",
                   "vehicle_count": None, "avg_speed": 5.0, "weather_condition": "Rain", "rainfall": 1.2,
                   "snowfall": 0.0, "road_name": ROADS[0][1], "district": "Brooklyn"},
                  {"road_id": "S3", "timestamp": hours[9], "metric": "vehicle_count", "value": 3000.0,
                   "expected": 400.0, "std": 200.0, "z_score": 13.0, "is_anomaly": True, "direction": "cao bất thường",
                   "vehicle_count": 3000.0, "avg_speed": None, "weather_condition": "Clear", "rainfall": 0.0,
                   "snowfall": 0.0, "road_name": ROADS[2][1], "district": "Brooklyn"}]
                 ).to_parquet(ana / "anomalies.parquet")
    pd.DataFrame([{"date": "2024-03-01", "ban_ghi": 48, "cham_bat_thuong": 1, "nhanh_bat_thuong": 0, "z_tb": -0.1,
                   "mua_mm_ngay": 2.4, "tuyet_cm_ngay": 0.0, "day_type": "weekday", "ti_le_bat_thuong_pct": 2.08,
                   "do_phu_pct": 100.0}]).to_parquet(ana / "anomaly_daily.parquet")
    return root


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory):
    return make_data(tmp_path_factory.mktemp("data"))


@pytest.fixture(scope="session")
def engine(data_dir):
    eng = create_engine(TEST_URL, **({} if IS_PG else {"connect_args": {"check_same_thread": False},
                                                       "poolclass": StaticPool}))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    load(eng, data_dir, verbose=False)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(scope="session")
def client(engine, data_dir):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine, autoflush=False)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = _db
    old = settings.DATA_DIR
    settings.DATA_DIR = data_dir
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    settings.DATA_DIR = old
    fastapi_app.dependency_overrides.clear()
