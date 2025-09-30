"""Module 4: UI Layer (FastAPI Implementation)

Objective: Provide web interface for query input and response display using FastAPI.
Note: This module has been migrated from Streamlit to FastAPI for 100% UI control.
"""

import logging
from typing import Dict, Any, Optional, List
from ..config.settings import Settings
from ..utils.exceptions import UIError

logger = logging.getLogger(__name__)


class UILayerModule:
    """Module for FastAPI-based user interface with audience toggle and feedback capture."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.ui_config = config.ui
        self.feedback_history = []
    
    def format_response_for_audience(self, response: Dict[str, Any], audience: str = "business") -> Dict[str, Any]:
        """Format response based on target audience."""
        try:
            formatted_response = {
                "content": response.get("response", ""),
                "sources": response.get("sources", []),
                "confidence": response.get("confidence_score", 0.0),
                "safety_score": response.get("safety_score", 0.0),
                "audience": audience
            }
            
            if audience == "business":
                formatted_response["simplified"] = True
            else:
                formatted_response["technical_details"] = response.get("metadata", {})
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error formatting response for audience {audience}: {e}")
            raise UIError(f"Failed to format response: {e}")
    
    def capture_feedback(self, query_hash: str, feedback: Dict[str, Any]) -> None:
        """Capture user feedback for a query."""
        try:
            feedback_entry = {
                "query_hash": query_hash,
                "timestamp": feedback.get("timestamp"),
                "rating": feedback.get("rating"),
                "comment": feedback.get("comment", ""),
                "helpful": feedback.get("helpful", False)
            }
            
            self.feedback_history.append(feedback_entry)
            logger.info(f"Captured feedback for query {query_hash[:8]}...")
            
        except Exception as e:
            logger.error(f"Error capturing feedback: {e}")
            raise UIError(f"Failed to capture feedback: {e}")
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of all feedback collected."""
        if not self.feedback_history:
            return {"total_feedback": 0, "average_rating": 0.0}
        
        total_feedback = len(self.feedback_history)
        ratings = [f["rating"] for f in self.feedback_history if f.get("rating")]
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        return {
            "total_feedback": total_feedback,
            "average_rating": round(average_rating, 2),
            "helpful_responses": len([f for f in self.feedback_history if f.get("helpful")])
        }
