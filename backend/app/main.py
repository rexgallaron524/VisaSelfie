import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.audit.routes import router as audit_router
from app.auth.dependencies import Database
from app.auth.routes import router as auth_router
from app.core.config import Settings, get_settings
from app.limiter import limiter
from app.processes.routes import router as processes_router

logger = logging.getLogger("visaselfie")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Visa Selfie API",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
    )
    app.state.settings = settings
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "HEAD", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Range", "X-Recording-Challenge"],
    )
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.forwarded_allow_ips)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic's default response includes submitted values, including passwords.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
        )

    @app.middleware("http")
    async def security_and_logging(request: Request, call_next):
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        # Exact Origin verification protects cookie-authenticated mutations, including login.
        # Missing Origin is rejected too; CLI clients must explicitly supply it.
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            request.headers.get("origin") not in settings.allowed_origins
        ):
            response = JSONResponse(status_code=403, content={"detail": "Request origin rejected."})
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Never serialize exception text: database errors can contain sensitive values.
                logger.error(
                    json.dumps(
                        {
                            "event": "request.error",
                            "request_id": request_id,
                            "error_type": type(exc).__name__,
                        }
                    )
                )
                response = JSONResponse(
                    status_code=500, content={"detail": "An unexpected error occurred."}
                )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "http.request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            )
        )
        return response

    @app.get("/api/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    @app.get("/api/ready", tags=["Health"])
    def ready(db: Database):
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ready"}

    app.include_router(auth_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(processes_router, prefix="/api")
    return app
