import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.repos import router as repos_router
from app.api.search import router as search_router
from app.api.graph import router as graph_router
from app.api.code import router as code_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("greppa.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Large-Repository Code Intelligence Engine with AST Symbol Graphs, PageRank & Multi-Step Agent Retrieval",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    logger.info("Initializing Greppa database tables...")
    init_db()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "gemini_configured": bool(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"))
    }

# Include API Routers
app.include_router(repos_router, prefix=settings.API_V1_STR)
app.include_router(search_router, prefix=settings.API_V1_STR)
app.include_router(graph_router, prefix=settings.API_V1_STR)
app.include_router(code_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
