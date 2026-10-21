"""Định dạng lỗi thống nhất cho mọi endpoint:

    {"error": {"status": 404, "type": "not_found", "message": "...", "details": ...}}

Client (dashboard) chỉ cần đọc một kiểu lỗi duy nhất, không phải đoán giữa nhiều dạng.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app")

_TYPES = {400: "bad_request", 404: "not_found", 405: "method_not_allowed", 409: "conflict",
          413: "payload_too_large", 422: "validation_error", 503: "service_unavailable"}


def error(status: int, message: str, details=None, type_: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {
        "status": status, "type": type_ or _TYPES.get(status, "error"), "message": message, "details": details}})


class ApiError(HTTPException):
    def __init__(self, status: int, message: str, details=None):
        super().__init__(status_code=status, detail=message)
        self.details = details


def not_found(what: str) -> ApiError:
    return ApiError(404, f"Không tìm thấy {what}")


def install(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return error(exc.status_code, str(exc.detail), getattr(exc, "details", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return error(422, "Tham số hoặc dữ liệu gửi lên không hợp lệ", details)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError):
        return error(409, "Dữ liệu vi phạm ràng buộc của database (khóa trùng, khóa ngoại hoặc CHECK theo contract)",
                     str(exc.orig).splitlines()[0] if exc.orig else None)

    @app.exception_handler(OperationalError)
    async def _db_down(_: Request, exc: OperationalError):
        log.error("Database error: %s", exc)
        return error(503, "Không kết nối được database. Kiểm tra PostgreSQL đã chạy chưa (docker compose up -d db).")

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.exception("Unhandled error")
        return error(500, "Lỗi không mong đợi ở server", type(exc).__name__, "internal_error")
