# Unit Test Artefact Portal (UTAP)

Enterprise web application for Snowflake and Informatica Cloud (IICS) developers to manage structured unit testing, evidence capture, and release sign-off workflows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UTAP System                              │
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────────────────────┐ │
│  │   React/TS SPA   │◄────►│      FastAPI Backend             │ │
│  │   (Nginx)        │      │      (Python 3.11)               │ │
│  │   Port 80        │      │      Port 8000                   │ │
│  └──────────────────┘      └──────┬────────────┬─────────────┘ │
│                                   │            │               │
│           ┌───────────────────────┘            │               │
│           ▼                                    ▼               │
│  ┌─────────────────┐              ┌────────────────────────┐   │
│  │  PostgreSQL 15  │              │     AWS S3 Bucket      │   │
│  │  (RDS in prod)  │              │  utap-unit-test-       │   │
│  │  Port 5432      │              │  artefacts-prod        │   │
│  └─────────────────┘              └────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Azure AD (External)                         │   │
│  │         SAML 2.0 SSO + Group-based RBAC                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **SAML 2.0 SSO** | Azure AD authentication with group-based RBAC |
| **Structured Test Plans** | Full test lifecycle: DRAFT → IN_REVIEW → APPROVED → LOCKED |
| **Test Case Execution** | Snowflake + IICS evidence capture with structured fields |
| **S3 Artefact Storage** | Pre-signed upload/download URLs, SSE-S3 encryption |
| **Approval Workflows** | Peer → QA → Release Manager sign-off chain |
| **Evidence Completeness** | Configurable threshold (default 90%) enforced on submission |
| **Export Packs** | PDF summary + CSV test cases + sign-off log + ZIP bundle |
| **Audit Log** | Every action logged with user, role, entity, timestamp |
| **8 Seed Templates** | Pre-built test case templates for all common scenarios |
| **Bulk CSV Import** | Import test cases in bulk via CSV upload |

---

## RBAC Roles

| Role | Azure AD Group | Permissions |
|------|---------------|-------------|
| `developer` | `UTAP_Developer` | Create/edit projects, releases, test plans, test cases |
| `reviewer` | `UTAP_Reviewer` | All developer perms + peer/QA sign-off, review plans |
| `release_manager` | `UTAP_Release_Manager` | All reviewer perms + release sign-off (locks plans) |
| `admin` | `UTAP_Admin` | Full access + lock override + user management + audit |

---

## Quick Start (Docker Compose)

### 1. Clone and configure

```bash
git clone <repo>
cd UnitTestingFramework

# Copy and configure environment
cp .env.example .env
# Edit .env with your Azure AD, AWS, and DB credentials
```

### 2. Start all services

```bash
docker-compose up -d
```

### 3. Run seed data

```bash
docker-compose exec backend python seed_data.py
```

### 4. Access the application

| Service | URL |
|---------|-----|
| UTAP UI | http://localhost |
| API Docs | http://localhost/api/docs |
| Health | http://localhost/health |

---

## API Documentation

Interactive OpenAPI docs available at `/api/docs` (Swagger UI) and `/api/redoc`.

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/auth/login` | Initiate SAML SSO |
| `POST` | `/api/v1/auth/acs` | SAML ACS (Azure AD posts here) |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `GET` | `/api/v1/dashboard/summary` | Dashboard metrics |
| `GET/POST` | `/api/v1/projects` | Project management |
| `GET/POST` | `/api/v1/releases` | Release management |
| `GET/POST` | `/api/v1/dev-activities` | Development activities |
| `GET/POST` | `/api/v1/test-plans` | Test plan management |
| `POST` | `/api/v1/test-plans/{id}/submit-review` | Submit plan for review |
| `GET/POST` | `/api/v1/test-cases` | Test case CRUD |
| `POST` | `/api/v1/test-cases/bulk-import` | CSV bulk import |
| `POST` | `/api/v1/evidence/presigned-upload` | Get S3 upload URL |
| `POST` | `/api/v1/evidence` | Register evidence after upload |
| `GET` | `/api/v1/evidence/{id}/download` | Get S3 download URL |
| `GET/POST` | `/api/v1/signoffs` | Sign-off management |
| `POST` | `/api/v1/signoffs/{id}/decide` | Approve/reject sign-off |
| `GET` | `/api/v1/export/test-plan/{id}/pdf` | Download PDF report |
| `GET` | `/api/v1/export/test-plan/{id}/zip` | Download full evidence ZIP |
| `GET` | `/api/v1/audit` | Audit log (reviewer+) |
| `GET` | `/health` | Health check |

---

## S3 Folder Structure

```
utap-unit-test-artefacts-prod/
└── {project_name}/
    └── {release_name}/
        └── {test_plan_id}/
            └── {test_case_id}/
                └── {artefact_type}/
                    └── evidence_{uuid}.{ext}
