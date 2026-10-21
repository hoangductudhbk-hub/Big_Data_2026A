from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "NYC Traffic Big Data API"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/traffic_bigdata"
    # Thư mục data/ của project: nơi Phase 1–2 ghi kết quả (processed/, interim/)
    DATA_DIR: Path = PROJECT_ROOT / "data"
    # Cho phép dashboard ở origin khác gọi API (mặc định: mọi origin, vì chỉ đọc dữ liệu công khai)
    CORS_ORIGINS: str = "*"
    MAX_PAGE_SIZE: int = 1000
    MAX_IMPORT_ROWS: int = 100_000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
