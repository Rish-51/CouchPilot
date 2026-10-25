"""Web service configuration."""
import os


class WebConfig:
    API_KEY: str = os.getenv("COUCHPILOT_API_KEY", "couchpilot_secret_key_change_me_in_prod")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "couchpilot.db")
    DEMO_MODE: str = os.getenv("DEMO_MODE", "replay")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_HOST: str = os.getenv("SENTRY_HOST", "sentry.io")
    SENTRY_ORG: str = os.getenv("SENTRY_ORG", "couchpilot")

    # Cloud & Operational environment flags
    IS_PRODUCTION: bool = bool(os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production")
    TESTING: bool = bool(os.getenv("TESTING", "false").lower() in ("true", "1") or "PYTEST_CURRENT_TEST" in os.environ)

    def audit_security(self) -> None:
        """Audit production secrets on startup and log alerts."""
        if self.IS_PRODUCTION and self.API_KEY == "couchpilot_secret_key_change_me_in_prod":
            import logging
            logging.getLogger("couchpilot.security").warning(
                "CRITICAL SECURITY ALERT: Running in production with the default API key! "
                "Ensure COUCHPILOT_API_KEY is configured in your Render environment."
            )


config = WebConfig()
