from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository
from app.search.hybrid import HybridSearchEngine
from app.search.expander import GraphExpander
from app.search.packer import ContextPacker
from app.agent.loop import CodebaseAgent

router = APIRouter(prefix="/repos/{repo_id}", tags=["search & agent"])

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 12
    expand_graph: Optional[bool] = True
    token_budget: Optional[int] = 6000
    api_key: Optional[str] = None

class AgentQueryRequest(BaseModel):
    query: str
    max_steps: Optional[int] = 6
    token_budget: Optional[int] = 8000
    api_key: Optional[str] = None

@router.post("/search")
def search_repository(
    repo_id: int,
    req: SearchRequest,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    key = req.api_key or x_gemini_api_key
    searcher = HybridSearchEngine(db, repo_id, api_key=key)
    hits = searcher.search(req.query, top_k=req.top_k or 12)

    expanded_contexts = []
    if req.expand_graph and hits:
        expander = GraphExpander(db, repo_id)
        expanded = expander.expand_hits(hits, max_expanded=5)
        expanded_contexts = [e.to_dict() for e in expanded]

    return {
        "query": req.query,
        "total_hits": len(hits),
        "hits": [h.to_dict() for h in hits],
        "expanded_graph_contexts": expanded_contexts
    }

@router.post("/agent")
def run_agent_query(
    repo_id: int,
    req: AgentQueryRequest,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    key = req.api_key or x_gemini_api_key
    agent = CodebaseAgent(
        db=db,
        repo_id=repo_id,
        api_key=key,
        max_steps=req.max_steps or 6
    )
    result = agent.run(req.query)
    return result.to_dict()

@router.get("/tour")
def get_guided_tour(repo_id: int, db: Session = Depends(get_db)):
    """
    Auto-generates an intelligent reading order through the codebase
    based on PageRank importance scores and symbol graph centrality.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.core.models import FileRecord, SymbolRecord
    files = db.query(FileRecord).filter(
        FileRecord.repo_id == repo_id
    ).order_by(FileRecord.importance_score.desc()).all()

    tour_stops = []
    for step_num, f in enumerate(files[:10], start=1):
        symbols = db.query(SymbolRecord).filter(
            SymbolRecord.file_id == f.id
        ).order_by(SymbolRecord.importance_score.desc()).limit(4).all()

        # Categorize architectural tier
        score = f.importance_score or 1.0
        if score >= 2.0:
            tier = "Core Foundation & Backbone"
            why_read = "Highest structural centrality; imported and called extensively across the system."
        elif score >= 1.2:
            tier = "Business Logic & Orchestration"
            why_read = "Implements core domain operations and workflows."
        else:
            tier = "Supporting Module & Utilities"
            why_read = "Provides targeted utility, integration, or peripheral functionality."

        tour_stops.append({
            "step": step_num,
            "file_path": f.path,
            "importance_score": round(score, 3),
            "tier": tier,
            "why_read": why_read,
            "summary": f.summary or "Core module logic",
            "line_count": f.line_count,
            "key_symbols": [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "signature": s.signature,
                    "start_line": s.start_line,
                    "end_line": s.end_line
                }
                for s in symbols
            ]
        })

    return {
        "repo_name": repo.name,
        "repo_summary": repo.repo_summary,
        "total_stops": len(tour_stops),
        "tour_stops": tour_stops
    }

class IssueMatchRequest(BaseModel):
    title: str
    description: str
    api_key: Optional[str] = None

@router.post("/issues/match")
def match_good_first_issue(
    repo_id: int,
    req: IssueMatchRequest,
    db: Session = Depends(get_db),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Good-first-issue matching engine:
    Analyzes an issue description, locates relevant symbols via hybrid search,
    computes complexity/side-effects, and generates a contributor onboarding roadmap.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    key = req.api_key or x_gemini_api_key
    searcher = HybridSearchEngine(db, repo_id, api_key=key)
    query_text = f"{req.title} {req.description}"
    hits = searcher.search(query_text, top_k=6)

    from app.core.models import SymbolEdgeRecord
    expander = GraphExpander(db, repo_id)
    expanded = expander.expand_hits(hits, max_expanded=4)

    # Calculate complexity
    affected_files = list(dict.fromkeys(h.file_path for h in hits))
    total_callers = sum(len(e.callers) for e in expanded)

    if len(affected_files) <= 2 and total_callers <= 3:
        difficulty = "Good First Issue (Beginner Friendly)"
        difficulty_color = "emerald"
    elif len(affected_files) <= 4:
        difficulty = "Intermediate (Moderate Fan-out)"
        difficulty_color = "amber"
    else:
        difficulty = "Advanced (Broad Architectural Impact)"
        difficulty_color = "red"

    # Generate guide
    from app.llm.provider import get_llm_provider
    llm = get_llm_provider(api_key=key)
    snippets = [f"- `{h.symbol_name}` in `{h.file_path}` (Lines {h.start_line}-{h.end_line})" for h in hits[:5]]

    guide_prompt = (
        f"You are onboarding a developer to fix this issue in '{repo.name}'.\n"
        f"Issue Title: {req.title}\n"
        f"Issue Description: {req.description}\n\n"
        f"Relevant Code Candidates:\n" + "\n".join(snippets) + "\n\n"
        "Provide:\n"
        "1. Exact files to inspect\n"
        "2. Step-by-step implementation plan\n"
        "3. Potential regressions or dependents to test"
    )

    roadmap = llm.generate_answer(
        prompt=guide_prompt,
        system_instruction="You are Greppa's issue matching and developer onboarding assistant. Be concrete, cite file paths and line numbers."
    )

    return {
        "issue_title": req.title,
        "difficulty": difficulty,
        "difficulty_color": difficulty_color,
        "affected_files": affected_files,
        "primary_symbols": [h.to_dict() for h in hits[:5]],
        "roadmap": roadmap
    }
