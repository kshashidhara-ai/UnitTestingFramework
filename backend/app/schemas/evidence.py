from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.evidence import ArtefactType


class EvidenceCreate(BaseModel):
    test_case_id: Optional[UUID] = None
    test_plan_id: Optional[UUID] = None
    artefact_type: ArtefactType
    description: Optional[str] = None
    original_filename: Optional[str] = None
    s3_object_key: str
    s3_bucket: str
    file_size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class EvidenceResponse(BaseModel):
    id: UUID
    test_case_id: Optional[UUID] = None
    test_plan_id: Optional[UUID] = None
    artefact_type: ArtefactType
    description: Optional[str] = None
    original_filename: Optional[str] = None
    s3_object_key: str
    s3_bucket: str
    file_size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    is_legal_hold: bool
    uploaded_by: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PresignedUploadRequest(BaseModel):
    test_case_id: Optional[UUID] = None
    test_plan_id: Optional[UUID] = None
    artefact_type: ArtefactType
    filename: str = Field(..., max_length=512)
    content_type: str
    file_size_bytes: int


class PresignedUploadResponse(BaseModel):
    upload_url: str
    s3_object_key: str
    s3_bucket: str
    fields: Optional[Dict[str, str]] = None
    expires_in: int


class PresignedDownloadResponse(BaseModel):
    download_url: str
    expires_in: int
    filename: Optional[str] = None
