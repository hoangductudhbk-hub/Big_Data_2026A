"""Kết quả Phase 2 (PySpark, bước 15–17) nạp từ data/processed/analytics/*.parquet."""
from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Statistic(Base):
    """Bảng thống kê dạng dài (bước 15): một dòng = (chiều, nhóm, chỉ số) → count/mean/std/min/max/median."""
    __tablename__ = "statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    mean: Mapped[float | None] = mapped_column(Float)
    std: Mapped[float | None] = mapped_column(Float)
    min: Mapped[float | None] = mapped_column(Float)
    max: Mapped[float | None] = mapped_column(Float)
    median: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("dimension", "group_key", "metric", name="uq_statistics_key"),)


class DailyStat(Base):
    """Chuỗi theo ngày (bước 15) kèm cờ ngày mất dữ liệu."""
    __tablename__ = "daily_stats"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    n_speed: Mapped[int] = mapped_column(Integer)
    mean_speed: Mapped[float | None] = mapped_column(Float)
    n_volume: Mapped[int] = mapped_column(Integer)
    mean_volume: Mapped[float | None] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    rain_mm_per_day: Mapped[float | None] = mapped_column(Float)
    snow_cm_per_day: Mapped[float | None] = mapped_column(Float)
    coverage_pct: Mapped[float | None] = mapped_column(Float)
    is_outage: Mapped[bool | None] = mapped_column(Boolean)


class WeatherImpact(Base):
    """Tác động thời tiết (bước 16): % thay đổi thô và có kiểm soát."""
    __tablename__ = "weather_impact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)      # chieu: weather_condition, rainfall, ...
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)      # nhom
    n: Mapped[int] = mapped_column(Integer)
    n_days: Mapped[int] = mapped_column(Integer)
    raw_mean: Mapped[float | None] = mapped_column(Float)
    raw_change_pct: Mapped[float | None] = mapped_column(Float)
    controlled_change_pct: Mapped[float | None] = mapped_column(Float)
    controlled_month_change_pct: Mapped[float | None] = mapped_column(Float)
    ci95_pct: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("dimension", "group_key", name="uq_weather_impact_key"),)


class Anomaly(Base):
    """Bản ghi bất thường (bước 17, |z| > 3). Đúng các cột plan yêu cầu + ngữ cảnh."""
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    road_id: Mapped[str] = mapped_column(String(32), ForeignKey("roads.road_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)          # avg_speed | vehicle_count
    value: Mapped[float] = mapped_column(Float, nullable=False)
    expected: Mapped[float | None] = mapped_column(Float)
    std: Mapped[float | None] = mapped_column(Float)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    direction: Mapped[str | None] = mapped_column(String(32))
    vehicle_count: Mapped[float | None] = mapped_column(Float)
    avg_speed: Mapped[float | None] = mapped_column(Float)
    weather_condition: Mapped[str | None] = mapped_column(String(32))
    rainfall: Mapped[float | None] = mapped_column(Float)
    snowfall: Mapped[float | None] = mapped_column(Float)
    road_name: Mapped[str | None] = mapped_column(String(200))
    district: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        UniqueConstraint("road_id", "timestamp", "metric", name="uq_anomalies_key"),
        Index("ix_anomalies_timestamp", "timestamp"),
        Index("ix_anomalies_road", "road_id"),
    )


class AnomalyDaily(Base):
    """Số bất thường tốc độ theo ngày cho cả thành phố (bước 17)."""
    __tablename__ = "anomaly_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    day_type: Mapped[str | None] = mapped_column(String(16))
    records: Mapped[int] = mapped_column(Integer)
    slow_anomalies: Mapped[int] = mapped_column(Integer)
    fast_anomalies: Mapped[int] = mapped_column(Integer)
    anomaly_rate_pct: Mapped[float | None] = mapped_column(Float)
    mean_z: Mapped[float | None] = mapped_column(Float)
    rain_mm_per_day: Mapped[float | None] = mapped_column(Float)
    snow_cm_per_day: Mapped[float | None] = mapped_column(Float)
    coverage_pct: Mapped[float | None] = mapped_column(Float)
