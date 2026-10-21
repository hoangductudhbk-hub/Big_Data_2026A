"""
Bước 18 — Nạp kết quả Phase 1 + Phase 2 (Parquet) vào PostgreSQL.

    cd backend
    alembic upgrade head                       # tạo bảng (một lần)
    python -m app.etl.load_processed           # nạp toàn bộ, chạy lại bao nhiêu lần cũng được
    python -m app.etl.load_processed --only analytics      # chỉ nạp lại kết quả Spark (bước 15–17)
    python -m app.etl.load_processed --mock                # dùng mock dataset (khi chưa có dữ liệu thật)

Luồng:  data/processed/roads.parquet           → roads
        data/interim/weather_clean.parquet     → weather_records
        data/processed/integrated_traffic/     → integrated_traffic   (kiểm tra data contract trước khi nạp)
        data/processed/analytics/*.parquet     → statistics, daily_stats, weather_impact, anomalies, anomaly_daily

Chế độ "replace": xóa dữ liệu cũ của bảng rồi nạp lại trong CÙNG MỘT transaction → không bao giờ có
trạng thái nửa cũ nửa mới; lỗi giữa chừng thì rollback, dữ liệu cũ còn nguyên.
PostgreSQL dùng lệnh COPY (nhanh hơn INSERT từng dòng hàng chục lần); SQLite (test) dùng INSERT.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Connection, Engine, func, select, text

import app  # noqa: F401  (đưa thư mục gốc project vào sys.path)
from app.core.config import settings
from app.models import (Anomaly, AnomalyDaily, DailyStat, ImportLog, IntegratedTraffic, Road, Statistic,
                        WeatherImpact, WeatherRecord)
from common.contract import COLUMN_NAMES, validate_pandas

# Thứ tự XÓA ngược với thứ tự NẠP (bảng con trước, bảng cha sau) vì có khóa ngoại tới roads
LOAD_ORDER = ("roads", "weather", "traffic", "analytics")


@dataclass
class Job:
    table: type
    source: Path
    df: pd.DataFrame


class LoadError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- đọc và chuẩn hóa từng nguồn
def read_integrated(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[[c for c in df.columns if c in COLUMN_NAMES]]          # bỏ cột partition year/month
    errors = validate_pandas(df)
    if errors:
        raise LoadError("integrated_traffic KHÔNG đạt data contract:\n- " + "\n- ".join(errors))
    return df[list(COLUMN_NAMES)]


def roads_from(path: Path | None, integrated: pd.DataFrame | None) -> pd.DataFrame:
    cols = ["road_id", "road_name", "district", "latitude", "longitude", "link_id", "segmentid", "description",
            "has_speed", "has_volume"]
    if path is not None and path.exists():
        r = pd.read_parquet(path)
        for c in cols:
            if c not in r.columns:
                r[c] = None
        return r[cols]
    if integrated is None:
        raise LoadError("Không có roads.parquet và cũng không có integrated_traffic để suy ra danh mục đường")
    # Mock / dữ liệu mới: suy danh mục đường từ chính integrated_traffic
    g = integrated.groupby("road_id")
    r = g[["road_name", "district", "latitude", "longitude"]].first().reset_index()
    r["has_speed"] = g["avg_speed"].apply(lambda s: s.notna().any()).values
    r["has_volume"] = g["vehicle_count"].apply(lambda s: s.notna().any()).values
    for c in ("link_id", "segmentid", "description"):
        r[c] = None
    return r[cols]


def read_analytics(folder: Path, suffix: str) -> list[tuple[type, Path, pd.DataFrame]]:
    def f(name):
        p = folder / f"{name}{suffix}.parquet"
        if not p.exists():
            raise LoadError(f"Thiếu {p}. Chạy Phase 2 (scripts/run_phase2.sh) trước.")
        return p, pd.read_parquet(p)

    out = []
    p, d = f("statistics")
    out.append((Statistic, p, d[["dimension", "group_key", "metric", "n", "mean", "std", "min", "max", "median"]]))
    # Bảng của bước 15–16 chỉ có cho dữ liệu thật (mock không chạy s15/s16) → bỏ qua nếu thiếu
    for name, table, rename in (
        ("daily_stats", DailyStat, {}),
        ("weather_impact", WeatherImpact, {"chieu": "dimension", "nhom": "group_key", "so_ngay": "n_days",
                                           "tb_tho": "raw_mean", "thay_doi_tho_pct": "raw_change_pct",
                                           "thay_doi_kiem_soat_pct": "controlled_change_pct",
                                           "kiem_soat_them_thang_pct": "controlled_month_change_pct",
                                           "ktc95_pct": "ci95_pct"}),
    ):
        p = folder / f"{name}{suffix}.parquet"
        if p.exists():
            d = pd.read_parquet(p).rename(columns=rename)
            if "date" in d:
                d["date"] = pd.to_datetime(d["date"]).dt.date
            out.append((table, p, d))
    p, d = f("anomalies")
    out.append((Anomaly, p, d))
    p, d = f("anomaly_daily")
    d = d.rename(columns={"ban_ghi": "records", "cham_bat_thuong": "slow_anomalies",
                          "nhanh_bat_thuong": "fast_anomalies", "ti_le_bat_thuong_pct": "anomaly_rate_pct",
                          "z_tb": "mean_z", "mua_mm_ngay": "rain_mm_per_day", "tuyet_cm_ngay": "snow_cm_per_day",
                          "do_phu_pct": "coverage_pct"})
    d["date"] = pd.to_datetime(d["date"]).dt.date
    out.append((AnomalyDaily, p, d))
    return out


# ----------------------------------------------------------------------------- ghi vào database
def _clean(df: pd.DataFrame, table: type) -> pd.DataFrame:
    cols = [c.name for c in table.__table__.columns if c.name in df.columns]
    df = df[cols].copy()
    for c in df.columns:                      # kiểu pandas → kiểu Python mà driver hiểu được (NaN/NA → None)
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.tz_localize(None) if getattr(df[c].dt, "tz", None) else df[c]
    df = df.astype(object).where(df.notna(), None)
    return df


def write(conn: Connection, table: type, df: pd.DataFrame) -> int:
    df = _clean(df, table)
    name = table.__tablename__
    if conn.dialect.name == "postgresql":
        cols = ", ".join(f'"{c}"' for c in df.columns)
        raw = conn.connection.driver_connection                       # psycopg 3 connection
        with raw.cursor() as cur, cur.copy(f'COPY {name} ({cols}) FROM STDIN') as cp:
            for row in df.itertuples(index=False, name=None):
                cp.write_row(row)
    else:
        conn.execute(table.__table__.insert(), df.to_dict("records"))
    return len(df)


def log(conn: Connection, target: str, source: str, mode: str, received: int, loaded: int, status: str,
        msg: str | None = None, started: datetime | None = None) -> None:
    conn.execute(ImportLog.__table__.insert().values(
        target=target, source=source, mode=mode, rows_received=received, rows_loaded=loaded,
        rows_rejected=received - loaded, status=status, message=msg, started_at=started or datetime.now(),
        finished_at=datetime.now()))


def load(engine: Engine, data_dir: Path, only: tuple[str, ...] = LOAD_ORDER, mock: bool = False,
         verbose: bool = True) -> dict[str, int]:
    say = print if verbose else (lambda *a, **k: None)
    processed, interim = data_dir / "processed", data_dir / "interim"
    integ_path = data_dir / "mock" / "integrated_traffic" if mock else processed / "integrated_traffic"
    integrated = read_integrated(integ_path) if ("traffic" in only or "roads" in only) else None

    jobs: list[Job] = []
    if "roads" in only:
        jobs.append(Job(Road, processed / "roads.parquet", roads_from(None if mock else processed / "roads.parquet",
                                                                      integrated)))
    if "weather" in only and not mock:
        w = pd.read_parquet(interim / "weather_clean.parquet")
        jobs.append(Job(WeatherRecord, interim / "weather_clean.parquet", w))
    if "traffic" in only:
        jobs.append(Job(IntegratedTraffic, integ_path, integrated))
    if "analytics" in only:
        jobs += [Job(t, p, d) for t, p, d in read_analytics(processed / "analytics", "_mock" if mock else "")]

    counts: dict[str, int] = {}
    started = datetime.now()
    with engine.begin() as conn:                      # MỘT transaction cho toàn bộ lần nạp
        # Khóa ngoại: kiểm tra trước khi xóa/nạp để báo lỗi dễ hiểu thay vì lỗi của database
        road_ids = set(next(j.df for j in jobs if j.table is Road)["road_id"]) if any(j.table is Road for j in jobs) \
            else set(conn.execute(select(Road.road_id)).scalars())
        for j in jobs:
            if "road_id" in j.df.columns and j.table is not Road:
                missing = set(j.df["road_id"]) - road_ids
                if missing:
                    raise LoadError(f"{j.table.__tablename__}: {len(missing)} road_id không có trong roads, "
                                    f"ví dụ {sorted(missing)[:3]}")
        # Xóa bảng con trước bảng cha
        to_clear = [j.table for j in jobs]
        if Road in to_clear:      # xóa roads thì phải xóa mọi bảng tham chiếu tới nó
            to_clear = list(dict.fromkeys([Anomaly, IntegratedTraffic] + to_clear))
        for t in sorted(to_clear, key=lambda t: t is Road):
            conn.execute(t.__table__.delete())
        for j in jobs:
            t0 = time.perf_counter()
            n = write(conn, j.table, j.df)
            got = conn.execute(select(func.count()).select_from(j.table)).scalar_one()
            if got != len(j.df):
                raise LoadError(f"{j.table.__tablename__}: nạp {got} dòng nhưng file có {len(j.df)} dòng")
            counts[j.table.__tablename__] = n
            log(conn, j.table.__tablename__, str(j.source), "replace", len(j.df), n, "ok", started=started)
            say(f"  {j.table.__tablename__:<20} {n:>9,} dòng  ({time.perf_counter() - t0:5.1f} s)  ← {j.source}")
        if conn.dialect.name == "postgresql":
            conn.execute(text("ANALYZE"))             # cập nhật thống kê cho bộ tối ưu truy vấn của PostgreSQL
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=settings.DATA_DIR)
    ap.add_argument("--only", nargs="+", choices=LOAD_ORDER, default=list(LOAD_ORDER))
    ap.add_argument("--mock", action="store_true", help="nạp data/mock/integrated_traffic + analytics *_mock")
    a = ap.parse_args()
    from app.core.database import engine
    t0 = time.perf_counter()
    print(f"Nạp dữ liệu từ {a.data_dir} vào {engine.url.render_as_string(hide_password=True)}")
    try:
        counts = load(engine, a.data_dir, tuple(a.only), a.mock)
    except LoadError as e:
        raise SystemExit(f"LỖI: {e}\n(Không có thay đổi nào được ghi vào database.)")
    print(f"Xong trong {time.perf_counter() - t0:.1f} s: {sum(counts.values()):,} dòng vào {len(counts)} bảng.")


if __name__ == "__main__":
    main()
