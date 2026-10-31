import math

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size


def paginate(db: Session, stmt: Select, params: PageParams, transform=lambda x: x) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)).all()
    return {
        "items": [transform(r) for r in rows],
        "page": params.page,
        "page_size": params.page_size,
        "total": total,
        "pages": math.ceil(total / params.page_size) if total else 0,
    }


def paginate_list(rows: list, params: PageParams) -> dict:
    total = len(rows)
    start = (params.page - 1) * params.page_size
    return {
        "items": rows[start : start + params.page_size],
        "page": params.page,
        "page_size": params.page_size,
        "total": total,
        "pages": math.ceil(total / params.page_size) if total else 0,
    }
