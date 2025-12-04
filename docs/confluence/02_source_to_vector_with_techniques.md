# Source-to-Vector Storage: Ingestion Pipeline with Techniques and Logging

## Overview

This document details the complete ingestion pipeline that transforms raw documents from multiple sources into searchable vector embeddings, with comprehensive tracking and logging.

**Entry Point**: `python main.py --ingest`  
**Main Module**: `src/rag_ing/modules/corpus_embedding.py`  
**Processing Time**: ~45 seconds for 150 documents

---

## Architecture Diagram (Text Representation)

```
Configuration (config.yaml + .env)
          ↓
    Source Resolver
          ↓
    ┌─────┴─────┬──────────┬──────────┐
    ↓           ↓          ↓          ↓
Local Files  Azure DevOps  Confluence  Jira
    └─────┬─────┴──────────┴──────────┘
          ↓
    Unified Document List
          ↓
    Duplicate Detector (document_hashes.db)
          ↓
    Document Chunker
          ↓
    Embedding Generator
          ↓
    Vector Store Writer (ChromaDB)
          ↓
    Ingestion Tracker (ingestion_tracking.db)
          ↓
    Statistics Report
```

---

## Phase 1: Configuration & Initialization

### Configuration Loading

**File**: `config.yaml`

**Key Sections**:
```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true
      path: "./data"
      file_types: [".txt", ".md", ".pdf", ".html"]
      
    - type: "azure_devops"
      enabled: true
      organization: "${AZURE_DEVOPS_ORG}"
      project: "${AZURE_DEVOPS_PROJECT}"
      repository: "${AZURE_DEVOPS_REPO}"
      branch: "main"
      include_paths: ["/models", "/macros"]
      exclude_paths: ["/tests/fixtures"]
      include_file_types: [".sql", ".yml", ".py"]
      exclude_file_types: [".gitignore", ".md"]
      fetch_commit_history: true
      commits_per_file: 10
      batch_size: 50
      enable_streaming: true

chunking:
  strategy: "recursive"
  chunk_size: 1200
  overlap: 100
  prepend_metadata: true

embedding_model:
  provider: "azure_openai"
  model: "text-embedding-ada-002"
  endpoint: "${AZURE_OPENAI_EMBEDDING_ENDPOINT}"
  api_key: "${AZURE_OPENAI_EMBEDDING_API_KEY}"
  fallback_model: "all-MiniLM-L6-v2"

vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "rag_documents"

duplicate_detection:
  enabled: true
  database_path: "./vector_store/document_hashes.db"
  method: "exact"  # Options: exact, fuzzy, semantic
```

### Environment Variables

**File**: `.env`

**Required Variables**:
```bash
# Azure OpenAI (Embedding)
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_API_KEY=your_embedding_key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure DevOps (Optional)
AZURE_DEVOPS_ORG=your-org
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_REPO=your-repo
AZURE_DEVOPS_PAT=your_personal_access_token

# Confluence (Optional, Planned)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_API_TOKEN=your_api_token

# Jira (Optional, Planned)
JIRA_URL=https://your-domain.atlassian.net
JIRA_TOKEN=your_jira_token
```

### Database Initialization

**Ingestion Tracker**: `ingestion_tracking.db`

**Schema**:
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,           -- 'local_file', 'azure_devops', etc.
    document_id TEXT NOT NULL,           -- file path or unique identifier
    content_hash TEXT NOT NULL,          -- SHA256 hash for change detection
    last_modified_date TEXT,             -- source's last modified timestamp
    processed_date TEXT NOT NULL,        -- when we processed it
    chunk_count INTEGER,                 -- number of chunks created
    status TEXT,                         -- 'success', 'failed', 'skipped'
    processing_time_seconds REAL,        -- how long it took
    error_message TEXT,                  -- if failed, why
    metadata TEXT,                       -- JSON blob for source-specific data
    UNIQUE(source_type, document_id)
);

