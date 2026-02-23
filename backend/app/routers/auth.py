"""
Authentication router — SAML 2.0 SSO endpoints.

Endpoints:
  GET  /auth/login       → redirect to Azure AD SSO
  POST /auth/acs         → SAML assertion consumer (Azure AD posts here)
  GET  /auth/logout      → initiate SLO
  GET  /auth/me          → return current user info
  GET  /saml/metadata    → SP metadata XML for Azure AD registration
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Response, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_session import UserSession
from app.models.audit_log import ActionType
from app.middleware.auth import get_current_user, COOKIE_NAME
from app.services import saml_service
from app.services.audit_service import log_action
from app.config import settings
import structlog

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = structlog.get_logger()


@router.get("/login")
async def initiate_login(request: Request):
    """Redirect user to Azure AD SSO login page."""
    try:
        redirect_url = saml_service.initiate_sso(request)
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error("SSO initiation failed", error=str(e))
        raise HTTPException(status_code=500, detail="SSO initiation failed")


@router.post("/acs")
async def saml_acs(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    SAML Assertion Consumer Service.
    Azure AD posts the SAML response here after authentication.
    """
    form_data = await request.form()
    post_data = dict(form_data)
    host = request.headers.get("host", "")

    user_info, error = saml_service.process_saml_response(
        request_data=dict(request.query_params),
        post_data=post_data,
        host=host,
    )

    if error or not user_info:
        logger.error("SAML ACS failed", error=error)
        raise HTTPException(status_code=401, detail=error or "Authentication failed")

    # Create session
    session_token = saml_service.generate_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=8)  # Max session duration

    db_session = UserSession(
        session_token=session_token,
        user_email=user_info["email"],
        user_name=user_info.get("upn"),
        display_name=user_info.get("display_name"),
        role=user_info["role"],
        azure_groups=user_info.get("groups", []),
        saml_name_id=user_info.get("name_id"),
        saml_session_index=user_info.get("session_index"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
    )
    db.add(db_session)
    db.commit()

    # Audit login
    log_action(
        db=db,
        user_email=user_info["email"],
        action_type=ActionType.LOGIN,
        description=f"User logged in via SAML SSO, role: {user_info['role']}",
        ip_address=request.client.host if request.client else None,
        user_role=user_info["role"],
    )
    log_action(
        db=db,
        user_email=user_info["email"],
        action_type=ActionType.ROLE_MAPPED,
        new_value={"role": user_info["role"], "groups": user_info.get("groups", [])},
        description=f"Azure AD groups mapped to role: {user_info['role']}",
        user_role=user_info["role"],
    )

    # Set secure HTTP-only session cookie
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=int((expires_at - datetime.utcnow()).total_seconds()),
    )
    return redirect


@router.get("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Logout — invalidate session and optionally initiate SAML SLO."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.query(UserSession).filter(UserSession.session_token == token).first()
        if session:
            session.is_active = False
            db.commit()

    log_action(
        db=db,
        user_email=current_user["email"],
        action_type=ActionType.LOGOUT,
        description="User logged out",
        ip_address=request.client.host if request.client else None,
        user_role=current_user.get("role"),
    )

    # Clear session cookie
    redir = RedirectResponse(url="/auth/login", status_code=302)
    redir.delete_cookie(COOKIE_NAME)

    # Optionally initiate SAML SLO
    name_id = current_user.get("name_id")
    session_index = current_user.get("session_index")
    if name_id and settings.AZURE_AD_SSO_URL:
        try:
            slo_url = saml_service.initiate_slo(request, name_id, session_index)
            return RedirectResponse(url=slo_url, status_code=302)
        except Exception:
            pass

    return redir


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "email": current_user["email"],
        "name": current_user.get("name"),
        "display_name": current_user.get("display_name"),
        "role": current_user["role"],
        "groups": current_user.get("groups", []),
    }


@router.get("/saml/metadata", response_class=HTMLResponse)
async def saml_metadata(request: Request):
    """Return SAML SP metadata XML for Azure AD app registration."""
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
    saml_cfg = saml_service.build_saml_settings(str(request.base_url))
    saml_settings_obj = OneLogin_Saml2_Settings(settings=saml_cfg, sp_validation_only=True)
    metadata = saml_settings_obj.get_sp_metadata()
    return HTMLResponse(content=metadata, media_type="application/xml")
