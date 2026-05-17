import os
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Multi-DB architecture supporting routing different stages to different destinations
_engines: dict[str, Engine] = {}
_SessionLocal = None

def init_db(core_db_url: str | None = None, routing_map: dict[str, str] | None = None):
    """
    Dynamically initializes the database architecture.
    
    Args:
        core_db_url: The primary fallback database URL for global data (Workspaces, Workflows).
        routing_map: A dictionary mapping model names to specialized database URLs.
                     For example, you can route 'ActivityLog' and 'WorkflowTrace' to
                     a data warehouse or ClickHouse database URL.
    """
    global _engines, _SessionLocal
    
    # Setup primary core engine
    actual_url = core_db_url or os.getenv("AGENTICAI_DB_URL", "sqlite:///agenticai.db")
    _engines["core"] = create_engine(
        actual_url, 
        echo=False, 
        connect_args={"check_same_thread": False} if "sqlite" in actual_url else {}
    )
    
    # Establish bound routing for specialized tables mapping
    binds = {}
    if routing_map:
        for tablename, url in routing_map.items():
            if url not in _engines:
                _engines[url] = create_engine(
                    url, echo=False,
                    connect_args={"check_same_thread": False} if "sqlite" in url else {}
                )
            
            # Map the specific Base metadata model class to the designated engine
            # using SQLAlchemy session-level binds dictionary
            for cls in Base.registry.mappers:
                if cls.class_.__tablename__ == tablename:
                    binds[cls.class_] = _engines[url]

    _SessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=_engines["core"],
        binds=binds
    )
    
    # Auto-create tables for the core DB
    Base.metadata.create_all(bind=_engines["core"])
    
    # Auto-create tables for specialized routing databases
    if binds:
        for mapper_class, engine in binds.items():
            mapper_class.__table__.create(bind=engine, checkfirst=True)
            
    return _engines

def get_session():
    """Provides a transactional scope aware of multi-DB routing."""
    if _SessionLocal is None:
        init_db()  # Auto-fallback init to core if not explicitly setup

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
