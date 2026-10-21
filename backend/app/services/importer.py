"""POST /import/traffic và /import/weather: kiểm tra từng dòng theo contract rồi UPSERT.

- Dòng hợp lệ được ghi; dòng lỗi bị từ chối kèm lý do (trả về cho client).
- all_or_nothing=True: chỉ cần 1 dòng lỗi là không ghi gì (trả 422).
- UPSERT theo khóa chính của contract (road_id, timestamp): gửi lại cùng dữ liệu không tạo bản trùng
  (idempotent), gửi giá trị mới thì ghi đè.
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.models import ImportLog, IntegratedTraffic, Road, WeatherRecord
from app.schemas.imports import ImportResult, RejectedRow, TrafficIn, WeatherIn
from app.services.validation import validate_traffic, validate_weather

MAX_REPORTED = 100   # chỉ trả về chi tiết 100 dòng lỗi đầu tiên


def parse_file(filename: str, content: bytes) -> list[dict]:
    name = (filename or "").lower()
    try:
        if name.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(content))
        elif name.endswith((".csv", ".txt")) or not name:
            df = pd.read_csv(io.BytesIO(content))
        elif name.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            raise ApiError(400, f"Định dạng file không hỗ trợ: {filename}. Dùng .csv, .json hoặc .parquet")
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ApiError(400, f"Không đọc được file {filename}: {e}")
    df = df.drop(columns=[c for c in ("year", "month", "id") if c in df.columns])
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _insert(db: Session):
    return pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert


def _parse(rows: list[dict], model) -> tuple[list[tuple[int, dict]], list[RejectedRow]]:
    ok, bad = [], []
    for i, r in enumerate(rows, start=1):
        try:
            ok.append((i, model.model_validate(r).model_dump()))
        except ValidationError as e:
            bad.append(RejectedRow(row=i, errors=[f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()]))
    return ok, bad


def _finish(db: Session, target: str, source: str, received: int, good: list[dict], bad: list[RejectedRow],
            inserted: int, updated: int, all_or_nothing: bool, started: datetime, new_roads=()) -> ImportResult:
    status = "ok" if not bad else ("failed" if all_or_nothing or not good else "partial")
    log = ImportLog(target=target, source=source, mode="upsert", rows_received=received,
                    rows_loaded=0 if status == "failed" else len(good), rows_rejected=len(bad), status=status,
                    message=None if not bad else f"{len(bad)} dòng lỗi, ví dụ dòng {bad[0].row}: {bad[0].errors[0]}",
                    started_at=started, finished_at=datetime.now())
    db.add(log)
    db.commit()
    res = ImportResult(import_id=log.id, target=target, received=received,
                       inserted=0 if status == "failed" else inserted, updated=0 if status == "failed" else updated,
                       rejected=len(bad), status=status, rejected_rows=bad[:MAX_REPORTED], new_roads=list(new_roads))
    if status == "failed" and all_or_nothing and bad:
        raise ApiError(422, f"Có {len(bad)} dòng không hợp lệ, không dòng nào được ghi (all_or_nothing=true)",
                       res.model_dump(mode="json"))
    return res


def import_traffic(db: Session, rows: list[dict], source: str, all_or_nothing: bool = False) -> ImportResult:
    started = datetime.now()
    if len(rows) > settings.MAX_IMPORT_ROWS:
        raise ApiError(413, f"Tối đa {settings.MAX_IMPORT_ROWS:,} dòng mỗi lần import (gửi {len(rows):,})")
    parsed, bad = _parse(rows, TrafficIn)
    ids = {r["road_id"] for _, r in parsed}
    roads = {r.road_id: {"road_name": r.road_name, "district": r.district, "latitude": r.latitude,
                         "longitude": r.longitude} for r in db.scalars(select(Road).where(Road.road_id.in_(ids)))}
    good, seen, new_roads = [], {}, {}
    for i, r in parsed:
        rec, errs = validate_traffic(r, roads.get(r["road_id"]) or new_roads.get(r["road_id"]))
        key = (r["road_id"], rec["timestamp"]) if rec else None
        if rec and key in seen:
            errs = [f"trùng khóa (road_id, timestamp) với dòng {seen[key]} trong cùng lần gửi"]
        if errs:
            bad.append(RejectedRow(row=i, errors=errs))
            continue
        seen[key] = i
        if rec["road_id"] not in roads and rec["road_id"] not in new_roads:
            new_roads[rec["road_id"]] = {k: rec[k] for k in ("road_name", "district", "latitude", "longitude")}
        good.append(rec)
    bad.sort(key=lambda b: b.row)
    inserted = updated = 0
    if good and not (all_or_nothing and bad):
        keys = [(g["road_id"], g["timestamp"]) for g in good]
        existing = set()
        for chunk in range(0, len(keys), 5000):
            part = keys[chunk:chunk + 5000]
            existing |= set(db.execute(select(IntegratedTraffic.road_id, IntegratedTraffic.timestamp).where(
                tuple_(IntegratedTraffic.road_id, IntegratedTraffic.timestamp).in_(part))).all())
        updated = len(existing)
        inserted = len(good) - updated
        for rid, info in new_roads.items():
            db.add(Road(road_id=rid, **info, has_speed=False, has_volume=False))
        db.flush()
        ins = _insert(db)(IntegratedTraffic)
        cols = [c for c in good[0] if c not in ("road_id", "timestamp")]
        for chunk in range(0, len(good), 5000):
            stmt = ins.values(good[chunk:chunk + 5000])
            stmt = stmt.on_conflict_do_update(index_elements=["road_id", "timestamp"],
                                              set_={c: stmt.excluded[c] for c in cols})
            db.execute(stmt)
        # cập nhật cờ has_speed / has_volume của các đường liên quan
        for rid in {g["road_id"] for g in good}:
            road = db.get(Road, rid)
            road.has_speed = road.has_speed or any(g["avg_speed"] is not None for g in good if g["road_id"] == rid)
            road.has_volume = road.has_volume or any(g["vehicle_count"] is not None for g in good if g["road_id"] == rid)
    else:
        db.rollback()
    return _finish(db, "integrated_traffic", source, len(rows), good, bad, inserted, updated, all_or_nothing,
                   started, new_roads.keys())


def import_weather(db: Session, rows: list[dict], source: str, all_or_nothing: bool = False) -> ImportResult:
    started = datetime.now()
    if len(rows) > settings.MAX_IMPORT_ROWS:
        raise ApiError(413, f"Tối đa {settings.MAX_IMPORT_ROWS:,} dòng mỗi lần import (gửi {len(rows):,})")
    parsed, bad = _parse(rows, WeatherIn)
    good, seen = [], {}
    for i, r in parsed:
        rec, errs = validate_weather(r)
        key = (rec["station_id"], rec["timestamp"]) if rec else None
        if rec and key in seen:
            errs = [f"trùng khóa (station_id, timestamp) với dòng {seen[key]}"]
        if errs:
            bad.append(RejectedRow(row=i, errors=errs))
            continue
        seen[key] = i
        good.append(rec)
    bad.sort(key=lambda b: b.row)
    inserted = updated = 0
    if good and not (all_or_nothing and bad):
        keys = [(g["station_id"], g["timestamp"]) for g in good]
        existing = set()
        for chunk in range(0, len(keys), 5000):
            existing |= set(db.execute(select(WeatherRecord.station_id, WeatherRecord.timestamp).where(
                tuple_(WeatherRecord.station_id, WeatherRecord.timestamp).in_(keys[chunk:chunk + 5000]))).all())
        updated, inserted = len(existing), len(good) - len(existing)
        ins = _insert(db)(WeatherRecord)
        cols = [c for c in good[0] if c not in ("station_id", "timestamp")]
        for chunk in range(0, len(good), 5000):
            stmt = ins.values(good[chunk:chunk + 5000])
            db.execute(stmt.on_conflict_do_update(index_elements=["station_id", "timestamp"],
                                                  set_={c: stmt.excluded[c] for c in cols}))
    else:
        db.rollback()
    return _finish(db, "weather_records", source, len(rows), good, bad, inserted, updated, all_or_nothing, started)
