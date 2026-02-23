from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import EvidenceArtefact, ArtefactType
from app.models.test_plan import TestPlan
from app.models.test_case import TestCase
from app.models.audit_log import ActionType
from app.models.project import Project
from app.models.release import Release
from app.models.dev_activity import DevelopmentActivity
from app.middleware.auth import get_current_user, require_role
from app.services.audit_service import log_action
from app.services import s3_service
from app.schemas.evidence import (
    EvidenceCreate, EvidenceResponse,
    PresignedUploadRequest, PresignedUploadResponse, PresignedDownloadResponse
)
from app.config import settings

router = APIRouter(prefix="/evidence", tags=["Evidence & Artefacts"])


def _get_plan_context(db: Session, plan_id: UUID):
    """Fetch project and release names for building the S3 key."""
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        return "unknown_project", "unknown_release", str(plan_id)
    activity = db.query(DevelopmentActivity).filter(
        DevelopmentActivity.id == plan.dev_activity_id
    ).first()
    if not activity:
        return "unknown_project", "unknown_release", str(plan_id)
    release = db.query(Release).filter(Release.id == activity.release_id).first()
    project = db.query(Project).filter(Project.id == activity.project_id).first()
    return (
        project.name if project else "unknown_project",
        release.release_name if release else "unknown_release",
        str(plan_id),
    )


@router.post("/presigned-upload", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    data: PresignedUploadRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    """Generate a pre-signed S3 URL for direct client-side upload."""
    if data.file_size_bytes > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB} MB"
        )

    # Resolve plan context for S3 key
    plan_id = data.test_plan_id or (
        db.query(TestCase).filter(TestCase.id == data.test_case_id).first().test_plan_id
        if data.test_case_id else None
    )
    if not plan_id:
        raise HTTPException(status_code=400, detail="Either test_case_id or test_plan_id is required")

    project_name, release_name, plan_id_str = _get_plan_context(db, plan_id)

    object_key = s3_service.build_s3_object_key(
        project_name=project_name,
        release_name=release_name,
        test_plan_id=plan_id_str,
        test_case_id=str(data.test_case_id) if data.test_case_id else None,
        artefact_type=data.artefact_type.value,
        filename=data.filename,
    )

    result = s3_service.generate_presigned_upload_url(
        object_key=object_key,
        content_type=data.content_type,
        file_size_bytes=data.file_size_bytes,
    )
    return PresignedUploadResponse(**result)


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def register_evidence(
    data: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("developer")),
):
    """Register an evidence record after successful S3 upload."""
    if not data.test_case_id and not data.test_plan_id:
        raise HTTPException(status_code=400, detail="Either test_case_id or test_plan_id is required")

    evidence = EvidenceArtefact(
        **data.model_dump(),
        uploaded_by=current_user["email"]
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.ARTEFACT_UPLOAD, entity_type="EvidenceArtefact",
        entity_id=str(evidence.id),
        new_value={
            "artefact_type": evidence.artefact_type.value,
            "s3_key": evidence.s3_object_key,
            "filename": evidence.original_filename,
        },
        user_role=current_user.get("role"),
    )
    return evidence


@router.get("", response_model=List[EvidenceResponse])
async def list_evidence(
    test_case_id: Optional[UUID] = None,
    test_plan_id: Optional[UUID] = None,
    artefact_type: Optional[ArtefactType] = None,
    uploaded_by: Optional[str] = None,
    query_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(EvidenceArtefact)
    if test_case_id:
        q = q.filter(EvidenceArtefact.test_case_id == test_case_id)
    if test_plan_id:
        q = q.filter(EvidenceArtefact.test_plan_id == test_plan_id)
    if artefact_type:
        q = q.filter(EvidenceArtefact.artefact_type == artefact_type)
    if uploaded_by:
        q = q.filter(EvidenceArtefact.uploaded_by == uploaded_by)
    if query_id:
        # Search in metadata_json for snowflake query IDs
        q = q.filter(EvidenceArtefact.metadata_json.astext.ilike(f"%{query_id}%"))

    total = q.count()
    items = q.order_by(EvidenceArtefact.uploaded_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/{evidence_id}/download", response_model=PresignedDownloadResponse)
async def get_download_url(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a pre-signed S3 download URL for an evidence artefact."""
    evidence = db.query(EvidenceArtefact).filter(EvidenceArtefact.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    result = s3_service.generate_presigned_download_url(
        object_key=evidence.s3_object_key,
        filename=evidence.original_filename,
    )

    log_action(
        db=db, user_email=current_user["email"],
        action_type=ActionType.ARTEFACT_DOWNLOAD, entity_type="EvidenceArtefact",
        entity_id=str(evidence.id),
        description=f"Downloaded: {evidence.original_filename}",
        user_role=current_user.get("role"),
    )
    return PresignedDownloadResponse(**result)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    evidence = db.query(EvidenceArtefact).filter(EvidenceArtefact.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if evidence.is_legal_hold:
        raise HTTPException(status_code=423, detail="Evidence is under legal hold and cannot be deleted")

    s3_service.delete_object(evidence.s3_object_key)
    db.delete(evidence)
    db.commit()
