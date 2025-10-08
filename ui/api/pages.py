"""
Page routes for serving HTML templates and static content.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory="ui/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main home page."""
    try:
        # For now, serve the static HTML file directly
        # Later this can be converted to use Jinja2 templates
        template_path = Path("ui/templates/home.html")
        if not template_path.exists():
            raise HTTPException(status_code=404, detail="Home page template not found")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Home page not found")

@router.get("/result/{result_id}", response_class=HTMLResponse)
async def get_detailed_result(result_id: str, request: Request):
    """Serve a detailed chat interface for a specific search result using Jinja2 template."""
    # Import here to avoid circular imports
    from api.routes import search_results_cache
    
    if result_id not in search_results_cache:
        raise HTTPException(status_code=404, detail="Search result not found")
    
    result_data = search_results_cache[result_id]
    
    # Use Jinja2 template to render the chat interface
    return templates.TemplateResponse("search_result_chat.html", {
        "request": request,
        "query": result_data.get("query", ""),
        "response": result_data.get("response", ""),
        "sources": result_data.get("sources", []),
        "metadata": result_data.get("metadata", {}),
        "query_hash": result_id,
        "audience": result_data.get("audience", "technical"),
        "timestamp": result_data.get("timestamp", ""),
        "selected_sources": result_data.get("selected_sources", []),
        "conversation": result_data.get("conversation", [])
    })

