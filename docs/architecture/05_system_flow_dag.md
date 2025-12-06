# System Flows and DAG Overview

This document describes the main execution flows in the current RAG-ing system:

- Environment and configuration loading
- Corpus ingestion (with DBT artifacts)
- Query and retrieval
- UI interaction

The focus is on **what calls what**, in which order.

---

## 1. Env and Configuration Flow

High-level DAG from environment variables to fully initialized orchestrator:

1. Shell / process environment
   - `.env` (optional) is loaded by your shell or process manager.
   - Azure/OpenAI and Azure DevOps secrets are exposed as environment variables.

2. `config.yaml`
   - Uses `${VAR}` syntax to reference environment variables.
   - Defines data sources, vector store, embedding model, LLM provider, retrieval options, UI and logging.

3. `Settings.from_yaml("./config.yaml")` (`src/rag_ing/config/settings.py`)
   - Parses YAML and resolves `${VAR}` placeholders.
   - Validates structure via Pydantic models.

4. `RAGOrchestrator.__init__` (`src/rag_ing/orchestrator.py`)
   - Accepts `config_path` (defaults to `./config.yaml`).
   - Calls `Settings.from_yaml` and stores the result as `self.settings`.
   - Instantiates all 5 modules:
     - `CorpusEmbeddingModule(self.settings)`
     - `QueryRetrievalModule(self.settings)`
     - `LLMOrchestrationModule(self.settings)`
     - `UILayerModule(self.settings)`
     - `EvaluationLoggingModule(self.settings)`
   - Injects the LLM client into:
     - Corpus embedding (for summarization when hierarchical storage is enabled).
     - Query retrieval (for multi-query expansion).
   - Optionally initializes `ActivityLogger` if activity logging is enabled.

Result: a fully configured `RAGOrchestrator` instance with all modules wired and ready.

---

## 2. Corpus Ingestion DAG

Entry point (CLI):

```bash
python main.py --ingest
```

High-level steps:

1. `main.py`
   - Parses CLI arguments.
   - Creates `RAGOrchestrator(config_path="./config.yaml")`.
   - Calls `orchestrator.ingest_corpus()`.

2. `RAGOrchestrator.ingest_corpus()`
   - Logs the start of ingestion.
   - Calls `self.corpus_embedding.process_corpus()`.
   - Measures total ingestion time.
   - Updates system metrics via `EvaluationLoggingModule`.

3. `CorpusEmbeddingModule.process_corpus()` (simplified DAG)
   - Step 1: Multi-source ingestion
     - Reads enabled sources from `self.settings.data_source`.
     - For Azure DevOps source:
       - Creates `AzureDevOpsConnector` (`connectors/azuredevops_connector.py`).
       - Streams files matching `include_paths`/`exclude_paths` and file-type filters.
       - Attaches metadata (file path, commit history if enabled).
       - Tracks processed vs skipped files.
     - Optionally ingests local files and other connectors if configured.

   - Step 2: DBT artifact processing
     - After all Azure DevOps documents are collected, calls:
       - `self._process_dbt_artifacts(all_docs)`
     - `_process_dbt_artifacts`:
       - Scans documents for:
         - `dbt_project.yml`
         - `target/manifest.json`
         - Seed `.csv` files under `/data/`.
       - If both project and manifest are found:
         - Writes their content (and optional `catalog.json`, `graph_summary.json` if present) to a temporary directory.
         - Instantiates `DBTArtifactParser` (`utils/dbt_artifacts.py`) pointing to that directory.
         - Calls `parser.extract_sql_documents(include_compiled=True)` to produce synthetic SQL documents for models, tests, macros.
         - Optionally calls `parser.extract_seed_documents(csv_files)` for seeds.
         - Wraps each synthetic document as a `Document` with metadata, including fields like `dbt_type`, `dbt_name`, `dbt_tags`, and lineage info.
         - Extends `all_docs` with these DBT documents.

   - Step 3: Chunking
     - Applies configured chunking strategy (recursive, code-aware, etc.).
     - Produces `chunks` with per-chunk metadata (including original file path and, for DBT, dbt metadata).

   - Step 4: Embedding
     - Initializes Azure OpenAI embedding provider via `utils/embedding_provider.py`.
     - Embeds each chunk using the configured Azure model.

   - Step 5: Vector storage and tracking
     - Stores embeddings + metadata into ChromaDB (`vector_store/`, collection `rag_documents`).
     - Records document and chunk info in ingestion tracker SQLite DB (e.g. `ingestion_tracking.db`) to support incremental updates.

   - Returns ingestion statistics (documents processed, chunks created, processing time).

Result: vector store populated with embedded chunks and DBT-aware metadata, ready for search.

---

## 3. Query and Retrieval DAG

There are two primary entry points:

- CLI: `python main.py --query "your question"`
- UI / API: HTTP request to `/api/search` (see `ui/api/routes.py`).

Underlying orchestrator methods:

1. `RAGOrchestrator.query_documents()`
   - Basic single-query pipeline.

