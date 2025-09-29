# RAG-ing Codebase Guide for AI Coding Agents

## Architecture Overview

This is a **5-module oncology-focused RAG system** implementing a comprehensive retrieval-augmented generation pipeline. The architecture follows strict modular separation as defined in `src/Requirement.md`:

- **Module 1**: `corpus_embedding.py` - Document ingestion & biomedical embeddings (PubMedBERT/Bio_ClinicalBERT)
- **Module 2**: `query_retrieval.py` - Hybrid retrieval with ontology filtering (ICD-O, SNOMED-CT, MeSH)
- **Module 3**: `llm_orchestration.py` - KoboldCpp integration with fallback providers
- **Module 4**: `ui_layer.py` - Streamlit UI with clinical/technical audience toggle
- **Module 5**: `evaluation_logging.py` - Performance tracking & safety scoring

The `orchestrator.py` coordinates all modules, while `config/settings.py` provides YAML-driven configuration using Pydantic models.

## Quick Start (3 Steps)

For new developers or AI agents getting started:

```bash
# Step 1: Install dependencies
pip install -e .

# Step 2: Process your documents (REQUIRED first step)
python main.py --ingest

# Step 3: Launch the interface
python main.py --ui
```

**Why this order matters**: The system needs to build embeddings from your documents before it can answer questions. Think of Step 2 as "teaching the AI about your documents" and Step 3 as "asking questions about what it learned."

## Configuration System

**Everything is driven by `config.yaml`** - this is the single source of truth for all system behavior. The settings use Pydantic models with strict validation:

```python
# Always load settings first
settings = Settings.from_yaml('./config.yaml')
orchestrator = RAGOrchestrator(settings)
```

Key configuration sections:
- `data_source`: Local files vs Confluence connector
- `embedding_model`: Biomedical model selection (pubmedbert/clinicalbert)
- `llm`: KoboldCpp primary with OpenAI/Anthropic fallback
- `ui.audience_toggle`: Clinical vs technical response modes
- `evaluation.metrics`: Enable/disable specific tracking

## Entry Points & Workflows

### Primary Entry Point
- `main.py` - CLI with extensive help text and examples
- `python main.py --ingest` - Process corpus and build vectors
- `python main.py --ui` - Launch Streamlit interface
- `python main.py --query "text" --audience clinical` - Single query

### Development Workflow
1. **First run**: Always `--ingest` to process documents
2. **Configuration changes**: Restart required, no hot-reload
3. **Testing**: Use `pytest tests/` - structure tests expect specific file locations
4. **Debugging**: `--debug` flag enables comprehensive logging

## Domain-Specific Patterns

### Oncology Specialization
- **Embeddings**: Uses medical literature-trained models (PubMedBERT)
- **Ontology Integration**: Extracts ICD-O, SNOMED-CT, MeSH codes during chunking
- **Safety Scoring**: Module 5 calculates safety scores with medical disclaimers
- **Audience Awareness**: Clinical (simple) vs Technical (detailed) response modes

### Query Processing
- All queries go through the orchestrator's `query_documents()` method
- Creates query hash for tracking and feedback correlation
- Retrieval uses hybrid search with domain-specific filtering
- Safety scores are mandatory for all responses

## Module Communication Patterns

### Data Flow
```
User Query → Orchestrator → Module 2 (retrieval) → Module 3 (LLM) → Module 5 (logging)
                          ↓
            Module 1 (corpus) stores embeddings used by Module 2
                          ↓
            Module 4 (UI) displays results and collects feedback
```

### Error Handling
- Custom `RAGError` exceptions in `utils/exceptions.py`
- Each module implements graceful degradation
- System-level metrics tracking in Module 5
- Retry logic built into LLM orchestration

## Key Implementation Details

### Vector Storage
- ChromaDB default, FAISS alternative
- Collection name: "oncology_docs" (configurable)
- Metadata preserved: source, ontology codes, timestamps

### LLM Integration  
- KoboldCpp as primary (local deployment)
- Fallback chain: OpenAI → Anthropic
- Prompt templates in `./prompts/` directory
- Audience-specific system instructions

### Logging & Metrics
- Structured JSON logs in `./logs/` directory
- Session-based tracking with export capabilities
- Real-time performance metrics (precision@K, latency, safety)
- User feedback correlation via query hashes

## Development Guidelines

### Adding New Features
1. **Configuration first**: Add to relevant Pydantic model in `settings.py`
2. **Module isolation**: Keep modules independent, communicate via orchestrator
3. **YAML-driven**: All behavior should be configurable via `config.yaml`
4. **Logging**: Use Module 5 for any metrics or performance tracking

### Testing Patterns
- Structure tests in `tests/test_structure.py` validate file existence
- Mock heavy dependencies (embedding models, external APIs)
- Test configuration loading separately from module functionality

### Common Gotchas
- **Path handling**: Use absolute paths, relative to project root
- **Environment variables**: Use `${VAR}` syntax in YAML for secrets
- **Module imports**: Follow the pattern in `modules/__init__.py`
- **CLI vs programmatic**: Different entry points, same underlying orchestrator

This system prioritizes modularity, medical domain accuracy, and comprehensive evaluation over generic RAG patterns.

## Development Philosophy & AI Agent Guidelines

**CRITICAL**: Always follow these principles when working on this codebase:

1. **Start Simple**: Begin with the simplest solution that works
2. **Small Changes**: Limit modifications to humanly reviewable chunks to avoid brain fatigue
3. **Break Down Problems**: Split complex tasks into smaller, manageable pieces - solve one at a time
4. **Educational Focus**: The maintainer wants to learn Python proficiently, so:
   - Explain all changes clearly
   - Add comments to code for debugging purposes
   - Document the "why" behind Python library choices
   - Show Python patterns and best practices in action

**Example Approach**:
```python
# Good: Small, commented change
def process_query(self, query: str) -> Dict:
    """Process user query with error handling.
    
    Args:
        query: User's question (string)
    Returns:
        Dict with response and metadata
    """
    # Step 1: Validate input (common Python pattern)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Step 2: Generate embeddings (using your PubMedBERT model)
    embeddings = self._create_embeddings(query)
    return {"embeddings": embeddings, "status": "success"}

# Bad: Large uncommented changes with multiple responsibilities
```

When implementing features, always prefer iterative development with clear explanations over complex one-shot solutions.