"""Làm sạch dữ liệu lưu lượng (Automated Traffic Volume Counts)."""
from __future__ import annotations

import pandas as pd

from data_integration.cleaning.common import CleaningLog, normalize_district, normalize_text
from data_integration.profiling.core import iqr_outliers

POINT = r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)"


def state_plane_to_wgs84(x: pd.Series, y: pd.Series) -> tuple[pd.Series, pd.Series]:
    """NY State Plane Long Island (EPSG:2263, đơn vị feet) → WGS84 (EPSG:4326)."""
    from pyproj import Transformer
    tf = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(x.to_numpy(dtype=float), y.to_numpy(dtype=float))
    return pd.Series(lat, index=x.index), pd.Series(lon, index=x.index)


def clean_volume(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog("volume", rows_in=len(raw))
    df = raw.copy()

    for c in ("yr", "m", "d", "hh", "mm", "vol"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["timestamp"] = pd.to_datetime(dict(year=df["yr"], month=df["m"], day=df["d"],
                                          hour=df["hh"], minute=df["mm"]), errors="coerce")
    bad = df["timestamp"].isna() | ~df["mm"].isin([0, 15, 30, 45]) | df["vol"].isna() | (df["vol"] < 0)
    log.add("Thời gian không hợp lệ, phút lệch lưới 15', vol rỗng hoặc âm", bad.sum(), "loại bỏ")
    df = df[~bad].copy()

    df["district"] = normalize_district(df["boro"])
    no_district = df["district"].isna()
    log.add("Tên quận không thuộc 5 quận chuẩn", no_district.sum(), "loại bỏ")
    df = df[~no_district].copy()

    for c in ("street", "fromst", "tost", "direction"):
        before = df[c].copy()
        df[c] = normalize_text(df[c])
        log.add(f"Chuẩn hóa chữ hoa và khoảng trắng: {c}", int((before != df[c]).sum()), "sửa")

    xy = df["wktgeom"].str.extract(POINT)
    x, y = pd.to_numeric(xy[0], errors="coerce"), pd.to_numeric(xy[1], errors="coerce")
    no_geo = x.isna() | y.isna()
    log.add("wktgeom không đọc được", no_geo.sum(), "loại bỏ")
    df, x, y = df[~no_geo].copy(), x[~no_geo], y[~no_geo]
    df["latitude"], df["longitude"] = state_plane_to_wgs84(x, y)
    log.add("Đổi tọa độ EPSG:2263 (feet) → WGS84 (lat/lon)", len(df), "chuyển đổi", "dùng pyproj")

    # 1 đoạn có thể có >1 tọa độ (đã thấy ở profiling) → dùng tọa độ trung bình của đoạn
    multi_geo = df.groupby("segmentid")["wktgeom"].transform("nunique") > 1
    log.add("Đoạn có nhiều hơn 1 tọa độ", multi_geo.sum(), "thống nhất về tọa độ trung bình của đoạn")
    df[["latitude", "longitude"]] = df.groupby("segmentid")[["latitude", "longitude"]].transform("mean")

    # Nhiều đợt khảo sát cùng đo 1 đoạn, 1 hướng, 1 thời điểm → lấy trung bình
    key = ["segmentid", "direction", "timestamp"]
    dup = df.duplicated(key, keep=False)
    log.add("Trùng (đoạn, hướng, thời điểm) từ nhiều đợt khảo sát", int(df.duplicated(key).sum()),
            "gộp: vol = trung bình làm tròn", "Profiling: 379 cặp, tất cả đều khác giá trị")
    first = ["street", "fromst", "tost", "district", "latitude", "longitude"]
    df = (df.groupby(key, as_index=False)
            .agg(vol=("vol", "mean"), n_requests=("requestid", "nunique"),
                 **{c: (c, "first") for c in first}))
    df["vol"] = df["vol"].round().astype("int64")

    n_out, lo, hi = iqr_outliers(df["vol"].astype(float))
    df["flag_outlier"] = ~df["vol"].between(lo, hi)
    df["flag_zero"] = df["vol"] == 0
    log.add("vol ngoại lai mạnh (Tukey k=3)", int(df["flag_outlier"].sum()), "GIỮ LẠI, gắn cờ flag_outlier",
            f"ngưỡng [{lo:,.0f}, {hi:,.0f}] xe/15 phút; có thể là đại lộ đông thật")
    log.add("vol = 0", int(df["flag_zero"].sum()), "GIỮ LẠI, gắn cờ flag_zero")

    df["segmentid"] = df["segmentid"].astype("string")
    cols = ["segmentid", "direction", "street", "fromst", "tost", "district", "latitude", "longitude",
            "timestamp", "vol", "n_requests", "flag_outlier", "flag_zero"]
    df = df[cols].sort_values(["segmentid", "direction", "timestamp"]).reset_index(drop=True)
    log.rows_out = len(df)
    return df, log
