from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, TimeRange
from app.api.util import paginate
from app.core.database import get_db
from app.core.errors import not_found
from app.models import Anomaly as A, AnomalyDaily
from app.schemas.analytics import AnomalyDailyOut, AnomalyOut, AnomalySummaryOut
from app.schemas.common import Page

router = APIRouter()


@router.get("", response_model=Page[AnomalyOut], summary="Bản ghi bất thường (Z-score, bước 17)")
def list_anomalies(pg: Pagination = Depends(), tr: TimeRange = Depends(),
                   metric: Literal["avg_speed", "vehicle_count"] | None = None, road_id: str | None = None,
                   district: str | None = None,
                   direction: Literal["thấp bất thường", "cao bất thường"] | None = None,
                   min_abs_z: float = Query(3.0, ge=0, description="Chỉ lấy |z| ≥ giá trị này (mặc định 3)"),
                   order: Literal["z", "time"] = Query("z", description="z: |z| giảm dần; time: theo thời gian"),
                   db: Session = Depends(get_db)):
    stmt = select(A).where(func.abs(A.z_score) >= min_abs_z)
    for col, v in ((A.metric, metric), (A.road_id, road_id), (A.district, district), (A.direction, direction)):
        if v:
            stmt = stmt.where(col == v)
    stmt = tr.apply(stmt, A.timestamp)
    o = (func.abs(A.z_score).desc(), A.id) if order == "z" else (A.timestamp, A.id)
    return paginate(db, stmt, pg, o)


@router.get("/summary", response_model=AnomalySummaryOut, summary="Tóm tắt bất thường")
def anomaly_summary(min_abs_z: float = Query(3.0, ge=0), db: Session = Depends(get_db)):
    base = func.abs(A.z_score) >= min_abs_z

    def count_by(col):
        rows = db.execute(select(col, func.count()).where(base).group_by(col).order_by(func.count().desc())).all()
        return [{"key": str(k), "count": n} for k, n in rows]

    top = db.execute(select(A.road_id, A.road_name, A.district, func.count().label("count"),
                            func.min(A.z_score).label("min_z"), func.max(A.z_score).label("max_z"))
                     .where(base, A.metric == "avg_speed").group_by(A.road_id, A.road_name, A.district)
                     .order_by(func.count().desc()).limit(10)).all()
    return {"total": db.scalar(select(func.count()).select_from(A).where(base)),
            "by_metric": count_by(A.metric), "by_direction": count_by(A.direction),
            "by_district": count_by(A.district), "top_roads": [dict(r._mapping) for r in top]}


@router.get("/daily", response_model=list[AnomalyDailyOut], summary="Số bất thường tốc độ theo ngày")
def anomaly_daily(start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    stmt = select(AnomalyDaily)
    if start:
        stmt = stmt.where(AnomalyDaily.date >= start)
    if end:
        stmt = stmt.where(AnomalyDaily.date < end)
    return db.scalars(stmt.order_by(AnomalyDaily.date)).all()


@router.get("/{id}", response_model=AnomalyOut)
def get_anomaly(id: int, db: Session = Depends(get_db)):
    a = db.get(A, id)
    if not a:
        raise not_found(f"bất thường id={id}")
    return a