CREATE INDEX idx_source_type ON documents(source_type);
CREATE INDEX idx_content_hash ON documents(content_hash);
CREATE INDEX idx_status ON documents(status);
CREATE INDEX idx_processed_date ON documents(processed_date);
```

**Purpose**:
- Track which documents have been processed
- Enable incremental updates (skip unchanged files)
- Store processing history and statistics
- Support error recovery and debugging

---

## Phase 2: Multi-Source Document Ingestion

### Source Resolution

**Code**: `corpus_embedding.py` lines 199-206

**Process**:
```python
enabled_sources = self.data_source_config.get_enabled_sources()
# Returns only sources where enabled: true

for source in enabled_sources:
    source_type = source.get('type')
    # Route to appropriate connector
```

### Connector 1: Local File Loader

**Status**: ✓ Completed

**Method**: `_ingest_local_files_enhanced()`

**Supported Formats**:
- **Plain Text**: `.txt`, `.md`, `.csv`
- **PDF**: Via `pdfplumber` library (text extraction, table detection)
- **HTML**: Via `BeautifulSoup` (main content extraction, script/style removal)
- **Word Documents**: `.docx` via `python-docx` (planned)

**Process**:
1. Walk directory tree from `source.path`
2. Filter files by `file_types` list
3. For each file:
   - Read content based on file type
   - Extract text (handling encoding issues)
   - Create LangChain `Document` object
   - Attach metadata:
     - `source`: "local_file"
     - `filename`: "sample.txt"
     - `file_type`: ".txt"
     - `file_size`: 12345 (bytes)
     - `last_modified`: "2025-11-26T10:30:00"
     - `path`: "./data/sample.txt"

**Example Output**:
```python
Document(
    page_content="This is the content of the file...",
    metadata={
        "source": "local_file",
        "filename": "sample.txt",
        "file_type": ".txt",
        "file_size": 1234,
        "last_modified": "2025-11-26T10:30:00",
        "path": "./data/sample.txt"
    }
)
```

### Connector 2: Azure DevOps

**Status**: ✓ Completed

**Module**: `src/rag_ing/connectors/azuredevops_connector.py`

**Method**: `_ingest_azuredevops_enhanced()`

**Authentication**:
- PAT (Personal Access Token) from `AZURE_DEVOPS_PAT`
- Scopes required: `Code (Read)`, `Project and Team (Read)`

**Process**:
1. **Authenticate**: Create session with PAT token
2. **Fetch File Tree**: GET `/repos/{repo}/items?recursionLevel=Full&branch={branch}`
3. **Apply Include Filters**:
   - If `include_paths` specified: only process files under those paths
   - If `include_file_types` specified: only process matching extensions
4. **Apply Exclude Filters**:
   - Skip files matching `exclude_paths`
   - Skip files matching `exclude_file_types`
5. **Download Content**: GET `/repos/{repo}/items?path={file_path}&branch={branch}`
6. **Fetch Commit History** (if `fetch_commit_history: true`):
   - GET `/repos/{repo}/commits?itemPath={file_path}&$top={commits_per_file}`
   - Extract: author, date, message, commit_id
   - Attach as metadata array
7. **Batch Processing** (if `enable_streaming: true`):
   - Process files in batches of `batch_size` (default 50)
   - Log progress: "Fetched batch 1/10: 50 files"

**Metadata Example**:
```python
{
    "source": "azure_devops",
    "filename": "stg_claims.sql",
    "file_type": ".sql",
    "repository": "analytics-dbt",
    "branch": "main",
    "path": "/models/staging/stg_claims.sql",
    "commit_history": [
        {
            "commit_id": "abc123",
            "author": "john.doe@company.com",
            "date": "2025-11-20",
            "message": "Add claim amount validation"
        },
        # ... up to 10 commits
    ]
}
```

**Performance**:
- ~10-20 files/second with commit history
- ~40-50 files/second without commit history
- Bottleneck: Azure DevOps API rate limits (200 requests/minute)

### Connector 3: Confluence

**Status**: 📋 Planned (code exists, needs testing)

**Module**: `src/rag_ing/connectors/confluence_connector.py`

**Planned Features**:
- Fetch pages by space keys
- Filter by page title keywords
- Extract page content (convert from Confluence storage format)
- Preserve page hierarchy (parent/child relationships)
- Attach labels and metadata

**Planned Configuration**:
```yaml
- type: "confluence"
  enabled: true
  base_url: "${CONFLUENCE_BASE_URL}"
  api_token: "${CONFLUENCE_API_TOKEN}"
  space_keys: ["ENG", "DOCS"]
  page_filter: ["Architecture", "API"]
  max_pages: 100
