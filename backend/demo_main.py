"""
UTAP Demo Server — self-contained with SQLite + bypass auth.
Run: python demo_main.py
"""
import sys
import os

# Patch config before any imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./utap_demo.db")
os.environ.setdefault("ENVIRONMENT", "demo")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "utap-demo-secret-key-for-preview-only")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "demo")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "demo")
os.environ.setdefault("S3_BUCKET_NAME", "utap-demo")
os.environ.setdefault("SAML_ENTITY_ID", "https://utap-demo.local/saml/metadata")
os.environ.setdefault("SAML_ACS_URL", "https://utap-demo.local/saml/acs")
os.environ.setdefault("SAML_SLO_URL", "https://utap-demo.local/saml/logout")
os.environ.setdefault("AZURE_AD_ENTITY_ID", "demo")
os.environ.setdefault("AZURE_AD_SSO_URL", "demo")
os.environ.setdefault("CORS_ORIGINS", '["*"]')
os.environ.setdefault("COOKIE_SECURE", "false")

sys.path.insert(0, os.path.dirname(__file__))

import structlog
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ── SQLite-compatible database setup ────────────────────────────────────────
DATABASE_URL = "sqlite:///./utap_demo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Import models (they use the app.database Base) ──────────────────────────
# Monkey-patch the database module to use our SQLite engine
import app.database as db_module
db_module.engine = engine
db_module.SessionLocal = SessionLocal
db_module.get_db = get_db

from app.database import Base
from app.models import *  # noqa

# Create all tables
Base.metadata.create_all(bind=engine)
print("✓ SQLite database initialized")

# ── Logging setup ────────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()


# ── Demo seed data ───────────────────────────────────────────────────────────
def seed_demo_data():
    from app.models.project import Project
    from app.models.release import Release, EnvironmentScope, ReleaseStatus
    from app.models.dev_activity import DevelopmentActivity, ActivityType
    from app.models.test_plan import TestPlan, TestPlanStatus
    from app.models.test_case import TestCase, TestCaseCategory, TestCaseComponent, TestCaseStatus

    db = SessionLocal()
    try:
        if db.query(Project).count() > 0:
            print("✓ Demo data already seeded")
            return

        # Project
        proj = Project(
            id=uuid.uuid4(), name="Sales_DWH", domain="Data Warehouse",
            description="Sales DWH — Demo Project", owner_team="DWH Engineering",
            country="US", dataset="Sales", vendor="IQVIA", frequency="Weekly",
            created_by="admin@utap.demo",
        )
        db.add(proj); db.flush()

        # Release
        rel = Release(
            id=uuid.uuid4(), project_id=proj.id, release_name="RLS_2026_02",
            environment_scope=EnvironmentScope.SIT, status=ReleaseStatus.IN_PROGRESS,
            created_by="admin@utap.demo",
        )
        db.add(rel); db.flush()

        # Dev Activity
        act = DevelopmentActivity(
            id=uuid.uuid4(), project_id=proj.id, release_id=rel.id,
            title="Sales Fact — New Metrics: Discount Amount & Net Revenue",
            activity_type=ActivityType.MIXED, jira_id="DWH-4521",
            snowflake_objects=[{"database": "SALES_DWH", "schema_name": "FACTS", "object_name": "FACT_SALES", "object_type": "TABLE"}],
            iics_assets=[{"org": "PROD_ORG", "asset_type": "Mapping", "asset_name": "M_SALES_FACT_LOAD", "asset_id": "A-001"}],
            created_by="admin@utap.demo",
        )
        db.add(act); db.flush()

        # Test Plan
        plan = TestPlan(
            id=uuid.uuid4(), dev_activity_id=act.id,
            plan_name="TP-001: Sales Fact Table SIT Test Plan",
            scope="Validate DISCOUNT_AMOUNT and NET_REVENUE additions to FACT_SALES.",
            test_strategy="1. File ingestion\n2. IICS mapping\n3. Reconciliation\n4. Performance",
            status=TestPlanStatus.DRAFT, evidence_completeness_score=0.0,
            created_by="developer@utap.demo",
        )
        db.add(plan); db.flush()

        # Test Cases
        templates = [
            ("TC-001", "FUNCTIONAL", "SNOWFLAKE", "Validate source file row count matches staging table",
             "Source file loaded to stage", "1. Count rows in source\n2. COUNT(*) FROM STG_SALES\n3. Compare",
             "STG row count = source row count. Zero truncations.", "NOT_RUN"),
            ("TC-002", "DATA_QUALITY", "SNOWFLAKE", "Validate PSA audit columns populated",
             "PSA load completed", "SELECT * FROM PSA_SALES WHERE LOAD_TIMESTAMP IS NULL",
             "Zero NULL audit columns", "PASS"),
            ("TC-003", "RECONCILIATION", "SNOWFLAKE", "Reconcile FACT_SALES vs source system",
             "DWH load completed", "SELECT SUM(NET_REVENUE) FROM FACT_SALES WHERE PERIOD='2026-02'",
             "Variance <= 0.01%", "IN_PROGRESS"),
            ("TC-004", "INTEGRATION", "IICS", "IICS Taskflow TF_SALES_DWH_WEEKLY completes successfully",
             "Taskflow deployed to SIT", "1. Trigger taskflow\n2. Monitor in IICS Activity Monitor\n3. Verify all tasks Success",
             "Taskflow status = Success. No errors.", "NOT_RUN"),
            ("TC-005", "IDEMPOTENCY", "BOTH", "Re-run mapping produces identical results without duplicates",
             "Initial run completed", "Re-execute mapping; compare row counts pre/post",
             "Identical counts, zero duplicates", "PASS"),
            ("TC-006", "PERFORMANCE", "SNOWFLAKE", "Query executes within 60s SLA",
             "Warehouse sized to MEDIUM", "Execute query, capture QUERY_ID, check elapsed time",
             "Execution <= 60 seconds", "FAIL"),
            ("TC-007", "DATA_QUALITY", "SNOWFLAKE", "MAT variance within 10% threshold vs prior period",
             "MAT refresh complete", "SELECT variance_pct FROM MAT_RECONCILIATION_VIEW",
             "All metrics within 10% variance", "NOT_RUN"),
            ("TC-008", "REGRESSION", "SNOWFLAKE", "Existing metrics unchanged after schema change",
             "Schema migration applied", "Compare REVENUE totals before/after migration",
             "All existing metrics match baseline", "NOT_RUN"),
        ]

        for tc_id, cat, comp, obj, pre, steps, expected, status in templates:
            tc = TestCase(
                id=uuid.uuid4(), test_plan_id=plan.id, testcase_id=tc_id,
                category=cat, component=comp, objective=obj,
                preconditions=pre, test_steps=steps, expected_result=expected,
                status=status,
                defect_reference="DWH-4523" if status == "FAIL" else None,
                reviewer_comment="Performance degradation identified — warehouse needs resizing" if status == "FAIL" else None,
                executed_by="developer@utap.demo" if status in ("PASS", "FAIL", "IN_PROGRESS") else None,
                executed_at=datetime.utcnow() if status in ("PASS", "FAIL") else None,
                snowflake_query_ids=["01abc123-0000-0001-0000-000000000001"] if comp in ("SNOWFLAKE", "BOTH") and status == "PASS" else None,
                snowflake_warehouse="COMPUTE_WH_M" if comp in ("SNOWFLAKE", "BOTH") else None,
                snowflake_database_schema_object="SALES_DWH.FACTS.FACT_SALES" if comp in ("SNOWFLAKE", "BOTH") else None,
                iics_org="PROD_ORG" if comp in ("IICS", "BOTH") else None,
                iics_asset_name="TF_SALES_DWH_WEEKLY" if comp in ("IICS", "BOTH") else None,
                created_by="developer@utap.demo",
            )
            db.add(tc)

        # Recalculate completeness
        total = 8
        with_evidence = 2  # TC-002 and TC-005 are PASS (demo)
        plan.evidence_completeness_score = round((with_evidence / total) * 100, 1)
        db.commit()
        print(f"✓ Demo data seeded: {proj.name} / {rel.release_name} / {plan.plan_name}")
    except Exception as e:
        db.rollback()
        print(f"⚠ Seed warning: {e}")
    finally:
        db.close()


