import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.models import Base

logger = logging.getLogger("greppa.db")

# Setup primary engine (SQLite fallback or PostgreSQL)
def get_engine():
    # If SQLite fallback is enabled or Postgres is localhost and unverified
    db_url = settings.DATABASE_SYNC_URL
    if settings.USE_SQLITE_FALLBACK:
        # Check if we should use SQLite
        sqlite_file = os.path.abspath(settings.SQLITE_DB_PATH)
        os.makedirs(os.path.dirname(sqlite_file) if os.path.dirname(sqlite_file) else ".", exist_ok=True)
        return create_engine(
            f"sqlite:///{sqlite_file}",
            connect_args={"check_same_thread": False}
        )
    return create_engine(db_url, pool_pre_ping=True)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create tables if they don't exist"""
    global engine, SessionLocal
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database init warning (switching to SQLite): {e}")
        # Fallback to local SQLite if Postgres connection failed
        sqlite_file = os.path.abspath("greppa.db")
        fallback_engine = create_engine(f"sqlite:///{sqlite_file}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=fallback_engine)
        engine = fallback_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database fallback to SQLite initialized successfully.")

def get_db():
    """Dependency for FastAPI route handlers"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
