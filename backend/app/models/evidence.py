import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ArtefactType(str, enum.Enum):
    # Snowflake
    SNOWFLAKE_QUERY_RESULT = "SNOWFLAKE_QUERY_RESULT"
    SNOWFLAKE_SCREENSHOT = "SNOWFLAKE_SCREENSHOT"
    SNOWFLAKE_EXPLAIN_PLAN = "SNOWFLAKE_EXPLAIN_PLAN"
    SNOWFLAKE_RECONCILIATION = "SNOWFLAKE_RECONCILIATION"
    # IICS
    IICS_ACTIVITY_LOG = "IICS_ACTIVITY_LOG"
    IICS_SESSION_LOG = "IICS_SESSION_LOG"
    IICS_MONITOR_SCREENSHOT = "IICS_MONITOR_SCREENSHOT"
    IICS_REJECTION_FILE = "IICS_REJECTION_FILE"
    # Generic
    SCREENSHOT = "SCREENSHOT"
    CSV_EXPORT = "CSV_EXPORT"
    PDF_DOCUMENT = "PDF_DOCUMENT"
    LOG_FILE = "LOG_FILE"
    OTHER = "OTHER"


class EvidenceArtefact(Base):
    __tablename__ = "evidence_artefacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=True)
    test_plan_id = Column(UUID(as_uuid=True), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=True)
    artefact_type = Column(Enum(ArtefactType), nullable=False)
    description = Column(Text, nullable=True)
    original_filename = Column(String(512), nullable=True)
    s3_object_key = Column(String(1024), nullable=False)
    s3_bucket = Column(String(255), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    content_type = Column(String(255), nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    is_legal_hold = Column(Boolean, default=False)
    retention_override_date = Column(DateTime, nullable=True)
    uploaded_by = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    test_case = relationship(
        "TestCase",
        primaryjoin="EvidenceArtefact.test_case_id == TestCase.id",
        back_populates="evidence_artefacts",
        foreign_keys="[EvidenceArtefact.test_case_id]"
    )
    test_plan = relationship(
        "TestPlan",
        primaryjoin="EvidenceArtefact.test_plan_id == TestPlan.id",
        back_populates="evidence_artefacts",
        foreign_keys="[EvidenceArtefact.test_plan_id]"
    )
