# RAG-ing Project Overview (Confluence-Ready)

This page documents the RAG-ing system architecture, configuration (`config.yaml`), and required environment variables. It is intended for onboarding, operations, and platform teams.

---

## 1. System Overview

RAG-ing is a **general-purpose Retrieval-Augmented Generation (RAG)** system with:

- Multi-source ingestion (local files, Azure DevOps, Confluence, Jira)
- Azure OpenAI–backed embeddings and LLMs
- ChromaDB vector store
- FastAPI UI and API
- Strict context grounding (no hallucination by design)
- Evaluation and logging with JSON metrics

Core modules:

1. **Module 1 – Corpus & Embedding Lifecycle**
2. **Module 2 – Query Processing & Retrieval**
3. **Module 3 – LLM Orchestration**
4. **Module 4 – UI Layer**
5. **Module 5 – Evaluation & Logging**

High-level flow:

1. Documents ingested from configured sources → chunked → embedded
2. Embeddings stored in Chroma vector store; ingestion tracker records metadata
3. User queries go through hybrid retrieval + reranking
4. LLM generates answers strictly from retrieved context
5. Metrics and logs stored for monitoring and tuning

See the architecture markdowns under `docs/architecture/` for draw.io-ready flowcharts.

---

## 2. Configuration (`config.yaml`)

The project is fully driven by `config.yaml` at the repository root. Main sections are:

### 2.1 Data Sources (`data_source`)

```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true
      path: "./data/"
      file_types: [".txt", ".md", ".pdf", ".docx", ".html"]

    - type: "confluence"
      enabled: false
      confluence:
        base_url: "${CONFLUENCE_BASE_URL}"
        username: "${CONFLUENCE_USERNAME}"
        auth_token: "${CONFLUENCE_API_TOKEN}"
        space_keys: ["FHIR", "DOCS", "RESEARCH"]
        page_filter: ["Implementation", "Guide", "FHIR", "Clinical"]
        max_pages: 100

    - type: "jira"
      enabled: false
      jira:
        server_url: "${JIRA_URL}"
        username: "${JIRA_USER}"
        auth_token: "${JIRA_TOKEN}"
        project_keys: ["PROJECT1", "PROJECT2", "PROJECT3"]
        issue_types: ["Story", "Task", "Bug", "Epic", "Requirement"]
        jql_filter: "project in (PROJECT1, PROJECT2) AND status != Closed"
        max_issues: 200

    - type: "azure_devops"
      enabled: true
      azure_devops:
        organization: "${AZURE_DEVOPS_ORG}"
        project: "${AZURE_DEVOPS_PROJECT}"
        pat_token: "${AZURE_DEVOPS_PAT}"
        repo_name: "${AZURE_DEVOPS_REPO}"
        branch: "develop"
        include_paths:
          - "/path1"
        exclude_paths:
          - "/path1/tests/fixtures"
          - "/path1/libraries"
          - "/path1/.github"
        include_file_types:
          - ".sql"
          - ".py"
          - ".yaml"
          - ".yml"
          - ".md"
          - ".csv"
          - ".bim"
        exclude_file_types:
          - ".pbix"
          - ".dll"
          - ".sln"
          - ".smproj"
          - ".gitignore"
          - ".gitkeep"
        fetch_commit_history: true
        commits_per_file: 10
        enable_streaming: true
        batch_size: 50
```

**Key points:**
- **Enable/disable sources** via `enabled: true|false`.
- All secrets are referenced via `${ENV_VAR}` and must be set in the runtime environment (usually via `.env`).
- Azure DevOps source supports **path and file-type filtering**, **commit history**, and **batch processing**.

### 2.2 Chunking (`chunking`)

```yaml
chunking:
  strategy: "recursive"      # recursive | semantic
  chunk_size: 1200
  overlap: 100
  prepend_metadata: true
  chunk_size_includes_metadata: false
```

- Used by Module 1 to split documents into retrieval-sized pieces.
- Larger `chunk_size` preserves more context at the cost of more tokens.

### 2.3 Embedding Model (`embedding_model`)

