"""
Authentication middleware — validates session token from HTTP-only cookie
and attaches the current user to the request state.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_session import UserSession
from app.config import settings
import structlog

logger = structlog.get_logger()

COOKIE_NAME = "utap_session"


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Dependency that validates the session cookie and returns current user info.
    Raises 401 if session is missing, invalid, or expired.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in via SSO.",
        )

    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == token,
            UserSession.is_active == True,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or has been revoked.",
        )

    now = datetime.utcnow()

    # Check absolute expiry
    if session.expires_at < now:
        session.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )

    # Check idle timeout
    idle_since = session.last_activity_at
    if (now - idle_since) > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
        session.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Session timed out after {settings.SESSION_TIMEOUT_MINUTES} minutes of inactivity.",
        )

    # Update last activity
    session.last_activity_at = now
    db.commit()

    return {
        "session_id": str(session.id),
        "email": session.user_email,
        "name": session.user_name,
        "display_name": session.display_name,
        "role": session.role,
        "groups": session.azure_groups or [],
        "name_id": session.saml_name_id,
        "session_index": session.saml_session_index,
    }


def require_role(*required_roles: str):
    """
    Dependency factory that enforces one of the specified roles.
    Usage: Depends(require_role("admin", "release_manager"))
    """
    from app.services.saml_service import ROLE_HIERARCHY

    async def _check(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "developer")

        for required in required_roles:
            if required not in ROLE_HIERARCHY:
                continue
            if ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_roles}, Your role: {user_role}",
        )

    return _check
