import os
import shutil
import subprocess
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository, FileRecord, SymbolRecord
from app.core.config import settings
from app.core.security import limiter, RateLimitConfig, validate_repo_url, sanitize_input
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/repos", tags=["repositories"])

class RepoCreateRequest(BaseModel):
    name: str
    url_or_path: str
    default_branch: Optional[str] = "main"
    api_key: Optional[str] = None

class RepoResponse(BaseModel):
    id: int
    name: str
    url_or_path: str
    default_branch: str
    status: str
    status_detail: Optional[str]
    stats: Dict[str, Any]
    repo_summary: Optional[str]

    class Config:
        from_attributes = True

def run_ingestion_background(repo_id: int, target_dir: str, api_key: Optional[str] = None, incremental: bool = False):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        pipeline = IngestionPipeline(db=db, repo_id=repo_id, api_key=api_key)
        pipeline.run(target_dir, incremental=incremental)
    except Exception as e:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.status = "failed"
            repo.status_detail = f"Ingestion error: {str(e)}"
            repo.error_message = str(e)
            db.commit()
    finally:
        db.close()

@router.get("", response_model=List[RepoResponse])
@limiter.limit(RateLimitConfig.DEFAULT)
def list_repositories(request: Request, db: Session = Depends(get_db)):
    return db.query(Repository).order_by(Repository.id.desc()).all()

@router.post("", response_model=RepoResponse)
@limiter.limit(RateLimitConfig.INGESTION)
def create_repository(
    request: Request,
    req: RepoCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    # Validate and sanitize inputs
    req.name = sanitize_input(req.name, max_length=255)
    req.url_or_path = sanitize_input(req.url_or_path, max_length=1024)
    
    # Validate repo URL for security (prevent SSRF)
    if not validate_repo_url(req.url_or_path):
        raise HTTPException(status_code=400, detail="Invalid or disallowed repository URL")
    
    key = req.api_key or x_gemini_api_key
    # Check if local directory exists, or clone git repo
    target_dir = req.url_or_path
    if req.url_or_path.startswith("http://") or req.url_or_path.startswith("https://") or req.url_or_path.startswith("git@"):
        # Git clone shallow
        storage_base = settings.STORAGE_DIR
        os.makedirs(storage_base, exist_ok=True)
        repo_slug = req.name.replace("/", "_").replace("\\", "_")
        target_dir = os.path.join(storage_base, repo_slug)
        if not os.path.exists(target_dir):
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", req.url_or_path, target_dir],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail=f"Repository path '{target_dir}' does not exist or is not a directory.")

    repo = Repository(
        name=req.name,
        url_or_path=target_dir,
        default_branch=req.default_branch or "main",
        status="pending",
        status_detail="Queued for ingestion",
        stats={}
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Launch ingestion
    background_tasks.add_task(run_ingestion_background, repo.id, target_dir, key, False)
    return repo

@router.post("/demo", response_model=RepoResponse)
def create_demo_repository(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Creates and indexes an instant multi-module demonstration repository
    with Auth, Controllers, Gateway, and Analytics components.
    """
    demo_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, "demo_ecommerce_service"))
    os.makedirs(demo_dir, exist_ok=True)

    # Sample File 1: auth.py
    with open(os.path.join(demo_dir, "auth_service.py"), "w", encoding="utf-8") as f:
        f.write('''"""Authentication and Token Management Service."""

class AuthService:
    def __init__(self, secret: str = "super_secret"):
        self.secret = secret

    def authenticate_user(self, username: str, password_hash: str) -> bool:
        """Validates credentials against hashed store."""
        return self._verify_hash(username, password_hash)

    def _verify_hash(self, u: str, p: str) -> bool:
        return len(u) > 0 and len(p) > 5

    def issue_token(self, user_id: int) -> str:
        """Issues JWT bearer token."""
        return f"token_bearer_{user_id}_{self.secret[:4]}"
''')

    # Sample File 2: payment_gateway.py
    with open(os.path.join(demo_dir, "payment_gateway.py"), "w", encoding="utf-8") as f:
        f.write('''"""Payment Processing and Transaction Verification."""

class PaymentGateway:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def process_charge(self, customer_id: int, amount_cents: int) -> bool:
        """Executes payment charge against bank provider."""
        return amount_cents > 0 and self._check_fraud(customer_id)

    def _check_fraud(self, customer_id: int) -> bool:
        return customer_id > 0
''')

    # Sample File 3: user_controller.py
    with open(os.path.join(demo_dir, "user_controller.py"), "w", encoding="utf-8") as f:
        f.write('''"""User HTTP API Controller."""
from auth_service import AuthService
from payment_gateway import PaymentGateway

class UserController:
    def __init__(self):
        self.auth = AuthService()
        self.gateway = PaymentGateway("pk_live_demo")

    def handle_login(self, username: str, password: str):
        """Authenticates user and returns session."""
        if self.auth.authenticate_user(username, password):
            return self.auth.issue_token(101)
        return None

    def purchase_subscription(self, user_id: int, plan_cost: int):
        """Charges user and activates subscription."""
        return self.gateway.process_charge(user_id, plan_cost)
''')

    repo = Repository(
        name="Demo E-Commerce Service",
        url_or_path=demo_dir,
        default_branch="main",
        status="pending",
        status_detail="Initializing demo repository...",
        stats={}
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Ingest immediately in background
    background_tasks.add_task(run_ingestion_background, repo.id, demo_dir, x_gemini_api_key, False)
    return repo

@router.get("/{repo_id}", response_model=RepoResponse)
@limiter.limit(RateLimitConfig.DEFAULT)
def get_repository(request: Request, repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/{repo_id}/cost", response_model=Dict[str, Any])
@limiter.limit(RateLimitConfig.DEFAULT)
def get_repository_cost(request: Request, repo_id: int, db: Session = Depends(get_db)):
    """Get cost tracking information for a repository"""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    from app.core.observability import LLMCallLogger
    logger_instance = LLMCallLogger(db=db, repo_id=repo_id)
    cost_info = logger_instance.get_repo_total_cost(repo_id)
    
    return cost_info

@router.post("/{repo_id}/sync", response_model=RepoResponse)
def sync_repository(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.status = "syncing"
    repo.status_detail = "Starting incremental update comparison..."
    db.commit()

    background_tasks.add_task(run_ingestion_background, repo.id, repo.url_or_path, x_gemini_api_key, True)
    return repo

@router.delete("/{repo_id}")
def delete_repository(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    db.delete(repo)
    db.commit()
    return {"message": f"Repository '{repo.name}' deleted successfully."}
