import time

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Pagination
from app.api.util import paginate
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.models import ImportLog
from app.schemas.common import Page
from app.schemas.imports import ImportLogOut, ImportResult, ReloadResult
from app.services.importer import import_traffic, import_weather, parse_file

router = APIRouter()
AON = Query(False, description="true: chỉ cần 1 dòng lỗi là không ghi dòng nào")

TRAFFIC_EXAMPLE = [{"road_id": "L4616337", "timestamp": "2025-01-02T08:00:00", "avg_speed": 12.5},
                   {"road_id": "S999001", "road_name": "TEST AVENUE", "district": "Queens", "latitude": 40.7,
                    "longitude": -73.85, "timestamp": "2025-01-02T08:00:00", "vehicle_count": 640}]


@router.post("/traffic", response_model=ImportResult, summary="Import bản ghi giao thông (JSON) theo data contract")
def post_traffic(rows: list[dict] = Body(..., examples=[TRAFFIC_EXAMPLE]), all_or_nothing: bool = AON,
                 db: Session = Depends(get_db)):
    """Mỗi dòng theo tên cột của data contract. `road_name/district/latitude/longitude` có thể bỏ trống nếu
    `road_id` đã có trong danh mục; `source` tự suy ra nếu bỏ trống. UPSERT theo (road_id, timestamp)."""
    return import_traffic(db, rows, "api:json", all_or_nothing)


@router.post("/traffic/file", response_model=ImportResult, summary="Import giao thông từ file CSV / JSON / Parquet")
async def post_traffic_file(file: UploadFile = File(...), all_or_nothing: bool = AON, db: Session = Depends(get_db)):
    rows = parse_file(file.filename, await file.read())
    return import_traffic(db, rows, f"api:file:{file.filename}", all_or_nothing)


@router.post("/weather", response_model=ImportResult, summary="Import thời tiết theo giờ (JSON)")
def post_weather(rows: list[dict] = Body(..., examples=[[{"station_id": "OM_QUEENS", "district": "Queens",
                                                          "timestamp": "2025-01-02T08:00:00", "temperature": 1.5,
                                                          "rainfall": 0.4, "snowfall": 0,
                                                          "weather_condition": "Drizzle"}]]),
                 all_or_nothing: bool = AON, db: Session = Depends(get_db)):
    return import_weather(db, rows, "api:json", all_or_nothing)


@router.post("/weather/file", response_model=ImportResult, summary="Import thời tiết từ file CSV / JSON / Parquet")
async def post_weather_file(file: UploadFile = File(...), all_or_nothing: bool = AON, db: Session = Depends(get_db)):
    rows = parse_file(file.filename, await file.read())
    return import_weather(db, rows, f"api:file:{file.filename}", all_or_nothing)


@router.post("/spark-results", response_model=ReloadResult,
             summary="Nạp lại kết quả Spark (bước 15–17) từ data/processed/analytics vào database")
def reload_spark_results(db: Session = Depends(get_db)):
    """Chạy sau khi chạy lại Phase 2. Thay thế toàn bộ statistics, daily_stats, weather_impact, anomalies,
    anomaly_daily trong một transaction."""
    from app.etl.load_processed import LoadError, load
    t0 = time.perf_counter()
    try:
        counts = load(db.get_bind(), settings.DATA_DIR, ("analytics",), verbose=False)
    except LoadError as e:
        raise ApiError(409, str(e))
    except FileNotFoundError as e:
        raise ApiError(404, f"Không thấy file kết quả: {e}")
    return {"tables": counts, "seconds": round(time.perf_counter() - t0, 2)}


@router.get("/logs", response_model=Page[ImportLogOut], summary="Nhật ký các lần nạp / import")
def logs(pg: Pagination = Depends(), db: Session = Depends(get_db)):
    return paginate(db, select(ImportLog), pg, (ImportLog.id.desc(),))
