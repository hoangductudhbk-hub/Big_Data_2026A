from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, TimeRange
from app.api.util import paginate
from app.core.database import get_db
from app.core.errors import ApiError, not_found
from app.models import IntegratedTraffic as T
from app.schemas.common import Page
from app.schemas.traffic import TimeseriesPoint, TrafficOut

router = APIRouter()


def _filters(stmt, road_id, district, source, weather_condition, tr: TimeRange):
    if road_id:
        stmt = stmt.where(T.road_id == road_id)
    if district:
        stmt = stmt.where(T.district == district)
    if source:
        stmt = stmt.where(T.source == source)
    if weather_condition:
        stmt = stmt.where(T.weather_condition == weather_condition)
    return tr.apply(stmt, T.timestamp)


@router.get("", response_model=Page[TrafficOut], summary="Bản ghi integrated_traffic (lọc + phân trang)")
def list_traffic(pg: Pagination = Depends(), tr: TimeRange = Depends(), road_id: str | None = None,
                 district: str | None = None, source: str | None = None, weather_condition: str | None = None,
                 order: Literal["asc", "desc"] = "asc", db: Session = Depends(get_db)):
    stmt = _filters(select(T), road_id, district, source, weather_condition, tr)
    o = T.timestamp.asc() if order == "asc" else T.timestamp.desc()
    return paginate(db, stmt, pg, (o, T.road_id))


@router.get("/timeseries", response_model=list[TimeseriesPoint],
            summary="Chuỗi thời gian gộp theo giờ/ngày/tuần (cho biểu đồ)")
def timeseries(tr: TimeRange = Depends(), road_id: str | None = None, district: str | None = None,
               bucket: Literal["hour", "day", "week", "month"] = "day", db: Session = Depends(get_db)):
    if db.get_bind().dialect.name != "postgresql":
        raise ApiError(400, "timeseries cần PostgreSQL (date_trunc)")
    if bucket == "hour" and not (road_id or (tr.start and tr.end and (tr.end - tr.start).days <= 31)):
        raise ApiError(400, "bucket=hour chỉ cho phép khi lọc theo road_id hoặc khoảng thời gian ≤ 31 ngày")
    b = func.date_trunc(bucket, T.timestamp).label("bucket")
    stmt = _filters(select(b, func.count().label("n"), func.avg(T.avg_speed).label("avg_speed"),
                           func.avg(T.vehicle_count).label("vehicle_count"), func.avg(T.rainfall).label("rainfall"),
                           func.avg(T.snowfall).label("snowfall")),
                    road_id, district, None, None, tr).group_by(b).order_by(b)
    return [dict(r._mapping) for r in db.execute(stmt)]


@router.get("/{id}", response_model=TrafficOut, summary="Một bản ghi theo id")
def get_traffic(id: int, db: Session = Depends(get_db)):
    rec = db.get(T, id)
    if not rec:
        raise not_found(f"bản ghi giao thông id={id}")
    return rec
