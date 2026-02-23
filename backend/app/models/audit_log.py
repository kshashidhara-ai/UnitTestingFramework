import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
import enum


class ActionType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ROLE_MAPPED = "ROLE_MAPPED"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STATUS_CHANGE = "STATUS_CHANGE"
    ARTEFACT_UPLOAD = "ARTEFACT_UPLOAD"
    ARTEFACT_DOWNLOAD = "ARTEFACT_DOWNLOAD"
    SIGNOFF = "SIGNOFF"
    LOCK = "LOCK"
    LOCK_OVERRIDE = "LOCK_OVERRIDE"
    EXPORT = "EXPORT"
    BULK_IMPORT = "BULK_IMPORT"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_email = Column(String(255), nullable=False, index=True)
    user_role = Column(String(100), nullable=True)
    action_type = Column(Enum(ActionType), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(255), nullable=True, index=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(512), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
