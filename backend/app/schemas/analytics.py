from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class StatisticOut(ORMModel):
    dimension: str
    group_key: str
    metric: str
    n: int
    mean: float | None
    std: float | None
    min: float | None
    max: float | None
    median: float | None


class DimensionOut(BaseModel):
    dimension: str
    groups: int
    metrics: list[str]


class LiveStatisticOut(BaseModel):
    group_key: str
    n: int
    mean: float | None
    std: float | None
    min: float | None
    max: float | None
    median: float | None = None


class DailyStatOut(ORMModel):
    date: date
    n_speed: int
    mean_speed: float | None
    n_volume: int
    mean_volume: float | None
    temperature: float | None
    rain_mm_per_day: float | None
    snow_cm_per_day: float | None
    coverage_pct: float | None
    is_outage: bool | None


class WeatherImpactOut(ORMModel):
    dimension: str
    group_key: str
    n: int
    n_days: int
    raw_mean: float | None
    raw_change_pct: float | None
    controlled_change_pct: float | None
    controlled_month_change_pct: float | None
    ci95_pct: float | None


class SummaryOut(BaseModel):
    records: int
    roads: int
    roads_with_speed: int
    roads_with_volume: int
    speed_records: int
    volume_records: int
    weather_records: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    mean_speed: float | None
    anomalies: int
    outage_days: int
    districts: list[str]


class AnomalyOut(ORMModel):
    id: int
    road_id: str
    road_name: str | None
    district: str | None
    timestamp: datetime
    metric: str
    value: float
    expected: float | None
    std: float | None
    z_score: float
    is_anomaly: bool
    direction: str | None
    vehicle_count: float | None
    avg_speed: float | None
    weather_condition: str | None
    rainfall: float | None
    snowfall: float | None


class AnomalyDailyOut(ORMModel):
    date: date
    day_type: str | None
    records: int
    slow_anomalies: int
    fast_anomalies: int
    anomaly_rate_pct: float | None
    mean_z: float | None
    rain_mm_per_day: float | None
    snow_cm_per_day: float | None
    coverage_pct: float | None


class CountItem(BaseModel):
    key: str
    count: int


class AnomalySummaryOut(BaseModel):
    total: int
    by_metric: list[CountItem]
    by_direction: list[CountItem]
    by_district: list[CountItem]
    top_roads: list[dict]
