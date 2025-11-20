# RAG-ing PoC Requirements & Implementation Plan

**Version**: 0.2 (PoC Enhancement)  
**Last Updated**: November 19, 2024  
**Status**: In Progress  
**Purpose**: Document Manager AI - Production-ready PoC with hierarchical storage and fine-tuning support

---

## 1. Executive Summary

### 1.1 Current State (v0.1)
- ✅ **Working**: Confluence document search with AI-powered answers
- ✅ **Core features**: Hybrid search, Azure OpenAI integration, ChromaDB vector storage
- ✅ **UI**: FastAPI web interface with progress tracking
- 🔧 **Status**: Functional but needs fine-tuning and production-readiness improvements

### 1.2 PoC Goals (v0.2)
- **Primary**: Production-ready search system with quality monitoring
- **Secondary**: Enable continuous improvement through user feedback
- **Timeline**: 2-3 weeks for core improvements

### 1.3 Out of Scope (Post-PoC)
- ❌ User authentication (SSO, SAML)
- ❌ Multi-tenancy and user management
- ❌ OCR and image-to-text processing
- ❌ Advanced analytics dashboard

---

## 2. Current Implementation (v0.1)

### 2.1 Technology Stack

| Component | Technology | Version | Status |
|-----------|------------|---------|--------|
| **Language** | Python | 3.8+ | ✅ |
| **Web Framework** | FastAPI | 0.121.1 | ✅ |
| **Vector Database** | ChromaDB | 1.3.4 | ✅ |
| **Embeddings** | Azure OpenAI | text-embedding-ada-002 | ✅ |
| **LLM** | Azure OpenAI | gpt-5-nano (GPT-4) | ✅ |
| **Search** | Hybrid (Semantic + BM25) | - | ✅ |
| **Reranking** | cross-encoder | ms-marco-MiniLM-L-6-v2 | ✅ |

### 2.2 What Works

#### Storage Layer
```python
# Current implementation
- Local files: PDF, MD, TXT, HTML (pdfplumber, pymupdf)
- Confluence: REST API connector with OAuth
- Chunking: 1200 tokens, 100 overlap
- Embeddings: Azure OpenAI text-embedding-ada-002 (1536 dimensions)
- Vector storage: ChromaDB persistent storage in ./vector_store/
```

#### Retrieval Layer
```python
# Current configuration (config.yaml)
retrieval:
  strategy: "hybrid"
  semantic_weight: 0.6  # ChromaDB cosine similarity
  keyword_weight: 0.4   # BM25 keyword matching
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20
    top_k_final: 5
```

#### LLM Orchestration
```python
# Current configuration
llm:
  model: "gpt-5-nano"
  provider: "azure_openai"
  temperature: 0.1
  max_tokens: 4096
  max_context_tokens: 12000
```

#### UI Layer
```python
# Current features
- FastAPI REST API (/api/search, /api/ingest)
- Web interface with search
- Real-time progress tracking (SSE)
- Multi-source selection
- Basic thumbs up/down feedback (in-memory only)
```

### 2.3 Known Issues & Limitations

| Issue | Impact | Priority |
|-------|--------|----------|
| No duplicate detection | Wastes storage, confuses search | 🔴 High |
| No user activity logging | Can't fine-tune or improve | 🔴 High |
| Feedback not persistent | Lose user insights | 🟡 Medium |
| No personalization | One-size-fits-all UX | 🟡 Medium |
| Manual prompt tuning | Hard to optimize | 🟡 Medium |

---

## 3. PoC Scope (v0.2) - Must Implement

### 3.1 Duplicate Detection System

**Goal**: Prevent duplicate documents from entering the system, improving search quality and reducing storage costs.

#### 3.1.1 Implementation Strategy

**Multi-stage detection:**

```python
# Stage 1: Exact duplicate detection (at ingestion)
# - Hash-based: SHA256 of document content
# - Fast, catches identical documents
# - Implementation: Before chunking

# Stage 2: Near-duplicate detection (at chunk level)
# - Fuzzy matching: Check similarity of chunks
# - Catches minor variations (formatting, whitespace)
# - Implementation: After chunking, before embedding

# Stage 3: Semantic duplicate detection (at retrieval)
# - Embedding similarity: Cosine similarity threshold
# - Catches semantically similar content
# - Implementation: During search result deduplication
```

#### 3.1.2 Technical Specifications

