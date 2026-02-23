# Azure AD SAML 2.0 Integration Guide

## Overview

UTAP uses SAML 2.0 (Service Provider–initiated SSO) via Azure AD. This guide walks through every step required to register the UTAP Enterprise App in your Azure AD tenant and wire it to the backend.

---

## 1. Prerequisites

| Item | Detail |
|------|--------|
| Azure AD role | Application Administrator or Global Administrator |
| UTAP URL | `https://utap.company.com` (replace with your domain) |
| SP certificate | RSA 2048-bit, self-signed or CA-issued |

---

## 2. Generate SP Certificate (if needed)

```bash
# Generate RSA private key + self-signed certificate (2 year validity)
openssl req -x509 -sha256 -nodes -days 730 \
  -newkey rsa:2048 \
  -keyout utap_sp.key \
  -out utap_sp.crt \
  -subj "/CN=utap.company.com/O=Your Company/C=US"

# View the certificate (copy this into SAML_CERT env var)
cat utap_sp.crt

# View the private key (copy this into SAML_PRIVATE_KEY env var)
cat utap_sp.key
```

---

## 3. Register Azure AD Enterprise Application

### 3.1 Create the App

1. Azure Portal → **Azure Active Directory** → **Enterprise Applications**
2. Click **New application** → **Create your own application**
3. Name: `UTAP - Unit Test Artefact Portal`
4. Select: **Integrate any other application you don't find in the gallery (Non-gallery)**
5. Click **Create**

### 3.2 Configure Single Sign-On

1. In the new app: **Single sign-on** → **SAML**
2. Configure **Basic SAML Configuration**:

| Field | Value |
|-------|-------|
| Identifier (Entity ID) | `https://utap.company.com/saml/metadata` |
| Reply URL (ACS URL) | `https://utap.company.com/saml/acs` |
| Sign on URL | `https://utap.company.com/auth/login` |
| Logout URL | `https://utap.company.com/saml/logout` |
| Relay State | *(leave blank)* |

3. Click **Save**

---

## 4. Configure Attribute Claims

In **Attributes & Claims**, set up these mappings:

| Claim Name | Source Attribute |
|------------|-----------------|
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | `user.mail` |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` | `user.givenname` |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` | `user.surname` |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn` | `user.userprincipalname` |
| `http://schemas.microsoft.com/ws/2008/06/identity/claims/groups` | *(Group claims — see below)* |

### 4.1 Add Group Claims

1. Click **Add a group claim**
2. Select: **Security groups** (or **All groups** if needed)
3. Source attribute: **Group Display Name** (recommended) or **sAMAccountName**
4. Check: **Customize the name of the group claim** → Name: `groups`

> **Note:** If users are members of many groups, Azure AD may omit group claims and instead include a `_claim_names` hint. In that case, use the Microsoft Graph API overage endpoint, or limit group membership.

---

## 5. Configure Token Signing

1. In **SAML Signing Certificate** section:
   - Signing Algorithm: **SHA-256**
   - Download: **Certificate (Base64)**  — this is your `AZURE_AD_CERT`

2. Optionally upload your SP certificate if you want Azure to encrypt assertions:
   - Click **Edit** → **Verification certificates** → Upload `utap_sp.crt`

---

## 6. Collect IdP Settings

From the **SAML Signing Certificate** panel, collect:

| Setting | Where to Find |
|---------|---------------|
| `AZURE_AD_ENTITY_ID` | **Azure AD Identifier** (e.g. `https://sts.windows.net/{tenant-id}/`) |
| `AZURE_AD_SSO_URL` | **Login URL** (e.g. `https://login.microsoftonline.com/{tenant-id}/saml2`) |
| `AZURE_AD_CERT` | Downloaded Base64 certificate content (strip `-----BEGIN/END CERTIFICATE-----`) |
| `AZURE_AD_METADATA_URL` | **App Federation Metadata URL** |

---

## 7. Configure Azure AD Groups for RBAC

Create the following Security Groups in Azure AD:

| Group Name | UTAP Role | Description |
|------------|-----------|-------------|
| `UTAP_Developer` | `developer` | Create/edit test plans and cases |
| `UTAP_Reviewer` | `reviewer` | Review, sign off at Peer/QA level |
| `UTAP_Release_Manager` | `release_manager` | Final sign-off, release approval |
| `UTAP_Admin` | `admin` | Full admin, lock override, audit |

Then assign users to these groups.

---

## 8. Assign Users to the Enterprise App

1. In Enterprise App → **Users and groups**
2. Click **Add user/group**
3. Assign the security groups (or individual users) who need UTAP access

---

## 9. Configure UTAP Environment Variables

Set these in your `.env` file (or AWS Secrets Manager):

```env
SAML_ENTITY_ID=https://utap.company.com/saml/metadata
SAML_ACS_URL=https://utap.company.com/saml/acs
SAML_SLO_URL=https://utap.company.com/saml/logout

SAML_CERT=<content of utap_sp.crt — single line with \n>
SAML_PRIVATE_KEY=<content of utap_sp.key — single line with \n>

AZURE_AD_ENTITY_ID=https://sts.windows.net/{YOUR-TENANT-ID}/
AZURE_AD_SSO_URL=https://login.microsoftonline.com/{YOUR-TENANT-ID}/saml2
AZURE_AD_CERT=<Base64 cert from Azure, single line>

AZURE_GROUP_DEVELOPER=UTAP_Developer
AZURE_GROUP_REVIEWER=UTAP_Reviewer
AZURE_GROUP_RELEASE_MANAGER=UTAP_Release_Manager
AZURE_GROUP_ADMIN=UTAP_Admin
```

---

## 10. SAML Flow Diagram

```
User Browser          UTAP Backend           Azure AD
     |                     |                     |
     |--GET /auth/login---->|                     |
     |                     |--Build AuthnRequest->|
     |<--HTTP 302 redirect--|                     |
     |                                            |
     |----------POST login.microsoftonline.com--->|
     |<----------SAML Response (POST to ACS)------|
     |                                            |
     |--POST /api/v1/auth/acs (SAMLResponse)----->|
     |          |--Validate signature              |
     |          |--Extract attributes              |
     |          |--Map groups → role               |
     |          |--Create session token            |
     |<--HTTP 302 / (Set-Cookie: utap_session)-----|
     |                                            |
     |--GET / (with session cookie)-------------->|
     |<--Dashboard HTML---------------------------|
```

---

## 11. SP Metadata Endpoint

UTAP exposes its SP metadata at:

```
GET https://utap.company.com/api/v1/auth/saml/metadata
```

You can download this XML and upload it to Azure AD's **Upload metadata file** option for automatic configuration.

---

## 12. Testing the Integration

1. Navigate to `https://utap.company.com/auth/login`
2. Verify redirect to Microsoft login page
3. Log in with an account that is a member of one of the UTAP groups
4. Verify redirect back to UTAP dashboard
5. Check `GET /api/v1/auth/me` returns correct email and role

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SAML authentication failed: Invalid signature` | Wrong IdP certificate in `AZURE_AD_CERT` | Re-download cert from Azure Portal |
| `User not authenticated` | Groups claim not emitted | Check group claim configuration in Azure |
| Role defaults to `developer` | Group names don't match env vars | Verify `AZURE_GROUP_*` env vars match exact Azure AD group display names |
| `Assertion expired` | Clock skew between servers | Sync NTP on UTAP server |
