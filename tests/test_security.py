"""Security test suite verifying defensive headers, constant-time auth, and rate limits."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.web.main import app
from app.web.config import config
from app.web.security import rate_limiter, MAX_BODY_SIZE


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure clean rate limiter state before each test."""
    rate_limiter.clear()
    yield
    rate_limiter.clear()


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify standard defensive headers are attached to responses."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200

        headers = resp.headers
        assert headers.get("x-frame-options") == "SAMEORIGIN"
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in headers.get("permissions-policy", "")

        csp = headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "https://fonts.googleapis.com" in csp
        assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_constant_time_api_auth():
    """Verify API authentication accepts valid keys and rejects invalid ones."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"repo_name": "sec_test_repo", "branch_name": "sec_test_branch"}

        # Missing key
        r1 = await client.post("/api/reports", json=payload)
        assert r1.status_code == 401

        # Incorrect key
        r2 = await client.post(
            "/api/reports",
            json=payload,
            headers={"X-CouchPilot-Key": "wrong_attacker_key"}
        )
        assert r2.status_code == 401

        # Correct key
        r3 = await client.post(
            "/api/reports",
            json=payload,
            headers={"X-CouchPilot-Key": config.API_KEY}
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "saved"


@pytest.mark.asyncio
async def test_input_validation_run_id_regex():
    """Verify malformed run_id paths are rejected with 400 Bad Request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid characters (SQL injection / path traversal probe attempts)
        resp = await client.get("/api/reports/bad%20run%20id!")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid run_id format"

        resp2 = await client.get("/api/reports/run;DROP%20TABLE")
        assert resp2.status_code == 400
        assert resp2.json()["detail"] == "Invalid run_id format"


@pytest.mark.asyncio
async def test_payload_size_limit():
    """Verify request bodies exceeding MAX_BODY_SIZE are rejected with 413."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Simulate oversized payload header
        resp = await client.post(
            "/api/reports",
            headers={
                "X-CouchPilot-Key": config.API_KEY,
                "Content-Length": str(MAX_BODY_SIZE + 1024),
            },
            content=b"test"
        )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limiter_enforcement():
    """Verify rate limiter blocks rapid abuse with HTTP 429 and Retry-After."""
    # Temporarily activate rate limiting by clearing TESTING flag
    orig_testing = config.TESTING
    config.TESTING = False
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Trigger demo run within limits
            for _ in range(20):
                resp = await client.post("/api/demo-trigger")
                assert resp.status_code == 200

            # 21st request should be blocked
            resp_blocked = await client.post("/api/demo-trigger")
            assert resp_blocked.status_code == 429
            assert "Retry-After" in resp_blocked.headers
            assert "rate limit exceeded" in resp_blocked.json()["detail"].lower()
    finally:
        config.TESTING = orig_testing
