"""
Tests for Observability and LLM Call Logging
"""
import pytest
import time
from app.core.observability import (
    LLMCallLogger,
    track_llm_call,
    PerformanceMonitor,
    StructuredLogger
)


class TestLLMCallLogger:
    """Tests for LLM call logging and cost tracking"""
    
    def test_pricing_data_exists(self):
        """Test that pricing data is configured"""
        assert "gemini-2.0-flash" in LLMCallLogger.PRICING
        assert "gemini-2.0-pro" in LLMCallLogger.PRICING
        assert "text-embedding-004" in LLMCallLogger.PRICING
        
        # Check pricing structure
        flash_pricing = LLMCallLogger.PRICING["gemini-2.0-flash"]
        assert "prompt" in flash_pricing
        assert "completion" in flash_pricing
        assert "embedding" in flash_pricing
    
    def test_cost_estimation_flash(self):
        """Test cost estimation for Gemini Flash"""
        cost = LLMCallLogger.estimate_cost(
            model_name="gemini-2.0-flash",
            prompt_tokens=1_000_000,  # 1M tokens
            completion_tokens=1_000_000  # 1M tokens
        )
        
        # Flash: $0.075 per 1M input + $0.30 per 1M output = $0.375
        assert 0.37 < cost < 0.38
    
    def test_cost_estimation_pro(self):
        """Test cost estimation for Gemini Pro"""
        cost = LLMCallLogger.estimate_cost(
            model_name="gemini-2.0-pro",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000
        )
        
        # Pro: $1.25 per 1M input + $5.00 per 1M output = $6.25
        assert 6.2 < cost < 6.3
    
    def test_cost_estimation_small_call(self):
        """Test cost estimation for typical small call"""
        cost = LLMCallLogger.estimate_cost(
            model_name="gemini-2.0-flash",
            prompt_tokens=500,
            completion_tokens=100
        )
        
        # Should be very small
        assert 0 < cost < 0.0001
    
    def test_model_name_normalization(self):
        """Test that model names are normalized correctly"""
        # Should work with various formats
        cost1 = LLMCallLogger.estimate_cost("gemini-2.0-flash", 1000, 100)
        cost2 = LLMCallLogger.estimate_cost("gemini-2.0-flash-001", 1000, 100)
        cost3 = LLMCallLogger.estimate_cost("Gemini-2.0-Flash", 1000, 100)
        
        # Should all be similar (within rounding)
        assert abs(cost1 - cost2) < 0.0001
    
    def test_embedding_cost_is_free(self):
        """Test that embedding calls are currently free"""
        cost = LLMCallLogger.estimate_embedding_cost(
            model_name="text-embedding-004",
            total_tokens=1_000_000
        )
        assert cost == 0.0
    
    def test_log_call_returns_cost(self):
        """Test that log_call returns estimated cost"""
        logger = LLMCallLogger()
        
        cost = logger.log_call(
            model_name="gemini-2.0-flash",
            prompt_tokens=1000,
            completion_tokens=200,
            latency_ms=150.0,
            operation="test",
            success=True
        )
        
        assert isinstance(cost, float)
        assert cost > 0
    
    def test_log_call_with_error(self):
        """Test logging failed calls"""
        logger = LLMCallLogger()
        
        cost = logger.log_call(
            model_name="gemini-2.0-flash",
            prompt_tokens=1000,
            completion_tokens=0,
            latency_ms=50.0,
            operation="test",
            success=False,
            error="API rate limit exceeded"
        )
        
        # Should still estimate cost for the prompt
        assert cost > 0
    
    def test_log_embedding_call(self):
        """Test logging embedding calls"""
        logger = LLMCallLogger()
        
        cost = logger.log_embedding_call(
            model_name="text-embedding-004",
            num_embeddings=10,
            total_tokens=5000,
            latency_ms=200.0,
            success=True
        )
        
        # Currently free
        assert cost == 0.0


class TestTrackLLMCall:
    """Tests for track_llm_call context manager"""
    
    def test_track_llm_call_success(self):
        """Test tracking successful LLM call"""
        logger = LLMCallLogger()
        
        with track_llm_call("test_operation", "gemini-2.0-flash", logger) as tracker:
            # Simulate some work
            time.sleep(0.01)
            tracker.set_tokens(prompt_tokens=100, completion_tokens=50)
        
        # Should complete without error
        assert tracker.success is True
        assert tracker.prompt_tokens == 100
        assert tracker.completion_tokens == 50
    
    def test_track_llm_call_error(self):
        """Test tracking failed LLM call"""
        logger = LLMCallLogger()
        
        try:
            with track_llm_call("test_operation", "gemini-2.0-flash", logger) as tracker:
                tracker.set_tokens(prompt_tokens=100, completion_tokens=0)
                raise ValueError("API error")
        except ValueError:
            pass
        
        # Should have recorded the error
        assert tracker.success is False
        assert tracker.error == "API error"
    
    def test_track_llm_call_without_logger(self):
        """Test tracking without a logger (should not fail)"""
        with track_llm_call("test_operation", "gemini-2.0-flash") as tracker:
            tracker.set_tokens(prompt_tokens=100, completion_tokens=50)
        
        assert tracker.success is True


class TestPerformanceMonitor:
    """Tests for performance monitoring"""
    
    def test_track_operation(self):
        """Test tracking operation duration"""
        monitor = PerformanceMonitor()
        
        with monitor.track("test_operation"):
            time.sleep(0.01)  # 10ms
        
        stats = monitor.get_stats("test_operation")
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 10
        assert stats["min_ms"] >= 10
    
    def test_track_multiple_operations(self):
        """Test tracking multiple operations"""
        monitor = PerformanceMonitor()
        
        for _ in range(5):
            with monitor.track("parsing"):
                time.sleep(0.005)
        
        stats = monitor.get_stats("parsing")
        assert stats["count"] == 5
        assert stats["total_ms"] >= 25  # 5 x 5ms
    
    def test_track_different_operations(self):
        """Test tracking different operation types"""
        monitor = PerformanceMonitor()
        
        with monitor.track("parsing"):
            time.sleep(0.01)
        
        with monitor.track("embedding"):
            time.sleep(0.01)
        
        all_stats = monitor.get_all_stats()
        assert "parsing" in all_stats
        assert "embedding" in all_stats
        assert all_stats["parsing"]["count"] == 1
        assert all_stats["embedding"]["count"] == 1
    
    def test_get_stats_nonexistent_operation(self):
        """Test getting stats for non-tracked operation"""
        monitor = PerformanceMonitor()
        stats = monitor.get_stats("nonexistent")
        assert stats == {}


class TestStructuredLogger:
    """Tests for structured logging"""
    
    def test_log_event(self):
        """Test logging structured events"""
        logger = StructuredLogger("test")
        
        # Should not raise exception
        logger.log_event(
            "test_event",
            level="info",
            user_id=123,
            action="search"
        )
    
    def test_log_error(self):
        """Test logging errors with context"""
        logger = StructuredLogger("test")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.log_error(e, {"operation": "test", "repo_id": 1})
    
    def test_log_ingestion_progress(self):
        """Test logging ingestion progress"""
        logger = StructuredLogger("test")
        
        logger.log_ingestion_progress(
            repo_id=1,
            stage="parsing",
            progress=50.0,
            message="Parsing files..."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
