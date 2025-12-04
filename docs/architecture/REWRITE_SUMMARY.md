# Architecture Documentation Rewrite Summary

**Date**: 2025-11-26  
**Author**: GitHub Copilot  
**Task**: Compare actual codebase implementation with architecture docs and rewrite to match reality

---

## What Changed

All four architecture documents have been **completely rewritten** to:
1. **Remove Mermaid diagrams** (user requested draw.io-compatible format)
2. **Match actual code implementation** (not idealized architecture)
3. **Use structured lists, tables, and step-by-step flows** instead of visual diagrams
4. **Include real file paths, line numbers, and code snippets** from the codebase
5. **Distinguish Completed vs In Progress vs Planned features** (especially for UI doc)

---

## Documents Rewritten

### 1. `01_high_level_flow.md` (4.1 KB)

**Before**: Mermaid flowchart with generic module descriptions

**After**: Structured component list with:
- Real file paths (`src/rag_ing/orchestrator.py`, `ui/app.py`)
- Actual method names (`ingest_corpus()`, `query_documents()`)
- Database details (`ingestion_tracking.db`, `chroma.sqlite3`)
- Two complete flows: Ingestion Flow + Query Flow (step-by-step)

**Key Additions**:
- Entry point details (FastAPI routes)
- Module 1-5 descriptions with actual features
- Data store schemas (vector store, tracker, logs)
- Configuration references

### 2. `02_source_to_vector_and_tracker.md` (9.8 KB)

**Before**: Mermaid flowchart with abstract source connectors

**After**: 10-step ingestion pipeline with:
- Configuration inputs (`config.yaml` + `.env` sections)
- Code references (line numbers from `corpus_embedding.py`)
- Per-source ingestion details (Local, Azure DevOps, Confluence, Jira)
- Duplicate detection algorithm (hash + fuzzy + semantic)
- Chunking strategies (recursive, semantic, code-specific)
- Embedding generation process (Azure OpenAI primary, HuggingFace fallback)
- Vector store write logic (Chroma vs FAISS)
- Tracker database schema and updates
- Data flow summary table

**Key Additions**:
- Actual code snippets showing how connectors work
- Azure DevOps filtering logic (include/exclude paths, file types)
- Commit history fetching details
- Hierarchical storage explanation
- Statistics reporting format

### 3. `03_retrieval_and_optimization_flow.md` (9.4 KB)

**Before**: Mermaid flowchart with generic retrieval steps

**After**: 13-step query pipeline with:
- Query reception via FastAPI (`/api/search`)
- Orchestrator coordination code
- Query embedding process
- Hybrid retrieval explained in detail:
  - Semantic retrieval (ChromaDB similarity search)
  - Keyword retrieval (BM25-style)
  - Weighted merge formula (0.6 semantic + 0.4 keyword)
- Domain-specific boosting (generic codes, not medical)
- Cross-encoder reranking (ms-marco-MiniLM model)
- Context assembly and truncation
- LLM prompt construction (strict grounding enforcement)
- Azure OpenAI API call details
- Response formatting
- Evaluation metrics (retrieval + generation)
- JSONL logging format

**Key Additions**:
- Real code from `query_retrieval.py` and `llm_orchestration.py`
- Configuration values from `config.yaml`
- Performance numbers (50ms for reranking 20 docs)
- Prompt template structure
- Metrics calculations

### 4. `04_ui_personalization_and_auth_flow.md` (12 KB)

**Before**: Mermaid flowchart with mixed completed/planned features

**After**: Comprehensive feature inventory with clear status markers:
- **Completed Features** (6 items):
  - Home page (`ui/templates/home.html`)
  - Search API (`/api/search`)
  - Results page (`search_result.html`)
  - Static assets (`ui/static/`)
  - Health check endpoint
  - Enhanced response formatting
- **In Progress Features** (1 item):
  - Session activity logging (backend done, UI wiring needed)
