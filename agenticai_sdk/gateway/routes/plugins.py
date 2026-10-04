"""Plugin discovery endpoints used to populate provider selectors."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db.models import User
from agenticai_sdk.plugins import IntegrationType, get_global_registry

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


@router.get("/providers")
async def list_provider_options(
    type: IntegrationType = IntegrationType.CHAT_MODEL,
    _: User = Depends(require_permission("integration:read")),
):
    """Return providers available through the installed plugin registry."""
    providers = get_global_registry().list_available(type)
    providers.sort(key=lambda provider: (provider.name.casefold(), provider.provider))
    return {
        "providers": [
            {
                "provider": provider.provider,
                "name": provider.name,
                "description": provider.description,
                "type": provider.type.value,
                "features": provider.features.model_dump(),
                "docs_url": provider.docs_url,
            }
            for provider in providers
        ]
    }
