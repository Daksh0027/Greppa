"""
Integration Tests for Complete Workflow
"""
import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.models import Base, Repository
from app.ingestion.pipeline import IngestionPipeline
from app.search.hybrid import HybridSearchEngine
from app.ingestion.tour_generator import TourGenerator


@pytest.fixture
def db_session():
    """Create a test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_code_repo():
    """Create a temporary repository with sample code"""
    temp_dir = tempfile.mkdtemp()
    
    # Create sample Python files
    main_py = os.path.join(temp_dir, "main.py")
    with open(main_py, "w") as f:
        f.write('''"""Main application entry point"""

def main():
    """Start the application"""
    print("Starting app...")
    result = process_data()
    return result

if __name__ == "__main__":
    main()
''')
    
    utils_py = os.path.join(temp_dir, "utils.py")
    with open(utils_py, "w") as f:
        f.write('''"""Utility functions"""

def process_data():
    """Process data and return results"""
    data = load_data()
    return transform(data)

def load_data():
    """Load data from source"""
    return {"key": "value"}

def transform(data):
    """Transform data"""
    return data
''')
    
    yield temp_dir
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_full_ingestion_pipeline(db_session, sample_code_repo):
    """Test complete ingestion pipeline from repo to indexed code"""
    # Create repository record
    repo = Repository(
        name="TestRepo",
        url_or_path=sample_code_repo,
        status="pending"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    
    # Run ingestion
    pipeline = IngestionPipeline(db_session, repo.id, api_key=None)
    stats = pipeline.run(sample_code_repo, incremental=False)
    
    # Verify stats
    assert stats is not None
    assert stats["total_files"] >= 2
    assert stats["total_symbols"] >= 5  # main, process_data, load_data, transform
    
    # Verify repository status
    db_session.refresh(repo)
    assert repo.status == "ready"
    assert repo.stats is not None


def test_search_after_ingestion(db_session, sample_code_repo):
    """Test that search works after ingestion"""
    # Create and index repository
    repo = Repository(
        name="SearchTestRepo",
        url_or_path=sample_code_repo,
        status="pending"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    
    pipeline = IngestionPipeline(db_session, repo.id, api_key=None)
    pipeline.run(sample_code_repo, incremental=False)
    
    # Search for functions
    search_engine = HybridSearchEngine(db_session, repo.id, api_key=None)
    hits = search_engine.search("process data", top_k=5)
    
    assert len(hits) > 0
    # Should find process_data function
    assert any("process" in hit.symbol_name.lower() for hit in hits)


def test_tour_generation_after_ingestion(db_session, sample_code_repo):
    """Test that tour generation works after ingestion"""
    # Create and index repository
    repo = Repository(
        name="TourTestRepo",
        url_or_path=sample_code_repo,
        status="pending"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    
    pipeline = IngestionPipeline(db_session, repo.id, api_key=None)
    pipeline.run(sample_code_repo, incremental=False)
    
    # Generate tour
    generator = TourGenerator(db_session, repo.id, api_key=None)
    tour = generator.generate_big_picture_tour(max_steps=5)
    
    assert tour is not None
    assert tour.repo_id == repo.id
    assert len(tour.steps) > 0
    
    # Verify tour steps are valid
    for step in tour.steps:
        assert step.file_path in ["main.py", "utils.py"]
        assert step.start_line > 0
        assert step.title is not None


def test_incremental_update(db_session, sample_code_repo):
    """Test incremental indexing after file changes"""
    # Initial indexing
    repo = Repository(
        name="IncrementalTestRepo",
        url_or_path=sample_code_repo,
        status="pending"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    
    pipeline = IngestionPipeline(db_session, repo.id, api_key=None)
    initial_stats = pipeline.run(sample_code_repo, incremental=False)
    initial_files = initial_stats["total_files"]
    
    # Add a new file
    new_file = os.path.join(sample_code_repo, "new_module.py")
    with open(new_file, "w") as f:
        f.write('''"""New module"""

def new_function():
    """A new function"""
    return "new"
''')
    
    # Run incremental update
    incremental_stats = pipeline.run(sample_code_repo, incremental=True)
    
    # Should have detected the new file
    assert incremental_stats["processed_files"] >= 1
    
    # Total files should increase
    assert incremental_stats["total_files"] > initial_files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
