"""Migration and compatibility layer for AgenticAI SDK.

Supports upgrading from legacy configurations and maintaining backward compatibility.
"""

from .legacy import LegacyConfigMigrator, migrate_legacy_config
from .compat import CompatLayer, get_compat_layer

__all__ = [
    "LegacyConfigMigrator",
    "migrate_legacy_config",
    "CompatLayer",
    "get_compat_layer",
]