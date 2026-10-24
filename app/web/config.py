"""Web service configuration."""
import os


class WebConfig:
    API_KEY: str = os.getenv("COUCHPILOT_API_KEY", "couchpilot_secret_key_change_me_in_prod")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "couchpilot.db")
    DEMO_MODE: str = os.getenv("DEMO_MODE", "replay")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_HOST: str = os.getenv("SENTRY_HOST", "sentry.io")
    SENTRY_ORG: str = os.getenv("SENTRY_ORG", "couchpilot")


config = WebConfig()
