from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TrafficOut(ORMModel):
    """Một bản ghi integrated_traffic: đúng 14 cột của data contract + id."""
    id: int
    road_id: str
    road_name: str
    district: str
    latitude: float
    longitude: float
    timestamp: datetime
    vehicle_count: int | None
    avg_speed: float | None
    temperature: float | None
    rainfall: float | None
    snowfall: float | None
    weather_condition: str | None
    weather_station_id: str | None
    source: str


class TimeseriesPoint(BaseModel):
    bucket: datetime
    n: int
    avg_speed: float | None
    vehicle_count: float | None
    rainfall: float | None
    snowfall: float | None
