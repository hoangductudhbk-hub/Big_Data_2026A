"""Làm sạch dữ liệu thời tiết (Open-Meteo)."""
from __future__ import annotations

import pandas as pd

from common.contract import wmo_to_condition
from data_integration.cleaning.common import CleaningLog, normalize_district

NUMERIC = ["temperature_2m", "precipitation", "rain", "snowfall", "weather_code"]


def clean_weather(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog("weather", rows_in=len(raw))
    df = raw.copy()

    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["time_local"], errors="coerce")
    df["district"] = normalize_district(df["district"])

    bad = df[["timestamp", "district"] + NUMERIC].isna().any(axis=1)
    log.add("Thiếu thời gian, quận hoặc chỉ số đo", bad.sum(), "loại bỏ")
    df = df[~bad]

    out_of_range = ~df["temperature_2m"].between(-40, 50) | (df[["precipitation", "rain", "snowfall"]] < 0).any(axis=1)
    log.add("Nhiệt độ ngoài [-40, 50] °C hoặc mưa/tuyết âm", out_of_range.sum(), "loại bỏ")
    df = df[~out_of_range]

    # Ngày lùi giờ: cùng 1 giờ địa phương có 2 bản ghi → gộp (trung bình số đo, mã thời tiết lấy mức nặng hơn)
    dup = df.duplicated(["station_id", "timestamp"], keep=False)
    log.add("Trùng (trạm, giờ địa phương) do lùi giờ 03/11", dup.sum(), "gộp 2 → 1",
            "Số đo lấy trung bình; weather_code lấy giá trị lớn hơn (thời tiết xấu hơn)")
    df = (df.groupby(["station_id", "district", "timestamp"], as_index=False)
            .agg(temperature=("temperature_2m", "mean"), precipitation=("precipitation", "mean"),
                 rainfall=("rain", "mean"), snowfall=("snowfall", "mean"), weather_code=("weather_code", "max")))

    df["weather_code"] = df["weather_code"].astype("int64")
    df["weather_condition"] = df["weather_code"].map(wmo_to_condition)
    unmapped = df["weather_condition"].isna()
    log.add("Mã WMO không thuộc nhóm nào", unmapped.sum(), "giữ lại, weather_condition = null")
    log.add("Đổi tên cột theo contract", len(df), "đổi tên",
            "temperature_2m → temperature, rain → rainfall, time_local → timestamp")

    df = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    log.rows_out = len(df)
    return df, log