```yaml
embedding_model:
  provider: "azure_openai"          # azure_openai | huggingface
  azure_model: "text-embedding-ada-002"
  azure_endpoint: "${AZURE_OPENAI_EMBEDDING_ENDPOINT}"
  azure_api_key: "${AZURE_OPENAI_EMBEDDING_API_KEY}"
  azure_deployment_name: "text-embedding-ada-002"
  azure_api_version: "${AZURE_OPENAI_EMBEDDING_API_VERSION}"
  fallback_model: "all-MiniLM-L6-v2"
  device: "cpu"
  use_azure_primary: true
```

- Primary embedding provider is **Azure OpenAI**.
- Falls back to **HuggingFace** model if Azure is unavailable.

### 2.4 Retrieval (`retrieval`)

```yaml
retrieval:
  top_k: 10
  strategy: "hybrid"            # semantic + BM25
  semantic_weight: 0.6
  keyword_weight: 0.4
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20
    top_k_final: 5
    relevance_threshold: 0.7
  max_context_tokens: 12000
  context_precision_threshold: 0.7
  query_enhancement:
    question_keywords_boost: 2.0
    date_keywords_boost: 1.8
    direct_answer_boost: 2.5
  domain_specific:
    medical_terms_boost: true
    ontology_codes_weight: 1.5
  filters:
    ontology_match: true
    date_range: "last_12_months"
```

- Controls **semantic vs keyword weighting**, cross-encoder reranking, and domain-specific boosts.
- `max_context_tokens` ensures context fits into the LLM token budget.

### 2.5 LLM Orchestration (`llm`)

```yaml
llm:
  model: "gpt-5-nano"
  provider: "azure_openai"          # azure_openai | koboldcpp
  max_tokens: 4096
  temperature: 0.2
  use_smart_truncation: true
  context_optimization: true
  token_buffer: 2000
  azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"
  azure_api_key: "${AZURE_OPENAI_API_KEY}"
  azure_api_version: "${AZURE_OPENAI_API_VERSION}"
  azure_deployment_name: "${AZURE_DEPLOYMENT_NAME}"
  api_url: "http://localhost:5000/v1"   # KoboldCpp fallback
  prompt_template: "./prompts/general.txt"
  system_instruction: "You are an AI assistant that provides clear, concise answers based STRICTLY on the provided context..."
  response_style: "concise"
  max_response_length: 300
  prioritize_direct_answers: true
  include_source_references: true
```

- Primary LLM provider is **Azure OpenAI**.
- Optional fallback to **KoboldCpp** for local development.
- System prompt strictly enforces **context-only answers**.

### 2.6 UI (`ui`)

```yaml
ui:
  framework: "fastapi"
  port: 8000
  host: "0.0.0.0"
  debug: false
  show_source_metadata: true
  enable_search_history: true
  response_streaming: false
```

- Controls FastAPI server binding and UI features.
- History + metadata are enabled; advanced personalization is on the roadmap.

### 2.7 Evaluation & Logging (`evaluation`)

```yaml
evaluation:
  ragas:
    enabled: true
    context_precision: true
    context_recall: true
    faithfulness: true
    answer_relevancy: true
    answer_similarity: true
    answer_correctness: true
    thresholds:
      context_precision: 0.75
      context_recall: 0.70
      faithfulness: 0.85
      answer_relevancy: 0.80
      answer_similarity: 0.80
      answer_correctness: 0.70
  continuous:
    enabled: true
    batch_size: 10
    evaluation_interval: 100
    sample_rate: 0.1
    alert_on_degradation: true
  logging:
    enabled: true
    format: "json"
    path: "./logs/"
    include_ragas_scores: true
  metrics:
    - "response_time"
    - "token_count"
    - "cost_estimate"
    - "retrieval_accuracy"
    - "context_relevance"
    - "safety_score"
  quality_gates:
    min_safety_score: 0.90
    max_response_time: 5.0
    min_context_relevance: 0.75
  log_level: "INFO"
  export_interval: 24
  retention_days: 30
```

- Drives RAGAS metrics, continuous evaluation, and JSONL logging.

### 2.8 Vector Store (`vector_store`)

```yaml
vector_store:
  type: "chroma"              # chroma | faiss
  path: "./vector_store"
  collection_name: "rag_documents"
```

- ChromaDB by default; FAISS can be introduced later.

---

## 3. Environment Variables

