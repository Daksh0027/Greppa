"""
Observability and LLM Call Logging for Greppa

Provides:
1. LLM call tracking (model, tokens, latency, cost)
2. Structured logging
3. Cost estimation and tracking
4. Performance metrics
"""
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.core.models import CostTrackingRecord

logger = logging.getLogger("greppa.observability")


class LLMCallLogger:
    """Tracks and logs all LLM API calls for cost monitoring and debugging"""
    
    # Cost per 1M tokens (as of 2024 for Gemini)
    PRICING = {
        "gemini-2.0-flash": {
            "prompt": 0.075,      # $0.075 per 1M input tokens
            "completion": 0.30,   # $0.30 per 1M output tokens
            "embedding": 0.00     # Free for now
        },
        "gemini-2.0-pro": {
            "prompt": 1.25,       # $1.25 per 1M input tokens
            "completion": 5.00,   # $5.00 per 1M output tokens
            "embedding": 0.00
        },
        "gemini-1.5-flash": {
            "prompt": 0.075,
            "completion": 0.30,
            "embedding": 0.00
        },
        "gemini-1.5-pro": {
            "prompt": 1.25,
            "completion": 5.00,
            "embedding": 0.00
        },
        "text-embedding-004": {
            "prompt": 0.00,
            "completion": 0.00,
            "embedding": 0.00
        }
    }
    
    def __init__(self, db: Optional[Session] = None, repo_id: Optional[int] = None):
        self.db = db
        self.repo_id = repo_id
    
    def log_call(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        operation: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> float:
        """
        Logs an LLM API call with token usage and cost estimation.
        
        Returns:
            Estimated cost in USD
        """
        # Calculate cost
        cost_usd = self.estimate_cost(model_name, prompt_tokens, completion_tokens)
        
        # Log to stdout
        logger.info(
            f"LLM Call: {operation} | Model: {model_name} | "
            f"Tokens: {prompt_tokens}+{completion_tokens} | "
            f"Latency: {latency_ms:.0f}ms | Cost: ${cost_usd:.6f} | "
            f"Success: {success}"
        )
        
        if error:
            logger.error(f"LLM Call Error: {error}")
        
        # Save to database if available
        if self.db and self.repo_id:
            try:
                record = CostTrackingRecord(
                    repo_id=self.repo_id,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    embedding_tokens=0,
                    estimated_cost_usd=cost_usd
                )
                self.db.add(record)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to save cost tracking record: {e}")
        
        return cost_usd
    
    def log_embedding_call(
        self,
        model_name: str,
        num_embeddings: int,
        total_tokens: int,
        latency_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> float:
        """
        Logs an embedding API call.
        
        Returns:
            Estimated cost in USD
        """
        cost_usd = self.estimate_embedding_cost(model_name, total_tokens)
        
        logger.info(
            f"Embedding Call: Model: {model_name} | "
            f"Count: {num_embeddings} | Tokens: {total_tokens} | "
            f"Latency: {latency_ms:.0f}ms | Cost: ${cost_usd:.6f} | "
            f"Success: {success}"
        )
        
        if error:
            logger.error(f"Embedding Call Error: {error}")
        
        # Save to database
        if self.db and self.repo_id:
            try:
                record = CostTrackingRecord(
                    repo_id=self.repo_id,
                    model_name=model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    embedding_tokens=total_tokens,
                    estimated_cost_usd=cost_usd
                )
                self.db.add(record)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Failed to save embedding cost record: {e}")
        
        return cost_usd
    
    @classmethod
    def estimate_cost(
        cls,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Estimates cost for a completion call.
        
        Returns cost in USD.
        """
        # Normalize model name
        model_key = model_name.lower()
        for key in cls.PRICING.keys():
            if key in model_key:
                model_key = key
                break
        
        pricing = cls.PRICING.get(model_key, cls.PRICING["gemini-2.0-flash"])
        
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    @classmethod
    def estimate_embedding_cost(cls, model_name: str, total_tokens: int) -> float:
        """Estimates cost for embedding calls (currently free for Gemini)"""
        return 0.0
    
    def get_repo_total_cost(self, repo_id: int) -> Dict[str, Any]:
        """
        Gets total cost statistics for a repository.
        """
        if not self.db:
            return {"error": "Database not available"}
        
        records = self.db.query(CostTrackingRecord).filter(
            CostTrackingRecord.repo_id == repo_id
        ).all()
        
        total_cost = sum(r.estimated_cost_usd for r in records)
        total_prompt_tokens = sum(r.prompt_tokens for r in records)
        total_completion_tokens = sum(r.completion_tokens for r in records)
        total_embedding_tokens = sum(r.embedding_tokens for r in records)
        
        # Group by model
        by_model: Dict[str, float] = {}
        for r in records:
            by_model[r.model_name] = by_model.get(r.model_name, 0.0) + r.estimated_cost_usd
        
        return {
            "repo_id": repo_id,
            "total_cost_usd": round(total_cost, 4),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_embedding_tokens": total_embedding_tokens,
            "total_calls": len(records),
            "cost_by_model": {k: round(v, 4) for k, v in by_model.items()}
        }


@contextmanager
def track_llm_call(
    operation: str,
    model_name: str,
    logger: Optional[LLMCallLogger] = None
):
    """
    Context manager to track LLM API calls with automatic timing.
    
    Usage:
        with track_llm_call("summarization", "gemini-2.0-flash", llm_logger) as tracker:
            response = llm.call(prompt)
            tracker.set_tokens(prompt_tokens=100, completion_tokens=50)
    """
    start_time = time.time()
    
    class CallTracker:
        def __init__(self):
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.success = True
            self.error = None
        
        def set_tokens(self, prompt_tokens: int, completion_tokens: int):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens
        
        def set_error(self, error: str):
            self.success = False
            self.error = error
    
    tracker = CallTracker()
    
    try:
        yield tracker
    except Exception as e:
        tracker.set_error(str(e))
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000
        
        if logger:
            logger.log_call(
                model_name=model_name,
                prompt_tokens=tracker.prompt_tokens,
                completion_tokens=tracker.completion_tokens,
                latency_ms=latency_ms,
                operation=operation,
                success=tracker.success,
                error=tracker.error
            )


class PerformanceMonitor:
    """Tracks performance metrics for various operations"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    @contextmanager
    def track(self, operation: str):
        """
        Context manager to track operation duration.
        
        Usage:
            with monitor.track("parsing"):
                parse_code(file)
        """
        start_time = time.time()
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            if operation not in self.metrics:
                self.metrics[operation] = []
            
            self.metrics[operation].append(duration_ms)
            
            logger.info(f"Performance: {operation} took {duration_ms:.2f}ms")
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Gets statistics for a tracked operation"""
        if operation not in self.metrics:
            return {}
        
        durations = self.metrics[operation]
        
        return {
            "count": len(durations),
            "total_ms": sum(durations),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Gets statistics for all tracked operations"""
        return {op: self.get_stats(op) for op in self.metrics.keys()}


class StructuredLogger:
    """Provides structured logging with consistent format"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(
        self,
        event: str,
        level: str = "info",
        **kwargs
    ):
        """
        Logs a structured event with metadata.
        
        Args:
            event: Event name/type
            level: Log level (info, warning, error)
            **kwargs: Additional metadata
        """
        metadata = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        
        message = f"{event} | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
        
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Logs an error with context"""
        self.log_event(
            "error",
            level="error",
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
    
    def log_ingestion_progress(
        self,
        repo_id: int,
        stage: str,
        progress: float,
        message: str
    ):
        """Logs ingestion pipeline progress"""
        self.log_event(
            "ingestion_progress",
            repo_id=repo_id,
            stage=stage,
            progress=f"{progress:.1f}%",
            message=message
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