```python
# Required packages
dependencies = [
    "hashlib",           # Built-in, for SHA256
    "fuzzywuzzy==0.18.0",  # For fuzzy string matching
    "python-Levenshtein==0.21.1",  # Speed up fuzzywuzzy
]

# Configuration (add to config.yaml)
duplicate_detection:
  enabled: true
  
  # Stage 1: Exact match
  exact_match:
    enabled: true
    hash_algorithm: "sha256"
    metadata_tracking: true  # Track source, timestamp
  
  # Stage 2: Near-duplicate
  fuzzy_match:
    enabled: true
    similarity_threshold: 0.95  # 95% similarity = duplicate
    chunk_comparison: true
  
  # Stage 3: Semantic duplicate
  semantic_match:
    enabled: true
    embedding_similarity_threshold: 0.98  # Very high for duplicates
    apply_at_retrieval: true
```

#### 3.1.3 Implementation Files

```python
# New file: src/rag_ing/utils/duplicate_detector.py
class DuplicateDetector:
    def __init__(self, config):
        self.config = config
        self.document_hashes = {}  # In-memory cache
        
    def is_exact_duplicate(self, content: str) -> bool:
        """Check if document already exists (SHA256)"""
        
    def is_fuzzy_duplicate(self, content: str, threshold: float = 0.95) -> bool:
        """Check if document is near-duplicate (fuzzy match)"""
        
    def is_semantic_duplicate(self, embedding: List[float], threshold: float = 0.98) -> bool:
        """Check if embedding is semantically duplicate"""
        
    def mark_as_processed(self, content: str, metadata: dict):
        """Store hash and metadata for future checks"""

# Storage: SQLite database for hash tracking
# File: ./vector_store/document_hashes.db
# Schema:
#   - id: int (primary key)
#   - content_hash: text (SHA256)
#   - source: text (confluence, local, etc.)
#   - source_url: text
#   - first_seen: timestamp
#   - last_updated: timestamp
```

#### 3.1.4 Integration Points

```python
# Modify: src/rag_ing/modules/corpus_embedding.py
# Add duplicate check before processing:

def process_document(self, doc):
    # NEW: Check for duplicates
    if self.duplicate_detector.is_exact_duplicate(doc.content):
        logger.info(f"Skipping exact duplicate: {doc.source}")
        return None
    
    # Existing chunking logic
    chunks = self.chunk_document(doc)
    
    # NEW: Check chunks for near-duplicates
    unique_chunks = self.duplicate_detector.filter_fuzzy_duplicates(chunks)
    
    # Existing embedding logic
    embeddings = self.generate_embeddings(unique_chunks)
    return embeddings
```

---

### 3.2 User Activity Logging

**Goal**: Track user interactions to enable fine-tuning, quality monitoring, and personalization.

#### 3.2.1 What to Log

```python
# Activity types
activity_types = [
    "search_query",        # User search
    "search_result",       # Results returned
    "feedback_positive",   # Thumbs up
    "feedback_negative",   # Thumbs down
    "source_click",        # Clicked on source document
    "session_start",       # User opened app
    "session_end",         # User closed app
]
```

#### 3.2.2 Log Schema

```json
{
  "event_id": "uuid-string",
  "timestamp": "2024-11-18T10:30:00Z",
  "session_id": "session-uuid",
  "event_type": "search_query",
  "user_id": "anonymous-001",  // For PoC, use session-based ID
  
  // Query details
  "query": {
    "text": "How do I configure FHIR resources?",
    "sources_selected": ["confluence", "local"],
    "filters": {}
  },
  
  // Results details
  "results": {
    "num_results": 5,
    "top_result_score": 0.87,
    "retrieval_time_ms": 234,
    "generation_time_ms": 1567,
    "total_time_ms": 1801
  },
  
  // Retrieved documents
  "retrieved_docs": [
    {
      "doc_id": "conf-123",
      "score": 0.87,
      "source": "confluence",
      "title": "FHIR Configuration Guide"
    }
  ],
  
  // Generated response (for fine-tuning)
  "response": {
    "text": "To configure FHIR resources...",
    "token_count": 245,
    "sources_cited": ["conf-123", "local-456"]
  },
  
  // User feedback (if provided)
  "feedback": {
    "type": "positive",  // or "negative"
    "timestamp": "2024-11-18T10:31:00Z",
    "comment": null  // Optional user comment
  },
  
  // Context for debugging
  "context": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "10.0.0.1",  // For PoC analytics
    "referrer": null
  }
}
```

#### 3.2.3 Storage Strategy

