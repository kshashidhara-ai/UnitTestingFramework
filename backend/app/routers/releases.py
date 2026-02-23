from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.release import Release
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.release import ReleaseCreate, ReleaseUpdate, ReleaseResponse
from typing import List, Optional

router = APIRouter(prefix="/releases", tags=["Releases"])


@router.get("", response_model=List[ReleaseResponse])
async def list_releases(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Release)
    if project_id:
        query = query.filter(Release.project_id == project_id)
    return query.order_by(Release.created_at.desc()).all()


@router.post("", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
async def create_release(
    data: ReleaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    release = Release(**data.model_dump(), created_by=current_user["email"])
    db.add(release)
    db.commit()
    db.refresh(release)
    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.CREATE, entity_type="Release",
        entity_id=str(release.id), new_value={"name": release.release_name},
        user_role=current_user.get("role"),
    )
    return release


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(
    release_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.patch("/{release_id}", response_model=ReleaseResponse)
async def update_release(
    release_id: UUID,
    data: ReleaseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(release, field, value)
    db.commit()
    db.refresh(release)
    return release
