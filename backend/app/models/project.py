import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    domain = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    owner_team = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    dataset = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    frequency = Column(String(50), nullable=True)  # Weekly/Monthly/Daily
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan")
