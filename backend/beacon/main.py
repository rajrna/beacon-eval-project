import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from beacon.core.logging import configure_logging
from beacon.core.settings import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    settings = get_settings()
    logger.info(
        "beacon_startup",
        environment=settings.environment,
        debug=settings.debug,
    )
    yield
    logger.info("beacon_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Beacon API",
        description="Student Agent Evaluation & Observability Platform",
        version="0.1.0",
        docs_url="/docs" if settings.is_local else None,
        redoc_url="/redoc" if settings.is_local else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    origins = (
        ["http://localhost:5173", "http://localhost:3000"]
        if settings.is_local
        else ["https://beacon.yourdomain.com"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Correlation-ID middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):  # type: ignore
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "type": "https://beacon.dev/errors/internal",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred.",
            },
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    from beacon.routes.institutions import router as institutions_router
    from beacon.routes.programs import router as programs_router
    from beacon.routes.agents import router as agents_router
    from beacon.routes.datasets import router as datasets_router
    from beacon.routes.judges import router as judges_router
    from beacon.routes.runs import router as runs_router
    from beacon.routes.traces import router as traces_router
    from beacon.routes.annotations import router as annotations_router
    from beacon.routes.sme import router as sme_router
    from beacon.routes.chat import router as chat_router
    from beacon.routes.dashboard import router as dashboard_router
    from beacon.routes.compare import router as compare_router

    app.include_router(institutions_router, prefix="/v1/institutions", tags=["institutions"])
    app.include_router(programs_router, prefix="/v1/programs", tags=["programs"])
    app.include_router(agents_router, prefix="/v1/agents", tags=["agents"])
    app.include_router(compare_router, prefix="/v1/agents", tags=["compare"])
    app.include_router(datasets_router, prefix="/v1/datasets", tags=["datasets"])
    app.include_router(judges_router, prefix="/v1/judges", tags=["judges"])
    app.include_router(runs_router, prefix="/v1/runs", tags=["runs"])
    app.include_router(traces_router, prefix="/v1/traces", tags=["traces"])
    app.include_router(annotations_router, prefix="/v1/annotations", tags=["annotations"])
    app.include_router(sme_router, prefix="/v1/sme", tags=["sme"])
    app.include_router(chat_router, prefix="/v1/chat", tags=["chat"])
    app.include_router(dashboard_router, prefix="/v1/dashboard", tags=["dashboard"])

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/healthz", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
