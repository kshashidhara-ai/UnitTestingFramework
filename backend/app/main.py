"""
Unit Test Artefact Portal (UTAP) — FastAPI Application Entry Point.
"""
import structlog
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import engine, Base
from app.middleware.logging import LoggingMiddleware
from app.routers import (
    auth, projects, releases, dev_activities,
    test_plans, test_cases, evidence, signoffs,
    export, dashboard, audit
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.LOG_LEVEL)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logger.info("UTAP starting up", environment=settings.ENVIRONMENT, version=settings.APP_VERSION)
    # Create tables if they don't exist (Alembic handles migrations in production)
    if settings.ENVIRONMENT != "production":
        Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")
    yield
    logger.info("UTAP shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise Unit Test Artefact Portal for Snowflake and Informatica Cloud developers. "
        "Provides structured test plans, evidence management, SAML SSO, and S3 artefact storage."
    ),
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost applied last) ────────────────────────

# HTTPS redirect in production
if settings.ENVIRONMENT == "production" and not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Session (used for SAML relay state)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.COOKIE_SECURE,
    same_site=settings.COOKIE_SAMESITE,
)

# Structured logging
app.add_middleware(LoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(releases.router, prefix=API_PREFIX)
app.include_router(dev_activities.router, prefix=API_PREFIX)
app.include_router(test_plans.router, prefix=API_PREFIX)
app.include_router(test_cases.router, prefix=API_PREFIX)
app.include_router(evidence.router, prefix=API_PREFIX)
app.include_router(signoffs.router, prefix=API_PREFIX)
app.include_router(export.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)

# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancer / ECS health checks."""
    from sqlalchemy import text
    from app.database import SessionLocal
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True
        db.close()
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unavailable",
    }


# ── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", path=str(request.url.path), error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )
