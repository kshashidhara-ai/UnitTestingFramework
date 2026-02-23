from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.signoff import SignoffLevel, SignoffDecision


class SignoffCreate(BaseModel):
    test_plan_id: UUID
    level: SignoffLevel
    comments: Optional[str] = None


class SignoffDecisionRequest(BaseModel):
    decision: SignoffDecision
    comments: Optional[str] = None
    rejection_reason: Optional[str] = None


class SignoffResponse(BaseModel):
    id: UUID
    test_plan_id: UUID
    level: SignoffLevel
    decision: SignoffDecision
    comments: Optional[str] = None
    rejection_reason: Optional[str] = None
    signed_by: Optional[str] = None
    signed_by_name: Optional[str] = None
    signed_at: Optional[datetime] = None
    requested_at: datetime
    requested_by: str

    class Config:
        from_attributes = True