- **Planned Features** (7 items):
  - Authentication (SSO/OAuth)
  - Personalized dashboard
  - Per-user query history
  - User-specific source toggles
  - Document upload interface
  - FAQ suggestions
  - Feedback mechanism

**Key Additions**:
- Status legend: ✓ Completed, ⏳ In Progress, 📋 Planned
- Feature status table with priority levels
- Current UI flow step-by-step (11 steps)
- Proposed implementation details for planned features
- Required changes (new files, database tables, config)
- Request/response schemas for all routes

---

## Methodology

1. **Read actual implementation code** across multiple files:
   - `src/rag_ing/orchestrator.py`
   - `src/rag_ing/modules/corpus_embedding.py`
   - `src/rag_ing/modules/query_retrieval.py`
   - `src/rag_ing/modules/llm_orchestration.py`
   - `ui/app.py`, `ui/api/routes.py`, `ui/api/pages.py`

2. **Extracted real details**:
   - Method names and signatures
   - Line number ranges
   - Configuration parameters
   - Database schemas
   - API endpoints

3. **Organized into logical flows**:
   - Numbered steps (1-13)
   - Clear inputs and outputs
   - Decision points explained
   - Error handling described

4. **Replaced Mermaid with structured text**:
   - Bullet lists for components
   - Numbered lists for sequences
   - Tables for comparisons
   - Code blocks for snippets

---

## Benefits

### For Draw.io Import
- No Mermaid syntax to parse
- Can be used as text reference while creating diagrams
- Step numbers map directly to diagram nodes
- Tables can become diagram annotations

### For Developers
- Real code references speed up navigation
- Line numbers make debugging easier
- Configuration examples show actual usage
- Status markers clarify what's implemented vs planned

### For Documentation
- Matches reality (no outdated diagrams)
- Easy to update (just edit text, no diagram tools)
- Searchable (Ctrl+F works well)
- Version control friendly (git diff shows meaningful changes)

---

## Verification

All documents cross-checked against:
- ✓ Actual file structure (`ls -R src/ ui/`)
- ✓ Code implementation (read_file on key modules)
- ✓ Configuration files (`config.yaml`, `.env` variables)
- ✓ Project documentation (`.github/copilot-instructions.md`)
- ✓ Database files (`ingestion_tracking.db`, `chroma.sqlite3`)

---

## Next Steps (Optional)

1. **Create draw.io diagrams** using these docs as reference
   - Copy step lists into diagram nodes
   - Connect nodes following the numbered flows
   - Add color coding for status (green=completed, yellow=in progress, blue=planned)

2. **Add to Confluence**:
   - Import markdown directly (Confluence supports MD)
   - Add screenshots from UI
   - Link to source code in repo

3. **Keep docs updated**:
   - When implementing planned features, move them to "Completed" section
   - Update line numbers if code moves
   - Add new configuration examples as they're added

---

## File Sizes

| File | Size | Lines | Content |
|------|------|-------|---------|
| `01_high_level_flow.md` | 4.1 KB | ~130 | System overview + 2 flows |
| `02_source_to_vector_and_tracker.md` | 9.8 KB | ~380 | 10-step ingestion pipeline |
| `03_retrieval_and_optimization_flow.md` | 9.4 KB | ~360 | 13-step query pipeline |
| `04_ui_personalization_and_auth_flow.md` | 12 KB | ~460 | Feature inventory + UI flow |
| **Total** | **35.3 KB** | **~1,330** | Complete architecture reference |

---

## Quality Checklist

- ✓ No Mermaid diagrams (plain text only)
- ✓ All code references verified against actual files
- ✓ Line numbers accurate as of 2025-11-26
- ✓ Configuration examples match `config.yaml` structure
- ✓ Database schemas match actual SQLite tables
- ✓ API routes match `routes.py` implementation
- ✓ Feature status accurate (Completed vs Planned)
- ✓ No emojis in code examples (ASCII-safe)
- ✓ No domain-specific language (generic, not medical)
- ✓ Strict grounding enforcement documented in LLM prompts
