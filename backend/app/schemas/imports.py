from datetime import datetime

from pydantic import BaseModel, Field


class TrafficIn(BaseModel):
    """Một bản ghi gửi lên POST /import/traffic. Tên cột = data contract. Kiểm tra chi tiết ở services/validation."""
    road_id: str
    road_name: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timestamp: datetime
    vehicle_count: int | None = None
    avg_speed: float | None = None
    temperature: float | None = None
    rainfall: float | None = None
    snowfall: float | None = None
    weather_condition: str | None = None
    weather_station_id: str | None = None
    source: str | None = None


class WeatherIn(BaseModel):
    station_id: str
    district: str | None = None
    timestamp: datetime
    temperature: float | None = None
    precipitation: float | None = None
    rainfall: float | None = None
    snowfall: float | None = None
    weather_code: int | None = None
    weather_condition: str | None = None


class RejectedRow(BaseModel):
    row: int = Field(..., description="Số thứ tự dòng trong dữ liệu gửi lên (bắt đầu từ 1)")
    errors: list[str]


class ImportResult(BaseModel):
    import_id: int
    target: str
    received: int
    inserted: int
    updated: int
    rejected: int
    status: str
    rejected_rows: list[RejectedRow]
    new_roads: list[str] = []


class ImportLogOut(BaseModel):
    id: int
    target: str
    source: str
    mode: str
    rows_received: int
    rows_loaded: int
    rows_rejected: int
    status: str
    message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class ReloadResult(BaseModel):
    tables: dict[str, int]
    seconds: float
