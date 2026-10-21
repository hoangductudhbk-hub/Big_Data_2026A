from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from common.contract import WEATHER_CONDITIONS


class WeatherRecord(Base):
    """Thời tiết theo giờ của từng điểm đo (Open-Meteo, bước 07: data/interim/weather_clean.parquet)."""
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str | None] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)   # giờ New York
    temperature: Mapped[float | None] = mapped_column(Float)
    precipitation: Mapped[float | None] = mapped_column(Float)
    rainfall: Mapped[float | None] = mapped_column(Float)
    snowfall: Mapped[float | None] = mapped_column(Float)
    weather_code: Mapped[int | None] = mapped_column(Integer)
    weather_condition: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        UniqueConstraint("station_id", "timestamp", name="uq_weather_station_ts"),
        Index("ix_weather_records_timestamp", "timestamp"),
        CheckConstraint("rainfall IS NULL OR rainfall >= 0", name="ck_weather_rainfall"),
        CheckConstraint("snowfall IS NULL OR snowfall >= 0", name="ck_weather_snowfall"),
        CheckConstraint("weather_condition IS NULL OR weather_condition IN ("
                        + ", ".join(repr(v) for v in WEATHER_CONDITIONS) + ")", name="ck_weather_condition"),
    )
