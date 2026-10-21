from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportLog(Base):
    """Nhật ký mỗi lần nạp dữ liệu (loader hoặc POST /import/...): truy vết được dữ liệu đến từ đâu."""
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(64), nullable=False)       # bảng đích
    source: Mapped[str] = mapped_column(String(300), nullable=False)      # file / "api"
    mode: Mapped[str] = mapped_column(String(16), nullable=False)         # replace | upsert
    rows_received: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False)       # ok | partial | failed
    message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
