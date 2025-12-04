# UI Components: FastAPI Web Interface

## Overview

The RAG-ing UI is a modern web interface built with FastAPI, providing search capabilities, result visualization, and system management features.

**Technology Stack**: FastAPI, Jinja2 templates, HTML5, CSS3, JavaScript  
**Port**: 8000 (configurable)  
**Access**: http://localhost:8000

---

## Architecture

```
ui/
├── app.py                    # FastAPI application entry point
├── __init__.py
├── enhanced_response.py      # Response formatting utilities
├── api/
│   ├── __init__.py
│   ├── routes.py            # REST API endpoints
│   ├── pages.py             # HTML page routes
│   └── simple_progress.py   # Progress tracking (ingestion)
├── templates/
│   ├── home.html            # Search page
│   ├── search_result.html   # Results display (basic)
│   └── search_result_chat.html  # Results display (enhanced)
├── static/
│   ├── css/
│   │   └── style.css        # Application styles
│   └── js/
│       └── search.js        # Client-side interactions
└── logs/
    └── *.jsonl              # Metrics logs (symlinked)
```

---

## Component Status

| Component | Status | Priority | Description |
|-----------|--------|----------|-------------|
| Home Page | ✓ Completed | - | Search input and filters |
| Search API | ✓ Completed | - | `/api/search` endpoint |
| Results Page | ✓ Completed | - | Answer + sources display |
| Health Check | ✓ Completed | - | `/api/health` endpoint |
| Static Assets | ✓ Completed | - | CSS, JS files |
| Activity Logging | ⏳ Backend Complete | High | Query history tracking |
| History UI | 📋 Planned | High | View past queries |
| Authentication | 📋 Planned | Medium | SSO/OAuth login |
| Dashboard | 📋 Planned | Medium | Personalized home |
| Source Toggles | 📋 Planned | Medium | Per-query source filtering |
| Document Upload | 📋 Planned | Low | User file uploads |
| FAQ Suggestions | 📋 Planned | Low | Common questions |
| Feedback System | 📋 Planned | Low | Thumbs up/down |

**Legend**: ✓ Completed, ⏳ In Progress, 📋 Planned

---

## Completed Components

### 1. FastAPI Application (`app.py`)

**Purpose**: Application entry point with lifecycle management

**Key Features**:
- Lifespan context manager (startup/shutdown)
- LLM connectivity validation on startup
- Static file mounting
- Router inclusion
- CORS configuration (optional)

**Code**:
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .api import routes, pages
from ..orchestrator import RAGOrchestrator
from ..config.settings import Settings

# Global RAG system instance
settings = Settings.from_yaml("./config.yaml")
rag_system = RAGOrchestrator(settings)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[OK] Starting FastAPI application...")
    print("[OK] Validating LLM connectivity...")
    try:
        rag_system.llm_orchestration.initialize_model()
        print("[OK] LLM connected successfully")
    except Exception as e:
        print(f"[X] LLM initialization failed: {e}")
        print("[!] Some features may be unavailable")
    
    yield
    
    # Shutdown
    print("[OK] Shutting down FastAPI application...")

