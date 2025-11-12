# RAG-ing: Enterprise RAG System

A production-ready Retrieval-Augmented Generation (RAG) system for intelligent document search and question answering. Connect to multiple data sources including Confluence, Jira, and local documents with Azure OpenAI integration.

## Features

### Core Capabilities
- **Multi-Source Integration**: Confluence, Jira, local files (PDF, Markdown, TXT, HTML)
- **Hybrid Search**: Semantic vector search combined with keyword matching
- **LLM Integration**: Azure OpenAI (GPT-4) with fallback to OpenAI and Anthropic
- **Real-time Responses**: Streaming text output with progress tracking
- **Vector Storage**: ChromaDB for persistent embeddings

### Architecture
Five-module system following YAML-driven configuration:
1. **Corpus Embedding**: Document ingestion, chunking, and vector generation
2. **Query Retrieval**: Hybrid search with semantic and keyword matching
3. **LLM Orchestration**: Multi-provider AI response generation
4. **UI Layer**: FastAPI web interface with real-time progress
5. **Evaluation & Logging**: Performance metrics and structured logging

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/selva-k-r/RAG-ing.git
cd RAG-ing

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

Create `.env` file with your API credentials:

```bash
# Azure OpenAI (Primary)
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional fallback providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Confluence integration (optional)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_TOKEN=your_confluence_token
CONFLUENCE_SPACE_KEY=YOUR_SPACE

# Jira integration (optional)
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@company.com
JIRA_API_TOKEN=your_jira_token
```

Configure data sources in `config.yaml`:

```yaml
data_source:
  type: "local_file"  # Options: local_file, confluence, jira
  path: "./data/"
  
  # Confluence configuration
  confluence:
    base_url: "${CONFLUENCE_BASE_URL}"
    auth_token: "${CONFLUENCE_TOKEN}"
    space_key: "${CONFLUENCE_SPACE_KEY}"
    page_filter: ["documentation", "guides"]
  
  # Jira configuration
  jira:
    server: "${JIRA_SERVER}"
    email: "${JIRA_EMAIL}"
    api_token: "${JIRA_API_TOKEN}"
    project_keys: ["PROJ1", "PROJ2"]
```

### Usage

```bash
# Step 1: Index your documents
python main.py --ingest

# Step 2: Launch web interface
python main.py --ui

# Step 3: Access at http://localhost:8000
```

Alternative commands:

```bash
# Single query via CLI
python main.py --query "your question here"

# System health check
python main.py --status

# Export performance metrics
python main.py --export-metrics
```

## Data Source Configuration

### Local Files
Place documents in the `./data/` directory. Supported formats:
- PDF documents
- Markdown (.md)
- Text files (.txt)
- HTML files (.html)

### Confluence Integration
Configure Confluence in `config.yaml`:

```yaml
data_source:
  type: "confluence"
  confluence:
    base_url: "https://your-domain.atlassian.net/wiki"
    auth_token: "${CONFLUENCE_TOKEN}"
    space_key: "DOCS"
    page_filter: ["guides", "api"]  # Optional: filter by labels
```

The system will automatically fetch and index pages from specified spaces.

### Jira Integration
Configure Jira in `config.yaml`:

```yaml
data_source:
  type: "jira"
  jira:
    server: "https://your-domain.atlassian.net"
    email: "your-email@company.com"
    api_token: "${JIRA_API_TOKEN}"
    project_keys: ["PROJ"]
    jql_filter: "project = PROJ AND type = Story"  # Optional
```

The system indexes ticket descriptions, comments, and attachments.

### Multi-Source Setup
To index from multiple sources, run ingestion separately for each:

```bash
# Index local files
python main.py --ingest

# Switch to Confluence in config.yaml, then:
python main.py --ingest

# Switch to Jira in config.yaml, then:
python main.py --ingest
```

All sources are stored in the same vector database for unified search.

## Project Structure

```
RAG-ing/
├── main.py                    # CLI entry point
├── config.yaml                # System configuration
├── .env                       # API credentials (create this)
├── pyproject.toml             # Dependencies and project metadata
│
├── src/rag_ing/              # Core application
│   ├── orchestrator.py       # Main RAG coordinator
│   ├── modules/              # Five core modules
│   │   ├── corpus_embedding.py
│   │   ├── query_retrieval.py
│   │   ├── llm_orchestration.py
│   │   ├── ui_layer.py
│   │   └── evaluation_logging.py
│   ├── config/               # Settings management
│   ├── connectors/           # Data source integrations
│   │   ├── confluence_connector.py
│   │   └── (jira connector planned)
│   └── utils/                # Shared utilities
│
├── ui/                       # Web interface
│   ├── app.py                # FastAPI application
│   ├── api/                  # API routes
│   ├── templates/            # HTML templates
│   └── static/               # CSS, JavaScript
│
├── data/                     # Local document storage
├── vector_store/             # ChromaDB persistence
├── logs/                     # Application logs
└── prompts/                  # LLM prompt templates
```

## API Reference

### REST Endpoints

