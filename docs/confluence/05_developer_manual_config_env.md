# Developer Manual: Configuration and Environment Setup

## Overview

This manual provides comprehensive guidance for configuring and deploying the RAG-ing system using `config.yaml` and `.env` files.

**Target Audience**: Developers, DevOps engineers, system administrators  
**Prerequisites**: Python 3.9+, Azure OpenAI access, Git  
**Setup Time**: 15-30 minutes

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/RAG-ing.git
cd RAG-ing
```

### 2. Install Dependencies
```bash
pip install -e .
```

### 3. Configure Environment
```bash
cp env.example .env
# Edit .env with your credentials
```

### 4. Configure Data Sources
```bash
# Edit config.yaml with your source settings
```

### 5. Run Ingestion
```bash
python main.py --ingest
```

### 6. Launch UI
```bash
python main.py --ui
# Access: http://localhost:8000
```

---

## Configuration Files

### config.yaml (Single Source of Truth)

**Location**: `./config.yaml` (repository root)

**Purpose**: Controls all system behavior without code changes

**Structure**: 8 main sections, 310 lines total

**Validation**: Automatic via Pydantic models on startup

### .env (Secrets and Credentials)

**Location**: `./` (repository root, gitignored)

**Purpose**: Store sensitive credentials outside version control

**Template**: `env.example` provided

**Loading**: Automatic via `python-dotenv`

---

## Section 1: Data Sources

### Configuration Block

```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true
      path: "./data/"
      file_types: [".txt", ".md", ".pdf", ".docx", ".html"]
      
    - type: "azure_devops"
      enabled: true
      azure_devops:
        organization: "${AZURE_DEVOPS_ORG}"
        project: "${AZURE_DEVOPS_PROJECT}"
        pat_token: "${AZURE_DEVOPS_PAT}"
        repo_name: "${AZURE_DEVOPS_REPO}"
        branch: "main"
        include_paths: ["/models", "/macros"]
        exclude_paths: ["/tests/fixtures"]
        include_file_types: [".sql", ".py", ".yml"]
        exclude_file_types: [".gitignore", ".md"]
        fetch_commit_history: true
        commits_per_file: 10
        enable_streaming: true
        batch_size: 50
        
    - type: "confluence"
      enabled: false  # Planned, not fully tested
      confluence:
        base_url: "${CONFLUENCE_BASE_URL}"
        username: "${CONFLUENCE_USERNAME}"
        auth_token: "${CONFLUENCE_API_TOKEN}"
        space_keys: ["ENG", "DOCS"]
        page_filter: ["Architecture", "API"]
        max_pages: 100
        
    - type: "jira"
      enabled: false  # Planned, not implemented
      jira:
        server_url: "${JIRA_URL}"
        username: "${JIRA_USER}"
        auth_token: "${JIRA_TOKEN}"
        project_keys: ["DATA", "ENG"]
        issue_types: ["Story", "Task", "Bug"]
        jql_filter: "project = DATA AND status != Closed"
        max_issues: 200
```

### Required Environment Variables

**For Azure DevOps**:
```bash
# .env file
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_DEVOPS_REPO=your-repository
```

**For Confluence** (optional):
```bash
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_api_token
```

**For Jira** (optional):
```bash
JIRA_URL=https://your-domain.atlassian.net
JIRA_USER=your-email@company.com
JIRA_TOKEN=your_api_token
```

### Configuration Options

#### Local File Loader

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | required | Must be "local_file" |
| `enabled` | boolean | required | Enable/disable source |
| `path` | string | "./data/" | Directory to scan |
| `file_types` | list | [".txt", ".md"] | Allowed file extensions |

**Example**: Ingest only PDFs from `./documents/`:
```yaml
- type: "local_file"
  enabled: true
  path: "./documents/"
  file_types: [".pdf"]
