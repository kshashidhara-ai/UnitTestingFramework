"""
UTAP Demo Configuration — SQLite + bypass auth for live preview.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Unit Test Artefact Portal (UTAP)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "demo"
    SECRET_KEY: str = "utap-demo-secret-key-for-preview-only"

    # SQLite for demo (no Postgres needed)
    DATABASE_URL: str = "sqlite:///./utap_demo.db"

    # S3 — mocked in demo mode
    AWS_ACCESS_KEY_ID: str = "demo"
    AWS_SECRET_ACCESS_KEY: str = "demo"
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "utap-demo-bucket"
    S3_PRESIGNED_URL_EXPIRY: int = 3600
    MAX_UPLOAD_SIZE_MB: int = 25

    # SAML — not used in demo (bypass auth)
    SAML_ENTITY_ID: str = "https://utap.demo.com/saml/metadata"
    SAML_ACS_URL: str = "https://utap.demo.com/saml/acs"
    SAML_SLO_URL: str = "https://utap.demo.com/saml/logout"
    SAML_CERT: str = ""
    SAML_PRIVATE_KEY: str = ""
    AZURE_AD_ENTITY_ID: str = ""
    AZURE_AD_SSO_URL: str = ""
    AZURE_AD_CERT: str = ""
    AZURE_AD_METADATA_URL: str = ""

    SESSION_TIMEOUT_MINUTES: int = 120
    COOKIE_SECURE: bool = False
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"

    AZURE_GROUP_DEVELOPER: str = "UTAP_Developer"
    AZURE_GROUP_REVIEWER: str = "UTAP_Reviewer"
    AZURE_GROUP_RELEASE_MANAGER: str = "UTAP_Release_Manager"
    AZURE_GROUP_ADMIN: str = "UTAP_Admin"

    EVIDENCE_COMPLETENESS_THRESHOLD: float = 90.0
    CORS_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env.demo"


settings = Settings()