Environment variables are usually provided via a `.env` file (for development) and standard environment configuration in production.

### 3.1 Azure OpenAI – LLM

Required for Module 3 (LLM Orchestration):

- `AZURE_OPENAI_API_KEY` – API key for main LLM endpoint
- `AZURE_OPENAI_ENDPOINT` – Base URL, e.g. `https://YOUR-RESOURCE.openai.azure.com/`
- `AZURE_OPENAI_API_VERSION` – API version, e.g. `2024-02-15-preview`
- `AZURE_DEPLOYMENT_NAME` – Name of the deployed chat model

### 3.2 Azure OpenAI – Embeddings

Required for Module 1 and 2 (embedding generation and retrieval):

- `AZURE_OPENAI_EMBEDDING_API_KEY` – API key for embedding deployment
- `AZURE_OPENAI_EMBEDDING_ENDPOINT` – Base URL for embeddings
- `AZURE_OPENAI_EMBEDDING_API_VERSION` – API version (optional; falls back to config)

### 3.3 Azure DevOps

Required when the Azure DevOps source is enabled:

- `AZURE_DEVOPS_ORG` – Organization name
- `AZURE_DEVOPS_PROJECT` – Project name
- `AZURE_DEVOPS_PAT` – Personal Access Token with **Code (Read)** permissions
- `AZURE_DEVOPS_REPO` – Repository name

### 3.4 Confluence (Planned / Optional)

Used if the Confluence source is enabled:

- `CONFLUENCE_BASE_URL` – Confluence base URL
- `CONFLUENCE_USERNAME` – Username (or email)
- `CONFLUENCE_API_TOKEN` – API token

### 3.5 Jira (Planned / Optional)

Used if the Jira source is enabled:

- `JIRA_URL` – Jira server URL
- `JIRA_USER` – User/email
- `JIRA_TOKEN` – API token

---

## 4. Feature Status (UI & Personalization)

The UI currently exposes:

**Completed**
- FastAPI app (`ui/app.py`) with HTML pages and static assets
- Search endpoint (`/api/search`) wired to the orchestrator
- Basic history hooks via `ActivityLogger` (server-side logs)
- Source metadata display in results

**In Progress / Planned**
- **Authentication & Login** (Planned)
  - SSO / OAuth integration
  - Per-user sessions
- **Per-User History & Personalization** (Planned)
  - Saved searches, favorites, feedback
  - User-specific source preferences
- **Document Upload UI** (Planned)
  - Upload PDFs/Markdown via browser
  - Route to ingestion pipeline with tenant-aware metadata
- **FAQ / Suggested Questions** (Planned)
  - Configurable list of starter questions
  - Curated examples per domain

The `docs/architecture/04_ui_personalization_and_auth_flow.md` file contains a draw.io-compatible diagram that marks **Completed**, **In Progress**, and **Planned** nodes.

---

## 5. How to Configure for a New Environment

1. **Clone and create virtual environment**
2. **Copy example env and fill values**

   ```bash
   cp env.example .env
   # Edit .env with Azure OpenAI + Azure DevOps + optional connectors
   ```

3. **Review and update `config.yaml`**
   - Enable/disable data sources as needed
   - Adjust `include_paths` / `file_types` for your repos
   - Tune retrieval and LLM parameters if necessary

4. **Run configuration validator (optional but recommended)**

   ```bash
   python debug_tools/01_check_config.py
   ```

5. **Ingest documents and start UI**

   ```bash
   python main.py --ingest
   python main.py --ui
   ```

---

## 6. Operational Notes

- All errors aim to be **polite and actionable** with system error codes.
- Logs are ASCII-safe (no emojis) and stored under `./logs/` and `./ui/logs/`.
- Ingestion tracker uses `ingestion_tracking.db` (SQLite) to avoid reprocessing unchanged documents.
- Vector store is persisted under `./vector_store/`.

For deeper technical details, refer to:

- `src/rag_ing/modules/corpus_embedding.py`
- `src/rag_ing/modules/query_retrieval.py`
- `src/rag_ing/modules/llm_orchestration.py`
- `ui/app.py`, `ui/api/routes.py`
- `debug_tools/DEVELOPER_GUIDE.md` for debugging procedures.
