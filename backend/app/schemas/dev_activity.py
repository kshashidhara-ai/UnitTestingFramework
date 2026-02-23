from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.dev_activity import ActivityType


class SnowflakeObject(BaseModel):
    database: str
    schema_name: str
    object_name: str
    object_type: str  # TABLE, VIEW, PROCEDURE, STAGE, etc.


class IICSAsset(BaseModel):
    org: str
    asset_type: str  # Mapping, Task, Taskflow
    asset_name: str
    asset_id: Optional[str] = None


class DevActivityBase(BaseModel):
    title: str = Field(..., max_length=512)
    description: Optional[str] = None
    activity_type: ActivityType = ActivityType.MIXED
    jira_id: Optional[str] = Field(None, max_length=100)
    git_repo: Optional[str] = None
    pr_link: Optional[str] = None
    commit_hash: Optional[str] = None
    snowflake_objects: Optional[List[Dict[str, Any]]] = None
    iics_assets: Optional[List[Dict[str, Any]]] = None


class DevActivityCreate(DevActivityBase):
    project_id: UUID
    release_id: UUID


class DevActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_type: Optional[ActivityType] = None
    jira_id: Optional[str] = None
    git_repo: Optional[str] = None
    pr_link: Optional[str] = None
    commit_hash: Optional[str] = None
    snowflake_objects: Optional[List[Dict[str, Any]]] = None
    iics_assets: Optional[List[Dict[str, Any]]] = None


class DevActivityResponse(DevActivityBase):
    id: UUID
    project_id: UUID
    release_id: UUID
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