```python
# Primary storage: JSONL files (one line per event)
# Location: ./logs/user_activity/YYYY-MM-DD.jsonl

# Benefits:
# - Easy to append (no database needed for PoC)
# - Easy to parse for analysis
# - Can be imported into analytics tools later
# - Compatible with existing evaluation logs

# Rotation: Daily files
# Retention: 90 days (configurable)
```

#### 3.2.4 Implementation

```python
# New file: src/rag_ing/utils/activity_logger.py
import json
import uuid
from datetime import datetime
from pathlib import Path

class ActivityLogger:
    def __init__(self, log_dir: str = "./logs/user_activity"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, data: dict, session_id: str):
        """Log a user activity event"""
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "event_type": event_type,
            **data
        }
        
        # Write to daily log file
        log_file = self.log_dir / f"{datetime.utcnow().date()}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
    
    def log_search(self, query: str, results: list, session_id: str):
        """Log a search query and results"""
        
    def log_feedback(self, session_id: str, message_index: int, 
                     feedback_type: str):
        """Log user feedback on a response"""
```

#### 3.2.5 Integration Points

```python
# Modify: ui/api/routes.py
# Add activity logging to search endpoint:

from src.rag_ing.utils.activity_logger import ActivityLogger

activity_logger = ActivityLogger()

@router.post("/api/search")
async def search(request: SearchRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    # Existing search logic
    results = rag_orchestrator.query_documents(
        query=request.query,
        audience=request.audience
    )
    
    # NEW: Log search activity
    activity_logger.log_search(
        query=request.query,
        results=results,
        session_id=session_id
    )
    
    return results

@router.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    # NEW: Log feedback
    activity_logger.log_feedback(
        session_id=feedback.session_id,
        message_index=feedback.message_index,
        feedback_type=feedback.feedback
    )
    
    return {"success": True}
```

#### 3.2.6 Configuration

```yaml
# Add to config.yaml
activity_logging:
  enabled: true
  log_dir: "./logs/user_activity"
  
  # What to log
  log_queries: true
  log_results: true
  log_feedback: true
  log_clicks: true
  
  # Privacy settings (for future)
  anonymize_ip: true
  retention_days: 90
  
  # Performance
  async_logging: true  # Don't block requests
  batch_size: 10       # Write in batches
```

---

### 3.3 Basic UI Personalization

**Goal**: Improve user experience with simple preference management (no authentication required for PoC).

#### 3.3.1 Personalization Features

```python
# PoC Scope - Simple preferences
personalization_features = [
    "default_sources",      # Which sources to search by default
    "results_per_page",     # Number of results to show
    "theme",                # Light/dark mode
    "recent_searches",      # Show recent queries
]

# Post-PoC (with authentication)
# - Saved searches
# - Custom filters
# - Notification preferences
# - Language preferences
```

#### 3.3.2 Storage Strategy

```python
# PoC: Browser localStorage + session cookies
# - No database needed
# - Preferences stored client-side
# - Session ID tracked server-side for activity logging

# Data structure (localStorage):
user_preferences = {
    "session_id": "uuid-string",
    "preferences": {
        "default_sources": ["confluence", "local"],
        "results_per_page": 10,
        "theme": "light",
        "show_recent_searches": true
    },
    "recent_searches": [
        "How to configure FHIR?",
        "What is OMOP CDM?",
        "Oncology data model"
    ]
}
```

#### 3.3.3 Implementation

```python
# Modify: ui/templates/home.html
# Add preference management

<script>
// Load preferences from localStorage
function loadPreferences() {
    const prefs = JSON.parse(localStorage.getItem('user_preferences') || '{}');
    return {
        default_sources: prefs.default_sources || ['confluence', 'local'],
        results_per_page: prefs.results_per_page || 10,
        theme: prefs.theme || 'light',
        show_recent_searches: prefs.show_recent_searches !== false
    };
}

// Save preferences
function savePreferences(preferences) {
    localStorage.setItem('user_preferences', JSON.stringify(preferences));
}

// Apply preferences on page load
document.addEventListener('DOMContentLoaded', function() {
    const prefs = loadPreferences();
    
    // Apply default sources
    prefs.default_sources.forEach(source => {
        document.querySelector(`[data-source="${source}"]`).classList.add('active');
    });
    
    // Apply theme
    document.body.classList.add(`theme-${prefs.theme}`);
    
    // Show recent searches
    if (prefs.show_recent_searches) {
        displayRecentSearches();
    }
});
</script>
```

#### 3.3.4 Recent Searches

