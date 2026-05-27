import os

API_TOKEN = os.getenv("API_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1440"))
JSON_LOGS = os.getenv("JSON_LOGS", "true").lower() == "true"
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
ENABLE_ALERT_EMAILS = os.getenv("ENABLE_ALERT_EMAILS", "false").lower() == "true"


def validate_runtime_config() -> None:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured for production safety")
    if SCHEDULER_INTERVAL_MINUTES < 1:
        raise RuntimeError("SCHEDULER_INTERVAL_MINUTES must be >= 1")
