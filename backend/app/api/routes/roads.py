from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination
from app.api.util import paginate
from app.core.database import get_db
from app.core.errors import ApiError, not_found
from app.models import Anomaly, IntegratedTraffic, Road
from app.schemas.common import Page
from app.schemas.road import RoadCreate, RoadDetailOut, RoadOut
from common.contract import DISTRICTS, NYC_BBOX

router = APIRouter()


@router.get("", response_model=Page[RoadOut], summary="Danh mục đường (sau record linkage)")
def list_roads(pg: Pagination = Depends(), district: str | None = None, has_speed: bool | None = None,
               has_volume: bool | None = None, q: str | None = Query(None, description="Tìm theo tên hoặc mã"),
               db: Session = Depends(get_db)):
    stmt = select(Road)
    if district:
        stmt = stmt.where(Road.district == district)
    if has_speed is not None:
        stmt = stmt.where(Road.has_speed == has_speed)
    if has_volume is not None:
        stmt = stmt.where(Road.has_volume == has_volume)
    if q:
        stmt = stmt.where(or_(Road.road_name.ilike(f"%{q}%"), Road.road_id.ilike(f"%{q}%")))
    return paginate(db, stmt, pg, (Road.road_id,))


@router.get("/{road_id}", response_model=RoadDetailOut, summary="Một đường kèm thống kê tóm tắt")
def get_road(road_id: str, db: Session = Depends(get_db)):
    road = db.get(Road, road_id)
    if not road:
        raise not_found(f"đường {road_id}")
    t = IntegratedTraffic
    s = db.execute(select(func.count(t.avg_speed), func.avg(t.avg_speed), func.min(t.avg_speed), func.max(t.avg_speed),
                          func.count(t.vehicle_count), func.avg(t.vehicle_count), func.max(t.vehicle_count),
                          func.min(t.timestamp), func.max(t.timestamp)).where(t.road_id == road_id)).one()
    std = None
    if db.get_bind().dialect.name == "postgresql":
        std = db.scalar(select(func.stddev_samp(t.avg_speed)).where(t.road_id == road_id))
    n_anom = db.scalar(select(func.count()).select_from(Anomaly).where(Anomaly.road_id == road_id))
    out = RoadOut.model_validate(road).model_dump()
    out["stats"] = {"n_speed": s[0], "mean_speed": s[1], "std_speed": std, "min_speed": s[2], "max_speed": s[3],
                    "n_volume": s[4], "mean_volume": float(s[5]) if s[5] is not None else None,
                    "max_volume": float(s[6]) if s[6] is not None else None,
                    "first_timestamp": s[7].isoformat() if s[7] else None,
                    "last_timestamp": s[8].isoformat() if s[8] else None, "anomalies": n_anom}
    return out


@router.post("", response_model=RoadOut, status_code=201, summary="Thêm một đường mới vào danh mục")
def create_road(body: RoadCreate, db: Session = Depends(get_db)):
    if body.district not in DISTRICTS:
        raise ApiError(422, f"district phải thuộc {list(DISTRICTS)}")
    if not (NYC_BBOX["lat_min"] <= body.latitude <= NYC_BBOX["lat_max"]
            and NYC_BBOX["lon_min"] <= body.longitude <= NYC_BBOX["lon_max"]):
        raise ApiError(422, "Tọa độ nằm ngoài khung New York của data contract", NYC_BBOX)
    if db.get(Road, body.road_id):
        raise ApiError(409, f"Đường {body.road_id} đã tồn tại")
    road = Road(**body.model_dump(), has_speed=False, has_volume=False)
    db.add(road)
    db.commit()
    db.refresh(road)
    return road
