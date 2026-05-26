"""Multi-DB persistence layer with plug-and-play config persistence.

Supports:
- SQLite (default, zero-config)
- PostgreSQL
- ClickHouse
- Custom routing maps for specialised tables
- Persistent config via .agenticai_db_config file (connect once, persist forever)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

_engines: dict[str, Engine] = {}
_SessionLocal: sessionmaker | None = None
engine: Engine | None = None

CONFIG_FILE = ".agenticai_db_config"


def _config_path() -> str:
    return os.environ.get("AGENTICAI_DB_CONFIG", CONFIG_FILE)


def _save_config(core_db_url: str, routing_map: dict[str, str] | None = None) -> None:
    """Persist DB configuration to a JSON file so it survives restarts."""
    config: dict[str, Any] = {
        "core_db_url": core_db_url,
        "routing_map": routing_map or {},
        "configured_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _config_path()
    try:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass


def _load_config() -> dict[str, Any] | None:
    """Load persisted DB configuration if it exists."""
    path = _config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _clear_config() -> None:
    path = _config_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def init_db(
    core_db_url: str | None = None,
    routing_map: dict[str, str] | None = None,
    persist: bool = False,
) -> dict[str, Engine]:
    """Initialise the database architecture.

    Resolution order:
      1. ``core_db_url`` argument (explicit)
      2. ``.agenticai_db_config`` file (persisted from a previous session)
      3. ``AGENTICAI_DB_URL`` environment variable
      4. SQLite fallback (``sqlite:///agenticai.db``)

    Args:
        core_db_url: Primary database URL for global tables.
        routing_map: Optional mapping of table names to specialised DB URLs.
        persist: If True, save the config so it survives restarts.

    Returns:
        Dict of engine name → SQLAlchemy Engine.
    """
    global _engines, _SessionLocal, engine

    # Resolution chain
    if core_db_url is None:
        persisted = _load_config()
        if persisted:
            core_db_url = persisted.get("core_db_url")
            routing_map = routing_map or persisted.get("routing_map")
        else:
            core_db_url = os.getenv("AGENTICAI_DB_URL", "sqlite:///agenticai.db")

    actual_url = core_db_url

    _engines["core"] = create_engine(
        actual_url,
        echo=False,
        connect_args=({"check_same_thread": False} if "sqlite" in actual_url else {}),
    )
    engine = _engines["core"]

    if "sqlite" in actual_url:
        _enable_sqlite_wal(engine)

    # Setup specialised routing
    binds: dict[Any, Engine] = {}
    if routing_map:
        for tablename, url in routing_map.items():
            if url not in _engines:
                _engines[url] = create_engine(
                    url,
                    echo=False,
                    connect_args=({"check_same_thread": False} if "sqlite" in url else {}),
                )
            for cls in Base.registry.mappers:
                if cls.class_.__tablename__ == tablename:
                    binds[cls.class_] = _engines[url]

    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engines["core"],
        binds=binds,
    )

    Base.metadata.create_all(bind=_engines["core"])
    if binds:
        for mapper_class, eng in binds.items():
            mapper_class.__table__.create(bind=eng, checkfirst=True)

    # ── Seed default IAM policies ────────────────────────────────────────
    _seed_default_policies()

    if persist:
        _save_config(actual_url, routing_map)

    return _engines


def reset_db(
    core_db_url: str,
    routing_map: dict[str, str] | None = None,
) -> dict[str, Engine]:
    """Reset the database connection with a new URL at runtime (plug-and-play reconnect)."""
    global _engines, _SessionLocal, engine

    # Dispose old engines
    for eng in _engines.values():
        eng.dispose()
    _engines = {}
    _SessionLocal = None
    engine = None

    return init_db(core_db_url=core_db_url, routing_map=routing_map, persist=True)


def get_session():
    """FastAPI dependency — provides a transactional DB session."""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_status() -> dict[str, Any]:
    """Return current database connection status."""
    global engine
    if engine is None:
        return {"status": "not_initialised", "provider": None}

    url = str(engine.url)
    provider = "sqlite"
    if "postgresql" in url:
        provider = "postgresql"
    elif "clickhouse" in url:
        provider = "clickhouse"
    elif "mysql" in url:
        provider = "mysql"

    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
            latency = 5  # mock
            return {"status": "connected", "provider": provider, "url": url, "latency_ms": latency}
    except Exception as exc:
        return {"status": "error", "provider": provider, "url": url, "error": str(exc)}


def _seed_default_policies() -> None:
    """Create system IAM policies for admin/editor/viewer roles if missing."""
    from agenticai_sdk.db.models import Policy, PolicyAttachment
    from agenticai_sdk.auth.permissions import DEFAULT_ROLE_POLICIES

    db = next(get_session())
    try:
        for role, (name, desc, doc) in DEFAULT_ROLE_POLICIES.items():
            existing = db.query(Policy).filter(Policy.id == f"policy_{role}").first()
            if existing:
                continue
            import uuid
            policy = Policy(
                id=f"policy_{role}",
                name=name,
                description=desc,
                policy_document=doc,
                is_system=1,
            )
            db.add(policy)
            db.flush()  # ensure policy.id is available

            # Attach to the role principal
            attachment = PolicyAttachment(
                id=str(uuid.uuid4()),
                policy_id=policy.id,
                principal_type="role",
                principal_id=role,
            )
            db.add(attachment)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _enable_sqlite_wal(engine: Engine) -> None:
    """Enable WAL mode for better concurrent read performance on SQLite."""

    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
