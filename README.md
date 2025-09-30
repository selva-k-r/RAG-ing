# RAG-ing: Modular Enterprise RAG System

� **A sophisticated 5-module RAG system with FastAPI web interface and beginner-friendly AI responses.**

## 🏗️ System Overview

This application implements a comprehensive **5-module architecture** designed for enterprise search and knowledge management, with each module serving a distinct purpose in the RAG pipeline:

### Module 1: Corpus & Embedding Lifecycle
- **Purpose**: Document ingestion and embedding generation
- **Features**: 
  - YAML-driven multi-format ingestion (PDF, TXT, MD, HTML)
  - Advanced embedding models with fallback support
  - Semantic chunking with metadata preservation
  - Vector store management (ChromaDB with persistence)
- **File**: `src/rag_ing/modules/corpus_embedding.py`

### Module 2: Query Processing & Retrieval
- **Purpose**: Query processing and document retrieval
- **Features**:
  - Hybrid retrieval (semantic + keyword)
  - Query enhancement and context understanding
  - Smart filtering and ranking
  - Similarity search with reranking
  - Intelligent caching system
- **File**: `src/rag_ing/modules/query_retrieval.py`

### Module 3: LLM Orchestration
- **Purpose**: Language model integration and response generation
- **Features**:
  - Azure OpenAI integration (gpt-5-nano)
  - Multi-provider fallback (OpenAI, Anthropic, KoboldCpp)
  - Beginner-friendly prompt engineering
  - Visual response formatting
  - Citation-aware response generation
- **File**: `src/rag_ing/modules/llm_orchestration.py`

### Module 4: UI Layer
- **Purpose**: FastAPI web interface with 100% control
- **Features**:
  - FastAPI backend with pure HTML/CSS/JS frontend
  - Real-time search with dynamic result pages
  - Audience toggle (clinical vs technical responses)
  - Professional result styling (faq1.html design)
  - Search results caching for detailed views
- **Files**: `web_app.py` (FastAPI server) + `index.html` (frontend)

### Module 5: Evaluation & Logging
- **Purpose**: Performance tracking and structured logging
- **Features**:
  - Precision@K metrics for retrieval evaluation
  - Citation coverage analysis
  - Safety score calculation
  - Structured JSON logging with session analytics
  - User feedback correlation and export capabilities
- **File**: `src/rag_ing/modules/evaluation_logging.py`

## 🎯 Key Features

### **Visual AI Responses**
- 📋 **Step-by-step processes** with numbered instructions
- 🔧 **Technical guidance** with troubleshooting steps
- 📊 **Data relationships** with simple diagrams
- ⚠️ **Important warnings** clearly highlighted
- ✅ **Success indicators** and completion steps

### **Beginner-Friendly Explanations**
- Simple, everyday language for complex topics
- Context explanations for all technical terms
- Visual organization with emojis and clear structure
- Examples and analogies to aid understanding
- Progressive disclosure from simple to detailed

### **Enterprise-Ready Architecture**
- FastAPI backend for high performance and scalability
- Pure HTML/CSS/JS frontend for maximum UI control
- Azure OpenAI integration with credential security
- Comprehensive error handling and retry logic
- Structured logging and performance monitoring

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd RAG-ing

# Install dependencies
pip install -e .
```

### 2. Environment Setup

Create your environment file:

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

Required environment variables:
```bash
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### 3. First Run (3 Simple Steps)

```bash
# Step 1: Process your documents (REQUIRED first step)
python main.py --ingest

# Step 2: Launch the web interface
python main.py --ui

# Alternative: Single query via CLI
python main.py --query "How do I setup my development environment?" --audience technical
```

**Access your system**: Open http://localhost:8000 in your browser

## 📱 Web Interface

### **Main Search Interface** (`index.html`)
- Clean, professional design matching mockup specifications
- Real-time search with live result previews
- Source filtering (Confluence, JIRA, Internal docs, Salesforce)
- Audience toggle for clinical vs technical responses

### **Dynamic Result Pages**
- Professionally styled result pages (faq1.html design)
- Step-by-step instructions with visual organization
- Confidence scoring and source attribution
- Actionable content with templates and checklists

### **Search Features**
- **Real-time search** with instant feedback
- **Result caching** for detailed view navigation
- **Multi-source filtering** with toggle options
- **Responsive design** for all screen sizes

## 📋 Usage Examples

### Command Line Interface

```bash
# System status and health check
python main.py --status
python main.py --health-check

# Launch web interface (FastAPI)
python main.py --ui

# Direct query testing
python main.py --query "How do I setup DBT for PopHealth?" --audience technical

# Document ingestion
python main.py --ingest --debug

# Export session metrics
python main.py --export-metrics
```

### Web Interface Usage

1. **Start the server**:
   ```bash
   python main.py --ui
   ```

2. **Open in browser**: http://localhost:8000

3. **Search examples**:
   - "How do I setup my development environment?"
   - "What's the process for raising a DevOps ticket?"
   - "How do I configure DBT for PopHealth team?"
   - "What are the data relationships in our analytics?"

