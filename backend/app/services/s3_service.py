"""
AWS S3 Service for UTAP artefact storage.

Responsibilities:
  - Generate pre-signed upload URLs
  - Generate pre-signed download URLs
  - Enforce bucket folder structure
  - Validate upload size limits
  - Server-side encryption enforcement
"""
import os
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import structlog

from app.config import settings

logger = structlog.get_logger()

# S3 folder structure:
# /{project_name}/{release_name}/{test_plan_id}/{test_case_id}/{artefact_type}/

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def build_s3_object_key(
    project_name: str,
    release_name: str,
    test_plan_id: str,
    test_case_id: Optional[str],
    artefact_type: str,
    filename: str,
) -> str:
    """
    Build the S3 object key following the UTAP folder convention.

    Example:
        Sales_DWH/RLS_2026_02/TP-123/TC-045/Snowflake_Query_Result/evidence_<uuid>.csv
    """
    safe_project = _sanitize_path_segment(project_name)
    safe_release = _sanitize_path_segment(release_name)
    safe_plan = _sanitize_path_segment(test_plan_id)
    safe_case = _sanitize_path_segment(test_case_id or "plan_level")
    safe_type = _sanitize_path_segment(artefact_type)
    unique_id = uuid.uuid4().hex[:8]
    _, ext = os.path.splitext(filename)
    safe_filename = f"evidence_{unique_id}{ext}"

    return f"{safe_project}/{safe_release}/{safe_plan}/{safe_case}/{safe_type}/{safe_filename}"


def generate_presigned_upload_url(
    object_key: str,
    content_type: str,
    file_size_bytes: int,
    expiry_seconds: int = None,
) -> Dict:
    """
    Generate a pre-signed POST URL for direct S3 upload from client.

    Returns dict with:
        url, fields, s3_object_key, s3_bucket, expires_in
    """
    if file_size_bytes > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"File size {file_size_bytes} exceeds maximum allowed "
            f"{MAX_UPLOAD_BYTES} bytes ({settings.MAX_UPLOAD_SIZE_MB} MB)"
        )

    expiry = expiry_seconds or settings.S3_PRESIGNED_URL_EXPIRY
    s3 = _get_s3_client()

    try:
        response = s3.generate_presigned_post(
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Fields={
                "Content-Type": content_type,
                "x-amz-server-side-encryption": "AES256",
            },
            Conditions=[
                {"Content-Type": content_type},
                {"x-amz-server-side-encryption": "AES256"},
                ["content-length-range", 1, MAX_UPLOAD_BYTES],
            ],
            ExpiresIn=expiry,
        )
        logger.info(
            "Presigned upload URL generated",
            object_key=object_key,
            bucket=settings.S3_BUCKET_NAME,
        )
        return {
            "upload_url": response["url"],
            "fields": response["fields"],
            "s3_object_key": object_key,
            "s3_bucket": settings.S3_BUCKET_NAME,
            "expires_in": expiry,
        }
    except (ClientError, BotoCoreError) as e:
        logger.error("Failed to generate presigned upload URL", error=str(e))
        raise


def generate_presigned_download_url(
    object_key: str,
    filename: Optional[str] = None,
    expiry_seconds: int = None,
) -> Dict:
    """Generate a pre-signed GET URL for downloading an artefact."""
    expiry = expiry_seconds or settings.S3_PRESIGNED_URL_EXPIRY
    s3 = _get_s3_client()

    params = {
        "Bucket": settings.S3_BUCKET_NAME,
        "Key": object_key,
    }
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry,
        )
        logger.info(
            "Presigned download URL generated",
            object_key=object_key,
            bucket=settings.S3_BUCKET_NAME,
        )
        return {
            "download_url": url,
            "expires_in": expiry,
            "filename": filename,
        }
    except (ClientError, BotoCoreError) as e:
        logger.error("Failed to generate presigned download URL", error=str(e))
        raise


def delete_object(object_key: str) -> bool:
    """Delete an object from S3 (admin/override only)."""
    s3 = _get_s3_client()
    try:
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
        logger.info("S3 object deleted", object_key=object_key)
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error("Failed to delete S3 object", object_key=object_key, error=str(e))
        return False


def object_exists(object_key: str) -> bool:
    """Check if an S3 object exists."""
    s3 = _get_s3_client()
    try:
        s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
        return True
    except ClientError:
        return False


def get_object_metadata(object_key: str) -> Optional[Dict]:
    """Retrieve object metadata from S3."""
    s3 = _get_s3_client()
    try:
        response = s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
        return {
            "content_length": response.get("ContentLength"),
            "content_type": response.get("ContentType"),
            "last_modified": response.get("LastModified"),
            "server_side_encryption": response.get("ServerSideEncryption"),
            "metadata": response.get("Metadata", {}),
        }
    except ClientError:
        return None


def create_bucket_if_not_exists():
    """Ensure the S3 bucket exists with correct configuration (run at startup)."""
    s3 = _get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        logger.info("S3 bucket exists", bucket=settings.S3_BUCKET_NAME)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            logger.info("Creating S3 bucket", bucket=settings.S3_BUCKET_NAME)
            if settings.AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            else:
                s3.create_bucket(
                    Bucket=settings.S3_BUCKET_NAME,
                    CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
                )
            # Block all public access
            s3.put_public_access_block(
                Bucket=settings.S3_BUCKET_NAME,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            # Enable default SSE-S3 encryption
            s3.put_bucket_encryption(
                Bucket=settings.S3_BUCKET_NAME,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                },
            )
            # Lifecycle: move to Glacier after 1 year, expire after 2 years
            s3.put_bucket_lifecycle_configuration(
                Bucket=settings.S3_BUCKET_NAME,
                LifecycleConfiguration={
                    "Rules": [
                        {
                            "ID": "utap-retention-policy",
                            "Status": "Enabled",
                            "Filter": {"Prefix": ""},
                            "Transitions": [
                                {
                                    "Days": 365,
                                    "StorageClass": "GLACIER",
                                }
                            ],
                            "Expiration": {"Days": 730},
                        }
                    ]
                },
            )
            logger.info("S3 bucket configured", bucket=settings.S3_BUCKET_NAME)


def _sanitize_path_segment(value: str) -> str:
    """Sanitize a string for safe use as S3 key path segment."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in value)[:100]
