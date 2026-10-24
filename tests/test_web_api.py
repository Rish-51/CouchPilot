import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from app.web.main import app
from app.web.config import config
from app.web import db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database schema is created and seeded before API tests run."""
    asyncio.run(db.init_db())


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_reports_seeded():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert len(data["reports"]) >= 1


@pytest.mark.asyncio
async def test_api_reports_auth_required():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"run_id": "test-unauth-run", "repo_name": "repo1", "branch_name": "b1"}
        # Without auth header
        resp_bad = await client.post("/api/reports", json=payload)
        assert resp_bad.status_code == 401

        # With auth header
        resp_good = await client.post(
            "/api/reports",
            json=payload,
            headers={"X-CouchPilot-Key": config.API_KEY}
        )
        assert resp_good.status_code == 200
        assert resp_good.json()["status"] == "saved"


@pytest.mark.asyncio
async def test_demo_trigger():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/demo-trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["run_id"] == "demo-run-001"


@pytest.mark.asyncio
async def test_html_views():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Overview
        r1 = await client.get("/")
        assert r1.status_code == 200
        assert "Repository Housekeeping Workbench" in r1.text

        # Runs history
        r2 = await client.get("/runs")
        assert r2.status_code == 200
        assert "Run History" in r2.text

        # Run detail
        r3 = await client.get("/runs/demo-run-001")
        assert r3.status_code == 200
        assert "Unified Diff" in r3.text
