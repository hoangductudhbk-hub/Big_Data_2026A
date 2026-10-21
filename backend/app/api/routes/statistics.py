from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, cast, extract, func, select
from sqlalchemy.orm import Session

from app.api.deps import TimeRange
from app.core.database import get_db
from app.core.errors import ApiError
from app.models import Anomaly, DailyStat, IntegratedTraffic as T, Road, Statistic, WeatherImpact, WeatherRecord
from app.schemas.analytics import (DailyStatOut, DimensionOut, LiveStatisticOut, StatisticOut, SummaryOut,
                                   WeatherImpactOut)

router = APIRouter()
METRICS = ("avg_speed", "vehicle_count")


@router.get("", response_model=list[StatisticOut],
            summary="Thống kê do Spark tính sẵn (bước 15): count, mean, std, min, max, median")
def get_statistics(dimension: str = Query("district", description="Xem /statistics/dimensions"),
                   metric: Literal["avg_speed", "vehicle_count"] | None = None, group_key: str | None = None,
                   db: Session = Depends(get_db)):
    dims = set(db.scalars(select(Statistic.dimension).distinct()))
    if dimension not in dims:
        raise ApiError(400, f"dimension '{dimension}' không tồn tại", sorted(dims))
    stmt = select(Statistic).where(Statistic.dimension == dimension)
    if metric:
        stmt = stmt.where(Statistic.metric == metric)
    if group_key:
        stmt = stmt.where(Statistic.group_key == group_key)
    return db.scalars(stmt.order_by(Statistic.metric, Statistic.group_key)).all()


@router.get("/dimensions", response_model=list[DimensionOut], summary="Các chiều thống kê có sẵn")
def dimensions(db: Session = Depends(get_db)):
    rows = db.execute(select(Statistic.dimension, Statistic.metric, func.count()).group_by(
        Statistic.dimension, Statistic.metric)).all()
    out: dict[str, dict] = {}
    for d, m, n in rows:
        o = out.setdefault(d, {"dimension": d, "groups": 0, "metrics": []})
        o["groups"] = max(o["groups"], n)
        o["metrics"].append(m)
    return sorted(out.values(), key=lambda x: x["dimension"])


@router.get("/summary", response_model=SummaryOut, summary="Số liệu tổng quan cho dashboard")
def summary(db: Session = Depends(get_db)):
    r = db.execute(select(func.count(), func.count(T.avg_speed), func.count(T.vehicle_count), func.min(T.timestamp),
                          func.max(T.timestamp), func.avg(T.avg_speed), func.count(func.distinct(T.road_id)))).one()
    roads_speed = db.scalar(select(func.count(func.distinct(T.road_id))).where(T.avg_speed.is_not(None)))
    roads_vol = db.scalar(select(func.count(func.distinct(T.road_id))).where(T.vehicle_count.is_not(None)))
    return {"records": r[0], "speed_records": r[1], "volume_records": r[2], "first_timestamp": r[3],
            "last_timestamp": r[4], "mean_speed": r[5], "roads": r[6], "roads_with_speed": roads_speed,
            "roads_with_volume": roads_vol,
            "weather_records": db.scalar(select(func.count()).select_from(WeatherRecord)),
            "anomalies": db.scalar(select(func.count()).select_from(Anomaly)),
            "outage_days": db.scalar(select(func.count()).select_from(DailyStat).where(DailyStat.is_outage.is_(True))),
            "districts": list(db.scalars(select(Road.district).where(Road.district.is_not(None)).distinct()
                                         .order_by(Road.district)))}


@router.get("/daily", response_model=list[DailyStatOut], summary="Chuỗi theo ngày (bước 15)")
def daily(start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    stmt = select(DailyStat)
    if start:
        stmt = stmt.where(DailyStat.date >= start)
    if end:
        stmt = stmt.where(DailyStat.date < end)
    return db.scalars(stmt.order_by(DailyStat.date)).all()


@router.get("/weather-impact", response_model=list[WeatherImpactOut], summary="Tác động thời tiết (bước 16)")
def weather_impact(dimension: str | None = Query(None, description="weather_condition | rainfall | snowfall | "
                                                               "temperature | rainfall_volume"),
                   db: Session = Depends(get_db)):
    stmt = select(WeatherImpact)
    if dimension:
        stmt = stmt.where(WeatherImpact.dimension == dimension)
    return db.scalars(stmt.order_by(WeatherImpact.dimension, WeatherImpact.group_key)).all()


GROUPS = {
    "district": lambda: T.district,
    "hour": lambda: cast(extract("hour", T.timestamp), Integer),
    "day_of_week": lambda: cast(extract("dow", T.timestamp), Integer),      # 0 = Chủ nhật (PostgreSQL)
    "month": lambda: cast(extract("month", T.timestamp), Integer),
    "weather_condition": lambda: T.weather_condition,
    "source": lambda: T.source,
    "road": lambda: T.road_id,
}


@router.get("/live", response_model=list[LiveStatisticOut],
            summary="Thống kê tính TRỰC TIẾP bằng SQL trên integrated_traffic, có lọc thời gian/quận")
def live(group_by: Literal["district", "hour", "day_of_week", "month", "weather_condition", "source", "road"]
         = "district", metric: Literal["avg_speed", "vehicle_count"] = "avg_speed", tr: TimeRange = Depends(),
         district: str | None = None, db: Session = Depends(get_db)):
    """Khác /statistics (Spark tính sẵn trên cả năm): endpoint này cho phép chọn khoảng thời gian bất kỳ.
    Dùng để đối chiếu: không lọc gì thì kết quả phải trùng với /statistics."""
    g = GROUPS[group_by]().label("group_key")
    m = getattr(T, metric)
    pg = db.get_bind().dialect.name == "postgresql"
    cols = [g, func.count(m).label("n"), func.avg(m).label("mean"), func.min(m).label("min"), func.max(m).label("max")]
    if pg:
        cols += [func.stddev_samp(m).label("std"), func.percentile_cont(0.5).within_group(m).label("median")]
    stmt = tr.apply(select(*cols).where(m.is_not(None)), T.timestamp)
    if district:
        stmt = stmt.where(T.district == district)
    rows = db.execute(stmt.group_by(g).order_by(g)).all()
    return [{**r._mapping, "group_key": str(r.group_key), "std": r._mapping.get("std"),
             "mean": float(r.mean) if r.mean is not None else None,
             "min": float(r.min) if r.min is not None else None, "max": float(r.max) if r.max is not None else None}
            for r in rows]