```

### Connector 4: Jira

**Status**: 📋 Planned (not implemented)

**Planned Features**:
- Execute JQL query
- Fetch issues by project and type
- Extract: description, comments, custom fields
- Attach issue metadata (status, priority, labels)

**Planned Configuration**:
```yaml
- type: "jira"
  enabled: true
  url: "${JIRA_URL}"
  api_token: "${JIRA_TOKEN}"
  jql_filter: "project = DATA AND type = Story"
  project_keys: ["DATA", "ENG"]
  issue_types: ["Story", "Bug", "Task"]
  max_issues: 500
```

---

## Phase 3: Duplicate Detection

**Status**: ✓ Completed (optional feature)

**Enabled When**: `duplicate_detection.enabled: true`

**Database**: `document_hashes.db` (SQLite)

**Module**: `src/rag_ing/utils/duplicate_detector.py`

### Detection Methods

#### 1. Exact Hash Matching (Default)
**Algorithm**: SHA256 content hash

**Process**:
1. Compute hash of document content
2. Query database: `SELECT * FROM hashes WHERE hash = ?`
3. If found: skip document (duplicate)
4. If not found: add to database and continue

**Pros**: Fast (O(1) lookup), deterministic  
**Cons**: Misses near-duplicates (even 1 character change = different hash)

#### 2. Fuzzy String Matching
**Algorithm**: Levenshtein distance via `fuzzywuzzy` library

**Process**:
1. For each existing document:
   - Compute string similarity score (0-100)
2. If similarity > 95%: mark as duplicate
3. Otherwise: add as new document

**Pros**: Catches near-duplicates (minor edits)  
**Cons**: Slow (O(n) comparison), high CPU usage

#### 3. Semantic Similarity
**Algorithm**: Cosine similarity of embeddings

**Process**:
1. Generate embedding for new document
2. Compare with all existing embeddings
3. If cosine similarity > 0.98: mark as duplicate
4. Otherwise: add as new document

**Pros**: Detects semantic duplicates (rewrites, paraphrases)  
**Cons**: Requires embedding (expensive), slower than hash

### Statistics

**Logged**:
```
Duplicate Detection Results:
- Documents processed: 152
- Duplicates skipped: 3
- New documents: 149
- Detection method: exact
```

---

## Phase 4: Document Chunking

**Module**: `corpus_embedding.py` method `_chunk_documents()`

**Purpose**: Split long documents into smaller, semantically coherent chunks for better retrieval

### Chunking Strategies

#### Strategy 1: Recursive Character Splitter (Default)

**Configuration**:
```yaml
chunking:
  strategy: "recursive"
  chunk_size: 1200        # characters
  overlap: 100            # characters of overlap between chunks
  prepend_metadata: true  # add "Source: {filename}" to each chunk
```

**Algorithm** (LangChain `RecursiveCharacterTextSplitter`):
1. Try to split on paragraphs (`\n\n`)
2. If chunk still too large, split on sentences (`. `)
3. If still too large, split on words (` `)
4. If still too large, split on characters

**Example**:
```
Document (2,500 chars)
    ↓
Chunk 1 (1,200 chars): "Source: file.txt\n\n{content 0-1200}"
Chunk 2 (1,200 chars): "{content 1100-2300}"  # 100 char overlap
Chunk 3 (400 chars): "{content 2200-2500}"
```

**Pros**: Preserves natural text boundaries  
**Cons**: May split mid-sentence for very long sentences

#### Strategy 2: Semantic Chunking

**Configuration**:
```yaml
chunking:
  strategy: "semantic"
  chunk_size: 1200
  overlap: 0  # semantic boundaries don't need overlap
