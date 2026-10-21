from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from common.contract import CONTRACT_VERSION

router = APIRouter()


@router.get("", summary="Server còn sống")
def health():
    return {"status": "ok", "contract_version": CONTRACT_VERSION}


@router.get("/db", summary="Kết nối database và phiên bản schema (Alembic)")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        raise ApiError(503, "Không kết nối được database", str(e).splitlines()[0])
    try:
        rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:  # noqa: BLE001  (test dùng create_all, không có bảng alembic_version)
        db.rollback()
        rev = None
    return {"status": "ok", "database": db.get_bind().dialect.name, "schema_revision": rev}