```python
# Track in localStorage
function addRecentSearch(query) {
    let recent = JSON.parse(localStorage.getItem('recent_searches') || '[]');
    
    // Add to beginning, remove duplicates, limit to 5
    recent = [query, ...recent.filter(q => q !== query)].slice(0, 5);
    
    localStorage.setItem('recent_searches', JSON.stringify(recent));
    displayRecentSearches();
}

function displayRecentSearches() {
    const recent = JSON.parse(localStorage.getItem('recent_searches') || '[]');
    const container = document.getElementById('recent-searches');
    
    if (recent.length === 0) return;
    
    container.innerHTML = '<h4>Recent Searches</h4>' + 
        recent.map(q => `
            <div class="recent-search-item" onclick="searchFromRecent('${q}')">
                ${q}
            </div>
        `).join('');
}
```

#### 3.3.5 UI Enhancements

```html
<!-- Add to home.html: Preferences Panel -->
<div class="preferences-panel">
    <h3>Preferences</h3>
    
    <!-- Default Sources -->
    <div class="preference-group">
        <label>Default Search Sources:</label>
        <div class="source-checkboxes">
            <label><input type="checkbox" value="confluence" checked> Confluence</label>
            <label><input type="checkbox" value="local" checked> Local Files</label>
            <label><input type="checkbox" value="jira"> Jira</label>
        </div>
    </div>
    
    <!-- Results per page -->
    <div class="preference-group">
        <label>Results per page:</label>
        <select id="results-per-page">
            <option value="5">5</option>
            <option value="10" selected>10</option>
            <option value="20">20</option>
        </select>
    </div>
    
    <!-- Theme -->
    <div class="preference-group">
        <label>Theme:</label>
        <select id="theme-select">
            <option value="light">Light</option>
            <option value="dark">Dark</option>
        </select>
    </div>
    
    <button onclick="saveUserPreferences()">Save Preferences</button>
</div>
```

---

### 3.4 Hierarchical Storage with Document Summaries

**Goal**: Implement lightweight hierarchical storage with document-level summaries and tags for faster retrieval and better context.

#### 3.4.1 Architecture Overview

```python
# Simple 2-level hierarchy (instead of complex 3-level)
Storage Structure:
├── Level 0: Document Summaries (NEW)
│   ├── High-level summary (2-3 sentences)
│   ├── Tags (5-10 keywords)
│   ├── Document metadata
│   └── Summary embedding
│
└── Level 1: Document Chunks (EXISTING)
    ├── Granular content (1200 tokens)
    ├── Chunk embeddings
    └── Link to parent document
```

**Benefits over flat chunking:**
- 2-3x faster for overview queries
- 30% token cost reduction
- Better document context
- Tag-based filtering
- Only 10% storage increase

**Cost Analysis:**
- Initial processing: $3 for 1,000 documents (vs $8,000 for full hierarchical)
- Maintenance: ~$20/year (vs $40k+/year for full hierarchical)
- Single LLM call per document (gpt-4o-mini)

#### 3.4.2 Document Metadata Schema

```python
# NEW: Document-level summary collection
document_summary = {
    "document_id": "doc-123",
    "title": "FHIR Configuration Guide",
    
    # Extracted by LLM
    "summary": "Comprehensive guide for configuring FHIR resources...",
    "tags": ["FHIR", "Azure", "configuration", "OAuth", "API"],
    "document_type": "technical_guide",  # guide, reference, tutorial, troubleshooting
    "target_audience": "developers",     # developer, admin, end-user
    "complexity": "intermediate",        # beginner, intermediate, advanced
    
    # Standard metadata
    "source": "confluence",
    "url": "https://confluence.company.com/...",
    "last_updated": "2024-11-15",
    "author": "John Doe",
    
    # Search optimization
    "summary_embedding": [0.023, -0.145, ...]  # 1536-dim vector
}

# EXISTING: Chunk collection (unchanged)
chunk = {
    "chunk_id": "doc-123-chunk-5",
    "document_id": "doc-123",  # Links to parent
    "content": "To configure OAuth 2.0...",
    "embedding": [0.087, -0.123, ...],
    "chunk_position": 5,
    "tags": ["FHIR", "OAuth"],  # Inherited from document
}
```

#### 3.4.3 ChromaDB Collections

```python
# Collection 1: Document Summaries (NEW)
collection_summaries = chromadb.create_collection(
    name="doc_summaries",
    metadata={"description": "Document-level summaries and tags"}
)
# Size: ~1,000 items (1 per document)
# Storage: ~5MB for 1,000 docs

# Collection 2: Document Chunks (EXISTING)
collection_chunks = chromadb.get_collection("doc_chunks")
# Size: ~10,000 items (10 per document average)
# Storage: ~50MB for 1,000 docs

# Total additional storage: Only 10% increase
```