app = FastAPI(
    title="RAG-ing Search",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# Include routers
app.include_router(routes.router)
app.include_router(pages.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Startup Output**:
```
[OK] Starting FastAPI application...
[OK] Validating LLM connectivity...
[OK] LLM connected successfully
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Home Page (`templates/home.html`)

**Purpose**: Search interface with input and filters

**Route**: `/` (GET)

**Features**:
- Search input box (text)
- Submit button
- Optional source filters (basic)
- Instructions/help text
- Links to documentation

**Layout**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>RAG-ing Search</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>RAG-ing Document Search</h1>
            <p>Ask questions about your documents</p>
        </header>
        
        <main>
            <form id="search-form" action="/api/search" method="POST">
                <div class="search-box">
                    <input 
                        type="text" 
                        name="query" 
                        id="query-input"
                        placeholder="Ask a question..."
                        required
                        autofocus
                    >
                    <button type="submit">Search</button>
                </div>
                
                <!-- Optional filters -->
                <div class="filters" style="display:none;">
                    <label>
                        <input type="checkbox" name="source" value="local_file" checked>
                        Local Files
                    </label>
                    <label>
                        <input type="checkbox" name="source" value="azure_devops" checked>
                        Azure DevOps
                    </label>
                </div>
            </form>
            
            <div class="examples">
                <h3>Example Questions:</h3>
                <ul>
                    <li><a href="#" class="example-query">What is dbt?</a></li>
                    <li><a href="#" class="example-query">How do I create a staging model?</a></li>
                    <li><a href="#" class="example-query">What are the available data sources?</a></li>
                </ul>
            </div>
        </main>
        
        <footer>
            <a href="/api/health">System Health</a> |
            <a href="/docs">API Docs</a>
        </footer>
    </div>
    
    <script src="/static/js/search.js"></script>
</body>
</html>
```

**Interaction Flow**:
1. User types query
2. Clicks "Search" or presses Enter
3. JavaScript intercepts form submission
4. AJAX POST to `/api/search`
5. Redirect to results page or inline display

### 3. Search API Endpoint (`api/routes.py`)

**Purpose**: Process search queries and return results

**Route**: `/api/search` (POST)

**Request Schema**:
```python
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    filters: dict = {}
    user_context: dict = {}
```

**Response Schema**:
```python
class SearchResponse(BaseModel):
    answer: str
    sources: List[dict]
    query: str
    retrieval_time: float
    generation_time: float
    model: str
    document_count: int
```

**Implementation**:
```python
from fastapi import APIRouter, HTTPException
from ..models import SearchRequest, SearchResponse
import time

router = APIRouter(prefix="/api", tags=["API"])

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        # Validate query
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Call RAG orchestrator
        start_time = time.time()
        result = rag_system.query_documents(
            query=request.query,
            user_context=request.user_context
        )
        total_time = time.time() - start_time
        
        # Format sources
        formatted_sources = []
        for doc in result.get("documents", []):
            formatted_sources.append({
                "title": doc["metadata"].get("filename", "Unknown"),
                "content": doc["content"][:500] + "...",  # Preview
                "score": doc["score"],
                "source_type": doc["metadata"].get("source", "unknown"),
                "path": doc["metadata"].get("path", "")
            })
        
        # Build response
        return SearchResponse(
            answer=result["answer"],
            sources=formatted_sources,
            query=request.query,
            retrieval_time=result.get("retrieval_time", 0),
            generation_time=result.get("generation_time", 0),
            model=result.get("model", "unknown"),
            document_count=len(formatted_sources)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Example Response**:
```json
{
  "answer": "dbt (data build tool) is a transformation workflow that helps teams quickly and collaboratively deploy analytics code. It allows analysts to write modular SQL SELECT statements and manages the transformation process.",
  "sources": [
    {
      "title": "dbt_introduction.md",
      "content": "dbt (data build tool) is...",
      "score": 0.95,
      "source_type": "azure_devops",
      "path": "/docs/dbt_introduction.md"
    }
  ],
  "query": "What is dbt?",
  "retrieval_time": 0.15,
  "generation_time": 1.2,
  "model": "gpt-4",
  "document_count": 5
}
```

**Error Handling**:
```python
# 400 Bad Request: Invalid query
{
  "detail": "Query cannot be empty"
}

# 500 Internal Server Error: Processing failure
{
  "detail": "Azure OpenAI API error: Connection timeout"
}
```

### 4. Results Page (`templates/search_result.html`)

**Purpose**: Display answer and source citations

**Route**: Rendered by `/api/search` redirect or inline

**Features**:
- Answer text (formatted markdown)
- Source citations with titles
- Relevance scores
- Expandable source content
- Metadata (source type, date, path)
- Performance metrics (retrieval/generation time)
- "Ask another question" link

**Layout**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Search Results - RAG-ing</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>RAG-ing Search</h1>
            <a href="/" class="back-link">← New Search</a>
        </header>
        
        <main>
            <!-- Query Display -->
            <div class="query-display">
                <strong>Your Question:</strong>
                <p>{{ query }}</p>
            </div>
            
            <!-- Answer Section -->
            <div class="answer-section">
                <h2>Answer</h2>
                <div class="answer-content">
                    {{ answer | markdown }}
                </div>
            </div>
            
            <!-- Sources Section -->
            <div class="sources-section">
                <h2>Sources ({{ sources|length }})</h2>
                {% for source in sources %}
                <div class="source-card">
                    <div class="source-header">
                        <h3>[{{ loop.index }}] {{ source.title }}</h3>
                        <span class="score">Relevance: {{ "%.2f"|format(source.score) }}</span>
                    </div>
                    <div class="source-meta">
                        <span class="badge">{{ source.source_type }}</span>
                        <span class="path">{{ source.path }}</span>
                    </div>
                    <div class="source-content">
                        <details>
                            <summary>View content</summary>
                            <pre>{{ source.content }}</pre>
                        </details>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <!-- Performance Metrics -->
            <div class="metrics">
                <h3>Performance</h3>
                <ul>
                    <li>Retrieval: {{ "%.2f"|format(retrieval_time) }}s</li>
                    <li>Generation: {{ "%.2f"|format(generation_time) }}s</li>
                    <li>Total: {{ "%.2f"|format(retrieval_time + generation_time) }}s</li>
                    <li>Model: {{ model }}</li>
                </ul>
            </div>
        </main>
    </div>
</body>
</html>
```

**Enhanced Version** (`search_result_chat.html`):
- Chat-style layout
- Inline citations `[1], [2], [3]`
- Confidence indicators
- Copy answer button
- Share link generation

### 5. Health Check Endpoint (`api/routes.py`)

**Purpose**: System status monitoring

**Route**: `/api/health` (GET)

**Implementation**:
```python
@router.get("/health")
async def health_check():
    try:
        # Check vector store
        collection = rag_system.corpus_embedding.vector_store.get()
        doc_count = len(collection.get("ids", []))
        
        # Check LLM
        llm_status = "healthy" if rag_system.llm_orchestration.client else "unavailable"
        
        # Get last ingestion time
        tracker = rag_system.corpus_embedding._ingestion_tracker
        stats = tracker.get_statistics()
        
        return {
            "status": "healthy",
            "vector_store": {
                "type": "chroma",
                "document_count": doc_count,
                "collection": "rag_documents"
            },
            "llm": {
                "status": llm_status,
                "provider": "azure_openai",
                "model": rag_system.llm_orchestration.model_name
            },
            "ingestion": {
                "last_run": stats.get("last_ingestion"),
                "total_documents": stats.get("total_documents"),
                "total_chunks": stats.get("total_chunks")
            },
            "uptime": "5h 23m"  # TODO: implement actual uptime tracking
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }
```

**Example Response**:
```json
{
  "status": "healthy",
  "vector_store": {
    "type": "chroma",
    "document_count": 1234,
    "collection": "rag_documents"
  },
  "llm": {
    "status": "healthy",
    "provider": "azure_openai",
    "model": "gpt-4"
  },
  "ingestion": {
    "last_run": "2025-11-26T10:30:00",
    "total_documents": 152,
    "total_chunks": 1234
  },
  "uptime": "5h 23m"
}
```

### 6. Static Assets

**CSS** (`static/css/style.css`):
```css
/* Modern, clean design */
:root {
    --primary-color: #0066cc;
    --secondary-color: #f0f0f0;
    --text-color: #333;
    --border-color: #ddd;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    margin: 0;
    padding: 20px;
    background: #fafafa;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    background: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.search-box {
    display: flex;
    gap: 10px;
    margin: 20px 0;
}

.search-box input {
    flex: 1;
    padding: 12px;
    font-size: 16px;
    border: 2px solid var(--border-color);
    border-radius: 4px;
}

.search-box button {
    padding: 12px 24px;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.source-card {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 15px;
    margin: 10px 0;
}

.badge {
    display: inline-block;
    padding: 4px 8px;
    background: var(--secondary-color);
    border-radius: 3px;
    font-size: 12px;
}
```

**JavaScript** (`static/js/search.js`):
```javascript
// Handle form submission
document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = document.getElementById('query-input').value;
    
    // Show loading indicator
    const button = e.target.querySelector('button');
    button.textContent = 'Searching...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const result = await response.json();
        
        // Display results (inline or redirect)
        displayResults(result);
        
    } catch (error) {
        alert('Search failed: ' + error.message);
    } finally {
        button.textContent = 'Search';
        button.disabled = false;
    }
});

// Example query click handlers
document.querySelectorAll('.example-query').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('query-input').value = e.target.textContent;
    });
});
```

---

## In Progress Components

### 7. Query History (Backend Complete, UI Pending)

**Backend**: `ActivityLogger` tracks all queries in memory and logs

**File**: `logs/evaluation.jsonl`

**Format**:
```json
{
  "query_hash": "abc123",
  "query": "What is dbt?",
  "timestamp": "2025-11-26T10:30:00",
  "retrieval_time": 0.15,
  "generation_time": 1.2,
  "answer_length": 256,
  "document_count": 5
}
```

**Missing**: UI endpoint and template to display history

**Planned Endpoint**: `/api/history` (GET)

**Planned Template**: `templates/history.html`

---

## Planned Components

### 8. Authentication (SSO/OAuth)

**Providers**: Azure AD, Google OAuth, username/password

**Required Files**:
- `ui/api/auth.py` - login/logout routes
- `ui/middleware/auth_middleware.py` - JWT validation
- `ui/templates/login.html` - login form

**Configuration**:
```yaml
authentication:
  enabled: true
  provider: "azure_ad"
  client_id: "${AZURE_AD_CLIENT_ID}"
  client_secret: "${AZURE_AD_CLIENT_SECRET}"
```

### 9. Document Upload Interface

**Feature**: Drag-and-drop file upload

**Route**: `/upload` (GET), `/api/upload` (POST)

**Process**:
1. User uploads file
2. Save to temp directory
3. Trigger ingestion for single file
4. Return success/failure

### 10. FAQ Suggestions

**Feature**: Common questions on home page

**Configuration**:
```yaml
ui:
  suggested_questions:
    - "What is dbt?"
    - "How do I configure sources?"
```

---

## Deployment

### Local Development
```bash
python main.py --ui
# Access: http://localhost:8000
```

### Production (Docker)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["python", "main.py", "--ui"]
```

### Reverse Proxy (nginx)
```nginx
server {
    listen 80;
    server_name rag.company.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /app/ui/static;
        expires 30d;
    }
}
```

---

## Summary

The UI provides a complete web interface with:
- ✓ Search page with query input
- ✓ REST API for programmatic access
- ✓ Results page with citations
- ✓ Health check endpoint
- ✓ Static assets (CSS, JS)
- ⏳ Query history (backend complete)
- 📋 Authentication, upload, FAQ (planned)

**Result**: Production-ready web interface accessible at http://localhost:8000
