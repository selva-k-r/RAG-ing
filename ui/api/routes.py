"""
API routes for the RAG system.
Handles search requests, health checks, and system status.
"""

from typing import Dict, Any, List
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# Global cache for search results
search_results_cache = {}

class SearchRequest(BaseModel):
    query: str
    sources: List[str] = ["confluence", "jira", "internal", "salesforce"]
    audience: str = "technical"

class SearchResponse(BaseModel):
    success: bool
    response: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_hash: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    modules: Dict[str, Any]

def get_rag_system():
    """Get the RAG system instance from the main app."""
    from app import rag_system
    return rag_system

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Process search queries through the RAG system.
    """
    rag_system = get_rag_system()
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        # Process query through RAG system
        result = rag_system.query_documents(
            query=request.query.strip(),
            audience=request.audience
        )
        
        # Format sources for frontend
        formatted_sources = []
        for source in result.get("sources", []):
            formatted_sources.append({
                "content": source.page_content[:500] + "..." if len(source.page_content) > 500 else source.page_content,
                "full_content": source.page_content,
                "metadata": source.metadata,
                "source": source.metadata.get('source', 'Unknown'),
                "title": source.metadata.get('title', 'Unknown Document'),
                "url": source.metadata.get('url', '#'),
                "author": source.metadata.get('author', 'Unknown'),
                "date": source.metadata.get('date', 'Unknown')
            })
        
        # Cache the result for detailed view
        result_id = result["query_hash"]
        search_results_cache[result_id] = {
            "query": request.query.strip(),
            "response": result["response"],
            "sources": formatted_sources,
            "metadata": result["metadata"],
            "timestamp": datetime.now().isoformat(),
            "audience": request.audience,
            "selected_sources": request.sources
        }
        
        return SearchResponse(
            success=True,
            response=result["response"],
            sources=formatted_sources,
            metadata=result["metadata"],
            query_hash=result["query_hash"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health and module status."""
    rag_system = get_rag_system()
    
    if not rag_system:
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            modules={"rag_system": "not_initialized"}
        )
    
    try:
        health_status = rag_system.health_check()
        return HealthResponse(
            status=health_status.get("overall", "unknown"),
            timestamp=health_status.get("timestamp", datetime.now().isoformat()),
            modules=health_status.get("modules", {})
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            modules={"error": str(e)}
        )

@router.get("/status")
async def system_status():
    """Get detailed system status and metrics."""
    rag_system = get_rag_system()
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        status = rag_system.get_system_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/results/{result_id}")
async def get_search_result(result_id: str):
    """Get cached search result by ID."""
    if result_id not in search_results_cache:
        raise HTTPException(status_code=404, detail="Search result not found")
    
    return JSONResponse(content=search_results_cache[result_id])

@router.post("/feedback")
async def submit_feedback(feedback_data: Dict[str, Any]):
    """Submit user feedback for a query result."""
    rag_system = get_rag_system()
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        query_hash = feedback_data.get("query_hash")
        feedback = feedback_data.get("feedback", {})
        
        if not query_hash:
            raise HTTPException(status_code=400, detail="query_hash is required")
        
        result = rag_system.submit_feedback(query_hash, feedback)
        return JSONResponse(content={"success": True, "message": "Feedback submitted successfully"})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")