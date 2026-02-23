import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TestPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"
    REJECTED = "REJECTED"


class TestPlan(Base):
    __tablename__ = "test_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dev_activity_id = Column(UUID(as_uuid=True), ForeignKey("development_activities.id", ondelete="CASCADE"), nullable=False)
    plan_name = Column(String(512), nullable=False)
    scope = Column(Text, nullable=True)
    test_strategy = Column(Text, nullable=True)
    entry_criteria = Column(Text, nullable=True)
    exit_criteria = Column(Text, nullable=True)
    status = Column(Enum(TestPlanStatus), nullable=False, default=TestPlanStatus.DRAFT)
    evidence_completeness_score = Column(Float, default=0.0)
    is_locked = Column(Boolean, default=False)
    lock_override_reason = Column(Text, nullable=True)
    submitted_for_review_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_autosave_at = Column(DateTime, nullable=True)

    dev_activity = relationship("DevelopmentActivity", back_populates="test_plans")
    test_cases = relationship("TestCase", back_populates="test_plan", cascade="all, delete-orphan")
    signoffs = relationship("Signoff", back_populates="test_plan", cascade="all, delete-orphan")
    evidence_artefacts = relationship(
        "EvidenceArtefact",
        primaryjoin="TestPlan.id == foreign(EvidenceArtefact.test_plan_id)",
        back_populates="test_plan"
    )
