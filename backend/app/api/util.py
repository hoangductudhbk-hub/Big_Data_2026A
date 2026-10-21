from sqlalchemy import func, select
from sqlalchemy.orm import Session


def paginate(db: Session, stmt, pg, order_by=()):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    items = db.scalars(stmt.order_by(*order_by).offset(pg.offset).limit(pg.page_size)).all()
    return {"items": items, "page": pg.page, "page_size": pg.page_size, "total": total}
