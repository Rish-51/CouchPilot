"""Sentry distributed tracing with custom span hierarchy and no-op fallback."""
import contextlib
import os
import time
from typing import Any, Dict, Generator, Optional
import sentry_sdk
from sentry_sdk.tracing import Span, Transaction


class SentryManager:
    """Manages Sentry transactions and spans with zero-crash fallback when unconfigured."""

    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or os.getenv("SENTRY_DSN", "")
        self.is_active = False

        if self.dsn and self.dsn.strip():
            try:
                sentry_sdk.init(
                    dsn=self.dsn.strip(),
                    traces_sample_rate=1.0,
                    environment=os.getenv("COUCHPILOT_ENV", "development"),
                    release="couchpilot@0.1.0",
                )
                self.is_active = True
            except Exception:
                self.is_active = False

    def get_current_trace_id(self) -> Optional[str]:
        """Return the current active Sentry trace ID, or None if inactive."""
        if not self.is_active:
            return None
        try:
            span = sentry_sdk.get_current_span()
            if span:
                return str(span.trace_id)
        except Exception:
            pass
        return None

    def start_transaction(self, name: str = "couchpilot.run", op: str = "agent.run") -> Any:
        """Start a root transaction for the housekeeping run."""
        if self.is_active:
            return sentry_sdk.start_transaction(name=name, op=op)
        return contextlib.nullcontext()

    @contextlib.contextmanager
    def span(
        self,
        op: str,
        description: str,
        tags: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Generator[Optional[Span], None, None]:
        """Start a traced span adhering to the mandated span hierarchy."""
        if not self.is_active:
            yield None
            return

        with sentry_sdk.start_span(op=op, description=description) as span:
            if tags:
                for k, v in tags.items():
                    span.set_tag(k, str(v))
            if data:
                for k, v in data.items():
                    span.set_data(k, v)
            yield span


# Global default instance
_sentry_instance: Optional[SentryManager] = None

def get_sentry_manager() -> SentryManager:
    global _sentry_instance
    if _sentry_instance is None:
        _sentry_instance = SentryManager()
    return _sentry_instance
