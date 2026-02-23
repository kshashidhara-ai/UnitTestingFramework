import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class SignoffLevel(str, enum.Enum):
    PEER = "PEER"
    QA = "QA"
    RELEASE = "RELEASE"


class SignoffDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class Signoff(Base):
    __tablename__ = "signoffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_plan_id = Column(UUID(as_uuid=True), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False)
    level = Column(Enum(SignoffLevel), nullable=False)
    decision = Column(Enum(SignoffDecision), nullable=False, default=SignoffDecision.PENDING)
    comments = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    signed_by = Column(String(255), nullable=True)
    signed_by_name = Column(String(255), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(String(255), nullable=False)

    test_plan = relationship("TestPlan", back_populates="signoffs")
