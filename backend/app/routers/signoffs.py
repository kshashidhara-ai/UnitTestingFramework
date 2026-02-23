from uuid import UUID
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.signoff import Signoff, SignoffLevel, SignoffDecision
from app.models.test_plan import TestPlan, TestPlanStatus
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.schemas.signoff import SignoffCreate, SignoffDecisionRequest, SignoffResponse

router = APIRouter(prefix="/signoffs", tags=["Sign-offs"])

# Minimum role required per signoff level
LEVEL_ROLE_MAP = {
    SignoffLevel.PEER: "reviewer",
    SignoffLevel.QA: "reviewer",
    SignoffLevel.RELEASE: "release_manager",
}


@router.get("", response_model=List[SignoffResponse])
async def list_signoffs(
    test_plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return db.query(Signoff).filter(Signoff.test_plan_id == test_plan_id).all()


@router.post("", response_model=SignoffResponse, status_code=status.HTTP_201_CREATED)
async def request_signoff(
    data: SignoffCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    """Request a sign-off for a test plan."""
    plan = db.query(TestPlan).filter(TestPlan.id == data.test_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    if plan.status not in (TestPlanStatus.IN_REVIEW, TestPlanStatus.APPROVED):
        raise HTTPException(status_code=400, detail="Plan must be IN_REVIEW to request sign-off")

    # Check no pending signoff at same level exists
    existing = db.query(Signoff).filter(
        Signoff.test_plan_id == data.test_plan_id,
        Signoff.level == data.level,
        Signoff.decision == SignoffDecision.PENDING,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Pending {data.level.value} sign-off already exists")

    signoff = Signoff(
        **data.model_dump(),
        requested_by=current_user["email"],
    )
    db.add(signoff)
    db.commit()
    db.refresh(signoff)
    return signoff


@router.post("/{signoff_id}/decide", response_model=SignoffResponse)
async def decide_signoff(
    signoff_id: UUID,
    data: SignoffDecisionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    """Approve or reject a sign-off."""
    signoff = db.query(Signoff).filter(Signoff.id == signoff_id).first()
    if not signoff:
        raise HTTPException(status_code=404, detail="Sign-off not found")
    if signoff.decision != SignoffDecision.PENDING:
        raise HTTPException(status_code=400, detail="Sign-off already decided")

    # Enforce role for the level
    from app.services.saml_service import ROLE_HIERARCHY
    required_role = LEVEL_ROLE_MAP.get(signoff.level, "reviewer")
    user_role = current_user.get("role", "developer")
    if ROLE_HIERARCHY.index(user_role) < ROLE_HIERARCHY.index(required_role):
        raise HTTPException(
            status_code=403,
            detail=f"{signoff.level.value} sign-off requires role: {required_role}"
        )

    if data.decision == SignoffDecision.REJECTED and not data.rejection_reason:
        raise HTTPException(status_code=422, detail="Rejection reason is required when rejecting")

    signoff.decision = data.decision
    signoff.comments = data.comments
    signoff.rejection_reason = data.rejection_reason
    signoff.signed_by = current_user["email"]
    signoff.signed_by_name = current_user.get("display_name")
    signoff.signed_at = datetime.utcnow()
    db.commit()

    # If this is a RELEASE level approval — lock the plan
    plan = db.query(TestPlan).filter(TestPlan.id == signoff.test_plan_id).first()
    if signoff.level == SignoffLevel.RELEASE and data.decision == SignoffDecision.APPROVED:
        plan.status = TestPlanStatus.LOCKED
        plan.is_locked = True
        db.commit()
        log_action(
            db=db, user_email=current_user["email"],
            action_type=ActionType.LOCK, entity_type="TestPlan",
            entity_id=str(plan.id),
            description="Test plan locked after Release Manager approval",
            user_role=current_user.get("role"),
        )

    if data.decision == SignoffDecision.REJECTED and plan:
        plan.status = TestPlanStatus.REJECTED
        db.commit()

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.SIGNOFF, entity_type="Signoff",
        entity_id=str(signoff.id),
        new_value={
            "level": signoff.level.value,
            "decision": data.decision.value,
            "plan_id": str(signoff.test_plan_id),
        },
        description=f"{signoff.level.value} sign-off {data.decision.value}",
        user_role=current_user.get("role"),
    )
    db.refresh(signoff)
    return signoff
