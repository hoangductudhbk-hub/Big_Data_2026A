"""FastAPI — NYC Traffic Big Data API (Phase 3).

    cd backend && uvicorn app.main:app --reload
    Tài liệu API: http://localhost:8000/docs      Dashboard: http://localhost:8000/dashboard/
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import app as _app  # noqa: F401  (sys.path cho common.contract)
from app.api.routes import anomalies, health, imports, roads, statistics, traffic, weather
from app.core import errors
from app.core.config import settings

API = "/api/v1"

app = FastAPI(title=settings.APP_NAME, version="1.0.0",
              description="Dữ liệu giao thông New York 2024 (tốc độ + lưu lượng) tích hợp thời tiết, "
                          "kết quả thống kê và phát hiện bất thường của PySpark.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
                   allow_methods=["*"], allow_headers=["*"])
errors.install(app)

app.include_router(health.router, prefix=f"{API}/health", tags=["health"])
app.include_router(roads.router, prefix=f"{API}/roads", tags=["roads"])
app.include_router(traffic.router, prefix=f"{API}/traffic", tags=["traffic"])
app.include_router(weather.router, prefix=f"{API}/weather", tags=["weather"])
app.include_router(statistics.router, prefix=f"{API}/statistics", tags=["statistics"])
app.include_router(anomalies.router, prefix=f"{API}/anomalies", tags=["anomalies"])
app.include_router(imports.router, prefix=f"{API}/import", tags=["import"])

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
if DASHBOARD.exists():
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD, html=True), name="dashboard")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard/" if DASHBOARD.exists() else "/docs")


@app.get("/health", include_in_schema=False)
def health_alias():
    """Plan yêu cầu GET /health: alias của /api/v1/health."""
    return health.health()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
