from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.dev_activity import DevelopmentActivity
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.dev_activity import DevActivityCreate, DevActivityUpdate, DevActivityResponse

router = APIRouter(prefix="/dev-activities", tags=["Development Activities"])


@router.get("", response_model=List[DevActivityResponse])
async def list_dev_activities(
    release_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(DevelopmentActivity)
    if release_id:
        q = q.filter(DevelopmentActivity.release_id == release_id)
    if project_id:
        q = q.filter(DevelopmentActivity.project_id == project_id)
    return q.order_by(DevelopmentActivity.created_at.desc()).all()


@router.post("", response_model=DevActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_dev_activity(
    data: DevActivityCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    activity = DevelopmentActivity(**data.model_dump(), created_by=current_user["email"])
    db.add(activity)
    db.commit()
    db.refresh(activity)
    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.CREATE, entity_type="DevelopmentActivity",
        entity_id=str(activity.id), new_value={"title": activity.title},
        user_role=current_user.get("role"),
    )
    return activity


@router.get("/{activity_id}", response_model=DevActivityResponse)
async def get_dev_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    activity = db.query(DevelopmentActivity).filter(DevelopmentActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.patch("/{activity_id}", response_model=DevActivityResponse)
async def update_dev_activity(
    activity_id: UUID,
    data: DevActivityUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    activity = db.query(DevelopmentActivity).filter(DevelopmentActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity
