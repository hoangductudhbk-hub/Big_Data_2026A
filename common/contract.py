"""
Data contract của bảng integrated_traffic.

Đây là "giao diện" giữa Phase 1 (Data Integration) và Phase 2 (PySpark):
- Phase 1 PHẢI xuất dữ liệu đúng schema này.
- Phase 2 CHỈ được giả định những gì ghi trong file này.

Mọi thay đổi schema phải sửa ở đây, tăng CONTRACT_VERSION và cập nhật
docs/data_contract.md.
"""
from __future__ import annotations

from dataclasses import dataclass

CONTRACT_VERSION = "1.0.0"

# Hằng số đổi đơn vị dùng chung
MPH_TO_KMH = 1.609344

# Giá trị hợp lệ
DISTRICTS = ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island")
WEATHER_CONDITIONS = ("Clear", "Cloudy", "Fog", "Drizzle", "Rain", "Snow", "Thunderstorm")
SOURCES = ("speeds", "volume", "speeds+volume")

# Khung tọa độ bao New York (WGS84) để phát hiện tọa độ sai
NYC_BBOX = {"lat_min": 40.45, "lat_max": 40.95, "lon_min": -74.30, "lon_max": -73.65}


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str            # kiểu logic: string | long | double | timestamp
    nullable: bool
    unit: str
    description: str
    min_value: float | None = None
    max_value: float | None = None
    allowed: tuple[str, ...] | None = None


INTEGRATED_TRAFFIC: tuple[Column, ...] = (
    Column("road_id", "string", False, "-",
           "Mã đường thống nhất sau record linkage. 'L<link_id>' nếu đường có cảm biến tốc độ, "
           "'S<segmentid>' nếu chỉ có điểm đếm lưu lượng"),
    Column("road_name", "string", False, "-", "Tên đường đã chuẩn hóa (chữ in hoa, bỏ viết tắt)"),
    Column("district", "string", False, "-", "Quận (borough) của New York", allowed=DISTRICTS),
    Column("latitude", "double", False, "độ (WGS84)", "Vĩ độ điểm đại diện của đường",
           NYC_BBOX["lat_min"], NYC_BBOX["lat_max"]),
    Column("longitude", "double", False, "độ (WGS84)", "Kinh độ điểm đại diện của đường",
           NYC_BBOX["lon_min"], NYC_BBOX["lon_max"]),
    Column("timestamp", "timestamp", False, "giờ New York",
           "Thời điểm BẮT ĐẦU khung 1 giờ, giờ địa phương America/New_York, không kèm múi giờ"),
    Column("vehicle_count", "long", True, "xe/giờ",
           "Tổng số xe trong giờ (cộng 4 khung 15 phút, mọi hướng). Null nếu đường không có điểm đếm",
           0, 20000),
    Column("avg_speed", "double", True, "km/h",
           "Tốc độ trung bình trong giờ (đã đổi từ mph). Null nếu đường không có cảm biến tốc độ",
           0, 160),
    Column("temperature", "double", True, "°C", "Nhiệt độ không khí 2m", -40, 50),
    Column("rainfall", "double", True, "mm", "Lượng mưa trong giờ (không gồm tuyết)", 0, 200),
    Column("snowfall", "double", True, "cm", "Lượng tuyết rơi trong giờ", 0, 50),
    Column("weather_condition", "string", True, "-", "Nhóm thời tiết suy ra từ mã WMO",
           allowed=WEATHER_CONDITIONS),
    Column("weather_station_id", "string", True, "-", "Điểm thời tiết đã ghép (theo quận)"),
    Column("source", "string", False, "-", "Nguồn đóng góp cho bản ghi", allowed=SOURCES),
)

PRIMARY_KEY = ("road_id", "timestamp")
COLUMN_NAMES = tuple(c.name for c in INTEGRATED_TRAFFIC)


