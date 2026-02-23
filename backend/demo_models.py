"""
SQLite-compatible models for demo mode.
Replaces JSONB → JSON (Text) and ARRAY → JSON (Text).
"""
import uuid
import json
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Float, BigInteger,
    ForeignKey, Enum, Date, create_engine
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool
import enum


Base = declarative_base()

# ── JSON helper (stores dicts/lists as JSON text) ────────────────────────────

class JSONText(TypeDecorator):
    impl = Text
    cache_ok = True
    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else None
    def process_result_value(self, value, dialect):
        if value is None: return None
        try: return json.loads(value)
        except: return value


# ── Enums ────────────────────────────────────────────────────────────────────

class EnvironmentScope(str, enum.Enum):
    SIT = "SIT"; UAT = "UAT"; PROD = "PROD"

class ReleaseStatus(str, enum.Enum):
    PLANNED = "PLANNED"; IN_PROGRESS = "IN_PROGRESS"; COMPLETED = "COMPLETED"; CANCELLED = "CANCELLED"

class ActivityType(str, enum.Enum):
    SNOWFLAKE = "SNOWFLAKE"; IICS = "IICS"; MIXED = "MIXED"; OTHER = "OTHER"

class TestPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"; IN_REVIEW = "IN_REVIEW"; APPROVED = "APPROVED"; LOCKED = "LOCKED"; REJECTED = "REJECTED"

class TestCaseStatus(str, enum.Enum):
    NOT_RUN = "NOT_RUN"; IN_PROGRESS = "IN_PROGRESS"; PASS = "PASS"; FAIL = "FAIL"; BLOCKED = "BLOCKED"; WAIVED = "WAIVED"

class TestCaseCategory(str, enum.Enum):
    FUNCTIONAL = "FUNCTIONAL"; REGRESSION = "REGRESSION"; PERFORMANCE = "PERFORMANCE"
    DATA_QUALITY = "DATA_QUALITY"; INTEGRATION = "INTEGRATION"; RECONCILIATION = "RECONCILIATION"
    IDEMPOTENCY = "IDEMPOTENCY"; NEGATIVE = "NEGATIVE"

class TestCaseComponent(str, enum.Enum):
    SNOWFLAKE = "SNOWFLAKE"; IICS = "IICS"; BOTH = "BOTH"; OTHER = "OTHER"

class ArtefactType(str, enum.Enum):
    SNOWFLAKE_QUERY_RESULT = "SNOWFLAKE_QUERY_RESULT"; SNOWFLAKE_SCREENSHOT = "SNOWFLAKE_SCREENSHOT"
    SNOWFLAKE_EXPLAIN_PLAN = "SNOWFLAKE_EXPLAIN_PLAN"; SNOWFLAKE_RECONCILIATION = "SNOWFLAKE_RECONCILIATION"
    IICS_ACTIVITY_LOG = "IICS_ACTIVITY_LOG"; IICS_SESSION_LOG = "IICS_SESSION_LOG"
    IICS_MONITOR_SCREENSHOT = "IICS_MONITOR_SCREENSHOT"; IICS_REJECTION_FILE = "IICS_REJECTION_FILE"
    SCREENSHOT = "SCREENSHOT"; CSV_EXPORT = "CSV_EXPORT"; PDF_DOCUMENT = "PDF_DOCUMENT"
    LOG_FILE = "LOG_FILE"; OTHER = "OTHER"

class SignoffLevel(str, enum.Enum):
    PEER = "PEER"; QA = "QA"; RELEASE = "RELEASE"

class SignoffDecision(str, enum.Enum):
    APPROVED = "APPROVED"; REJECTED = "REJECTED"; PENDING = "PENDING"

class ActionType(str, enum.Enum):
    LOGIN = "LOGIN"; LOGOUT = "LOGOUT"; ROLE_MAPPED = "ROLE_MAPPED"; CREATE = "CREATE"
    UPDATE = "UPDATE"; DELETE = "DELETE"; STATUS_CHANGE = "STATUS_CHANGE"
    ARTEFACT_UPLOAD = "ARTEFACT_UPLOAD"; ARTEFACT_DOWNLOAD = "ARTEFACT_DOWNLOAD"
    SIGNOFF = "SIGNOFF"; LOCK = "LOCK"; LOCK_OVERRIDE = "LOCK_OVERRIDE"
    EXPORT = "EXPORT"; BULK_IMPORT = "BULK_IMPORT"


# ── Models ───────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    domain = Column(String(100)); description = Column(Text); owner_team = Column(String(255))
    country = Column(String(100)); dataset = Column(String(255)); vendor = Column(String(255))
    frequency = Column(String(50)); is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    releases = relationship("Release", back_populates="project", cascade="all, delete-orphan")


class Release(Base):
    __tablename__ = "releases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    release_name = Column(String(255), nullable=False); description = Column(Text)
    environment_scope = Column(String(10), nullable=False, default="SIT")
    status = Column(String(20), nullable=False, default="PLANNED")
    planned_deploy_date = Column(Date); actual_deploy_date = Column(Date); release_notes = Column(Text)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = relationship("Project", back_populates="releases")
    dev_activities = relationship("DevelopmentActivity", back_populates="release", cascade="all, delete-orphan")


