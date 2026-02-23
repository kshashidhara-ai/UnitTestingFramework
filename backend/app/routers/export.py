from uuid import UUID
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models.test_plan import TestPlan
from app.models.test_case import TestCase
from app.models.signoff import Signoff
from app.models.evidence import EvidenceArtefact
from app.models.dev_activity import DevelopmentActivity
from app.models.release import Release
from app.models.project import Project
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.services.export_service import (
    generate_pdf_summary, generate_test_cases_csv,
    generate_signoff_log_csv, create_evidence_zip
)

router = APIRouter(prefix="/export", tags=["Export"])


def _build_context(db: Session, plan_id: UUID):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")

    activity = db.query(DevelopmentActivity).filter(
        DevelopmentActivity.id == plan.dev_activity_id
    ).first()
    release = db.query(Release).filter(Release.id == activity.release_id).first() if activity else None
    project = db.query(Project).filter(Project.id == activity.project_id).first() if activity else None
    cases = db.query(TestCase).filter(TestCase.test_plan_id == plan_id).all()
    signoffs = db.query(Signoff).filter(Signoff.test_plan_id == plan_id).all()

    return plan, activity, release, project, cases, signoffs


@router.get("/test-plan/{plan_id}/pdf")
async def export_pdf(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Export PDF summary for a test plan."""
    plan, activity, release, project, cases, signoffs = _build_context(db, plan_id)

    tc_list = [{c.name: getattr(tc, c.name) for c in tc.__table__.columns} for tc in cases]
    so_list = [{c.name: getattr(so, c.name) for c in so.__table__.columns} for so in signoffs]

    pdf_bytes = generate_pdf_summary(
        project_name=project.name if project else "Unknown",
        release_name=release.release_name if release else "Unknown",
        environment=release.environment_scope.value if release else "Unknown",
        test_plan_name=plan.plan_name,
        plan_id=str(plan_id),
        scope=plan.scope,
        test_strategy=plan.test_strategy,
        test_cases=tc_list,
        signoffs=so_list,
        evidence_completeness=plan.evidence_completeness_score,
        created_by=plan.created_by,
        created_at=plan.created_at,
    )

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.EXPORT, entity_type="TestPlan",
        entity_id=str(plan_id), description="PDF export",
        user_role=current_user.get("role"),
    )

    filename = f"UTAP_{str(plan_id)[:8]}_evidence_pack.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/test-plan/{plan_id}/csv")
async def export_csv(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Export test cases CSV for a test plan."""
    plan, _, _, _, cases, _ = _build_context(db, plan_id)
    tc_list = [{c.name: getattr(tc, c.name) for c in tc.__table__.columns} for tc in cases]
    csv_bytes = generate_test_cases_csv(tc_list)

    filename = f"UTAP_{str(plan_id)[:8]}_test_cases.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/test-plan/{plan_id}/zip")
async def export_zip(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("reviewer")),
):
    """Export full evidence pack as ZIP (PDF + CSV + signoff log + metadata)."""
    plan, activity, release, project, cases, signoffs = _build_context(db, plan_id)

    tc_list = [{c.name: getattr(tc, c.name) for c in tc.__table__.columns} for tc in cases]
    so_list = [{c.name: getattr(so, c.name) for c in so.__table__.columns} for so in signoffs]

    pdf_bytes = generate_pdf_summary(
        project_name=project.name if project else "Unknown",
        release_name=release.release_name if release else "Unknown",
        environment=release.environment_scope.value if release else "Unknown",
        test_plan_name=plan.plan_name,
        plan_id=str(plan_id),
        scope=plan.scope,
        test_strategy=plan.test_strategy,
        test_cases=tc_list,
        signoffs=so_list,
        evidence_completeness=plan.evidence_completeness_score,
        created_by=plan.created_by,
        created_at=plan.created_at,
    )
    csv_bytes = generate_test_cases_csv(tc_list)
    signoff_csv = generate_signoff_log_csv(so_list)

    metadata = {
        "export_timestamp": datetime.utcnow().isoformat(),
        "exported_by": current_user["email"],
        "project": project.name if project else None,
        "release": release.release_name if release else None,
        "plan_id": str(plan_id),
        "plan_name": plan.plan_name,
        "total_test_cases": len(cases),
        "evidence_completeness": plan.evidence_completeness_score,
    }

    zip_bytes = create_evidence_zip(pdf_bytes, csv_bytes, signoff_csv, metadata)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.EXPORT, entity_type="TestPlan",
        entity_id=str(plan_id), description="Full ZIP evidence pack export",
        user_role=current_user.get("role"),
    )

    filename = f"UTAP_{str(plan_id)[:8]}_evidence_pack.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
