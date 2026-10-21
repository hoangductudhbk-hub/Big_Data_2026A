"""Kiểm tra từng bản ghi gửi lên theo data contract (common/contract.py).

Cùng một nguồn quy tắc với Phase 1 (validate_pandas) và với ràng buộc CHECK trong database,
nên dữ liệu đi vào bằng API không thể "lỏng" hơn dữ liệu đi vào bằng pipeline.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from common.contract import INTEGRATED_TRAFFIC, WEATHER_CONDITIONS

NY = ZoneInfo("America/New_York")
_COLS = {c.name: c for c in INTEGRATED_TRAFFIC}


def to_local_naive(ts: datetime) -> datetime:
    """Contract: giờ địa phương New York, không múi giờ. Có múi giờ → đổi sang New York rồi bỏ múi giờ."""
    return ts.astimezone(NY).replace(tzinfo=None) if ts.tzinfo else ts


def check_value(name: str, value) -> str | None:
    c = _COLS[name]
    if value is None:
        return None if c.nullable else f"{name}: bắt buộc"
    if c.min_value is not None and value < c.min_value:
        return f"{name}={value} nhỏ hơn {c.min_value} {c.unit}"
    if c.max_value is not None and value > c.max_value:
        return f"{name}={value} lớn hơn {c.max_value} {c.unit}"
    if c.allowed and value not in c.allowed:
        return f"{name}='{value}' không thuộc {list(c.allowed)}"
    return None


def derive_source(rec: dict) -> str:
    has_s, has_v = rec.get("avg_speed") is not None, rec.get("vehicle_count") is not None
    return "speeds+volume" if has_s and has_v else ("speeds" if has_s else "volume")


def validate_traffic(rec: dict, road: dict | None) -> tuple[dict | None, list[str]]:
    """rec: một bản ghi (dict). road: thông tin đường đã có trong DB (None nếu đường mới).
    Trả về (bản ghi đầy đủ 14 cột, danh sách lỗi)."""
    errs: list[str] = []
    rec = dict(rec)
    rec["timestamp"] = to_local_naive(rec["timestamp"])
    if rec["timestamp"].minute or rec["timestamp"].second or rec["timestamp"].microsecond:
        errs.append("timestamp phải là đầu giờ (vd 2024-03-01T08:00:00): contract dùng khung 1 giờ")
    # Thông tin đường: lấy từ danh mục nếu đường đã có, bắt buộc gửi kèm nếu là đường mới
    for f in ("road_name", "district", "latitude", "longitude"):
        if rec.get(f) is None and road is not None:
            rec[f] = road[f]
    if road is None:
        miss = [f for f in ("road_name", "district", "latitude", "longitude") if rec.get(f) is None]
        if miss:
            errs.append(f"road_id '{rec['road_id']}' chưa có trong danh mục đường: phải gửi kèm {miss}")
    if rec.get("avg_speed") is None and rec.get("vehicle_count") is None:
        errs.append("phải có ít nhất một trong avg_speed hoặc vehicle_count")
    src = derive_source(rec)
    if rec.get("source") is None:
        rec["source"] = src
    elif rec["source"] != src and not errs:
        errs.append(f"source='{rec['source']}' mâu thuẫn với dữ liệu (theo các cột đo được phải là '{src}')")
    for name in _COLS:
        if name in ("road_name", "district", "latitude", "longitude") and road is None and rec.get(name) is None:
            continue   # đã báo lỗi thiếu thông tin đường ở trên
        e = check_value(name, rec.get(name))
        if e:
            errs.append(e)
    return (None, errs) if errs else ({k: rec.get(k) for k in _COLS}, [])


def validate_weather(rec: dict) -> tuple[dict | None, list[str]]:
    errs: list[str] = []
    rec = dict(rec)
    rec["timestamp"] = to_local_naive(rec["timestamp"])
    for f in ("rainfall", "snowfall", "precipitation"):
        if rec.get(f) is not None and rec[f] < 0:
            errs.append(f"{f}={rec[f]} không được âm")
    if rec.get("temperature") is not None and not -40 <= rec["temperature"] <= 50:
        errs.append(f"temperature={rec['temperature']} ngoài khoảng [-40, 50] °C")
    if rec.get("weather_condition") is not None and rec["weather_condition"] not in WEATHER_CONDITIONS:
        errs.append(f"weather_condition='{rec['weather_condition']}' không thuộc {list(WEATHER_CONDITIONS)}")
    return (None, errs) if errs else (rec, [])
