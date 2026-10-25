"""FastAPI REST API routes."""
from datetime import datetime, timezone
import json
import os
import re
import secrets
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.core.models import Report
from app.web.config import config
from app.web import db

router = APIRouter(prefix="/api", tags=["api"])

# Regex for safe run_id format (alphanumeric, hyphens, underscores)
RUN_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def verify_api_key(x_couchpilot_key: Optional[str] = Header(None)) -> None:
    """Enforce authentication on write endpoints using constant-time comparison to prevent timing leaks."""
    if not x_couchpilot_key or not secrets.compare_digest(x_couchpilot_key, config.API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing X-CouchPilot-Key header"
        )


@router.post("/reports")
async def receive_report(
    report: Dict[str, Any],
    x_couchpilot_key: Optional[str] = Header(None)
):
    """Receive and persist a housekeeping run report from local engine or worker."""
    verify_api_key(x_couchpilot_key)
    if "run_id" not in report:
        report["run_id"] = str(uuid.uuid4())
    elif not RUN_ID_REGEX.match(str(report["run_id"])):
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    if "created_at" not in report:
        report["created_at"] = datetime.now(timezone.utc).isoformat()

    await db.save_report(report)
    return {"status": "saved", "run_id": report["run_id"]}


@router.get("/reports")
async def list_reports(
    status: Optional[str] = Query(None),
    repo: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List runs with optional filtering by status and repository name."""
    reports = await db.get_reports(status=status, repo_name=repo, limit=limit, offset=offset)
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{run_id}")
async def get_report_detail(run_id: str):
    """Fetch complete detail for a single run including metrics and diff."""
    if not RUN_ID_REGEX.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    report = await db.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return report


@router.post("/demo-trigger")
async def trigger_demo_run(request: Request):
    """One-click trigger for judges: replays sample housekeeping run with zero setup."""
    demo_mode = config.DEMO_MODE

    # In replay mode, select or refresh the primary demo fixture run
    demo_run = await db.get_report("demo-run-001")
    if not demo_run:
        # Re-seed if needed
        await db.init_db()
        demo_run = await db.get_report("demo-run-001")

    return {
        "status": "success",
        "mode": demo_mode,
        "run_id": "demo-run-001",
        "message": "Demo replay completed successfully.",
    }


@router.get("/healthz")
async def health_check():
    """Service health probe for Render."""
    return {"status": "healthy", "service": "couchpilot-dashboard"}