```

#### Azure DevOps Connector

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `organization` | string | required | Azure DevOps org name |
| `project` | string | required | Project name |
| `pat_token` | string | required | Personal Access Token |
| `repo_name` | string | required | Repository name |
| `branch` | string | "main" | Branch to fetch from |
| `include_paths` | list | [] | Only these paths (e.g., "/models") |
| `exclude_paths` | list | [] | Skip these paths (e.g., "/tests") |
| `include_file_types` | list | [] | Only these extensions |
| `exclude_file_types` | list | [] | Skip these extensions |
| `fetch_commit_history` | boolean | false | Include commit metadata |
| `commits_per_file` | int | 10 | Number of commits to fetch |
| `enable_streaming` | boolean | true | Process in batches |
| `batch_size` | int | 50 | Files per batch |

**Example**: Ingest SQL models only from dbt project:
```yaml
- type: "azure_devops"
  enabled: true
  azure_devops:
    organization: "my-org"
    project: "analytics"
    pat_token: "${AZURE_DEVOPS_PAT}"
    repo_name: "dbt-models"
    branch: "main"
    include_paths: ["/models/staging", "/models/marts"]
    include_file_types: [".sql"]
    fetch_commit_history: false  # Faster without commits
```

---

## Section 2: Chunking Strategy

### Configuration Block

```yaml
chunking:
  strategy: "recursive"      # Options: recursive, semantic
  chunk_size: 1200           # Characters per chunk
  overlap: 100               # Character overlap between chunks
  prepend_metadata: true     # Add source info to chunks
  chunk_size_includes_metadata: false
```

### Chunking Strategies

#### Recursive (Default)

**Algorithm**: Split on paragraphs → sentences → words → characters

**Use Case**: General text documents, markdown, documentation

**Example**:
```yaml
chunking:
  strategy: "recursive"
  chunk_size: 1500  # Larger for more context
  overlap: 150
```

#### Semantic

**Algorithm**: Split at semantic boundaries (headers, sections)

**Use Case**: Well-structured documents with clear sections

**Example**:
```yaml
chunking:
  strategy: "semantic"
  chunk_size: 2000
  overlap: 0  # Semantic boundaries don't need overlap
```

### Tuning Guidelines

| Corpus Type | Recommended chunk_size | Recommended overlap |
|-------------|------------------------|---------------------|
| Short docs (< 1 page) | 800-1000 | 50-100 |
| Medium docs (1-5 pages) | 1200-1500 | 100-150 |
| Long docs (> 5 pages) | 1500-2000 | 150-200 |
| Code files | 1000-1200 | 50 |

**Trade-offs**:
- **Smaller chunks**: More precise retrieval, but less context
- **Larger chunks**: More context, but slower embedding/retrieval
- **More overlap**: Better boundary handling, but more storage

---

## Section 3: Embedding Model

### Configuration Block

```yaml
embedding_model:
  provider: "azure_openai"          # Options: azure_openai, huggingface
  azure_model: "text-embedding-ada-002"
  azure_endpoint: "${AZURE_OPENAI_EMBEDDING_ENDPOINT}"
  azure_api_key: "${AZURE_OPENAI_EMBEDDING_API_KEY}"
  azure_deployment_name: "text-embedding-ada-002"
  azure_api_version: "2023-05-15"
  fallback_model: "all-MiniLM-L6-v2"
  device: "cpu"                     # Options: cpu, cuda
  use_azure_primary: true
```

### Required Environment Variables

```bash
# .env file
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_API_KEY=your_embedding_api_key
AZURE_OPENAI_EMBEDDING_API_VERSION=2023-05-15
```

### Model Options

#### Azure OpenAI (Recommended)

**Model**: `text-embedding-ada-002`
- **Dimensions**: 1,536
- **Max Input**: 8,191 tokens (~32,000 characters)
- **Cost**: $0.0001 per 1K tokens
- **Pros**: High quality, production-grade
- **Cons**: Requires Azure subscription

**Alternative Model**: `text-embedding-3-large`
- **Dimensions**: 3,072 (higher quality)
- **Cost**: $0.00013 per 1K tokens

```yaml
embedding_model:
  provider: "azure_openai"
  azure_model: "text-embedding-3-large"
  # ... rest of config
```

#### HuggingFace (Fallback)

**Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Max Input**: 512 tokens (~2,000 characters)
- **Cost**: Free (local execution)
- **Pros**: No API dependency, air-gapped deployments
- **Cons**: Lower quality, requires chunking for long docs

```yaml
embedding_model:
  provider: "huggingface"
  fallback_model: "all-MiniLM-L6-v2"
  device: "cuda"  # Use GPU if available
