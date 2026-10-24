"""FastAPI application entrypoint for Render."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
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
