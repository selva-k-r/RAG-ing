# UI, Authentication & Personalization Flow

## Overview

This document describes the web UI architecture, distinguishing between **Completed**, **In Progress**, and **Planned** features.

**Current Status**: Basic search interface is functional; advanced features (auth, history, upload) are planned.

---

## Current Architecture (Completed)

### 1. Application Entry Point

**File**: `ui/app.py`

**Status**: ✓ Completed

**Features**:
- FastAPI application with lifespan management
- Validates LLM connectivity on startup
- Mounts static files (`/static`)
- Includes API routes and page routes

**Code** (lines 1-40):
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api import routes, pages

app = FastAPI(title="RAG-ing Search")
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
app.include_router(routes.router)
app.include_router(pages.router)

@app.on_event("startup")
async def startup_event():
    # Validate LLM connectivity
    rag_system.initialize_model()
```

**Access**: http://localhost:8000

### 2. Home / Search Page

**File**: `ui/templates/home.html`

**Route**: `/` (GET)

**Status**: ✓ Completed

**Features**:
- Search input box
- Submit button
- Basic instructions
- Links to documentation

**Code** (`ui/api/pages.py` lines 20-30):
```python
@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
```

**UI Elements**:
- Text input: `<input name="query">`
- Submit button: `<button>Search</button>`
- Form action: `/api/search` (POST)

### 3. Search API Endpoint

**File**: `ui/api/routes.py`

**Route**: `/api/search` (POST)

**Status**: ✓ Completed

**Process**:
1. Receive `SearchRequest` with query text
2. Call `rag_system.query_documents(query)`
3. Format sources and metadata
4. Return `SearchResponse` JSON

**Code** (lines 45-80):
```python
@router.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    query = request.query
    
    # Call RAG orchestrator
    result = rag_system.query_documents(
        query=query,
        user_context={}
    )
    
    # Format response
    return SearchResponse(
        answer=result["answer"],
        sources=result["sources"],
        query=query,
        retrieval_time=result["retrieval_time"],
        generation_time=result["generation_time"]
    )
```

**Request Schema**:
```json
{
  "query": "What is dbt?"
}
```

**Response Schema**:
```json
{
  "answer": "dbt (data build tool)...",
  "sources": [
    {"title": "doc1.sql", "content": "...", "score": 0.95}
  ],
  "query": "What is dbt?",
  "retrieval_time": 0.15,
  "generation_time": 1.2
}
```

### 4. Search Results Page

**File**: `ui/templates/search_result.html` (basic) or `ui/templates/search_result_chat.html` (enhanced)

**Route**: Returns HTML rendered with results

**Status**: ✓ Completed

**Features**:
- Display answer text (formatted as markdown)
- Show source citations with titles and scores
- Display raw chunk content (expandable)
- Show retrieval and generation times
- "Ask another question" link back to home

**Enhanced Features** (from `enhanced_response.py`):
- Citation numbering `[1], [2], [3]`
- Confidence scores for each source
- Metadata display (source_type, file_type, date)

### 5. Static Assets

**Directory**: `ui/static/`

**Status**: ✓ Completed

**Contents**:
- `ui/static/css/style.css` - styling for all pages
- `ui/static/js/search.js` - client-side search interactions
- Future: icons, images, vendor libraries

### 6. Health Check Endpoint

**Route**: `/api/health` (GET)

**Status**: ✓ Completed

**Returns**:
```json
{
  "status": "healthy",
  "vector_store": "chroma",
  "llm_provider": "azure_openai",
  "document_count": 1234,
  "last_ingestion": "2025-11-26T10:30:00"
}
```

---

## In Progress Features

### 7. Session-Based Activity Logging

**Files**: 
- `src/rag_ing/utils/activity_logger.py` (code exists)
- `src/rag_ing/modules/evaluation_logging.py` (logs query events)

**Status**: ⏳ In Progress (backend complete, UI wiring needed)

**Current Implementation**:
- Backend tracks queries via `ActivityLogger`
- Writes to `logs/evaluation.jsonl`
- Each query has unique `query_hash`
- Session history available in memory

**Missing**:
- UI endpoint to retrieve session history
- Frontend component to display past queries
- "View History" button on home page

**Planned Route**: `/api/history` (GET)

**Planned Response**:
```json
{
  "history": [
    {
      "query": "What is dbt?",
      "timestamp": "2025-11-26T10:30:00",
      "answer_preview": "dbt is...",
      "query_hash": "abc123"
    }
  ]
}
```

---

## Planned Features (Not Started)

### 8. Authentication & Authorization

**Status**: 📋 Planned

**Proposed Implementation**:
- **SSO/OAuth Integration**:
  - Azure AD (for enterprise)
  - Google OAuth (for external users)
  - Username/password fallback
- **Session Management**:
  - JWT tokens stored in cookies
  - Expiration: 8 hours
  - Refresh token support
- **Authorization**:
  - Role-based access control (RBAC)
  - Roles: "viewer", "contributor", "admin"
  - Document-level permissions (filter sources by user)

**Required Changes**:
- New file: `ui/api/auth.py` with login/logout routes
- Middleware: `ui/middleware/auth_middleware.py` to validate tokens
- Database table: `users` (SQLite or Postgres)
- Frontend: `ui/templates/login.html`

**Configuration** (proposed `config.yaml` additions):
```yaml
authentication:
  enabled: true
  provider: "azure_ad"
  client_id: "${AZURE_AD_CLIENT_ID}"
  client_secret: "${AZURE_AD_CLIENT_SECRET}"
  redirect_uri: "http://localhost:8000/auth/callback"