### Programmatic Usage

```python
from src.rag_ing.config.settings import Settings
from src.rag_ing.orchestrator import RAGOrchestrator

# Load configuration
settings = Settings.from_yaml('./config.yaml')

# Initialize orchestrator
orchestrator = RAGOrchestrator(settings)

# Process corpus
results = orchestrator.process_corpus()

# Query the system
response = orchestrator.query_documents(
    query="How do I access the PopHealth database?",
    audience="technical"
)

print(response['response'])
```

## 🎨 Response Examples

### **Technical Setup Question**
**Query**: "How do I setup DBT for PopHealth?"

**Response Format**:
```
Here's what I found: You need to install DBT and configure your PopHealth environment.

📋 Setup Steps:
1. Install DBT for Snowflake
2. Configure your DBT profile
3. Clone the PopHealth repository
4. Request Snowflake access via DevOps ticket

🔧 Technical Details:
• Installation: pip install dbt-snowflake
• Configuration: ~/.dbt/profiles.yml
• Repository: https://github.com/integraconnect/dbt-pophealth

⚠️ Important: You'll need DevOps ticket for database access

✅ Success: Run 'dbt --version' to verify installation
```

### **Process Question**
**Query**: "How do I raise a DevOps ticket?"

**Response Format**:
```
Here's what I found: You can create a DevOps ticket using our standard template.

📋 DevOps Ticket Process:
1. Use the ticket template below
2. Fill in your specific details  
3. Submit via our DevOps portal
4. Track progress in JIRA

🎫 Ticket Template:
Title: [Your Issue] - Access Request
Priority: Medium
Category: Access Management
Description: [Detailed description with steps to reproduce]
```

## 📊 Configuration Reference

### Core Configuration Structure

The system is driven by `config.yaml` with YAML-based configuration:

```yaml
# Module 1: Corpus & Embedding
data_source:
  type: "local_file"
  path: "./data/"

embedding_model:
  name: "pubmedbert"
  device: "cpu"

# Module 2: Query Processing
retrieval:
  top_k: 5
  strategy: "similarity"

# Module 3: LLM Orchestration  
llm:
  model: "gpt-5-nano"
  provider: "azure_openai"
  prompt_template: "./prompts/iconnect_enterprise.txt"
  max_tokens: 800

# Module 4: UI Layer (FastAPI)
ui:
  framework: "fastapi"
  audience_toggle: true
  feedback_enabled: true

# Module 5: Evaluation & Logging
evaluation:
  metrics:
    precision_at_k: true
    citation_coverage: true
    safety: true
  logging:
    enabled: true
    format: "json"
    path: "./logs/"

# Vector Store Configuration
vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "oncology_docs"
```

### Environment Variables

Required for Azure OpenAI integration:

```bash
# Azure OpenAI (Primary)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Fallback Providers (Optional)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# System Paths
DATA_DIR=./data
LOGS_DIR=./logs
```

### Prompt Templates

The system uses specialized prompts for different response styles:

- **`iconnect_enterprise.txt`**: Full-featured responses with visual organization
- **`iconnect_concise.txt`**: Streamlined responses for quick answers
- **`oncology.txt`**: Legacy medical/clinical responses (archived)

Customize prompts by editing files in `./prompts/` directory.

## 🏥 Clinical vs Technical Modes

The system provides specialized interfaces for different audiences:

### Clinical Mode
- Simplified, accessible language
- Focus on treatment guidelines and recommendations
- Safety warnings and medical disclaimers
- Direct clinical applicability

### Technical Mode  
- Detailed methodology and statistical analysis
- Research limitations and study design details
- Peer review status and confidence intervals
- Advanced technical terminology

Toggle between modes using the UI or specify via CLI:

```bash
python main.py --query "How does CAR-T therapy work?" --audience clinical
python main.py --query "What is the mechanism of CAR-T cell activation?" --audience technical
```

## 📈 Performance Monitoring

### Built-in Metrics

The system automatically tracks:
- **Retrieval Metrics**: Precision@1/3/5, hit rate, latency
- **Generation Metrics**: Response quality, citation coverage, safety scores
- **System Metrics**: Error rates, response times, memory usage
- **User Feedback**: Clarity, usefulness, safety ratings

### Viewing Metrics

```bash
# System status
python main.py --status

# Export detailed metrics
python main.py --export-metrics

# Health check
python main.py --health-check
```

### Log Files

Structured logs are written to:
- `./logs/evaluation.jsonl` - Complete query events
- `./logs/retrieval_metrics.jsonl` - Retrieval performance
- `./logs/generation_metrics.jsonl` - Generation quality

## 🔧 Development Setup

### Local Development Environment

1. **Prerequisites**
   ```bash
   # Python 3.8+ required
   python --version
   
   # Git for version control  
   git --version
   ```