#### 3.4.4 Implementation: Summary Extraction

```python
# New file: src/rag_ing/utils/document_processor.py

from openai import AzureOpenAI
import json

class SimpleDocumentProcessor:
    def __init__(self):
        self.llm = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
    
    def extract_summary_and_tags(self, content: str, title: str) -> dict:
        """
        Single LLM call to extract summary, tags, and metadata
        Cost: ~$0.002-0.005 per document
        """
        truncated = content[:8000]  # ~2000 tokens
        
        prompt = f"""Analyze this document and extract:

1. A 2-3 sentence summary
2. 5-10 relevant tags/keywords
3. Document type (guide, reference, tutorial, troubleshooting)
4. Target audience (developer, admin, end-user)
5. Complexity level (beginner, intermediate, advanced)

Title: {title}
Content: {truncated}

Respond in JSON:
{{
    "summary": "...",
    "tags": ["tag1", "tag2", ...],
    "document_type": "...",
    "target_audience": "...",
    "complexity": "..."
}}
"""
        
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper model
            messages=[
                {"role": "system", "content": "Extract key document information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
```

#### 3.4.5 Implementation: Storage

```python
# Modified: src/rag_ing/modules/corpus_embedding.py

class EnhancedDocumentStorage:
    def process_and_store(self, document: Document):
        # Step 1: Extract summary and tags (NEW)
        processor = SimpleDocumentProcessor()
        metadata = processor.extract_summary_and_tags(
            content=document.content,
            title=document.title
        )
        
        # Step 2: Store summary with embedding (NEW)
        summary_embedding = self.embedder.embed_query(metadata["summary"])
        self.collection_summaries.add(
            ids=[document.id],
            embeddings=[summary_embedding],
            documents=[metadata["summary"]],
            metadatas=[{
                "document_id": document.id,
                "title": document.title,
                "tags": json.dumps(metadata["tags"]),
                "document_type": metadata["document_type"],
                "target_audience": metadata["target_audience"],
                "complexity": metadata["complexity"],
                "source": document.source,
                "url": document.url,
                "last_updated": document.last_updated
            }]
        )
        
        # Step 3: Chunk and store as before (EXISTING)
        chunks = self.chunk_document(document.content)
        for idx, chunk in enumerate(chunks):
            chunk_embedding = self.embedder.embed_query(chunk)
            self.collection_chunks.add(
                ids=[f"{document.id}-chunk-{idx}"],
                embeddings=[chunk_embedding],
                documents=[chunk],
                metadatas=[{
                    "document_id": document.id,
                    "document_title": document.title,
                    "chunk_position": idx,
                    "tags": json.dumps(metadata["tags"])  # Inherit
                }]
            )
```

#### 3.4.6 Intelligent Retrieval Strategy

```python
# New file: src/rag_ing/modules/smart_retrieval.py

class SmartRetrieval:
    def classify_query_type(self, query: str) -> str:
        """Simple keyword-based classification (no LLM needed)"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in 
               ["what is", "overview", "explain", "summary"]):
            return "overview"
        
        if any(kw in query_lower for kw in 
               ["how to", "step by step", "configure", "setup"]):
            return "specific"
        
        if any(kw in query_lower for kw in 
               ["error", "fix", "troubleshoot", "issue"]):
            return "troubleshoot"
        
        return "general"
    
    def search(self, query: str, n_results: int = 5) -> dict:
        """Route query to appropriate search strategy"""
        query_type = self.classify_query_type(query)
        query_embedding = self.embedder.embed_query(query)
        
        if query_type == "overview":
            # Search summaries only (FAST - 10ms)
            return self.collection_summaries.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
        
        elif query_type in ["specific", "troubleshoot"]:
            # Two-stage: summaries → filtered chunks (25ms)
            # Find relevant documents
            summaries = self.collection_summaries.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            # Search chunks only in those documents
            doc_ids = [s['document_id'] for s in summaries['metadatas'][0]]
            return self.collection_chunks.query(
                query_embeddings=[query_embedding],
                where={"document_id": {"$in": doc_ids}},
                n_results=n_results
            )
        
        else:
            # General: parallel search both collections (30ms)
            summaries = self.collection_summaries.query(
                query_embeddings=[query_embedding], n_results=3
            )
            chunks = self.collection_chunks.query(
                query_embeddings=[query_embedding], n_results=n_results
            )
            return self.merge_results(summaries, chunks)
```

#### 3.4.7 Query Examples

