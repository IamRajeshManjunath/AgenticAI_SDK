"""Gateway sub-package — FastAPI web server for workflow execution."""

from agenticai_sdk.gateway.app import create_app

__all__ = ["create_app"]
