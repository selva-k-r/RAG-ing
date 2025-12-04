"""
API routes for the RAG system.
Handles search requests, health checks, and system status.
"""

from typing import Dict, Any, List
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import enhanced response generator with relative path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from enhanced_response import enhanced_generator

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Global cache for search results
search_results_cache = {}

class SearchRequest(BaseModel):
    query: str
    sources: List[str] = ["confluence", "jira", "internal", "salesforce"]

class ChatRequest(BaseModel):
    query: str
    session_id: str

class SearchResponse(BaseModel):
    success: bool
    response: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_hash: str

class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    session_id: str

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
    Process search queries through the RAG system with enhanced response generation.
    """
    import time
    start_time = time.time()
    
    rag_system = get_rag_system()
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        # Use the query retrieval module's process_query method
        query_result = rag_system.query_retrieval.process_query(request.query.strip())
        
        # Extract documents from the result
        docs = query_result.get("documents", [])
        
        # Format document context for LLM
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"--- Document {i} (Source: {source}) ---\n{doc.page_content}\n")
        context = "\n".join(context_parts)
        
        # Generate LLM-powered response using the orchestrator
        llm_result = rag_system.llm_orchestration.generate_response(
            query=request.query.strip(),
            context=context
        )
        
        enhanced_response = llm_result.get("response", "Unable to generate response.")
        
        # Format sources for frontend
        formatted_sources = []
        for source in docs:
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
        
        # Calculate metrics
        response_time = time.time() - start_time
        unique_sources = len(set(source.get('source', '') for source in formatted_sources))
        
        # Create query hash for caching
        import hashlib
        query_hash = hashlib.md5(request.query.strip().encode()).hexdigest()[:8]
        
        current_timestamp = datetime.now().isoformat()
        
        # Cache the result for detailed view and initialize conversation
        search_results_cache[query_hash] = {
            "query": request.query.strip(),
            "response": enhanced_response,
            "sources": formatted_sources,
            "metadata": {
                "total_docs": len(docs),
                "response_type": "enhanced",
                "timestamp": current_timestamp,
                "query_result": query_result,  # Include the original query result
                "response_time": round(response_time, 2),
                "unique_sources": unique_sources,
                "source_diversity": f"Used {unique_sources} different source(s)"
            },
            "timestamp": current_timestamp,
            "selected_sources": request.sources,
            "conversation": [{
                "query": request.query.strip(),
                "response": enhanced_response,
                "sources": formatted_sources,
                "timestamp": current_timestamp,
                "response_time": round(response_time, 2),
                "unique_sources": unique_sources
            }]
        }
        
        return SearchResponse(
            success=True,
            response=enhanced_response,
            sources=formatted_sources,
            metadata={
                "total_docs": len(docs),
                "response_type": "enhanced",
                "timestamp": datetime.now().isoformat(),
                "response_time": round(response_time, 2),
                "unique_sources": unique_sources
            },
            query_hash=query_hash
        )
        
    except (ValueError, ConnectionError) as e:
        # Configuration or connectivity errors - provide actionable guidance
        import hashlib
        error_hash = hashlib.md5(f"error_{request.query}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        error_type = "Configuration Error" if isinstance(e, ValueError) else "Connection Error"
        error_message = str(e)
        
        # Create user-friendly error response with markdown formatting
        user_response = f"""## {error_type}

{error_message}

### What Happened?
The RAG system successfully retrieved relevant documents, but failed to generate an AI response because the LLM (Language Model) provider is not properly configured or accessible.

### Quick Diagnosis
- Document retrieval: Working
- Vector database: Working  
- LLM provider: **Not configured or unreachable**

### Need Help?
- Run system diagnostics: `python main.py --status`
- View troubleshooting guide: `TROUBLESHOOTING.md`
- Quick setup for Azure OpenAI: `python setup_azure_openai.py`

**Note**: This is a configuration issue, not a bug. Once the LLM provider is set up, your query will work perfectly.
"""
        
        # Log detailed error for developers
        logger.error(f"LLM {error_type} during search:")
        logger.error(error_message)
        logger.error(f"Query: {request.query}")
        logger.error(f"Provider: {rag_system.llm_orchestration.llm_config.provider if rag_system else 'Unknown'}")
        
        # Cache error response
        search_results_cache[error_hash] = {
            "query": request.query.strip(),
            "response": user_response,
            "sources": [],
            "metadata": {
                "error": True,
                "error_type": error_type,
                "error_details": error_message,
                "retrieval_status": "success",
                "llm_status": "failed"
            },
            "timestamp": datetime.now().isoformat(),
            "selected_sources": request.sources
        }
        
        raise HTTPException(
            status_code=503,
            detail={
                "error": error_type,
                "message": error_message,
                "user_message": user_response,
                "fix_instructions": "See FIX_404_ERROR.md or run setup_azure_openai.py",
                "query_hash": error_hash
            }
        )
        
    except Exception as e:
        # Unexpected errors - provide full context
        import traceback
        import hashlib
        
        error_hash = hashlib.md5(f"error_{request.query}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        full_traceback = traceback.format_exc()
        
        # Log for developers
        logger.error("Unexpected error during search:")
        logger.error(full_traceback)
        
        # User-friendly error message
        user_response = f"""## Unexpected Error

An unexpected error occurred while processing your query.

