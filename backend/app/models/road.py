from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Road(Base):
    """Danh mục đường sau record linkage (bước 09, data/processed/roads.parquet).
    road_id: 'L<link_id>' (có cảm biến tốc độ) hoặc 'S<segmentid>' (chỉ có điểm đếm lưu lượng)."""
    __tablename__ = "roads"

    road_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    road_name: Mapped[str] = mapped_column(String(200))
    district: Mapped[str | None] = mapped_column(String(32), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    link_id: Mapped[str | None] = mapped_column(String(32))
    segmentid: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    has_speed: Mapped[bool] = mapped_column(Boolean, default=False)
    has_volume: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
