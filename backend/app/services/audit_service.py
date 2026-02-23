"""Audit logging service."""
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, ActionType
import structlog

logger = structlog.get_logger()


def log_action(
    db: Session,
    user_email: str,
    action_type: ActionType,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    user_role: Optional[str] = None,
):
    """Write an audit log entry to the database."""
    entry = AuditLog(
        user_email=user_email,
        user_role=user_role,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        old_value=old_value,
        new_value=new_value,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()

    logger.info(
        "Audit log",
        user=user_email,
        action=action_type.value,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
    )