**Error Type**: {type(e).__name__}  
**Error Message**: {str(e)}

### For Users
Please try again in a moment. If the issue persists, contact your system administrator.

### For Developers
Check application logs for full traceback:
- Location: `logs/evaluation.jsonl`
- Run diagnostics: `python main.py --status`
- View error details in terminal/console output

**Error ID**: {error_hash}
"""
        
        # Cache error
        search_results_cache[error_hash] = {
            "query": request.query.strip(),
            "response": user_response,
            "sources": [],
            "metadata": {
                "error": True,
                "error_type": type(e).__name__,
                "error_details": str(e),
                "traceback": full_traceback
            },
            "timestamp": datetime.now().isoformat()
        }
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(e).__name__,
                "message": str(e),
                "user_message": user_response,
                "error_id": error_hash,
                "traceback": full_traceback if rag_system and hasattr(rag_system, 'debug_mode') else None
            }
        )

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat/follow-up queries with conversation history.
    """
    import time
    start_time = time.time()
    
    rag_system = get_rag_system()
    
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        # Get conversation history from cache
        session_data = search_results_cache.get(request.session_id, {})
        conversation_history = session_data.get('conversation', [])
        
        # Process the query
        query_result = rag_system.query_retrieval.process_query(request.query.strip())
        docs = query_result.get("documents", [])
        
        # Format document context for LLM
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"--- Document {i} (Source: {source}) ---\n{doc.page_content}\n")
        context = "\n".join(context_parts)
        
        # Add conversation history to prompt for context
        if conversation_history:
            history_text = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 exchanges
                history_text += f"User: {msg['query']}\nAssistant: {msg['response'][:200]}...\n"
            context = history_text + "\n" + context
        
        # Generate LLM-powered response
        llm_result = rag_system.llm_orchestration.generate_response(
            query=request.query.strip(),
            context=context
        )
        
        response_text = llm_result.get("response", "Unable to generate response.")
        
        # Format sources for frontend
        formatted_sources = []
        for source in docs:
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
        
        # Update conversation history
        conversation_history.append({
            "query": request.query.strip(),
            "response": response_text,
            "sources": formatted_sources,
            "timestamp": datetime.now().isoformat()
        })
        
        # Calculate metrics
        response_time = time.time() - start_time
        unique_sources = len(set(source.get('source', '') for source in formatted_sources))
        
        # Update session cache
        session_data['conversation'] = conversation_history
        session_data['last_updated'] = datetime.now().isoformat()
        search_results_cache[request.session_id] = session_data
        
        return ChatResponse(
            success=True,
            response=response_text,
            sources=formatted_sources,
            metadata={
                "total_docs": len(docs),
                "timestamp": datetime.now().isoformat(),
                "conversation_length": len(conversation_history),
                "response_time": round(response_time, 2),
                "unique_sources": unique_sources,
                "source_diversity": f"Used {unique_sources} different source(s)"
            },
            session_id=request.session_id
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health and module status with detailed diagnostics."""
    rag_system = get_rag_system()
    
    if not rag_system:
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            modules={
                "rag_system": "not_initialized",
                "message": "[FAIL] RAG system failed to initialize. Check startup logs for details.",
                "action": "Run 'python setup_azure_openai.py' or check FIX_404_ERROR.md"
            }
        )
    
    try:
        health_status = rag_system.health_check()
        
        # Add LLM connectivity details
        llm_module = rag_system.llm_orchestration
        llm_status = {
            "provider": llm_module.llm_config.provider,
            "model": llm_module.llm_config.model,
            "initialized": llm_module.client is not None,
            "status": "[OK] Connected" if llm_module.client else "[FAIL] Not connected"
        }
        
        # Test LLM connection
        try:
            connection_test = llm_module.test_connection()
            llm_status["connection_test"] = "[OK] Passed" if connection_test else "[FAIL] Failed"
        except Exception as test_error:
            llm_status["connection_test"] = f"[FAIL] Failed: {str(test_error)}"
            llm_status["action_required"] = "Check LLM provider configuration"
        
        health_status["modules"]["llm_details"] = llm_status
        
        return HealthResponse(
            status=health_status.get("overall", "unknown"),
            timestamp=health_status.get("timestamp", datetime.now().isoformat()),
            modules=health_status.get("modules", {})
        )
    except Exception as e:
        import traceback
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            modules={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message": "Health check failed. See logs for details."
            }
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
    """Submit user feedback for a message (thumbs up/down)."""
    try:
        session_id = feedback_data.get("session_id")
        message_index = feedback_data.get("message_index")
        feedback_type = feedback_data.get("feedback")  # 'positive' or 'negative'
        
        if not session_id or message_index is None:
            raise HTTPException(status_code=400, detail="session_id and message_index are required")
        
        # Get session data
        session_data = search_results_cache.get(session_id, {})
        conversation = session_data.get('conversation', [])
        
        if message_index < len(conversation):
            # Store feedback
            conversation[message_index]['feedback'] = feedback_type
            conversation[message_index]['feedback_timestamp'] = datetime.now().isoformat()
            session_data['conversation'] = conversation
            search_results_cache[session_id] = session_data
            
            return JSONResponse(content={
                "success": True, 
                "message": f"Feedback recorded: {feedback_type}"
            })
        else:
            raise HTTPException(status_code=404, detail="Message not found")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")