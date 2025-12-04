# RAG-ing High-Level Architecture

## System Components

### 1. Entry Point
- **User** → interacts via web browser
- **FastAPI UI** (`ui/app.py`)
  - HTTP API endpoints
  - HTML template rendering
  - Static assets (CSS, JS)
  - Routes: `/api/search`, `/api/health`, `/` (home page)

### 2. Core Orchestrator
- **RAGOrchestrator** (`src/rag_ing/orchestrator.py`)
  - Loads configuration from `config.yaml`
  - Initializes all 5 modules
  - Coordinates query → retrieval → LLM → logging flow
  - Methods:
    - `ingest_corpus()` - triggers document ingestion
    - `query_documents(query, user_context)` - main query pipeline
    - `get_system_status()` - health check

### 3. Five Core Modules

#### Module 1: Corpus & Embedding Lifecycle
- **CorpusEmbeddingModule** (`src/rag_ing/modules/corpus_embedding.py`)
  - Multi-source document ingestion (local files, Azure DevOps, Confluence, Jira)
  - Document chunking (recursive or semantic)
  - Embedding generation (Azure OpenAI / HuggingFace)
  - Writes to vector store (Chroma/FAISS)
  - Tracks ingestion in SQLite (`ingestion_tracking.db`)

#### Module 2: Query Processing & Retrieval
- **QueryRetrievalModule** (`src/rag_ing/modules/query_retrieval.py`)
  - Embeds user query
  - Hybrid retrieval: semantic (vector similarity) + keyword (BM25-style)
  - Weighted merge with configurable weights
  - Optional cross-encoder reranking
  - Returns top-k documents

#### Module 3: LLM Orchestration
- **LLMOrchestrationModule** (`src/rag_ing/modules/llm_orchestration.py`)
  - Azure OpenAI client (primary)
  - KoboldCpp client (fallback)
  - Loads prompt template from `prompts/general.txt`
  - Enforces strict context grounding
  - Smart truncation for token limits

#### Module 4: UI Layer Module
- **UILayerModule** (`src/rag_ing/modules/ui_layer.py`)
  - Response formatting
  - Session history hooks (via ActivityLogger)
  - Metadata display

#### Module 5: Evaluation & Logging
- **EvaluationLoggingModule** (`src/rag_ing/modules/evaluation_logging.py`)
  - Calculates retrieval metrics (precision, hit rate)
  - Calculates generation metrics (safety score, clarity)
  - Writes JSONL logs: `evaluation.jsonl`, `retrieval_metrics.jsonl`, `generation_metrics.jsonl`
  - RAGAS integration for continuous evaluation

### 4. Data Stores

#### Vector Store
- **ChromaDB** (default) or **FAISS**
- Location: `./vector_store/`
- Collection: `rag_documents`
- Stores embeddings + metadata for semantic search

#### Ingestion Tracker
- **SQLite database**: `ingestion_tracking.db`
- Table: `documents` with columns:
  - `source_type`, `document_id`, `content_hash`
  - `processed_date`, `chunk_count`, `status`
  - Prevents duplicate processing
  - Supports incremental updates

#### Logs Directory
- **`./logs/`**
  - `evaluation.jsonl` - complete query events
  - `retrieval_metrics.jsonl` - retrieval performance
  - `generation_metrics.jsonl` - LLM response quality

---

## High-Level Flow

### Ingestion Flow (one-time or incremental)
1. CLI: `python main.py --ingest`
2. Orchestrator → `corpus_embedding.process_corpus()`
3. Module 1:
   - Fetches documents from enabled sources
   - Checks `ingestion_tracking.db` for duplicates
   - Chunks new/changed documents
   - Generates embeddings
   - Writes to Chroma
   - Updates tracker database
4. Returns stats (document count, chunk count, processing time)

### Query Flow (runtime)
1. User enters query in UI
2. FastAPI route `/api/search` receives request
3. Orchestrator → `query_documents(query)`
4. Module 2:
   - Embeds query
   - Hybrid retrieval from Chroma
   - Reranks results
   - Returns top-k documents
5. Module 3:
   - Assembles context from retrieved docs
   - Calls Azure OpenAI with strict grounding prompt
   - Returns generated answer
6. Module 5:
   - Calculates metrics
   - Logs query event to JSONL
7. Response returned to UI with answer + sources

---

## Configuration

All behavior driven by:
- **`config.yaml`** - data sources, chunking, retrieval, LLM settings
- **`.env`** - secrets (Azure keys, PAT tokens)

See `docs/confluence_project_config_and_env.md` for details.
