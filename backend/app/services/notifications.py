"""Create notifications without ever endangering the caller's transaction.

Rows are added inside a SAVEPOINT in the caller's session, so they commit (or roll back) together
with the business change. Live push happens only after the commit succeeds. Any failure here is
logged and swallowed: a broken notification must never fail a donation, review or assignment.
"""
import hashlib
import logging
from collections.abc import Iterable

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    Donation,
    DonationStatus,
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
    Opportunity,
    User,
    Volunteer,
)
from app.ws.manager import manager

logger = logging.getLogger(__name__)
PENDING_KEY = "pending_push"


def serialize(n: Notification) -> dict:
    return {
        "id": n.id, "title": n.title, "message": n.message,
        "notification_type": n.notification_type.value, "priority": n.priority.value,
        "status": n.status.value, "link": n.link, "created_at": n.created_at.isoformat(),
    }


def notify(
    db: Session,
    user_ids: Iterable[int],
    *,
    title: str,
    message: str,
    type: NotificationType,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    link: str | None = None,
    dedupe_key: str | None = None,
) -> int:
    """Returns how many notifications were created (0 on failure or when everything was a duplicate)."""
    ids = {int(i) for i in user_ids}
    if not ids:
        return 0
    try:
        created: list[Notification] = []
        with db.begin_nested():
            ids -= _muted_users(db, ids, type, priority)

            for uid in sorted(ids):
                if dedupe_key and db.scalar(select(Notification.id).where(
                    Notification.user_id == uid, Notification.dedupe_key == dedupe_key,
                    Notification.status == NotificationStatus.UNREAD,
                ).limit(1)):
                    continue
                n = Notification(user_id=uid, title=title[:160], message=message, notification_type=type,
                                 priority=priority, link=link, dedupe_key=dedupe_key)
                db.add(n)
                created.append(n)
            db.flush()
        db.info.setdefault(PENDING_KEY, []).extend(
            {"user_id": n.user_id, "data": {"event": "notification", "notification": serialize(n)}}
            for n in created
        )
        return len(created)
    except Exception:
        logger.exception("Failed to create notification '%s'", title)
        return 0


@event.listens_for(Session, "after_commit")
def _deliver_after_commit(session: Session) -> None:
    payloads = session.info.pop(PENDING_KEY, None)
    if payloads:
        try:
            manager.publish(payloads)
        except Exception:
            logger.exception("Live notification delivery failed")


@event.listens_for(Session, "after_rollback")
def _discard_on_rollback(session: Session) -> None:
    session.info.pop(PENDING_KEY, None)


def _muted_users(db: Session, ids: set[int], type: NotificationType, priority: NotificationPriority) -> set[int]:
    """Users who switched this type off. HIGH priority and emergency alerts can never be muted."""
    if priority == NotificationPriority.HIGH or type == NotificationType.EMERGENCY_ALERT:
        return set()
    rows = db.execute(select(User.id, User.notification_prefs).where(User.id.in_(ids)))
    return {uid for uid, prefs in rows if type.value in ((prefs or {}).get("muted_types") or [])}


def dedupe_hash(*parts: object) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:20]


# ---- audiences -----------------------------------------------------------

def volunteer_user_ids(db: Session, ngo_id: int, campaign_id: int | None = None) -> set[int]:
    """Active volunteers with an accepted application with this NGO (optionally for one campaign)."""
    stmt = (
        select(Volunteer.user_id).distinct()
        .join(Application, Application.volunteer_id == Volunteer.id)
        .join(Opportunity, Application.opportunity_id == Opportunity.id)
        .join(User, User.id == Volunteer.user_id)
        .where(Opportunity.ngo_id == ngo_id, Application.status == ApplicationStatus.ACCEPTED,
               User.is_active.is_(True))
    )
    if campaign_id is not None:
        stmt = stmt.where(Opportunity.campaign_id == campaign_id)
    return set(db.scalars(stmt))


def donor_user_ids(db: Session, ngo_id: int, campaign_id: int | None = None) -> set[int]:
    stmt = (
        select(Donation.donor_id).distinct()
        .join(User, User.id == Donation.donor_id)
        .where(Donation.ngo_id == ngo_id, Donation.status != DonationStatus.REJECTED,
               User.is_active.is_(True))
    )
    if campaign_id is not None:
        stmt = stmt.where(Donation.campaign_id == campaign_id)
    return set(db.scalars(stmt))
