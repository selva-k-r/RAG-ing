"""Module 5: Evaluation & Logging

Objective: Track performance and safety of RAG system.
"""

import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from ..config.settings import Settings, EvaluationConfig
from ..utils.exceptions import EvaluationError

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval performance."""
    precision_at_1: Optional[float] = None
    precision_at_3: Optional[float] = None
    precision_at_5: Optional[float] = None
    hit_rate: Optional[float] = None
    chunk_overlap: Optional[float] = None
    latency_ms: Optional[float] = None
    query_hash: Optional[str] = None


@dataclass
class GenerationMetrics:
    """Metrics for generation quality."""
    clarity_score: Optional[float] = None
    citation_coverage: Optional[float] = None
    safety_score: Optional[float] = None
    response_length: Optional[int] = None
    token_count: Optional[int] = None
    generation_time_ms: Optional[float] = None
    model_used: Optional[str] = None


@dataclass
class SystemMetrics:
    """System-level performance metrics."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_end_to_end_time: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    error_rate: Optional[float] = None


@dataclass
class QueryEvent:
    """Complete query evaluation event."""
    timestamp: str
    query: str
    query_hash: str
    retrieval_metrics: RetrievalMetrics
    generation_metrics: GenerationMetrics
    user_feedback: Optional[Dict[str, Any]] = None
    system_metadata: Optional[Dict[str, Any]] = None