```

**Algorithm**:
1. Detect semantic boundaries:
   - Markdown headers (`## `, `### `)
   - Section breaks (`---`, `===`)
   - Paragraph breaks (`\n\n`)
2. Split at boundaries while respecting `chunk_size`
3. Each chunk = complete semantic unit

**Pros**: Better semantic coherence  
**Cons**: Variable chunk sizes, more complex

#### Strategy 3: Code-Specific Chunking

**Auto-Enabled For**: `.sql`, `.py`, `.js`, `.java` files

**Module**: `src/rag_ing/utils/code_chunker.py`

**Algorithm**:
1. Parse code into AST (Abstract Syntax Tree)
2. Extract functions, classes, models
3. Keep each function/class as a single chunk (if < chunk_size)
4. Preserve docstrings and comments with code

**Example** (SQL):
```sql
-- Chunk 1: Model definition
{{ config(materialized='incremental') }}

SELECT ...

-- Chunk 2: Next model
{{ config(materialized='view') }}
```

**Pros**: Preserves code structure, better for code search  
**Cons**: Only works for supported languages

### Metadata Prepending

**When Enabled** (`prepend_metadata: true`):

**Original Chunk**:
```
This is the content of the chunk explaining dbt models...
```

**With Metadata**:
```
Source: /models/staging/stg_claims.sql
Repository: analytics-dbt
Last Modified: 2025-11-20

This is the content of the chunk explaining dbt models...
```

**Purpose**: Provides context to LLM during retrieval, improves answer quality

---

## Phase 5: Embedding Generation

**Module**: `corpus_embedding.py` method `_load_embedding_model()`

### Primary Provider: Azure OpenAI

**Configuration**:
```yaml
embedding_model:
  provider: "azure_openai"
  model: "text-embedding-ada-002"
  endpoint: "${AZURE_OPENAI_EMBEDDING_ENDPOINT}"
  api_key: "${AZURE_OPENAI_EMBEDDING_API_KEY}"
  batch_size: 16
```

**Model**: `text-embedding-ada-002`
- **Dimensions**: 1,536
- **Max Input**: 8,191 tokens (~32,000 characters)
- **Cost**: $0.0001 per 1K tokens
- **Latency**: ~50ms per batch of 16

**Process**:
1. Initialize OpenAI client with Azure endpoint
2. Batch chunks into groups of 16
3. For each batch:
   - Call `client.embeddings.create(input=chunks, model="text-embedding-ada-002")`
   - Receive 1,536-dimensional vectors
4. Flatten batches into single list of embeddings

**Error Handling**:
- Retry 3 times with exponential backoff (1s, 2s, 4s)
- Skip chunks exceeding token limit (log warning)
- Fallback to HuggingFace on persistent failures

### Fallback Provider: HuggingFace

**Configuration**:
```yaml
embedding_model:
  fallback_model: "all-MiniLM-L6-v2"
  device: "cpu"  # or "cuda" for GPU
```

**Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Max Input**: 512 tokens (~2,000 characters)
- **Cost**: Free (local execution)
- **Latency**: ~200ms per batch of 16 (CPU)

**Use Cases**:
- Azure OpenAI unavailable
- Air-gapped environments
- Cost optimization for development/testing

**Note**: HuggingFace embeddings are **NOT compatible** with Azure OpenAI embeddings (different dimensions). Must re-embed entire corpus if switching.

---

## Phase 6: Vector Store Write

**Module**: `corpus_embedding.py` methods `_setup_vector_store()` and `_store_embeddings()`

### Vector Store: ChromaDB (Default)

**Configuration**:
```yaml
vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "rag_documents"
```

**Storage Structure**:
```
./vector_store/
├── chroma.sqlite3              # Metadata database
├── 20da0efe-2932-4ba1-a357-90fe4a36c900/  # Collection ID
│   ├── data_level0.bin         # Vector index
│   └── header.bin              # Index metadata
└── summaries/                  # Hierarchical storage (optional)
    └── chroma.sqlite3
```

