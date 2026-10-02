"""
Secrets configuration integration for AgenticAI config system.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import AgenticAIConfig


class SecretsConfig(BaseModel):
    """Secrets manager configuration."""

    backend: str = Field(default="env", description="Backend: azure, aws, vault, env, dotenv, chained")
    # Azure Key Vault
    azure_vault_url: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    # AWS Secrets Manager
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_prefix: str = Field(default="", description="AWS secrets prefix")
    # HashiCorp Vault
    vault_url: Optional[str] = Field(default=None, description="Vault URL")
    vault_token: Optional[str] = Field(default=None, description="Vault token")
    vault_mount_point: str = Field(default="secret", description="Vault mount point")
    vault_kv_version: int = Field(default=2, description="Vault KV version")
    # Environment variables
    env_prefix: str = Field(default="", description="Environment variable prefix")
    # DotEnv
    dotenv_path: str = Field(default=".env", description="Path to .env file")
    # Chained
    chained_managers: list[dict[str, Any]] = Field(default_factory=list, description="Chained manager configs")

    def to_dict(self) -> dict[str, Any]:
        """Convert to secrets manager config dict."""
        return {
            "backend": self.backend,
            "vault_url": self.azure_vault_url,
            "region": self.aws_region,
            "prefix": self.aws_prefix,
            "url": self.vault_url,
            "token": self.vault_token,
            "mount_point": self.vault_mount_point,
            "kv_version": self.vault_kv_version,
            "managers": self.chained_managers,
        }


def get_secrets_manager(config: Optional[AgenticAIConfig] = None):
    """Get secrets manager instance from platform config."""
    from agenticai_sdk.secrets import create_secrets_manager

    if config and hasattr(config, "secrets") and config.secrets:
        return create_secrets_manager(config.secrets.to_dict())

    # Fallback to environment-based config
    import os
    backend = os.getenv("SECRETS_BACKEND", "env")
    mgr_config = {"backend": backend}

    if backend == "azure":
        mgr_config["vault_url"] = os.getenv("AZURE_KEY_VAULT_URL")
    elif backend == "aws":
        mgr_config["region"] = os.getenv("AWS_REGION", "us-east-1")
        mgr_config["prefix"] = os.getenv("AWS_SECRETS_PREFIX", "")
    elif backend == "vault":
        mgr_config["url"] = os.getenv("VAULT_ADDR")
        mgr_config["token"] = os.getenv("VAULT_TOKEN")
        mgr_config["mount_point"] = os.getenv("VAULT_MOUNT_POINT", "secret")
        mgr_config["kv_version"] = int(os.getenv("VAULT_KV_VERSION", "2"))
    elif backend == "dotenv":
        mgr_config["path"] = os.getenv("DOTENV_PATH", ".env")
    elif backend == "chained":
        # Default chain: env -> dotenv
        mgr_config["managers"] = [
            {"backend": "env", "prefix": os.getenv("SECRETS_PREFIX", "")},
            {"backend": "dotenv", "path": os.getenv("DOTENV_PATH", ".env")},
        ]

    return create_secrets_manager(mgr_config)