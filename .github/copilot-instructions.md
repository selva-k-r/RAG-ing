# RAG-ing Codebase Guide for AI Coding Agents

## Project Status: Production-Ready General-Purpose RAG System

**Current Version**: Generalized, Domain-Agnostic RAG System  
**Status**: Production-Ready ✓  
**Last Major Update**: 2025-11-22 (Generalization & Quality Improvements)

**Important rule : Always architect the solution and discuss with me before implementation, You can propose multiple approaches and we will decide together before coding.**

### What This System Does

A general-purpose Retrieval-Augmented Generation (RAG) system that:
- Ingests documents from multiple sources (Azure DevOps, Confluence, Local files)
- Creates searchable embeddings with Azure OpenAI
- **Answers questions STRICTLY based on provided documents** (no hallucination)
- Provides helpful rephrasing suggestions when information is not available
- Supports batch processing, incremental updates, and commit history tracking

---

## Architecture Overview

**5-Module Production Architecture**:

- **Module 1**: `corpus_embedding.py` - Multi-source document ingestion (Azure DevOps, Confluence, Local)
- **Module 2**: `query_retrieval.py` - Hybrid retrieval with semantic search and metadata filtering
- **Module 3**: `llm_orchestration.py` - Azure OpenAI integration with multi-provider fallback
- **Module 4**: Modular FastAPI UI in `ui/` directory - Complete web interface
- **Module 5**: `evaluation_logging.py` - Real-time performance tracking and structured logging

The `orchestrator.py` coordinates all modules using **YAML-driven configuration** via Pydantic models in `config/settings.py`.

---

## Quick Start (3 Steps)

```bash
# Step 1: Install dependencies
pip install -e .

# Step 2: Process your documents (REQUIRED first step)
python main.py --ingest

# Step 3: Launch the FastAPI web interface
python main.py --ui
```

**Access**: Open http://localhost:8000 in your browser

---

## Critical System Characteristics

### 1. Strict Document Grounding (NO HALLUCINATION)
**ALL prompts enforce this rule**:
- Answer ONLY from provided context
- NEVER use external knowledge
- If answer NOT in context, system MUST:
  ```
  "I cannot find information about [topic] in the available documents.
  
  However, I found related information about [closest topic from context].
  
  You might want to rephrase your question as: '[suggested question]'"
  ```

### 2. Domain-Agnostic Design
- **Was**: Oncology/medical-focused system
- **Now**: Generic RAG applicable to ANY domain
- Collection name: `rag_documents` (was `oncology_docs`)
- Prompts: `prompts/general.txt` (was `prompts/oncology.txt`)
- Code extraction: Generic patterns (error codes, tickets, versions) instead of medical codes

### 3. Production Code Quality
- **NO EMOJIS** in production code (encoding issues on Windows)
- ASCII-safe logging: `[OK]`, `[X]`, `[!]` instead of emojis
- Comments describe CURRENT implementation (not history - git tracks that)
- Error messages are polite + include system error codes + provide solutions

---

## Configuration System

**Everything is driven by `config.yaml`** - single source of truth:

```yaml
# Key sections
data_source:
  azure_devops:
    enabled: true
    include_paths: ["/models", "/macros"]
    exclude_paths: ["/tests"]
    include_file_types: [".sql", ".yml"]
    exclude_file_types: [".md", ".txt"]
    fetch_commit_history: true
    commits_per_file: 10
    batch_size: 50

vector_store:
  type: "chroma"
  collection_name: "rag_documents"  # Generic, not domain-specific

llm:
  prompt_template: "./prompts/general.txt"  # Generic prompt
  system_instruction: "Answer STRICTLY from context..."  # Strict grounding
```

### Configuration Loading
```python
# Always load settings first
settings = Settings.from_yaml('./config.yaml')
orchestrator = RAGOrchestrator(settings)
```

---

## Entry Points & Workflows

### Primary Entry Point
- `main.py` - CLI with extensive help text
- `python main.py --ingest` - Process corpus and build vectors
- `python main.py --ui` - Launch FastAPI web interface
- `python main.py --query "text"` - Single query

### Development Workflow
1. **First run**: Always `--ingest` to process documents
2. **Configuration changes**: Restart required
3. **Testing**: Use `pytest tests/`
4. **UI Development**: Edit files in `ui/` directory
5. **Debugging**: `--debug` flag enables comprehensive logging

---

## Coding Standards (CRITICAL)

### 1. NO EMOJIS in Production Code

**Rule**: Emojis are **PROHIBITED** in all Python files, log messages, and error messages.

**Why**:
- Cause `UnicodeEncodeError` on Windows terminals
- Complicate log parsing
- Not professional for production code

**Allowed**: Markdown documentation files only (README.md, guides)

