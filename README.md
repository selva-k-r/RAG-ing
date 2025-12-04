# RAG-ing: General-Purpose RAG System

A production-ready Retrieval-Augmented Generation (RAG) system for intelligent document search and question answering. Strictly grounds answers in your documents with no hallucination. Connect to Azure DevOps, Confluence, and local files with Azure OpenAI integration.

## ✨ Key Features

### Strict Document Grounding
- **Zero Hallucination**: Answers ONLY from provided documents
- **Helpful Guidance**: Suggests question rephrasing when information unavailable
- **Source Attribution**: Clear citation of document sources

### Multi-Source Integration
- **Azure DevOps**: Query your codebase with commit history tracking
  - Path and file type filtering
  - Batch processing (configurable batch size)
  - Incremental updates (track changes, skip unchanged files)
  - Last N commits per file
  - **DBT Integration** (beta): Lineage graphs, SQL extraction from artifacts
- **Confluence**: Wiki pages and documentation (planned)
- **Local Files**: PDF, Markdown, TXT, HTML
- **Jira**: Tickets and requirements (planned)

### Production-Ready
- **FastAPI Web Interface**: Modern REST API with SSE progress tracking
- **Hierarchical Storage**: Two-tier retrieval (summaries → detailed chunks)
  - LLM-generated rich summaries with business context, keywords, topics
  - Type-specific summarization (SQL, Python, YAML, PDF)
  - Smart routing based on relevance scores
- **Hybrid Search**: Semantic vector search + keyword matching
- **Azure OpenAI Integration**: GPT-4/GPT-4o with fallback providers
- **Persistent Storage**: ChromaDB vector database with dual collections
- **Structured Logging**: JSON logs for analysis and monitoring

### Code Quality
- **ASCII-Safe**: No emoji encoding issues (Windows compatible)
- **Domain-Agnostic**: Works for any use case (tech, business, finance, etc.)
- **Professional Standards**: Clear error messages with system codes

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Azure OpenAI API key
- Git (for Azure DevOps integration)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/RAG-ing.git
cd RAG-ing

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -e .
```

### Configuration

**1. Create `.env` file:**

```bash
# Azure OpenAI (Required)
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure OpenAI Embedding (Required)
AZURE_OPENAI_EMBEDDING_API_KEY=your_embedding_key
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-endpoint.openai.azure.com/

# Azure DevOps (Optional - for code intelligence)
AZURE_DEVOPS_ORG=your_organization
AZURE_DEVOPS_PROJECT=your_project
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_DEVOPS_REPO=your_repository

# Confluence (Optional - planned feature)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_TOKEN=your_token
CONFLUENCE_SPACE_KEY=YOUR_SPACE
```

**2. Configure `config.yaml`:**

See [Configuration](#configuration) section below for detailed settings.

### Usage

```bash
# Step 1: Index your documents
python main.py --ingest

# Step 2: Launch web interface
python main.py --ui

# Step 3: Access at http://localhost:8000
```

**Alternative commands:**

```bash
# Single query via CLI
python main.py --query "What SQL models exist in the repository?"

# System health check
python main.py --status

# Debug mode
python main.py --ingest --debug
```

---

## 📁 Data Sources

### Azure DevOps (Primary Feature)

**Query your codebase with advanced intelligence:**

#### What You Can Ask:
- "How is authentication implemented?"
- "What SQL models are in the dbt-anthem repository?"
- "When was the avoidable admissions logic last changed?"
- "What files handle data transformation?"

#### Features:
- **Commit History**: Tracks last N commits for each file (default: 10)
- **Smart Filtering**: Include/exclude paths and file types
- **Batch Processing**: Configurable batch size (default: 50 files)
- **Incremental Updates**: Only processes changed files
- **Change Detection**: Content hash-based tracking

#### Setup:

**Generate PAT Token:**
1. Go to `https://dev.azure.com/{org}/_usersSettings/tokens`
2. Create new token with **Code (Read)** scope
3. Add to `.env` file

**Configure in `config.yaml`:**

