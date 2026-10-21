"""Các bảng PostgreSQL. Import module này để đăng ký mọi bảng vào Base.metadata (Alembic, tests)."""
from app.models.analytics import AnomalyDaily, Anomaly, DailyStat, Statistic, WeatherImpact  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.import_log import ImportLog  # noqa: F401
from app.models.road import Road  # noqa: F401
from app.models.traffic import IntegratedTraffic  # noqa: F401
from app.models.weather import WeatherRecord  # noqa: F401
