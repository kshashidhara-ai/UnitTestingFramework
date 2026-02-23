from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import get_db
from app.models.test_plan import TestPlan, TestPlanStatus
from app.models.test_case import TestCase, TestCaseStatus
from app.models.signoff import Signoff, SignoffDecision
from app.models.project import Project
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return dashboard summary metrics."""
    user_email = current_user["email"]

    # My test plans
    my_plans = db.query(TestPlan).filter(TestPlan.created_by == user_email).count()

    # Pending reviews (plans in IN_REVIEW status)
    pending_reviews = db.query(TestPlan).filter(
        TestPlan.status == TestPlanStatus.IN_REVIEW
    ).count()

    # Total test cases by status
    tc_stats = db.query(
        TestCase.status, func.count(TestCase.id)
    ).group_by(TestCase.status).all()
    tc_by_status = {str(s.value): c for s, c in tc_stats}

    total_tc = sum(tc_by_status.values())
    passed = tc_by_status.get("PASS", 0)
    pass_rate = round((passed / total_tc * 100), 1) if total_tc > 0 else 0

    # Plans by status
    plan_stats = db.query(
        TestPlan.status, func.count(TestPlan.id)
    ).group_by(TestPlan.status).all()
    plans_by_status = {str(s.value): c for s, c in plan_stats}

    # Active projects
    active_projects = db.query(Project).filter(Project.is_active == True).count()

    # Pending sign-offs for current user's reviewer role
    pending_signoffs = db.query(Signoff).filter(
        Signoff.decision == SignoffDecision.PENDING
    ).count()

    return {
        "my_test_plans": my_plans,
        "pending_reviews": pending_reviews,
        "pending_signoffs": pending_signoffs,
        "active_projects": active_projects,
        "test_case_stats": {
            "total": total_tc,
            "pass": passed,
            "fail": tc_by_status.get("FAIL", 0),
            "not_run": tc_by_status.get("NOT_RUN", 0),
            "blocked": tc_by_status.get("BLOCKED", 0),
            "waived": tc_by_status.get("WAIVED", 0),
            "pass_rate": pass_rate,
        },
        "test_plan_stats": plans_by_status,
    }


@router.get("/my-plans")
async def get_my_plans(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get test plans created by current user."""
    plans = db.query(TestPlan).filter(
        TestPlan.created_by == current_user["email"]
    ).order_by(TestPlan.updated_at.desc()).limit(10).all()

    result = []
    for plan in plans:
        cases = db.query(TestCase).filter(TestCase.test_plan_id == plan.id).all()
        result.append({
            "id": str(plan.id),
            "plan_name": plan.plan_name,
            "status": plan.status.value,
            "evidence_completeness_score": plan.evidence_completeness_score,
            "is_locked": plan.is_locked,
            "created_at": plan.created_at.isoformat(),
            "test_case_count": len(cases),
            "pass_count": sum(1 for c in cases if c.status == TestCaseStatus.PASS),
            "fail_count": sum(1 for c in cases if c.status == TestCaseStatus.FAIL),
        })
    return result
