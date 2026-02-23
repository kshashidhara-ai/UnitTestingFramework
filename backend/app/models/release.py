import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class EnvironmentScope(str, enum.Enum):
    SIT = "SIT"
    UAT = "UAT"
    PROD = "PROD"


class ReleaseStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Release(Base):
    __tablename__ = "releases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    release_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    environment_scope = Column(Enum(EnvironmentScope), nullable=False, default=EnvironmentScope.SIT)
    status = Column(Enum(ReleaseStatus), nullable=False, default=ReleaseStatus.PLANNED)
    planned_deploy_date = Column(Date, nullable=True)
    actual_deploy_date = Column(Date, nullable=True)
    release_notes = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="releases")
    dev_activities = relationship("DevelopmentActivity", back_populates="release", cascade="all, delete-orphan")
