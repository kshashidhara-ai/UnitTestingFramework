"""
UTAP Seed Data Script
Loads mandatory templates and sample data into the database.
Run: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.project import Project
from app.models.release import Release, EnvironmentScope, ReleaseStatus
from app.models.dev_activity import DevelopmentActivity, ActivityType
from app.models.test_plan import TestPlan, TestPlanStatus
from app.models.test_case import TestCase, TestCaseCategory, TestCaseComponent, TestCaseStatus

SYSTEM_USER = "system@utap.local"

# ── Template Test Cases ───────────────────────────────────────────────────────
TEMPLATES = [
    {
        "template_name": "File Ingestion Validation",
        "testcase_id": "TPL-001",
        "category": TestCaseCategory.DATA_QUALITY,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Validate that source file has been correctly ingested into the staging table with expected row count and no truncation.",
        "preconditions": "Source file loaded to S3/stage. Staging table exists and is accessible.",
        "test_steps": (
            "1. Query source file row count from file metadata or control table.\n"
            "2. Execute: SELECT COUNT(*) FROM {STG_SCHEMA}.{STG_TABLE};\n"
            "3. Compare source row count with staging row count.\n"
            "4. Check for truncated columns: SELECT MAX(LEN({column})) FROM {STG_TABLE};"
        ),
        "expected_result": "Staging row count = source file row count. No column truncation. All mandatory fields populated.",
    },
    {
        "template_name": "STG Row Count Validation",
        "testcase_id": "TPL-002",
        "category": TestCaseCategory.DATA_QUALITY,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Validate STG layer row count matches the PSA layer after load.",
        "preconditions": "PSA and STG loads completed successfully.",
        "test_steps": (
            "1. SELECT COUNT(*) FROM {PSA_SCHEMA}.{PSA_TABLE} WHERE LOAD_DATE = CURRENT_DATE;\n"
            "2. SELECT COUNT(*) FROM {STG_SCHEMA}.{STG_TABLE} WHERE LOAD_DATE = CURRENT_DATE;\n"
            "3. Compare counts."
        ),
        "expected_result": "STG count equals PSA count for the same load date. Zero discrepancies.",
    },
    {
        "template_name": "PSA Audit Column Validation",
        "testcase_id": "TPL-003",
        "category": TestCaseCategory.DATA_QUALITY,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Validate all PSA audit columns are correctly populated after load.",
        "preconditions": "PSA load completed.",
        "test_steps": (
            "1. SELECT * FROM {PSA_TABLE} WHERE LOAD_TIMESTAMP IS NULL;\n"
            "2. SELECT * FROM {PSA_TABLE} WHERE SOURCE_SYSTEM IS NULL;\n"
            "3. SELECT * FROM {PSA_TABLE} WHERE RECORD_HASH IS NULL;\n"
            "4. Verify no NULL values in mandatory audit columns."
        ),
        "expected_result": "Zero NULL values in LOAD_TIMESTAMP, SOURCE_SYSTEM, RECORD_HASH, LOAD_DATE columns.",
    },
    {
        "template_name": "DWH Fact Reconciliation",
        "testcase_id": "TPL-004",
        "category": TestCaseCategory.RECONCILIATION,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Reconcile fact table metrics against source system totals.",
        "preconditions": "DWH fact load completed. Source system reconciliation extract available.",
        "test_steps": (
            "1. Extract totals from DWH: SELECT SUM(AMOUNT), COUNT(*) FROM {FACT_TABLE} WHERE PERIOD = '{PERIOD}';\n"
            "2. Compare with source system reconciliation extract.\n"
            "3. Calculate variance: (DWH_TOTAL - SOURCE_TOTAL) / SOURCE_TOTAL * 100.\n"
            "4. Document query IDs and results."
        ),
        "expected_result": "Variance <= 0.01% of source total. Zero unmatched keys.",
    },
    {
        "template_name": "MAT Variance Threshold Validation",
        "testcase_id": "TPL-005",
        "category": TestCaseCategory.DATA_QUALITY,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Validate materialized view metrics are within acceptable variance threshold vs prior period.",
        "preconditions": "Current period MAT load completed. Prior period data available.",
        "test_steps": (
            "1. SELECT metric, current_value, prior_value, ABS((current_value - prior_value)/NULLIF(prior_value,0)) AS variance_pct FROM {MAT_RECONCILIATION_VIEW};\n"
            "2. Flag rows where variance_pct > {THRESHOLD}.\n"
            "3. Investigate and document any flagged rows."
        ),
        "expected_result": "All metrics within configurable variance threshold (default 10%). Any exceptions documented with business justification.",
    },
    {
        "template_name": "IICS Taskflow Success Validation",
        "testcase_id": "TPL-006",
        "category": TestCaseCategory.INTEGRATION,
        "component": TestCaseComponent.IICS,
        "objective": "Validate that the IICS Taskflow completes successfully with no task failures.",
        "preconditions": "IICS Taskflow configured and scheduled. Source data available.",
        "test_steps": (
            "1. Trigger/confirm Taskflow execution.\n"
            "2. Monitor IICS Activity Monitor for completion.\n"
            "3. Verify all child tasks show 'Success' status.\n"
            "4. Capture Run ID and screenshot of Activity Monitor.\n"
            "5. Check target table row counts."
        ),
        "expected_result": "Taskflow status = Success. All child tasks = Success. No warning/error entries in activity log. Target row count matches expected.",
        "iics_asset_type": "Taskflow",
    },
    {
        "template_name": "Idempotency Re-run Validation",
        "testcase_id": "TPL-007",
        "category": TestCaseCategory.IDEMPOTENCY,
        "component": TestCaseComponent.BOTH,
        "objective": "Validate that re-running the pipeline/mapping produces identical results without duplicates.",
        "preconditions": "Initial pipeline run completed. Results captured.",
        "test_steps": (
            "1. Capture pre-rerun row counts and key metrics.\n"
            "2. Re-execute the pipeline/IICS mapping for the same period.\n"
            "3. Post-rerun: SELECT COUNT(*) and SUM(metrics) from target table.\n"
            "4. Compare pre and post rerun results.\n"
            "5. Verify no duplicate records: SELECT {KEY_COLUMNS}, COUNT(*) FROM {TABLE} GROUP BY {KEY_COLUMNS} HAVING COUNT(*) > 1;"
        ),
        "expected_result": "Row counts identical before and after re-run. Zero duplicate key records. All metrics match initial run.",
    },
    {
        "template_name": "Performance Benchmark Validation",
        "testcase_id": "TPL-008",
        "category": TestCaseCategory.PERFORMANCE,
        "component": TestCaseComponent.SNOWFLAKE,
        "objective": "Validate that the pipeline/query completes within the agreed SLA execution time.",
        "preconditions": "Performance baseline defined. Warehouse size confirmed.",
        "test_steps": (
            "1. Execute pipeline/query and capture Query ID.\n"
            "2. In Snowflake: SELECT QUERY_ID, TOTAL_ELAPSED_TIME/1000 AS seconds FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE QUERY_ID = '{QUERY_ID}';\n"
            "3. Compare execution time against SLA threshold.\n"
            "4. Review query plan for any full table scans or missing clustering keys."
        ),
        "expected_result": f"Execution time <= SLA threshold. No unexpected full table scans. Warehouse credit consumption within budget.",
    },
]


def seed_templates(db: Session, plan_id: uuid.UUID):
    """Create all 8 mandatory template test cases under a given plan."""
    for tpl in TEMPLATES:
        tc = TestCase(
            test_plan_id=plan_id,
            testcase_id=tpl["testcase_id"],
            category=tpl["category"],
            component=tpl["component"],
            objective=tpl["objective"],
            preconditions=tpl.get("preconditions"),
            test_steps=tpl["test_steps"],
            expected_result=tpl["expected_result"],
            iics_asset_type=tpl.get("iics_asset_type"),
            is_template=True,
            template_name=tpl["template_name"],
            created_by=SYSTEM_USER,
        )
        db.add(tc)
    db.commit()
    print(f"  ✓ {len(TEMPLATES)} template test cases created")


def seed_sample_project(db: Session):
    """Create a sample Sales DWH project with a SIT release and test plan."""
    # Project
    project = db.query(Project).filter(Project.name == "Sales_DWH").first()
    if not project:
        project = Project(
            id=uuid.uuid4(),
            name="Sales_DWH",
            domain="Data Warehouse",
            description="Sales Data Warehouse — EDW for all sales KPIs",
            owner_team="DWH Engineering",
            country="US",
            dataset="Sales",
            vendor="IQVIA",
            frequency="Weekly",
            created_by=SYSTEM_USER,
        )
        db.add(project)
        db.flush()
        print(f"  ✓ Project created: {project.name}")

    # Release
    release = db.query(Release).filter(
        Release.project_id == project.id,
        Release.release_name == "RLS_2026_02"
    ).first()
    if not release:
        release = Release(
            id=uuid.uuid4(),
            project_id=project.id,
            release_name="RLS_2026_02",
            description="February 2026 SIT Release — Sales DWH v2.3",
            environment_scope=EnvironmentScope.SIT,
            status=ReleaseStatus.IN_PROGRESS,
            planned_deploy_date=date(2026, 2, 28),
            created_by=SYSTEM_USER,
        )
        db.add(release)
        db.flush()
        print(f"  ✓ Release created: {release.release_name}")

    # Dev Activity
    activity = db.query(DevelopmentActivity).filter(
        DevelopmentActivity.release_id == release.id
    ).first()
    if not activity:
        activity = DevelopmentActivity(
            id=uuid.uuid4(),
            project_id=project.id,
            release_id=release.id,
            title="Sales Fact Table — New Metrics: Discount Amount and Net Revenue",
            description="Add DISCOUNT_AMOUNT and NET_REVENUE to FACT_SALES. Update all dependent MATs.",
            activity_type=ActivityType.MIXED,
            jira_id="DWH-4521",
            snowflake_objects=[
                {"database": "SALES_DWH_PROD", "schema_name": "FACTS", "object_name": "FACT_SALES", "object_type": "TABLE"},
                {"database": "SALES_DWH_PROD", "schema_name": "MATS", "object_name": "MAT_WEEKLY_REVENUE", "object_type": "DYNAMIC_TABLE"},
            ],
            iics_assets=[
                {"org": "UTAP_PROD_ORG", "asset_type": "Mapping", "asset_name": "M_SALES_FACT_LOAD", "asset_id": "ASSET-001"},
                {"org": "UTAP_PROD_ORG", "asset_type": "Taskflow", "asset_name": "TF_SALES_DWH_WEEKLY", "asset_id": "TF-001"},
            ],
            created_by=SYSTEM_USER,
        )
        db.add(activity)
        db.flush()
        print(f"  ✓ Dev Activity created: {activity.title[:60]}...")

    # Test Plan
    plan = db.query(TestPlan).filter(TestPlan.dev_activity_id == activity.id).first()
    if not plan:
        plan = TestPlan(
            id=uuid.uuid4(),
            dev_activity_id=activity.id,
            plan_name="TP-001: Sales Fact Table New Metrics SIT Test Plan",
            scope="Test the addition of DISCOUNT_AMOUNT and NET_REVENUE to FACT_SALES and all dependent objects.",
            test_strategy=(
                "1. Validate source-to-staging ingestion accuracy.\n"
                "2. Execute IICS mapping and validate activity logs.\n"
                "3. Reconcile FACT_SALES totals against source system.\n"
                "4. Validate MAT refresh with variance checks.\n"
                "5. Idempotency re-run test.\n"
                "6. Performance benchmark within SLA."
            ),
            entry_criteria="IICS mapping deployed to SIT org. Snowflake SIT environment refreshed.",
            exit_criteria="All 8 test cases PASS. Evidence completeness >= 90%. Peer and QA sign-off obtained.",
            status=TestPlanStatus.DRAFT,
            created_by=SYSTEM_USER,
        )
        db.add(plan)
        db.flush()
        print(f"  ✓ Test Plan created: {plan.plan_name}")

        seed_templates(db, plan.id)

    db.commit()
    return project, release, activity, plan


def main():
    print("\n=== UTAP Seed Data ===\n")
    db = SessionLocal()
    try:
        print("Creating sample project and hierarchy...")
        project, release, activity, plan = seed_sample_project(db)
        print(f"\n✓ Seed complete!")
        print(f"  Project:  {project.name} ({project.id})")
        print(f"  Release:  {release.release_name} ({release.id})")
        print(f"  Activity: {activity.jira_id} ({activity.id})")
        print(f"  Plan:     {plan.plan_name[:60]}... ({plan.id})")
    except Exception as e:
        print(f"\n✗ Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
