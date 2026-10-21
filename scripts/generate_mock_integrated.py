"""
Sinh MOCK dataset integrated_traffic đúng data contract (common/contract.py).

Mục đích: để Phase 2 (PySpark) bắt đầu ngay khi Phase 1 chưa xong (theo mục 15 của plan).
Đây là DỮ LIỆU GIẢ, chỉ dùng để phát triển và test code, KHÔNG dùng cho kết quả phân tích cuối cùng.

Chạy:
    python scripts/generate_mock_integrated.py                       # mặc định: 200 đường, cả năm 2024
    python scripts/generate_mock_integrated.py --roads 50 --start 2024-01-01 --end 2024-01-31
    python scripts/generate_mock_integrated.py --roads 1000          # dataset lớn để thử benchmark

Đầu ra:
    data/mock/integrated_traffic/year=YYYY/month=M/part-*.parquet
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.contract import (COLUMN_NAMES, DISTRICTS, NYC_BBOX, arrow_schema,  # noqa: E402
                             validate_pandas, wmo_to_condition)

DISTRICT_CENTER = {
    "Manhattan": (40.7831, -73.9712), "Brooklyn": (40.6782, -73.9442), "Queens": (40.7282, -73.7949),
    "Bronx": (40.8448, -73.8648), "Staten Island": (40.5795, -74.1502),
}
STREET_TYPES = ["AVENUE", "STREET", "BOULEVARD", "EXPRESSWAY", "PARKWAY", "ROAD"]


def make_roads(n: int, rng: np.random.Generator) -> pd.DataFrame:
    district = rng.choice(DISTRICTS, size=n, p=[0.3, 0.25, 0.25, 0.12, 0.08])
    kind = rng.choice(["speeds", "volume", "speeds+volume"], size=n, p=[0.55, 0.30, 0.15])
    lat = np.array([DISTRICT_CENTER[d][0] for d in district]) + rng.normal(0, 0.02, n)
    lon = np.array([DISTRICT_CENTER[d][1] for d in district]) + rng.normal(0, 0.02, n)
    roads = pd.DataFrame({
        "road_id": [("L" if k != "volume" else "S") + str(4_000_000 + i) for i, k in enumerate(kind)],
        "road_name": [f"{rng.integers(1, 200)} {rng.choice(STREET_TYPES)}" for _ in range(n)],
        "district": district,
        "latitude": lat.clip(NYC_BBOX["lat_min"], NYC_BBOX["lat_max"]),
        "longitude": lon.clip(NYC_BBOX["lon_min"], NYC_BBOX["lon_max"]),
        "source": kind,
        "free_flow_kmh": rng.uniform(35, 95, n),       # tốc độ khi đường vắng
        "base_volume": rng.uniform(150, 2500, n),      # lưu lượng trung bình/giờ
    })
    return roads


def make_weather(hours: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    """Thời tiết giả theo quận: nhiệt độ theo mùa + theo ngày, mưa/tuyết theo chuỗi Markov."""
    frames = []
    doy = hours.dayofyear.values
    hod = hours.hour.values
    for d in DISTRICTS:
        temp = 12 - 13 * np.cos(2 * np.pi * (doy - 15) / 366) + 4 * np.sin(2 * np.pi * (hod - 9) / 24)
        temp = temp + rng.normal(0, 1.5, len(hours))
        wet = np.zeros(len(hours), dtype=bool)
        for i in range(1, len(hours)):           # chuỗi Markov: trời mưa thì dễ mưa tiếp
            p = 0.85 if wet[i - 1] else 0.03
            wet[i] = rng.random() < p
        precip = np.where(wet, rng.gamma(1.2, 1.5, len(hours)), 0.0)
        snow_mask = wet & (temp < 1)
        code = np.where(~wet, rng.choice([0, 1, 2, 3], len(hours), p=[0.35, 0.25, 0.2, 0.2]),
                        np.where(snow_mask, 73, np.where(precip > 6, 95, np.where(precip > 2, 63, 61))))
        frames.append(pd.DataFrame({
            "district": d, "timestamp": hours,
            "temperature": temp.round(1),
            "rainfall": np.where(snow_mask, 0.0, precip).round(2),
            "snowfall": np.where(snow_mask, precip * 0.7, 0.0).round(2),
            "weather_code": code,
        }))
    w = pd.concat(frames, ignore_index=True)
    w["weather_condition"] = w["weather_code"].map(wmo_to_condition)
    w["weather_station_id"] = "OM_" + w["district"].str.upper().str.replace(" ", "_")
    return w.drop(columns="weather_code")


def traffic_profile(ts: pd.Series) -> np.ndarray:
    """Hệ số lưu lượng theo giờ: 2 đỉnh cao điểm sáng/chiều, cuối tuần thấp hơn."""
    h = ts.dt.hour.values
    weekday = ts.dt.dayofweek.values < 5
    peak = np.exp(-((h - 8) ** 2) / 4) + np.exp(-((h - 17.5) ** 2) / 5)
    base = 0.25 + 0.55 * np.sin(np.pi * np.clip(h - 5, 0, 18) / 18)
    return np.where(weekday, base + 0.9 * peak, 0.85 * base + 0.2 * peak)


def build(roads_n: int, start: str, end: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    hours = pd.date_range(start, pd.Timestamp(end) + pd.Timedelta(hours=23), freq="h")
    roads = make_roads(roads_n, rng)
    weather = make_weather(hours, rng)

    df = roads.merge(pd.DataFrame({"timestamp": hours}), how="cross")
    df = df.merge(weather, on=["district", "timestamp"], how="left")

    prof = traffic_profile(df["timestamp"])
    # Thời tiết xấu: xe chạy chậm hơn rõ rệt (giảm tầm nhìn, đường trơn), lưu lượng chỉ giảm nhẹ
    rain = np.minimum(df["rainfall"].values, 10)
    snow = np.minimum(df["snowfall"].values, 5)
    speed_factor = 1 - 0.12 * (rain > 0) - 0.015 * rain - 0.25 * (snow > 0) - 0.03 * snow
    speed_factor = speed_factor - 0.10 * (df["weather_condition"].values == "Thunderstorm")
    volume = df["base_volume"].values * prof * (1 - 0.02 * (rain > 0) - 0.05 * (snow > 0))
    volume = rng.poisson(np.maximum(volume, 1))
    # Hàm BPR (Bureau of Public Roads): tốc độ = tốc độ tự do / (1 + a·(lưu lượng/năng lực)^b)
    v_over_c = volume / (df["base_volume"].values * 1.2)
    speed = df["free_flow_kmh"].values / (1 + 1.0 * v_over_c ** 4) * speed_factor * rng.normal(1, 0.06, len(df))

    # Cài bất thường (khoảng 0,1%): kẹt xe đột ngột hoặc lưu lượng tăng vọt, để test Z-score
    anomaly = rng.random(len(df)) < 0.001
    speed = np.where(anomaly, speed * 0.25, speed)
    volume = np.where(anomaly, (volume * 3.5).astype(int), volume)
    df["_injected"] = anomaly          # nhãn đúng, chỉ dùng để kiểm chứng bước 17 (không thuộc contract)

    df["avg_speed"] = np.clip(speed, 1, 159).round(2)
    df["vehicle_count"] = np.clip(volume, 0, 19_999).astype("int64")
    df.loc[df["source"] == "volume", "avg_speed"] = np.nan
    df["vehicle_count"] = df["vehicle_count"].astype("Int64")
    df.loc[df["source"] == "speeds", "vehicle_count"] = pd.NA

    # Mô phỏng mất dữ liệu cảm biến (khoảng 2% số giờ)
    df = df[rng.random(len(df)) > 0.02]
    return df[list(COLUMN_NAMES) + ["_injected"]].reset_index(drop=True)


def write_partitioned(df: pd.DataFrame, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    table = pa.Table.from_pandas(df, schema=arrow_schema(), preserve_index=False)
    table = table.append_column("year", pa.array(df["timestamp"].dt.year.astype("int32")))
    table = table.append_column("month", pa.array(df["timestamp"].dt.month.astype("int32")))
    pq.write_to_dataset(table, root_path=str(out_dir), partition_cols=["year", "month"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--roads", type=int, default=200)
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end", default="2024-12-31")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(ROOT / "data" / "mock" / "integrated_traffic"))
    a = p.parse_args()

    df = build(a.roads, a.start, a.end, a.seed)
    labels = df.loc[df.pop("_injected"), ["road_id", "timestamp", "source"]]
    errors = validate_pandas(df)
    if errors:
        raise SystemExit("Mock data KHÔNG đạt contract:\n- " + "\n- ".join(errors))
    write_partitioned(df, Path(a.out))
    # Danh sách bất thường đã cài (đáp án) để bước 17 đo precision/recall của Z-score
    labels_path = Path(a.out).parent / "injected_anomalies.parquet"
    labels.assign(timestamp=labels["timestamp"].astype("datetime64[us]")).to_parquet(labels_path, index=False)
    print(f"Đã cài {len(labels):,} bất thường → {labels_path}")
    size_mb = sum(f.stat().st_size for f in Path(a.out).rglob("*.parquet")) / 1e6
    print(f"Đạt contract. {len(df):,} dòng, {df['road_id'].nunique()} đường → {a.out} ({size_mb:.1f} MB)")
    print(df["source"].value_counts().to_string())


if __name__ == "__main__":
    main()