```yaml
data_source:
  sources:
    - type: "azure_devops"
      enabled: true
      azure_devops:
        organization: "${AZURE_DEVOPS_ORG}"
        project: "${AZURE_DEVOPS_PROJECT}"
        pat_token: "${AZURE_DEVOPS_PAT}"
        repo_name: "dbt-anthem"
        branch: "develop"
        
        # Path filtering
        include_paths:
          - "/dbt_anthem/models"
          - "/dbt_anthem/macros"
          - "/dbt_anthem/tests"
        
        exclude_paths:
          - "/dbt_anthem/tests/fixtures"
        
        # File type filtering
        include_file_types: [".sql", ".yml", ".py", ".md"]
        exclude_file_types: [".gitignore", ".gitkeep"]
        
        # Commit history
        fetch_commit_history: true
        commits_per_file: 10
        
        # Batch processing
        batch_size: 50
```

**Run ingestion:**

```bash
python main.py --ingest
```

The system will:
1. Connect to Azure DevOps
2. Fetch files matching filters
3. Track last N commits per file
4. Process in batches (default: 50 files)
5. Create searchable embeddings
6. Store in vector database

### Local Files

Place documents in `./data/` directory:

```bash
data/
├── documentation.pdf
├── guide.md
├── notes.txt
└── reference.html
```

Supported formats: PDF, Markdown, TXT, HTML

### Confluence (Planned)

Wiki pages and documentation import.

**Status**: Connector code exists, needs testing and configuration.

### DBT Integration (Beta)

Query DBT project metadata, lineage, and SQL code.

**Capabilities**:
- **Lineage Graphs**: In-memory graph traversal for model dependencies
- **SQL Extraction**: Parse manifest.json to extract 1,478+ SQL documents (models, tests, macros)
- **Seed Data**: CSV reference data with automatic linking to models
- **Business Queries**: "Does QM2 include J1434 for NK1 high emetic risk?"

**Configuration**:
```yaml
azure_devops:
  include_paths:
    - "/dbt_anthem/target/"         # Artifacts (manifest, catalog, graph)
    - "/dbt_anthem/dbt_project.yml" # Project config
    - "/dbt_anthem/data/"           # Seed CSV files
```

**Status**: Core processing complete, streaming configuration pending (30 min setup)  
**Documentation**: See `docs/DBT_INTEGRATION_STATUS.md`

### Jira (Planned)

Ticket descriptions, comments, and requirements.

**Status**: API integration planned.

---

## ⚙️ Configuration

### Main Settings (`config.yaml`)

```yaml
# Vector Store
vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "rag_documents"  # Generic collection name

# Embedding Model
embedding_model:
  provider: "azure_openai"
  azure_model: "text-embedding-ada-002"
  azure_deployment_name: "text-embedding-ada-002"

# LLM Configuration
llm:
  model: "gpt-4o"
  provider: "azure_openai"
  temperature: 0.1
  max_tokens: 4096
  prompt_template: "./prompts/general.txt"  # Enforces strict grounding
  system_instruction: "Answer STRICTLY from context..."

# Retrieval Settings
retrieval:
  top_k: 5
  strategy: "hybrid"  # Semantic + keyword
  rerank: true

# UI Settings
ui:
  framework: "fastapi"
  port: 8000
  host: "0.0.0.0"
  debug: false
```

### Prompt Templates

System uses strict grounding prompts in `prompts/`:

- **`general.txt`**: Default (enforces document-only answers) ← **PRIMARY**
- **`simple.txt`**: Minimal style
- **`iconnect_concise.txt`**: Concise with visual elements
- **`iconnect_enterprise.txt`**: Detailed explanatory style

All prompts enforce: **Answer ONLY from provided context, suggest rephrasing if information unavailable.**

---

## 🏗️ Architecture

### 5-Module System

```
┌─────────────────────────────────────────────────┐
│ Module 1: Corpus Embedding                      │
│ - Multi-source ingestion (Azure DevOps, Local)  │
│ - Chunking with configurable strategies         │
│ - Azure OpenAI embeddings                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Module 2: Query Retrieval                       │
│ - Hybrid search (semantic + keyword)            │
│ - Metadata filtering                            │
│ - Result reranking                              │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Module 3: LLM Orchestration                     │
│ - Azure OpenAI GPT-4/GPT-4o                     │
│ - Fallback providers (OpenAI, Anthropic)        │
│ - Strict grounding enforcement                  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Module 4: UI Layer (FastAPI)                    │
│ - REST API endpoints                            │
│ - Server-Sent Events for progress              │
│ - HTML templates + static assets               │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ Module 5: Evaluation & Logging                  │
│ - Structured JSON logs                          │
│ - Performance metrics                           │
│ - Query/response tracking                       │
└─────────────────────────────────────────────────┘
```

### Project Structure

