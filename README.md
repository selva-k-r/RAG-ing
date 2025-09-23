# RAG-ing

A comprehensive RAG (Retrieval-Augmented Generation) application with multiple document connectors and dynamic model selection. Built with LangChain and Streamlit.

## Features

- 🔗 **Multiple Document Connectors**: Connect to various data sources
  - Confluence (Atlassian)
  - Medium articles
  - Twitter/X posts
  - Reddit posts
  - Extensible architecture for more connectors

- 🤖 **Dynamic Model Selection**: 
  - Support for multiple embedding providers (OpenAI, HuggingFace)
  - Support for multiple LLM providers (OpenAI, Anthropic)
  - Runtime model switching

- 🗄️ **Flexible Vector Storage**:
  - Snowflake integration
  - FAISS (local)
  - ChromaDB (local)

- ✂️ **Smart Text Chunking**: Configurable chunking strategies for optimal retrieval

- 🎛️ **User-Friendly Interface**: Streamlit-based web UI for easy interaction

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or conda package manager

### Install from source

1. Clone the repository:
```bash
git clone https://github.com/selva-k-r/RAG-ing.git
cd RAG-ing
```

2. Install dependencies:
```bash
pip install -e .
```

Or for development:
```bash
pip install -e ".[dev]"
```

## Quick Start

1. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

2. **Run the application**:
```bash
python main.py
```

Or directly with Streamlit:
```bash
streamlit run src/rag_ing/ui/streamlit_app.py
```

3. **Open your browser** to `http://localhost:8501`

## Configuration

### Environment Variables

Create a `.env` file with your API keys and configuration:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (for Claude models)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Snowflake Configuration (optional)
SNOWFLAKE_ACCOUNT=your_account.region.snowflakecomputing.com
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema

# Confluence Configuration (optional)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your_email@domain.com
CONFLUENCE_API_TOKEN=your_confluence_api_token
```

### Supported Models

#### Embedding Models
- **OpenAI**: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
- **HuggingFace**: sentence-transformers/all-MiniLM-L6-v2, BAAI/bge-small-en-v1.5, and more

#### Language Models
- **OpenAI**: gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o
- **Anthropic**: claude-3-sonnet, claude-3-opus, claude-3-haiku

## Usage

### 1. Configure Models
- In the sidebar, select your preferred embedding and language models
- Enter API keys
- Click "Load Models"

### 2. Connect Data Sources
Navigate to the "Document Sources" tab and configure your connectors:

#### Confluence
- Enter your Confluence base URL, username, and API token
- Optionally specify a space key to limit the scope
- Click "Connect to Confluence" and then "Fetch Documents"

#### Medium
- Enter a Medium username (e.g., @your_username) or RSS URL
- Click "Connect to Medium" and then "Fetch Articles"

#### Twitter
- Enter your Twitter Bearer Token and target username
- Click "Connect to Twitter" and then "Fetch Tweets"

#### Reddit
- Enter your Reddit app credentials and target subreddit
- Click "Connect to Reddit" and then "Fetch Posts"

### 3. Process Documents
Go to the "Processing" tab:
- Configure chunking parameters (size, overlap, method)
- Click "Chunk Documents" to split documents into smaller pieces
- Click "Store in Vector Database" to create embeddings and store them

### 4. Query Your Data
In the "Query & Chat" tab:
- Enter questions about your documents
- Adjust the number of results to retrieve
- Get AI-powered answers based on your data

## API Reference

### Core Components

#### EmbeddingManager
```python
from rag_ing.models import embedding_manager, EmbeddingModelConfig

config = EmbeddingModelConfig(
    provider="openai",
    model_name="text-embedding-ada-002",
    api_key="your-key"
)
embedding_manager.load_model(config)
```

#### LLMManager
```python
from rag_ing.models import llm_manager, LLMConfig

config = LLMConfig(
    provider="openai",
    model_name="gpt-3.5-turbo",
    api_key="your-key",
    temperature=0.1
)
llm_manager.load_model(config)
```

#### VectorStoreManager
```python
from rag_ing.storage import vector_store_manager

# Create FAISS store
store = vector_store_manager.create_faiss_store(embeddings)

# Add documents
vector_store_manager.add_documents(documents)

# Search
results = vector_store_manager.similarity_search("query", k=5)
```

### Connectors

#### Confluence
```python
from rag_ing.connectors import ConfluenceConnector

config = {
    "base_url": "https://your-domain.atlassian.net",
    "username": "your-email@domain.com",
    "api_token": "your-token"
}

connector = ConfluenceConnector(config)
connector.connect()
documents = connector.fetch_documents(limit=50)
```

## Development

### Project Structure
```
RAG-ing/
├── src/rag_ing/
│   ├── config/          # Configuration management
│   ├── connectors/      # Document source connectors
│   ├── models/          # LLM and embedding managers
│   ├── storage/         # Vector store implementations
│   ├── ui/              # Streamlit interface
│   └── chunking.py      # Text chunking service
├── main.py              # Main entry point
├── pyproject.toml       # Project configuration
└── README.md           # This file
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Type Checking
```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [ ] Additional connectors (Slack, Discord, GitHub, etc.)
- [ ] Advanced query techniques (hypothetical document embeddings, etc.)
- [ ] Support for more vector databases (Pinecone, Weaviate, etc.)
- [ ] Chat history and conversation memory
- [ ] Document summarization features
- [ ] API endpoints for programmatic access
- [ ] Docker containerization
- [ ] Cloud deployment templates

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/selva-k-r/RAG-ing/issues) page
2. Create a new issue with detailed information
3. Provide logs and configuration details (without sensitive information)

## Acknowledgments

- Built with [LangChain](https://langchain.com/) for LLM orchestration
- UI powered by [Streamlit](https://streamlit.io/)
- Thanks to the open-source community for the amazing tools and libraries
