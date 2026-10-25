"""FastAPI application entrypoint for Render."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.web import db
from app.web.config import config
from app.web.routes.api import router as api_router
from app.web.routes.views import router as views_router
from app.web.security import SecurityHeadersMiddleware

logger = logging.getLogger("couchpilot.web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: audit operational security, initialize SQLite DB and seed fixtures."""
    config.audit_security()
    await db.init_db()
    yield


app = FastAPI(
    title="CouchPilot Dashboard",
    description="Autonomous repository housekeeping dashboard for Hacktoberfest DEV Challenge",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if config.IS_PRODUCTION else "/docs",
    redoc_url=None if config.IS_PRODUCTION else "/redoc",
)

# Operational & Cloud Security: Defensive security headers, CSP, rate-limiting, and payload size bounds
app.add_middleware(SecurityHeadersMiddleware)

# Performance: Automatic GZip compression for responses > 500 bytes (reduces CSS/JS/HTML by 70-80%)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def add_performance_cache_headers(request, call_next):
    """Add browser caching headers to static assets to prevent redundant downloads."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitize unhandled 500 exceptions to prevent internal system or traceback leaks in production."""
    logger.exception("Unhandled server exception: %s", exc)
    if config.IS_PRODUCTION:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "An internal server error occurred. Telemetry has been recorded."},
        )
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )


# Ensure static directories exist
static_dir = Path(__file__).parent / "static"
os.makedirs(static_dir / "css", exist_ok=True)
os.makedirs(static_dir / "js", exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(api_router)
app.include_router(views_router)


@app.get("/healthz")
async def root_health_check():
    """Direct root health check endpoint for Render."""
    return {"status": "healthy", "service": "couchpilot-dashboard"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.web.main:app", host="0.0.0.0", port=port, reload=True)