```

**Warning**: Switching embedding models requires **re-ingesting entire corpus** (embeddings not compatible)

---

## Section 4: Vector Store

### Configuration Block

```yaml
vector_store:
  type: "chroma"                    # Options: chroma, faiss
  path: "./vector_store"
  collection_name: "rag_documents"
  summary_collection: "rag_documents_summaries"
  
  chroma:
    persist_directory: "./vector_store"
    
  faiss:
    index_path: "./vector_store/faiss_index.bin"
    index_type: "IndexFlatL2"      # Options: IndexFlatL2, IndexIVFFlat
```

### Vector Store Options

#### ChromaDB (Default)

**Use When**:
- Corpus < 50,000 documents
- Need metadata filtering
- Prefer simplicity

**Pros**:
- Easy setup (no configuration)
- Built-in metadata storage
- Persistent storage

**Cons**:
- Slower for large corpuses (> 50K docs)
- Query latency ~100-200ms

```yaml
vector_store:
  type: "chroma"
  path: "./vector_store"
  collection_name: "rag_documents"
```

#### FAISS (Advanced)

**Use When**:
- Corpus > 50,000 documents
- Need sub-10ms query latency
- High query volume (> 100 QPS)

**Pros**:
- Very fast queries (< 10ms)
- Optimized for scale
- GPU acceleration support

**Cons**:
- More complex setup
- No built-in metadata (need separate DB)
- Requires separate persistence logic

```yaml
vector_store:
  type: "faiss"
  faiss:
    index_path: "./vector_store/faiss_index.bin"
    index_type: "IndexIVFFlat"  # Faster than IndexFlatL2
    nlist: 100  # Number of clusters
    nprobe: 10  # Number of clusters to search
```

---

## Section 5: Retrieval Configuration

### Configuration Block

```yaml
retrieval:
  top_k: 5
  strategy: "hybrid"                # Options: hybrid, semantic, keyword
  hybrid_search:
    enabled: true
    semantic_weight: 0.6
    keyword_weight: 0.4
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20
    top_k_final: 5
    relevance_threshold: 0.3
  domain_boost:
    enabled: true
    boost_multiplier: 1.5
    code_patterns:
      - "ERR-\\d{3,6}"
      - "TICKET-\\d+"
      - "v\\d+\\.\\d+\\.\\d+"
```

### Retrieval Strategies

#### Hybrid Search (Recommended)

Combines semantic (vector) and keyword (BM25) search

```yaml
retrieval:
  strategy: "hybrid"
  hybrid_search:
    semantic_weight: 0.6  # 60% weight to vector similarity
    keyword_weight: 0.4   # 40% weight to keyword matching
```

**Tuning**:
- **More semantic** (0.7/0.3): Conceptual questions, paraphrases
- **More keyword** (0.4/0.6): Technical terms, exact matches
- **Balanced** (0.6/0.4): General use (default)

#### Semantic Only

Pure vector similarity search

```yaml
retrieval:
  strategy: "semantic"
  hybrid_search:
    enabled: false
```

**Use Case**: Natural language queries, broad conceptual search

#### Keyword Only

Pure BM25 term matching

```yaml
retrieval:
  strategy: "keyword"
  hybrid_search:
    enabled: false
```

**Use Case**: Exact term lookup, technical documentation

### Cross-Encoder Reranking

**Purpose**: Improve precision by rescoring top results

**Configuration**:
```yaml
reranking:
  enabled: true
  model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
  top_k_initial: 20    # Fetch 20 docs
  top_k_final: 5       # Rerank to top 5
  relevance_threshold: 0.3  # Drop docs below this score
```

**Cost**: +50ms latency, +5-10% accuracy

**When to Enable**:
- ✓ Accuracy-critical applications (compliance, legal)
- ✓ Low query volume (< 10 QPS)
- ✗ Real-time requirements (< 100ms)
- ✗ High query volume (> 100 QPS)

### Domain Boosting

**Purpose**: Boost documents containing specific patterns (error codes, versions)

```yaml
domain_boost:
  enabled: true
  boost_multiplier: 1.5
  code_patterns:
    - "ERR-\\d{3,6}"      # ERR-12345
    - "TICKET-\\d+"       # TICKET-999
    - "v\\d+\\.\\d+"      # v1.2.3
