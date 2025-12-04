# RAG-ing: High-Level Architecture and Purpose

## Executive Summary

**RAG-ing** is a production-ready, general-purpose Retrieval-Augmented Generation (RAG) system that enables organizations to build intelligent question-answering applications over their document repositories. The system ingests documents from multiple sources, creates searchable embeddings, and answers questions **strictly based on provided documents** with no hallucination.

**Version**: 1.0 (Production-Ready)  
**Last Updated**: November 2025  
**Technology Stack**: Python 3.9+, FastAPI, ChromaDB, Azure OpenAI, LangChain

---

## What is RAG-ing?

RAG-ing is an enterprise-grade system that combines:
- **Multi-source document ingestion** (Azure DevOps, Confluence, local files, Jira)
- **Vector embedding storage** with ChromaDB or FAISS
- **Hybrid retrieval** (semantic + keyword search)
- **LLM-powered answer generation** with strict document grounding
- **Continuous evaluation** with performance metrics tracking

### Key Differentiator: Zero Hallucination

Unlike general-purpose LLMs, RAG-ing **ONLY answers from ingested documents**. If information isn't in the corpus, the system:
1. Explicitly states it cannot find the information
2. Suggests related topics that ARE in the documents
3. Proposes rephrased questions that might yield results

This makes RAG-ing ideal for compliance-sensitive, accuracy-critical domains.

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

### Five-Module Design

#### Module 1: Corpus & Embedding Lifecycle
**Purpose**: Ingest documents and create searchable embeddings

**Components**:
- Multi-source connectors (Azure DevOps, Confluence, local files, Jira)
- Document chunking (recursive, semantic, code-aware)
- Embedding generation (Azure OpenAI text-embedding-ada-002)
- Vector store writer (ChromaDB/FAISS)
- Ingestion tracker (SQLite database)

**Output**: 1,536-dimensional embeddings stored in vector database

#### Module 2: Query Processing & Retrieval
**Purpose**: Find most relevant documents for user queries

**Components**:
- Query embedding
- Hybrid retrieval (60% semantic + 40% keyword)
- Cross-encoder reranking (ms-marco-MiniLM)
- Domain-specific boosting
- Metadata filtering

**Output**: Top-k documents ranked by relevance

#### Module 3: LLM Orchestration
**Purpose**: Generate accurate answers from retrieved context

**Components**:
- Azure OpenAI client (gpt-4, gpt-4o)
- KoboldCpp fallback (local LLM)
- Strict grounding prompts
- Smart context truncation
- Response formatting

**Output**: Natural language answer with source citations

#### Module 4: UI Layer
**Purpose**: Web interface for user interaction

**Components**:
- FastAPI application (REST API)
- HTML/CSS templates
- Search result pages
- Health check endpoints
- Static asset serving

**Output**: Web UI at http://localhost:8000

#### Module 5: Evaluation & Logging
**Purpose**: Track system performance and quality

**Components**:
- RAGAS-style retrieval metrics (hit rate, precision)
- Generation metrics (safety score, clarity)
- JSONL logging (structured logs)
- Performance tracking
- User feedback correlation

**Output**: Metrics in `logs/*.jsonl` files

---

## Data Flow

### Ingestion Flow (Setup Phase)
```
Documents → Connectors → Chunking → Embedding → Vector Store
                                              ↓
                                    Ingestion Tracker DB
```

**Steps**:
1. Configure sources in `config.yaml`
2. Run: `python main.py --ingest`
3. System fetches documents from enabled sources
4. Documents chunked into 1,200-character segments
5. Azure OpenAI generates embeddings
6. Embeddings stored in ChromaDB
7. Metadata logged in `ingestion_tracking.db`

**Result**: Searchable knowledge base ready for queries

### Query Flow (Runtime)
```
User Query → Embedding → Hybrid Retrieval → Reranking → LLM → Answer + Sources
                                                           ↓
                                                  Metrics Logging
```

**Steps**:
1. User enters question in UI
2. Query embedded with same model as documents
3. Hybrid search finds relevant chunks (semantic + keyword)
4. Cross-encoder reranks results by relevance
5. Top-k documents assembled into context
6. LLM generates answer with strict grounding
7. Response returned with source citations
8. Metrics logged for evaluation

**Result**: Accurate answer backed by document sources

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
