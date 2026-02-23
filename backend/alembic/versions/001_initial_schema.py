"""Initial UTAP schema

Revision ID: 001
Revises:
Create Date: 2026-02-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── projects ─────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("domain", sa.String(100)),
        sa.Column("description", sa.Text),
        sa.Column("owner_team", sa.String(255)),
        sa.Column("country", sa.String(100)),
        sa.Column("dataset", sa.String(255)),
        sa.Column("vendor", sa.String(255)),
        sa.Column("frequency", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    # ── releases ─────────────────────────────────────────────────────────────
    op.create_table(
        "releases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("environment_scope", sa.Enum("SIT", "UAT", "PROD", name="environmentscope"), nullable=False),
        sa.Column("status", sa.Enum("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="releasestatus"), nullable=False),
        sa.Column("planned_deploy_date", sa.Date),
        sa.Column("actual_deploy_date", sa.Date),
        sa.Column("release_notes", sa.Text),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── development_activities ────────────────────────────────────────────────
    op.create_table(
        "development_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("releases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("activity_type", sa.Enum("SNOWFLAKE", "IICS", "MIXED", "OTHER", name="activitytype"), nullable=False),
        sa.Column("jira_id", sa.String(100)),
        sa.Column("git_repo", sa.String(512)),
        sa.Column("pr_link", sa.String(512)),
        sa.Column("commit_hash", sa.String(100)),
        sa.Column("snowflake_objects", postgresql.JSONB),
        sa.Column("iics_assets", postgresql.JSONB),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_dev_activities_jira_id", "development_activities", ["jira_id"])

    # ── test_plans ────────────────────────────────────────────────────────────
    op.create_table(
        "test_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dev_activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("development_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_name", sa.String(512), nullable=False),
        sa.Column("scope", sa.Text),
        sa.Column("test_strategy", sa.Text),
        sa.Column("entry_criteria", sa.Text),
        sa.Column("exit_criteria", sa.Text),
        sa.Column("status", sa.Enum("DRAFT", "IN_REVIEW", "APPROVED", "LOCKED", "REJECTED", name="testplanstatus"), nullable=False, server_default="DRAFT"),
        sa.Column("evidence_completeness_score", sa.Float, server_default="0.0"),
        sa.Column("is_locked", sa.Boolean, server_default="false"),
        sa.Column("lock_override_reason", sa.Text),
        sa.Column("submitted_for_review_at", sa.DateTime),
        sa.Column("last_autosave_at", sa.DateTime),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── test_cases ────────────────────────────────────────────────────────────
    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("testcase_id", sa.String(50), nullable=False),
        sa.Column("category", sa.Enum("FUNCTIONAL","REGRESSION","PERFORMANCE","DATA_QUALITY","INTEGRATION","RECONCILIATION","IDEMPOTENCY","NEGATIVE", name="testcasecategory"), nullable=False),
        sa.Column("component", sa.Enum("SNOWFLAKE","IICS","BOTH","OTHER", name="testcasecomponent"), nullable=False),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("preconditions", sa.Text),
        sa.Column("test_steps", sa.Text, nullable=False),
        sa.Column("expected_result", sa.Text, nullable=False),
        sa.Column("actual_result", sa.Text),
        sa.Column("status", sa.Enum("NOT_RUN","IN_PROGRESS","PASS","FAIL","BLOCKED","WAIVED", name="testcasestatus"), nullable=False, server_default="NOT_RUN"),
        sa.Column("defect_reference", sa.String(255)),
        sa.Column("waiver_reason", sa.Text),
        sa.Column("waiver_approved_by", sa.String(255)),
        # Snowflake fields
        sa.Column("snowflake_query_ids", postgresql.ARRAY(sa.String)),
        sa.Column("snowflake_warehouse", sa.String(255)),
        sa.Column("snowflake_database_schema_object", sa.String(512)),
        sa.Column("sql_executed", sa.Text),
        sa.Column("snowflake_execution_timestamp", sa.DateTime),
        sa.Column("snowflake_rows_produced", sa.String(50)),
        sa.Column("snowflake_execution_duration_ms", sa.String(50)),
        sa.Column("snowflake_error_message", sa.Text),
        # IICS fields
        sa.Column("iics_run_ids", postgresql.ARRAY(sa.String)),
        sa.Column("iics_org", sa.String(255)),
        sa.Column("iics_asset_type", sa.String(100)),
        sa.Column("iics_asset_name", sa.String(512)),
        sa.Column("iics_asset_id", sa.String(255)),
        sa.Column("iics_run_start", sa.DateTime),
        sa.Column("iics_run_end", sa.DateTime),
        sa.Column("iics_run_status", sa.String(50)),
        sa.Column("executed_by", sa.String(255)),
        sa.Column("executed_at", sa.DateTime),
        sa.Column("reviewer_comment", sa.Text),
        sa.Column("is_template", sa.Boolean, server_default="false"),
        sa.Column("template_name", sa.String(255)),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    # Full-text index on SQL text
    op.execute("CREATE INDEX ix_tc_sql_fts ON test_cases USING gin(to_tsvector('english', coalesce(sql_executed,'')));")
    op.execute("CREATE INDEX ix_tc_testcase_id ON test_cases (testcase_id);")

    # ── evidence_artefacts ────────────────────────────────────────────────────
    op.create_table(
        "evidence_artefacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE")),
        sa.Column("test_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_plans.id", ondelete="CASCADE")),
        sa.Column("artefact_type", sa.Enum(
            "SNOWFLAKE_QUERY_RESULT","SNOWFLAKE_SCREENSHOT","SNOWFLAKE_EXPLAIN_PLAN","SNOWFLAKE_RECONCILIATION",
            "IICS_ACTIVITY_LOG","IICS_SESSION_LOG","IICS_MONITOR_SCREENSHOT","IICS_REJECTION_FILE",
            "SCREENSHOT","CSV_EXPORT","PDF_DOCUMENT","LOG_FILE","OTHER",
            name="artefacttype"
        ), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("original_filename", sa.String(512)),
        sa.Column("s3_object_key", sa.String(1024), nullable=False),
        sa.Column("s3_bucket", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("content_type", sa.String(255)),
        sa.Column("metadata_json", postgresql.JSONB),
        sa.Column("is_legal_hold", sa.Boolean, server_default="false"),
        sa.Column("retention_override_date", sa.DateTime),
        sa.Column("uploaded_by", sa.String(255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── signoffs ──────────────────────────────────────────────────────────────
    op.create_table(
        "signoffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Enum("PEER","QA","RELEASE", name="signofflevel"), nullable=False),
        sa.Column("decision", sa.Enum("APPROVED","REJECTED","PENDING", name="signoffdecision"), nullable=False, server_default="PENDING"),
        sa.Column("comments", sa.Text),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("signed_by", sa.String(255)),
        sa.Column("signed_by_name", sa.String(255)),
        sa.Column("signed_at", sa.DateTime),
        sa.Column("requested_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("requested_by", sa.String(255), nullable=False),
    )

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("user_role", sa.String(100)),
        sa.Column("action_type", sa.Enum(
            "LOGIN","LOGOUT","ROLE_MAPPED","CREATE","UPDATE","DELETE","STATUS_CHANGE",
            "ARTEFACT_UPLOAD","ARTEFACT_DOWNLOAD","SIGNOFF","LOCK","LOCK_OVERRIDE","EXPORT","BULK_IMPORT",
            name="actiontype"
        ), nullable=False),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", sa.String(255)),
        sa.Column("old_value", postgresql.JSONB),
        sa.Column("new_value", postgresql.JSONB),
        sa.Column("description", sa.Text),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user_email", "audit_log", ["user_email"])
    op.create_index("ix_audit_action_type", "audit_log", ["action_type"])
    op.create_index("ix_audit_entity_id", "audit_log", ["entity_id"])
    op.create_index("ix_audit_timestamp", "audit_log", ["timestamp"])

    # ── user_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_token", sa.String(512), nullable=False, unique=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("user_name", sa.String(255)),
        sa.Column("display_name", sa.String(255)),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("azure_groups", postgresql.JSONB),
        sa.Column("saml_name_id", sa.String(512)),
        sa.Column("saml_session_index", sa.String(512)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sessions_token", "user_sessions", ["session_token"])
    op.create_index("ix_sessions_email", "user_sessions", ["user_email"])


def downgrade() -> None:
    op.drop_table("user_sessions")
    op.drop_table("audit_log")
    op.drop_table("signoffs")
    op.drop_table("evidence_artefacts")
    op.drop_table("test_cases")
    op.drop_table("test_plans")
    op.drop_table("development_activities")
    op.drop_table("releases")
    op.drop_table("projects")

    # Drop enums
    for enum_name in [
        "environmentscope", "releasestatus", "activitytype", "testplanstatus",
        "testcasecategory", "testcasecomponent", "testcasestatus",
        "artefacttype", "signofflevel", "signoffdecision", "actiontype"
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
