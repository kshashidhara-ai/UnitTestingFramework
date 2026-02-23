"""
UTAP Demo Server — self-contained SQLite + bypass auth.
Run: python demo_server.py
"""
import os, sys, uuid, json
from datetime import datetime, timedelta

os.environ.setdefault("ENVIRONMENT", "demo")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import structlog, logging
from contextlib import asynccontextmanager
from demo_models import (
    create_demo_db, Base, UserSession, Project, Release, DevelopmentActivity,
    TestPlan, TestCase, EvidenceArtefact, Signoff, AuditLog,
    EnvironmentScope, ReleaseStatus, ActivityType, TestPlanStatus, TestCaseStatus,
    TestCaseCategory, TestCaseComponent, ArtefactType, SignoffLevel, SignoffDecision, ActionType
)
from fastapi import FastAPI, Request, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import io

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "utap_demo.db")
engine, SessionLocal = create_demo_db(DB_PATH)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ── Logging ───────────────────────────────────────────────────────────────────
structlog.configure(
    processors=[structlog.processors.add_log_level, structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()
COOKIE_NAME = "utap_session"

DEMO_USERS = [
    {"email":"admin@utap.demo","display_name":"Admin User","role":"admin"},
    {"email":"developer@utap.demo","display_name":"Developer User","role":"developer"},
    {"email":"reviewer@utap.demo","display_name":"Reviewer User","role":"reviewer"},
    {"email":"release@utap.demo","display_name":"Release Manager","role":"release_manager"},
]
ROLE_HIERARCHY = ["developer","reviewer","release_manager","admin"]

# ── Auth helpers ──────────────────────────────────────────────────────────────
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token: raise HTTPException(401, "Not authenticated")
    sess = db.query(UserSession).filter(UserSession.session_token==token, UserSession.is_active==True).first()
    if not sess: raise HTTPException(401, "Session expired")
    if sess.expires_at < datetime.utcnow():
        sess.is_active = False; db.commit()
        raise HTTPException(401, "Session expired")
    sess.last_activity_at = datetime.utcnow(); db.commit()
    return {"email":sess.user_email,"display_name":sess.display_name,"role":sess.role,"groups":sess.azure_groups or []}

def require_role(*roles):
    async def _check(user=Depends(get_current_user)):
        for r in roles:
            if ROLE_HIERARCHY.index(user["role"]) >= ROLE_HIERARCHY.index(r):
                return user
        raise HTTPException(403, f"Need role: {roles}, have: {user['role']}")
    return _check

def audit(db, user_email, action, entity_type=None, entity_id=None, description=None, role=None, new_value=None):
    db.add(AuditLog(
        id=str(uuid.uuid4()), user_email=user_email, user_role=role,
        action_type=action, entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        description=description, new_value=new_value, timestamp=datetime.utcnow()
    )); db.commit()

# ── Seed data ─────────────────────────────────────────────────────────────────
def seed():
    db = SessionLocal()
    try:
        if db.query(Project).count() > 0: return
        p = Project(id=str(uuid.uuid4()), name="Sales_DWH", domain="Data Warehouse",
            description="Enterprise Sales Data Warehouse", owner_team="DWH Engineering",
            country="US", dataset="Sales", vendor="IQVIA", frequency="Weekly",
            is_active=True, created_by="admin@utap.demo")
        db.add(p); db.flush()
        r = Release(id=str(uuid.uuid4()), project_id=p.id, release_name="RLS_2026_02",
            description="February 2026 SIT Release", environment_scope="SIT",
            status="IN_PROGRESS", created_by="admin@utap.demo")
        db.add(r); db.flush()
        a = DevelopmentActivity(id=str(uuid.uuid4()), project_id=p.id, release_id=r.id,
            title="Sales Fact — New Metrics: Discount Amount & Net Revenue",
            activity_type="MIXED", jira_id="DWH-4521",
            snowflake_objects=json.dumps([{"database":"SALES_DWH","schema_name":"FACTS","object_name":"FACT_SALES","object_type":"TABLE"}]),
            iics_assets=json.dumps([{"org":"PROD_ORG","asset_type":"Mapping","asset_name":"M_SALES_FACT_LOAD"}]),
            created_by="admin@utap.demo")
        db.add(a); db.flush()
        plan = TestPlan(id=str(uuid.uuid4()), dev_activity_id=a.id,
            plan_name="TP-001: Sales Fact Table SIT Test Plan",
            scope="Validate DISCOUNT_AMOUNT and NET_REVENUE additions to FACT_SALES.",
            test_strategy="1. File ingestion validation\n2. IICS mapping execution\n3. Fact reconciliation\n4. MAT variance check\n5. Performance benchmark",
            status="DRAFT", evidence_completeness_score=37.5,
            created_by="developer@utap.demo")
        db.add(plan); db.flush()
        cases = [
            ("TC-001","DATA_QUALITY","SNOWFLAKE","Validate source file row count matches staging table","Source file loaded to stage",
             "1. Query source file row count\n2. SELECT COUNT(*) FROM STG_SALES\n3. Compare counts","STG count = source count","PASS",
             None,None,["01abc123-0001"],"COMPUTE_WH","SALES_DWH.STG.STG_SALES","SELECT COUNT(*) FROM STG.STG_SALES"),
            ("TC-002","DATA_QUALITY","SNOWFLAKE","Validate PSA audit columns populated after load","PSA load complete",
             "SELECT * FROM PSA_SALES WHERE LOAD_TIMESTAMP IS NULL","Zero NULL audit columns","PASS",
             None,None,["01abc123-0002"],"COMPUTE_WH","SALES_DWH.PSA.PSA_SALES","SELECT COUNT(*) FROM PSA_SALES WHERE LOAD_TIMESTAMP IS NULL"),
            ("TC-003","RECONCILIATION","SNOWFLAKE","Reconcile FACT_SALES totals against source system","DWH load complete",
             "SELECT SUM(NET_REVENUE) FROM FACT_SALES WHERE PERIOD='2026-02'\nCompare to source extract","Variance <= 0.01%","IN_PROGRESS",
             None,None,["01abc123-0003"],"COMPUTE_WH","SALES_DWH.FACTS.FACT_SALES","SELECT SUM(NET_REVENUE), SUM(DISCOUNT_AMOUNT) FROM FACT_SALES"),
            ("TC-004","INTEGRATION","IICS","IICS Taskflow TF_SALES_DWH_WEEKLY completes successfully","Taskflow deployed to SIT",
             "1. Trigger taskflow\n2. Monitor IICS Activity Monitor\n3. Verify all child tasks Success","Taskflow = Success, zero errors","NOT_RUN",
             None,None,None,None,None,None),
            ("TC-005","IDEMPOTENCY","BOTH","Re-run mapping produces identical results","Initial run completed",
             "1. Capture pre-rerun metrics\n2. Re-run pipeline\n3. Compare row counts\n4. Check for duplicates","Identical counts, zero duplicates","PASS",
             None,None,["01abc123-0005"],"COMPUTE_WH","SALES_DWH.FACTS.FACT_SALES","SELECT COUNT(*) FROM FACT_SALES — pre and post match"),
            ("TC-006","PERFORMANCE","SNOWFLAKE","Query executes within 60s SLA on MEDIUM warehouse","Warehouse sized to MEDIUM",
             "1. Execute fact load query\n2. Capture QUERY_ID\n3. Check TOTAL_ELAPSED_TIME in QUERY_HISTORY","Execution <= 60s","FAIL",
             "DWH-4523","Performance regression — 87s on MEDIUM, need LARGE warehouse",["01abc123-0006"],"COMPUTE_WH_M","SALES_DWH.FACTS.FACT_SALES","INSERT INTO FACT_SALES SELECT ..."),
            ("TC-007","DATA_QUALITY","SNOWFLAKE","MAT variance within 10% threshold vs prior period","MAT refresh complete",
             "SELECT metric, variance_pct FROM MAT_RECONCILIATION_VIEW WHERE variance_pct > 0.10","All metrics within 10% variance","NOT_RUN",
             None,None,None,"COMPUTE_WH","SALES_DWH.MATS.MAT_WEEKLY_REVENUE",None),
            ("TC-008","REGRESSION","SNOWFLAKE","Existing metrics unchanged after schema change","Schema migration applied",
             "Compare REVENUE, UNITS_SOLD totals before/after migration","All existing metrics match baseline","NOT_RUN",
             None,None,None,"COMPUTE_WH","SALES_DWH.FACTS.FACT_SALES",None),
        ]
        for tc_id,cat,comp,obj,pre,steps,exp,stat,defect,comment,qids,wh,dso,sql in cases:
            tc = TestCase(
                id=str(uuid.uuid4()), test_plan_id=plan.id, testcase_id=tc_id,
                category=cat, component=comp, objective=obj, preconditions=pre,
                test_steps=steps, expected_result=exp, status=stat,
                defect_reference=defect, reviewer_comment=comment,
                snowflake_query_ids=json.dumps(qids) if qids else None,
                snowflake_warehouse=wh, snowflake_database_schema_object=dso, sql_executed=sql,
                executed_by="developer@utap.demo" if stat in ("PASS","FAIL","IN_PROGRESS") else None,
                executed_at=datetime.utcnow() if stat in ("PASS","FAIL") else None,
                iics_org="PROD_ORG" if comp in ("IICS","BOTH") else None,
                iics_asset_name="TF_SALES_DWH_WEEKLY" if comp in ("IICS","BOTH") else None,
                created_by="developer@utap.demo"
            )
            db.add(tc)
        # Add second project for variety
        p2 = Project(id=str(uuid.uuid4()), name="Finance_ETL", domain="Finance",
            description="Finance ETL pipelines", owner_team="Finance Engineering",
            country="UK", dataset="Finance", vendor="Circana", frequency="Monthly",
            is_active=True, created_by="admin@utap.demo")
        db.add(p2)
        db.commit()
        print("✓ Demo data seeded")
    except Exception as e:
        db.rollback(); print(f"Seed warning: {e}")
    finally:
        db.close()

# ── App ───────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    logger.info("UTAP Demo started", db=DB_PATH)
    yield

app = FastAPI(title="UTAP — Unit Test Artefact Portal",version="1.0.0",
    description="Demo: SAML bypassed. Click any role to log in.",
    openapi_url="/api/openapi.json", docs_url="/api/docs", redoc_url="/api/redoc",
    lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key="utap-demo-key", https_only=False, same_site="lax")

# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.get("/api/v1/auth/login", response_class=HTMLResponse)
async def login_page():
    cards = "".join([f'<a href="/api/v1/auth/demo-login?email={u["email"]}" class="card"><div class="role">{u["role"].replace("_"," ").title()}</div><div class="email">{u["email"]}</div></a>' for u in DEMO_USERS])
    return HTMLResponse(f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UTAP Login</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:Inter,sans-serif;background:linear-gradient(135deg,#1e3a8a,#1d4ed8,#2563eb);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.wrap{{background:#fff;border-radius:20px;padding:40px;max-width:460px;width:100%;box-shadow:0 30px 70px rgba(0,0,0,.3)}}
.head{{display:flex;align-items:center;gap:14px;margin-bottom:6px}}
.logo{{width:48px;height:48px;background:#1d4ed8;border-radius:14px;display:grid;place-items:center;color:#fff;font-size:22px;font-weight:800}}
h1{{font-size:24px;font-weight:700;color:#1e3a8a}}.sub{{color:#64748b;font-size:13px;margin-bottom:4px}}
.banner{{background:#fef9c3;border:1px solid #fde047;border-radius:10px;padding:12px 16px;margin:18px 0;font-size:12px;color:#713f12}}
.banner b{{display:block;margin-bottom:3px;font-size:13px}}
h2{{font-size:13px;font-weight:600;color:#475569;margin-bottom:10px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{display:block;padding:14px 16px;border:2px solid #e2e8f0;border-radius:12px;text-decoration:none;transition:.15s}}
.card:hover{{border-color:#1d4ed8;background:#eff6ff;transform:translateY(-2px);box-shadow:0 4px 12px rgba(29,78,216,.15)}}
.role{{font-weight:600;font-size:13px;color:#1e3a8a;margin-bottom:3px}}.email{{font-size:11px;color:#94a3b8}}
.footer{{margin-top:20px;font-size:11px;color:#94a3b8;text-align:center}}</style></head>
<body><div class="wrap"><div class="head"><div class="logo">U</div><div><h1>UTAP</h1><div class="sub">Unit Test Artefact Portal</div></div></div>
<div class="banner"><b>🎯 Live Demo Mode</b>Azure AD SAML 2.0 SSO bypassed for preview. Select a role to log in instantly.</div>
<h2>Choose a demo account:</h2><div class="grid">{cards}</div>
<div class="footer">Production uses Azure AD SAML 2.0 with group-based RBAC</div></div></body></html>""")

@app.get("/api/v1/auth/demo-login")
async def demo_login(email: str, db: Session = Depends(get_db)):
    user = next((u for u in DEMO_USERS if u["email"] == email), DEMO_USERS[1])
    token = str(uuid.uuid4())
    db.add(UserSession(id=str(uuid.uuid4()), session_token=token, user_email=user["email"],
        user_name=user["email"], display_name=user["display_name"], role=user["role"],
        azure_groups=json.dumps([f"UTAP_{user['role'].title()}"]),
        is_active=True, expires_at=datetime.utcnow()+timedelta(hours=8), last_activity_at=datetime.utcnow()))
    db.commit()
    audit(db, user["email"], "LOGIN", description=f"Demo login as {user['role']}", role=user["role"])
    r = RedirectResponse("/", status_code=302)
    r.set_cookie(COOKIE_NAME, token, httponly=True, secure=False, samesite="lax", max_age=28800)
    return r

@app.get("/api/v1/auth/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    t = request.cookies.get(COOKIE_NAME)
    if t:
        s = db.query(UserSession).filter_by(session_token=t).first()
        if s: s.is_active = False; db.commit()
    r = RedirectResponse("/api/v1/auth/login", status_code=302)
    r.delete_cookie(COOKIE_NAME); return r

@app.get("/api/v1/auth/me")
async def me(user=Depends(get_current_user)):
    return user

# ── Dashboard ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/dashboard/summary")
async def dashboard_summary(db: Session = Depends(get_db), user=Depends(get_current_user)):
    tc_stats = db.query(TestCase.status, func.count(TestCase.id)).group_by(TestCase.status).all()
    tc = {s: c for s, c in tc_stats}
    total = sum(tc.values()); passed = tc.get("PASS",0)
    plan_stats = db.query(TestPlan.status, func.count(TestPlan.id)).group_by(TestPlan.status).all()
    return {"my_test_plans": db.query(TestPlan).filter(TestPlan.created_by==user["email"]).count(),
        "pending_reviews": db.query(TestPlan).filter(TestPlan.status=="IN_REVIEW").count(),
        "pending_signoffs": db.query(Signoff).filter(Signoff.decision=="PENDING").count(),
        "active_projects": db.query(Project).filter(Project.is_active==True).count(),
        "test_case_stats": {"total":total,"pass":passed,"fail":tc.get("FAIL",0),"not_run":tc.get("NOT_RUN",0),
            "blocked":tc.get("BLOCKED",0),"waived":tc.get("WAIVED",0),
            "pass_rate": round(passed/total*100,1) if total else 0},
        "test_plan_stats": {s: c for s, c in plan_stats}}

@app.get("/api/v1/dashboard/my-plans")
async def my_plans(db: Session = Depends(get_db), user=Depends(get_current_user)):
    plans = db.query(TestPlan).filter(TestPlan.created_by==user["email"]).order_by(TestPlan.updated_at.desc()).limit(10).all()
    out = []
    for p in plans:
        cases = db.query(TestCase).filter(TestCase.test_plan_id==p.id).all()
        out.append({"id":p.id,"plan_name":p.plan_name,"status":p.status,
            "evidence_completeness_score":p.evidence_completeness_score,"is_locked":p.is_locked,
            "created_at":p.created_at.isoformat(),"test_case_count":len(cases),
            "pass_count":sum(1 for c in cases if c.status=="PASS"),"fail_count":sum(1 for c in cases if c.status=="FAIL")})
    return out

# ── Projects ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/projects")
async def list_projects(page:int=1, page_size:int=20, search:str=None, country:str=None,
        db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(Project).filter(Project.is_active==True)
    if search: q = q.filter(or_(Project.name.ilike(f"%{search}%"), Project.domain.ilike(f"%{search}%")))
    if country: q = q.filter(Project.country==country)
    total = q.count()
    items = q.offset((page-1)*page_size).limit(page_size).all()
    return {"items":[_proj(p) for p in items],"total":total,"page":page,"page_size":page_size}

@app.post("/api/v1/projects", status_code=201)
async def create_project(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    p = Project(id=str(uuid.uuid4()), created_by=user["email"], **{k:v for k,v in data.items() if k not in ("id","created_by","created_at","updated_at")})
    db.add(p); db.commit(); db.refresh(p)
    audit(db, user["email"], "CREATE", "Project", p.id, f"Created project: {p.name}", user["role"])
    return _proj(p)

@app.get("/api/v1/projects/{pid}")
async def get_project(pid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    p = db.query(Project).filter(Project.id==pid).first()
    if not p: raise HTTPException(404,"Not found")
    return _proj(p)

@app.patch("/api/v1/projects/{pid}")
async def update_project(pid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    p = db.query(Project).filter(Project.id==pid).first()
    if not p: raise HTTPException(404,"Not found")
    for k,v in data.items():
        if hasattr(p,k): setattr(p,k,v)
    db.commit(); db.refresh(p); return _proj(p)

def _proj(p): return {"id":p.id,"name":p.name,"domain":p.domain,"description":p.description,
    "owner_team":p.owner_team,"country":p.country,"dataset":p.dataset,"vendor":p.vendor,
    "frequency":p.frequency,"is_active":p.is_active,"created_by":p.created_by,
    "created_at":p.created_at.isoformat() if p.created_at else None,
    "updated_at":p.updated_at.isoformat() if p.updated_at else None}

# ── Releases ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/releases")
async def list_releases(project_id:str=None, db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(Release)
    if project_id: q = q.filter(Release.project_id==project_id)
    return [_rel(r) for r in q.order_by(Release.created_at.desc()).all()]

@app.post("/api/v1/releases", status_code=201)
async def create_release(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    r = Release(id=str(uuid.uuid4()), created_by=user["email"], **{k:v for k,v in data.items() if k not in ("id","created_by")})
    db.add(r); db.commit(); db.refresh(r); return _rel(r)

@app.get("/api/v1/releases/{rid}")
async def get_release(rid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    r = db.query(Release).filter(Release.id==rid).first()
    if not r: raise HTTPException(404,"Not found")
    return _rel(r)

@app.patch("/api/v1/releases/{rid}")
async def update_release(rid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    r = db.query(Release).filter(Release.id==rid).first()
    if not r: raise HTTPException(404,"Not found")
    for k,v in data.items():
        if hasattr(r,k): setattr(r,k,v)
    db.commit(); db.refresh(r); return _rel(r)

def _rel(r): return {"id":r.id,"project_id":r.project_id,"release_name":r.release_name,
    "description":r.description,"environment_scope":r.environment_scope,"status":r.status,
    "planned_deploy_date":str(r.planned_deploy_date) if r.planned_deploy_date else None,
    "actual_deploy_date":str(r.actual_deploy_date) if r.actual_deploy_date else None,
    "created_by":r.created_by,"created_at":r.created_at.isoformat() if r.created_at else None,
    "updated_at":r.updated_at.isoformat() if r.updated_at else None}

# ── Dev Activities ────────────────────────────────────────────────────────────
@app.get("/api/v1/dev-activities")
async def list_activities(project_id:str=None, release_id:str=None, db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DevelopmentActivity)
    if project_id: q=q.filter(DevelopmentActivity.project_id==project_id)
    if release_id: q=q.filter(DevelopmentActivity.release_id==release_id)
    return [_act(a) for a in q.order_by(DevelopmentActivity.created_at.desc()).all()]

@app.post("/api/v1/dev-activities", status_code=201)
async def create_activity(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    for k in ("snowflake_objects","iics_assets"):
        if k in data and isinstance(data[k], (list,dict)): data[k] = json.dumps(data[k])
    a = DevelopmentActivity(id=str(uuid.uuid4()), created_by=user["email"], **{k:v for k,v in data.items() if k not in ("id","created_by")})
    db.add(a); db.commit(); db.refresh(a); return _act(a)

@app.get("/api/v1/dev-activities/{aid}")
async def get_activity(aid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    a = db.query(DevelopmentActivity).filter(DevelopmentActivity.id==aid).first()
    if not a: raise HTTPException(404,"Not found")
    return _act(a)

@app.patch("/api/v1/dev-activities/{aid}")
async def update_activity(aid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    a = db.query(DevelopmentActivity).filter(DevelopmentActivity.id==aid).first()
    if not a: raise HTTPException(404,"Not found")
    for k,v in data.items():
        if hasattr(a,k): setattr(a, k, json.dumps(v) if k in ("snowflake_objects","iics_assets") and isinstance(v,(list,dict)) else v)
    db.commit(); db.refresh(a); return _act(a)

def _parse_json(v):
    if isinstance(v, str):
        try: return json.loads(v)
        except: return v
    return v

def _act(a): return {"id":a.id,"project_id":a.project_id,"release_id":a.release_id,
    "title":a.title,"description":a.description,"activity_type":a.activity_type,
    "jira_id":a.jira_id,"git_repo":a.git_repo,"pr_link":a.pr_link,"commit_hash":a.commit_hash,
    "snowflake_objects":_parse_json(a.snowflake_objects),"iics_assets":_parse_json(a.iics_assets),
    "created_by":a.created_by,"created_at":a.created_at.isoformat() if a.created_at else None,
    "updated_at":a.updated_at.isoformat() if a.updated_at else None}

# ── Test Plans ────────────────────────────────────────────────────────────────
def _completeness(db, plan_id):
    total = db.query(TestCase).filter(TestCase.test_plan_id==plan_id).count()
    if not total: return 0.0
    with_ev = db.query(TestCase).filter(TestCase.test_plan_id==plan_id).filter(
        or_(TestCase.status=="WAIVED",
            TestCase.id.in_(db.query(EvidenceArtefact.test_case_id).filter(EvidenceArtefact.test_case_id!=None).distinct()))
    ).count()
    return round(with_ev/total*100, 1)

def _plan_dict(plan, db):
    cases = db.query(TestCase).filter(TestCase.test_plan_id==plan.id).all()
    return {"id":plan.id,"dev_activity_id":plan.dev_activity_id,"plan_name":plan.plan_name,
        "scope":plan.scope,"test_strategy":plan.test_strategy,"entry_criteria":plan.entry_criteria,
        "exit_criteria":plan.exit_criteria,"status":plan.status,
        "evidence_completeness_score":plan.evidence_completeness_score,"is_locked":plan.is_locked,
        "lock_override_reason":plan.lock_override_reason,
        "submitted_for_review_at":plan.submitted_for_review_at.isoformat() if plan.submitted_for_review_at else None,
        "created_by":plan.created_by,"created_at":plan.created_at.isoformat() if plan.created_at else None,
        "updated_at":plan.updated_at.isoformat() if plan.updated_at else None,
        "last_autosave_at":plan.last_autosave_at.isoformat() if plan.last_autosave_at else None,
        "test_case_count":len(cases),"pass_count":sum(1 for c in cases if c.status=="PASS"),
        "fail_count":sum(1 for c in cases if c.status=="FAIL"),
        "not_run_count":sum(1 for c in cases if c.status=="NOT_RUN")}

@app.get("/api/v1/test-plans")
async def list_plans(dev_activity_id:str=None, status:str=None, created_by:str=None,
        page:int=1, page_size:int=20, db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(TestPlan)
    if dev_activity_id: q=q.filter(TestPlan.dev_activity_id==dev_activity_id)
    if status: q=q.filter(TestPlan.status==status)
    if created_by: q=q.filter(TestPlan.created_by==created_by)
    plans = q.order_by(TestPlan.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return [_plan_dict(p, db) for p in plans]

@app.post("/api/v1/test-plans", status_code=201)
async def create_plan(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    plan = TestPlan(id=str(uuid.uuid4()), created_by=user["email"], status="DRAFT",
        evidence_completeness_score=0.0, **{k:v for k,v in data.items() if k not in ("id","created_by","status","evidence_completeness_score")})
    db.add(plan); db.commit(); db.refresh(plan)
    audit(db, user["email"], "CREATE", "TestPlan", plan.id, f"Created: {plan.plan_name}", user["role"])
    return _plan_dict(plan, db)

@app.get("/api/v1/test-plans/{pid}")
async def get_plan(pid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
    if not plan: raise HTTPException(404,"Not found")
    plan.evidence_completeness_score = _completeness(db, pid); db.commit()
    return _plan_dict(plan, db)

@app.patch("/api/v1/test-plans/{pid}")
async def update_plan(pid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
    if not plan: raise HTTPException(404,"Not found")
    if plan.is_locked: raise HTTPException(423,"Plan is locked")
    for k,v in data.items():
        if hasattr(plan,k): setattr(plan,k,v)
    plan.last_autosave_at = datetime.utcnow(); db.commit(); db.refresh(plan)
    return _plan_dict(plan, db)

@app.post("/api/v1/test-plans/{pid}/submit-review")
async def submit_review(pid:str, data:dict={}, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
    if not plan: raise HTTPException(404,"Not found")
    if plan.is_locked: raise HTTPException(423,"Locked")
    cases = db.query(TestCase).filter(TestCase.test_plan_id==pid).all()
    not_run = [c for c in cases if c.status=="NOT_RUN"]
    if not_run: raise HTTPException(422,f"{len(not_run)} cases still NOT_RUN")
    fail_no_defect = [c for c in cases if c.status=="FAIL" and not c.defect_reference]
    if fail_no_defect: raise HTTPException(422,f"{len(fail_no_defect)} FAIL cases missing defect reference")
    comp = _completeness(db, pid)
    if comp < 90.0: raise HTTPException(422,f"Evidence completeness {comp}% < 90% threshold")
    plan.status = "IN_REVIEW"; plan.evidence_completeness_score = comp
    plan.submitted_for_review_at = datetime.utcnow(); db.commit()
    audit(db, user["email"], "STATUS_CHANGE", "TestPlan", pid, "Submitted for review", user["role"], {"status":"IN_REVIEW"})
    return _plan_dict(plan, db)

@app.post("/api/v1/test-plans/{pid}/lock-override")
async def lock_override(pid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("admin"))):
    plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
    if not plan: raise HTTPException(404,"Not found")
    plan.is_locked=False; plan.lock_override_reason=data.get("reason",""); db.commit()
    audit(db, user["email"], "LOCK_OVERRIDE", "TestPlan", pid, data.get("reason"), user["role"])
    return _plan_dict(plan, db)

# ── Test Cases ────────────────────────────────────────────────────────────────
def _tc_dict(tc, db):
    ev = db.query(EvidenceArtefact).filter(EvidenceArtefact.test_case_id==tc.id).count()
    d = {c.name: getattr(tc,c.name) for c in tc.__table__.columns}
    for k in ("snowflake_query_ids","iics_run_ids"):
        if isinstance(d.get(k), str):
            try: d[k] = json.loads(d[k])
            except: d[k] = []
    for k, v in d.items():
        if isinstance(v, datetime): d[k] = v.isoformat()
    d["evidence_count"] = ev
    return d

@app.get("/api/v1/test-cases")
async def list_cases(test_plan_id:str=None, status:str=None, component:str=None, search:str=None,
        page:int=1, page_size:int=50, db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(TestCase)
    if test_plan_id: q=q.filter(TestCase.test_plan_id==test_plan_id)
    if status: q=q.filter(TestCase.status==status)
    if component: q=q.filter(TestCase.component==component)
    if search: q=q.filter(or_(TestCase.objective.ilike(f"%{search}%"), TestCase.testcase_id.ilike(f"%{search}%")))
    return [_tc_dict(tc, db) for tc in q.order_by(TestCase.testcase_id).offset((page-1)*page_size).limit(page_size).all()]

@app.post("/api/v1/test-cases", status_code=201)
async def create_case(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    plan = db.query(TestPlan).filter(TestPlan.id==data.get("test_plan_id")).first()
    if not plan: raise HTTPException(404,"Plan not found")
    if plan.is_locked: raise HTTPException(423,"Plan is locked")
    for k in ("snowflake_query_ids","iics_run_ids"):
        if k in data and isinstance(data[k], list): data[k] = json.dumps(data[k])
    tc = TestCase(id=str(uuid.uuid4()), created_by=user["email"], status="NOT_RUN",
        **{k:v for k,v in data.items() if k not in ("id","created_by","status","evidence_count")})
    db.add(tc); db.commit(); db.refresh(tc); return _tc_dict(tc, db)

@app.get("/api/v1/test-cases/{cid}")
async def get_case(cid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    tc = db.query(TestCase).filter(TestCase.id==cid).first()
    if not tc: raise HTTPException(404,"Not found")
    return _tc_dict(tc, db)

@app.patch("/api/v1/test-cases/{cid}")
async def update_case(cid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    tc = db.query(TestCase).filter(TestCase.id==cid).first()
    if not tc: raise HTTPException(404,"Not found")
    plan = db.query(TestPlan).filter(TestPlan.id==tc.test_plan_id).first()
    if plan and plan.is_locked: raise HTTPException(423,"Plan is locked")
    new_status = data.get("status")
    if new_status == "PASS":
        ev = db.query(EvidenceArtefact).filter(EvidenceArtefact.test_case_id==cid).count()
        if ev == 0 and not tc.waiver_reason and not data.get("waiver_reason"):
            raise HTTPException(422,"PASS requires evidence or waiver")
    if new_status == "FAIL":
        if not data.get("defect_reference") and not tc.defect_reference and not data.get("reviewer_comment") and not tc.reviewer_comment:
            raise HTTPException(422,"FAIL requires defect reference or reviewer comment")
    old_status = tc.status
    for k,v in data.items():
        if hasattr(tc,k):
            setattr(tc, k, json.dumps(v) if k in ("snowflake_query_ids","iics_run_ids") and isinstance(v,list) else v)
    if new_status in ("PASS","FAIL","BLOCKED"):
        if not tc.executed_at: tc.executed_at = datetime.utcnow()
        if not tc.executed_by: tc.executed_by = user["email"]
    db.commit(); db.refresh(tc)
    if new_status and new_status != old_status:
        audit(db, user["email"], "STATUS_CHANGE", "TestCase", tc.id, f"{old_status}→{new_status}", user["role"])
    return _tc_dict(tc, db)

@app.delete("/api/v1/test-cases/{cid}", status_code=204)
async def delete_case(cid:str, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    tc = db.query(TestCase).filter(TestCase.id==cid).first()
    if not tc: raise HTTPException(404,"Not found")
    db.delete(tc); db.commit()

@app.post("/api/v1/test-cases/bulk-import", status_code=201)
async def bulk_import(test_plan_id:str, file:UploadFile=File(...), db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    import csv, io
    plan = db.query(TestPlan).filter(TestPlan.id==test_plan_id).first()
    if not plan: raise HTTPException(404,"Plan not found")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    created = 0; errors = []
    for i, row in enumerate(reader, 2):
        try:
            tc = TestCase(id=str(uuid.uuid4()), test_plan_id=test_plan_id,
                testcase_id=row.get("testcase_id",f"TC-{i:03d}"), category=row.get("category","FUNCTIONAL"),
                component=row.get("component","SNOWFLAKE"), objective=row.get("objective",""),
                preconditions=row.get("preconditions"), test_steps=row.get("test_steps",""),
                expected_result=row.get("expected_result",""), created_by=user["email"])
            db.add(tc); created += 1
        except Exception as e:
            errors.append({"row":i,"error":str(e)})
    db.commit()
    audit(db, user["email"], "BULK_IMPORT", "TestCase", test_plan_id, f"Imported {created} cases", user["role"])
    return {"created":created,"errors":errors}

# ── Evidence ──────────────────────────────────────────────────────────────────
def _ev_dict(e):
    d = {c.name: getattr(e,c.name) for c in e.__table__.columns}
    for k,v in d.items():
        if isinstance(v, datetime): d[k] = v.isoformat()
    if isinstance(d.get("metadata_json"), str):
        try: d["metadata_json"] = json.loads(d["metadata_json"])
        except: pass
    d["is_legal_hold"] = bool(d.get("is_legal_hold",False))
    return d

@app.post("/api/v1/evidence/presigned-upload")
async def presigned_upload(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    """Demo: returns a fake presigned URL (no real S3)."""
    obj_key = f"demo/{data.get('artefact_type','OTHER')}/{uuid.uuid4().hex[:8]}_{data.get('filename','file')}"
    return {"upload_url":"/api/v1/evidence/demo-upload", "s3_object_key":obj_key,
        "s3_bucket":"utap-demo","fields":{"key":obj_key},"expires_in":3600}

@app.post("/api/v1/evidence/demo-upload")
async def demo_upload(request:Request):
    """Demo stub — accepts any file upload."""
    return JSONResponse({"ok":True})

@app.post("/api/v1/evidence", status_code=201)
async def register_evidence(data:dict, db:Session=Depends(get_db), user=Depends(require_role("developer"))):
    if isinstance(data.get("metadata_json"),(dict,list)): data["metadata_json"] = json.dumps(data["metadata_json"])
    e = EvidenceArtefact(id=str(uuid.uuid4()), uploaded_by=user["email"],
        **{k:v for k,v in data.items() if k not in ("id","uploaded_by","uploaded_at","is_legal_hold")})
    db.add(e); db.commit(); db.refresh(e)
    audit(db, user["email"], "ARTEFACT_UPLOAD", "EvidenceArtefact", e.id, e.original_filename, user["role"])
    return _ev_dict(e)

@app.get("/api/v1/evidence")
async def list_evidence(test_case_id:str=None, test_plan_id:str=None, artefact_type:str=None,
        uploaded_by:str=None, page:int=1, page_size:int=20, db:Session=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(EvidenceArtefact)
    if test_case_id: q=q.filter(EvidenceArtefact.test_case_id==test_case_id)
    if test_plan_id: q=q.filter(EvidenceArtefact.test_plan_id==test_plan_id)
    if artefact_type: q=q.filter(EvidenceArtefact.artefact_type==artefact_type)
    if uploaded_by: q=q.filter(EvidenceArtefact.uploaded_by==uploaded_by)
    return [_ev_dict(e) for e in q.order_by(EvidenceArtefact.uploaded_at.desc()).offset((page-1)*page_size).limit(page_size).all()]

@app.get("/api/v1/evidence/{eid}/download")
async def evidence_download(eid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    e = db.query(EvidenceArtefact).filter(EvidenceArtefact.id==eid).first()
    if not e: raise HTTPException(404,"Not found")
    audit(db, user["email"], "ARTEFACT_DOWNLOAD", "EvidenceArtefact", eid, e.original_filename, user["role"])
    return {"download_url":f"/api/v1/evidence/{eid}/demo-download","expires_in":3600,"filename":e.original_filename}

@app.delete("/api/v1/evidence/{eid}", status_code=204)
async def delete_evidence(eid:str, db:Session=Depends(get_db), user=Depends(require_role("admin"))):
    e = db.query(EvidenceArtefact).filter(EvidenceArtefact.id==eid).first()
    if not e: raise HTTPException(404,"Not found")
    db.delete(e); db.commit()

# ── Signoffs ──────────────────────────────────────────────────────────────────
def _so_dict(s):
    return {"id":s.id,"test_plan_id":s.test_plan_id,"level":s.level,"decision":s.decision,
        "comments":s.comments,"rejection_reason":s.rejection_reason,"signed_by":s.signed_by,
        "signed_by_name":s.signed_by_name,"signed_at":s.signed_at.isoformat() if s.signed_at else None,
        "requested_at":s.requested_at.isoformat() if s.requested_at else None,"requested_by":s.requested_by}

@app.get("/api/v1/signoffs")
async def list_signoffs(test_plan_id:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    return [_so_dict(s) for s in db.query(Signoff).filter(Signoff.test_plan_id==test_plan_id).all()]

@app.post("/api/v1/signoffs", status_code=201)
async def request_signoff(data:dict, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    plan = db.query(TestPlan).filter(TestPlan.id==data.get("test_plan_id")).first()
    if not plan: raise HTTPException(404,"Plan not found")
    if plan.status not in ("IN_REVIEW","APPROVED"): raise HTTPException(400,"Plan must be IN_REVIEW")
    s = Signoff(id=str(uuid.uuid4()), requested_by=user["email"], decision="PENDING", **{k:v for k,v in data.items() if k not in ("id","decision","requested_by")})
    db.add(s); db.commit(); db.refresh(s); return _so_dict(s)

@app.post("/api/v1/signoffs/{sid}/decide")
async def decide_signoff(sid:str, data:dict, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    s = db.query(Signoff).filter(Signoff.id==sid).first()
    if not s: raise HTTPException(404,"Not found")
    if s.decision != "PENDING": raise HTTPException(400,"Already decided")
    if data.get("decision")=="REJECTED" and not data.get("rejection_reason"):
        raise HTTPException(422,"Rejection reason required")
    s.decision=data["decision"]; s.comments=data.get("comments"); s.rejection_reason=data.get("rejection_reason")
    s.signed_by=user["email"]; s.signed_by_name=user.get("display_name"); s.signed_at=datetime.utcnow()
    plan = db.query(TestPlan).filter(TestPlan.id==s.test_plan_id).first()
    if s.level=="RELEASE" and data["decision"]=="APPROVED" and plan:
        plan.status="LOCKED"; plan.is_locked=True
    if data["decision"]=="REJECTED" and plan: plan.status="REJECTED"
    db.commit()
    audit(db, user["email"], "SIGNOFF", "Signoff", sid, f"{s.level} {data['decision']}", user["role"])
    db.refresh(s); return _so_dict(s)

# ── Export ────────────────────────────────────────────────────────────────────
@app.get("/api/v1/export/test-plan/{pid}/csv")
async def export_csv(pid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    import csv, io
    cases = db.query(TestCase).filter(TestCase.test_plan_id==pid).all()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["testcase_id","category","component","objective","status","executed_by","defect_reference"])
    w.writeheader()
    for tc in cases: w.writerow({"testcase_id":tc.testcase_id,"category":tc.category,"component":tc.component,"objective":tc.objective,"status":tc.status,"executed_by":tc.executed_by or "","defect_reference":tc.defect_reference or ""})
    audit(db, user["email"], "EXPORT", "TestPlan", pid, "CSV export", user["role"])
    return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv", headers={"Content-Disposition":f'attachment; filename="UTAP_{pid[:8]}_cases.csv"'})

@app.get("/api/v1/export/test-plan/{pid}/pdf")
async def export_pdf(pid:str, db:Session=Depends(get_db), user=Depends(get_current_user)):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
        if not plan: raise HTTPException(404,"Not found")
        cases = db.query(TestCase).filter(TestCase.test_plan_id==pid).all()
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"UTAP Evidence Report — {plan.plan_name}", styles["Title"]),
            Spacer(1,12), Paragraph(f"Status: {plan.status} | Completeness: {plan.evidence_completeness_score:.1f}%", styles["Normal"]),
            Spacer(1,12)]
        data = [["TC ID","Category","Component","Status","Executed By"]] + \
            [[tc.testcase_id,tc.category,tc.component,tc.status,tc.executed_by or "—"] for tc in cases]
        t = Table(data)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1d4ed8")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.5,colors.grey)]))
        story.append(t)
        doc.build(story)
        audit(db, user["email"], "EXPORT", "TestPlan", pid, "PDF export", user["role"])
        return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/pdf", headers={"Content-Disposition":f'attachment; filename="UTAP_{pid[:8]}_report.pdf"'})
    except ImportError:
        raise HTTPException(501,"ReportLab not installed")

@app.get("/api/v1/export/test-plan/{pid}/zip")
async def export_zip(pid:str, db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    import zipfile, csv
    plan = db.query(TestPlan).filter(TestPlan.id==pid).first()
    if not plan: raise HTTPException(404,"Not found")
    cases = db.query(TestCase).filter(TestCase.test_plan_id==pid).all()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        csv_buf = io.StringIO()
        w = csv.DictWriter(csv_buf, fieldnames=["testcase_id","category","component","objective","status","executed_by"])
        w.writeheader()
        for tc in cases: w.writerow({"testcase_id":tc.testcase_id,"category":tc.category,"component":tc.component,"objective":tc.objective,"status":tc.status,"executed_by":tc.executed_by or ""})
        zf.writestr(f"test_cases_{pid[:8]}.csv", csv_buf.getvalue())
        zf.writestr(f"metadata_{pid[:8]}.json", json.dumps({"plan_id":pid,"plan_name":plan.plan_name,"status":plan.status,"exported_by":user["email"],"export_time":datetime.utcnow().isoformat(),"total_cases":len(cases)},indent=2))
    audit(db, user["email"], "EXPORT", "TestPlan", pid, "ZIP export", user["role"])
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/zip", headers={"Content-Disposition":f'attachment; filename="UTAP_{pid[:8]}_evidence_pack.zip"'})

# ── Audit log ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/audit")
async def get_audit(user_email:str=None, action_type:str=None, entity_type:str=None, page:int=1, page_size:int=50,
        db:Session=Depends(get_db), user=Depends(require_role("reviewer"))):
    q = db.query(AuditLog)
    if user_email: q=q.filter(AuditLog.user_email==user_email)
    if action_type: q=q.filter(AuditLog.action_type==action_type)
    if entity_type: q=q.filter(AuditLog.entity_type==entity_type)
    total = q.count()
    items = q.order_by(AuditLog.timestamp.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {"total":total,"page":page,"page_size":page_size,"items":[{
        "id":a.id,"user_email":a.user_email,"user_role":a.user_role,"action_type":a.action_type,
        "entity_type":a.entity_type,"entity_id":a.entity_id,"description":a.description,
        "timestamp":a.timestamp.isoformat(),"ip_address":a.ip_address} for a in items]}

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status":"healthy","version":"1.0.0","environment":"demo","database":"sqlite"}

# ── Serve React SPA ──────────────────────────────────────────────────────────
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
if os.path.isdir(DIST):
    ASSETS = os.path.join(DIST, "assets")
    if os.path.isdir(ASSETS):
        app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        if full_path.startswith("api/"): return JSONResponse({"detail":"Not found"},404)
        idx = os.path.join(DIST,"index.html")
        return FileResponse(idx) if os.path.exists(idx) else JSONResponse({"message":"Frontend not built"},404)
else:
    @app.get("/{full_path:path}")
    async def catch(full_path: str):
        if not full_path.startswith("api"): return RedirectResponse("/api/v1/auth/login")
        return JSONResponse({"detail":"Not found"},404)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n{'='*55}")
    print(f"  UTAP Demo Server starting on port {port}")
    print(f"  DB: {DB_PATH}")
    print(f"  Frontend: {'found' if os.path.isdir(DIST) else 'not found'}")
    print(f"{'='*55}\n")
    uvicorn.run("demo_server:app", host="0.0.0.0", port=port, reload=False, log_level="warning")
