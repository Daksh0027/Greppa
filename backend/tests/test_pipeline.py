import os
import shutil
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models import Base, Repository, FileRecord, SymbolRecord
from app.ingestion.parser import parse_code_file
from app.ingestion.graph_builder import SymbolGraph
from app.ingestion.chunker import chunk_file_by_symbols
from app.ingestion.pipeline import IngestionPipeline
from app.search.hybrid import HybridSearchEngine
from app.search.expander import GraphExpander
from app.search.packer import ContextPacker
from app.agent.loop import CodebaseAgent

SAMPLE_AUTH_SERVICE = '''"""Authentication and token validation service."""

class AuthService:
    def __init__(self, secret: str):
        self.secret = secret

    def authenticate_user(self, username: str, password_hash: str) -> bool:
        """Validates credentials and issues token."""
        return self._verify_hash(username, password_hash)

    def _verify_hash(self, u: str, p: str) -> bool:
        return len(u) > 0 and len(p) > 5

def generate_session_token(user_id: int) -> str:
    """Generates secure bearer token."""
    return f"token_{user_id}"
'''

SAMPLE_USER_CONTROLLER = '''"""User API Controller."""
from auth_service import AuthService, generate_session_token

class UserController:
    def __init__(self):
        self.auth = AuthService("secret_123")

    def handle_login(self, username: str, password: str):
        valid = self.auth.authenticate_user(username, password)
        if valid:
            return generate_session_token(42)
        return None
'''

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_ast_symbol_parsing():
    parsed = parse_code_file(SAMPLE_AUTH_SERVICE, "auth_service.py", "python")
    assert parsed.rel_path == "auth_service.py"
    
    names = [s.name for s in parsed.symbols]
    assert "AuthService" in names
    assert "AuthService.authenticate_user" in names
    assert "AuthService._verify_hash" in names
    assert "generate_session_token" in names

    # Check caller and callee extraction
    auth_method = next(s for s in parsed.symbols if s.name == "AuthService.authenticate_user")
    assert "_verify_hash" in auth_method.calls
    assert auth_method.start_line > 0
    assert auth_method.end_line >= auth_method.start_line

def test_symbol_graph_and_pagerank():
    graph = SymbolGraph()
    p1 = parse_code_file(SAMPLE_AUTH_SERVICE, "auth_service.py", "python")
    p2 = parse_code_file(SAMPLE_USER_CONTROLLER, "user_controller.py", "python")

    graph.add_file(p1)
    graph.add_file(p2)
    graph.build_edges()

    scores = graph.compute_pagerank()
    assert len(scores) > 0

    # User controller calls AuthService.authenticate_user, so AuthService should receive incoming edges
    file_scores = graph.get_file_importance_scores(scores)
    assert "auth_service.py" in file_scores
    assert "user_controller.py" in file_scores

    rf_graph = graph.get_react_flow_graph()
    assert "nodes" in rf_graph
    assert "edges" in rf_graph
    assert len(rf_graph["nodes"]) > 0

def test_chunker_by_symbol():
    p = parse_code_file(SAMPLE_AUTH_SERVICE, "auth_service.py", "python")
    chunks = chunk_file_by_symbols(p, SAMPLE_AUTH_SERVICE)
    
    assert len(chunks) >= 4
    method_chunk = next(c for c in chunks if c.symbol_name == "AuthService.authenticate_user")
    assert method_chunk.parent_class == "AuthService"
    assert "def AuthService.authenticate_user" in method_chunk.signature
    assert "Validates credentials" in method_chunk.docstring

def test_full_pipeline_ingestion_and_search(test_db):
    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "auth_service.py"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_AUTH_SERVICE)
        with open(os.path.join(temp_dir, "user_controller.py"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_USER_CONTROLLER)

        repo = Repository(name="TestRepo", url_or_path=temp_dir, status="pending")
        test_db.add(repo)
        test_db.commit()
        test_db.refresh(repo)

        pipeline = IngestionPipeline(test_db, repo.id)
        stats = pipeline.run(temp_dir, incremental=False)

        assert stats["total_files"] == 2
        assert stats["total_symbols"] > 0
        assert repo.status == "ready"

        # Test Hybrid Search
        searcher = HybridSearchEngine(test_db, repo.id)
        results = searcher.search("authenticate user token validation", top_k=5)
        assert len(results) > 0
        top = results[0]
        assert "auth" in top.file_path.lower() or "token" in top.content.lower()

        # Test Graph Expansion
        expander = GraphExpander(test_db, repo.id)
        expanded = expander.expand_hits(results, max_expanded=2)
        assert len(expanded) > 0

        # Test Context Packing
        packer = ContextPacker(token_budget=4000)
        packed = packer.pack(expanded)
        assert len(packed.citations) > 0
        assert "File:" in packed.context_str

        # Test Multi-Step Agent Loop
        agent = CodebaseAgent(test_db, repo.id, max_steps=4)
        agent_res = agent.run("How does authentication and token generation work?")
        assert len(agent_res.steps) >= 2
        assert len(agent_res.citations) > 0
        assert agent_res.answer != ""

        # Test Incremental Update
        # Modify user_controller.py
        with open(os.path.join(temp_dir, "user_controller.py"), "a", encoding="utf-8") as f:
            f.write("\ndef logout_user():\n    return True\n")

        # Run pipeline incrementally
        inc_stats = pipeline.run(temp_dir, incremental=True)
        # auth_service.py was NOT modified, user_controller was modified
        assert inc_stats["processed_files"] == 1
        assert inc_stats["unchanged_files"] == 1

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
