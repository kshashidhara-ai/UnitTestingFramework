import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String as Str
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TestCaseStatus(str, enum.Enum):
    NOT_RUN = "NOT_RUN"
    IN_PROGRESS = "IN_PROGRESS"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    WAIVED = "WAIVED"


class TestCaseCategory(str, enum.Enum):
    FUNCTIONAL = "FUNCTIONAL"
    REGRESSION = "REGRESSION"
    PERFORMANCE = "PERFORMANCE"
    DATA_QUALITY = "DATA_QUALITY"
    INTEGRATION = "INTEGRATION"
    RECONCILIATION = "RECONCILIATION"
    IDEMPOTENCY = "IDEMPOTENCY"
    NEGATIVE = "NEGATIVE"


class TestCaseComponent(str, enum.Enum):
    SNOWFLAKE = "SNOWFLAKE"
    IICS = "IICS"
    BOTH = "BOTH"
    OTHER = "OTHER"


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_plan_id = Column(UUID(as_uuid=True), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False)
    testcase_id = Column(String(50), nullable=False)  # Human-readable ID e.g. TC-001
    category = Column(Enum(TestCaseCategory), nullable=False, default=TestCaseCategory.FUNCTIONAL)
    component = Column(Enum(TestCaseComponent), nullable=False, default=TestCaseComponent.SNOWFLAKE)
    objective = Column(Text, nullable=False)
    preconditions = Column(Text, nullable=True)
    test_steps = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)
    actual_result = Column(Text, nullable=True)
    status = Column(Enum(TestCaseStatus), nullable=False, default=TestCaseStatus.NOT_RUN)
    defect_reference = Column(String(255), nullable=True)  # JIRA ID for FAIL cases
    waiver_reason = Column(Text, nullable=True)
    waiver_approved_by = Column(String(255), nullable=True)

    # Snowflake-specific fields
    snowflake_query_ids = Column(ARRAY(Str), nullable=True)
    snowflake_warehouse = Column(String(255), nullable=True)
    snowflake_database_schema_object = Column(String(512), nullable=True)
    sql_executed = Column(Text, nullable=True)
    snowflake_execution_timestamp = Column(DateTime, nullable=True)
    snowflake_rows_produced = Column(String(50), nullable=True)
    snowflake_execution_duration_ms = Column(String(50), nullable=True)
    snowflake_error_message = Column(Text, nullable=True)

    # IICS-specific fields
    iics_run_ids = Column(ARRAY(Str), nullable=True)
    iics_org = Column(String(255), nullable=True)
    iics_asset_type = Column(String(100), nullable=True)
    iics_asset_name = Column(String(512), nullable=True)
    iics_asset_id = Column(String(255), nullable=True)
    iics_run_start = Column(DateTime, nullable=True)
    iics_run_end = Column(DateTime, nullable=True)
    iics_run_status = Column(String(50), nullable=True)

    executed_by = Column(String(255), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    reviewer_comment = Column(Text, nullable=True)
    is_template = Column(Boolean, default=False)
    template_name = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test_plan = relationship("TestPlan", back_populates="test_cases")
    evidence_artefacts = relationship(
        "EvidenceArtefact",
        primaryjoin="TestCase.id == foreign(EvidenceArtefact.test_case_id)",
        back_populates="test_case"
    )
