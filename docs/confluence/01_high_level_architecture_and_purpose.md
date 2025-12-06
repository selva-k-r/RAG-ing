# RAG-ing: High-Level Architecture and Purpose

## Executive Summary

**RAG-ing** is a production-ready Retrieval-Augmented Generation (RAG) system that enables you to ask natural-language questions over your own documents and receive answers that are **strictly grounded in those documents**.

In the current configuration, RAG-ing focuses on:
- A dbt project stored in Azure DevOps (project configuration, manifest, macros, and seed data)
- Optional local files
- Azure OpenAI for both embeddings and generation

Answers are always drawn from retrieved context; if the information is not present, the system explains that it cannot answer and suggests better queries instead of hallucinating.

**Technology Stack (current)**
- Python 3.10+
- FastAPI (UI and API)
- ChromaDB (vector store)
- Azure OpenAI (embeddings + LLM)
- LangChain-style document objects and chunking utilities

### Key Differentiator: Strict Grounding

RAG-ing **only answers from ingested documents**. The prompt templates enforce that behavior:
1. If context is sufficient, answer using only that context.
2. If context is missing, explain that the answer cannot be found.
3. Suggest related topics and better-formulated questions to help the user.

This makes RAG-ing suitable for accuracy-critical scenarios where traceability to source documents is required.

---

## Business Use Cases

### 1. Technical Documentation Q&A
- **Problem**: Developers waste hours searching through scattered documentation
- **Solution**: RAG-ing indexes all docs and answers questions instantly
- **Example**: "How do I configure Azure DevOps connector?" → retrieves exact config example

### 2. Knowledge Base Search
- **Problem**: Support teams struggle with inconsistent answers across wikis
- **Solution**: Unified search across Confluence, SharePoint, internal docs
- **Example**: "What's our data retention policy?" → cites specific policy doc

### 3. Code Repository Intelligence
- **Problem**: Onboarding engineers can't find relevant code examples
- **Solution**: RAG-ing ingests SQL models, Python scripts, dbt docs
- **Example**: "Show me examples of incremental models" → returns actual code from repo

### 4. Compliance & Audit
- **Problem**: Manual evidence gathering for audits is time-consuming
- **Solution**: Query system with audit questions, get cited answers
- **Example**: "What encryption standards do we use?" → returns security docs with sources

---

## System Architecture

### Five-Module Design (Current Implementation)

The core of the system is implemented in `src/rag_ing/` and orchestrated by `RAGOrchestrator`.

#### Module 1: Corpus & Embedding Lifecycle
**Purpose**: Ingest documents and create searchable embeddings.

**Key responsibilities**:
- Read configuration from `config.yaml` and environment variables via `Settings`.
- Ingest from enabled sources (currently focused on Azure DevOps and optional local files).
- Perform DBT-aware processing when a dbt project is detected (using `dbt_project.yml` and `target/manifest.json`).
- Chunk documents into manageable segments.
- Generate embeddings using Azure OpenAI.
- Store embeddings and metadata in ChromaDB and record ingestion in an SQLite tracker.

#### Module 2: Query Processing & Retrieval
**Purpose**: Find and rank relevant document chunks for a user query.

**Key responsibilities**:
- Embed the incoming query with the same Azure embedding model used during ingestion.
- Perform semantic vector search in ChromaDB.
- Optionally expand the query into multiple variations using the LLM module (multi-query retrieval).
- Build a hybrid context (semantic + keyword) when configured.
- Return a set of `Document` objects and retrieval statistics.

#### Module 3: LLM Orchestration
**Purpose**: Turn retrieved context into a grounded answer.

**Key responsibilities**:
- Initialize Azure OpenAI client based on configuration.
- Load strict-grounding prompt templates from `prompts/`.
- Expose a `generate_response(query, context)` method used by the orchestrator and retrieval module.
- Apply smart truncation to avoid exceeding token limits.
- Return response text and metadata (model used, token usage if available).

#### Module 4: UI Layer
**Purpose**: Provide a simple web and API interface.

**Key responsibilities**:
- Run a FastAPI app (`ui/app.py`) exposing endpoints for search and health checks.
- Render HTML templates from `ui/templates/` and serve static assets from `ui/static/`.
- Shape responses (answer text + sources + metadata) into UI-friendly structures using `ui/enhanced_response.py`.

#### Module 5: Evaluation & Logging
**Purpose**: Track system performance and support analysis.

**Key responsibilities**:
- Record each query as a structured event in JSONL logs.
- Compute retrieval and generation metrics per query.
- Maintain system-level metrics (success counts, processing times).
- Optionally log user activity in a separate log stream for later analysis.

---

## Data Flow

### 1. Configuration and Startup