2. **Clone and Setup**
   ```bash
   git clone https://github.com/your-org/rag-ing.git
   cd rag-ing
   
   # Install in development mode
   pip install -e .
   ```

3. **Environment Configuration**
   ```bash
   # Configure your API keys and settings
   nano config.yaml
   
   # Set environment variables
   export AZURE_OPENAI_API_KEY="your_azure_key"
   export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
   ```

4. **First Time Setup**
   ```bash
   # Process your documents (required first step)
   python main.py --ingest
   
   # Test configuration
   python validate.py
   
   # Launch FastAPI development server
   python main.py --ui
   # Web interface: http://localhost:8000
   ```

### Docker Development

Run the complete stack with Docker:

```bash
# Build and run
docker-compose up --build

# Access services
# FastAPI: http://localhost:8000
# Vector DB Admin: http://localhost:8080
```

### Project Structure

```
RAG-ing/
├── config.yaml                 # Main configuration file
├── main.py                     # CLI entry point
├── src/rag_ing/                # Core RAG system modules
│   ├── config/                 # YAML configuration management
│   ├── modules/                # 5 core modules
│   │   ├── corpus_embedding.py
│   │   ├── query_retrieval.py
│   │   ├── llm_orchestration.py
│   │   ├── ui_layer.py
│   │   └── evaluation_logging.py
│   ├── orchestrator.py         # Main coordinator
│   ├── connectors/             # External integrations
│   └── utils/                  # Shared utilities
├── ui/                         # Modular FastAPI web interface
│   ├── app.py                  # Main FastAPI application
│   ├── api/                    # API routes and handlers
│   ├── templates/              # HTML templates
│   └── static/                 # CSS and JavaScript files
├── prompts/                    # AI response templates
├── data/                       # Document storage
├── tests/                      # Test suite
├── archived/                   # Deprecated code with restoration info
└── temp_helper_codes/          # Development and testing utilities
```

### Testing & Quality Assurance

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_structure.py -v

# Run with coverage report
pytest tests/ --cov=src/rag_ing --cov-report=html
```

Code quality tools:

```bash
# Format code
black src/

# Lint code  
flake8 src/

# Type checking
mypy src/
```

### Adding New Data Sources

1. Update `config.yaml`:
```yaml
data_sources:
  - path: "/path/to/new/documents"
    type: "directory"
    enabled: true
    metadata:
      domain: "oncology"
      source_type: "clinical_trials"
```

2. Re-run ingestion:
```bash
python main.py --ingest
```

## 🛡️ Safety and Compliance

### Medical Disclaimers
The system automatically includes medical disclaimers for clinical queries and tracks safety scores.

### Data Privacy
- Configurable query anonymization
- Data retention policies
- Secure API key management

### Error Handling
- Comprehensive retry logic
- Graceful degradation
- Detailed error logging

## 📚 API Reference

### FastAPI Endpoints

The web interface provides several API endpoints:

```python
# Main endpoints
GET  /                    # Home page with search interface
POST /search             # Process search queries  
GET  /health            # System health check
GET  /metrics           # Performance metrics

# Query endpoint example
POST /search
{
    "query": "How does immunotherapy work?",
    "audience": "clinical"  # or "technical"
}

# Response format
{
    "response": "🩺 Medical Treatment...",
    "sources": [...],
    "query_hash": "abc123",
    "safety_score": 0.95
}
```

### RAGOrchestrator Class

Core system orchestrator:

```python
class RAGOrchestrator:
    def __init__(self, config: Settings)
    def process_corpus(self) -> Dict[str, Any]
    def query_documents(self, query: str, audience: str) -> Dict[str, Any]  
    def submit_feedback(self, query_hash: str, feedback: Dict) -> Dict
    def get_system_status(self) -> Dict[str, Any]
    def health_check(self) -> Dict[str, Any]
```

### Module Interfaces

Each module implements a consistent interface:
- Configuration-driven initialization from `config.yaml`
- Comprehensive error handling with `RAGError` exceptions
- Performance metrics tracking via Module 5
- Structured logging to `./logs/` directory

### Configuration API

Programmatic configuration access:

```python
from rag_ing.config.settings import Settings

# Load configuration
settings = Settings.from_yaml('./config.yaml')

# Access settings
print(settings.llm.model)           # gpt-5-nano
print(settings.llm.max_tokens)      # 800
print(settings.ui.framework)        # fastapi
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes following our coding standards
4. Add tests for new functionality
5. Run the test suite: `pytest tests/`
6. Submit a pull request

### Coding Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include comprehensive docstrings
- Write unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI Framework**: Modern, fast web framework for the API backend
- **Azure OpenAI**: gpt-5-nano model integration for advanced language processing  
- **ChromaDB**: Vector database for efficient semantic search
- **PubMedBERT**: Biomedical embeddings for domain-specific understanding
- **Pure HTML/CSS/JS**: Complete frontend control with dynamic page generation
- **Pydantic**: Configuration validation and settings management

---

**🔬 Enterprise-Grade RAG System with Advanced Prompt Engineering**