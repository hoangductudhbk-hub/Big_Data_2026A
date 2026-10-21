"""Làm sạch dữ liệu tốc độ (DOT Traffic Speeds) và danh mục tuyến."""
from __future__ import annotations

import numpy as np
import pandas as pd

from common.contract import MPH_TO_KMH, NYC_BBOX
from data_integration.cleaning.common import CleaningLog, normalize_district, normalize_text, parse_link_points

MAX_MPH = 100


def clean_speeds_month(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Làm sạch 1 file tháng. Gọi lặp cho 12 tháng với cùng 1 log để cộng dồn số liệu."""
    log.rows_in += len(raw)
    df = raw.copy()
    df["speed_mph"] = pd.to_numeric(df["speed"], errors="coerce")
    df["travel_time"] = pd.to_numeric(df["travel_time"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["data_as_of"], errors="coerce", format="ISO8601")

    bad_parse = df["speed_mph"].isna() | df["timestamp"].isna()
    log.add("speed hoặc data_as_of không đọc được", bad_parse.sum(), "loại bỏ")
    df = df[~bad_parse]

    st = df["status"] != "0"
    log.add("status = -101 (bản ghi cảm biến không hợp lệ)", st.sum(), "loại bỏ",
            "Profiling: phân bố tốc độ lệch hẳn, có tuyến hỏng 100%")
    df = df[~st]

    zero = df["speed_mph"] <= 0
    log.add("speed ≤ 0 với status = 0", zero.sum(), "loại bỏ")
    df = df[~zero]

    fast = df["speed_mph"] > MAX_MPH
    log.add(f"speed > {MAX_MPH} mph", fast.sum(), "loại bỏ", "Bất hợp lý trong đô thị")
    df = df[~fast]

    dup = df.duplicated(["link_id", "timestamp"])
    log.add("Trùng (link_id, thời điểm)", dup.sum(), "loại bỏ bản sau")
    df = df[~dup]

    out = pd.DataFrame({
        "link_id": df["link_id"].astype("string"),
        "timestamp": df["timestamp"].astype("datetime64[us]"),
        "speed_mph": df["speed_mph"].astype("float64"),
        "speed_kmh": (df["speed_mph"] * MPH_TO_KMH).round(2),
        "travel_time_s": df["travel_time"].astype("float64"),
    })
    log.rows_out += len(out)
    return out


def clean_links(raw_links: pd.DataFrame, seen: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    """
    Danh mục tuyến: chuẩn hóa tên, quận, tính tọa độ đại diện từ link_points.
    `seen` = (link_id, link_name, borough) lấy từ chính các bản ghi, để bổ sung tuyến có trong
    bản ghi nhưng thiếu trong links.csv.
    """
    log = CleaningLog("links", rows_in=len(raw_links))
    links = raw_links[["link_id", "link_name", "borough", "link_points"]].copy()

    missing = seen[~seen["link_id"].isin(links["link_id"])].drop_duplicates("link_id")
    log.add("Tuyến có trong bản ghi nhưng thiếu trong links.csv", len(missing), "bổ sung (không có tọa độ)")
    links = pd.concat([links, missing.assign(link_points="")], ignore_index=True)

    links["link_name_raw"] = links["link_name"]
    links["link_name"] = normalize_text(links["link_name"])
    log.add("Tên tuyến lẫn chữ thường", int((links["link_name_raw"] != links["link_name"]).sum()), "viết hoa")
    links["district"] = normalize_district(links["borough"])

    pts = links["link_points"].map(parse_link_points)
    truncated = links["link_points"].str.len().eq(255)
    log.add("link_points bị cắt ở 255 ký tự (giới hạn Socrata)", int(truncated.sum()),
            "bỏ cặp tọa độ cuối bị cụt")
    pts = pts.map(lambda ps: [(la, lo) for la, lo in ps
                              if NYC_BBOX["lat_min"] <= la <= NYC_BBOX["lat_max"]
                              and NYC_BBOX["lon_min"] <= lo <= NYC_BBOX["lon_max"]])
    links["n_points"] = pts.map(len)
    links["latitude"] = pts.map(lambda ps: float(np.mean([p[0] for p in ps])) if ps else np.nan)
    links["longitude"] = pts.map(lambda ps: float(np.mean([p[1] for p in ps])) if ps else np.nan)
    links["start_lat"] = pts.map(lambda ps: ps[0][0] if ps else np.nan)
    links["start_lon"] = pts.map(lambda ps: ps[0][1] if ps else np.nan)
    links["end_lat"] = pts.map(lambda ps: ps[-1][0] if ps else np.nan)
    links["end_lon"] = pts.map(lambda ps: ps[-1][1] if ps else np.nan)
    log.add("Tuyến không có tọa độ hợp lệ trong New York", int(links["latitude"].isna().sum()),
            "giữ lại, tọa độ = null")
    log.add("Tọa độ đại diện = trung bình các điểm của tuyến", int(links["latitude"].notna().sum()), "tính mới")

    links = links.drop(columns=["link_points", "borough"])
    links["link_id"] = links["link_id"].astype("string")
    log.rows_out = len(links)
    return links.sort_values("link_id").reset_index(drop=True), log


def coverage_flags(speeds: pd.DataFrame, threshold: float = 50.0) -> pd.DataFrame:
    """Độ phủ theo ngày: % cặp (tuyến, giờ) có dữ liệu. Đánh dấu ngày < threshold là ngày mất dữ liệu."""
    hours = speeds.assign(h=speeds["timestamp"].dt.floor("h"))[["link_id", "h"]].drop_duplicates()
    hours["date"] = hours["h"].dt.floor("D")
    month = hours["date"].dt.to_period("M")
    active = hours.groupby(month)["link_id"].nunique()
    daily = hours.groupby("date").size().rename("covered_link_hours").reset_index()
    daily["active_links"] = daily["date"].dt.to_period("M").map(active)
    daily["coverage_pct"] = (100 * daily["covered_link_hours"] / (daily["active_links"] * 24)).round(1)
    full = pd.DataFrame({"date": pd.date_range(hours["date"].min().to_period("M").start_time,
                                               hours["date"].max().to_period("M").end_time.normalize(), freq="D")})
    daily = full.merge(daily, on="date", how="left").fillna({"covered_link_hours": 0, "coverage_pct": 0.0})
    daily["is_outage"] = daily["coverage_pct"] < threshold
    return daily
