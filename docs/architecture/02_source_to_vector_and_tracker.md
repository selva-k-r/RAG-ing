# Source → Vector Store + Ingestion Tracker Flow

## Overview

This flow describes how documents are ingested from multiple sources, processed, and stored in the vector database with tracking in SQLite.

**Entry Point**: `CorpusEmbeddingModule.process_corpus()` in `src/rag_ing/modules/corpus_embedding.py`

---

## Configuration Inputs

### 1. config.yaml
- `data_source.sources[]` - array of source configurations
  - `type`: "local_file", "azure_devops", "confluence", "jira"
  - `enabled`: true/false
  - Source-specific settings (paths, credentials, filters)
- `chunking` - strategy, chunk_size, overlap
- `embedding_model` - provider, model name, endpoints
- `vector_store` - type, path, collection_name
- `duplicate_detection` - enabled, database_path

### 2. .env
- `AZURE_OPENAI_EMBEDDING_API_KEY`
- `AZURE_OPENAI_EMBEDDING_ENDPOINT`
- `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_REPO`
- `CONFLUENCE_BASE_URL`, `CONFLUENCE_API_TOKEN` (optional)
- `JIRA_URL`, `JIRA_TOKEN` (optional)

---

## Processing Steps

### Step 1: Initialize Ingestion Tracker

**Code**: Lines 107-112 in `corpus_embedding.py`

```python
from ..utils.ingestion_tracker_sqlite import IngestionTrackerSQLite
self._ingestion_tracker = IngestionTrackerSQLite(db_path="ingestion_tracking.db")
```

**Creates**:
- SQLite database: `ingestion_tracking.db`
- Table: `documents` with schema:
  - `source_type`, `document_id`, `content_hash`
  - `last_modified_date`, `processed_date`, `chunk_count`
  - `status` (success/failed/skipped)
  - Indexes on `source_type`, `content_hash`, `status`

**Purpose**: Track processed documents to avoid reprocessing unchanged files

### Step 2: Resolve Enabled Sources

**Code**: Lines 199-206 in `corpus_embedding.py`

```python
enabled_sources = self.data_source_config.get_enabled_sources()
for source in enabled_sources:
    source_type = source.get('type')
    # Route to appropriate connector
```

**Iterates over** `config.yaml` → `data_source.sources[]` and processes only sources where `enabled: true`

### Step 3: Per-Source Ingestion

#### 3a. Local File Loader

**Triggered when**: `source.type == "local_file"` and `source.enabled == true`

**Method**: `_ingest_local_files_enhanced()` (line 252+)

**Process**:
1. Walks directory: `source.path` (e.g., `./data/`)
2. Filters by extensions: `source.file_types` (e.g., `[".txt", ".md", ".pdf"]`)
3. Extracts text content using:
   - Plain text readers for `.txt`, `.md`
   - `pdfplumber` for `.pdf`
   - `BeautifulSoup` for `.html`
4. Creates `LangChain Document` objects with metadata:
   - `source`: file path
   - `filename`, `file_type`, `date`
5. Returns list of documents

#### 3b. Azure DevOps Connector

**Triggered when**: `source.type == "azure_devops"` and `source.enabled == true`

**Method**: `_ingest_azuredevops_enhanced()` (line 400+)

**Uses**: `AzureDevOpsConnector` from `src/rag_ing/connectors/azuredevops_connector.py`

**Process**:
1. Authenticates with PAT token: `AZURE_DEVOPS_PAT`
2. Fetches repository file tree from specified branch
3. Applies filters:
   - **include_paths**: only these directories (e.g., `["/models", "/macros"]`)
   - **exclude_paths**: skip these (e.g., `["/tests/fixtures"]`)
   - **include_file_types**: only these extensions (e.g., `[".sql", ".py"]`)
   - **exclude_file_types**: skip these (e.g., `[".gitignore"]`)
4. If `fetch_commit_history: true`:
   - Fetches last N commits for each file (`commits_per_file`)
   - Adds commit metadata (author, date, message)
5. If `enable_streaming: true`:
   - Processes files in batches (`batch_size: 50`)
6. Returns documents with rich metadata

#### 3c. Confluence Connector (Planned)

**Triggered when**: `source.type == "confluence"` and `source.enabled == true`

**Status**: Connector code exists (`src/rag_ing/connectors/confluence_connector.py`) but needs testing

**Planned Process**:
1. Authenticate with API token
2. Fetch pages by `space_keys`
3. Filter by `page_filter` keywords
4. Extract page content + metadata
5. Return documents

#### 3d. Jira Connector (Planned)

**Triggered when**: `source.type == "jira"` and `source.enabled == true`

**Status**: Not yet implemented

**Planned Process**:
1. Authenticate with Jira API token
2. Execute JQL query from `jql_filter`
3. Fetch issues matching `issue_types` and `project_keys`
4. Extract descriptions, comments, custom fields
5. Return documents

### Step 4: Unified Document List

**Code**: Line 233 in `corpus_embedding.py`

```python
all_documents.extend(docs)
```

**Result**: Single list of `LangChain Document` objects from all enabled sources

### Step 5: Duplicate Detection (Optional)

**Triggered when**: `config.duplicate_detection.enabled == true`

**Uses**: `DuplicateDetector` from `src/rag_ing/utils/duplicate_detector.py`

**Process**:
1. For each document:
   - Compute content hash (SHA256)
   - Check `document_hashes.db` SQLite table
2. Detection methods:
   - **Exact**: Hash comparison
   - **Fuzzy**: String similarity (95% threshold) via `fuzzywuzzy`
   - **Semantic**: Embedding cosine similarity (98% threshold)
