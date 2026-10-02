"""
GitHub Integration for Phase 6: Issue Matching and Good First Issue Recommendations

Provides functionality to:
1. Pull open issues from GitHub repositories
2. Match issues to likely code files using hybrid search
3. Generate contribution plans with file suggestions and difficulty estimates
4. Extract CONTRIBUTING.md guidelines
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from github import Github, GithubException, Repository as GHRepo, Issue as GHIssue
from sqlalchemy.orm import Session
from app.core.models import Repository, FileRecord
from app.search.hybrid import HybridSearchEngine
from app.llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger("greppa.github")


class GitHubIssue:
    """Represents a GitHub issue with matching information"""
    def __init__(
        self,
        number: int,
        title: str,
        body: Optional[str],
        labels: List[str],
        state: str,
        html_url: str,
        created_at: datetime,
        updated_at: datetime,
        comments_count: int
    ):
        self.number = number
        self.title = title
        self.body = body or ""
        self.labels = labels
        self.state = state
        self.html_url = html_url
        self.created_at = created_at
        self.updated_at = updated_at
        self.comments_count = comments_count
        
        # Matching results (populated later)
        self.matched_files: List[Dict[str, Any]] = []
        self.contribution_plan: Optional[str] = None
        self.difficulty: Optional[str] = None
        self.estimated_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "labels": self.labels,
            "state": self.state,
            "url": self.html_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "comments": self.comments_count,
            "matched_files": self.matched_files,
            "contribution_plan": self.contribution_plan,
            "difficulty": self.difficulty,
            "estimated_time": self.estimated_time
        }


class GitHubClient:
    """Client for GitHub API integration"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            github_token: Personal access token or App installation token.
                         If None, uses unauthenticated access (rate limited to 60/hour)
        """
        self.token = github_token or os.environ.get("GITHUB_TOKEN")
        if self.token:
            self.client = Github(self.token)
            logger.info("GitHub client initialized with authentication")
        else:
            self.client = Github()
            logger.warning("GitHub client initialized without authentication (rate limited)")
    
    def extract_repo_from_url(self, url: str) -> Optional[str]:
        """
        Extracts owner/repo from GitHub URL.
        
        Examples:
        - https://github.com/owner/repo -> owner/repo
        - git@github.com:owner/repo.git -> owner/repo
        """
        patterns = [
            r'github\.com[:/]([^/]+)/([^/.]+)',
            r'github\.com/([^/]+)/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner, repo = match.groups()
                repo = repo.replace('.git', '')
                return f"{owner}/{repo}"
        
        return None
    
    def get_repository(self, repo_identifier: str) -> Optional[GHRepo]:
        """
        Gets a GitHub repository by owner/repo identifier.
        
        Args:
            repo_identifier: Format "owner/repo"
        """
        try:
            return self.client.get_repo(repo_identifier)
        except GithubException as e:
            logger.error(f"Failed to fetch repository {repo_identifier}: {e}")
            return None
    
    def fetch_issues(
        self,
        repo_identifier: str,
        labels: Optional[List[str]] = None,
        state: str = "open",
        max_count: int = 50
    ) -> List[GitHubIssue]:
        """
        Fetches issues from a GitHub repository.
        
        Args:
            repo_identifier: Format "owner/repo"
            labels: Filter by labels (e.g., ["good first issue", "help wanted"])
            state: "open", "closed", or "all"
            max_count: Maximum number of issues to fetch
        """
        repo = self.get_repository(repo_identifier)
        if not repo:
            return []
        
        try:
            # Build label filter
            label_objs = []
            if labels:
                for label_name in labels:
                    try:
                        label_objs.append(repo.get_label(label_name))
                    except GithubException:
                        logger.warning(f"Label '{label_name}' not found in {repo_identifier}")
            
            # Fetch issues
            if label_objs:
                gh_issues = repo.get_issues(state=state, labels=label_objs)
            else:
                gh_issues = repo.get_issues(state=state)
            
            # Convert to our format
            issues: List[GitHubIssue] = []
            for gh_issue in gh_issues[:max_count]:
                # Skip pull requests
                if gh_issue.pull_request:
                    continue
                
                issue = GitHubIssue(
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
                issues.append(issue)
            
            logger.info(f"Fetched {len(issues)} issues from {repo_identifier}")
            return issues
        
        except GithubException as e:
            logger.error(f"Failed to fetch issues from {repo_identifier}: {e}")
            return []
    
    def fetch_contributing_guidelines(self, repo_identifier: str) -> Optional[str]:
        """
        Fetches CONTRIBUTING.md or similar contribution guidelines.
        """
        repo = self.get_repository(repo_identifier)
        if not repo:
            return None
        
        # Try common filenames
        contributing_files = [
            "CONTRIBUTING.md",
            "CONTRIBUTING",
            ".github/CONTRIBUTING.md",
            "docs/CONTRIBUTING.md",
            "CONTRIBUTE.md"
        ]
        
        for filename in contributing_files:
            try:
                content = repo.get_contents(filename)
                if hasattr(content, 'decoded_content'):
                    decoded = content.decoded_content.decode('utf-8')
                    logger.info(f"Found {filename} in {repo_identifier}")
                    return decoded
            except GithubException:
                continue
        
        logger.info(f"No contributing guidelines found in {repo_identifier}")
        return None
    
    def extract_test_commands(self, contributing_text: Optional[str]) -> List[str]:
        """
        Extracts test commands from contributing guidelines.
        Looks for common patterns like "npm test", "pytest", etc.
        """
        if not contributing_text:
            return []
        
        commands = []
        
        # Common test command patterns
        patterns = [
            r'`([^`]*(?:test|pytest|npm test|yarn test|make test)[^`]*)`',
            r'\$\s+([^\n]*(?:test|pytest)[^\n]*)',
            r'```[^\n]*\n([^\n]*(?:test|pytest)[^\n]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, contributing_text, re.IGNORECASE)
            commands.extend(matches)
        
        # Deduplicate and clean
        unique_commands = list(set([cmd.strip() for cmd in commands if cmd.strip()]))
        return unique_commands[:5]  # Limit to top 5


class IssueFileMatcher:
    """Matches GitHub issues to relevant code files using hybrid search"""
    
    def __init__(self, db: Session, repo_id: int, api_key: Optional[str] = None):
        self.db = db
        self.repo_id = repo_id
        self.search_engine = HybridSearchEngine(db, repo_id, api_key=api_key)
        self.llm = get_llm_provider(api_key=api_key)
    
    def match_issue_to_files(
        self,
        issue: GitHubIssue,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Matches an issue to likely code files using hybrid search.
        
        Returns a list of matched files with scores and reasons.
        """
        # Build search query from issue title and body
        query = f"{issue.title}\n\n{issue.body[:500]}"
        
        # Search for relevant code
        hits = self.search_engine.search(query, top_k=top_k)
        
        # Convert to file-level matches (deduplicate by file)
        file_matches: Dict[str, Dict[str, Any]] = {}
        
        for hit in hits:
            file_path = hit.file_path
            if file_path not in file_matches:
                file_matches[file_path] = {
                    "file_path": file_path,
                    "relevance_score": hit.rrf_score,
                    "symbols": [],
                    "reason": ""
                }
            
            file_matches[file_path]["symbols"].append({
                "name": hit.symbol_name,
                "line_range": f"{hit.start_line}-{hit.end_line}",
                "snippet": hit.content[:200]
            })
        
        # Sort by relevance
        ranked_files = sorted(
            file_matches.values(),
            key=lambda x: x["relevance_score"],
            reverse=True
        )
        
        return ranked_files[:top_k]
    
    def generate_contribution_plan(
        self,
        issue: GitHubIssue,
        matched_files: List[Dict[str, Any]],
        contributing_guidelines: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generates an AI-powered contribution plan for the issue.
        
        Returns:
            (plan_text, difficulty, estimated_time)
        """
        # Build context
        files_context = "\n".join([
            f"- {f['file_path']} (relevance: {f['relevance_score']:.3f})"
            for f in matched_files[:3]
        ])
        
        guidelines_context = ""
        if contributing_guidelines:
            guidelines_context = f"\n\nContributing Guidelines:\n{contributing_guidelines[:1000]}"
        
        prompt = f"""You are helping a developer make their first contribution to an open-source project.

**Issue #{issue.number}: {issue.title}**
Labels: {', '.join(issue.labels)}

Description:
{issue.body[:800]}

**Likely Files to Modify:**
{files_context}
{guidelines_context}

Generate a contribution plan with:
1. **Summary**: What needs to be done (2-3 sentences)
2. **Files to Touch**: Which files need changes and why
3. **Approach**: Step-by-step approach to implement the fix/feature
4. **Testing**: How to test the changes
5. **Difficulty**: Rate as "Beginner", "Intermediate", or "Advanced"
6. **Estimated Time**: Estimate like "1-2 hours", "2-4 hours", "4-8 hours"

Format your response as:
DIFFICULTY: [level]
ESTIMATED_TIME: [time]
PLAN:
[detailed plan]
"""

        try:
            response = self.llm.generate_answer(
                prompt=prompt,
                system_instruction="You are an expert software engineer mentoring new contributors."
            )
            
            # Parse response
            difficulty = "Intermediate"
            estimated_time = "2-4 hours"
            plan = response
            
            # Extract structured fields if present
            diff_match = re.search(r'DIFFICULTY:\s*(\w+)', response, re.IGNORECASE)
            if diff_match:
                difficulty = diff_match.group(1)
            
            time_match = re.search(r'ESTIMATED_TIME:\s*([^\n]+)', response, re.IGNORECASE)
            if time_match:
                estimated_time = time_match.group(1).strip()
            
            plan_match = re.search(r'PLAN:\s*(.+)', response, re.DOTALL | re.IGNORECASE)
            if plan_match:
                plan = plan_match.group(1).strip()
            
            return plan, difficulty, estimated_time
        
        except Exception as e:
            logger.error(f"Failed to generate contribution plan: {e}")
            return (
                "Review the issue and matched files to understand what needs to be changed.",
                "Intermediate",
                "2-4 hours"
            )


class GitHubIssueService:
    """High-level service for GitHub issue matching"""
    
    def __init__(
        self,
        db: Session,
        repo_id: int,
        github_token: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.db = db
        self.repo_id = repo_id
        self.github_client = GitHubClient(github_token)
        self.matcher = IssueFileMatcher(db, repo_id, api_key)
    
    def get_good_first_issues(
        self,
        repo_url: str,
        labels: Optional[List[str]] = None,
        max_count: int = 20
    ) -> List[GitHubIssue]:
        """
        Fetches and matches good first issues for a repository.
        
        Args:
            repo_url: GitHub repository URL
            labels: Label filters (defaults to ["good first issue", "help wanted"])
            max_count: Maximum issues to fetch
        """
        # Extract repo identifier
        repo_identifier = self.github_client.extract_repo_from_url(repo_url)
        if not repo_identifier:
            logger.error(f"Could not extract repo identifier from URL: {repo_url}")
            return []
        
        # Default labels for good first issues
        if labels is None:
            labels = ["good first issue", "help wanted", "beginner-friendly"]
        
        # Fetch issues
        issues = self.github_client.fetch_issues(
            repo_identifier=repo_identifier,
            labels=labels,
            state="open",
            max_count=max_count
        )
        
        # Fetch contributing guidelines
        contributing = self.github_client.fetch_contributing_guidelines(repo_identifier)
        
        # Match each issue to files and generate plans
        for issue in issues:
            logger.info(f"Matching issue #{issue.number}: {issue.title}")
            
            # Find matching files
            matched_files = self.matcher.match_issue_to_files(issue, top_k=5)
            issue.matched_files = matched_files
            
            # Generate contribution plan
            if matched_files:
                plan, difficulty, time = self.matcher.generate_contribution_plan(
                    issue,
                    matched_files,
                    contributing
                )
                issue.contribution_plan = plan
                issue.difficulty = difficulty
                issue.estimated_time = time
        
        return issues