**Process**:
1. Initialize/load collection: `rag_documents`
2. For each chunk:
   - Generate unique ID (hash of content + metadata)
   - Store embedding vector (1,536 floats)
   - Store chunk text (`page_content`)
   - Store metadata dict (source, filename, date, etc.)
3. Persist to disk (automatic in ChromaDB)

**Collection Schema**:
- **ID**: `{source}_{document_id}_{chunk_index}`
- **Vector**: `[0.123, -0.456, ...]` (1,536 dimensions)
- **Text**: "Source: file.txt\n\nThis is the chunk content..."
- **Metadata**: `{"source": "local_file", "filename": "...", ...}`

**Performance**:
- Write speed: ~500 chunks/second
- Storage: ~6 KB per chunk (embedding + metadata)
- Query latency: 100-200ms for top-k=20

### Alternative: FAISS

**Configuration**:
```yaml
vector_store:
  type: "faiss"
  path: "./vector_store/faiss_index.bin"
```

**When to Use**:
- Large corpus (> 50K documents)
- High query volume (> 100 QPS)
- Need sub-10ms query latency

**Pros**: Faster queries, better scaling  
**Cons**: More complex, no built-in metadata storage (need separate DB)

---

## Phase 7: Ingestion Tracker Update

**Database**: `ingestion_tracking.db`

**Method**: `IngestionTrackerSQLite.add_or_update_document()`

**Process**:
1. After successfully storing embeddings for a document:
   - Compute content hash (SHA256)
   - Record processing time
   - Count chunks created
2. Insert/update row in `documents` table:

```python
tracker.add_or_update_document(
    source_type="azure_devops",
    document_id="/models/staging/stg_claims.sql",
    metadata={
        "content_hash": "a3f5b2c...",
        "processed_date": "2025-11-26T10:30:15",
        "chunk_count": 5,
        "status": "success",
        "processing_time_seconds": 2.5,
        "repository": "analytics-dbt",
        "branch": "main"
    }
)
```

**Use Cases**:

### Incremental Updates
On subsequent runs, system checks tracker:
```python
existing = tracker.get_document(source_type="azure_devops", 
                                 document_id="/models/staging/stg_claims.sql")
if existing and existing["content_hash"] == new_hash:
    # Skip unchanged file
    pass
else:
    # Re-process changed file
    pass
```

### Statistics Reporting
```python
stats = tracker.get_statistics()
# Returns:
# {
#   "total_documents": 152,
#   "by_source": {
#     "local_file": 45,
#     "azure_devops": 107
#   },
#   "total_chunks": 1234,
#   "last_ingestion": "2025-11-26T10:30:00"
# }
```

### Error Analysis
```python
failed = tracker.get_failed_documents()
# Returns documents where status='failed' with error messages
```

---

## Phase 8: Hierarchical Storage (Optional)

**Status**: ✓ Completed (advanced feature)

**Enabled When**: `hierarchical_storage.enabled: true`

**Purpose**: Two-level retrieval for long documents

**Configuration**:
```yaml
hierarchical_storage:
  enabled: true
  summary_collection: "rag_documents_summaries"
  summary_generation:
    provider: "azure_openai"
    model: "gpt-4"
    max_summary_length: 500
```

**Process**:
1. For each document (before chunking):
   - Generate summary using LLM
   - Store summary in separate collection
   - Link summary to original document chunks
2. During retrieval:
   - First, search summaries (coarse-grained)
   - Then, search chunks within matched documents (fine-grained)

**Benefits**:
- Better retrieval for very long documents (> 10 pages)
- Faster queries (fewer vectors to search)
- Hierarchical context (document overview + specific chunks)

**Cost**: Additional LLM calls for summary generation (~$0.03 per 1K tokens)

---

## Phase 9: Statistics & Logging

### Console Output

