# RAG-ing: Modular RAG PoC for Oncology

🔬 **A sophisticated 5-module RAG system specifically designed for oncology research and clinical decision support.**

## 🏗️ Modular Architecture

This application implements a comprehensive **5-module architecture** as specified in our requirements document, with each module serving a distinct purpose in the RAG pipeline:

### Module 1: Corpus & Embedding Lifecycle
- **Purpose**: Document ingestion and embedding generation
- **Features**: 
  - YAML-driven multi-format ingestion (PDF, TXT, MD, HTML)
  - Biomedical embedding models (PubMedBERT, Bio_ClinicalBERT)
  - Semantic chunking with ontology code extraction (ICD-O, SNOMED-CT, MeSH)
  - Vector store management (ChromaDB, FAISS)
- **File**: `src/rag_ing/modules/corpus_embedding.py`

### Module 2: Query Processing & Retrieval
- **Purpose**: Query processing and document retrieval
- **Features**:
  - Hybrid retrieval (semantic + keyword)
  - Query expansion and enhancement
  - Domain-specific filtering for oncology
  - Similarity search with reranking
  - Intelligent caching system
- **File**: `src/rag_ing/modules/query_retrieval.py`

### Module 3: LLM Orchestration
- **Purpose**: Language model integration and response generation
- **Features**:
  - KoboldCpp integration for local deployment
  - Multi-provider fallback (OpenAI, Anthropic)
  - Audience-specific prompt templates (clinical vs technical)
  - Retry logic and timeout handling
  - Citation-aware response generation
- **File**: `src/rag_ing/modules/llm_orchestration.py`

### Module 4: UI Layer
- **Purpose**: User interface with audience toggle and feedback collection
- **Features**:
  - Streamlit-based responsive interface
  - Clinical vs Technical audience toggle
  - Real-time feedback collection (clarity, safety, usefulness)
  - Query history and source document display
  - Performance metrics visualization
- **File**: `src/rag_ing/modules/ui_layer.py`

### Module 5: Evaluation & Logging
- **Purpose**: Performance tracking and structured logging
- **Features**:
  - Precision@K metrics for retrieval evaluation
  - Citation coverage analysis
  - Safety score calculation with medical disclaimers
  - Structured JSON logging
  - Session analytics and export capabilities
- **File**: `src/rag_ing/modules/evaluation_logging.py`

## 🎯 Oncology Domain Specialization

This RAG system is specifically tailored for oncology use cases:

- **Biomedical Embeddings**: Uses PubMedBERT and Bio_ClinicalBERT models trained on medical literature
- **Ontology Integration**: Extracts and preserves medical ontology codes (ICD-O, SNOMED-CT, MeSH)
- **Clinical Safety**: Implements safety scoring and medical disclaimer requirements
- **Audience Awareness**: Distinguishes between clinical practitioners and technical researchers
- **Domain Filtering**: Focuses retrieval on oncology-relevant content

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd RAG-ing

# Install dependencies
pip install -e .
# or
pip install -r requirements.txt
```

### 2. Configuration

The system is driven by a comprehensive YAML configuration file. Copy and customize:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
```

Key configuration sections:
- `data_sources`: Define your document sources
- `embedding_model`: Configure biomedical embedding models  
- `llm`: Set up KoboldCpp and fallback models
- `evaluation`: Enable metrics and logging

### 3. First Run

```bash
# Step 1: Ingest your corpus
python main.py --ingest

# Step 2: Launch the UI
python main.py --ui

# Alternative: Single query via CLI
python main.py --query "What are the latest treatment options for breast cancer?" --audience clinical
```

## 📋 Usage Examples

### Command Line Interface

```bash
# System status and health check
python main.py --status
python main.py --health-check

# Export session metrics
python main.py --export-metrics

# Custom configuration
python main.py --config custom-config.yaml --ui

# Debug mode
python main.py --debug --ingest
```

### Programmatic Usage

```python
from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator

# Load configuration
settings = Settings.from_yaml('./config.yaml')

# Initialize orchestrator
orchestrator = RAGOrchestrator(settings)

# Process corpus
results = orchestrator.process_corpus()

# Query the system
response = orchestrator.query_system(
    query="What are the side effects of immunotherapy?",
    audience="clinical"
)

print(response['response'])
```

## 📊 Configuration Reference

### Core Configuration Structure

```yaml
# Module 1: Corpus & Embedding
data_sources:
  - path: "./data/oncology-papers/"
    type: "directory"
    file_patterns: ["*.pdf", "*.txt"]

embedding_model:
  model_name: "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
  fallback_model: "sentence-transformers/all-MiniLM-L6-v2"

# Module 2: Query Processing
retrieval:
  top_k: 5
  similarity_threshold: 0.7
  retrieval_strategy: "hybrid"

# Module 3: LLM Orchestration  
llm:
  primary_model:
    provider: "koboldcpp"
    base_url: "http://localhost:5001"

# Module 4: UI Layer
ui:
  audience_toggle:
    enabled: true
    default_audience: "clinical"

# Module 5: Evaluation & Logging
evaluation:
  metrics:
    precision_at_k: true
    citation_coverage: true
    safety: true
```

### Environment Variables

Set these environment variables for API access:

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"  
export KOBOLD_API_KEY="your-kobold-key"
export DATA_DIR="./data"
export LOGS_DIR="./logs"
```

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

## 🔧 Development

### Project Structure

```
RAG-ing/
├── config.yaml                 # Main configuration file
├── main.py                    # CLI entry point
├── src/rag_ing/
│   ├── config/
│   │   └── settings.py        # YAML configuration management
│   ├── modules/               # 5 core modules
│   │   ├── corpus_embedding.py
│   │   ├── query_retrieval.py
│   │   ├── llm_orchestration.py
│   │   ├── ui_layer.py
│   │   └── evaluation_logging.py
│   ├── orchestrator.py        # Main coordinator
│   ├── utils/
│   │   └── exceptions.py      # Custom exceptions
│   └── cli.py                # CLI interface
├── tests/                     # Test suite
├── data/                     # Document storage
└── logs/                     # Application logs
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_structure.py -v

# Run with coverage
pytest tests/ --cov=src/rag_ing --cov-report=html
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

### RAGOrchestrator Class

```python
class RAGOrchestrator:
    def __init__(self, config: Settings)
    def process_corpus(self) -> Dict[str, Any]
    def query_system(self, query: str, audience: str) -> Dict[str, Any]
    def submit_feedback(self, query_hash: str, feedback: Dict) -> Dict
    def get_system_status(self) -> Dict[str, Any]
    def health_check(self) -> Dict[str, Any]
```

### Module Interfaces

Each module implements a consistent interface:
- Configuration-driven initialization
- Comprehensive error handling  
- Performance metrics tracking
- Structured logging

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

- Built on LangChain framework
- Uses Streamlit for UI components  
- Integrates PubMedBERT for biomedical embeddings
- Supports KoboldCpp for local LLM deployment

---

**🔬 Specialized for Oncology Research and Clinical Decision Support**