from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.test_case import TestCaseStatus, TestCaseCategory, TestCaseComponent


class TestCaseBase(BaseModel):
    testcase_id: str = Field(..., max_length=50)
    category: TestCaseCategory = TestCaseCategory.FUNCTIONAL
    component: TestCaseComponent = TestCaseComponent.SNOWFLAKE
    objective: str
    preconditions: Optional[str] = None
    test_steps: str
    expected_result: str

    # Snowflake fields
    snowflake_warehouse: Optional[str] = None
    snowflake_database_schema_object: Optional[str] = None
    sql_executed: Optional[str] = None

    # IICS fields
    iics_org: Optional[str] = None
    iics_asset_type: Optional[str] = None
    iics_asset_name: Optional[str] = None
    iics_asset_id: Optional[str] = None


class TestCaseCreate(TestCaseBase):
    test_plan_id: UUID


class TestCaseUpdate(BaseModel):
    category: Optional[TestCaseCategory] = None
    component: Optional[TestCaseComponent] = None
    objective: Optional[str] = None
    preconditions: Optional[str] = None
    test_steps: Optional[str] = None
    expected_result: Optional[str] = None
    actual_result: Optional[str] = None
    status: Optional[TestCaseStatus] = None
    defect_reference: Optional[str] = None
    waiver_reason: Optional[str] = None

    # Snowflake execution fields
    snowflake_query_ids: Optional[List[str]] = None
    snowflake_warehouse: Optional[str] = None
    snowflake_database_schema_object: Optional[str] = None
    sql_executed: Optional[str] = None
    snowflake_execution_timestamp: Optional[datetime] = None
    snowflake_rows_produced: Optional[str] = None
    snowflake_execution_duration_ms: Optional[str] = None
    snowflake_error_message: Optional[str] = None

    # IICS execution fields
    iics_run_ids: Optional[List[str]] = None
    iics_org: Optional[str] = None
    iics_asset_type: Optional[str] = None
    iics_asset_name: Optional[str] = None
    iics_asset_id: Optional[str] = None
    iics_run_start: Optional[datetime] = None
    iics_run_end: Optional[datetime] = None
    iics_run_status: Optional[str] = None

    reviewer_comment: Optional[str] = None


class TestCaseResponse(TestCaseBase):
    id: UUID
    test_plan_id: UUID
    actual_result: Optional[str] = None
    status: TestCaseStatus
    defect_reference: Optional[str] = None
    waiver_reason: Optional[str] = None
    waiver_approved_by: Optional[str] = None

    snowflake_query_ids: Optional[List[str]] = None
    snowflake_execution_timestamp: Optional[datetime] = None
    snowflake_rows_produced: Optional[str] = None
    snowflake_execution_duration_ms: Optional[str] = None
    snowflake_error_message: Optional[str] = None

    iics_run_ids: Optional[List[str]] = None
    iics_run_start: Optional[datetime] = None
    iics_run_end: Optional[datetime] = None
    iics_run_status: Optional[str] = None

    executed_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    reviewer_comment: Optional[str] = None
    is_template: bool
    template_name: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    evidence_count: Optional[int] = None

    class Config:
        from_attributes = True


class TestCaseBulkImportRow(BaseModel):
    testcase_id: str
    category: str
    component: str
    objective: str
    preconditions: Optional[str] = None
    test_steps: str
    expected_result: str
    snowflake_warehouse: Optional[str] = None
    snowflake_database_schema_object: Optional[str] = None
    iics_org: Optional[str] = None
    iics_asset_name: Optional[str] = None


class TestCaseBulkImport(BaseModel):
    test_plan_id: UUID
    test_cases: List[TestCaseBulkImportRow]
