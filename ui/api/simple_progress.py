"""
Simplified progress tracking that works with existing search endpoint.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging

# Import requests with fallback
try:
    import requests
except ImportError:
    print("Warning: requests not available, progress tracking may not work")
    requests = None

logger = logging.getLogger(__name__)

router = APIRouter()

# Global progress tracking
progress_store: Dict[str, Dict[str, Any]] = {}

class ProgressSearchRequest(BaseModel):
    query: str
    sources: list = ["confluence", "jira", "internal", "salesforce"]
    audience: str = "technical"

async def generate_progress_stream(session_id: str) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events for progress updates."""
    
    # Send initial connection event
    yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
    
    last_progress = -1
    start_time = time.time()
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Get current progress
        progress_data = progress_store.get(session_id, {})
        current_progress = progress_data.get("progress", 0)
        
        # Only send updates when progress changes
        if current_progress != last_progress:
            # Add contextual flying words
            flying_words = get_flying_words_for_step(progress_data.get("step", 0))
            
            event_data = {
                "type": "progress",
                "session_id": session_id,
                "progress": current_progress,
                "step": progress_data.get("step", 0),
                "step_name": progress_data.get("step_name", "Initializing"),
                "details": progress_data.get("details", ""),
                "status": progress_data.get("status", "starting"),
                "elapsed": elapsed,
                "flying_words": flying_words,
                "estimated_remaining": max(0, 20 - elapsed) if current_progress < 100 else 0
            }
            
            yield f"data: {json.dumps(event_data)}\n\n"
            last_progress = current_progress
        
        # Check if complete
        if progress_data.get("status") in ["complete", "error"]:
            yield f"data: {json.dumps({'type': 'complete', 'session_id': session_id, 'status': progress_data.get('status')})}\n\n"
            break
            
        # Check for timeout (35 seconds max)
        if elapsed > 35:
            yield f"data: {json.dumps({'type': 'timeout', 'session_id': session_id})}\n\n"
            break
            
        await asyncio.sleep(0.2)  # Update every 200ms

def get_flying_words_for_step(step: int) -> list:
    """Get contextual flying words based on processing step."""
    word_sets = [
        ["initializing", "loading", "preparing", "starting"],
        ["searching", "indexing", "querying", "scanning", "retrieving"],
        ["documents", "context", "relevance", "similarity", "ranking"],
        ["processing", "analyzing", "parsing", "extracting", "filtering"],
        ["generating", "reasoning", "thinking", "composing", "AI", "GPT-4"],
        ["finalizing", "formatting", "completing", "ready"]
    ]
    
    if step < len(word_sets):
        return word_sets[step]
    return ["processing", "working", "computing"]

def update_progress(session_id: str, step: int, step_name: str, details: str, progress: float):
    """Update progress for a session."""
    progress_store[session_id] = {
        "progress": min(progress, 99),  # Keep at 99% until truly complete
        "step": step,
        "step_name": step_name,
        "details": details,
        "status": "processing",
        "timestamp": time.time()
    }

def complete_progress(session_id: str, success: bool = True):
    """Mark progress as complete."""
    if session_id in progress_store:
        progress_store[session_id].update({
            "progress": 100,
            "status": "complete" if success else "error",
            "step": 6,
            "step_name": "Complete"
        })

@router.get("/progress/{session_id}")
async def stream_progress(session_id: str):
    """Stream progress updates using Server-Sent Events."""
    return StreamingResponse(
        generate_progress_stream(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.post("/search-with-progress")
async def search_with_progress(request: ProgressSearchRequest):
    """
    Start search with progress tracking using existing search endpoint.
    """
    session_id = str(uuid.uuid4())
    
    # Start the background task
    asyncio.create_task(process_search_with_simulated_progress(session_id, request))
    
    return {
        "session_id": session_id,
        "progress_url": f"/api/progress/{session_id}",
        "estimated_time": "15-20 seconds"
    }

async def process_search_with_simulated_progress(session_id: str, request: ProgressSearchRequest):
    """
    Process search with realistic progress updates by calling existing endpoint.
    """
    try:
        # Step 1: Initialize (5%)
        update_progress(session_id, 0, "Initializing", "Setting up search parameters", 5)
        await asyncio.sleep(0.5)
        
        # Step 2: Start search (15%)
        update_progress(session_id, 1, "Searching knowledge base", f"Scanning {len(request.sources)} data sources", 15)
        await asyncio.sleep(0.8)
        
        # Step 3: Call the actual search API
        update_progress(session_id, 2, "Retrieving documents", "Processing vector search", 35)
        
        # Make the actual API call to your existing search endpoint
        search_start_time = time.time()
        
        try:
            # Import the search function directly from routes
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__)))
            from routes import SearchRequest, search as search_function
            
            # Create search request
            search_req = SearchRequest(
                query=request.query,
                sources=request.sources,
                audience=request.audience
            )
            
            # Simulate realistic progress updates during search
            async def update_progress_during_search():
                await asyncio.sleep(1)
                update_progress(session_id, 2, "Retrieving documents", "Vector search in progress", 45)
                
                await asyncio.sleep(3)
                update_progress(session_id, 3, "Processing context", "Analyzing document content", 60)
                
                await asyncio.sleep(2)
                update_progress(session_id, 4, "Generating AI response", "AI is analyzing and composing", 85)
                
                await asyncio.sleep(1)
                update_progress(session_id, 5, "Finalizing results", "Formatting response", 95)
            
            # Start progress updates in background
            progress_task = asyncio.create_task(update_progress_during_search())
            
            # Call the actual search function
            result = await search_function(search_req)
            
            # Wait for progress updates to complete
            try:
                await progress_task
            except:
                pass
            
            # Store the final result
            progress_store[f"{session_id}_result"] = result.dict() if hasattr(result, 'dict') else result
            complete_progress(session_id, success=True)
                
        except Exception as search_error:
            logger.error(f"Search function error: {search_error}")
            complete_progress(session_id, success=False)
            
    except Exception as e:
        logger.error(f"Progress tracking error: {e}")
        complete_progress(session_id, success=False)

@router.get("/result/{session_id}")
async def get_search_result(session_id: str):
    """Get the final search result after processing is complete."""
    result = progress_store.get(f"{session_id}_result")
    if not result:
        # Check if still processing
        progress_data = progress_store.get(session_id, {})
        if progress_data.get("status") == "processing":
            return {"error": "Still processing, please wait"}
        else:
            return {"error": "Result not found"}
    return result
