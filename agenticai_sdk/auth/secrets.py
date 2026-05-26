from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _get_fernet_key() -> bytes:
    raw = os.environ.get(
        "SECRETS_ENCRYPTION_KEY",
        os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
    )
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    key = _get_fernet_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    key = _get_fernet_key()
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()
