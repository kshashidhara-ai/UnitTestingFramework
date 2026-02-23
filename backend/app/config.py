from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Unit Test Artefact Portal (UTAP)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = "change-me-in-production-use-32-char-secret"

    # Database
    DATABASE_URL: str = "postgresql://utap:utap@localhost:5432/utap_db"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "utap-unit-test-artefacts-prod"
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # 1 hour
    MAX_UPLOAD_SIZE_MB: int = 25

    # SAML / Azure AD
    SAML_ENTITY_ID: str = "https://utap.company.com/saml/metadata"
    SAML_ACS_URL: str = "https://utap.company.com/saml/acs"
    SAML_SLO_URL: str = "https://utap.company.com/saml/logout"
    SAML_CERT: str = ""  # SP certificate (PEM)
    SAML_PRIVATE_KEY: str = ""  # SP private key (PEM)
    AZURE_AD_METADATA_URL: str = ""  # IdP metadata URL
    AZURE_AD_ENTITY_ID: str = ""
    AZURE_AD_SSO_URL: str = ""
    AZURE_AD_CERT: str = ""  # IdP certificate

    # Session
    SESSION_TIMEOUT_MINUTES: int = 30
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"

    # RBAC Group Mapping
    AZURE_GROUP_DEVELOPER: str = "UTAP_Developer"
    AZURE_GROUP_REVIEWER: str = "UTAP_Reviewer"
    AZURE_GROUP_RELEASE_MANAGER: str = "UTAP_Release_Manager"
    AZURE_GROUP_ADMIN: str = "UTAP_Admin"

    # Evidence Completeness
    EVIDENCE_COMPLETENESS_THRESHOLD: float = 90.0

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://utap.company.com"]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
