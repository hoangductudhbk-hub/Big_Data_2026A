from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class WeatherOut(ORMModel):
    id: int
    station_id: str
    district: str | None
    timestamp: datetime
    temperature: float | None
    precipitation: float | None
    rainfall: float | None
    snowfall: float | None
    weather_code: int | None
    weather_condition: str | None


class StationOut(BaseModel):
    station_id: str
    district: str | None
    records: int
    first_timestamp: datetime
    last_timestamp: datetime
