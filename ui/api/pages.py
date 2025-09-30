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
    """Serve a detailed result page for a specific search result."""
    # Import here to avoid circular imports
    from api.routes import search_results_cache
    
    if result_id not in search_results_cache:
        raise HTTPException(status_code=404, detail="Search result not found")
    
    result_data = search_results_cache[result_id]
    
    # For now, generate HTML directly
    # Later this can use a proper template
    html_content = generate_result_page(result_data, result_id)
    return HTMLResponse(content=html_content)

def generate_result_page(result_data: dict, result_id: str) -> str:
    """Generate a detailed HTML page for search results."""
    
    # Calculate confidence score based on metadata
    metadata = result_data.get("metadata", {})
    safety_score = metadata.get("safety_score", 0.5)
    
    # Determine confidence level
    if safety_score >= 0.8:
        confidence_level = "High"
        confidence_color = "#22c55e"  # green
        confidence_icon = "✅"
    elif safety_score >= 0.6:
        confidence_level = "Medium"
        confidence_color = "#f59e0b"  # yellow
        confidence_icon = "⚠️"
    else:
        confidence_level = "Low"
        confidence_color = "#ef4444"  # red
        confidence_icon = "❌"
    
    # Generate sources HTML
    sources_html = ""
    for idx, source in enumerate(result_data.get("sources", []), 1):
        source_title = source.get("title", "Unknown Document")
        source_url = source.get("url", "#")
        source_content = source.get("content", "No preview available")
        source_author = source.get("author", "Unknown")
        source_date = source.get("date", "Unknown")
        
        sources_html += f"""
        <div class="source-item">
            <div class="source-header">
                <span class="source-number">{idx}</span>
                <a href="{source_url}" target="_blank" class="source-title">{source_title}</a>
            </div>
            <div class="source-meta">
                <span class="author">By: {source_author}</span>
                <span class="date">Date: {source_date}</span>
            </div>
            <div class="source-preview">{source_content}</div>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Search Result - {result_data.get('query', 'Query')}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8fafc;
            }}
            
            .header {{
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 2rem;
            }}
            
            .query {{
                font-size: 1.5rem;
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 1rem;
            }}
            
            .confidence-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: {confidence_color};
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 25px;
                font-weight: 500;
                font-size: 0.875rem;
            }}
            
            .response-section {{
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 2rem;
            }}
            
            .response-content {{
                font-size: 1.1rem;
                line-height: 1.8;
                color: #374151;
            }}
            
            .sources-section {{
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .sources-header {{
                font-size: 1.25rem;
                font-weight: 600;
                color: #1e293b;
                margin-bottom: 1.5rem;
            }}
            
            .source-item {{
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1rem;
            }}
            
            .source-header {{
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 0.5rem;
            }}
            
            .source-number {{
                background: #3b82f6;
                color: white;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.875rem;
                font-weight: 600;
            }}
            
            .source-title {{
                color: #1e293b;
                text-decoration: none;
                font-weight: 600;
                font-size: 1.1rem;
            }}
            
            .source-title:hover {{
                color: #3b82f6;
            }}
            
            .source-meta {{
                display: flex;
                gap: 2rem;
                color: #6b7280;
                font-size: 0.875rem;
                margin-bottom: 1rem;
            }}
            
            .source-preview {{
                color: #4b5563;
                line-height: 1.6;
            }}
            
            .back-button {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: #3b82f6;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 500;
                margin-bottom: 2rem;
            }}
            
            .back-button:hover {{
                background: #2563eb;
            }}
            
            .metadata {{
                background: #f1f5f9;
                padding: 1rem;
                border-radius: 8px;
                margin-top: 1rem;
                font-size: 0.875rem;
                color: #64748b;
            }}
        </style>
    </head>
    <body>
        <a href="/" class="back-button">
            ← Back to Search
        </a>
        
        <div class="header">
            <div class="query">"{result_data.get('query', 'Query')}"</div>
            <div class="confidence-badge">
                {confidence_icon} {confidence_level} Confidence ({safety_score:.0%})
            </div>
        </div>
        
        <div class="response-section">
            <h2>Response</h2>
            <div class="response-content">
                {result_data.get('response', 'No response available').replace(chr(10), '<br>')}
            </div>
            
            <div class="metadata">
                <strong>Search Details:</strong><br>
                Audience: {result_data.get('audience', 'Unknown')} | 
                Timestamp: {result_data.get('timestamp', 'Unknown')} | 
                Model: {metadata.get('model_used', 'Unknown')} |
                Processing Time: {metadata.get('total_processing_time', 0):.2f}s
            </div>
        </div>
        
        <div class="sources-section">
            <div class="sources-header">Sources ({len(result_data.get('sources', []))})</div>
            {sources_html}
        </div>
    </body>
    </html>
    """
    
    return html_template