```python
# Search endpoint
POST /api/search
{
    "query": "What is the process for X?",
    "audience": "technical"  # or "business"
}

# Search with progress tracking
POST /api/search-with-progress
GET  /api/progress/{session_id}  # Server-Sent Events
GET  /api/result/{session_id}

# System endpoints
GET  /api/health
GET  /docs  # Interactive API documentation
```

### Programmatic Usage

```python
from src.rag_ing.orchestrator import RAGOrchestrator
from src.rag_ing.config.settings import Settings

# Load configuration
settings = Settings.from_yaml('./config.yaml')
rag = RAGOrchestrator(settings)

# Index documents
rag.process_corpus()

# Query the system
result = rag.query_documents(
    query="your question",
    audience="technical"
)

print(result['response'])
print(result['sources'])
```

## Configuration

### Main Settings (config.yaml)

```yaml
# Embedding configuration
embedding_model:
  provider: "azure_openai"
  azure_model: "text-embedding-ada-002"
  fallback_model: "all-MiniLM-L6-v2"

# LLM configuration
llm:
  model: "gpt-4"
  provider: "azure_openai"
  max_tokens: 4096
  temperature: 0.1
  fallback_providers: ["openai", "anthropic"]

# Vector store
vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "enterprise_docs"

# Retrieval settings
retrieval:
  top_k: 5
  strategy: "hybrid"  # semantic + keyword
  rerank: true

# UI settings
ui:
  framework: "fastapi"
  port: 8000
  enable_progress: true
```

### Environment Variables

Required variables in `.env`:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Fallback providers (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Data source credentials (optional)
CONFLUENCE_TOKEN=
JIRA_API_TOKEN=
```

## Development

### Technology Stack
- **Python**: 3.8+
- **Framework**: FastAPI
- **AI/ML**: Azure OpenAI, LangChain, sentence-transformers
- **Vector DB**: ChromaDB
- **Frontend**: HTML/CSS/JavaScript (no framework dependencies)

### Development Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Code formatting
black src/ ui/
flake8 src/ ui/

# Type checking
mypy src/
```

### Package Status

All dependencies are on latest stable versions as of November 2025:

- **LangChain**: 1.0.5 (upgraded from 0.3.x)
- **OpenAI SDK**: 2.7.2 (upgraded from 1.x)
- **FastAPI**: 0.121.1
- **ChromaDB**: 1.3.4
- **Pydantic**: 2.12.4

Run package status checker:

```bash
python check_package_status.py
```

For details on completed Phase 2 migrations, see `MIGRATION_GUIDE.md` and `src/Requirement.md`.

## Deployment

### Docker

```bash
# Quick start
docker-compose up --build

# Minimal deployment (no persistence)
docker-compose -f docker-compose.minimal.yml up --build

# Using deployment script
./docker/deploy.sh start
./docker/deploy.sh logs
./docker/deploy.sh stop
```

### Production Considerations

- **Azure App Service**: Deploy FastAPI application
- **Azure OpenAI**: Use managed service for AI workloads
- **Persistent Storage**: Mount volumes for `vector_store/` and `data/`
- **Environment Variables**: Use Azure Key Vault or similar for secrets
- **Monitoring**: Enable Application Insights for logging and metrics

See `DOCKER_QUICKSTART.md` for detailed deployment instructions.

## Monitoring & Logs

### Log Files

Structured JSON logs for analysis:

```
logs/
├── evaluation.jsonl          # Complete query/response events
├── retrieval_metrics.jsonl   # Search performance metrics
└── generation_metrics.jsonl  # LLM response quality
```

### Health Monitoring

```bash
# System health check
python main.py --status

# Export metrics
python main.py --export-metrics

# View metrics in browser
http://localhost:8000/docs  # FastAPI interactive docs
```

### Performance Metrics

The system tracks:
- Query latency and throughput
- Vector search performance
- LLM token usage and cost
- User satisfaction scores
- Error rates and types

## Roadmap

### Current Features
- Local file ingestion (PDF, Markdown, TXT, HTML)
- Azure OpenAI integration with fallback providers
- ChromaDB vector storage
- FastAPI web interface with progress tracking
- Hybrid search (semantic + keyword)
- Structured logging and metrics

### Planned Enhancements
- **Confluence Integration**: Live document synchronization
- **Jira Integration**: Ticket and comment indexing
- **Advanced Chunking**: Semantic splitting with context preservation
- **Multi-modal Search**: Image and diagram processing
- **Citation Tracking**: Improved source attribution
- **Caching Layer**: Reduce redundant LLM calls

See `src/Requirement.md` for detailed technical requirements and implementation status.
## Contributing

Contributions are welcome. Please follow the development setup and coding standards outlined in this document.

For major version updates or dependency changes, refer to:
- `MIGRATION_GUIDE.md` - Step-by-step migration instructions
- `check_package_status.py` - Dependency status checker

## License

MIT License - See LICENSE file for details.

## Support

- Technical documentation: `src/Requirement.md`
- Configuration guide: `.github/copilot-instructions.md`
- Deployment help: `DOCKER_QUICKSTART.md`

For questions or issues, please open a GitHub issue.
