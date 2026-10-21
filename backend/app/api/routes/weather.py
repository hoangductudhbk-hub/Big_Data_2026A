from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, TimeRange
from app.api.util import paginate
from app.core.database import get_db
from app.core.errors import not_found
from app.models import WeatherRecord as W
from app.schemas.common import Page
from app.schemas.weather import StationOut, WeatherOut

router = APIRouter()


@router.get("", response_model=Page[WeatherOut], summary="Thời tiết theo giờ (lọc + phân trang)")
def list_weather(pg: Pagination = Depends(), tr: TimeRange = Depends(), station_id: str | None = None,
                 district: str | None = None, weather_condition: str | None = None, db: Session = Depends(get_db)):
    stmt = select(W)
    if station_id:
        stmt = stmt.where(W.station_id == station_id)
    if district:
        stmt = stmt.where(W.district == district)
    if weather_condition:
        stmt = stmt.where(W.weather_condition == weather_condition)
    return paginate(db, tr.apply(stmt, W.timestamp), pg, (W.timestamp, W.station_id))


@router.get("/stations", response_model=list[StationOut], summary="Các điểm đo thời tiết")
def stations(db: Session = Depends(get_db)):
    rows = db.execute(select(W.station_id, func.max(W.district).label("district"), func.count().label("records"),
                             func.min(W.timestamp).label("first_timestamp"),
                             func.max(W.timestamp).label("last_timestamp")).group_by(W.station_id)
                      .order_by(W.station_id))
    return [dict(r._mapping) for r in rows]


@router.get("/{id}", response_model=WeatherOut)
def get_weather(id: int, db: Session = Depends(get_db)):
    rec = db.get(W, id)
    if not rec:
        raise not_found(f"bản ghi thời tiết id={id}")
    return rec
