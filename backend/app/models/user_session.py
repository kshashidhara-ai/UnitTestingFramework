import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = Column(String(512), nullable=False, unique=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    role = Column(String(100), nullable=False)
    azure_groups = Column(JSONB, nullable=True)
    saml_name_id = Column(String(512), nullable=True)
    saml_session_index = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
