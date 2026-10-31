from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, enum_column
from app.models.enums import NotificationPriority, NotificationStatus, NotificationType


class Notification(TimestampMixin, Base):
    """`created_at` is the notification date. `dedupe_key` stops identical unread alerts piling up."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_status", "user_id", "status"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    notification_type: Mapped[NotificationType] = enum_column(NotificationType, index=True)
    priority: Mapped[NotificationPriority] = enum_column(
        NotificationPriority, default=NotificationPriority.NORMAL, index=True
    )
    status: Mapped[NotificationStatus] = enum_column(NotificationStatus, default=NotificationStatus.UNREAD)
    link: Mapped[str | None] = mapped_column(String(200))
    dedupe_key: Mapped[str | None] = mapped_column(String(120), index=True)
