from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_action(
    db: Session,
    actor: User | None,
    action_type: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit row in the caller's session so it commits atomically with the change."""
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    db.add(entry)
    return entry
