from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.v1 import applications, auth, campaigns, events, ngos, opportunities, tasks, volunteers

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def health(db: DbSession):
    db.execute(select(1))
    return {"status": "ok"}


api_router.include_router(auth.router)
api_router.include_router(ngos.router)
api_router.include_router(campaigns.router)
api_router.include_router(events.router)
api_router.include_router(volunteers.router)
api_router.include_router(opportunities.router)
api_router.include_router(applications.router)
api_router.include_router(tasks.router)
