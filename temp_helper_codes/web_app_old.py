#!/usr/bin/env python3
"""
FastAPI web application serving the home.html interface with RAG backend integration.
This provides 100% control over the UI while maintaining full Python RAG functionality.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import json

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import uvicorn
import hashlib
import json
from datetime import datetime
from contextlib import asynccontextmanager

from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator

# Global RAG orchestrator
rag_system = None

# Store search results for detailed views
search_results_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG system on startup and cleanup on shutdown."""
    global rag_system
    try:
        rag_system = RAGOrchestrator('./config.yaml')
        print("✅ RAG system initialized successfully")
        yield
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        rag_system = None
        yield
    finally:
        # Cleanup code would go here if needed
        pass

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="iConnect - RAG System",
    description="AI-Powered Search with 100% UI Control",
    version="1.0.0",
    lifespan=lifespan
)

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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the index.html page with 100% control."""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Home page not found")

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Process search queries through the RAG system.
    This endpoint provides the backend functionality for your home.html interface.
    """
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

@app.get("/result/{result_id}", response_class=HTMLResponse)
async def get_detailed_result(result_id: str):
    """Serve a detailed result page for a specific search result."""
    if result_id not in search_results_cache:
        raise HTTPException(status_code=404, detail="Search result not found")
    
    result_data = search_results_cache[result_id]
    
    # Generate detailed HTML page
    html_content = generate_result_page(result_data, result_id)
    return HTMLResponse(content=html_content)