**Use Instead**:
```python
# Good - ASCII-safe status indicators
logger.info("[OK] Processing completed successfully")
logger.error("[X] Connection failed")
logger.warning("[!] Rate limit approaching")
print("[OK] Ingestion complete: 552 files")

# Bad - Emojis cause encoding errors
logger.info("✅ Processing completed")
logger.error("❌ Connection failed")
```

### 2. Comment Philosophy: Current State, Not History

**Good** - Describes what code does NOW:
```python
# Retry connection up to 3 times with exponential backoff
# Retries: 3 attempts with wait times of 1s, 2s, 4s
# Returns: Response object if successful
# Raises: RequestException after all retries exhausted
def fetch_with_retry(url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return requests.get(url, timeout=10)
        except requests.RequestException as e:
            if attempt == max_attempts - 1:
                raise
            wait_time = 2 ** attempt
            time.sleep(wait_time)
```

**Bad** - Historical explanations:
```python
# We used to use 5 retries but changed to 3 because it was too slow
# TODO: Maybe increase this later (added 6 months ago)
# NOTE: This was John's idea from the meeting
def fetch_with_retry(url):
    for i in range(3):  # Used to be 5
        ...
```

**Remember**: Git tracks history. Comments should help developers understand current implementation.

### 3. Error Messages: Polite + System Error + Solution

**Good**:
```python
try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError as e:
    print(f"Configuration Error: File not found at '{config_path}'")
    print(f"System Error: [Errno {e.errno}] {e.strerror}")
    print(f"")
    print(f"Please ensure the file exists or provide correct path:")
    print(f"  - Check current directory: {os.getcwd()}")
    print(f"  - Set CONFIG_PATH environment variable")
    print(f"  - Use --config flag to specify path")
    sys.exit(1)
```

**Bad**:
```python
except FileNotFoundError:
    print("Can't find file!")
    sys.exit(1)
```

### 4. Log Messages: Direct and Informative

```python
# Good - Direct, informative, ASCII-safe
logger.info("Starting Azure DevOps file ingestion")
logger.info(f"Repository: {repo_name}, Branch: {branch}")
logger.info(f"Fetched batch 1/10: 50 files")
logger.info(f"Ingestion complete: 552 files processed in 45.2s")

# Clear warnings
logger.warning("Skipping 3 files with unsupported encoding")
logger.warning(f"File too large: {file_path} ({file_size} MB > 10 MB limit)")

# Actionable errors
logger.error(f"Failed to fetch file: {file_path}")
logger.error(f"API Error: HTTP 404 - File not found in repository")
```

---

## Key Implementation Changes (Generalization)

### Domain-Specific Code Removed

**Before (Oncology-Focused)**:
```python
# Extract medical codes
def _extract_ontology_codes(content):
    # ICD-O codes, MeSH terms, TNM staging
    codes = re.findall(r'C\d{2}\.\d', content)
    ...

# Semantic boundaries
boundaries = ["## Diagnosis", "## Treatment", "## Biomarkers"]

# Test embedding
embedding = model.embed_query("oncology biomarker test")

# Audience
audience = "clinical"  # vs "technical"
```

**After (Generic)**:
```python
# Extract generic domain codes
def _extract_domain_codes(content):
    # Error codes, ticket IDs, version numbers
    codes = re.findall(r'ERR(?:OR)?[-_]?\d{3,6}', content)
    ...

# Generic semantic boundaries
boundaries = ["## ", "### ", "# ", "\n\n"]  # Markdown headers, paragraphs

# Test embedding
embedding = model.embed_query("document embedding test")

# Audience
audience = "general"  # vs "technical"
```

### Vector Store Changes
```yaml
# Before
collection_name: "oncology_docs"
summary_collection: "oncology_docs_summaries"

# After
collection_name: "rag_documents"
summary_collection: "rag_documents_summaries"
```

### Prompt Changes
- **Removed**: `prompts/oncology.txt`
- **Added**: `prompts/general.txt` with strict grounding
- **Updated**: All prompts enforce document-only answers

---

## Module Communication Patterns

### Data Flow
```
User Query → Orchestrator → Module 2 (retrieval) → Module 3 (LLM) → Module 5 (logging)
                          ↓
            Module 1 (corpus) stores embeddings used by Module 2
                          ↓
            Module 4 (UI) displays results
```

### Error Handling
- Custom `RAGError` exceptions in `utils/exceptions.py`
- Each module implements graceful degradation
- System-level metrics tracking in Module 5
- Retry logic built into LLM orchestration

---

## Vector Storage & LLM Integration

### Vector Storage
- ChromaDB default, FAISS alternative
- Collection name: "rag_documents" (generic, configurable)
- Metadata preserved: source, domain codes, timestamps

### LLM Integration  
- Azure OpenAI as primary (gpt-4/gpt-4o)
- Fallback chain: OpenAI → Anthropic → KoboldCpp
- Prompt templates in `./prompts/` directory
- **Strict grounding enforced in all prompts**

### Logging & Metrics
- Structured JSON logs in `./logs/` directory
- Session-based tracking with export capabilities
- Real-time performance metrics
- User feedback correlation via query hashes

