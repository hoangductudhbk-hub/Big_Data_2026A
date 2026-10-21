"""Biến đổi dữ liệu đã làm sạch về lược đồ và mức chi tiết chung (đường × giờ)."""
from __future__ import annotations

import pandas as pd

from data_integration.alignment.names import normalize_name, parse_link_name


def speeds_hourly(month_df: pd.DataFrame) -> pd.DataFrame:
    """Trung bình tốc độ theo (link, giờ). Gọi cho từng tháng."""
    g = (month_df.assign(timestamp=month_df["timestamp"].dt.floor("h"))
         .groupby(["link_id", "timestamp"], observed=True)
         .agg(avg_speed=("speed_kmh", "mean"), n_readings=("speed_kmh", "size")).reset_index())
    g["avg_speed"] = g["avg_speed"].round(2)
    return g


def volume_hourly(v: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Cộng 4 khung 15' thành 1 giờ, cộng mọi hướng của đoạn.
    Chỉ giữ giờ ĐẦY ĐỦ: mỗi hướng có đủ 4 khung, và có đủ mọi hướng của đoạn đó.
    (Nếu cộng giờ thiếu khung thì lưu lượng bị đánh giá thấp một cách giả tạo.)
    """
    v = v.assign(timestamp=v["timestamp"].dt.floor("h"))
    per_dir = (v.groupby(["segmentid", "direction", "timestamp"])
               .agg(vol=("vol", "sum"), n_slots=("vol", "size"),
                    any_outlier=("flag_outlier", "any")).reset_index())
    n_dirs = v.groupby("segmentid")["direction"].nunique().rename("n_dirs")
    per_dir = per_dir.join(n_dirs, on="segmentid")
    per_seg = (per_dir.groupby(["segmentid", "timestamp"])
               .agg(vehicle_count=("vol", "sum"), slots=("n_slots", "sum"), dirs=("direction", "nunique"),
                    n_dirs=("n_dirs", "first"), any_outlier=("any_outlier", "any")).reset_index())
    complete = (per_seg["dirs"] == per_seg["n_dirs"]) & (per_seg["slots"] == 4 * per_seg["n_dirs"])
    stats = {"segment_hours": int(len(per_seg)), "complete": int(complete.sum()),
             "dropped_incomplete": int((~complete).sum())}
    out = per_seg[complete][["segmentid", "timestamp", "vehicle_count", "n_dirs", "any_outlier"]]
    return out.reset_index(drop=True), stats


def roads_from_links(links: pd.DataFrame) -> pd.DataFrame:
    parsed = links["link_name"].map(parse_link_name)
    return pd.DataFrame({
        "link_id": links["link_id"],
        "link_name": links["link_name"],
        "main_road": parsed.map(lambda p: p["main_road"]),
        "direction": parsed.map(lambda p: p["direction"]),
        "endpoints": parsed.map(lambda p: "; ".join(p["endpoints"])),
        "district": links["district"],
        "latitude": links["latitude"], "longitude": links["longitude"],
        "start_lat": links["start_lat"], "start_lon": links["start_lon"],
        "end_lat": links["end_lat"], "end_lon": links["end_lon"],
    })


def roads_from_volume(v: pd.DataFrame) -> pd.DataFrame:
    seg = (v.groupby("segmentid")
           .agg(street=("street", "first"), fromst=("fromst", "first"), tost=("tost", "first"),
                district=("district", "first"), latitude=("latitude", "first"),
                longitude=("longitude", "first"), directions=("direction", lambda s: ",".join(sorted(set(s)))),
                n_rows=("vol", "size")).reset_index())
    seg["main_road"] = seg["street"].map(normalize_name)
    seg["endpoints"] = seg["fromst"].map(normalize_name) + "; " + seg["tost"].map(normalize_name)
    return seg


def weather_hourly(w: pd.DataFrame) -> pd.DataFrame:
    return w.rename(columns={"station_id": "weather_station_id"})[
        ["weather_station_id", "district", "timestamp", "temperature", "rainfall", "snowfall", "weather_condition"]]