```

Example:
```
Sales_DWH/RLS_2026_02/TP-123/TC-045/SNOWFLAKE_QUERY_RESULT/evidence_a1b2c3d4.csv
```

---

## Database Migrations

```bash
# Apply all migrations
cd backend
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Roll back one step
alembic downgrade -1
```

---

## Test Case Templates (Seeded)

| ID | Template Name |
|----|--------------|
| TPL-001 | File Ingestion Validation |
| TPL-002 | STG Row Count Validation |
| TPL-003 | PSA Audit Column Validation |
| TPL-004 | DWH Fact Reconciliation |
| TPL-005 | MAT Variance Threshold Validation |
| TPL-006 | IICS Taskflow Success Validation |
| TPL-007 | Idempotency Re-run Validation |
| TPL-008 | Performance Benchmark Validation |

---

## Workflow Enforcement Rules

### Test Case Rules
- **PASS** requires: at least 1 evidence artefact OR approved waiver
- **FAIL** requires: defect reference (JIRA ID) OR reviewer comment

### Test Plan Submission Rules
- All test cases must be executed (no NOT_RUN)
- All FAIL cases must have defect references
- Evidence completeness ≥ 90% (configurable via `EVIDENCE_COMPLETENESS_THRESHOLD`)

### Locking
- Plan is locked when Release Manager approves the RELEASE sign-off
- Locked plans are read-only
- Admin override requires audit trail reason

---

## Production Deployment

### ECS / EKS

Build and push Docker images:

```bash
# Build images
docker build -t utap-backend:latest ./backend
docker build -t utap-frontend:latest ./frontend

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag utap-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/utap-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/utap-backend:latest
```

### Environment Variables via AWS Secrets Manager

Store secrets in Secrets Manager, inject via ECS task definition or EKS Secrets Store CSI Driver:

```bash
aws secretsmanager create-secret \
  --name "utap/prod" \
  --secret-string file://.env
```

### Recommended AWS Architecture

```
Internet → ALB (HTTPS/443) → ECS Service (Frontend + Backend)
                           → RDS PostgreSQL (private subnet)
                           → S3 Bucket (private, SSE-S3)
```

---

## Security Controls Summary

| Control | Implementation |
|---------|----------------|
| Authentication | SAML 2.0 + Azure AD (no local passwords) |
| Authorisation | Group-based RBAC, route + action level |
| Session | HTTP-only secure cookie, 30-min idle timeout |
| CSRF | SameSite cookie policy |
| S3 Access | Pre-signed URLs only (no public bucket) |
| Encryption at rest | SSE-S3 enforced on all uploads |
| Audit | All actions logged to `audit_log` table |
| HTTPS | HTTPSRedirectMiddleware in production |

---

## Directory Structure

```
UnitTestingFramework/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # FastAPI routers (one per resource)
│   │   ├── middleware/          # Auth + logging middleware
│   │   └── services/            # SAML, S3, export, audit services
│   ├── alembic/                 # Database migrations
│   ├── seed_data.py             # Seed templates + sample project
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router configuration
│   │   ├── main.tsx             # React entry point
│   │   ├── types/               # TypeScript interfaces
│   │   ├── services/api.ts      # Axios API client
│   │   ├── contexts/            # Auth context
│   │   ├── components/          # Reusable components
│   │   └── pages/               # Page components
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── SAML_INTEGRATION_GUIDE.md
```