```

### 9. Personalized Dashboard

**Status**: 📋 Planned

**Proposed Features**:
- Welcome message with user name
- Quick stats:
  - "You've asked 42 questions"
  - "Top 3 sources you use"
- Recent queries (last 10)
- Favorite/pinned documents
- Suggested questions based on history

**Proposed Route**: `/dashboard` (GET)

**Proposed Template**: `ui/templates/dashboard.html`

### 10. Per-User Query History

**Status**: 📋 Planned

**Proposed Implementation**:
- Store queries in database with `user_id` foreign key
- Table schema:
  ```sql
  CREATE TABLE query_history (
      id INTEGER PRIMARY KEY,
      user_id INTEGER,
      query TEXT,
      answer TEXT,
      timestamp DATETIME,
      retrieval_time REAL,
      generation_time REAL,
      sources_json TEXT
  );
  ```
- UI features:
  - Paginated history view
  - Search within history
  - "Re-run query" button
  - "Favorite" toggle

**Proposed Route**: `/api/history?user_id={id}` (GET)

### 11. User-Specific Source Toggles

**Status**: 📋 Planned

**Current Limitation**: Sources are globally enabled/disabled via `config.yaml`

**Proposed Implementation**:
- Frontend checkboxes on search page:
  - ☑ Local Files
  - ☑ Azure DevOps
  - ☐ Confluence (disable for this query)
  - ☐ Jira
- Pass selected sources in `SearchRequest`:
  ```json
  {
    "query": "What is dbt?",
    "enabled_sources": ["local_file", "azure_devops"]
  }
  ```
- Backend filters documents by `source_type` metadata

**Required Changes**:
- Modify `SearchRequest` schema to accept `enabled_sources`
- Update `query_retrieval.py` to apply source filter
- Frontend: `ui/templates/home.html` with checkboxes

### 12. Document Upload Interface

**Status**: 📋 Planned

**Proposed Features**:
- Drag-and-drop file upload
- Supported formats: `.txt`, `.md`, `.pdf`, `.docx`, `.html`
- Assign uploaded docs to "user_uploads" source_type
- Optional: Map to user-specific collection (multi-tenancy)

**Proposed Route**: `/api/upload` (POST)

**Proposed Request**:
```python
@router.post("/api/upload")
async def upload_file(file: UploadFile, user_id: int):
    # Save file to temp directory
    # Trigger ingestion for this file only
    # Update vector store
    # Return success message