**Example 1: Overview Query**
```python
Query: "What is FHIR?"
→ Type: overview
→ Strategy: Search summaries only (1,000 items)
→ Time: ~10ms
→ Token usage: ~300 tokens
→ Result: High-level explanation from document summaries
```

**Example 2: Specific Query**
```python
Query: "How to configure OAuth for FHIR?"
→ Type: specific
→ Strategy: Summaries (find 3 docs) → Chunks (filter ~30 chunks)
→ Time: ~25ms
→ Token usage: ~1,500 tokens
→ Result: Detailed steps from relevant chunks
```

**Example 3: Troubleshooting Query**
```python
Query: "Why am I getting 401 error?"
→ Type: troubleshoot
→ Strategy: Summaries → Filtered chunks + tag search
→ Time: ~25ms
→ Token usage: ~1,500 tokens
→ Result: Specific error resolution from chunks
```

#### 3.4.8 Configuration

```yaml
# Add to config.yaml

hierarchical_storage:
  enabled: true
  
  # Summary extraction
  summary_extraction:
    model: "gpt-4o-mini"  # Cheaper model for extraction
    temperature: 0.1
    max_tokens: 500
    max_content_tokens: 2000  # Truncate long docs
  
  # Collection names
  collections:
    summaries: "doc_summaries"
    chunks: "doc_chunks"
  
  # Query routing
  query_routing:
    enabled: true
    classification_method: "keyword"  # Simple, no LLM needed
    fallback_to_chunks: true  # If summary search fails
  
  # Tag extraction
  tags:
    min_tags: 5
    max_tags: 10
    extract_entities: true  # Named entity recognition
```

#### 3.4.9 Cost & Performance Comparison

| Metric | Flat Chunking | Simple Hierarchical | Full Hierarchical |
|--------|---------------|---------------------|-------------------|
| **Initial Cost** | $0 | $3 (1k docs) | $8,000 (1k docs) |
| **Maintenance/Year** | $0 | $20 | $40,000+ |
| **Storage Overhead** | 0% | +10% | +50% |
| **Overview Query Speed** | 50ms | 10ms (5x faster) | 8ms |
| **Detailed Query Speed** | 50ms | 25ms (2x faster) | 25ms |
| **Token Usage (avg)** | 2,000 | 1,200 (40% less) | 1,000 |
| **Complexity** | Low | Low | High |
| **False Negative Risk** | None | Low | Medium |
| **Maintenance Effort** | Easy | Easy | Complex |

#### 3.4.10 Migration Strategy

```python
# One-time backfill for existing documents
def backfill_summaries():
    """Add summaries to existing documents"""
    processor = SimpleDocumentProcessor()
    
    # Get all unique documents
    all_chunks = collection_chunks.get()
    doc_ids = set(c['document_id'] for c in all_chunks['metadatas'])
    
    for doc_id in doc_ids:
        # Get chunks for this document
        doc_chunks = collection_chunks.get(
            where={"document_id": doc_id}
        )
        
        # Reconstruct content
        full_content = " ".join(doc_chunks['documents'])
        title = doc_chunks['metadatas'][0]['document_title']
        
        # Extract and store summary
        metadata = processor.extract_summary_and_tags(full_content, title)
        summary_embedding = embedder.embed_query(metadata['summary'])
        
        collection_summaries.add(
            ids=[doc_id],
            embeddings=[summary_embedding],
            documents=[metadata['summary']],
            metadatas=[metadata]
        )
        
        print(f"Processed: {doc_id}")

# Run once during migration
backfill_summaries()
```

#### 3.4.11 Success Metrics

```python
# Track to validate approach
metrics = {
    "performance": {
        "overview_query_time": 10,     # ms (target: < 15ms)
        "specific_query_time": 25,     # ms (target: < 30ms)
        "general_query_time": 30       # ms (target: < 40ms)
    },
    "cost": {
        "tokens_per_overview_query": 300,   # 70% reduction
        "tokens_per_specific_query": 1500,  # 25% reduction
        "monthly_llm_cost": 30              # For 300k queries
    },
    "quality": {
        "false_negative_rate": 0.05,    # Target: < 10%
        "user_satisfaction": 0.85,      # Target: > 80%
        "summary_accuracy": 0.90        # Manual review sample
    }
}
```

#### 3.4.12 Future Evaluation Criteria

After 2-3 months of production use, evaluate whether to add section-level hierarchy:

**Add Section Level IF:**
- 60%+ of queries are overview/summary type
- Search corpus > 5,000 documents
- Average search time > 500ms
- Budget allows $1-5 per document

