"""
SAML 2.0 Service Provider implementation for Azure AD integration.

This service handles:
  - SAML authentication request generation
  - SAML assertion processing / validation
  - Attribute extraction (email, name, groups)
  - Role mapping from Azure AD groups
"""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree as ET

import structlog
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from app.config import settings

logger = structlog.get_logger()

# RBAC: Azure AD group → internal role
GROUP_ROLE_MAP: Dict[str, str] = {
    settings.AZURE_GROUP_ADMIN: "admin",
    settings.AZURE_GROUP_RELEASE_MANAGER: "release_manager",
    settings.AZURE_GROUP_REVIEWER: "reviewer",
    settings.AZURE_GROUP_DEVELOPER: "developer",
}

# Role hierarchy for permission checks (higher index = more permissions)
ROLE_HIERARCHY = ["developer", "reviewer", "release_manager", "admin"]


def build_saml_settings(request_host: str) -> dict:
    """Build python3-saml settings dict from app config."""
    return {
        "strict": True,
        "debug": settings.DEBUG,
        "sp": {
            "entityId": settings.SAML_ENTITY_ID,
            "assertionConsumerService": {
                "url": settings.SAML_ACS_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": settings.SAML_SLO_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": settings.SAML_CERT,
            "privateKey": settings.SAML_PRIVATE_KEY,
        },
        "idp": {
            "entityId": settings.AZURE_AD_ENTITY_ID,
            "singleSignOnService": {
                "url": settings.AZURE_AD_SSO_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": settings.AZURE_AD_SSO_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": settings.AZURE_AD_CERT,
        },
        "security": {
            "nameIdEncrypted": False,
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "signMetadata": False,
            "wantMessagesSigned": False,
            "wantAssertionsSigned": True,   # Enforce assertion signature from Azure AD
            "wantAssertionsEncrypted": False,
            "wantNameId": True,
            "wantNameIdEncrypted": False,
            "wantAttributeStatement": True,
            "requestedAuthnContext": False,
            "failOnAuthnContextMismatch": False,
        },
    }


def prepare_flask_request(request) -> dict:
    """Convert FastAPI Request to the dict format python3-saml expects."""
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host", ""),
        "server_port": str(request.url.port or (443 if request.url.scheme == "https" else 80)),
        "script_name": "",
        "get_data": dict(request.query_params),
        "post_data": {},
    }


def initiate_sso(request) -> str:
    """Generate SAML AuthnRequest and return redirect URL."""
    req = prepare_flask_request(request)
    saml_settings = build_saml_settings(str(request.url))
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    redirect_url = auth.login()
    logger.info("SAML SSO initiated", redirect_url=redirect_url)
    return redirect_url


def process_saml_response(
    request_data: dict,
    post_data: dict,
    host: str,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Process the SAML response from Azure AD.

    Returns:
        (user_attributes, error_message)
    """
    req = {
        "https": "on",
        "http_host": host,
        "server_port": "443",
        "script_name": "",
        "get_data": request_data,
        "post_data": post_data,
    }

    try:
        saml_settings = build_saml_settings(host)
        auth = OneLogin_Saml2_Auth(req, saml_settings)
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            logger.error("SAML assertion errors", errors=errors, reason=error_reason)
            return None, f"SAML authentication failed: {error_reason}"

        if not auth.is_authenticated():
            return None, "SAML authentication: user not authenticated"

        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        session_index = auth.get_session_index()

        # Extract user attributes from SAML claims
        email = _extract_claim(attributes, [
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "email", "mail",
        ]) or name_id

        given_name = _extract_claim(attributes, [
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
            "givenname", "given_name",
        ])

        surname = _extract_claim(attributes, [
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
            "surname", "sn",
        ])

        upn = _extract_claim(attributes, [
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn",
            "name", "userprincipalname",
        ])

        # Groups claim — Azure AD returns list of group object IDs or display names
        groups = attributes.get(
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
            attributes.get("groups", [])
        )

        role = map_groups_to_role(groups)

        user_info = {
            "email": email,
            "given_name": given_name,
            "surname": surname,
            "display_name": f"{given_name or ''} {surname or ''}".strip() or email,
            "upn": upn or email,
            "groups": groups,
            "role": role,
            "name_id": name_id,
            "session_index": session_index,
        }

        logger.info(
            "SAML authentication successful",
            email=email,
            role=role,
            groups=groups,
        )
        return user_info, None

    except Exception as e:
        logger.exception("SAML processing error", error=str(e))
        return None, f"SAML processing error: {str(e)}"


def initiate_slo(request, name_id: str, session_index: str) -> str:
    """Generate SAML SLO request and return redirect URL."""
    req = prepare_flask_request(request)
    saml_settings = build_saml_settings(str(request.url))
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    redirect_url = auth.logout(name_id=name_id, session_index=session_index)
    return redirect_url


def map_groups_to_role(groups: list) -> str:
    """
    Map Azure AD group memberships to UTAP internal role.
    Priority: admin > release_manager > reviewer > developer
    If no recognised group, default to 'developer' (least privilege).
    """
    for group_name, role in GROUP_ROLE_MAP.items():
        if group_name in groups:
            return role
    # Also check by partial match for display-name vs object-id scenarios
    groups_lower = [g.lower() for g in groups]
    for group_name, role in GROUP_ROLE_MAP.items():
        if group_name.lower() in groups_lower:
            return role
    logger.warning("No recognised Azure AD group found, defaulting to developer", groups=groups)
    return "developer"


def has_permission(user_role: str, required_role: str) -> bool:
    """Check if user_role meets or exceeds required_role in the hierarchy."""
    if user_role not in ROLE_HIERARCHY or required_role not in ROLE_HIERARCHY:
        return False
    return ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required_role)


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(64)


def _extract_claim(attributes: dict, possible_keys: list) -> Optional[str]:
    """Extract first non-empty value from a list of possible attribute keys."""
    for key in possible_keys:
        val = attributes.get(key)
        if val:
            if isinstance(val, list) and val:
                return val[0]
            if isinstance(val, str):
                return val
    return None
