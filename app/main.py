"""
DeepTrace — FastAPI Application Factory
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.client import connect, disconnect
from app.exceptions import register_exception_handlers

# Feature routers
from app.features.auth.router          import router as auth_router
from app.features.organizations.router import router as organizations_router
from app.features.api_keys.router      import router as api_keys_router
from app.features.investigations.router import router as investigations_router
from app.features.documents.router     import router as documents_router
from app.features.pipeline.router      import router as pipeline_router
from app.features.evidence.router      import router as evidence_router
from app.features.risk.router          import router as risk_router
from app.features.agents.router        import router as agents_router
from app.features.reports.router       import router as reports_router
from app.features.webhooks.router      import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Prisma client lifecycle with FastAPI startup/shutdown."""
    await connect()
    yield
    await disconnect()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DeepTrace Forensics API",
        description=(
            "Explainable AI Document Forensics & Verification API Platform. "
            "SBP & NIST compliant. Pakistan & Global Edition."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=settings.app_debug,
    )

    # ── Middleware ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────────────────────
    # Auth & identity
    app.include_router(auth_router,            prefix="/api/v1/auth",           tags=["Auth"])
    app.include_router(organizations_router,   prefix="/api/v1/org",            tags=["Organization"])
    app.include_router(api_keys_router,        prefix="/api/v1/api-keys",       tags=["API Keys"])

    # Investigation domain (all nested under /investigations)
    app.include_router(investigations_router,  prefix="/api/v1/investigations", tags=["Investigations"])
    app.include_router(documents_router,       prefix="/api/v1/investigations", tags=["Documents"])
    app.include_router(pipeline_router,        prefix="/api/v1/investigations", tags=["Pipeline"])
    app.include_router(evidence_router,        prefix="/api/v1/investigations", tags=["Evidence"])
    app.include_router(risk_router,            prefix="/api/v1/investigations", tags=["Risk"])
    app.include_router(agents_router,          prefix="/api/v1/investigations", tags=["Agents"])
    app.include_router(reports_router,         prefix="/api/v1/investigations", tags=["Reports"])

    # Platform integrations
    app.include_router(webhooks_router,        prefix="/api/v1/webhooks",       tags=["Webhooks"])

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_check():
        return {"status": "ok", "service": "deeptrace-api"}

    return app


app = create_app()
