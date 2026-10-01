import os
import shutil
import tempfile
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models import Base, Repository, FileRecord, SymbolRecord
from app.ingestion.pipeline import IngestionPipeline
from app.search.hybrid import HybridSearchEngine
from app.api.search import get_guided_tour, match_good_first_issue, IssueMatchRequest

@pytest.fixture
def scale_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def generate_synthetic_large_repo(target_dir: str, num_modules: int = 15, funcs_per_module: int = 15):
    """
    Generates a synthetic multi-tier codebase with core services, models, and controllers
    simulating a complex interconnected repository.
    """
    os.makedirs(target_dir, exist_ok=True)

    # Core Backbone Model
    with open(os.path.join(target_dir, "core_engine.py"), "w", encoding="utf-8") as f:
        f.write('''"""Central Orchestration Engine."""

class CoreEngine:
    def __init__(self):
        self.state = {}

    def dispatch_event(self, event_name: str, payload: dict) -> bool:
        """Central event dispatcher called across the application."""
        return len(event_name) > 0 and len(payload) >= 0

    def get_cluster_status(self) -> str:
        """Reports system health status."""
        return "operational"
''')

    # Generate interconnected service modules that import and call CoreEngine
    for m in range(num_modules):
        file_name = f"service_{m}.py"
        code_lines = [
            f'"""Service module {m} handling domain subsystem {m}."""',
            'from core_engine import CoreEngine',
            '',
            f'class ServiceWorker{m}:',
            '    def __init__(self):',
            '        self.engine = CoreEngine()',
            ''
        ]

        for fn in range(funcs_per_module):
            code_lines.extend([
                f'    def process_task_{m}_{fn}(self, data: str):',
                f'        """Executes subsystem task {fn}."""',
                f'        return self.engine.dispatch_event("task_{m}_{fn}", {{"data": data}})',
                ''
            ])

        with open(os.path.join(target_dir, file_name), "w", encoding="utf-8") as f:
            f.write("\n".join(code_lines))

def test_scale_ingestion_and_guided_tour(scale_db):
    temp_dir = tempfile.mkdtemp()
    try:
        generate_synthetic_large_repo(temp_dir, num_modules=10, funcs_per_module=10)

        repo = Repository(name="ScaleRepo", url_or_path=temp_dir, status="pending")
        scale_db.add(repo)
        scale_db.commit()
        scale_db.refresh(repo)

        t0 = time.time()
        pipeline = IngestionPipeline(scale_db, repo.id)
        stats = pipeline.run(temp_dir, incremental=False)
        duration = time.time() - t0

        # Verified stats: 11 files, >100 symbols
        assert stats["total_files"] == 11
        assert stats["total_symbols"] > 100
        assert duration < 10.0  # Fast execution

        # Test Guided Tour: CoreEngine MUST be ranked as Step 1 because all 10 services call it!
        tour = get_guided_tour(repo.id, scale_db)
        assert tour["total_stops"] >= 5
        first_stop = tour["tour_stops"][0]
        assert "core_engine" in first_stop["file_path"].lower()
        assert first_stop["importance_score"] >= 1.5

        # Test Good-First-Issue Matcher
        issue_req = IssueMatchRequest(
            title="Fix event serialization in task dispatcher",
            description="Special characters in event payload cause dispatch_event to raise an exception."
        )
        issue_res = match_good_first_issue(repo.id, issue_req, scale_db)
        assert len(issue_res["affected_files"]) > 0
        assert "core_engine" in issue_res["affected_files"][0].lower() or "service" in issue_res["affected_files"][0].lower()
        assert "roadmap" in issue_res
        assert issue_res["difficulty"] != ""

        # Test Incremental sync on large repo: modify 1 file only
        with open(os.path.join(temp_dir, "service_0.py"), "a", encoding="utf-8") as f:
            f.write("\ndef extra_task():\n    return 42\n")

        t_inc_start = time.time()
        inc_stats = pipeline.run(temp_dir, incremental=True)
        inc_duration = time.time() - t_inc_start

        assert inc_stats["processed_files"] == 1
        assert inc_stats["unchanged_files"] == 10
        assert inc_duration < 3.0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