```
RAG-ing/
├── main.py                    # CLI entry point
├── config.yaml                # System configuration (SINGLE SOURCE OF TRUTH)
├── .env                       # API credentials (create this)
│
├── src/rag_ing/              # Core application
│   ├── orchestrator.py       # Coordinates all modules
│   ├── modules/              # Five core modules
│   │   ├── corpus_embedding.py      # Module 1
│   │   ├── query_retrieval.py       # Module 2
│   │   ├── llm_orchestration.py     # Module 3
│   │   ├── ui_layer.py              # Module 4
│   │   └── evaluation_logging.py    # Module 5
│   ├── connectors/           # Data source integrations
│   │   ├── azuredevops_connector.py
│   │   └── confluence_connector.py
│   ├── config/               # Settings management
│   └── utils/                # Utilities (tracking, chunking, etc.)
│
├── ui/                       # FastAPI web interface
│   ├── app.py                # FastAPI application
│   ├── api/                  # REST endpoints
│   ├── templates/            # Jinja2 HTML templates
│   └── static/               # CSS, JavaScript
│
├── prompts/                  # LLM prompt templates (strict grounding)
├── data/                     # Local document storage
├── vector_store/             # ChromaDB persistence
└── logs/                     # Structured JSON logs
```

---

## 🔌 API Reference

### REST Endpoints

```python
# Search endpoint
POST /api/search
{
    "query": "What SQL models exist?",
    "audience": "general"  # or "technical"
}

# Search with progress tracking
POST /api/search-with-progress
GET  /api/progress/{session_id}  # Server-Sent Events
GET  /api/result/{session_id}

# System endpoints
GET  /api/health
GET  /docs  # Interactive API documentation (Swagger UI)
```

### Programmatic Usage

```python
from src.rag_ing.orchestrator import RAGOrchestrator
from src.rag_ing.config.settings import Settings

# Load configuration
settings = Settings.from_yaml('./config.yaml')
rag = RAGOrchestrator(settings)

# Index documents
rag.ingest_corpus()

# Query the system
result = rag.query_documents(
    query="How is data transformation implemented?",
    audience="technical"
)

print(result['response'])
print(result['sources'])
```

---

## 📊 Monitoring & Logs

### Structured Logging

JSON logs for analysis:

```
logs/
├── evaluation.jsonl          # Query/response events
├── retrieval_metrics.jsonl   # Search performance
└── generation_metrics.jsonl  # LLM quality metrics
```

### Health Monitoring

```bash
# System health check
python main.py --status

# View logs
tail -f logs/evaluation.jsonl
```

### Performance Metrics

Tracks:
- Query latency and throughput
- Vector search performance
- LLM token usage
- Embedding API calls
- Batch processing stats

---

## 🛠️ Development

### Technology Stack
- **Python**: 3.8+
- **Framework**: FastAPI
- **AI/ML**: Azure OpenAI, LangChain
- **Vector DB**: ChromaDB
- **Frontend**: HTML/CSS/JavaScript (vanilla - no framework)

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Code quality
black src/ ui/
flake8 src/ ui/
mypy src/
```

### Coding Standards

See `.github/copilot-instructions.md` for comprehensive guidelines:

1. **NO EMOJIS** in production code (encoding issues)
2. Comments describe CURRENT state (not history)
3. Error messages: polite + system error + solution
4. Strict grounding in all LLM prompts
5. Generic/domain-agnostic code

---

## 🚢 Deployment

### Docker

```bash
# Standard deployment
docker-compose up --build

# Minimal (no persistence)
docker-compose -f docker-compose.minimal.yml up --build

