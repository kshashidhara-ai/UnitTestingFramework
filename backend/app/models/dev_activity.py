import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ActivityType(str, enum.Enum):
    SNOWFLAKE = "SNOWFLAKE"
    IICS = "IICS"
    MIXED = "MIXED"
    OTHER = "OTHER"


class DevelopmentActivity(Base):
    __tablename__ = "development_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    release_id = Column(UUID(as_uuid=True), ForeignKey("releases.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(Enum(ActivityType), nullable=False, default=ActivityType.MIXED)
    jira_id = Column(String(100), nullable=True, index=True)
    git_repo = Column(String(512), nullable=True)
    pr_link = Column(String(512), nullable=True)
    commit_hash = Column(String(100), nullable=True)
    # JSON arrays for flexible object references
    snowflake_objects = Column(JSONB, nullable=True)  # [{db, schema, object, type}]
    iics_assets = Column(JSONB, nullable=True)        # [{org, type, name, asset_id}]
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    release = relationship("Release", back_populates="dev_activities")
    test_plans = relationship("TestPlan", back_populates="dev_activity", cascade="all, delete-orphan")
