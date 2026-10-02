"""
Secrets Manager Abstraction — unified interface for multiple secret backends.

Supports:
- Azure Key Vault
- AWS Secrets Manager
- HashiCorp Vault
- Environment variables (fallback)
- Local .env file (dev fallback)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
import os
import logging

logger = logging.getLogger(__name__)


class SecretsManager(ABC):
    """Abstract base class for secrets managers."""

    @abstractmethod
    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value by name."""
        pass

    @abstractmethod
    def set_secret(self, name: str, value: str) -> bool:
        """Set a secret value (if supported by backend)."""
        pass

    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """Delete a secret (if supported by backend)."""
        pass

    @abstractmethod
    def list_secrets(self, prefix: str = "") -> list[str]:
        """List secret names with optional prefix filter."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Check connectivity and return status."""
        pass


class EnvSecretsManager(SecretsManager):
    """Environment variables secrets manager (fallback)."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def _full_name(self, name: str) -> str:
        return f"{self.prefix}{name}" if self.prefix else name

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(self._full_name(name), default)

    def set_secret(self, name: str, value: str) -> bool:
        os.environ[self._full_name(name)] = value
        return True

    def delete_secret(self, name: str) -> bool:
        if self._full_name(name) in os.environ:
            del os.environ[self._full_name(name)]
            return True
        return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        full_prefix = self._full_name(prefix)
        return [k[len(full_prefix):] for k in os.environ.keys() if k.startswith(full_prefix)]

    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "backend": "environment", "prefix": self.prefix}


class DotEnvSecretsManager(SecretsManager):
    """Local .env file secrets manager (dev fallback)."""

    def __init__(self, path: str = ".env"):
        self.path = path
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        self._cache[key.strip()] = value.strip()
        except FileNotFoundError:
            pass

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self._cache.get(name, default)

    def set_secret(self, name: str, value: str) -> bool:
        self._cache[name] = value
        try:
            with open(self.path, "w") as f:
                for k, v in self._cache.items():
                    f.write(f"{k}={v}\n")
            return True
        except OSError:
            return False

    def delete_secret(self, name: str) -> bool:
        if name in self._cache:
            del self._cache[name]
            return self.set_secret("", "")  # Rewrite file
        return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        return [k for k in self._cache.keys() if k.startswith(prefix)]

    def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "backend": "dotenv", "path": self.path, "count": len(self._cache)}


# Optional backends - imported lazily to avoid hard dependencies
_AZURE_AVAILABLE = None
_AWS_AVAILABLE = None
_VAULT_AVAILABLE = None


def _check_azure() -> bool:
    global _AZURE_AVAILABLE
    if _AZURE_AVAILABLE is None:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            _AZURE_AVAILABLE = True
        except ImportError:
            _AZURE_AVAILABLE = False
    return _AZURE_AVAILABLE


def _check_aws() -> bool:
    global _AWS_AVAILABLE
    if _AWS_AVAILABLE is None:
        try:
            import boto3
            _AWS_AVAILABLE = True
        except ImportError:
            _AWS_AVAILABLE = False
    return _AWS_AVAILABLE


def _check_vault() -> bool:
    global _VAULT_AVAILABLE
    if _VAULT_AVAILABLE is None:
        try:
            import hvac
            _VAULT_AVAILABLE = True
        except ImportError:
            _VAULT_AVAILABLE = False
    return _VAULT_AVAILABLE


class AzureKeyVaultManager(SecretsManager):
    """Azure Key Vault secrets manager."""

    def __init__(self, vault_url: str, credential=None):
        if not _check_azure():
            raise RuntimeError("azure-identity and azure-keyvault-secrets packages required. Install with: pip install azure-identity azure-keyvault-secrets")

        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        self.vault_url = vault_url
        self.credential = credential or DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        try:
            secret = self.client.get_secret(name)
            return secret.value
        except Exception:
            return default

    def set_secret(self, name: str, value: str) -> bool:
        try:
            self.client.set_secret(name, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {name}: {e}")
            return False

    def delete_secret(self, name: str) -> bool:
        try:
            poller = self.client.begin_delete_secret(name)
            poller.wait()
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            secrets = []
            for secret in self.client.list_properties_of_secrets():
                if secret.name.startswith(prefix):
                    secrets.append(secret.name)
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []

    def health_check(self) -> dict[str, Any]:
        try:
            # Try to list one secret to verify connectivity
            list(self.client.list_properties_of_secrets(max_results=1))
            return {"status": "healthy", "backend": "azure_keyvault", "vault_url": self.vault_url}
        except Exception as e:
            return {"status": "unhealthy", "backend": "azure_keyvault", "error": str(e)}


class AWSSecretsManager(SecretsManager):
    """AWS Secrets Manager secrets manager."""

    def __init__(self, region: str = "us-east-1", prefix: str = ""):
        if not _check_aws():
            raise RuntimeError("boto3 package required. Install with: pip install boto3")

        import boto3
        self.region = region
        self.prefix = prefix
        self.client = boto3.client("secretsmanager", region_name=region)

    def _full_name(self, name: str) -> str:
        return f"{self.prefix}{name}" if self.prefix else name

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        try:
            response = self.client.get_secret_value(SecretId=self._full_name(name))
            return response.get("SecretString", default)
        except self.client.exceptions.ResourceNotFoundException:
            return default
        except Exception as e:
            logger.error(f"Failed to get secret {name}: {e}")
            return default

    def set_secret(self, name: str, value: str) -> bool:
        try:
            full_name = self._full_name(name)
            try:
                self.client.update_secret(SecretId=full_name, SecretString=value)
            except self.client.exceptions.ResourceNotFoundException:
                self.client.create_secret(Name=full_name, SecretString=value)
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {name}: {e}")
            return False

    def delete_secret(self, name: str) -> bool:
        try:
            self.client.delete_secret(SecretId=self._full_name(name), ForceDeleteWithoutRecovery=True)
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            secrets = []
            paginator = self.client.get_paginator("list_secrets")
            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret["Name"]
                    if name.startswith(self._full_name(prefix)):
                        secrets.append(name[len(self.prefix):] if self.prefix else name)
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []

    def health_check(self) -> dict[str, Any]:
        try:
            self.client.list_secrets(MaxResults=1)
            return {"status": "healthy", "backend": "aws_secretsmanager", "region": self.region}
        except Exception as e:
            return {"status": "unhealthy", "backend": "aws_secretsmanager", "error": str(e)}


class HashiCorpVaultManager(SecretsManager):
    """HashiCorp Vault secrets manager."""

    def __init__(self, url: str, token: str, mount_point: str = "secret", kv_version: int = 2):
        if not _check_vault():
            raise RuntimeError("hvac package required. Install with: pip install hvac")

        import hvac
        self.client = hvac.Client(url=url, token=token)
        self.mount_point = mount_point
        self.kv_version = kv_version

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        try:
            if self.kv_version == 2:
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=name, mount_point=self.mount_point
                )
                return response["data"]["data"].get("value", default)
            else:
                response = self.client.secrets.kv.v1.read_secret(
                    path=name, mount_point=self.mount_point
                )
                return response["data"].get("value", default)
        except Exception:
            return default

    def set_secret(self, name: str, value: str) -> bool:
        try:
            if self.kv_version == 2:
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=name, mount_point=self.mount_point, secret={"value": value}
                )
            else:
                self.client.secrets.kv.v1.create_or_update_secret(
                    path=name, mount_point=self.mount_point, secret={"value": value}
                )
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {name}: {e}")
            return False

    def delete_secret(self, name: str) -> bool:
        try:
            if self.kv_version == 2:
                self.client.secrets.kv.v2.delete_latest_version_of_secret(
                    path=name, mount_point=self.mount_point
                )
            else:
                self.client.secrets.kv.v1.delete_secret(
                    path=name, mount_point=self.mount_point
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False

    def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            if self.kv_version == 2:
                response = self.client.secrets.kv.v2.list_secrets(
                    path=prefix, mount_point=self.mount_point
                )
                return response["data"]["keys"]
            else:
                response = self.client.secrets.kv.v1.list_secrets(
                    path=prefix, mount_point=self.mount_point
                )
                return response["data"]["keys"]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []

    def health_check(self) -> dict[str, Any]:
        try:
            if self.client.sys.is_sealed():
                return {"status": "unhealthy", "backend": "hashicorp_vault", "error": "Vault is sealed"}
            return {"status": "healthy", "backend": "hashicorp_vault", "url": self.client.url}
        except Exception as e:
            return {"status": "unhealthy", "backend": "hashicorp_vault", "error": str(e)}


class ChainedSecretsManager(SecretsManager):
    """Chain multiple secrets managers with fallback."""

    def __init__(self, managers: list[SecretsManager]):
        self.managers = managers

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        for manager in self.managers:
            value = manager.get_secret(name)
            if value is not None:
                return value
        return default

    def set_secret(self, name: str, value: str) -> bool:
        # Set on all managers that support it
        results = [m.set_secret(name, value) for m in self.managers]
        return any(results)

    def delete_secret(self, name: str) -> bool:
        results = [m.delete_secret(name) for m in self.managers]
        return any(results)

    def list_secrets(self, prefix: str = "") -> list[str]:
        all_secrets = set()
        for manager in self.managers:
            all_secrets.update(manager.list_secrets(prefix))
        return sorted(all_secrets)

    def health_check(self) -> dict[str, Any]:
        results = {}
        for i, manager in enumerate(self.managers):
            results[f"manager_{i}"] = manager.health_check()
        overall = "healthy" if all(r.get("status") == "healthy" for r in results.values()) else "degraded"
        return {"status": overall, "backends": results}


def create_secrets_manager(config: Optional[dict[str, Any]] = None) -> SecretsManager:
    """
    Create a secrets manager based on configuration.

    Config options:
    - backend: "azure" | "aws" | "vault" | "env" | "dotenv" | "chained"
    - For chained: list of backend configs under "managers" key
    - Azure: vault_url
    - AWS: region, prefix
    - Vault: url, token, mount_point, kv_version
    - Env: prefix
    - DotEnv: path
    """
    config = config or {}
    backend = config.get("backend", "env")

    if backend == "azure":
        vault_url = config.get("vault_url") or os.getenv("AZURE_KEY_VAULT_URL")
        if not vault_url:
            raise ValueError("Azure Key Vault URL required (vault_url or AZURE_KEY_VAULT_URL)")
        return AzureKeyVaultManager(vault_url)

    elif backend == "aws":
        region = config.get("region") or os.getenv("AWS_REGION", "us-east-1")
        prefix = config.get("prefix") or os.getenv("AWS_SECRETS_PREFIX", "")
        return AWSSecretsManager(region=region, prefix=prefix)

    elif backend == "vault":
        url = config.get("url") or os.getenv("VAULT_ADDR")
        token = config.get("token") or os.getenv("VAULT_TOKEN")
        if not url or not token:
            raise ValueError("Vault URL and token required (url/VAULT_ADDR and token/VAULT_TOKEN)")
        mount_point = config.get("mount_point", "secret")
        kv_version = config.get("kv_version", 2)
        return HashiCorpVaultManager(url=url, token=token, mount_point=mount_point, kv_version=kv_version)

    elif backend == "dotenv":
        path = config.get("path", ".env")
        return DotEnvSecretsManager(path)

    elif backend == "chained":
        managers = []
        for mgr_config in config.get("managers", []):
            managers.append(create_secrets_manager(mgr_config))
        if not managers:
            # Default chain: env -> dotenv
            managers = [EnvSecretsManager(), DotEnvSecretsManager()]
        return ChainedSecretsManager(managers)

    else:  # env (default)
        prefix = config.get("prefix") or os.getenv("SECRETS_PREFIX", "")
        return EnvSecretsManager(prefix=prefix)