**Keep Simple Approach IF:**
- Mixed query types (< 60% overview)
- Corpus < 5,000 documents
- Performance acceptable (< 200ms)
- Budget constrained

---

## 4. Technical Implementation Details

### 4.1 File Structure Changes

```
RAG-ing/
├── src/rag_ing/
│   ├── utils/
│   │   ├── document_processor.py       # NEW - Summary/tag extraction
│   │   ├── duplicate_detector.py       # NEW - Duplicate detection
│   │   ├── activity_logger.py          # NEW - User activity logging
│   │   └── exceptions.py               # Existing
│   └── modules/
│       ├── corpus_embedding.py         # MODIFIED - Add summary storage
│       ├── query_retrieval.py          # MODIFIED - Add smart routing
│       └── smart_retrieval.py          # NEW - Intelligent query routing
│
├── ui/
│   ├── api/
│   │   └── routes.py                   # MODIFIED - Activity logging
│   ├── templates/
│   │   ├── home.html                   # MODIFIED - Preferences
│   │   └── preferences.html            # NEW
│   └── static/
│       ├── js/
│       │   └── preferences.js          # NEW
│       └── css/
│           └── preferences.css         # NEW
│
├── logs/
│   └── user_activity/                  # NEW
│       └── YYYY-MM-DD.jsonl
│
├── vector_store/
│   ├── chroma.sqlite3                  # Existing - ChromaDB storage
│   ├── doc_summaries/                  # NEW - Summary collection
│   ├── doc_chunks/                     # EXISTING - Chunk collection
│   └── document_hashes.db              # NEW - Duplicate tracking
│
├── config.yaml                         # MODIFIED
├── POC_REQUIREMENTS.md                 # This file
└── RAG_PROCESS_FLOW.drawio             # Process flowcharts
```

### 4.2 Dependencies to Add

```toml
# Add to pyproject.toml
dependencies = [
    # Existing dependencies...
    
    # NEW: For duplicate detection
    "fuzzywuzzy>=0.18.0",
    "python-Levenshtein>=0.21.1",
    
    # Already have these, but ensure versions:
    "fastapi>=0.121.1",
    "uvicorn>=0.38.0",
]
```

### 4.3 Configuration Updates

```yaml
# Add to config.yaml

# Duplicate Detection Configuration
duplicate_detection:
  enabled: true
  exact_match:
    enabled: true
    hash_algorithm: "sha256"
  fuzzy_match:
    enabled: true
    similarity_threshold: 0.95
  semantic_match:
    enabled: true
    embedding_similarity_threshold: 0.98
  storage:
    database_path: "./vector_store/document_hashes.db"
    cleanup_interval_days: 30

# Activity Logging Configuration
activity_logging:
  enabled: true
  log_dir: "./logs/user_activity"
  log_queries: true
  log_results: true
  log_feedback: true
  retention_days: 90
  async_logging: true

# UI Personalization Configuration
ui_personalization:
  enabled: true
  features:
    - default_sources
    - results_per_page
    - theme
    - recent_searches
  recent_searches_limit: 5

# Hierarchical Storage Configuration
hierarchical_storage:
  enabled: true
  summary_extraction:
    model: "gpt-4o-mini"
    temperature: 0.1
    max_tokens: 500
    max_content_tokens: 2000
  collections:
    summaries: "doc_summaries"
    chunks: "doc_chunks"
  query_routing:
    enabled: true
    classification_method: "keyword"
    fallback_to_chunks: true
  tags:
    min_tags: 5
    max_tags: 10
```

---

## 5. Testing & Validation

### 5.1 Duplicate Detection Tests

```python
# tests/test_duplicate_detection.py
def test_exact_duplicate():
    """Test SHA256 hash-based exact duplicate detection"""
    
def test_fuzzy_duplicate():
    """Test fuzzy matching for near-duplicates"""
    
def test_semantic_duplicate():
    """Test embedding similarity for semantic duplicates"""
    
def test_duplicate_across_sources():
    """Test duplicate detection across Confluence and local files"""
```

### 5.2 Activity Logging Tests

```python
# tests/test_activity_logging.py
def test_log_search_event():
    """Test search event logging"""
    
def test_log_feedback_event():
    """Test feedback event logging"""
    
def test_log_file_rotation():
    """Test daily log file creation"""
```

### 5.3 Performance Tests

```python
# Acceptance criteria
performance_targets = {
    "duplicate_check_time": "< 50ms per document",
    "activity_logging_overhead": "< 10ms per request",
    "preference_load_time": "< 100ms",
}
```

