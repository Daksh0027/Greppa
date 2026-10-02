import os
import sys
import json
import tempfile
import shutil

# Ensure backend in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.models import Base, Repository
from app.ingestion.pipeline import IngestionPipeline
from app.search.hybrid import HybridSearchEngine

SAMPLE_AUTH = '''"""Authentication and Token Management Service."""

class AuthService:
    def __init__(self, secret: str = "super_secret"):
        self.secret = secret

    def authenticate_user(self, username: str, password_hash: str) -> bool:
        """Validates credentials against hashed store."""
        return self._verify_hash(username, password_hash)

    def _verify_hash(self, u: str, p: str) -> bool:
        return len(u) > 0 and len(p) > 5

    def issue_token(self, user_id: int) -> str:
        """Issues JWT bearer token strings with user IDs."""
        return f"token_bearer_{user_id}_{self.secret[:4]}"
'''

SAMPLE_GATEWAY = '''"""Payment Processing and Transaction Verification."""

class PaymentGateway:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def process_charge(self, customer_id: int, amount_cents: int) -> bool:
        """Executes bank credit card charges and transactions."""
        return amount_cents > 0 and self._check_fraud(customer_id)

    def _check_fraud(self, customer_id: int) -> bool:
        """Customer fraud prevented during charge processing."""
        return customer_id > 0
'''

SAMPLE_CONTROLLER = '''"""User HTTP API Controller."""
from auth_service import AuthService
from payment_gateway import PaymentGateway

class UserController:
    def __init__(self):
        self.auth = AuthService()
        self.gateway = PaymentGateway("pk_live_demo")

    def handle_login(self, username: str, password: str):
        """Authenticates user and returns session bearer tokens."""
        if self.auth.authenticate_user(username, password):
            return self.auth.issue_token(101)
        return None

    def purchase_subscription(self, user_id: int, plan_cost: int):
        """User subscription purchasing and billing orchestrated here."""
        return self.gateway.process_charge(user_id, plan_cost)
'''

def run_eval():
    questions_file = os.path.join(os.path.dirname(__file__), "questions.json")
    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Setup temp environment & DB
    temp_dir = tempfile.mkdtemp()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        with open(os.path.join(temp_dir, "auth_service.py"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_AUTH)
        with open(os.path.join(temp_dir, "payment_gateway.py"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_GATEWAY)
        with open(os.path.join(temp_dir, "user_controller.py"), "w", encoding="utf-8") as f:
            f.write(SAMPLE_CONTROLLER)

        repo = Repository(name="EvalRepo", url_or_path=temp_dir, status="pending")
        db.add(repo)
        db.commit()
        db.refresh(repo)

        pipeline = IngestionPipeline(db, repo.id)
        pipeline.run(temp_dir, incremental=False)

        searcher = HybridSearchEngine(db, repo.id)

        hits_at_5 = 0
        hits_at_1 = 0
        reciprocal_ranks = []

        print("\n" + "=" * 80)
        print(" GREPPA RETRIEVAL BENCHMARK & EVALUATION HARNESS")
        print("=" * 80)
        print(f"{'QID':<4} | {'Query':<45} | {'Expected':<16} | {'Found at':<8}")
        print("-" * 80)

        for q in questions:
            qid = q["id"]
            query = q["question"]
            expected = q["expected_files"]

            results = searcher.search(query, top_k=5)
            retrieved_files = [r.file_path for r in results]

            # Find rank of first expected match
            first_rank = None
            for rank, rf in enumerate(retrieved_files, start=1):
                if any(exp in rf for exp in expected):
                    first_rank = rank
                    break

            if first_rank is not None:
                reciprocal_ranks.append(1.0 / first_rank)
                if first_rank <= 5:
                    hits_at_5 += 1
                if first_rank == 1:
                    hits_at_1 += 1
                rank_str = f"Rank {first_rank}"
            else:
                reciprocal_ranks.append(0.0)
                rank_str = "Miss"

            q_short = query[:42] + "..." if len(query) > 42 else query
            exp_str = ",".join(expected)[:15]
            print(f"{qid:<4} | {q_short:<45} | {exp_str:<16} | {rank_str:<8}")

        total_q = len(questions)
        recall_at_5 = (hits_at_5 / total_q) * 100
        recall_at_1 = (hits_at_1 / total_q) * 100
        mrr = (sum(reciprocal_ranks) / total_q)

        print("-" * 80)
        print(f"Total Questions Evaluated: {total_q}")
        print(f"Recall@1: {recall_at_1:.1f}%")
        print(f"Recall@5: {recall_at_5:.1f}%  (Target: >= 70.0%)")
        print(f"MRR (Mean Reciprocal Rank): {mrr:.3f}")
        print("=" * 80)

        assert recall_at_5 >= 70.0, f"Recall@5 {recall_at_5}% below target 70%!"
        print("[SUCCESS] Retrieval Evaluation PASSED Target Thresholds!\n")
        return {"recall@5": recall_at_5, "mrr": mrr}

    finally:
        db.close()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_eval()
