"""
Profiling riêng cho từng nguồn dữ liệu raw.

Mỗi hàm trả về dict gồm:
    rows, columns (profile từng cột), checks (danh sách kiểm tra chất lượng), tables (bảng phụ dạng Markdown)
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from common.contract import NYC_BBOX, wmo_to_condition
from data_integration.profiling.core import check, iqr_outliers, is_empty, profile_frame

MPH_IMPLAUSIBLE = 100           # tốc độ > 100 mph trong đô thị coi là bất hợp lý
STREET_SUFFIX_VARIANTS = {
    "AVENUE": ["AV", "AVE", "AVENUE"],
    "STREET": ["ST", "STR", "STREET"],
    "BOULEVARD": ["BLVD", "BL", "BOULEVARD"],
    "PLACE": ["PL", "PLACE"],
    "ROAD": ["RD", "ROAD"],
    "EXPRESSWAY": ["EXPY", "EXPWY", "EXP", "EXPRESSWAY"],
    "PARKWAY": ["PKWY", "PKY", "PARKWAY"],
}


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f"{v:,}" if isinstance(v, (int, np.integer)) else
                                       (f"{v:,.2f}" if isinstance(v, (float, np.floating)) else str(v))
                                       for v in r.values) + " |")
    return "\n".join(lines)


# ===========================================================================
# 1. Thời tiết (Open-Meteo)
# ===========================================================================
def profile_weather(path: Path, start: str, end: str) -> dict:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    n = len(df)
    checks = []
    expected_hours = len(pd.date_range(start, pd.Timestamp(end) + pd.Timedelta(hours=23), freq="h"))

    per_station = df.groupby("station_id").size()
    for sid, cnt in per_station.items():
        checks.append(check(f"Số giờ của {sid}", cnt, None, f"kỳ vọng {expected_hours:,}"))

    utc = pd.to_datetime(df["time_utc"], errors="coerce")
    local = pd.to_datetime(df["time_local"], errors="coerce")
    checks.append(check("time_utc không đọc được", int(utc.isna().sum()), n))
    checks.append(check("Trùng (station, time_utc)", int(df.assign(t=utc).duplicated(["station_id", "t"]).sum()), n))
    dup_local = df.assign(t=local).duplicated(["station_id", "t"], keep=False)
    checks.append(check("Trùng (station, time_local)", int(dup_local.sum()), n,
                        "Do lùi giờ mùa đông: 01:00 xuất hiện 2 lần" if dup_local.any() else ""))
    if dup_local.any():
        days = sorted(local[dup_local].dt.strftime("%Y-%m-%d %H:%M").unique())
        checks[-1]["note"] += f" ({', '.join(days)})"

    lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23)
    checks.append(check("Giờ địa phương nằm ngoài phạm vi nghiên cứu", int((~local.between(lo, hi)).sum()), n,
                        f"phạm vi {lo:%Y-%m-%d %H:%M} → {hi:%Y-%m-%d %H:%M}"))
    expected_local = pd.date_range(lo, hi, freq="h")
    missing_local = 0
    for _, g in df.assign(t=local).groupby("station_id"):
        missing_local += len(expected_local.difference(pd.DatetimeIndex(g["t"].dropna().unique())))
    checks.append(check("Giờ địa phương bị thiếu (tính cả 5 trạm)", missing_local, None,
                        "Ngày đổi giờ 10/03 không có 02:00 nên mỗi trạm thiếu 1 giờ là bình thường"))

    gaps = 0
    for _, g in df.assign(t=utc).groupby("station_id"):
        gaps += int((g["t"].sort_values().diff().dropna() != pd.Timedelta(hours=1)).sum())
    checks.append(check("Khoảng trống giữa 2 giờ liên tiếp (theo UTC)", gaps, n))

    num = {c: pd.to_numeric(df[c], errors="coerce") for c in
           ("temperature_2m", "precipitation", "rain", "snowfall", "weather_code")}
    for c, s in num.items():
        checks.append(check(f"{c} rỗng/không phải số", int(s.isna().sum()), n))
    checks.append(check("temperature_2m ngoài [-40, 50] °C",
                        int(((num["temperature_2m"] < -40) | (num["temperature_2m"] > 50)).sum()), n))
    checks.append(check("Lượng mưa/tuyết âm",
                        int(((num["precipitation"] < 0) | (num["rain"] < 0) | (num["snowfall"] < 0)).sum()), n))
    checks.append(check("rain > precipitation (mâu thuẫn)",
                        int((num["rain"] > num["precipitation"] + 0.01).sum()), n,
                        "precipitation = rain + showers + tuyết quy ra nước"))

    cond = num["weather_code"].map(lambda c: wmo_to_condition(c) if pd.notna(c) else None)
    cond_tbl = (pd.DataFrame({"condition": cond.fillna("(không map được)"), "code": num["weather_code"]})
                .groupby("condition").agg(so_gio=("code", "size"),
                                          ma_wmo=("code", lambda s: ",".join(str(int(x)) for x in sorted(s.dropna().unique()))))
                .sort_values("so_gio", ascending=False).reset_index())
    cond_tbl["ti_le_%"] = (100 * cond_tbl["so_gio"] / n).round(2)

    monthly = (pd.DataFrame({"month": local.dt.strftime("%Y-%m"), "t": num["temperature_2m"],
                             "rain": num["rain"], "snow": num["snowfall"]})
               .groupby("month").agg(nhiet_do_tb=("t", "mean"), mua_mm=("rain", "sum"), tuyet_cm=("snow", "sum"))
               .round(1).reset_index())
    monthly["mua_mm"] = (monthly["mua_mm"] / df["station_id"].nunique()).round(1)
    monthly["tuyet_cm"] = (monthly["tuyet_cm"] / df["station_id"].nunique()).round(1)

    return {
        "rows": n, "columns": profile_frame(df), "checks": checks,
        "tables": {
            "Phân bố nhóm thời tiết (sau khi map mã WMO)": _md_table(cond_tbl),
            "Khí hậu theo tháng (trung bình 5 quận)": _md_table(monthly),
        },
    }


# ===========================================================================
# 2. Lưu lượng (Automated Traffic Volume Counts)
# ===========================================================================
POINT_RE = re.compile(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)")


def _state_plane_to_wgs84(x: pd.Series, y: pd.Series):
    try:
        from pyproj import Transformer
    except ImportError:
        return None, None
    tf = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(x.to_numpy(), y.to_numpy())
    return pd.Series(lat, index=x.index), pd.Series(lon, index=x.index)


def street_suffix_table(names: pd.Series) -> pd.DataFrame:
    tokens = names.str.upper().str.split().str[-1].value_counts()
    rows = []
    for canon, variants in STREET_SUFFIX_VARIANTS.items():
        found = {v: int(tokens.get(v, 0)) for v in variants if tokens.get(v, 0)}
        if found:
            rows.append({"chuan": canon, "cach_viet_gap": ", ".join(f"{k} ({v})" for k, v in found.items()),
                         "so_kieu_viet": len(found)})
    return pd.DataFrame(rows)


def profile_volume(path: Path) -> dict:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    n = len(df)
    checks = []

    ints = {c: pd.to_numeric(df[c], errors="coerce") for c in ("yr", "m", "d", "hh", "mm", "vol")}
    ts = pd.to_datetime(dict(year=ints["yr"], month=ints["m"], day=ints["d"], hour=ints["hh"], minute=ints["mm"]),
                        errors="coerce")
    checks.append(check("Thời gian (yr,m,d,hh,mm) không hợp lệ", int(ts.isna().sum()), n))
    checks.append(check("Phút không thuộc {0,15,30,45}", int((~ints["mm"].isin([0, 15, 30, 45])).sum()), n))
    checks.append(check("Giờ ngoài 0–23", int((~ints["hh"].between(0, 23)).sum()), n))

    vol = ints["vol"]
    checks.append(check("vol rỗng/không phải số", int(vol.isna().sum()), n))
    checks.append(check("vol âm", int((vol < 0).sum()), n))
    checks.append(check("vol = 0", int((vol == 0).sum()), n, "Có thể hợp lệ (ban đêm, đường nhỏ)"))
    out_n, lo, hi = iqr_outliers(vol)
    checks.append(check("vol ngoại lai mạnh (ngoài Q1−3·IQR … Q3+3·IQR)", out_n, n,
                        f"ngưỡng trên ≈ {hi:,.0f} xe/15 phút"))

    checks.append(check("Trùng toàn bộ dòng", int(df.duplicated().sum()), n))
    key = ["segmentid", "direction"]
    keyed = df.assign(ts=ts)
    dup_key = keyed.duplicated(key + ["ts"], keep=False)
    checks.append(check("Trùng khóa (segmentid, direction, thời gian)", int(keyed.duplicated(key + ["ts"]).sum()), n))
    conflict = keyed[dup_key].assign(vol=vol[dup_key]).groupby(key + ["ts"])["vol"].nunique()
    checks.append(check("…trong đó khác giá trị vol (mâu thuẫn)", int((conflict > 1).sum()), n,
                        "Nhiều đợt khảo sát (requestid) đo cùng đoạn, cùng lúc"))

    for c in ("boro", "street", "segmentid", "wktgeom", "direction"):
        checks.append(check(f"{c} rỗng", int(is_empty(df[c]).sum()), n))

    m = df["wktgeom"].str.extract(POINT_RE)
    x, y = pd.to_numeric(m[0], errors="coerce"), pd.to_numeric(m[1], errors="coerce")
    checks.append(check("wktgeom không đọc được dạng POINT(x y)", int(x.isna().sum()), n))
    lat, lon = _state_plane_to_wgs84(x.fillna(0), y.fillna(0))
    if lat is not None:
        outside = x.notna() & ~(lat.between(NYC_BBOX["lat_min"], NYC_BBOX["lat_max"])
                                & lon.between(NYC_BBOX["lon_min"], NYC_BBOX["lon_max"]))
        checks.append(check("Tọa độ (sau khi đổi EPSG:2263 → WGS84) nằm ngoài New York", int(outside.sum()), n))

    for c in ("street", "fromst", "tost"):
        v = df[c].drop_duplicates()
        variants = int(v.groupby(v.str.upper().str.strip()).size().gt(1).sum())
        checks.append(check(f"{c}: cùng tên nhưng khác chữ hoa/thường", variants, None,
                            "số tên có từ 2 cách viết trở lên, ví dụ 'Dead End' / 'Dead end'"))
    geo_per_seg = df.groupby("segmentid")["wktgeom"].nunique()
    checks.append(check("segmentid có nhiều hơn 1 tọa độ", int((geo_per_seg > 1).sum()), None))

    # Mức độ đầy đủ: mỗi đợt khảo sát × đoạn × hướng phải có đủ các khung 15 phút liên tục
    # Chỉ đếm các mốc DUY NHẤT nằm đúng lưới 15 phút (dòng trùng hay phút lệch không được che khung thiếu)
    on_grid = keyed.dropna(subset=["ts"])
    on_grid = on_grid[on_grid["ts"].dt.minute.isin([0, 15, 30, 45])]
    g = on_grid.groupby(["requestid", "segmentid", "direction"])["ts"]
    span = g.agg(["min", "max", "nunique"]).rename(columns={"nunique": "count"})
    expected = ((span["max"] - span["min"]) / pd.Timedelta(minutes=15) + 1).astype(int)
    missing_slots = int((expected - span["count"]).clip(lower=0).sum())
    checks.append(check("Khung 15 phút bị thiếu bên trong các đợt đếm", missing_slots, int(expected.sum()),
                        "so với số khung kỳ vọng từ lúc bắt đầu đến lúc kết thúc mỗi đợt"))

    coverage = pd.DataFrame({
        "chi_so": ["Số đợt khảo sát (requestid)", "Số đoạn đường (segmentid)", "Số tên phố (street)",
                   "Số ngày trung bình mỗi đợt", "Ngày sớm nhất", "Ngày muộn nhất"],
        "gia_tri": [df["requestid"].nunique(), df["segmentid"].nunique(), df["street"].nunique(),
                    round(float(((span["max"] - span["min"]).dt.total_seconds() / 86400).mean()), 1),
                    str(ts.min()), str(ts.max())],
    })
    boro = df["boro"].value_counts().rename_axis("boro").reset_index(name="so_dong")
    by_month = ts.dt.strftime("%Y-%m").value_counts().sort_index().rename_axis("thang").reset_index(name="so_dong")

    return {
        "rows": n, "columns": profile_frame(df), "checks": checks,
        "tables": {
            "Phạm vi bao phủ": _md_table(coverage),
            "Số dòng theo quận (giá trị gốc của cột boro)": _md_table(boro),
            "Số dòng theo tháng": _md_table(by_month),
            "Cách viết hậu tố tên phố không thống nhất (cột street)": _md_table(street_suffix_table(df["street"])),
        },
    }


# ===========================================================================
# 3. Tốc độ (DOT Traffic Speeds) — 12 file tháng, xử lý từng file để tiết kiệm bộ nhớ
# ===========================================================================
SPEED_COLS = ["id", "speed", "travel_time", "status", "data_as_of", "link_id", "borough", "link_name"]


def profile_speeds(raw_dir: Path) -> dict:
    files = sorted(raw_dir.glob("speeds_*.csv"))
    links = pd.read_csv(raw_dir / "links.csv", dtype=str, keep_default_na=False) \
        if (raw_dir / "links.csv").exists() else pd.DataFrame(columns=["link_id", "link_name", "borough"])
    link_name = links.set_index("link_id")["link_name"].to_dict()

    monthly, totals = [], {}
    speed_samples, status_counts, borough_counts = [], pd.Series(dtype="int64"), pd.Series(dtype="int64")
    per_link_rows = pd.Series(dtype="int64")
    crosstab = pd.Series(dtype="int64")
    daily = []
    names_seen: set[str] = set()
    intervals = []
    dst_rows = {}

    def add(k, v):
        totals[k] = totals.get(k, 0) + int(v)

    for f in files:
        month = f.stem.replace("speeds_", "")
        df = pd.read_csv(f, dtype=str, keep_default_na=False, usecols=lambda c: c in SPEED_COLS)
        n = len(df)
        add("rows", n)

        speed = pd.to_numeric(df["speed"], errors="coerce")
        tt = pd.to_numeric(df["travel_time"], errors="coerce")
        t = pd.to_datetime(df["data_as_of"], errors="coerce", format="ISO8601")
        mstart = pd.Period(month, freq="M").start_time
        mend = mstart + pd.offsets.MonthBegin(1)

        bad_speed = speed.isna()
        zero_both = (speed == 0) & (tt == 0)
        status_nonzero = df["status"] != "0"
        too_fast = speed > MPH_IMPLAUSIBLE
        bad_time = t.isna()
        outside = t.notna() & ((t < mstart) | (t >= mend))
        full_dup = df.duplicated()
        key_dup = df.assign(t=t).duplicated(["link_id", "t"])
        unknown_link = ~df["link_id"].isin(link_name.keys()) if link_name else pd.Series(False, index=df.index)
        name_mismatch = df["link_id"].map(link_name).notna() & (df["link_id"].map(link_name) != df["link_name"])

        for k, s in [("speed_not_numeric", bad_speed), ("speed_zero_traveltime_zero", zero_both),
                     ("status_nonzero", status_nonzero), ("speed_gt_100mph", too_fast),
                     ("time_unparseable", bad_time), ("time_outside_month", outside),
                     ("full_duplicate", full_dup), ("key_duplicate", key_dup),
                     ("unknown_link", unknown_link), ("link_name_mismatch", name_mismatch),
                     ("speed_negative", speed < 0)]:
            add(k, s.sum())

        valid = ~(bad_speed | zero_both | status_nonzero | bad_time | outside)
        status_counts = status_counts.add(df["status"].value_counts(), fill_value=0)
        borough_counts = borough_counts.add(df["borough"].value_counts(), fill_value=0)
        per_link_rows = per_link_rows.add(df["link_id"].value_counts(), fill_value=0)

        ct = pd.Series(list(zip(df["status"], zero_both))).value_counts()
        crosstab = crosstab.add(ct, fill_value=0)
        names_seen.update(df["link_name"].unique())

        sp = speed[valid]
        speed_samples.append(sp.sample(min(len(sp), 100_000), random_state=0))

        # Khoảng cách giữa 2 lần đo liên tiếp của cùng tuyến (phút)
        tv = pd.DataFrame({"link": df["link_id"][valid], "t": t[valid]}).drop_duplicates().sort_values(["link", "t"])
        d = tv.groupby("link")["t"].diff().dt.total_seconds().div(60).dropna()
        intervals.append(d.sample(min(len(d), 200_000), random_state=0))

        # Độ phủ theo giờ: tỉ lệ cặp (tuyến, giờ) có ít nhất 1 bản ghi hợp lệ
        hours_in_month = int((mend - mstart) / pd.Timedelta(hours=1))
        active_links = tv["link"].nunique()
        covered = tv.assign(h=tv["t"].dt.floor("h")).drop_duplicates(["link", "h"]).shape[0]
        coverage = 100 * covered / (active_links * hours_in_month) if active_links else 0.0

        day_cov = (tv.assign(d=tv["t"].dt.floor("D"), h=tv["t"].dt.floor("h"))
                   .drop_duplicates(["link", "h"]).groupby("d").size() / (active_links * 24) * 100)
        all_days = pd.date_range(mstart, mend - pd.Timedelta(days=1), freq="D")
        daily.append(day_cov.reindex(all_days, fill_value=0.0))

        if month == "2024-11":
            day = t.dt.strftime("%Y-%m-%d") == "2024-11-03"
            dst_rows = t[day].dt.hour.value_counts().sort_index().to_dict()

        monthly.append({
            "thang": month, "so_dong": n, "so_tuyen": int(df["link_id"].nunique()),
            "khong_hop_le": int((~valid).sum()), "ti_le_khong_hop_le_%": round(100 * float((~valid).mean()), 2) if n else 0,
            "trung_khoa": int(key_dup.sum()), "do_phu_gio_%": round(coverage, 1),
        })

    total = totals.get("rows", 0)
    names = {
        "speed_not_numeric": "speed rỗng/không phải số",
        "speed_negative": "speed âm",
        "speed_zero_traveltime_zero": "speed = 0 và travel_time = 0 (bản ghi rỗng)",
        "status_nonzero": "status khác 0",
        "speed_gt_100mph": f"speed > {MPH_IMPLAUSIBLE} mph (bất hợp lý)",
        "time_unparseable": "data_as_of không đọc được",
        "time_outside_month": "data_as_of nằm ngoài tháng của file",
        "full_duplicate": "Trùng toàn bộ dòng",
        "key_duplicate": "Trùng khóa (link_id, data_as_of)",
        "unknown_link": "link_id không có trong links.csv",
        "link_name_mismatch": "link_name khác với tên trong links.csv",
    }
    checks = [check(v, totals.get(k, 0), total) for k, v in names.items()]

    sp = pd.concat(speed_samples) if speed_samples else pd.Series(dtype=float)
    iv = pd.concat(intervals) if intervals else pd.Series(dtype=float)
    stats = pd.DataFrame({
        "chi_so": ["Tốc độ hợp lệ: trung vị (mph)", "Tốc độ hợp lệ: p01 – p99 (mph)",
                   "Khoảng cách giữa 2 lần đo: trung vị (phút)", "Khoảng cách: p90 (phút)",
                   "Khoảng cách: lớn nhất trong mẫu (giờ)", "Số tuyến (link_id) xuất hiện",
                   "Số bản ghi mỗi tuyến: ít nhất – nhiều nhất"],
        "gia_tri": [f"{sp.median():.1f}" if len(sp) else "",
                    f"{sp.quantile(.01):.1f} – {sp.quantile(.99):.1f}" if len(sp) else "",
                    f"{iv.median():.1f}" if len(iv) else "", f"{iv.quantile(.9):.1f}" if len(iv) else "",
                    f"{iv.max() / 60:.1f}" if len(iv) else "", f"{len(per_link_rows):,}",
                    f"{int(per_link_rows.min()):,} – {int(per_link_rows.max()):,}" if len(per_link_rows) else ""],
    })
    tables = {
        "Theo tháng": _md_table(pd.DataFrame(monthly)),
        "Chỉ số tổng hợp": _md_table(stats),
        "Phân bố status": _md_table(status_counts.astype(int).sort_values(ascending=False)
                                    .rename_axis("status").reset_index(name="so_dong")),
        "Phân bố borough (giá trị gốc)": _md_table(borough_counts.astype(int).sort_values(ascending=False)
                                                    .rename_axis("borough").reset_index(name="so_dong")),
    }
    ct = crosstab.astype(int).reset_index()
    ct.columns = ["key", "so_dong"]
    ct["status"] = ct["key"].str[0]
    ct["speed=0 & travel_time=0"] = ct["key"].str[1].map({True: "có", False: "không"})
    tables["Đối chiếu status với bản ghi rỗng (speed = 0 và travel_time = 0)"] = _md_table(
        ct[["status", "speed=0 & travel_time=0", "so_dong"]].sort_values(["status", "so_dong"]))

    if daily:
        dc = pd.concat(daily)
        low = dc[dc < 50]
        runs, cur = [], None
        for d, v in low.items():                      # gộp các ngày liên tiếp thành 1 khoảng
            if cur and d - cur[1] == pd.Timedelta(days=1):
                cur = (cur[0], d, cur[2] + [v])
            else:
                if cur:
                    runs.append(cur)
                cur = (d, d, [v])
        if cur:
            runs.append(cur)
        tables["Các khoảng ngày bị mất dữ liệu (độ phủ giờ < 50%)"] = _md_table(pd.DataFrame(
            [{"tu_ngay": f"{a:%Y-%m-%d}", "den_ngay": f"{b:%Y-%m-%d}", "so_ngay": len(v),
              "do_phu_tb_%": round(float(np.mean(v)), 1)} for a, b, v in runs])) if runs else "Không có."
        totals["days_low_coverage"] = int(len(low))
        checks.append(check("Số ngày có độ phủ giờ < 50%", len(low), len(dc)))

    tok = (pd.Series(sorted(names_seen)).str.upper().str.findall(r"[A-Z0-9]+").explode()
           .value_counts().astype(int).sort_values(ascending=False))
    tok = tok[~tok.index.str.fullmatch(r"\d+")].head(30)
    tables["Các từ xuất hiện nhiều trong link_name (nhiều từ viết tắt)"] = _md_table(
        tok.rename_axis("tu").reset_index(name="so_tuyen"))

    if dst_rows:
        tables["Ngày lùi giờ 03/11/2024: số bản ghi theo giờ địa phương"] = _md_table(
            pd.DataFrame({"gio": list(dst_rows.keys()), "so_dong": list(dst_rows.values())}))
    return {"rows": total, "files": [f.name for f in files], "columns": {}, "checks": checks, "tables": tables}
