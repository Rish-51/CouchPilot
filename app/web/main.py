"""FastAPI application entrypoint for Render."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.web import db
from app.web.routes.api import router as api_router
from app.web.routes.views import router as views_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: initialize SQLite DB and seed fixtures on startup."""
    await db.init_db()
    yield


app = FastAPI(
    title="CouchPilot Dashboard",
    description="Autonomous repository housekeeping dashboard for Hacktoberfest DEV Challenge",
    version="0.1.0",
    lifespan=lifespan,
)

# Performance: Automatic GZip compression for responses > 500 bytes (reduces CSS/JS/HTML by 70-80%)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def add_performance_cache_headers(request, call_next):
    """Add browser caching headers to static assets to prevent redundant downloads."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return response


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
