"""
Tests for GitHub Integration (Phase 6)
"""
import pytest
from app.integrations.github_client import GitHubClient, GitHubIssue


class TestGitHubClient:
    """Tests for GitHub client"""
    
    def test_extract_repo_from_https_url(self):
        """Test extracting owner/repo from HTTPS URL"""
        client = GitHubClient()
        
        result = client.extract_repo_from_url("https://github.com/owner/repo")
        assert result == "owner/repo"
        
        result = client.extract_repo_from_url("https://github.com/owner/repo.git")
        assert result == "owner/repo"
    
    def test_extract_repo_from_ssh_url(self):
        """Test extracting owner/repo from SSH URL"""
        client = GitHubClient()
        
        result = client.extract_repo_from_url("git@github.com:owner/repo.git")
        assert result == "owner/repo"
    
    def test_extract_repo_invalid_url(self):
        """Test invalid URL returns None"""
        client = GitHubClient()
        
        result = client.extract_repo_from_url("https://example.com/not-github")
        assert result is None
        
        result = client.extract_repo_from_url("invalid-url")
        assert result is None
    
    def test_initialization_without_token(self):
        """Test initialization without GitHub token"""
        client = GitHubClient(github_token=None)
        assert client.token is None
        assert client.client is not None  # Should still create unauthenticated client
    
    def test_initialization_with_token(self):
        """Test initialization with GitHub token"""
        client = GitHubClient(github_token="fake_token_for_testing")
        assert client.token == "fake_token_for_testing"
    
    def test_extract_test_commands(self):
        """Test extracting test commands from contributing guidelines"""
        client = GitHubClient()
        
        contributing_text = """
        # Contributing Guide
        
        To run tests, use:
        ```
        pytest tests/
        npm test
        ```
        
        You can also run `make test` to execute all tests.
        """
        
        commands = client.extract_test_commands(contributing_text)
        
        # Should find test-related commands
        assert len(commands) > 0
        assert any("test" in cmd.lower() for cmd in commands)
    
    def test_extract_test_commands_empty(self):
        """Test extracting from text without test commands"""
        client = GitHubClient()
        
        commands = client.extract_test_commands("No test commands here")
        assert len(commands) == 0
    
    def test_extract_test_commands_none(self):
        """Test extracting from None"""
        client = GitHubClient()
        
        commands = client.extract_test_commands(None)
        assert len(commands) == 0


class TestGitHubIssue:
    """Tests for GitHubIssue model"""
    
    def test_issue_initialization(self):
        """Test creating a GitHub issue"""
        from datetime import datetime
        
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="This is a test issue",
            labels=["bug", "good first issue"],
            state="open",
            html_url="https://github.com/owner/repo/issues/123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            comments_count=5
        )
        
        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert "bug" in issue.labels
        assert "good first issue" in issue.labels
        assert issue.state == "open"
    
    def test_issue_to_dict(self):
        """Test converting issue to dictionary"""
        from datetime import datetime
        
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="Description",
            labels=["bug"],
            state="open",
            html_url="https://github.com/owner/repo/issues/123",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 2, 12, 0, 0),
            comments_count=3
        )
        
        result = issue.to_dict()
        
        assert result["number"] == 123
        assert result["title"] == "Test Issue"
        assert result["labels"] == ["bug"]
        assert result["comments"] == 3
        assert "url" in result
        assert result["matched_files"] == []
        assert result["contribution_plan"] is None
    
    def test_issue_with_matching_results(self):
        """Test issue with file matching results"""
        from datetime import datetime
        
        issue = GitHubIssue(
            number=123,
            title="Fix authentication bug",
            body="Auth token validation fails",
            labels=["bug"],
            state="open",
            html_url="https://github.com/owner/repo/issues/123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            comments_count=0
        )
        
        # Add matching results
        issue.matched_files = [
            {
                "file_path": "auth/token_validator.py",
                "relevance_score": 0.95,
                "symbols": []
            }
        ]
        issue.contribution_plan = "Fix the token validation logic"
        issue.difficulty = "Intermediate"
        issue.estimated_time = "2-3 hours"
        
        result = issue.to_dict()
        
        assert len(result["matched_files"]) == 1
        assert result["matched_files"][0]["file_path"] == "auth/token_validator.py"
        assert result["contribution_plan"] == "Fix the token validation logic"
        assert result["difficulty"] == "Intermediate"
        assert result["estimated_time"] == "2-3 hours"


class TestIssueFileMatcher:
    """Tests for issue-to-file matching"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.models import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        return Session()
    
    def test_matcher_initialization(self, mock_db_session):
        """Test IssueFileMatcher initialization"""
        from app.integrations.github_client import IssueFileMatcher
        
        matcher = IssueFileMatcher(mock_db_session, repo_id=1)
        assert matcher.repo_id == 1
        assert matcher.db == mock_db_session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
