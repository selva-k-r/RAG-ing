"""
Progress tracking routes using Server-Sent Events (SSE).
Provides real-time progress updates without slowing down the main processing.
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

logger = logging.getLogger(__name__)

router = APIRouter()

# Global progress tracking
progress_store: Dict[str, Dict[str, Any]] = {}

class ProgressSearchRequest(BaseModel):
    query: str
    sources: list = ["confluence", "jira", "internal", "salesforce"]
    audience: str = "technical"

class ProgressTracker:
    """Thread-safe progress tracker for RAG operations."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.steps = [
            {"name": "Initializing", "weight": 5},
            {"name": "Searching knowledge base", "weight": 20},
            {"name": "Retrieving relevant documents", "weight": 15},
            {"name": "Processing context", "weight": 10},
            {"name": "Generating AI response", "weight": 40},
            {"name": "Finalizing results", "weight": 10}
        ]
        self.current_step = 0
        self.current_progress = 0
        self.status = "starting"
        self.details = ""
        
    def update_step(self, step_index: int, details: str = ""):
        """Update current step and details."""
        self.current_step = step_index
        self.details = details
        self.status = "processing"
        
        # Calculate progress based on completed steps
        completed_weight = sum(step["weight"] for step in self.steps[:step_index])
        current_step_progress = 0.3  # Assume 30% through current step
        if step_index < len(self.steps):
            current_step_progress *= self.steps[step_index]["weight"]
        
        self.current_progress = min(95, completed_weight + current_step_progress)
        
        # Store in global progress store
        progress_store[self.session_id] = {
            "progress": self.current_progress,
            "step": step_index,
            "step_name": self.steps[step_index]["name"] if step_index < len(self.steps) else "Complete",
            "details": details,
            "status": self.status,
            "elapsed": time.time() - self.start_time
        }
        
    def complete(self, success: bool = True):
        """Mark processing as complete."""
        self.current_progress = 100
        self.status = "complete" if success else "error"
        progress_store[self.session_id] = {
            "progress": 100,
            "step": len(self.steps),
            "step_name": "Complete",
            "details": "Response generated successfully" if success else "Error occurred",
            "status": self.status,
            "elapsed": time.time() - self.start_time
        }

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
            # Add some visual flair with "words flying" effect
            flying_words = generate_flying_words(progress_data.get("step", 0))
            
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
            # Send final event
            yield f"data: {json.dumps({'type': 'complete', 'session_id': session_id, 'status': progress_data.get('status')})}\n\n"
            break
            
        # Check for timeout (30 seconds max)
        if elapsed > 30:
            yield f"data: {json.dumps({'type': 'timeout', 'session_id': session_id})}\n\n"
            break
            
        await asyncio.sleep(0.1)  # Update every 100ms

def generate_flying_words(step: int) -> list:
    """Generate contextual 'flying words' based on current processing step."""
    word_sets = [
        ["initializing", "loading", "preparing", "starting"],
        ["searching", "indexing", "querying", "scanning", "retrieving", "matching"],
        ["documents", "context", "relevance", "similarity", "ranking"],
        ["processing", "analyzing", "parsing", "extracting", "filtering"],
        ["generating", "reasoning", "thinking", "composing", "crafting", "AI", "GPT-4"],
        ["finalizing", "formatting", "completing", "optimizing", "ready"]
    ]
    
    if step < len(word_sets):
        return word_sets[step]
    return ["processing", "working", "computing"]

@router.get("/progress/{session_id}")
async def stream_progress(session_id: str):
    """Stream progress updates using Server-Sent Events."""
    return StreamingResponse(
        generate_progress_stream(session_id),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@router.post("/search-with-progress")
async def search_with_progress(request: ProgressSearchRequest):
    """
    Initiate search with progress tracking.
    Returns session_id immediately, client connects to /progress/{session_id} for updates.
    """
    session_id = str(uuid.uuid4())
    
    # Start the background task
    asyncio.create_task(process_search_with_progress(session_id, request))
    
    return {
        "session_id": session_id,
        "progress_url": f"/api/progress/{session_id}",
        "estimated_time": "15-20 seconds"
    }

async def process_search_with_progress(session_id: str, request: ProgressSearchRequest):
    """Process search query with progress updates."""
    tracker = ProgressTracker(session_id)
    
    try:
        # Get RAG system
        rag_system = get_rag_system()
        if not rag_system:
            tracker.complete(success=False)
            return
        
        # Step 1: Initialize
        tracker.update_step(0, "Setting up search parameters")
        await asyncio.sleep(0.2)  # Small delay for UI effect
        
        # Step 2: Search knowledge base
        tracker.update_step(1, f"Searching across {len(request.sources)} data sources")
        await asyncio.sleep(0.1)
        
        # Run the actual query (this is the main time-consuming part)
        query_result = await asyncio.get_event_loop().run_in_executor(
            None, 
            rag_system.query_retrieval.process_query, 
            request.query.strip()
        )
        
        # Step 3: Process documents
        tracker.update_step(2, f"Found {len(query_result.get('documents', []))} relevant documents")
        docs = query_result.get("documents", [])
        
        # Step 4: Prepare context
        tracker.update_step(3, "Preparing context for AI analysis")
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"--- Document {i} (Source: {source}) ---\n{doc.page_content}\n")
        context = "\n".join(context_parts)
        
        # Step 5: Generate AI response
        tracker.update_step(4, "AI is analyzing and generating response...")
        
        llm_result = await asyncio.get_event_loop().run_in_executor(
            None,
            rag_system.llm_orchestration.generate_response,
            request.query.strip(),
            context,
            request.audience
        )
        
        # Step 6: Finalize
        tracker.update_step(5, "Formatting final response")
        
        # Format the final result
        formatted_sources = []
        for source in docs:
            formatted_sources.append({
                "content": source.page_content[:500] + "..." if len(source.page_content) > 500 else source.page_content,
                "metadata": source.metadata,
                "relevance_score": getattr(source, 'relevance_score', 0.8)
            })
        
        # Store final result
        final_result = {
            "success": True,
            "response": llm_result.get("response", "Unable to generate response."),
            "sources": formatted_sources,
            "metadata": {
                "query_hash": session_id,
                "processing_time": time.time() - tracker.start_time,
                "source_count": len(docs),
                "confidence_score": llm_result.get("confidence_score", 0.8)
            }
        }
        
        # Store result for retrieval
        progress_store[f"{session_id}_result"] = final_result
        
        # Mark complete
        tracker.complete(success=True)
        
    except Exception as e:
        logger.error(f"Error in search processing: {e}")
        tracker.complete(success=False)

@router.get("/result/{session_id}")
async def get_search_result(session_id: str):
    """Get the final search result after processing is complete."""
    result = progress_store.get(f"{session_id}_result")
    if not result:
        return {"error": "Result not found or still processing"}
    return result

def get_rag_system():
    """Get the RAG system instance from the main app."""
    try:
        # Try multiple import paths
        try:
            from ..app import rag_system
            return rag_system
        except:
            import sys
            import os
            # Add the ui directory to path
            ui_path = os.path.join(os.path.dirname(__file__), '..')
            if ui_path not in sys.path:
                sys.path.insert(0, ui_path)
            from app import rag_system
            return rag_system
    except Exception as e:
        logger.error(f"Failed to get RAG system: {e}")
        return None
