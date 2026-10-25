"""Security and defensive protection middleware for CouchPilot Review Dashboard.
Enforces:
1. Strict defensive HTTP security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
2. In-memory sliding-window rate limiting (DoS / brute-force protection)
3. Maximum request body size enforcement (memory exhaustion defense)
4. Client IP extraction behind reverse proxies (Render / Cloudflare)
"""
from collections import defaultdict
import logging
import time
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.web.config import config

logger = logging.getLogger("couchpilot.security")

# Maximum permitted payload size for incoming POST requests (5 MB)
MAX_BODY_SIZE = 5 * 1024 * 1024


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter without external dependencies."""

    def __init__(self):
        self._history: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Check if an identifier has exceeded max_requests within window_seconds."""
        now = time.time()
        cutoff = now - window_seconds
        # Retain only timestamps within the active sliding window
        active_window = [ts for ts in self._history[key] if ts > cutoff]
        if len(active_window) >= max_requests:
            self._history[key] = active_window
            return True
        active_window.append(now)
        self._history[key] = active_window
        return False

    def clear(self) -> None:
        """Reset rate limiter state (useful for test suites)."""
        self._history.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract real client IP taking into account reverse-proxy headers (Render / Cloudflare)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defensive HTTP security headers and request-level protection middleware."""

    async def dispatch(self, request: Request, call_next):
        # 1. Payload size protection on POST / PUT
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_BODY_SIZE:
                        return JSONResponse(
                            {"detail": "Request entity too large. Maximum allowed size is 5MB."},
                            status_code=413,
                        )
                except ValueError:
                    return JSONResponse(
                        {"detail": "Invalid Content-Length header"},
                        status_code=400,
                    )

        # 2. Rate limiting check (bypassed in test environment)
        if not getattr(config, "TESTING", False):
            client_ip = get_client_ip(request)
            path = request.url.path

            if path == "/api/demo-trigger" and request.method == "POST":
                # Limit demo trigger to 20 triggers per minute per IP
                if rate_limiter.is_rate_limited(f"demo:{client_ip}", max_requests=20, window_seconds=60):
                    logger.warning("Rate limit exceeded for demo trigger from IP: %s", client_ip)
                    return JSONResponse(
                        {"detail": "Rate limit exceeded for demo trigger. Please wait 60 seconds before retrying."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
            elif path == "/api/reports" and request.method == "POST":
                # Limit automated report submissions to 120 per minute per IP
                if rate_limiter.is_rate_limited(f"reports:{client_ip}", max_requests=120, window_seconds=60):
                    logger.warning("Rate limit exceeded for report submission from IP: %s", client_ip)
                    return JSONResponse(
                        {"detail": "Rate limit exceeded for report ingestion. Please wait before retrying."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )

        # Process the request
        response = await call_next(request)

        # 3. Defensive Security Headers
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # Content-Security-Policy (tight whitelist with local styles and Google Fonts)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.sentry.io; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS (Strict-Transport-Security) on Render or when HTTPS is detected
        if config.IS_PRODUCTION or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
