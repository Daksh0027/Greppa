"""
Tour API Endpoints for Phase 4: Guided Tours

Provides endpoints for generating and retrieving code tours.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository, TourRecord, TourStepRecord
from app.core.security import limiter, RateLimitConfig, sanitize_input
from app.ingestion.tour_generator import TourGenerator

router = APIRouter(prefix="/tours", tags=["tours"])


class TourStepResponse(BaseModel):
    step_order: int
    file_path: str
    start_line: int
    end_line: int
    title: str
    why_it_matters: str
    body: str
    
    class Config:
        from_attributes = True


class TourResponse(BaseModel):
    id: int
    repo_id: int
    tour_type: str
    title: str
    description: Optional[str]
    steps: List[TourStepResponse]
    
    class Config:
        from_attributes = True


class GenerateTourRequest(BaseModel):
    tour_type: str = "big_picture"  # big_picture or feature_trace
    title: Optional[str] = None
    max_steps: int = 12
    feature_query: Optional[str] = None  # Required for feature_trace


def generate_tour_background(
    repo_id: int,
    tour_type: str,
    max_steps: int,
    api_key: Optional[str],
    title: Optional[str] = None,
    feature_query: Optional[str] = None
):
    """Background task to generate a tour"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        generator = TourGenerator(db, repo_id, api_key=api_key)
        
        if tour_type == "feature_trace":
            if not feature_query:
                raise ValueError("feature_query is required for feature_trace tours")
            generator.generate_feature_trace_tour(
                query=feature_query,
                title=title,
                max_steps=max_steps
            )
        else:
            generator.generate_big_picture_tour(
                max_steps=max_steps,
                title=title
            )
    except Exception as e:
        import logging
        logging.error(f"Tour generation failed for repo {repo_id}: {e}")
    finally:
        db.close()


@router.get("/repo/{repo_id}", response_model=List[TourResponse])
@limiter.limit(RateLimitConfig.DEFAULT)
def list_tours(request: Request, repo_id: int, db: Session = Depends(get_db)):
    """List all tours for a repository"""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    tours = db.query(TourRecord).filter(TourRecord.repo_id == repo_id).all()
    
    # Load steps for each tour
    result = []
    for tour in tours:
        steps = db.query(TourStepRecord).filter(
            TourStepRecord.tour_id == tour.id
        ).order_by(TourStepRecord.step_order).all()
        
        tour_dict = {
            "id": tour.id,
            "repo_id": tour.repo_id,
            "tour_type": tour.tour_type,
            "title": tour.title,
            "description": tour.description,
            "steps": [
                {
                    "step_order": s.step_order,
                    "file_path": s.file_path,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "title": s.title,
                    "why_it_matters": s.why_it_matters,
                    "body": s.body
                }
                for s in steps
            ]
        }
        result.append(tour_dict)
    
    return result


@router.get("/{tour_id}", response_model=TourResponse)
def get_tour(tour_id: int, db: Session = Depends(get_db)):
    """Get a specific tour with all its steps"""
    tour = db.query(TourRecord).filter(TourRecord.id == tour_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    steps = db.query(TourStepRecord).filter(
        TourStepRecord.tour_id == tour_id
    ).order_by(TourStepRecord.step_order).all()
    
    return {
        "id": tour.id,
        "repo_id": tour.repo_id,
        "tour_type": tour.tour_type,
        "title": tour.title,
        "description": tour.description,
        "steps": [
            {
                "step_order": s.step_order,
                "file_path": s.file_path,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "title": s.title,
                "why_it_matters": s.why_it_matters,
                "body": s.body
            }
            for s in steps
        ]
    }


@router.post("/repo/{repo_id}/generate", response_model=dict)
@limiter.limit(RateLimitConfig.LLM_OPERATIONS)
def generate_tour(
    request: Request,
    repo_id: int,
    req: GenerateTourRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Generate a new tour for a repository.
    
    Tour types:
    - big_picture: Default architectural walkthrough from entry points
    - feature_trace: Custom tour based on a feature query
    """
    # Sanitize inputs
    if req.title:
        req.title = sanitize_input(req.title, max_length=255)
    if req.feature_query:
        req.feature_query = sanitize_input(req.feature_query, max_length=1000)
    
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if repo.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Repository must be in 'ready' status, currently: {repo.status}"
        )
    
    if req.tour_type == "feature_trace" and not req.feature_query:
        raise HTTPException(
            status_code=400,
            detail="feature_query is required for feature_trace tours"
        )
    
    # Start background generation
    background_tasks.add_task(
        generate_tour_background,
        repo_id=repo_id,
        tour_type=req.tour_type,
        max_steps=req.max_steps,
        api_key=x_gemini_api_key,
        title=req.title,
        feature_query=req.feature_query
    )
    
    return {
        "message": "Tour generation started",
        "repo_id": repo_id,
        "tour_type": req.tour_type
    }


@router.delete("/{tour_id}")
def delete_tour(tour_id: int, db: Session = Depends(get_db)):
    """Delete a tour"""
    tour = db.query(TourRecord).filter(TourRecord.id == tour_id).first()
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    db.delete(tour)
    db.commit()
    
    return {"message": f"Tour '{tour.title}' deleted successfully"}
