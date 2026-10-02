"""
AgenticAI SDK — FastAPI entrypoint with plug-and-play database support.

Usage:
    python main.py                          # default (SQLite)
    python main.py --db-url postgresql://... # persistent PostgreSQL
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import argparse

import uvicorn
from agenticai_sdk.db.database import init_db
from agenticai_sdk.gateway.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="AgenticAI SDK Gateway")
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (e.g. postgresql://user:pass@host/db). "
             "If omitted, uses persisted config, env var AGENTICAI_DB_URL, or SQLite default.",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--reload", action="store_true", default=True, help="Auto-reload on code changes")
    args = parser.parse_args()

    if args.db_url:
        init_db(core_db_url=args.db_url, persist=True)

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

# Export for uvicorn direct usage: `uvicorn main:app`
app = create_app(log_level="INFO")
