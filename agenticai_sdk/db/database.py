import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DatabaseURL = os.getenv("AGENTICAI_DB_URL", "sqlite:///agenticai.db")

engine = create_engine(
    DatabaseURL, 
    echo=False, 
    connect_args={"check_same_thread": False} if "sqlite" in DatabaseURL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