3. If duplicate found:
   - Skip document
   - Increment `duplicates_skipped` counter
4. If new:
   - Add hash to database
   - Continue to chunking

### Step 6: Document Chunking

**Code**: `_chunk_documents()` method (line 159+)

**Uses**: `RecursiveCharacterTextSplitter` from LangChain

**Configuration** (from `config.yaml`):
- `chunking.strategy`: "recursive" (default) or "semantic"
- `chunking.chunk_size`: 1200 characters
- `chunking.overlap`: 100 characters
- `chunking.prepend_metadata`: true (adds source info to chunk text)

**Process**:
1. For each document:
   - Split into chunks using configured strategy
   - If `prepend_metadata: true`:
     - Prefix each chunk with "Source: {filename}\n\n"
   - Preserve original metadata on each chunk
2. Return flattened list of chunks

**Code-Specific Chunker** (if applicable):
- For `.sql`, `.py` files: uses `CodeChunker` (`src/rag_ing/utils/code_chunker.py`)
- Respects language syntax (functions, classes)
- Preserves code structure

### Step 7: Embedding Generation

**Code**: `_load_embedding_model()` method (line 175+)

**Provider Selection**:
1. **Primary**: Azure OpenAI (`embedding_model.provider == "azure_openai"`)
   - Uses `openai` Python SDK
   - Model: `text-embedding-ada-002` (or `text-embedding-3-large`)
   - Endpoint: `AZURE_OPENAI_EMBEDDING_ENDPOINT`
   - API Key: `AZURE_OPENAI_EMBEDDING_API_KEY`
2. **Fallback**: HuggingFace (`embedding_model.fallback_model`)
   - Model: `all-MiniLM-L6-v2` (default)
   - Runs locally on CPU/GPU

**Process**:
1. Initialize embedding model wrapper
2. Batch embed all chunks (batch_size: 16 for Azure)
3. Each chunk → 1536-dimensional vector (for ada-002)
4. Return list of embeddings

### Step 8: Vector Store Write

**Code**: `_setup_vector_store()` and `_store_embeddings()` methods

**Storage Backend** (from `config.vector_store.type`):
- **Chroma** (default for <50K docs)
  - Persists to: `./vector_store/`
  - Collection: `rag_documents`
  - Uses SQLite internally (`chroma.sqlite3`)
- **FAISS** (alternative for >50K docs)
  - Faster queries (<10ms)
  - Persists as binary index file

**Process**:
1. Initialize/load collection
2. For each chunk:
   - Store embedding vector
   - Store chunk text (page_content)
   - Store metadata (source, date, codes, etc.)
3. Persist to disk

**Hierarchical Storage** (optional):
- If `hierarchical_storage.enabled: true`:
  - Generates document summaries using LLM
  - Stores summaries in separate collection (`rag_documents_summaries`)
  - Enables two-level retrieval: summary first, then chunks

### Step 9: Ingestion Tracker Update

**Code**: Called after successful embedding storage

**Updates** `ingestion_tracking.db`:

```python
tracker.add_or_update_document(
    source_type="azure_devops",
    document_id="/models/staging/stg_claims.sql",
    metadata={
        "content_hash": "abc123...",
        "processed_date": "2025-11-26T10:30:00",
        "chunk_count": 5,
        "status": "success",
        "processing_time_seconds": 2.5
    }
)
```

**Enables**:
- Incremental updates (skip unchanged files on next run)
- Statistics reporting
- Error tracking

### Step 10: Statistics Reporting

**Code**: End of `process_corpus()` method

**Returns**:
```python
{
    "success": True,
    "processing_time": 45.2,
    "documents_processed": 152,
    "chunk_count": 1234,
    "sources_processed": 2,
    "duplicates_skipped": 3,
    "embedding_model": "text-embedding-ada-002",
    "vector_store_type": "chroma"
}
```

**Logged to console**:
```
CORPUS PROCESSING COMPLETED SUCCESSFULLY
Documents ingested: 152
Chunks created: 1,234
READY TO SEARCH - 1,234 chunks available for queries
```

---

## Data Flow Summary

| Step | Input | Process | Output |
|------|-------|---------|--------|
| 1 | `config.yaml`, `.env` | Load settings | Configuration objects |
| 2 | Config | Initialize tracker DB | `ingestion_tracking.db` |
| 3 | Enabled sources | Resolve source list | List of sources to process |
| 4 | Each source | Fetch documents via connectors | Raw documents |
| 5 | Raw documents | Check duplicates | Filtered documents |
| 6 | Filtered documents | Split into chunks | Document chunks |
| 7 | Chunks | Generate embeddings | Vector embeddings |
| 8 | Embeddings + chunks | Write to vector store | `./vector_store/` |
| 9 | Processing metadata | Update tracker | `ingestion_tracking.db` |
| 10 | All stats | Log and return | Ingestion summary |

---

## Key Files

- **Main module**: `src/rag_ing/modules/corpus_embedding.py`
- **Tracker**: `src/rag_ing/utils/ingestion_tracker_sqlite.py`
- **Duplicate detection**: `src/rag_ing/utils/duplicate_detector.py`
- **Connectors**:
  - `src/rag_ing/connectors/azuredevops_connector.py`
  - `src/rag_ing/connectors/confluence_connector.py`
- **Databases**:
  - `ingestion_tracking.db` (SQLite)
  - `vector_store/chroma.sqlite3` (ChromaDB)
  - `vector_store/document_hashes.db` (duplicate detection)
