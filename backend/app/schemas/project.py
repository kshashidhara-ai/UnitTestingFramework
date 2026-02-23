from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255)
    domain: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    owner_team: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    dataset: Optional[str] = Field(None, max_length=255)
    vendor: Optional[str] = Field(None, max_length=255)
    frequency: Optional[str] = Field(None, max_length=50)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = None
    description: Optional[str] = None
    owner_team: Optional[str] = None
    country: Optional[str] = None
    dataset: Optional[str] = None
    vendor: Optional[str] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    id: UUID
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