```

**Example**: Query "Fix ERR-12345" will boost docs containing that error code by 1.5x

---

## Section 6: LLM Configuration

### Configuration Block

```yaml
llm:
  provider: "azure_openai"
  model: "gpt-4"
  azure_endpoint: "${AZURE_OPENAI_API_BASE}"
  azure_api_key: "${AZURE_OPENAI_API_KEY}"
  azure_deployment_name: "gpt-4"
  azure_api_version: "2023-05-15"
  max_context_tokens: 6000
  prompt_template: "./prompts/general.txt"
  temperature: 0.1
  fallback:
    enabled: true
    provider: "koboldcpp"
    endpoint: "http://localhost:5001/api/v1/generate"
```

### Required Environment Variables

```bash
# .env file
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_llm_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

### Model Options

#### Azure OpenAI (Primary)

**Model**: `gpt-4`
- **Context**: 8K tokens
- **Cost**: $0.03/1K prompt tokens, $0.06/1K completion
- **Quality**: Highest

**Model**: `gpt-4o` (Optimized)
- **Context**: 128K tokens
- **Cost**: $0.005/1K prompt tokens, $0.015/1K completion
- **Quality**: High, faster

```yaml
llm:
  provider: "azure_openai"
  model: "gpt-4o"  # Cheaper, faster alternative
```

#### KoboldCpp (Fallback)

**Use Case**: Local deployment, air-gapped environments

```yaml
llm:
  fallback:
    enabled: true
    provider: "koboldcpp"
    endpoint: "http://localhost:5001/api/v1/generate"
    model: "mistral-7b"
```

**Setup**:
```bash
# Download KoboldCpp
git clone https://github.com/LostRuins/koboldcpp
cd koboldcpp
python koboldcpp.py --model mistral-7b-instruct.gguf --port 5001
```

### Prompt Template

**Location**: `./prompts/general.txt`

**Purpose**: Define LLM behavior and strict grounding rules

**Critical Rule**: LLM MUST answer only from provided context

**Template Structure**:
```
SYSTEM INSTRUCTION:
You are a helpful assistant that answers questions STRICTLY based on the provided context.
Never use external knowledge. If information is not in the context, say so explicitly.

CONTEXT:
{context}

USER QUERY:
{query}

INSTRUCTIONS:
- Answer only from context
- Cite sources with [Document X]
- If answer not in context, suggest related topics that ARE in context
- Provide rephrased question suggestions
```

**Custom Templates**: Create new files in `./prompts/` and reference in config:
```yaml
llm:
  prompt_template: "./prompts/custom_domain.txt"
```

---

## Section 7: Duplicate Detection

### Configuration Block

```yaml
duplicate_detection:
  enabled: true
  database_path: "./vector_store/document_hashes.db"
  method: "exact"              # Options: exact, fuzzy, semantic
  fuzzy_threshold: 95          # For fuzzy matching (0-100)
  semantic_threshold: 0.98     # For semantic matching (0-1)
```

### Detection Methods

#### Exact (Recommended)

**Algorithm**: SHA256 content hash

**Pros**: Fast, deterministic  
**Cons**: Misses near-duplicates

```yaml
duplicate_detection:
  enabled: true
  method: "exact"
```

#### Fuzzy

**Algorithm**: Levenshtein distance string similarity

**Pros**: Catches near-duplicates (typo fixes, minor edits)  
**Cons**: Slow for large corpuses

```yaml
duplicate_detection:
  enabled: true
  method: "fuzzy"
  fuzzy_threshold: 95  # 95% similarity = duplicate
```

#### Semantic

**Algorithm**: Embedding cosine similarity

**Pros**: Detects semantic duplicates (rewrites, paraphrases)  
**Cons**: Expensive (requires embedding)

```yaml
duplicate_detection:
  enabled: true
  method: "semantic"
  semantic_threshold: 0.98  # 98% similarity = duplicate
```

---

## Section 8: Logging and Evaluation

### Configuration Block

```yaml
logging:
  log_directory: "./logs"
  log_level: "INFO"            # Options: DEBUG, INFO, WARNING, ERROR
  structured_logs: true
  
evaluation:
  enabled: true
  metrics:
    - "hit_rate"
    - "context_precision"
    - "safety_score"
    - "clarity"
  log_file: "./logs/evaluation.jsonl"
```

### Log Files

**Location**: `./logs/`

**Files**:
- `evaluation.jsonl` - Complete query events
- `retrieval_metrics.jsonl` - Retrieval performance
- `generation_metrics.jsonl` - LLM response quality