2. `RAGOrchestrator.query_documents_with_multi_query()`
   - Advanced pipeline with:
     - Query expansion (9 variations).
     - Project detection and filtering.
     - Hybrid context (semantic + keyword) assembly.

Common DAG (simplified):

1. Start
   - Compute a short `query_hash` for logging.
   - Log the incoming query.

2. Retrieval (Module 2: `QueryRetrievalModule`)
   - In `query_documents`:
     - Calls `self.query_retrieval.process_query(query)`.
   - In `query_documents_with_multi_query`:
     - Calls `self.query_retrieval.process_query_with_multi_query(...)`.
   - Inside retrieval module:
     - Uses Azure OpenAI embedding provider (same model as ingestion) to embed the query.
     - For multi-query mode:
       - Uses `LLMOrchestrationModule` to generate query variations.
       - Performs parallel vector searches in Chroma for each variation.
       - Aggregates and ranks results (frequency + relevance).
     - For hybrid context builder:
       - Combines semantic results with keyword-based retrieval.
     - Returns:
       - `documents`: list of LangChain `Document` objects (with metadata).
       - `stats`: retrieval statistics.

3. Evaluation (retrieval metrics)
   - `EvaluationLoggingModule.calculate_retrieval_metrics(...)` computes retrieval metrics based on:
     - Query text.
     - Retrieved documents.
     - Retrieval time.

4. LLM generation (Module 3: `LLMOrchestrationModule`)
   - Builds a `context` string by concatenating selected document chunks.
   - Calls `self.llm_orchestration.generate_response(query=query, context=context)`.
   - The LLM module:
     - Loads the strict-grounding prompt from `prompts/general.txt` (or configured prompt).
     - Uses Azure OpenAI chat/completions API to generate an answer.
     - Returns response text and model/usage metadata.

5. Evaluation (generation metrics)
   - `EvaluationLoggingModule.calculate_generation_metrics(...)`:
     - Evaluates response length, clarity, alignment with sources.
   - `EvaluationLoggingModule.calculate_safety_score(...)`:
     - Computes a safety score based on heuristics and content.

6. Logging and activity tracking
   - Creates a `QueryEvent` and writes it to `logs/evaluation.jsonl`.
   - Updates system metrics (success flag, processing time).
   - If `ActivityLogger` is enabled:
     - Writes per-query activity to `logs/user_activity/*.jsonl`.

7. Return
   - Returns a structured response dict:
     - `query`, `query_hash`.
     - `response` (LLM output string).
     - `sources` (retrieved `Document` objects).
     - `metadata` (retrieval and generation stats, timing, safety score).

Result: caller (CLI or UI) receives an answer plus associated source documents and metadata.

---

## 4. UI and API Flow

The UI is implemented as a FastAPI app in `ui/app.py` with routes defined in `ui/api/`.

High-level DAG for a browser-based search:

1. Browser → HTTP request
   - User opens `/` in a browser.
   - Submits a form or uses a JavaScript-based search interface.

2. FastAPI route handler
   - In `ui/api/routes.py` (or similar):
     - Parses incoming JSON or form data.
     - Constructs a query string and optional user context.
     - Calls orchestrator:
       - `orchestrator.query_documents_with_multi_query(...)`.

3. Orchestrator pipeline
   - Follows the query/retrieval DAG described above.

4. Response formatting
   - Uses `ui/enhanced_response.py` to:
     - Convert raw response and source documents into a UI-friendly structure.
     - Attach metadata such as file paths, DBT model names/tags, and scores.

5. Template rendering / JSON
   - For HTML responses:
     - Passes data into Jinja2 templates in `ui/templates/`.
   - For API responses:
     - Returns JSON with answer, sources, and metadata.

6. Browser display
   - Renders answer text and source snippets.
   - Optionally shows metadata (scores, DBT tags, file paths).

Result: user sees an answer grounded in the ingested corpus, along with links/snippets of underlying documents.

---

## 5. Where to Look When Debugging

- **Config and env**
  - `config.yaml` – all tunable behavior.
  - `src/rag_ing/config/settings.py` – Pydantic models and defaults.

- **Ingestion**
  - `src/rag_ing/modules/corpus_embedding.py` – overall ingestion pipeline.
  - `src/rag_ing/connectors/azuredevops_connector.py` – Azure DevOps streaming.
  - `src/rag_ing/utils/dbt_artifacts.py` – DBT manifest/project parsing.

- **Retrieval**
  - `src/rag_ing/modules/query_retrieval.py` – query expansion, hybrid retrieval.
  - `src/rag_ing/retrieval/` – query expansion, hybrid context, aggregation.

- **LLM**
  - `src/rag_ing/modules/llm_orchestration.py` – Azure OpenAI setup and prompts.
  - `prompts/` – prompt templates (notably `general.txt`).

- **UI**
  - `ui/app.py` – FastAPI application.
  - `ui/api/` – routes.
  - `ui/enhanced_response.py` – response shaping for the UI.

- **Evaluation & Logs**
  - `src/rag_ing/modules/evaluation_logging.py` – metrics + JSONL logging.
  - `logs/` and `logs/user_activity/` – actual log files.
