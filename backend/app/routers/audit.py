from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.audit_log import AuditLog, ActionType
from app.middleware.auth import require_role

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("")
async def get_audit_log(
    user_email: Optional[str] = None,
    action_type: Optional[ActionType] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    q = db.query(AuditLog)
    if user_email:
        q = q.filter(AuditLog.user_email == user_email)
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)

    total = q.count()
    items = q.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(item.id),
                "user_email": item.user_email,
                "user_role": item.user_role,
                "action_type": item.action_type.value,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "description": item.description,
                "timestamp": item.timestamp.isoformat(),
                "ip_address": item.ip_address,
            }
            for item in items
        ],
    }
