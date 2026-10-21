from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RoadOut(ORMModel):
    road_id: str
    road_name: str
    district: str | None
    latitude: float | None
    longitude: float | None
    link_id: str | None = None
    segmentid: str | None = None
    has_speed: bool
    has_volume: bool


class RoadStatsOut(BaseModel):
    n_speed: int
    mean_speed: float | None
    std_speed: float | None
    min_speed: float | None
    max_speed: float | None
    n_volume: int
    mean_volume: float | None
    max_volume: float | None
    first_timestamp: str | None
    last_timestamp: str | None
    anomalies: int


class RoadDetailOut(RoadOut):
    stats: RoadStatsOut


class RoadCreate(BaseModel):
    road_id: str = Field(..., min_length=1, max_length=32, examples=["L4616337"])
    road_name: str = Field(..., min_length=1, max_length=200)
    district: str
    latitude: float
    longitude: float