def wmo_to_condition(code: int | None) -> str | None:
    """Đổi mã thời tiết WMO (Open-Meteo weather_code) sang nhóm thời tiết của contract."""
    if code is None:
        return None
    code = int(code)
    if code in (0, 1):
        return "Clear"
    if code in (2, 3):
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if 51 <= code <= 57:
        return "Drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "Rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "Snow"
    if 95 <= code <= 99:
        return "Thunderstorm"
    return None


# ---------------------------------------------------------------------------
# Schema cho từng công cụ
# ---------------------------------------------------------------------------
def spark_schema():
    """StructType cho PySpark (import trễ để module dùng được khi chưa cài Spark)."""
    from pyspark.sql import types as T

    mapping = {
        "string": T.StringType(),
        "long": T.LongType(),
        "double": T.DoubleType(),
        "timestamp": T.TimestampNTZType(),   # không múi giờ: giờ địa phương New York
    }
    return T.StructType([T.StructField(c.name, mapping[c.dtype], c.nullable) for c in INTEGRATED_TRAFFIC])


def arrow_schema():
    """Schema pyarrow để ghi Parquet bằng pandas."""
    import pyarrow as pa

    mapping = {
        "string": pa.string(),
        "long": pa.int64(),
        "double": pa.float64(),
        "timestamp": pa.timestamp("us"),
    }
    return pa.schema([pa.field(c.name, mapping[c.dtype], nullable=c.nullable) for c in INTEGRATED_TRAFFIC])


# ---------------------------------------------------------------------------
# Kiểm tra dữ liệu theo contract (dùng cho pandas DataFrame)
# ---------------------------------------------------------------------------
def validate_pandas(df) -> list[str]:
    """Trả về danh sách lỗi. Danh sách rỗng nghĩa là dữ liệu đạt contract."""
    import pandas as pd

    errors: list[str] = []

    missing = [c for c in COLUMN_NAMES if c not in df.columns]
    extra = [c for c in df.columns if c not in COLUMN_NAMES]
    if missing:
        errors.append(f"Thiếu cột: {missing}")
    if extra:
        errors.append(f"Thừa cột: {extra}")
    if missing:
        return errors

    for c in INTEGRATED_TRAFFIC:
        s = df[c.name]
        if not c.nullable and s.isna().any():
            errors.append(f"{c.name}: có {int(s.isna().sum())} giá trị null nhưng cột không cho phép null")
        if c.dtype == "timestamp" and not pd.api.types.is_datetime64_any_dtype(s):
            errors.append(f"{c.name}: kiểu {s.dtype}, cần datetime")
        if c.dtype in ("long", "double") and not pd.api.types.is_numeric_dtype(s):
            errors.append(f"{c.name}: kiểu {s.dtype}, cần số")
        if c.min_value is not None and (s < c.min_value).any():
            errors.append(f"{c.name}: có {int((s < c.min_value).sum())} giá trị < {c.min_value}")
        if c.max_value is not None and (s > c.max_value).any():
            errors.append(f"{c.name}: có {int((s > c.max_value).sum())} giá trị > {c.max_value}")
        if c.allowed is not None:
            bad = s.dropna()[~s.dropna().isin(c.allowed)]
            if len(bad):
                errors.append(f"{c.name}: giá trị không hợp lệ {sorted(bad.unique())[:5]}")

    if pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        ts = df["timestamp"]
        not_hour = ts.notna() & (ts != ts.dt.floor("h"))
        if not_hour.any():
            errors.append(f"timestamp: có {int(not_hour.sum())} giá trị không tròn giờ")

    both_null = df["vehicle_count"].isna() & df["avg_speed"].isna()
    if both_null.any():
        errors.append(f"Có {int(both_null.sum())} dòng thiếu cả vehicle_count lẫn avg_speed")

    dup = df.duplicated(subset=list(PRIMARY_KEY)).sum()
    if dup:
        errors.append(f"Khóa chính {PRIMARY_KEY} bị trùng {int(dup)} dòng")

    return errors