1. Environment variables (e.g. Azure keys, Azure DevOps PAT) are provided via `.env` or the host environment.
2. `config.yaml` references these variables using `${VAR}` syntax and defines:
  - Data sources (Azure DevOps repo paths, local folders)
  - Embedding and LLM provider settings (Azure OpenAI)
  - Vector store path and collection name
  - Retrieval parameters (k, hybrid weights, multi-query options)
  - UI and logging options.
3. On startup, `RAGOrchestrator` loads `Settings.from_yaml("./config.yaml")` and constructs all five modules.

Result: a single orchestrator instance that other entry points (CLI and UI) use.

### 2. Ingestion Flow (Setup / Refresh)

Simplified diagram:

```
Azure DevOps / Local Files
   ↓
 Connectors (e.g. AzureDevOpsConnector)
   ↓
 CorpusEmbeddingModule
   ↓ (optionally: DBTArtifactParser for manifest + project)
 Chunking → Embeddings → ChromaDB
                  ↓
            Ingestion Tracker DB
```

High-level steps:
1. Operator runs `python main.py --ingest`.
2. `main.py` creates `RAGOrchestrator` and calls `ingest_corpus()`.
3. Module 1 (corpus embedding) reads enabled sources from settings and:
  - Streams files from Azure DevOps that match `include_paths` and `include_file_types`.
  - For dbt projects, collects:
    - `/dbt_anthem/dbt_project.yml`
    - `/dbt_anthem/target/manifest.json`
    - Seed CSVs under `/dbt_anthem/data/`.
  - Passes these into `_process_dbt_artifacts`, which uses `DBTArtifactParser` to create synthetic model/test/macro/seed documents with metadata such as `dbt_type`, `dbt_name`, `dbt_tags`, and lineage.
4. The module then chunks all documents according to the configured strategy.
5. Each chunk is embedded using Azure OpenAI and written to ChromaDB with its metadata.
6. The ingestion tracker SQLite database is updated so that subsequent runs can be incremental.

Result: the vector store contains DBT-aware document chunks and any additional ingested files, ready to serve queries.

### 3. Query Flow (Runtime)

Simplified diagram:

```
User / Client
  ↓
FastAPI UI / API
  ↓
RAGOrchestrator
  ↓
QueryRetrievalModule → LLMOrchestrationModule
  ↓                         ↓
EvaluationLoggingModule (metrics + logs)
```

High-level steps:
1. A user sends a query via the UI or API.
2. The FastAPI route calls `RAGOrchestrator.query_documents_with_multi_query(...)` (or the basic `query_documents` method).
3. Retrieval module:
  - Embeds the query using Azure embeddings.
  - Optionally asks the LLM module to generate query variations (multi-query) to capture different phrasings.
  - Performs multiple vector searches in ChromaDB and aggregates results.
  - Builds a hybrid context (semantic + keyword) when enabled.
4. LLM orchestration module:
  - Receives the query and assembled context.
  - Calls Azure OpenAI with a strict-grounding prompt.
  - Returns a grounded answer plus any relevant metadata.
5. Evaluation and logging module:
  - Computes retrieval and generation metrics.
  - Writes a structured `QueryEvent` to JSONL logs.
6. UI layer:
  - Formats the answer and sources for display (HTML) or JSON API response.

Result: the user sees an answer along with the underlying sources and relevant metadata.

---

## Technology Stack

### Core Framework
- **Python 3.9+**: Primary language
- **FastAPI**: Web framework for UI and API
- **LangChain**: Document processing and chunking
- **Pydantic**: Configuration validation

### Vector Storage
- **ChromaDB**: Default vector database (< 50K documents)
- **FAISS**: Alternative for large-scale (> 50K documents)
- **SQLite**: Ingestion tracking and duplicate detection

### Embedding Models
- **Azure OpenAI** (Primary):
  - `text-embedding-ada-002` (1,536 dimensions)
  - `text-embedding-3-large` (3,072 dimensions)
- **HuggingFace** (Fallback):
  - `all-MiniLM-L6-v2` (384 dimensions, local)

### LLM Providers
- **Azure OpenAI** (Primary):
  - `gpt-4` (high quality)
  - `gpt-4o` (optimized speed)
- **KoboldCpp** (Fallback):
  - Local LLM for offline/air-gapped environments

### Data Sources
- **Azure DevOps**: Git repositories, wikis
- **Confluence**: Spaces, pages (planned)
- **Local Files**: .txt, .md, .pdf, .html, .docx
- **Jira**: Issues, comments (planned)

---

## Key Features

### 1. Multi-Source Ingestion
- Connect to multiple data sources simultaneously
- Incremental updates (only process changed files)
- Rich metadata preservation (authors, dates, commit history)
- Source filtering (include/exclude paths, file types)

### 2. Intelligent Chunking
- **Recursive**: Text split by paragraphs, sentences
- **Semantic**: Boundary detection at logical breaks
- **Code-Aware**: Preserves function/class structure for `.sql`, `.py`