**Format**: JSONL (JSON Lines, one object per line)

**Example**:
```json
{"query_hash": "abc123", "query": "What is dbt?", "retrieval_time": 0.15, "hit_rate": 1.0, "timestamp": "2025-11-26T10:30:00"}
```

---

## Environment Variables Reference

### Complete .env Template

```bash
# Azure OpenAI - Embedding
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_API_KEY=your_embedding_api_key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_EMBEDDING_API_VERSION=2023-05-15

# Azure OpenAI - LLM
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_llm_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2023-05-15

# Azure DevOps (Optional)
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_PAT=your_personal_access_token
AZURE_DEVOPS_REPO=your-repository

# Confluence (Optional)
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_confluence_token

# Jira (Optional)
JIRA_URL=https://your-domain.atlassian.net
JIRA_USER=your-email@company.com
JIRA_TOKEN=your_jira_token
```

### Security Best Practices

1. **Never commit `.env` to version control**
   - Already in `.gitignore`
   - Use `env.example` as template

2. **Rotate keys regularly**
   - Azure OpenAI keys: every 90 days
   - PAT tokens: every 180 days

3. **Use least-privilege access**
   - Azure DevOps PAT: `Code (Read)` scope only
   - Jira/Confluence: Read-only API tokens

4. **Encrypt secrets in production**
   - Use Azure Key Vault
   - Or environment-specific secret managers

---

## Troubleshooting

### Issue 1: Missing Environment Variables

**Error**: `KeyError: 'AZURE_OPENAI_EMBEDDING_ENDPOINT'`

**Solution**:
```bash
# Verify .env file exists
ls -la .env

# Check variable is set
grep AZURE_OPENAI_EMBEDDING_ENDPOINT .env

# Load environment
source .env  # or restart Python process
```

### Issue 2: Configuration Validation Failed

**Error**: `ValidationError: Invalid configuration`

**Solution**:
```bash
# Validate config
python main.py --validate-config

# Check for typos, required fields
# Ensure YAML syntax is correct (indentation!)
```

### Issue 3: Azure OpenAI Connection Failed

**Error**: `HTTP 401 Unauthorized` or `Connection timeout`

**Solution**:
```bash
# Test endpoint
curl -X POST "${AZURE_OPENAI_EMBEDDING_ENDPOINT}/openai/deployments/text-embedding-ada-002/embeddings?api-version=2023-05-15" \
  -H "api-key: ${AZURE_OPENAI_EMBEDDING_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'

# Check:
# - Endpoint URL correct (must end with /)
# - API key valid (check Azure portal)
# - Deployment name matches config
```

---

## Common Configuration Patterns

### Pattern 1: Development Environment

**Goal**: Fast ingestion, local files only, debug logging

```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true
      path: "./data"

chunking:
  chunk_size: 800  # Smaller for faster embedding

vector_store:
  type: "chroma"

retrieval:
  reranking:
    enabled: false  # Skip for speed

logging:
  log_level: "DEBUG"
```

### Pattern 2: Production Environment

**Goal**: All sources, high accuracy, metrics enabled

```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true
    - type: "azure_devops"
      enabled: true
    - type: "confluence"
      enabled: true

chunking:
  chunk_size: 1500  # More context

retrieval:
  reranking:
    enabled: true  # Higher accuracy
    top_k_final: 5

evaluation:
  enabled: true
  metrics:
    - "hit_rate"
    - "context_precision"
    - "safety_score"

logging:
  log_level: "INFO"
```

### Pattern 3: Air-Gapped Environment

**Goal**: No external APIs, local models only

```yaml
embedding_model:
  provider: "huggingface"
  fallback_model: "all-MiniLM-L6-v2"
  device: "cuda"  # Use GPU

llm:
  provider: "koboldcpp"
  fallback:
    enabled: true
    endpoint: "http://localhost:5001/api/v1/generate"

data_source:
  sources:
    - type: "local_file"
      enabled: true
```

---

## Summary

This developer manual covers:
- ✓ Complete `config.yaml` reference (8 sections)
- ✓ `.env` environment variables (all required + optional)
- ✓ Configuration options and tuning guidelines
- ✓ Troubleshooting common issues
- ✓ Configuration patterns for different environments

**Next Steps**: See other Confluence pages for architecture details, retrieval techniques, and UI components.
