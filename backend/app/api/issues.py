"""
GitHub Issues API Endpoints for Phase 6: Good First Issue Matching

Provides endpoints for fetching and matching GitHub issues to code files.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import Repository
from app.core.security import limiter, RateLimitConfig, sanitize_input
from app.integrations.github_client import GitHubIssueService, GitHubIssue

router = APIRouter(prefix="/issues", tags=["github-issues"])


class IssueMatchedFile(BaseModel):
    file_path: str
    relevance_score: float
    symbols: List[dict]


class IssueResponse(BaseModel):
    number: int
    title: str
    body: Optional[str]
    labels: List[str]
    state: str
    url: str
    created_at: Optional[str]
    updated_at: Optional[str]
    comments: int
    matched_files: List[dict]
    contribution_plan: Optional[str]
    difficulty: Optional[str]
    estimated_time: Optional[str]


class GoodFirstIssuesRequest(BaseModel):
    labels: Optional[List[str]] = None
    max_count: int = 20


@router.post("/repo/{repo_id}/good-first-issues", response_model=List[IssueResponse])
@limiter.limit(RateLimitConfig.LLM_OPERATIONS)
def get_good_first_issues(
    request: Request,
    repo_id: int,
    req: GoodFirstIssuesRequest,
    db: Session = Depends(get_db),
    x_github_token: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Fetch and match good first issues for a repository.
    
    This endpoint:
    1. Fetches open issues from GitHub with labels like "good first issue"
    2. Matches each issue to relevant code files using hybrid search
    3. Generates an AI-powered contribution plan
    4. Estimates difficulty and time required
    
    Headers:
    - X-GitHub-Token: Optional GitHub personal access token for higher rate limits
    - X-Gemini-API-Key: Optional Gemini API key for LLM-based plan generation
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if repo.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Repository must be indexed first. Current status: {repo.status}"
        )
    
    # Check if repo URL is a GitHub URL
    repo_url = repo.url_or_path
    if not ("github.com" in repo_url or "github:" in repo_url):
        raise HTTPException(
            status_code=400,
            detail="Repository must be a GitHub repository to fetch issues"
        )
    
    # Initialize service
    service = GitHubIssueService(
        db=db,
        repo_id=repo_id,
        github_token=x_github_token,
        api_key=x_gemini_api_key
    )
    
    # Fetch and match issues
    try:
        issues = service.get_good_first_issues(
            repo_url=repo_url,
            labels=req.labels,
            max_count=req.max_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch issues: {str(e)}"
        )
    
    # Convert to response format
    return [issue.to_dict() for issue in issues]


@router.get("/repo/{repo_id}/github-info", response_model=dict)
def get_github_repo_info(
    repo_id: int,
    db: Session = Depends(get_db),
    x_github_token: Optional[str] = Header(None)
):
    """
    Get GitHub repository information and contributing guidelines.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo_url = repo.url_or_path
    if not ("github.com" in repo_url or "github:" in repo_url):
        raise HTTPException(
            status_code=400,
            detail="Repository must be a GitHub repository"
        )
    
    from app.integrations.github_client import GitHubClient
    
    client = GitHubClient(x_github_token)
    repo_identifier = client.extract_repo_from_url(repo_url)
    
    if not repo_identifier:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    # Fetch repository info
    gh_repo = client.get_repository(repo_identifier)
    if not gh_repo:
        raise HTTPException(status_code=404, detail="GitHub repository not found")
    
    # Fetch contributing guidelines
    contributing = client.fetch_contributing_guidelines(repo_identifier)
    test_commands = client.extract_test_commands(contributing)
    
    return {
        "full_name": gh_repo.full_name,
        "description": gh_repo.description,
        "stars": gh_repo.stargazers_count,
        "forks": gh_repo.forks_count,
        "open_issues": gh_repo.open_issues_count,
        "language": gh_repo.language,
        "has_contributing": contributing is not None,
        "contributing_excerpt": contributing[:500] if contributing else None,
        "test_commands": test_commands,
        "html_url": gh_repo.html_url
    }


@router.get("/repo/{repo_id}/issue/{issue_number}", response_model=IssueResponse)
def match_single_issue(
    repo_id: int,
    issue_number: int,
    db: Session = Depends(get_db),
    x_github_token: Optional[str] = Header(None),
    x_gemini_api_key: Optional[str] = Header(None)
):
    """
    Fetch and match a specific issue by number.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if repo.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Repository must be indexed first. Current status: {repo.status}"
        )
    
    repo_url = repo.url_or_path
    if not ("github.com" in repo_url or "github:" in repo_url):
        raise HTTPException(
            status_code=400,
            detail="Repository must be a GitHub repository"
        )
    
    from app.integrations.github_client import GitHubClient, IssueFileMatcher
    
    # Fetch the specific issue
    client = GitHubClient(x_github_token)
    repo_identifier = client.extract_repo_from_url(repo_url)
    
    if not repo_identifier:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    gh_repo = client.get_repository(repo_identifier)
    if not gh_repo:
        raise HTTPException(status_code=404, detail="GitHub repository not found")
    
    try:
        gh_issue = gh_repo.get_issue(issue_number)
        
        # Convert to our format
        from app.integrations.github_client import GitHubIssue as GHI
        issue = GHI(
            number=gh_issue.number,
            title=gh_issue.title,
            body=gh_issue.body,
            labels=[label.name for label in gh_issue.labels],
            state=gh_issue.state,
            html_url=gh_issue.html_url,
            created_at=gh_issue.created_at,
            updated_at=gh_issue.updated_at,
            comments_count=gh_issue.comments
        )
        
        # Match to files
        matcher = IssueFileMatcher(db, repo_id, api_key=x_gemini_api_key)
        matched_files = matcher.match_issue_to_files(issue, top_k=5)
        issue.matched_files = matched_files
        
        # Generate plan
        if matched_files:
            contributing = client.fetch_contributing_guidelines(repo_identifier)
            plan, difficulty, time = matcher.generate_contribution_plan(
                issue,
                matched_files,
                contributing
            )
            issue.contribution_plan = plan
            issue.difficulty = difficulty
            issue.estimated_time = time
        
        return issue.to_dict()
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch or match issue: {str(e)}"
        )