# Using deployment script
./docker/deploy.sh start
./docker/deploy.sh logs
./docker/deploy.sh stop
```

### Production Considerations

- **Azure App Service**: Deploy FastAPI application
- **Azure OpenAI**: Use managed AI service
- **Persistent Storage**: Mount volumes for `vector_store/` and `data/`
- **Secrets Management**: Azure Key Vault for credentials
- **Monitoring**: Application Insights integration

---

## 🗺️ Roadmap

### ✅ Current Features (v0.1.0)

**Core System**:
- General-purpose RAG (domain-agnostic)
- Strict document grounding (zero hallucination)
- Azure OpenAI integration (GPT-4/GPT-4o)
- ChromaDB vector storage with hierarchical collections
- FastAPI web interface
- Structured logging

**Hierarchical Storage** (✅ Complete):
- Two-tier retrieval: summaries for high-level search, chunks for details
- LLM-generated rich summaries with:
  - Business context and purpose
  - Searchable keywords and topics (10-15 per doc)
  - Document type classification
  - Technical details (tables, functions, dependencies)
- Type-specific summarization:
  - SQL: Business logic, data transformations, key metrics
  - Python: Functionality, classes, external dependencies
  - YAML: Configuration settings, relationships
  - PDF: Key entities, document category, sections
- Smart routing: Top 15 summary candidates → metadata boosting → top 5 detailed results
### 🎯 Next Release: Project-Aware RAG with DBT Artifacts (v0.2.0)

**DBT Artifacts Integration** (In Development - Q1 2026):
- [ ] **DBT Manifest Parser**: Parse manifest.json, catalog.json, dbt_project.yml
- [ ] **Project Detection**: Identify DBT projects from folder structure
- [ ] **Rich Metadata Extraction**:
  - Model descriptions and documentation
  - Column-level lineage and descriptions
  - Tags, meta properties, owners
  - Dependency graphs (upstream/downstream)
  - Test definitions and results
- [ ] **Project-Aware Filtering**: 
  - Query understanding layer (detect project mentions)
  - Metadata-based filtering (project tags)
  - Multi-project comparison queries
- [ ] **Enhanced Search**:
  - "What is QM2 logic in Anthem project?" (project-scoped)
  - "Compare QM1 across EOM, Anthem, and UPMC" (multi-project)
  - "Show all models in staging layer" (structural queries)
- [ ] **Knowledge Graph Integration**:
  - DBT lineage → graph relationships
  - Model-to-model dependencies
  - Table-to-column mappings

**Enhanced Azure DevOps** (Q1 2026):
- Multi-repository support
- Commit history tracking (last N commits per file)
- Path and file type filtering
- Batch processing (configurable size)
- Incremental updates (change detection)
- SQLite-based ingestion tracking

**Data Processing**:
- Local file ingestion (PDF, MD, TXT, HTML)
- Hybrid search (semantic + keyword)
- Generic domain code extraction (error codes, tickets, versions)

### 🎯 Planned Features (v0.2.0)

**Enhanced Azure DevOps** (Q1 2026):
- [ ] PR and commit message analysis
- [ ] Code diff tracking
- [ ] Branch comparison
- [ ] Author-based filtering
- [ ] Time-range queries ("changes in last 3 months")

**Additional Connectors** (Q1-Q2 2026):
- [ ] **Confluence**: Live wiki synchronization
- [ ] **Jira**: Ticket and comment indexing
- [ ] **SharePoint**: Document library integration
- [ ] **GitHub**: Repository and PR analysis

**Advanced Features** (Q2 2026):
- [ ] Multi-modal search (images, diagrams)
- [ ] Semantic code chunking (function/class aware)
- [ ] Caching layer (reduce redundant LLM calls)
- [ ] Query suggestions and autocomplete
- [ ] Document summarization
- [ ] User feedback loop integration

**Performance** (Q2 2026):
- [ ] Async embedding generation
- [ ] Parallel batch processing
- [ ] Response streaming
- [ ] Query result caching

**Enterprise Features** (Q3 2026):
- [ ] User authentication (Azure AD)
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Multi-tenant support
- [ ] Custom domain code patterns

### 📋 Backlog

- Graph-based RAG for relationship queries
- Fine-tuned embedding models
- Custom chunking strategies per file type
- Automated document refresh scheduling
- Export/import vector store
- A/B testing framework for prompts

---

## 📚 Documentation

- **Quick Start**: This README
- **Developer Guide**: `developer_guide.md`
- **AI Agent Instructions**: `.github/copilot-instructions.md`
- **Technical Requirements**: `src/Requirement.md`
- **Configuration Reference**: See `config.yaml` comments

---

## 🤝 Contributing

Contributions welcome! Please:

1. Follow coding standards in `.github/copilot-instructions.md`
2. No emojis in production code
3. Enforce strict grounding in LLM prompts
4. Write tests for new features
5. Update documentation

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 💬 Support

**Issues**: Open a GitHub issue for bugs or feature requests

**Documentation**:
- Quick Start: This README
- Developer Guide: `developer_guide.md`
- API Docs: http://localhost:8000/docs (after starting UI)

**Key Files**:
- Configuration: `config.yaml`
- Environment: `.env` (create from `env.example`)
- Prompts: `prompts/general.txt`

---

**Made with ❤️ for developers who want truthful AI answers**
