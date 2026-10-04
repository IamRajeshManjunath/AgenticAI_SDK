import pytest

from agenticai_sdk.security import get_cors_origins, validate_security_configuration


def test_development_cors_is_localhost_only(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    assert get_cors_origins() == ["http://localhost:3000", "http://127.0.0.1:3000"]


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"SECRET_KEY": "too-short"},
        {
            "SECRET_KEY": "s" * 48,
            "SECRETS_ENCRYPTION_KEY": "e" * 48,
            "CORS_ORIGINS": "*",
        },
        {
            "SECRET_KEY": "s" * 48,
            "SECRETS_ENCRYPTION_KEY": "e" * 48,
        },
    ],
)
def test_production_rejects_insecure_configuration(monkeypatch, settings):
    for key in ("SECRET_KEY", "SECRETS_ENCRYPTION_KEY", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    for key, value in settings.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(RuntimeError):
        validate_security_configuration()


def test_production_accepts_explicit_secrets_and_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.setenv("SECRETS_ENCRYPTION_KEY", "e" * 48)
    monkeypatch.setenv("CORS_ORIGINS", "https://console.example.com")

    validate_security_configuration()
    assert get_cors_origins() == ["https://console.example.com"]
