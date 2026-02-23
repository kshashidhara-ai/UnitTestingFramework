from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.test_plan import TestPlanStatus


class TestPlanBase(BaseModel):
    plan_name: str = Field(..., max_length=512)
    scope: Optional[str] = None
    test_strategy: Optional[str] = None
    entry_criteria: Optional[str] = None
    exit_criteria: Optional[str] = None


class TestPlanCreate(TestPlanBase):
    dev_activity_id: UUID


class TestPlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    scope: Optional[str] = None
    test_strategy: Optional[str] = None
    entry_criteria: Optional[str] = None
    exit_criteria: Optional[str] = None
    status: Optional[TestPlanStatus] = None


class TestPlanResponse(TestPlanBase):
    id: UUID
    dev_activity_id: UUID
    status: TestPlanStatus
    evidence_completeness_score: float
    is_locked: bool
    submitted_for_review_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_autosave_at: Optional[datetime] = None
    test_case_count: Optional[int] = None
    pass_count: Optional[int] = None
    fail_count: Optional[int] = None
    not_run_count: Optional[int] = None

    class Config:
        from_attributes = True


class TestPlanSummary(BaseModel):
    id: UUID
    plan_name: str
    status: TestPlanStatus
    evidence_completeness_score: float
    is_locked: bool
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class TestPlanSubmitReview(BaseModel):
    comments: Optional[str] = None


class TestPlanLockOverride(BaseModel):
    reason: str = Field(..., min_length=10)