def generate_result_page(result_data: dict, result_id: str) -> str:
    """Generate a detailed HTML page for search results."""
    
    # Calculate confidence score based on metadata
    confidence = int(result_data["metadata"].get("safety_score", 0.8) * 100)
    
    # Format sources HTML
    sources_html = ""
    for i, source in enumerate(result_data["sources"], 1):
        sources_html += f"""
        <div class="source-item">
            <div class="source-info">
                <div class="source-title">{source.get('title', f'Source {i}')}</div>
                <div class="source-description">{source.get('content', 'No content available')} • {source.get('author', 'Unknown author')}</div>
            </div>
            <a href="{source.get('url', '#')}" class="source-link" target="_blank">View Source</a>
        </div>
        """
    
    # Generate ticket template or actionable content based on the response
    action_content = generate_action_content(result_data)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>iConnect - Search Result</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #ffffff;
                color: #333;
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            .header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #1e88e5;
            }}
            
            .header-left {{
                display: flex;
                align-items: center;
                gap: 20px;
                flex: 1;
            }}
            
            .home-btn {{
                background: none;
                border: none;
                cursor: pointer;
                padding: 12px;
                border-radius: 12px;
                transition: all 0.3s ease;
                width: 56px;
                height: 56px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .home-btn:hover {{
                background: rgba(30,136,229,0.1);
                transform: scale(1.05);
            }}
            
            .home-icon {{
                width: 32px;
                height: 32px;
                fill: #1e88e5;
                transition: all 0.3s ease;
            }}
            
            .main-title {{
                font-size: 24px;
                background: linear-gradient(135deg, #1e88e5, #26a69a);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 300;
                letter-spacing: 1px;
                margin-bottom: 1px;
            }}
            
            .subtitle {{
                font-size: 11px;
                color: #888;
                font-weight: 400;
                margin-top: 4px;
            }}
            
            .mini-search {{
                width: 280px;
                position: relative;
            }}
            
            .mini-search-input {{
                width: 100%;
                padding: 8px 35px 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 20px;
                font-size: 13px;
                outline: none;
                background: #fafafa;
                transition: all 0.3s ease;
            }}
            
            .mini-search-input:focus {{
                border-color: #1e88e5;
                background: #ffffff;
                box-shadow: 0 2px 8px rgba(30,136,229,0.1);
            }}
            
            .mini-search-btn {{
                position: absolute;
                right: 4px;
                top: 50%;
                transform: translateY(-50%);
                background: #1e88e5;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 12px;
                padding: 6px 8px;
                border-radius: 50%;
                transition: all 0.3s ease;
                width: 26px;
                height: 26px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .search-query {{
                padding: 25px 30px;
                margin-bottom: 30px;
                background: linear-gradient(90deg, rgba(30,136,229,0.05) 0%, rgba(30,136,229,0.02) 50%, transparent 100%);
                border-radius: 12px;
                border-left: 4px solid rgba(30,136,229,0.3);
            }}
            
            .query-label {{
                font-size: 11px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            
            .query-text {{
                font-size: 20px;
                color: #333;
                font-weight: 600;
                line-height: 1.4;
            }}
            
            .response-section {{
                margin-bottom: 40px;
            }}
            
            .response-header {{
                font-size: 13px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 15px;
            }}
            
            .response-content {{
                padding: 25px 30px;
                background: linear-gradient(270deg, rgba(38,166,154,0.05) 0%, rgba(38,166,154,0.02) 50%, transparent 100%);
                border-radius: 12px;
                border-right: 4px solid rgba(38,166,154,0.3);
            }}
            
            .confidence-badge {{
                background: rgba(38,166,154,0.1);
                color: #26a69a;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 15px;
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                border: 1px solid rgba(38,166,154,0.2);
                font-weight: 600;
            }}
            
            .ai-response {{
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 20px;
                color: #333;
                font-weight: 500;
            }}
            
            .action-section {{
                background: rgba(255,255,255,0.7);
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                border: 1px solid rgba(30,136,229,0.2);
            }}
            
            .action-header {{
                font-weight: 600;
                color: #1e88e5;
                margin-bottom: 15px;
                font-size: 14px;
            }}
            
            .action-btn {{
                background: linear-gradient(135deg, #1e88e5, #26a69a);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 15px;
                box-shadow: 0 3px 8px rgba(30,136,229,0.3);
            }}
            
            .action-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(30,136,229,0.4);
            }}
            
            .sources-section {{
                margin-top: 50px;
                border-top: 1px solid #e8e8e8;
                padding-top: 30px;
            }}
            
            .sources-header {{
                font-size: 12px;
                color: #999;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 20px;
            }}
            
            .source-item {{
                padding: 12px 0;
                border-bottom: 1px solid #f0f0f0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .source-info {{
                flex: 1;
            }}
            
            .source-title {{
                font-weight: 500;
                color: #555;
                margin-bottom: 2px;
                font-size: 14px;
            }}
            
            .source-description {{
                font-size: 12px;
                color: #888;
                line-height: 1.4;
            }}
            
            .source-link {{
                color: #1e88e5;
                text-decoration: none;
                font-size: 12px;
                font-weight: 500;
            }}
            
            .source-link:hover {{
                text-decoration: underline;
            }}
            
            .metadata-section {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 30px;
                border: 1px solid #e8e8e8;
            }}
            
            .metadata-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }}
            
            .metadata-item {{
                text-align: center;
            }}
            
            .metadata-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }}
            
            .metadata-value {{
                font-size: 16px;
                font-weight: 600;
                color: #1e88e5;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-left">
                    <button class="home-btn" onclick="goHome()">
                        <svg class="home-icon" viewBox="0 0 24 24">
                            <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                        </svg>
                    </button>
                    <div>
                        <div class="main-title">iConnect</div>
                        <div class="subtitle">IntegraConnect AI-Powered Search</div>
                    </div>
                </div>
                
                <div class="mini-search">
                    <input type="text" class="mini-search-input" placeholder="Search..." />
                    <button class="mini-search-btn" onclick="performMiniSearch()">⌕</button>
                </div>
            </div>
            
            <div class="search-query">
                <div class="query-label">Your Question</div>
                <div class="query-text">{result_data['query']}</div>
            </div>
            
            <div class="response-section">
                <div class="response-header">AI Response</div>
                <div class="response-content">
                    <div class="confidence-badge">{confidence}% Confidence</div>
                    <div class="ai-response">{result_data['response']}</div>
                    {action_content}
                </div>
            </div>
            
            <div class="metadata-section">
                <div class="metadata-grid">
                    <div class="metadata-item">
                        <div class="metadata-label">Processing Time</div>
                        <div class="metadata-value">{result_data['metadata'].get('total_processing_time', 0):.2f}s</div>
                    </div>
                    <div class="metadata-item">
                        <div class="metadata-label">Sources Found</div>
                        <div class="metadata-value">{len(result_data['sources'])}</div>
                    </div>
                    <div class="metadata-item">
                        <div class="metadata-label">Safety Score</div>
                        <div class="metadata-value">{result_data['metadata'].get('safety_score', 0):.2f}</div>
                    </div>
                    <div class="metadata-item">
                        <div class="metadata-label">Timestamp</div>
                        <div class="metadata-value">{result_data['timestamp'][:19]}</div>
                    </div>
                </div>
            </div>
            
            <div class="sources-section">
                <div class="sources-header">Sources</div>
                {sources_html}
            </div>
        </div>
        
        <script>
            function goHome() {{
                window.location.href = '/';
            }}
            
            function performMiniSearch() {{
                const query = document.querySelector('.mini-search-input').value.trim();
                if (query) {{
                    window.location.href = `/?q=${{encodeURIComponent(query)}}`;
                }} else {{
                    alert('Please enter a search query!');
                }}
            }}
            
            document.querySelector('.mini-search-input').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    performMiniSearch();
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_template

def generate_action_content(result_data: dict) -> str:
    """Generate actionable content based on the response."""
    response = result_data['response'].lower()
    query = result_data['query'].lower()
    
    # Detect if this is a troubleshooting/issue query
    if any(word in query for word in ['issue', 'error', 'problem', 'failed', 'not working', 'pipeline']):
        return f"""
        <div class="action-section">
            <div class="action-header">Suggested Actions</div>
            <p>Based on this response, here are recommended next steps:</p>
            <ul style="margin: 15px 0; padding-left: 20px;">
                <li>Check the referenced documentation</li>
                <li>Review similar resolved cases</li>
                <li>Contact the relevant team if needed</li>
                <li>Create a ticket if this requires further assistance</li>
            </ul>
            <button class="action-btn" onclick="createTicket()">Create Support Ticket</button>
        </div>
        """
    
    # Detect if this is an informational query
    elif any(word in query for word in ['what', 'how', 'where', 'when', 'why']):
        return f"""
        <div class="action-section">
            <div class="action-header">Additional Resources</div>
            <p>For more detailed information:</p>
            <ul style="margin: 15px 0; padding-left: 20px;">
                <li>Review the source documents linked below</li>
                <li>Check related documentation</li>
                <li>Contact subject matter experts</li>
            </ul>
            <button class="action-btn" onclick="shareResult()">Share This Result</button>
        </div>
        """
    
    # Default action content
    return f"""
    <div class="action-section">
        <div class="action-header">Next Steps</div>
        <p>This information should help answer your question. If you need additional assistance:</p>
        <ul style="margin: 15px 0; padding-left: 20px;">
            <li>Review the sources provided below</li>
            <li>Search for related topics</li>
            <li>Contact the relevant team for clarification</li>
        </ul>
        <button class="action-btn" onclick="provideFeedback()">Provide Feedback</button>
    </div>
    """

@app.post("/api/feedback")
async def submit_feedback(query_hash: str, feedback: Dict[str, Any]):
    """Submit feedback for a query."""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        rag_system.collect_feedback(query_hash, feedback)
        return {"success": True, "message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

@app.get("/api/status")
async def system_status():
    """Get system status information."""
    if not rag_system:
        return {"status": "unavailable", "message": "RAG system not initialized"}
    
    try:
        status = rag_system.get_system_status()
        return {"status": "healthy", "details": status}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "message": "iConnect API is running"}

if __name__ == "__main__":
    print("🚀 Starting iConnect FastAPI server...")
    print("📱 Frontend: http://localhost:8000 (Your exact home.html)")
    print("🔧 API Docs: http://localhost:8000/docs")
    print("⚡ Performance: Maximum - No framework overhead")
    
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./"],
        log_level="info"
    )