# RAG-ing Application - Build & Run Guide

## What is RAG-ing?

**RAG-ing** is a comprehensive **Retrieval-Augmented Generation (RAG)** application that provides:

### Core Features:
- 🔗 **Multiple Document Connectors**: Connect to various data sources
  - Confluence (Atlassian)
  - Medium articles  
  - Twitter/X posts
  - Reddit posts
- 🤖 **Dynamic Model Selection**: Support for multiple LLM and embedding providers
  - LLMs: OpenAI, Anthropic (Claude)
  - Embeddings: OpenAI, HuggingFace
- 🗄️ **Flexible Vector Storage**: Snowflake, FAISS, ChromaDB
- ✂️ **Smart Text Chunking**: Configurable chunking strategies
- 🎛️ **User-Friendly Interface**: Streamlit-based web UI

### Reference Design:
The `/tests/poc/` folder contains **iConnect** - the reference design showing:
- Modern gradient UI (blue to teal)
- Multi-source search with toggleable filters
- FAQ sections with detailed answer pages
- Clean search interface

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection for downloading dependencies

## Build Instructions

### 1. Install Dependencies

```bash
# Install the application in development mode
pip install -e .

# Or for production
pip install .

# Or with development tools
pip install -e ".[dev]"
```

### 2. Configure Environment

Copy and customize the environment configuration:

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

Required API keys (get from respective providers):
- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Claude models (optional)
- `HUGGINGFACE_API_KEY`: For HuggingFace models (optional)

### 3. Run the Application

#### Method 1: Using CLI (Recommended)
```bash
# Basic run
rag-ing

# With custom port
rag-ing --port 8080

# Allow external connections (for dev containers)
rag-ing --host 0.0.0.0 --port 8501

# With debug logging
rag-ing --debug
```

#### Method 2: Using main.py
```bash
# Basic run
python main.py

# With options
python main.py --port 8080 --debug
```

### 4. Access the Application

Once running, access the application at:
- Local: http://localhost:8501
- Dev Container: http://0.0.0.0:8501

## Available CLI Options

```
rag-ing [-h] [--ui {streamlit}] [--port PORT] [--host HOST] [--debug] [--version]

Options:
  --ui {streamlit}     UI type to launch (default: streamlit)
  --port PORT          Port for the web interface (default: 8501)
  --host HOST          Host for the web interface (default: localhost)
  --debug              Enable debug logging
  --version            Show program version
```

## Configuration

The application uses a hierarchical configuration system via `.env` file:

```bash
# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
HUGGINGFACE_API_KEY=your_key_here

# Application
DEBUG=false
```

Additional configuration can be done through the Streamlit UI for:
- Document connectors (Confluence, Medium, etc.)
- Vector stores (FAISS, ChromaDB, Snowflake)
- Model selection (LLM and embedding models)
- Chunking strategies

## Architecture

```
src/rag_ing/
├── config/          # Configuration management
├── connectors/      # Document source connectors
├── models/          # LLM and embedding model managers
├── storage/         # Vector store implementations
├── ui/              # Streamlit web interface
├── chunking.py      # Text chunking utilities
└── cli.py           # Command-line interface
```

## Development

For development work:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black .

# Type checking
mypy .
```

## Troubleshooting

1. **Import Errors**: Ensure you're running from the project root directory
2. **API Key Issues**: Verify your API keys in the `.env` file
3. **Port Conflicts**: Use `--port` option to specify a different port
4. **Permission Issues**: Use `--host 0.0.0.0` for dev container access

## Next Steps

1. Configure your API keys in `.env`
2. Launch the application using `rag-ing --host 0.0.0.0`
3. Access the web interface to configure connectors and test queries
4. Explore the POC examples in `/tests/poc/` for UI reference design