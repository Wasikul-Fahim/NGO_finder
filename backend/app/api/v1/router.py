from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.v1 import auth, campaigns, events, ngos

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def health(db: DbSession):
    db.execute(select(1))
    return {"status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(ngos.router)
api_router.include_router(campaigns.router)
api_router.include_router(events.router)