# ── FastAPI App ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_demo_data()
    logger.info("UTAP Demo Server started")
    yield
    logger.info("UTAP Demo Server stopped")


app = FastAPI(
    title="UTAP — Unit Test Artefact Portal (DEMO)",
    version="1.0.0",
    description="Live demo of UTAP. Authentication is bypassed — use any email to log in.",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key="utap-demo-secret-for-preview",
    https_only=False,
    same_site="lax",
)

COOKIE_NAME = "utap_session"

# ── Demo Auth Routes ─────────────────────────────────────────────────────────
from app.models.user_session import UserSession

DEMO_USERS = [
    {"email": "admin@utap.demo",    "name": "Admin User",    "role": "admin",           "display_name": "Admin User"},
    {"email": "developer@utap.demo","name": "Dev User",      "role": "developer",       "display_name": "Developer User"},
    {"email": "reviewer@utap.demo", "name": "Reviewer User", "role": "reviewer",        "display_name": "Reviewer User"},
    {"email": "release@utap.demo",  "name": "Release Mgr",   "role": "release_manager", "display_name": "Release Manager"},
]

@app.get("/api/v1/auth/login", response_class=HTMLResponse)
async def demo_login():
    """Demo login page — select a user role."""
    user_options = "".join([
        f'<a href="/api/v1/auth/demo-login?email={u["email"]}" class="user-card">'
        f'<div class="role">{u["role"].replace("_"," ").title()}</div>'
        f'<div class="email">{u["email"]}</div>'
        f'</a>'
        for u in DEMO_USERS
    ])
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>UTAP — Demo Login</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#1e3a8a 0%,#1e40af 50%,#2563eb 100%);min-height:100vh;display:flex;align-items:center;justify-content:center}}
  .card{{background:#fff;border-radius:20px;padding:40px;width:100%;max-width:480px;box-shadow:0 25px 60px rgba(0,0,0,0.3)}}
  .logo{{display:flex;align-items:center;gap:12px;margin-bottom:8px}}
  .logo-icon{{width:44px;height:44px;background:#2563eb;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:20px;font-weight:700}}
  h1{{font-size:22px;font-weight:700;color:#1e3a8a}}
  .subtitle{{color:#64748b;font-size:13px;margin-bottom:6px}}
  .demo-banner{{background:#fef3c7;border:1px solid #fcd34d;border-radius:10px;padding:12px 16px;margin:20px 0;font-size:12px;color:#92400e}}
  .demo-banner strong{{display:block;margin-bottom:2px}}
  h2{{font-size:14px;font-weight:600;color:#374151;margin-bottom:12px}}
  .users{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  .user-card{{display:block;padding:14px;border:2px solid #e2e8f0;border-radius:12px;text-decoration:none;transition:all 0.2s;cursor:pointer}}
  .user-card:hover{{border-color:#2563eb;background:#eff6ff;transform:translateY(-1px)}}
  .role{{font-size:13px;font-weight:600;color:#1e3a8a;margin-bottom:2px}}
  .email{{font-size:11px;color:#94a3b8}}
  .footer{{margin-top:20px;text-align:center;font-size:11px;color:#94a3b8}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">U</div>
    <div>
      <h1>UTAP</h1>
      <div class="subtitle">Unit Test Artefact Portal</div>
    </div>
  </div>
  <div class="demo-banner">
    <strong>🎯 Live Demo Mode</strong>
    SAML/Azure AD authentication is bypassed. Click any role below to log in instantly.
  </div>
  <h2>Select a demo user to log in:</h2>
  <div class="users">{user_options}</div>
  <div class="footer">Enterprise edition uses Azure AD SAML 2.0 SSO</div>
</div>
</body>
</html>""")


@app.get("/api/v1/auth/demo-login")
async def demo_login_as(email: str, db: Session = Depends(get_db)):
    """Instantly log in as a demo user."""
    user = next((u for u in DEMO_USERS if u["email"] == email), DEMO_USERS[0])
    token = str(uuid.uuid4())
    session = UserSession(
        id=uuid.uuid4(),
        session_token=token,
        user_email=user["email"],
        user_name=user["email"],
        display_name=user["display_name"],
        role=user["role"],
        azure_groups=[f"UTAP_{user['role'].title()}"],
        expires_at=datetime.utcnow() + timedelta(hours=8),
        last_activity_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key=COOKIE_NAME, value=token,
        httponly=True, secure=False, samesite="lax",
        max_age=28800,
    )
    return response


@app.get("/api/v1/auth/logout")
async def demo_logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.query(UserSession).filter(UserSession.session_token == token).first()
        if session:
            session.is_active = False
            db.commit()
    response = RedirectResponse(url="/api/v1/auth/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/api/v1/auth/me")
async def demo_me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
    ).first()
    if not session:
        return JSONResponse(status_code=401, content={"detail": "Session expired"})
    session.last_activity_at = datetime.utcnow()
    db.commit()
    return {
        "email": session.user_email,
        "name": session.user_name,
        "display_name": session.display_name,
        "role": session.role,
        "groups": session.azure_groups or [],
    }


# ── Override auth middleware for demo ────────────────────────────────────────
async def get_current_user_demo(request: Request, db: Session = Depends(get_db)):
    from fastapi import HTTPException, status
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = db.query(UserSession).filter(
        UserSession.session_token == token,
        UserSession.is_active == True,
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    session.last_activity_at = datetime.utcnow()
    db.commit()
    return {
        "session_id": str(session.id),
        "email": session.user_email,
        "name": session.user_name,
        "display_name": session.display_name,
        "role": session.role,
        "groups": session.azure_groups or [],
    }

# Patch the auth module
import app.middleware.auth as auth_module
auth_module.get_current_user = get_current_user_demo
auth_module.COOKIE_NAME = COOKIE_NAME


# ── Mount all API routers ────────────────────────────────────────────────────
from app.routers import (
    projects, releases, dev_activities,
    test_plans, test_cases, signoffs,
    dashboard, audit, export
)

# Evidence router with mocked S3
from app.routers import evidence as evidence_router

API = "/api/v1"
app.include_router(dashboard.router, prefix=API)
app.include_router(projects.router, prefix=API)
app.include_router(releases.router, prefix=API)
app.include_router(dev_activities.router, prefix=API)
app.include_router(test_plans.router, prefix=API)
app.include_router(test_cases.router, prefix=API)
app.include_router(evidence_router.router, prefix=API)
app.include_router(signoffs.router, prefix=API)
app.include_router(export.router, prefix=API)
app.include_router(audit.router, prefix=API)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "environment": "demo", "database": "sqlite"}


# ── Serve built frontend (SPA) ───────────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index = os.path.join(DIST, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return JSONResponse({"message": "Frontend not built yet. Run: npm run build in /frontend"})
else:
    @app.get("/")
    async def root():
        return RedirectResponse(url="/api/v1/auth/login")

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        if not full_path.startswith("api"):
            return RedirectResponse(url="/api/v1/auth/login")
        return JSONResponse({"detail": "Not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("demo_main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
