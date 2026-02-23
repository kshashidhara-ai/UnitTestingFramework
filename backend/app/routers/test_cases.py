from uuid import UUID
from datetime import datetime
from typing import List, Optional
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.test_case import TestCase, TestCaseStatus
from app.models.test_plan import TestPlan
from app.models.evidence import EvidenceArtefact
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate, TestCaseResponse

router = APIRouter(prefix="/test-cases", tags=["Test Cases"])


def _enrich_case(tc: TestCase, db: Session) -> dict:
    d = {c.name: getattr(tc, c.name) for c in tc.__table__.columns}
    d["evidence_count"] = db.query(EvidenceArtefact).filter(
        EvidenceArtefact.test_case_id == tc.id
    ).count()
    return d


@router.get("", response_model=List[TestCaseResponse])
async def list_test_cases(
    test_plan_id: Optional[UUID] = None,
    status_filter: Optional[TestCaseStatus] = Query(None, alias="status"),
    component: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(TestCase)
    if test_plan_id:
        query = query.filter(TestCase.test_plan_id == test_plan_id)
    if status_filter:
        query = query.filter(TestCase.status == status_filter)
    if component:
        query = query.filter(TestCase.component == component)
    if search:
        query = query.filter(TestCase.sql_executed.ilike(f"%{search}%") |
                             TestCase.objective.ilike(f"%{search}%") |
                             TestCase.testcase_id.ilike(f"%{search}%"))

    total = query.count()
    cases = query.order_by(TestCase.testcase_id).offset((page - 1) * page_size).limit(page_size).all()
    return [TestCaseResponse(**_enrich_case(tc, db)) for tc in cases]


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    plan = db.query(TestPlan).filter(TestPlan.id == data.test_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    if plan.is_locked:
        raise HTTPException(status_code=423, detail="Test plan is locked")

    tc = TestCase(**data.model_dump(), created_by=current_user["email"])
    db.add(tc)
    db.commit()
    db.refresh(tc)
    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.CREATE, entity_type="TestCase",
        entity_id=str(tc.id), new_value={"testcase_id": tc.testcase_id},
        user_role=current_user.get("role"),
    )
    return TestCaseResponse(**_enrich_case(tc, db))


@router.get("/{case_id}", response_model=TestCaseResponse)
async def get_test_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    return TestCaseResponse(**_enrich_case(tc, db))


@router.patch("/{case_id}", response_model=TestCaseResponse)
async def update_test_case(
    case_id: UUID,
    data: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    plan = db.query(TestPlan).filter(TestPlan.id == tc.test_plan_id).first()
    if plan and plan.is_locked:
        raise HTTPException(status_code=423, detail="Test plan is locked")

    # Enforce: PASS requires evidence or waiver
    if data.status == TestCaseStatus.PASS:
        evidence_count = db.query(EvidenceArtefact).filter(
            EvidenceArtefact.test_case_id == case_id
        ).count()
        if evidence_count == 0 and not tc.waiver_reason:
            raise HTTPException(
                status_code=422,
                detail="Cannot mark as PASS: no evidence artefact uploaded and no waiver submitted."
            )

    # Enforce: FAIL requires defect reference or reviewer comment
    if data.status == TestCaseStatus.FAIL:
        defect = data.defect_reference or tc.defect_reference
        comment = data.reviewer_comment or tc.reviewer_comment
        if not defect and not comment:
            raise HTTPException(
                status_code=422,
                detail="FAIL status requires a defect reference or reviewer comment."
            )

    old_status = tc.status
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tc, field, value)

    # Auto-capture execution timestamp & executor
    if data.status in (TestCaseStatus.PASS, TestCaseStatus.FAIL, TestCaseStatus.BLOCKED):
        if not tc.executed_at:
            tc.executed_at = datetime.utcnow()
        if not tc.executed_by:
            tc.executed_by = current_user["email"]

    db.commit()
    db.refresh(tc)

    if data.status and data.status != old_status:
        log_action(
            db=db, user_email=current_user["email"],
            action_type=ActionType.STATUS_CHANGE, entity_type="TestCase",
            entity_id=str(tc.id),
            old_value={"status": old_status.value},
            new_value={"status": tc.status.value},
            user_role=current_user.get("role"),
        )
    return TestCaseResponse(**_enrich_case(tc, db))


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    plan = db.query(TestPlan).filter(TestPlan.id == tc.test_plan_id).first()
    if plan and plan.is_locked:
        raise HTTPException(status_code=423, detail="Test plan is locked")
    db.delete(tc)
    db.commit()


@router.post("/bulk-import", status_code=status.HTTP_201_CREATED)
async def bulk_import_test_cases(
    test_plan_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    """Bulk import test cases from CSV file."""
    plan = db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    if plan.is_locked:
        raise HTTPException(status_code=423, detail="Test plan is locked")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    created = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        try:
            tc = TestCase(
                test_plan_id=test_plan_id,
                testcase_id=row.get("testcase_id", f"TC-{i:03d}"),
                category=row.get("category", "FUNCTIONAL"),
                component=row.get("component", "SNOWFLAKE"),
                objective=row.get("objective", ""),
                preconditions=row.get("preconditions"),
                test_steps=row.get("test_steps", ""),
                expected_result=row.get("expected_result", ""),
                snowflake_warehouse=row.get("snowflake_warehouse"),
                snowflake_database_schema_object=row.get("snowflake_database_schema_object"),
                iics_org=row.get("iics_org"),
                iics_asset_name=row.get("iics_asset_name"),
                created_by=current_user["email"],
            )
            db.add(tc)
            created += 1
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.BULK_IMPORT, entity_type="TestCase",
        entity_id=str(test_plan_id),
        new_value={"created": created, "errors": len(errors)},
        user_role=current_user.get("role"),
    )
    return {"created": created, "errors": errors}
