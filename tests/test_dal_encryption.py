import pytest
from cryptography.fernet import Fernet

from agenticai_sdk.db.dal import DALEncryptor


def test_database_encryptor_uses_dedicated_secret_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("SECRETS_ENCRYPTION_KEY", key)
    monkeypatch.setenv("AGENTICAI_ENCRYPTION_KEY", "legacy-key-that-must-not-win")

    encryptor = DALEncryptor()
    encrypted = encryptor.encrypt("sensitive value")

    assert encryptor.decrypt(encrypted) == "sensitive value"


def test_database_encryptor_rejects_missing_production_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRETS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("AGENTICAI_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRETS_ENCRYPTION_KEY"):
        DALEncryptor()
