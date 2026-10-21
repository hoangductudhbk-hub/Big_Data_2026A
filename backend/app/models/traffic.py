"""Bảng integrated_traffic: đúng 14 cột của data contract (common/contract.py) + khóa thay thế `id`.

Ràng buộc CHECK (khoảng giá trị, giá trị cho phép) được SINH TỰ ĐỘNG từ contract, nên database
không thể lệch với Phase 1–2: sửa contract → sinh migration mới.
"""
from datetime import datetime

from sqlalchemy import (BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from common.contract import INTEGRATED_TRAFFIC


def contract_checks() -> list[CheckConstraint]:
    checks = []
    for c in INTEGRATED_TRAFFIC:
        conds = []
        if c.min_value is not None:
            conds.append(f"{c.name} >= {c.min_value}")
        if c.max_value is not None:
            conds.append(f"{c.name} <= {c.max_value}")
        if c.allowed:
            conds.append(f"{c.name} IN ({', '.join(repr(v) for v in c.allowed)})")
        if conds:
            expr = " AND ".join(conds)
            if c.nullable:
                expr = f"{c.name} IS NULL OR ({expr})"
            checks.append(CheckConstraint(expr, name=f"ck_integrated_traffic_{c.name}"))
    return checks


class IntegratedTraffic(Base):
    __tablename__ = "integrated_traffic"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"),
                                    primary_key=True, autoincrement=True)
    road_id: Mapped[str] = mapped_column(String(32), ForeignKey("roads.road_id"), nullable=False)
    road_name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[str] = mapped_column(String(32), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # Giờ địa phương New York, KHÔNG kèm múi giờ (contract) → TIMESTAMP WITHOUT TIME ZONE
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    vehicle_count: Mapped[int | None] = mapped_column(BigInteger)
    avg_speed: Mapped[float | None] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    rainfall: Mapped[float | None] = mapped_column(Float)
    snowfall: Mapped[float | None] = mapped_column(Float)
    weather_condition: Mapped[str | None] = mapped_column(String(32))
    weather_station_id: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        UniqueConstraint("road_id", "timestamp", name="uq_integrated_traffic_road_ts"),   # khóa chính của contract
        Index("ix_integrated_traffic_timestamp", "timestamp"),
        Index("ix_integrated_traffic_district_ts", "district", "timestamp"),
        *contract_checks(),
    )