class EvaluationLoggingModule:
    """Module for YAML-driven evaluation metrics and structured logging."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.eval_config = config.evaluation
        self.metrics_enabled = self.eval_config.metrics
        self.logging_config = self.eval_config.logging
        
        # Initialize logging infrastructure
        if self.logging_config.enabled:
            self._setup_structured_logging()
        
        # Initialize metrics tracking
        self._system_metrics = SystemMetrics()
        self._query_events = []
        self._session_start = datetime.now()
    
    def _is_metric_enabled(self, metric_name: str) -> bool:
        """Check if a metric is enabled in the configuration."""
        if isinstance(self.metrics_enabled, list):
            return metric_name in self.metrics_enabled
        elif isinstance(self.metrics_enabled, dict):
            return self._is_metric_enabled(metric_name)
        else:
            return False
    
    def _setup_structured_logging(self) -> None:
        """Setup structured JSON logging infrastructure."""
        try:
            log_path = Path(self.logging_config.path)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Create evaluation-specific logger
            self.eval_logger = logging.getLogger("rag_evaluation")
            self.eval_logger.setLevel(logging.INFO)
            
            # Remove existing handlers to avoid duplicates
            for handler in self.eval_logger.handlers[:]:
                self.eval_logger.removeHandler(handler)
            
            # JSON formatter for structured logging
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    # Ensure message is JSON-formatted
                    if isinstance(record.getMessage(), str):
                        try:
                            # Try to parse as JSON, if it fails, wrap in a JSON object
                            json.loads(record.getMessage())
                            return record.getMessage()
                        except json.JSONDecodeError:
                            return json.dumps({
                                "timestamp": datetime.now().isoformat(),
                                "level": record.levelname,
                                "logger": record.name,
                                "message": record.getMessage()
                            })
                    return record.getMessage()
            
            # File handler for evaluation logs
            eval_handler = logging.FileHandler(log_path / "evaluation.jsonl")
            eval_handler.setFormatter(JSONFormatter())
            self.eval_logger.addHandler(eval_handler)
            
            # Separate handlers for different metric types
            if self._is_metric_enabled("precision_at_k"):
                retrieval_handler = logging.FileHandler(log_path / "retrieval_metrics.jsonl")
                retrieval_handler.setFormatter(JSONFormatter())
                retrieval_logger = logging.getLogger("retrieval_metrics")
                retrieval_logger.addHandler(retrieval_handler)
            
            if self._is_metric_enabled("clarity_rating"):
                generation_handler = logging.FileHandler(log_path / "generation_metrics.jsonl")
                generation_handler.setFormatter(JSONFormatter())
                generation_logger = logging.getLogger("generation_metrics")
                generation_logger.addHandler(generation_handler)
            
            logger.info(f"Structured logging initialized at {log_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup structured logging: {e}")
            raise EvaluationError(f"Logging setup failed: {e}")
    
    def log_query_event(self, event: QueryEvent) -> None:
        """Log a complete query evaluation event."""
        if not self.logging_config.enabled:
            return
        
        try:
            # Convert dataclass to dict and serialize
            event_dict = asdict(event)
            event_json = json.dumps(event_dict, default=str)
            
            # Log to main evaluation log
            self.eval_logger.info(event_json)
            
            # Log to specific metric logs if enabled
            if (self._is_metric_enabled("precision_at_k") and 
                event.retrieval_metrics):
                retrieval_logger = logging.getLogger("retrieval_metrics")
                retrieval_data = {
                    "timestamp": event.timestamp,
                    "query_hash": event.query_hash,
                    "metrics": asdict(event.retrieval_metrics)
                }
                retrieval_logger.info(json.dumps(retrieval_data, default=str))
            
            if (self._is_metric_enabled("clarity_rating") and 
                event.generation_metrics):
                generation_logger = logging.getLogger("generation_metrics")
                generation_data = {
                    "timestamp": event.timestamp,
                    "query_hash": event.query_hash,
                    "metrics": asdict(event.generation_metrics)
                }
                generation_logger.info(json.dumps(generation_data, default=str))
            
            # Store in memory for session analysis
            self._query_events.append(event)
            
            # Keep only last 1000 events in memory
            if len(self._query_events) > 1000:
                self._query_events = self._query_events[-1000:]
            
        except Exception as e:
            logger.error(f"Failed to log query event: {e}")
    
    def calculate_retrieval_metrics(self, query: str, retrieved_docs: List[Dict[str, Any]], 
                                  relevant_docs: Optional[List[str]] = None,
                                  retrieval_time: float = 0.0) -> RetrievalMetrics:
        """Calculate retrieval performance metrics."""
        metrics = RetrievalMetrics()
        
        if self._is_metric_enabled("precision_at_k") and relevant_docs:
            # Calculate precision@k metrics
            metrics.precision_at_1 = self._precision_at_k(retrieved_docs, relevant_docs, 1)
            metrics.precision_at_3 = self._precision_at_k(retrieved_docs, relevant_docs, 3)
            metrics.precision_at_5 = self._precision_at_k(retrieved_docs, relevant_docs, 5)
        
        if self._is_metric_enabled("latency"):
            metrics.latency_ms = retrieval_time * 1000
        
        # Calculate hit rate (whether any results were retrieved)
        metrics.hit_rate = 1.0 if len(retrieved_docs) > 0 else 0.0
        
        # Calculate chunk overlap if multiple chunks from same source
        if len(retrieved_docs) > 1:
            metrics.chunk_overlap = self._calculate_chunk_overlap(retrieved_docs)
        
        # Generate query hash for tracking
        import hashlib
        metrics.query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        return metrics
    
    def calculate_generation_metrics(self, response: str, sources: List[Dict[str, Any]], 
                                   generation_time: float = 0.0,
                                   model_name: str = "unknown",
                                   user_feedback: Optional[Dict[str, Any]] = None) -> GenerationMetrics:
        """Calculate generation quality metrics."""
        metrics = GenerationMetrics()
        
        # Basic response metrics
        metrics.response_length = len(response)
        metrics.model_used = model_name
        
        if self._is_metric_enabled("latency"):
            metrics.generation_time_ms = generation_time * 1000
        
        # Citation coverage calculation
        if self._is_metric_enabled("citation_coverage"):
            metrics.citation_coverage = self._calculate_citation_coverage(response, sources)
        
        # User feedback-based metrics
        if user_feedback and self._is_metric_enabled("clarity_rating"):
            ratings = user_feedback.get("ratings", {})
            metrics.clarity_score = ratings.get("clarity")
            metrics.safety_score = ratings.get("safety")
        
        # Estimate token count (rough approximation)
        metrics.token_count = len(response.split()) * 1.3  # Approximation
        
        return metrics
    
    def calculate_safety_score(self, response: str, query: str) -> float:
        """Calculate safety adherence score."""
        if not self._is_metric_enabled("safety"):
            return 0.0
        
        safety_score = 1.0  # Start with perfect score
        
        # Check for medical disclaimers
        disclaimers = [
            "consult", "healthcare professional", "medical advice",
            "professional", "expert", "not a substitute"
        ]
        
        response_lower = response.lower()
        query_lower = query.lower()
        
        # Sensitive queries should have appropriate disclaimers
        sensitive_keywords = [
            "advice", "recommendation", "decision", "critical",
            "important", "urgent", "guidance"
        ]
        
        is_sensitive = any(keyword in query_lower for keyword in sensitive_keywords)
        has_disclaimer = any(disclaimer in response_lower for disclaimer in disclaimers)
        
        if is_sensitive and not has_disclaimer:
            safety_score -= 0.3  # Deduct for missing appropriate disclaimer
        
        # Check for certainty claims in uncertain contexts
        certainty_words = ["definitely", "certainly", "always", "never", "guaranteed"]
        has_certainty_claims = any(word in response_lower for word in certainty_words)
        
        if has_certainty_claims:
            safety_score -= 0.2  # Deduct for inappropriate certainty
        
        # Check for proper citation behavior
        if "based on" in response_lower or "according to" in response_lower:
            safety_score += 0.1  # Bonus for citing sources
        
        return max(0.0, min(1.0, safety_score))  # Clamp to [0, 1]
    
    def _precision_at_k(self, retrieved_docs: List[Dict[str, Any]], 
                       relevant_docs: List[str], k: int) -> float:
        """Calculate precision@k metric."""
        if not retrieved_docs or k <= 0:
            return 0.0
        
        top_k = retrieved_docs[:k]
        relevant_count = 0
        
        for doc in top_k:
            # Handle both Document objects and dictionaries
            if hasattr(doc, 'metadata'):
                # Document object from ChromaDB
                doc_id = doc.metadata.get('id') or doc.metadata.get('source', str(doc))
            elif isinstance(doc, dict):
                # Dictionary
                doc_id = doc.get('id') or doc.get('source', str(doc))
            else:
                # Fallback
                doc_id = str(doc)
                
            if doc_id in relevant_docs:
                relevant_count += 1
        
        return relevant_count / min(k, len(top_k))
    
    def _calculate_citation_coverage(self, response: str, sources: List[Dict[str, Any]]) -> float:
        """Calculate how well response cites sources."""
        if not sources:
            return 0.0
        
        response_lower = response.lower()
        cited_sources = 0
        
        for source in sources:
            # Handle both Document objects and dictionaries
            if hasattr(source, 'metadata'):
                # Document object from ChromaDB
                metadata = source.metadata
                source_indicators = [
                    metadata.get('source', '').lower(),
                    metadata.get('title', '').lower(),
                    metadata.get('filename', '').lower(),
                ]
            elif isinstance(source, dict):
                # Dictionary
                source_indicators = [
                    source.get('source', '').lower(),
                    source.get('title', '').lower(),
                    source.get('filename', '').lower(),
                ]
            else:
                # Fallback
                source_indicators = [str(source).lower()]
            
            # Remove empty strings
            source_indicators = [s for s in source_indicators if s]
            
            # Check if any source indicator appears in response
            for indicator in source_indicators:
                if len(indicator) > 3 and indicator in response_lower:
                    cited_sources += 1
                    break
        
        return cited_sources / len(sources)
    
    def _calculate_chunk_overlap(self, retrieved_docs: List[Dict[str, Any]]) -> float:
        """Calculate overlap between retrieved chunks."""
        if len(retrieved_docs) < 2:
            return 0.0
        
        # Group by source
        sources = {}
        for doc in retrieved_docs:
            source = doc.metadata.get('source', 'unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(doc)
        
        # Calculate overlap ratio
        total_docs = len(retrieved_docs)
        docs_from_same_source = sum(max(0, len(docs) - 1) for docs in sources.values())
        
        return docs_from_same_source / max(1, total_docs - 1)
    
    def update_system_metrics(self, success: bool = True, processing_time: float = 0.0) -> None:
        """Update system-level metrics."""
        self._system_metrics.total_queries += 1
        
        if success:
            self._system_metrics.successful_queries += 1
        else:
            self._system_metrics.failed_queries += 1
        
        # Update error rate
        total = self._system_metrics.total_queries
        self._system_metrics.error_rate = self._system_metrics.failed_queries / total
        
        # Update average end-to-end time
        if self._system_metrics.avg_end_to_end_time is None:
            self._system_metrics.avg_end_to_end_time = processing_time
        else:
            # Running average
            prev_avg = self._system_metrics.avg_end_to_end_time
            self._system_metrics.avg_end_to_end_time = (
                (prev_avg * (total - 1) + processing_time) / total
            )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session metrics."""
        session_duration = (datetime.now() - self._session_start).total_seconds()
        
        # Aggregate metrics from query events
        retrieval_metrics = []
        generation_metrics = []
        feedback_ratings = {"clarity": [], "citation": [], "safety": [], "usefulness": []}
        
        for event in self._query_events:
            if event.retrieval_metrics:
                retrieval_metrics.append(event.retrieval_metrics)
            
            if event.generation_metrics:
                generation_metrics.append(event.generation_metrics)
            
            if event.user_feedback and "ratings" in event.user_feedback:
                ratings = event.user_feedback["ratings"]
                for metric, value in ratings.items():
                    if metric in feedback_ratings and value is not None:
                        feedback_ratings[metric].append(value)
        
        # Calculate averages
        avg_feedback = {}
        for metric, values in feedback_ratings.items():
            if values:
                avg_feedback[metric] = sum(values) / len(values)
        
        return {
            "session_duration_minutes": session_duration / 60,
            "system_metrics": asdict(self._system_metrics),
            "total_events": len(self._query_events),
            "avg_retrieval_latency": self._calculate_avg_latency(retrieval_metrics, "latency_ms"),
            "avg_generation_latency": self._calculate_avg_latency(generation_metrics, "generation_time_ms"),
            "avg_citation_coverage": self._calculate_avg_metric(generation_metrics, "citation_coverage"),
            "avg_user_feedback": avg_feedback,
            "feedback_rate": len([e for e in self._query_events if e.user_feedback]) / max(1, len(self._query_events))
        }
    
    def _calculate_avg_latency(self, metrics_list: List, field_name: str) -> Optional[float]:
        """Calculate average latency from metrics list."""
        values = [getattr(m, field_name) for m in metrics_list if getattr(m, field_name) is not None]
        return sum(values) / len(values) if values else None
    
    def _calculate_avg_metric(self, metrics_list: List, field_name: str) -> Optional[float]:
        """Calculate average metric from metrics list."""
        values = [getattr(m, field_name) for m in metrics_list if getattr(m, field_name) is not None]
        return sum(values) / len(values) if values else None
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in specified format."""
        if format_type == "json":
            return json.dumps({
                "session_summary": self.get_session_summary(),
                "system_metrics": asdict(self._system_metrics),
                "query_events": [asdict(event) for event in self._query_events]
            }, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def clear_session_data(self) -> None:
        """Clear session data and reset metrics."""
        self._query_events = []
        self._system_metrics = SystemMetrics()
        self._session_start = datetime.now()
        logger.info("Session data cleared and metrics reset")
    
    def is_logging_enabled(self) -> bool:
        """Check if logging is enabled."""
        return self.logging_config.enabled
    
    def get_enabled_metrics(self) -> Dict[str, bool]:
        """Get dictionary of enabled metrics."""
        return self.metrics_enabled.copy()