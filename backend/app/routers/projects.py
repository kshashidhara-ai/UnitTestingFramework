from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models.project import Project
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectList

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectList)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    country: Optional[str] = None,
    vendor: Optional[str] = None,
    frequency: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Project)
    if is_active is not None:
        query = query.filter(Project.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                Project.name.ilike(f"%{search}%"),
                Project.domain.ilike(f"%{search}%"),
                Project.owner_team.ilike(f"%{search}%"),
            )
        )
    if country:
        query = query.filter(Project.country == country)
    if vendor:
        query = query.filter(Project.vendor.ilike(f"%{vendor}%"))
    if frequency:
        query = query.filter(Project.frequency == frequency)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ProjectList(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    existing = db.query(Project).filter(Project.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Project '{data.name}' already exists")

    project = Project(**data.model_dump(), created_by=current_user["email"])
    db.add(project)
    db.commit()
    db.refresh(project)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.CREATE, entity_type="Project",
        entity_id=str(project.id),
        new_value={"name": project.name},
        user_role=current_user.get("role"),
    )
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    old_values = {k: getattr(project, k) for k in data.model_dump(exclude_none=True)}
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.UPDATE, entity_type="Project",
        entity_id=str(project.id),
        old_value=old_values,
        new_value=data.model_dump(exclude_none=True),
        user_role=current_user.get("role"),
    )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.DELETE, entity_type="Project",
        entity_id=str(project_id),
        description=f"Deleted project: {project.name}",
        user_role=current_user.get("role"),
    )