---

## Development Guidelines

### Adding New Features
1. **Configuration first**: Add to relevant Pydantic model in `settings.py`
2. **Module isolation**: Keep modules independent, communicate via orchestrator
3. **YAML-driven**: All behavior should be configurable via `config.yaml`
4. **Logging**: Use Module 5 for metrics tracking
5. **NO EMOJIS**: Use ASCII-safe characters only

### Code Quality Checklist
- [ ] No emojis in code, logs, or error messages
- [ ] Comments describe current implementation (not history)
- [ ] Error messages include: what failed + system error + how to fix
- [ ] Log messages are direct and informative
- [ ] Strict grounding enforced in any LLM prompts
- [ ] Generic/domain-agnostic code (no medical/clinical assumptions)

### Testing Patterns
- Structure tests validate file existence
- Mock heavy dependencies (embedding models, external APIs)
- Test configuration loading separately from module functionality

### Common Gotchas
- **Path handling**: Use absolute paths, relative to project root
- **Environment variables**: Use `${VAR}` syntax in YAML for secrets
- **Module imports**: Follow the pattern in `modules/__init__.py`
- **Emoji encoding**: Will break on Windows - NEVER use in code
- **Hallucination prevention**: Always enforce strict grounding in prompts

---

## Docker Deployment

### Quick Commands
```bash
# Fastest start
docker-compose -f docker-compose.minimal.yml up --build

# With data persistence
docker-compose up --build

# Using deploy script
./docker/deploy.sh build && ./docker/deploy.sh start
```

---

## UI Architecture (Module 4)

### Current: Modular FastAPI Structure
- **`ui/app.py`**: Main FastAPI application
- **`ui/api/routes.py`**: RESTful API endpoints
- **`ui/api/pages.py`**: HTML page generation
- **`ui/templates/`**: Jinja2 templates
- **`ui/static/`**: CSS, JavaScript

### Launch Mechanism
```python
# From orchestrator.py
def run_web_app(self) -> None:
    subprocess.run([sys.executable, "ui/app.py"], check=True)
```

---

## Development Philosophy for AI Agents

**CRITICAL Principles**:

1. **Start Simple**: Begin with the simplest solution
2. **Small Changes**: Humanly reviewable chunks to avoid brain fatigue
3. **Break Down Problems**: Solve one piece at a time
4. **Educational Focus**: Maintainer wants to learn Python:
   - Explain all changes clearly
   - Add comments for debugging
   - Document "why" behind library choices
   - Show Python patterns and best practices

5. **NO EMOJIS**: NEVER add emojis to Python files - causes encoding errors
6. **Strict Grounding**: ALWAYS enforce document-only answers in LLM prompts
7. **Generic Code**: Avoid domain-specific assumptions (medical, clinical, etc.)

### Example Approach
```python
# Good: Small, commented, ASCII-safe change
def process_query(self, query: str) -> Dict:
    """Process user query with error handling.
    
    Args:
        query: User's question (string)
    Returns:
        Dict with response and metadata
    """
    # Step 1: Validate input
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Step 2: Generate embeddings
    embeddings = self._create_embeddings(query)
    
    logger.info("[OK] Query processed successfully")
    return {"embeddings": embeddings, "status": "success"}

# Bad: Large uncommented changes, emojis, multiple responsibilities
```

---

## Project Structure

```
RAG-ing/
├── src/rag_ing/          # Core application code
│   ├── connectors/       # Data source connectors (Azure DevOps, Confluence)
│   ├── modules/          # Core modules (embedding, LLM, retrieval)
│   ├── utils/            # Utilities (tracking, chunking, exceptions)
│   └── config/           # Configuration management
├── prompts/              # LLM prompt templates (generic, strict grounding)
│   ├── general.txt       # Default generic prompt (PRIMARY)
│   ├── simple.txt        # Simple style
│   ├── iconnect_concise.txt
│   └── iconnect_enterprise.txt
├── ui/                   # FastAPI web interface
├── tests/                # Unit tests
├── data/                 # Sample documents
├── vector_store/         # ChromaDB storage
├── logs/                 # Application logs
├── config.yaml           # Main configuration (SINGLE SOURCE OF TRUTH)
├── main.py               # Entry point
└── README.md             # Project documentation
```

---

## Summary: Key Takeaways for AI Agents

1. **System is generic** - works for ANY domain, not just medical/oncology
2. **Strict grounding enforced** - answers ONLY from documents, no external knowledge
3. **NO EMOJIS in code** - causes Windows encoding errors, use ASCII characters
4. **Comments = current state** - git tracks history, comments explain implementation
5. **Error messages = polite + system code + solution**
6. **Configuration-driven** - `config.yaml` controls everything
7. **Production-ready** - clean codebase, professional standards

When in doubt: Keep it simple, make it generic, avoid emojis, enforce grounding.
