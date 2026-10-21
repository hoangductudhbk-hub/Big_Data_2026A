"""
Tải dữ liệu thời tiết theo giờ của 5 quận New York từ Open-Meteo Historical Weather API.

Chạy:
    python -m data_integration.collect.fetch_weather
    python -m data_integration.collect.fetch_weather --start 2024-01-01 --end 2024-12-31

Đầu ra:
    data/raw/weather/open_meteo_<start>_<end>.json   (phản hồi gốc, không sửa)
    data/raw/weather/open_meteo_<start>_<end>.csv    (dạng bảng, chưa làm sạch)

Lưu ý về phạm vi: start/end là ngày theo GIỜ NEW YORK. Vì API trả theo UTC, script xin thêm 1 ngày
mỗi đầu rồi cắt lại đúng [start 00:00, end 23:00] giờ địa phương. (Phiên bản đầu không làm vậy nên
thiếu 5 giờ cuối ngày 31/12/2024 và thừa 5 giờ của 31/12/2023 — phát hiện ở bước profiling.)

Lưu ý về giờ mùa hè (DST): khi truyền timezone=America/New_York, Open-Meteo dùng MỘT độ lệch
cố định cho cả khoảng ngày, bỏ qua việc chuyển giờ mùa hè. Vì vậy script yêu cầu thời gian dạng
unixtime (UTC) rồi tự đổi sang giờ New York bằng pandas, để giờ luôn đúng quanh các ngày đổi giờ.
"""
from __future__ import annotations

import argparse
import json
import logging

import pandas as pd

from data_integration import config
from data_integration.collect.http_utils import get_with_retry

log = logging.getLogger("fetch_weather")


def build_params(start: str, end: str) -> dict:
    """Xin dư 1 ngày mỗi đầu (theo UTC) để bao trọn khoảng giờ địa phương."""
    stations = list(config.WEATHER_STATIONS.values())
    start = (pd.Timestamp(start) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "latitude": ",".join(str(s["latitude"]) for s in stations),
        "longitude": ",".join(str(s["longitude"]) for s in stations),
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(config.WEATHER_HOURLY_VARS),
        "timezone": "GMT",
        "timeformat": "unixtime",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }


def response_to_frame(payload) -> pd.DataFrame:
    """Đổi JSON của Open-Meteo (1 object hoặc list object, mỗi object 1 vị trí) thành bảng dài."""
    if isinstance(payload, dict):
        payload = [payload]
    station_ids = list(config.WEATHER_STATIONS.keys())
    if len(payload) != len(station_ids):
        raise ValueError(f"Nhận {len(payload)} vị trí, mong đợi {len(station_ids)}")

    frames = []
    for station_id, loc in zip(station_ids, payload):
        hourly = loc["hourly"]
        df = pd.DataFrame(hourly)
        utc = pd.to_datetime(df.pop("time"), unit="s", utc=True)
        df.insert(0, "time_utc", utc.dt.tz_localize(None))
        df.insert(1, "time_local", utc.dt.tz_convert(config.LOCAL_TZ).dt.tz_localize(None))
        df.insert(0, "station_id", station_id)
        df["district"] = config.WEATHER_STATIONS[station_id]["district"]
        df["grid_latitude"] = loc.get("latitude")
        df["grid_longitude"] = loc.get("longitude")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def clip_local_range(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Giữ đúng các giờ địa phương trong [start 00:00, end 23:00]."""
    lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23)
    return df[df["time_local"].between(lo, hi)].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=config.STUDY_START)
    parser.add_argument("--end", default=config.STUDY_END)
    args = parser.parse_args()

    out_dir = config.RAW_DIR / "weather"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"open_meteo_{args.start}_{args.end}"
    if (out_dir / f"{stem}.csv").exists():
        log.info("Đã có %s.csv, bỏ qua", stem)
        return

    log.info("Gọi Open-Meteo cho %d điểm, %s → %s", len(config.WEATHER_STATIONS), args.start, args.end)
    resp = get_with_retry(config.OPEN_METEO_URL, params=build_params(args.start, args.end))
    payload = resp.json()

    (out_dir / f"{stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    df = clip_local_range(response_to_frame(payload), args.start, args.end)
    df.to_csv(out_dir / f"{stem}.csv", index=False)
    log.info("Đã lưu %s dòng → %s", f"{len(df):,}", out_dir / f"{stem}.csv")
    log.info("Số dòng theo điểm:\n%s", df.groupby("station_id").size().to_string())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
