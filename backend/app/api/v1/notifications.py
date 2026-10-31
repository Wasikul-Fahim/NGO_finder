from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, DbSession, VerifiedNgo
from app.core.errors import not_found
from app.models import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.schemas.common import Page
from app.schemas.notification import (
    AnnouncementCreate,
    AnnouncementResult,
    NotificationOut,
    UnreadCount,
)
from app.services import campaigns as campaign_svc
from app.services import notifications as svc
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=Page[NotificationOut])
def list_notifications(
    user: CurrentUser, db: DbSession, params: Annotated[PageParams, Depends()],
    status: NotificationStatus | None = None, priority: NotificationPriority | None = None,
    notification_type: NotificationType | None = None,
):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if status:
        stmt = stmt.where(Notification.status == status)
    if priority:
        stmt = stmt.where(Notification.priority == priority)
    if notification_type:
        stmt = stmt.where(Notification.notification_type == notification_type)
    return paginate(db, stmt.order_by(Notification.created_at.desc(), Notification.id.desc()), params,
                    NotificationOut.model_validate)


@router.get("/notifications/unread-count", response_model=UnreadCount)
def unread_count(user: CurrentUser, db: DbSession):
    base = select(func.count()).where(Notification.user_id == user.id,
                                      Notification.status == NotificationStatus.UNREAD)
    return UnreadCount(
        unread=db.scalar(base) or 0,
        high_priority_unread=db.scalar(base.where(Notification.priority == NotificationPriority.HIGH)) or 0,
    )


@router.patch("/notifications/read-all", status_code=204)
def read_all(user: CurrentUser, db: DbSession):
    db.execute(update(Notification).where(
        Notification.user_id == user.id, Notification.status == NotificationStatus.UNREAD
    ).values(status=NotificationStatus.READ))
    db.commit()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise not_found("Notification")  # never reveal other users' notifications
    n.status = NotificationStatus.READ
    db.commit()
    return n


@router.post("/announcements", response_model=AnnouncementResult, status_code=201)
def announce(data: AnnouncementCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    """Message the volunteers and/or donors connected to this NGO. HIGH priority = emergency alert."""
    if data.campaign_id is not None:
        campaign_svc.get_owned_campaign(db, data.campaign_id, ngo)
    audience: set[int] = set()
    if data.audience in ("VOLUNTEERS", "ALL"):
        audience |= svc.volunteer_user_ids(db, ngo.id, data.campaign_id)
    if data.audience in ("DONORS", "ALL"):
        audience |= svc.donor_user_ids(db, ngo.id, data.campaign_id)
    emergency = data.priority == "HIGH"
    created = svc.notify(
        db, audience, title=data.title, message=data.message,
        type=NotificationType.EMERGENCY_ALERT if emergency else NotificationType.ANNOUNCEMENT,
        priority=NotificationPriority(data.priority),
        dedupe_key=f"announce:{ngo.id}:{svc.dedupe_hash(data.title, data.message)}",
    )
    log_action(db, user, "SEND_EMERGENCY_ALERT" if emergency else "SEND_ANNOUNCEMENT", "NGO", ngo.id,
               {"title": data.title, "audience": data.audience, "campaign_id": data.campaign_id,
                "audience_size": len(audience), "recipients": created})
    db.commit()
    return AnnouncementResult(recipients=created, audience_size=len(audience), emergency=emergency)
