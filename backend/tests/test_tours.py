"""
Tests for Tour Generation System (Phase 4)
"""
import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.models import Base, Repository, FileRecord, SymbolRecord, SymbolEdgeRecord
from app.ingestion.tour_generator import TourGenerator


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_repo(db_session):
    """Create a sample repository with files and symbols"""
    repo = Repository(
        name="TestRepo",
        url_or_path="/tmp/test",
        status="ready"
    )
    db_session.add(repo)
    db_session.flush()
    
    # Add files
    main_file = FileRecord(
        repo_id=repo.id,
        path="main.py",
        language="python",
        content_hash="abc123",
        line_count=50,
        importance_score=10.0,
        is_entrypoint=True
    )
    db_session.add(main_file)
    db_session.flush()
    
    utils_file = FileRecord(
        repo_id=repo.id,
        path="utils.py",
        language="python",
        content_hash="def456",
        line_count=30,
        importance_score=5.0
    )
    db_session.add(utils_file)
    db_session.flush()
    
    # Add symbols
    main_func = SymbolRecord(
        repo_id=repo.id,
        file_id=main_file.id,
        name="main",
        kind="function",
        signature="def main():",
        start_line=1,
        end_line=10,
        content="def main():\n    print('Hello')",
        importance_score=10.0
    )
    db_session.add(main_func)
    
    helper_func = SymbolRecord(
        repo_id=repo.id,
        file_id=utils_file.id,
        name="helper",
        kind="function",
        signature="def helper():",
        start_line=1,
        end_line=5,
        content="def helper():\n    return True",
        importance_score=3.0
    )
    db_session.add(helper_func)
    db_session.flush()
    
    # Add call edge
    edge = SymbolEdgeRecord(
        repo_id=repo.id,
        source_file="main.py",
        source_symbol="main",
        target_file="utils.py",
        target_symbol="helper",
        edge_type="calls"
    )
    db_session.add(edge)
    
    db_session.commit()
    return repo


def test_tour_generator_initialization(db_session, sample_repo):
    """Test TourGenerator initialization"""
    generator = TourGenerator(db_session, sample_repo.id)
    assert generator.repo_id == sample_repo.id
    assert generator.repo is not None
    assert generator.repo.name == "TestRepo"


def test_find_entry_points(db_session, sample_repo):
    """Test entry point detection"""
    generator = TourGenerator(db_session, sample_repo.id)
    entry_points = generator._find_entry_points()
    
    assert len(entry_points) > 0
    assert any(f.is_entrypoint for f in entry_points)
    assert any(f.path == "main.py" for f in entry_points)


def test_get_top_files_by_importance(db_session, sample_repo):
    """Test getting top files by PageRank score"""
    generator = TourGenerator(db_session, sample_repo.id)
    top_files = generator._get_top_files_by_importance(limit=2)
    
    assert len(top_files) <= 2
    # Should be sorted by importance
    if len(top_files) == 2:
        assert top_files[0].importance_score >= top_files[1].importance_score


def test_symbol_to_tour_step(db_session, sample_repo):
    """Test converting a symbol to a tour step"""
    generator = TourGenerator(db_session, sample_repo.id)
    
    symbol = db_session.query(SymbolRecord).filter(
        SymbolRecord.name == "main"
    ).first()
    file = db_session.query(FileRecord).filter(FileRecord.id == symbol.file_id).first()
    
    step = generator._symbol_to_tour_step(symbol, file)
    
    assert step.file_path == "main.py"
    assert step.symbol_name == "main"
    assert step.start_line == 1
    assert step.end_line == 10
    assert "def main():" in step.signature


def test_validate_step(db_session, sample_repo):
    """Test tour step validation"""
    generator = TourGenerator(db_session, sample_repo.id)
    
    symbol = db_session.query(SymbolRecord).filter(
        SymbolRecord.name == "main"
    ).first()
    file = db_session.query(FileRecord).filter(FileRecord.id == symbol.file_id).first()
    
    step = generator._symbol_to_tour_step(symbol, file)
    
    # Valid step should pass
    assert generator._validate_step(step) is True
    
    # Invalid file path should fail
    step.file_path = "nonexistent.py"
    assert generator._validate_step(step) is False
    
    # Invalid line numbers should fail
    step.file_path = "main.py"
    step.start_line = -1
    assert generator._validate_step(step) is False


def test_generate_big_picture_tour(db_session, sample_repo):
    """Test generating a big picture tour"""
    generator = TourGenerator(db_session, sample_repo.id)
    
    # Generate tour (without API key, will use heuristic explanations)
    tour = generator.generate_big_picture_tour(max_steps=5, title="Test Tour")
    
    assert tour is not None
    assert tour.tour_type == "big_picture"
    assert tour.title == "Test Tour"
    assert len(tour.steps) > 0
    
    # Check first step
    first_step = tour.steps[0]
    assert first_step.step_order == 1
    assert first_step.file_path in ["main.py", "utils.py"]
    assert first_step.title is not None
    assert first_step.body is not None


def test_traverse_call_graph(db_session, sample_repo):
    """Test call graph traversal"""
    generator = TourGenerator(db_session, sample_repo.id)
    
    entry_files = [db_session.query(FileRecord).filter(
        FileRecord.path == "main.py"
    ).first()]
    
    candidates = generator._traverse_call_graph(entry_files, max_depth=2)
    
    assert len(candidates) > 0
    # Should include both main and helper functions
    symbol_names = [c.symbol_name for c in candidates]
    assert "main" in symbol_names


def test_select_tour_steps(db_session, sample_repo):
    """Test tour step selection and ordering"""
    generator = TourGenerator(db_session, sample_repo.id)
    
    # Create some candidate steps
    symbols = db_session.query(SymbolRecord).all()
    files = {s.file_id: db_session.query(FileRecord).filter(
        FileRecord.id == s.file_id
    ).first() for s in symbols}
    
    candidates = [generator._symbol_to_tour_step(s, files[s.file_id]) for s in symbols]
    
    selected = generator._select_tour_steps(candidates, max_steps=5)
    
    assert len(selected) <= 5
    # Should be ordered by importance
    if len(selected) > 1:
        assert selected[0].importance_score >= selected[-1].importance_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
