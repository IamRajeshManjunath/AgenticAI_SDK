"""Production security configuration validation."""

from __future__ import annotations

import os

_INSECURE_DEFAULT_SECRET = "dev-secret-key-change-in-production"
_PRODUCTION_ENVIRONMENTS = {"production", "prod"}


def validate_security_configuration() -> None:
    """Fail closed when production is started with development security settings."""
    environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if environment not in _PRODUCTION_ENVIRONMENTS:
        return

    secret_key = os.getenv("SECRET_KEY", "")
    if len(secret_key.encode("utf-8")) < 32 or secret_key == _INSECURE_DEFAULT_SECRET:
        raise RuntimeError("Production requires SECRET_KEY to contain at least 32 random bytes.")

    encryption_key = os.getenv("SECRETS_ENCRYPTION_KEY", "")
    if len(encryption_key.encode("utf-8")) < 32:
        raise RuntimeError("Production requires a dedicated SECRETS_ENCRYPTION_KEY of at least 32 bytes.")

    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("Production requires explicit CORS_ORIGINS; wildcard origins are not allowed.")


def get_cors_origins() -> list[str]:
    """Return explicit configured CORS origins or safe local-development origins."""
    configured = os.getenv("CORS_ORIGINS")
    if configured is not None:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if origins:
            return origins
    environment = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if environment in _PRODUCTION_ENVIRONMENTS:
        raise RuntimeError("Production requires explicit CORS_ORIGINS.")
    return ["http://localhost:3000", "http://127.0.0.1:3000"]
