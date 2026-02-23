from uuid import UUID
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.test_plan import TestPlan, TestPlanStatus
from app.models.test_case import TestCase, TestCaseStatus
from app.models.evidence import EvidenceArtefact
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.test_plan import (
    TestPlanCreate, TestPlanUpdate, TestPlanResponse,
    TestPlanSubmitReview, TestPlanLockOverride
)
from app.config import settings

router = APIRouter(prefix="/test-plans", tags=["Test Plans"])


def _calculate_completeness(db: Session, plan_id: UUID) -> float:
    """Calculate evidence completeness score for a test plan."""
    total_cases = db.query(TestCase).filter(TestCase.test_plan_id == plan_id).count()
    if total_cases == 0:
        return 0.0

    # Cases that have at least one evidence artefact or are waived
    cases_with_evidence = (
        db.query(TestCase)
        .filter(TestCase.test_plan_id == plan_id)
        .filter(
            (TestCase.status == TestCaseStatus.WAIVED) |
            (TestCase.id.in_(
                db.query(EvidenceArtefact.test_case_id)
                .filter(EvidenceArtefact.test_case_id.isnot(None))
                .distinct()
            ))
        )
        .count()
    )
    return round((cases_with_evidence / total_cases) * 100, 2)


def _enrich_plan(plan: TestPlan, db: Session) -> dict:
    plan_dict = {c.name: getattr(plan, c.name) for c in plan.__table__.columns}
    cases = db.query(TestCase).filter(TestCase.test_plan_id == plan.id).all()
    plan_dict["test_case_count"] = len(cases)
    plan_dict["pass_count"] = sum(1 for c in cases if c.status == TestCaseStatus.PASS)
    plan_dict["fail_count"] = sum(1 for c in cases if c.status == TestCaseStatus.FAIL)
    plan_dict["not_run_count"] = sum(1 for c in cases if c.status == TestCaseStatus.NOT_RUN)
    return plan_dict


@router.get("", response_model=List[TestPlanResponse])
async def list_test_plans(
    dev_activity_id: Optional[UUID] = None,
    status_filter: Optional[TestPlanStatus] = Query(None, alias="status"),
    created_by: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(TestPlan)
    if dev_activity_id:
        query = query.filter(TestPlan.dev_activity_id == dev_activity_id)
    if status_filter:
        query = query.filter(TestPlan.status == status_filter)
    if created_by:
        query = query.filter(TestPlan.created_by == created_by)

    total = query.count()
    plans = query.order_by(TestPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    results = []
    for plan in plans:
        d = _enrich_plan(plan, db)
        results.append(TestPlanResponse(**d))
    return results


@router.post("", response_model=TestPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_test_plan(
    data: TestPlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    plan = TestPlan(**data.model_dump(), created_by=current_user["email"])
    db.add(plan)
    db.commit()
    db.refresh(plan)
    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.CREATE, entity_type="TestPlan",
        entity_id=str(plan.id), new_value={"name": plan.plan_name},
        user_role=current_user.get("role"),
    )
    d = _enrich_plan(plan, db)
    return TestPlanResponse(**d)


@router.get("/{plan_id}", response_model=TestPlanResponse)
async def get_test_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    # Refresh completeness score
    plan.evidence_completeness_score = _calculate_completeness(db, plan_id)
    db.commit()
    return TestPlanResponse(**_enrich_plan(plan, db))


@router.patch("/{plan_id}", response_model=TestPlanResponse)
async def update_test_plan(
    plan_id: UUID,
    data: TestPlanUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    if plan.is_locked:
        raise HTTPException(status_code=423, detail="Test plan is locked. Contact Admin for override.")

    old_status = plan.status
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    plan.last_autosave_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)

    if data.status and data.status != old_status:
        log_action(
            db=db, user_email=current_user["email"],
            action_type=ActionType.STATUS_CHANGE, entity_type="TestPlan",
            entity_id=str(plan.id),
            old_value={"status": old_status.value},
            new_value={"status": plan.status.value},
            user_role=current_user.get("role"),
        )
    return TestPlanResponse(**_enrich_plan(plan, db))


@router.post("/{plan_id}/submit-review", response_model=TestPlanResponse)
async def submit_for_review(
    plan_id: UUID,
    data: TestPlanSubmitReview,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    """Submit test plan for review. Enforces all completion rules."""
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    if plan.is_locked:
        raise HTTPException(status_code=423, detail="Plan is locked")
    if plan.status not in (TestPlanStatus.DRAFT, TestPlanStatus.REJECTED):
        raise HTTPException(status_code=400, detail=f"Cannot submit from status: {plan.status.value}")

    cases = db.query(TestCase).filter(TestCase.test_plan_id == plan_id).all()

    # Rule: No NOT_RUN cases allowed
    not_run = [c for c in cases if c.status == TestCaseStatus.NOT_RUN]
    if not_run:
        raise HTTPException(
            status_code=422,
            detail=f"{len(not_run)} test case(s) are still NOT_RUN. All must be executed before submission."
        )

    # Rule: FAIL cases must have defect reference
    fail_no_defect = [c for c in cases if c.status == TestCaseStatus.FAIL and not c.defect_reference]
    if fail_no_defect:
        raise HTTPException(
            status_code=422,
            detail=f"{len(fail_no_defect)} FAIL case(s) missing defect reference."
        )

    # Rule: Evidence completeness threshold
    completeness = _calculate_completeness(db, plan_id)
    plan.evidence_completeness_score = completeness
    threshold = settings.EVIDENCE_COMPLETENESS_THRESHOLD
    if completeness < threshold:
        raise HTTPException(
            status_code=422,
            detail=f"Evidence completeness {completeness:.1f}% is below required {threshold}%"
        )

    plan.status = TestPlanStatus.IN_REVIEW
    plan.submitted_for_review_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.STATUS_CHANGE, entity_type="TestPlan",
        entity_id=str(plan.id),
        old_value={"status": "DRAFT"},
        new_value={"status": "IN_REVIEW"},
        description="Submitted for review",
        user_role=current_user.get("role"),
    )
    return TestPlanResponse(**_enrich_plan(plan, db))


@router.post("/{plan_id}/lock-override", response_model=TestPlanResponse)
async def admin_lock_override(
    plan_id: UUID,
    data: TestPlanLockOverride,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Admin override to unlock a locked test plan."""
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")

    plan.is_locked = False
    plan.status = TestPlanStatus.APPROVED
    plan.lock_override_reason = data.reason
    db.commit()
    db.refresh(plan)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.LOCK_OVERRIDE, entity_type="TestPlan",
        entity_id=str(plan.id),
        new_value={"reason": data.reason},
        description=f"Admin lock override: {data.reason}",
        user_role=current_user.get("role"),
    )
    return TestPlanResponse(**_enrich_plan(plan, db))