```

**Proposed Template**: `ui/templates/upload.html` with dropzone

**Integration**:
- Call `corpus_embedding.process_corpus()` with single-file mode
- Add to `ingestion_tracking.db` with `source_type="user_upload"`

### 13. FAQ / Suggested Questions

**Status**: 📋 Planned

**Proposed Implementation**:
- Curated list of common questions
- Display on home page as clickable buttons
- Optionally: Auto-generate suggestions from query history (most popular)

**Proposed Configuration** (`config.yaml`):
```yaml
ui:
  suggested_questions:
    - "What is dbt?"
    - "How do I configure sources?"
    - "What are the available data sources?"
    - "How does retrieval work?"
```

**Proposed Frontend** (`home.html`):
```html
<div class="suggestions">
  <h3>Suggested Questions:</h3>
  <button onclick="fillQuery('What is dbt?')">What is dbt?</button>
  <button onclick="fillQuery('How do I...')">How do I configure sources?</button>
</div>
```

### 14. Feedback Mechanism

**Status**: 📋 Planned

**Proposed Features**:
- Thumbs up/down on answers
- Optional text feedback
- Store feedback with query_hash in database

**Proposed Route**: `/api/feedback` (POST)

**Proposed Request**:
```json
{
  "query_hash": "abc123",
  "rating": "positive",
  "comment": "Very helpful!"
}
```

**Uses**:
- RAGAS evaluation correlation
- Model fine-tuning data
- Quality monitoring

---

## Feature Status Summary

| Feature | Status | Files | Priority |
|---------|--------|-------|----------|
| Home page | ✓ Completed | `home.html`, `pages.py` | - |
| Search API | ✓ Completed | `routes.py` | - |
| Results page | ✓ Completed | `search_result.html` | - |
| Static assets | ✓ Completed | `ui/static/` | - |
| Health check | ✓ Completed | `routes.py` | - |
| Activity logging (backend) | ⏳ In Progress | `activity_logger.py` | High |
| History UI | 📋 Planned | TBD | High |
| Authentication | 📋 Planned | `auth.py` (new) | Medium |
| Dashboard | 📋 Planned | `dashboard.html` (new) | Medium |
| Source toggles | 📋 Planned | `home.html` | Medium |
| Document upload | 📋 Planned | `upload.html` (new) | Low |
| FAQ suggestions | 📋 Planned | `home.html` | Low |
| Feedback | 📋 Planned | `routes.py` | Low |

---

## Current UI Flow (Step-by-Step)

1. **User opens** http://localhost:8000
2. **Browser loads** `home.html` with search box
3. **User enters query** "What is dbt?"
4. **Frontend submits** POST to `/api/search` with JSON body
5. **Backend calls** `RAGOrchestrator.query_documents()`
6. **Retrieval module** fetches relevant documents from ChromaDB
7. **LLM module** generates answer using Azure OpenAI
8. **Evaluation module** logs query to `evaluation.jsonl`
9. **API returns** JSON with answer + sources
10. **Frontend renders** `search_result.html` with formatted answer
11. **User sees** answer text, source citations, metadata

---

## Configuration

All UI behavior controlled by:
- **FastAPI config** in `ui/app.py`
- **Template directory**: `ui/templates/`
- **Static directory**: `ui/static/`
- **Port**: 8000 (hardcoded in `main.py`)

Proposed future config (`config.yaml`):
```yaml
ui:
  host: "0.0.0.0"
  port: 8000
  enable_auth: false
  enable_uploads: false
  suggested_questions: []
  session_timeout_hours: 8
```

---

## Key Files

### Completed
- `ui/app.py` - FastAPI application
- `ui/api/routes.py` - REST API endpoints
- `ui/api/pages.py` - HTML page routes
- `ui/templates/home.html` - search page
- `ui/templates/search_result.html` - results display
- `ui/static/css/style.css` - styling
- `ui/static/js/search.js` - client-side logic

### Planned
- `ui/api/auth.py` - authentication routes
- `ui/api/history.py` - query history routes
- `ui/templates/login.html` - login page
- `ui/templates/dashboard.html` - personalized dashboard
- `ui/templates/upload.html` - document upload UI
- `ui/middleware/auth_middleware.py` - token validation
