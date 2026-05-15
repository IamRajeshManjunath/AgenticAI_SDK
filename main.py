"""
AgenticAI SDK — FastAPI entrypoint.

Start the server:
    python main.py
    # or via uvicorn:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import uvicorn
from agenticai_sdk.gateway.app import create_app

# Create the application instance (importable by uvicorn as `main:app`)
app = create_app(log_level="INFO")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
