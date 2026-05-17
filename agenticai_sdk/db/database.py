import os
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Global pointers supporting dynamic late-binding
_engine: Engine | None = None
_SessionLocal = None

def init_db(db_url: str | None = None):
    """
    Dynamically initializes the database connection.
    Supports customer choice for persistent storage mapping across all stages.
    (e.g., PostgreSQL, MySQL, SQLite)
    """
    global _engine, _SessionLocal
    
    # Defaults to env var AGENTICAI_DB_URL or local sqlite
    actual_url = db_url or os.getenv("AGENTICAI_DB_URL", "sqlite:///agenticai.db")
    
    _engine = create_engine(
        actual_url, 
        echo=False, 
        connect_args={"check_same_thread": False} if "sqlite" in actual_url else {}
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Auto-create tables for the selected DB
    Base.metadata.create_all(bind=_engine)
    return _engine

def get_session():
    """Provides a transactional scope around a series of operations."""
    if _SessionLocal is None:
        init_db()  # Auto-fallback init if not explicitly run

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

