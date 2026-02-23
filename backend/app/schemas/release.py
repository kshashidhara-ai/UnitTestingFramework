from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from app.models.release import EnvironmentScope, ReleaseStatus


class ReleaseBase(BaseModel):
    release_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    environment_scope: EnvironmentScope = EnvironmentScope.SIT
    status: ReleaseStatus = ReleaseStatus.PLANNED
    planned_deploy_date: Optional[date] = None
    release_notes: Optional[str] = None


class ReleaseCreate(ReleaseBase):
    project_id: UUID


class ReleaseUpdate(BaseModel):
    release_name: Optional[str] = None
    description: Optional[str] = None
    environment_scope: Optional[EnvironmentScope] = None
    status: Optional[ReleaseStatus] = None
    planned_deploy_date: Optional[date] = None
    actual_deploy_date: Optional[date] = None
    release_notes: Optional[str] = None


class ReleaseResponse(ReleaseBase):
    id: UUID
    project_id: UUID
    actual_deploy_date: Optional[date] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