### 3. Hybrid Retrieval
- **Semantic Search**: Vector similarity (cosine distance)
- **Keyword Search**: BM25-style term matching
- **Weighted Merge**: Configurable weight distribution
- **Reranking**: Cross-encoder for precision

### 4. Strict Document Grounding
- LLM answers ONLY from provided context
- No external knowledge injection
- Explicit "not found" responses with suggestions
- Source citations for every claim

### 5. Performance Tracking
- Retrieval metrics: hit rate, precision, recall
- Generation metrics: safety, clarity, length
- Query-level logging with unique hashes
- RAGAS integration for continuous evaluation

### 6. Configuration-Driven
- Single `config.yaml` controls all behavior
- Environment variables (`.env`) for secrets
- No code changes needed for configuration updates
- Validation on startup with helpful error messages

---

## Deployment Options

### 1. Local Development
```bash
python main.py --ingest  # One-time corpus processing
python main.py --ui      # Launch web UI
```
Access: http://localhost:8000

### 2. Docker Container
```bash
docker-compose up --build
```
Access: http://localhost:8000

### 3. Production Deployment
- Use reverse proxy (nginx, Traefik)
- Enable HTTPS with TLS certificates
- Configure authentication (Azure AD, OAuth)
- Set up monitoring (Prometheus, Grafana)
- Scale with Kubernetes or Docker Swarm

---

## Performance Characteristics

### Ingestion Speed
- **Local Files**: ~50 files/second
- **Azure DevOps**: ~10-20 files/second (with commit history)
- **Embedding**: ~16 documents/second (Azure OpenAI batch)

### Query Latency
- **Retrieval**: 100-200ms (ChromaDB semantic search)
- **Reranking**: 50ms (20 documents, CPU)
- **LLM Generation**: 1-3 seconds (Azure OpenAI)
- **Total**: ~1.5-3.5 seconds per query

### Storage Requirements
- **Embeddings**: ~6 KB per document chunk (ada-002)
- **Metadata**: ~2 KB per document
- **Logs**: ~1 KB per query event
- **Example**: 10,000 documents = ~80 MB vector store

---

## Security & Compliance

### Data Handling
- All documents stored locally (no external uploads)
- Vector embeddings are one-way (cannot reverse to original text)
- Azure OpenAI API calls encrypted via HTTPS
- No training data sent to OpenAI (zero retention policy)

### Access Control
- API key authentication for Azure services
- PAT tokens for Azure DevOps (user-scoped)
- Planned: SSO/OAuth for multi-user deployments
- Planned: Role-based access control (RBAC)

### Audit Trail
- All queries logged with timestamps
- Source document citations preserved
- User actions tracked (planned for multi-user)
- Ingestion history in SQLite database

---

## Success Metrics

### Quantitative
- **Retrieval Accuracy**: 85-95% hit rate (answer in top-5 results)
- **Query Latency**: < 3 seconds end-to-end
- **User Adoption**: Track queries per user per week
- **Coverage**: % of questions answerable from corpus

### Qualitative
- User feedback (thumbs up/down on answers)
- Time saved vs manual search
- Reduction in repeated questions
- Onboarding time improvement

---

## Roadmap

### Current (Completed)
- ✓ Multi-source ingestion (local, Azure DevOps)
- ✓ Hybrid retrieval with reranking
- ✓ Azure OpenAI integration
- ✓ FastAPI web UI
- ✓ Metrics logging

### In Progress
- ⏳ Query history UI (backend complete)
- ⏳ Enhanced response formatting

### Planned
- 📋 Confluence connector (code exists, needs testing)
- 📋 Jira connector
- 📋 User authentication (SSO/OAuth)
- 📋 Document upload interface
- 📋 Feedback mechanism
- 📋 RAGAS dashboard

---

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Azure OpenAI API access (embedding + LLM)
- Azure DevOps PAT token (optional, for repo ingestion)

### Quick Start
1. Clone repository
2. Copy `env.example` to `.env` and configure
3. Edit `config.yaml` with your data sources
4. Run: `pip install -e .`
5. Run: `python main.py --ingest`
6. Run: `python main.py --ui`
7. Open: http://localhost:8000

**Time to first query**: ~10 minutes

---

## Support & Resources

- **Documentation**: `/docs/` directory
- **Developer Guide**: `.github/copilot-instructions.md`
- **Configuration Guide**: `docs/confluence_project_config_and_env.md`
- **Architecture Details**: `docs/architecture/` directory
- **Debug Tools**: `debug_tools/` directory

---

## Conclusion

RAG-ing provides a production-ready foundation for building intelligent, document-grounded Q&A systems. Its modular architecture, strict grounding enforcement, and comprehensive metrics make it ideal for enterprise deployments where accuracy and traceability are critical.

**Next Steps**: See "Developer Manual" for detailed configuration and deployment instructions.
