from datetime import datetime

from fastapi import Query

from app.core.config import settings


class Pagination:
    def __init__(self, page: int = Query(1, ge=1, description="Trang, bắt đầu từ 1"),
                 page_size: int = Query(50, ge=1, le=settings.MAX_PAGE_SIZE, description="Số dòng mỗi trang")):
        self.page, self.page_size = page, page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class TimeRange:
    def __init__(self, start: datetime | None = Query(None, description="Từ thời điểm (giờ New York), vd 2024-03-01"),
                 end: datetime | None = Query(None, description="Trước thời điểm (không gồm), vd 2024-04-01")):
        from app.core.errors import ApiError
        if start and end and start >= end:
            raise ApiError(400, "start phải nhỏ hơn end")
        self.start, self.end = start, end

    def apply(self, stmt, col):
        if self.start:
            stmt = stmt.where(col >= self.start)
        if self.end:
            stmt = stmt.where(col < self.end)
        return stmt