class DevelopmentActivity(Base):
    __tablename__ = "development_activities"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    release_id = Column(String(36), ForeignKey("releases.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False); description = Column(Text)
    activity_type = Column(String(20), nullable=False, default="MIXED")
    jira_id = Column(String(100)); git_repo = Column(String(512)); pr_link = Column(String(512))
    commit_hash = Column(String(100))
    snowflake_objects = Column(JSONText); iics_assets = Column(JSONText)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = relationship("Project")
    release = relationship("Release", back_populates="dev_activities")
    test_plans = relationship("TestPlan", back_populates="dev_activity", cascade="all, delete-orphan")


class TestPlan(Base):
    __tablename__ = "test_plans"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dev_activity_id = Column(String(36), ForeignKey("development_activities.id", ondelete="CASCADE"), nullable=False)
    plan_name = Column(String(512), nullable=False); scope = Column(Text); test_strategy = Column(Text)
    entry_criteria = Column(Text); exit_criteria = Column(Text)
    status = Column(String(20), nullable=False, default="DRAFT")
    evidence_completeness_score = Column(Float, default=0.0)
    is_locked = Column(Boolean, default=False); lock_override_reason = Column(Text)
    submitted_for_review_at = Column(DateTime); last_autosave_at = Column(DateTime)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dev_activity = relationship("DevelopmentActivity", back_populates="test_plans")
    test_cases = relationship("TestCase", back_populates="test_plan", cascade="all, delete-orphan")
    signoffs = relationship("Signoff", back_populates="test_plan", cascade="all, delete-orphan")
    evidence_artefacts = relationship("EvidenceArtefact",
        primaryjoin="TestPlan.id == foreign(EvidenceArtefact.test_plan_id)", back_populates="test_plan")


class TestCase(Base):
    __tablename__ = "test_cases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_plan_id = Column(String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False)
    testcase_id = Column(String(50), nullable=False)
    category = Column(String(30), nullable=False, default="FUNCTIONAL")
    component = Column(String(20), nullable=False, default="SNOWFLAKE")
    objective = Column(Text, nullable=False); preconditions = Column(Text)
    test_steps = Column(Text, nullable=False); expected_result = Column(Text, nullable=False)
    actual_result = Column(Text); status = Column(String(20), nullable=False, default="NOT_RUN")
    defect_reference = Column(String(255)); waiver_reason = Column(Text); waiver_approved_by = Column(String(255))
    snowflake_query_ids = Column(JSONText); snowflake_warehouse = Column(String(255))
    snowflake_database_schema_object = Column(String(512)); sql_executed = Column(Text)
    snowflake_execution_timestamp = Column(DateTime); snowflake_rows_produced = Column(String(50))
    snowflake_execution_duration_ms = Column(String(50)); snowflake_error_message = Column(Text)
    iics_run_ids = Column(JSONText); iics_org = Column(String(255)); iics_asset_type = Column(String(100))
    iics_asset_name = Column(String(512)); iics_asset_id = Column(String(255))
    iics_run_start = Column(DateTime); iics_run_end = Column(DateTime); iics_run_status = Column(String(50))
    executed_by = Column(String(255)); executed_at = Column(DateTime); reviewer_comment = Column(Text)
    is_template = Column(Boolean, default=False); template_name = Column(String(255))
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_plan = relationship("TestPlan", back_populates="test_cases")
    evidence_artefacts = relationship("EvidenceArtefact",
        primaryjoin="TestCase.id == foreign(EvidenceArtefact.test_case_id)", back_populates="test_case")


class EvidenceArtefact(Base):
    __tablename__ = "evidence_artefacts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_case_id = Column(String(36), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=True)
    test_plan_id = Column(String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=True)
    artefact_type = Column(String(50), nullable=False)
    description = Column(Text); original_filename = Column(String(512))
    s3_object_key = Column(String(1024), nullable=False); s3_bucket = Column(String(255), nullable=False)
    file_size_bytes = Column(BigInteger); content_type = Column(String(255))
    metadata_json = Column(JSONText); is_legal_hold = Column(Boolean, default=False)
    retention_override_date = Column(DateTime)
    uploaded_by = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    test_case = relationship("TestCase",
        primaryjoin="EvidenceArtefact.test_case_id == TestCase.id",
        back_populates="evidence_artefacts", foreign_keys="[EvidenceArtefact.test_case_id]")
    test_plan = relationship("TestPlan",
        primaryjoin="EvidenceArtefact.test_plan_id == TestPlan.id",
        back_populates="evidence_artefacts", foreign_keys="[EvidenceArtefact.test_plan_id]")


class Signoff(Base):
    __tablename__ = "signoffs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_plan_id = Column(String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), nullable=False); decision = Column(String(20), nullable=False, default="PENDING")
    comments = Column(Text); rejection_reason = Column(Text)
    signed_by = Column(String(255)); signed_by_name = Column(String(255)); signed_at = Column(DateTime)
    requested_at = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(String(255), nullable=False)
    test_plan = relationship("TestPlan", back_populates="signoffs")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String(255), nullable=False, index=True)
    user_role = Column(String(100))
    action_type = Column(String(30), nullable=False, index=True)
    entity_type = Column(String(100)); entity_id = Column(String(255), index=True)
    old_value = Column(JSONText); new_value = Column(JSONText)
    description = Column(Text); ip_address = Column(String(50)); user_agent = Column(String(512))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token = Column(String(512), nullable=False, unique=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255)); display_name = Column(String(255))
    role = Column(String(100), nullable=False)
    azure_groups = Column(JSONText); saml_name_id = Column(String(512)); saml_session_index = Column(String(512))
    is_active = Column(Boolean, default=True); ip_address = Column(String(50)); user_agent = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


def create_demo_db(db_path="./utap_demo.db"):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)
