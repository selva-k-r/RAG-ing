# RAG-ing Developer Guide

Developer-facing overview of how the system is structured today, how configuration flows into runtime objects, and how ingestion/query pipelines are wired.

This guide only describes the **current state** of the project on `feature/using-dbt-artifacts`.

---

## Directory Overview

```
RAG-ing/
├── config.yaml              # System configuration
├── .env                     # Credentials (gitignored)
├── env.example             # Credentials template
├── pyproject.toml          # Python dependencies
├── main.py                 # CLI entry point
│
├── src/rag_ing/            # Core RAG package
│   ├── orchestrator.py     # Main coordinator
│   ├── config/            # Settings management
│   ├── connectors/        # Data source connectors
│   ├── modules/           # 5 core modules
│   ├── evaluation/        # RAGAS integration
│   ├── retrieval/         # Hybrid search
│   └── utils/             # Shared utilities
│
├── ui/                     # Web interface
│   ├── app.py             # FastAPI application
│   ├── enhanced_response.py # Response generator
│   ├── api/               # API routes
│   ├── templates/         # HTML templates
│   └── static/            # CSS/JS assets
│
├── data/                   # Source documents
├── vector_store/          # Vector database
├── logs/                  # Application logs
├── prompts/               # LLM prompt templates
└── tests/                 # Unit tests
```

## Core Components

### 1. Entry Points
- **main.py** - CLI interface
- **ui/app.py** - Web server

### 2. Configuration
- **config.yaml** - All system settings
- **.env** - API credentials

### 3. Source Code Modules
- **orchestrator.py** - Coordinates all modules
- **config/settings.py** - Configuration management
- **connectors/** - Data source integrations
- **modules/** - 5 core RAG modules
- **evaluation/** - Quality metrics
- **retrieval/** - Search logic
- **utils/** - Helper functions

### 4. Web Interface
- **ui/app.py** - FastAPI server
- **ui/api/routes.py** - REST endpoints
- **ui/enhanced_response.py** - Response formatting
- **ui/templates/** - HTML pages
- **ui/static/** - Frontend assets