---

## 6. Success Metrics

### 6.1 PoC Completion Criteria

| Feature | Success Criteria |
|---------|------------------|
| **Hierarchical Storage** | ✅ All documents have summaries + tags |
| **Duplicate Detection** | ✅ 0 duplicate documents in vector store |
| **Activity Logging** | ✅ 100% of searches logged with full context |
| **User Feedback** | ✅ Feedback persisted and queryable |
| **Personalization** | ✅ User preferences saved and applied |
| **Performance** | ✅ Overview queries < 15ms, Specific queries < 30ms |
| **Cost Efficiency** | ✅ 30%+ token usage reduction |

### 6.2 Quality Metrics (for fine-tuning)

```python
# Track these from activity logs
quality_metrics = {
    "search_success_rate": "% of searches with positive feedback",
    "avg_response_time": "Average search response time",
    "source_relevance": "% of users clicking on sources",
    "repeat_searches": "% of users searching same query",
}
```

---

## 7. Implementation Timeline

### Week 1: Hierarchical Storage & Duplicate Detection
- [ ] Day 1: Implement SimpleDocumentProcessor (summary + tags extraction)
- [ ] Day 2: Create doc_summaries collection, integrate with ingestion
- [ ] Day 3: Implement DuplicateDetector class
- [ ] Day 4: Create document_hashes.db schema, integrate with corpus_embedding.py
- [ ] Day 5: Test hierarchical storage and duplicate detection

### Week 2: Smart Retrieval & Activity Logging
- [ ] Day 1: Implement SmartRetrieval with query classification
- [ ] Day 2: Test query routing (overview vs specific vs general)
- [ ] Day 3: Implement ActivityLogger class
- [ ] Day 4: Integrate activity logging with API routes
- [ ] Day 5: Add frontend tracking, test end-to-end

### Week 3: Personalization & Polish
- [ ] Day 1-2: Implement preferences UI (localStorage)
- [ ] Day 3: Add recent searches functionality
- [ ] Day 4: Performance testing and optimization
- [ ] Day 5: Documentation updates, bug fixes

### Week 4: Backfill & Production Readiness
- [ ] Day 1-2: Backfill existing documents with summaries
- [ ] Day 3: Final integration testing
- [ ] Day 4: Performance benchmarking, cost analysis
- [ ] Day 5: Production deployment, monitoring setup

---

## 8. Future Enhancements (Post-PoC)

### Phase 2: Authentication & Multi-user
- User authentication (OAuth, SSO)
- User profiles and preferences database
- Role-based access control
- Team collaboration features

### Phase 3: Advanced Features
- OCR and image processing (pytesseract, Tesseract)
- Image to embeddings (CLIP model)
- Multi-modal search
- Advanced analytics dashboard

### Phase 4: Production Hardening
- Horizontal scaling
- High availability setup
- Advanced monitoring
- Compliance and audit logs

---

## 9. References & Documentation

- **Process Flows**: `RAG_PROCESS_FLOW.drawio` - 5 comprehensive diagrams covering:
  - Main Search Flow
  - Document Ingestion + Duplicate Detection
  - Activity Logging Architecture
  - Vector Database Storage Architecture
  - Hierarchical Storage & Retrieval
- **Process Verification**: `PROCESS_VERIFICATION_CHECKLIST.md`
- **Dependencies**: See `pyproject.toml`
- **Configuration**: See `config.yaml`

---

## 10. Document Change History

### Version 0.2 (November 19, 2024)
- ✅ Added Section 3.4: Hierarchical Storage with Document Summaries
- ✅ Updated implementation timeline to 4 weeks
- ✅ Added hierarchical storage configuration
- ✅ Updated file structure with new components
- ✅ Enhanced success criteria with performance metrics
- ✅ Consolidated all design documentation into single requirements file

### Key Additions:
- Simple 2-level hierarchical architecture (summaries + chunks)
- Document processor for summary/tag extraction
- Smart query routing (overview vs specific vs general)
- Cost analysis: $3 upfront vs $8,000 for full hierarchy
- Performance targets: 10ms (overview), 25ms (specific)
- Token usage reduction: 30-40%

---

**Next Steps**: 
1. ✅ Requirements document finalized
2. ✅ Process flowcharts completed (5 diagrams)
3. ✅ Architecture design validated
4. 🚀 Begin implementation Week 1: Hierarchical Storage + Duplicate Detection
5. 📊 Track metrics for post-PoC evaluation

**Questions?** All requirements consolidated. Ready for implementation!
