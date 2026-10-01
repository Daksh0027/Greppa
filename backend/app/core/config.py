import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Greppa"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://greppa:greppa@localhost:5432/greppa"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://greppa:greppa@localhost:5432/greppa"
    # Fallback SQLite DB path for standalone local testing without Docker
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_DB_PATH: str = "greppa.db"
    
    # Redis Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
    
    # LLM Settings (Defaults to Google Gemini)
    GEMINI_API_KEY: Optional[str] = None
    # Fast model for bulk hierarchical summaries
    CHEAP_MODEL_NAME: str = "gemini-2.0-flash"
    # Strong model for answering queries and running agent loops
    STRONG_MODEL_NAME: str = "gemini-2.0-pro"
    # Embedding model
    EMBEDDING_MODEL_NAME: str = "text-embedding-004"
    EMBEDDING_DIM: int = 768
    
    # Agent & Search settings
    DEFAULT_TOKEN_BUDGET: int = 8000
    MAX_AGENT_STEPS: int = 6
    PAGERANK_DAMPING: float = 0.85
    PAGERANK_WEIGHT: float = 0.35
    
    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings()