**During Processing**:
```
[OK] Corpus embedding process started
[OK] Enabled sources: local_file, azure_devops
[OK] Fetching from local_file: ./data
[OK] Found 45 files matching filters
[OK] Fetching from azure_devops: analytics-dbt/main
[OK] Fetched batch 1/3: 50 files
[OK] Fetched batch 2/3: 50 files
[OK] Fetched batch 3/3: 7 files
[OK] Total documents fetched: 152
[OK] Duplicate detection: 3 duplicates skipped
[OK] Chunking 149 documents...
[OK] Created 1,234 chunks
[OK] Generating embeddings (batch size: 16)...
[OK] Embedded 1,234 chunks in 45.2s
[OK] Storing in ChromaDB: rag_documents
[OK] Updating ingestion tracker...
[OK] CORPUS PROCESSING COMPLETED SUCCESSFULLY

Ingestion Summary:
==================
Processing Time:     45.2 seconds
Documents Processed: 152
Duplicates Skipped:  3
Chunks Created:      1,234
Embedding Model:     text-embedding-ada-002
Vector Store:        chroma (./vector_store)

By Source:
- local_file:     45 documents (356 chunks)
- azure_devops:   107 documents (878 chunks)

READY TO SEARCH - 1,234 chunks available for queries
```

### Metrics Logged

**File**: `logs/ingestion_metrics.jsonl` (optional)

**Format**:
```json
{
  "timestamp": "2025-11-26T10:30:00",
  "event": "ingestion_complete",
  "processing_time": 45.2,
  "documents_processed": 152,
  "duplicates_skipped": 3,
  "chunk_count": 1234,
  "sources": {
    "local_file": {"documents": 45, "chunks": 356},
    "azure_devops": {"documents": 107, "chunks": 878}
  },
  "embedding_model": "text-embedding-ada-002",
  "vector_store": "chroma"
}
```

---

## Troubleshooting

### Common Issues

#### 1. Azure DevOps Authentication Failure
**Error**: `HTTP 401 Unauthorized`

**Solution**:
- Verify PAT token has correct scopes: `Code (Read)`, `Project and Team (Read)`
- Check token expiration date
- Ensure environment variable is set: `echo $AZURE_DEVOPS_PAT`

#### 2. Embedding API Rate Limit
**Error**: `HTTP 429 Too Many Requests`

**Solution**:
- Reduce `batch_size` in config (e.g., 8 instead of 16)
- Add retry logic with exponential backoff (already implemented)
- Upgrade Azure OpenAI quota

#### 3. ChromaDB Lock Error
**Error**: `database is locked`

**Solution**:
- Ensure no other process is accessing `./vector_store/`
- Delete lock file: `rm ./vector_store/chroma.sqlite3-wal`
- Restart ingestion

#### 4. Out of Memory
**Error**: `MemoryError` during embedding

**Solution**:
- Process in smaller batches (reduce `batch_size`)
- Use streaming mode: `enable_streaming: true`
- Increase system RAM or use disk-based vector store (FAISS)

---

## Performance Optimization

### Tips for Large Corpuses

1. **Enable Streaming**: Process files in batches
   ```yaml
   enable_streaming: true
   batch_size: 50
   ```

2. **Optimize Chunk Size**: Larger chunks = fewer embeddings
   ```yaml
   chunk_size: 1500  # instead of 1200
   ```

3. **Skip Commit History**: Faster Azure DevOps fetching
   ```yaml
   fetch_commit_history: false
   ```

4. **Use Exact Duplicate Detection**: Fastest method
   ```yaml
   duplicate_detection:
     method: "exact"  # not "fuzzy" or "semantic"
   ```

5. **Parallel Processing**: Multiple workers (planned feature)

---

## Summary

The ingestion pipeline transforms raw documents into searchable embeddings through:
1. **Multi-source connectors** (local, Azure DevOps, Confluence, Jira)
2. **Duplicate detection** (exact hash, fuzzy, semantic)
3. **Intelligent chunking** (recursive, semantic, code-aware)
4. **Azure OpenAI embeddings** (1,536 dimensions)
5. **ChromaDB storage** (vector + metadata)
6. **SQLite tracking** (incremental updates, statistics)

**Result**: Production-ready knowledge base searchable in <200ms with comprehensive audit trail.
