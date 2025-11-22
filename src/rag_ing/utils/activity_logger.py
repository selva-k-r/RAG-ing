"""Activity logging for RAG system analytics and fine-tuning data collection.

Logs user interactions in JSONL format for:
- Search queries and results
- User feedback (thumbs up/down)
- Source document clicks
- Performance metrics
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ActivityLogger:
    """Logs user activity to daily JSONL files."""
    
    def __init__(self, log_dir: str = "./logs/user_activity"):
        """Initialize activity logger.
        
        Args:
            log_dir: Directory for activity log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ActivityLogger initialized: {self.log_dir}")
    
    def log_search(
        self,
        query: str,
        results: List[Any],
        session_id: str,
        retrieval_time: float,
        generation_time: float,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """Log search query with results and timing.
        
        Args:
            query: User query string
            results: List of retrieved documents
            session_id: Session identifier
            retrieval_time: Time to retrieve documents (seconds)
            generation_time: Time to generate response (seconds)
            user_context: Additional user context (sources, filters, etc.)
        """
        user_context = user_context or {}
        
        # Extract document info from results
        retrieved_docs = []
        if isinstance(results, list):
            for doc in results[:10]:  # Log top 10 only
                if hasattr(doc, 'metadata'):
                    retrieved_docs.append({
                        "source": doc.metadata.get('source', 'unknown'),
                        "source_type": doc.metadata.get('source_type', 'unknown'),
                        "filename": doc.metadata.get('filename', ''),
                    })
        
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "event_type": "search_query",
            "query": {
                "text": query,
                "sources_selected": user_context.get('sources', []),
                "filters": user_context.get('filters', {})
            },
            "results": {
                "num_results": len(results) if isinstance(results, list) else 0,
                "retrieval_time_ms": int(retrieval_time * 1000),
                "generation_time_ms": int(generation_time * 1000),
                "total_time_ms": int((retrieval_time + generation_time) * 1000)
            },
            "retrieved_docs": retrieved_docs
        }
        
        self._write_event(event)
        logger.debug(f"Logged search: {query[:50]}...")
    
    def log_feedback(
        self,
        session_id: str,
        query: str,
        feedback_type: str,
        comment: Optional[str] = None
    ):
        """Log user feedback on response.
        
        Args:
            session_id: Session identifier
            query: Original query
            feedback_type: 'positive' or 'negative'
            comment: Optional user comment
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "event_type": f"feedback_{feedback_type}",
            "query": query,
            "feedback": {
                "type": feedback_type,
                "comment": comment
            }
        }
        
        self._write_event(event)
        logger.debug(f"Logged feedback: {feedback_type}")
    
    def log_source_click(
        self,
        session_id: str,
        doc_id: str,
        doc_source: str
    ):
        """Log when user clicks on source document.
        
        Args:
            session_id: Session identifier
            doc_id: Document identifier
            doc_source: Document source (filename, URL, etc.)
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "event_type": "source_click",
            "document": {
                "doc_id": doc_id,
                "source": doc_source
            }
        }
        
        self._write_event(event)
        logger.debug(f"Logged source click: {doc_source}")
    
    def _write_event(self, event: Dict[str, Any]):
        """Write event to today's JSONL file.
        
        Args:
            event: Event data dictionary
        """
        log_file = self._get_today_log_file()
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to write activity log: {e}")
    
    def _get_today_log_file(self) -> Path:
        """Get path to today's log file.
        
        Returns:
            Path to log file (YYYY-MM-DD.jsonl format)
        """
        today = datetime.utcnow().date()
        return self.log_dir / f"{today}.jsonl"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get activity logging statistics.
        
        Returns:
            Dictionary with log file count, total events, etc.
        """
        log_files = list(self.log_dir.glob("*.jsonl"))
        total_events = 0
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    total_events += sum(1 for _ in f)
            except Exception:
                # Silently skip corrupted, inaccessible, or malformed log files
                # to ensure stats collection continues even if some files are problematic
                pass
        
        return {
            'log_directory': str(self.log_dir),
            'log_files': len(log_files),
            'total_events': total_events,
            'today_log_file': str(self._get_today_log_file())
        }



