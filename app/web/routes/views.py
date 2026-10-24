"""FastAPI Jinja2 HTML views."""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.web import db
from app.web.config import config
from app.web.pygments_style import highlight_diff

template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

router = APIRouter(tags=["views"])


@router.get("/", response_class=HTMLResponse)
async def view_overview(request: Request):
    """Overview dashboard view with metrics bar and latest runs."""
    metrics = await db.get_overview_metrics()
    latest_runs = await db.get_reports(limit=20)
    active_run = latest_runs[0] if latest_runs else None
    diff_html = highlight_diff(active_run.get("unified_diff", "")) if active_run else ""
    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            "metrics": metrics,
            "latest_runs": latest_runs,
            "run": active_run,
            "diff_html": diff_html,
            "sentry_host": config.SENTRY_HOST,
            "sentry_org": config.SENTRY_ORG,
        },
    )


@router.get("/runs", response_class=HTMLResponse)
async def view_runs_history(
    request: Request,
    status: Optional[str] = Query(None),
    repo: Optional[str] = Query(None),
):
    """Filterable run history feed."""
    runs = await db.get_reports(status=status, repo_name=repo, limit=50)
    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context={
            "runs": runs,
            "active_status": status,
            "active_repo": repo,
        },
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def view_run_detail(request: Request, run_id: str):
    """Run detail page with Pygments syntax-highlighted diff viewer."""
    report = await db.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run not found")

    diff_html = highlight_diff(report.get("unified_diff", ""))
    return templates.TemplateResponse(
        request=request,
        name="run_detail.html",
        context={
            "run": report,
            "diff_html": diff_html,
            "sentry_host": config.SENTRY_HOST,
            "sentry_org": config.SENTRY_ORG,
        },
    )
