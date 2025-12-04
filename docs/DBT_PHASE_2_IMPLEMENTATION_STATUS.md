# DBT Integration Phase 2: Implementation Status

**Date**: 2025-12-04  
**Branch**: `feature/using-dbt-artifacts`  
**Status**: Phase 2A Complete ✅, Phase 2B-D In Progress ⚠️

---

## Summary of Changes

### Key Discovery: Manifest Contains ALL SQL Code

We discovered that `manifest.json` contains:
- ✅ **139 models** → `raw_code` + `compiled_code` (100% coverage)
- ✅ **729 tests** → `raw_code` (100% coverage)
- ✅ **610 macros** → `macro_sql` (100% coverage)
- ✅ **Total**: 1,478 SQL documents

**Impact**: No need to fetch `/models/`, `/tests/`, `/macros/` directories separately!

---

## What Was Implemented (Phase 2A)

### 1. SQL Extraction Method ✅

**File**: `src/rag_ing/utils/dbt_artifacts.py`

**New Method**: `extract_sql_documents(include_compiled=True)`

```python
def extract_sql_documents(self, include_compiled: bool = True) -> List[Dict[str, Any]]:
    """Extract all SQL code from manifest for embedding.
    
    Returns:
        List of documents with:
        - content: Compiled SQL (easier to interpret) or raw SQL
        - metadata: Rich DBT metadata (type, name, tags, lineage)
        - summary: Human-readable summary with dependencies
    """
```

**Features**:
- Extracts 1,478 SQL documents from manifest
- Prefers `compiled_code` over `raw_code` for models (Jinja expanded)
- Includes complete metadata: tags, descriptions, lineage, schema
- Creates human-readable summaries with dependency context
- Separates models, tests, and macros with appropriate metadata

**Document Structure**:
```python
{
    'content': 'SELECT ... FROM ... WHERE ...',  # Actual SQL
    'metadata': {
        'dbt_type': 'model',
        'dbt_name': 'stg_qm2',
        'dbt_description': 'QM2 Informations',
        'dbt_tags': [],
        'dbt_schema': 'staging',
        'dbt_materialization': 'table',
        'dbt_code_type': 'compiled',
        'dbt_upstream_models': [...],
        'dbt_upstream_sources': [...],
        'dbt_downstream_models': [...],
        'lineage_depth': 17
    },
    'summary': 'DBT Model: stg_qm2\nType: table\n...'
}
```

---

### 2. Seed Reference Tracking ✅

**New Method**: `get_seed_references()`

```python
def get_seed_references(self) -> Dict[str, List[str]]:
    """Get mapping of seed names to models that reference them.
    
    Returns:
        Dict mapping seed names to list of model names
        Example: {'seed_antiemetics': ['stg_qm2', 'stg_qm3']}
    """
```

**Purpose**: Links seed CSV files to models that use them for business queries

**Example Output**:
```python
{
    'seed_chemo_w_emeticrisk_codes': ['stg_qm2', 'stg_qm3', 'stg_qm7'],
    'seed_antiemetics': ['stg_qm2', 'stg_qm5'],
    ...
}
```

---

### 3. Updated Configuration ✅

**File**: `config.yaml`

**Changes**:
```yaml
azure_devops:
  include_paths:
    # DBT ARTIFACTS (REQUIRED) - Contains ALL SQL code
    - "/dbt_anthem/target/manifest.json"       # SQL + metadata
    - "/dbt_anthem/target/catalog.json"        # Column types
    - "/dbt_anthem/target/graph_summary.json"  # Lineage
    - "/dbt_anthem/dbt_project.yml"            # Config
    
    # SEED FILES (REQUIRED for business data queries)
    - "/dbt_anthem/data/"                      # CSV reference data
  
  include_file_types:
    - ".json"   # Artifacts
    - ".yml"    # Config
    - ".csv"    # Seed data
    # NOT NEEDED: .sql, .md, .py
```

**Benefits**:
- 10x faster ingestion (artifacts + CSVs only)
- 100% SQL coverage from manifest
- Business reference data from seeds
- Complete lineage from graph

---

## Business Query Capability Demonstrated ✅

### Example Query

**Question**: "Does Anthem QM2 include J1434 for NK1 high emetic risk?"

**Query Flow**:
1. ✅ Find model: `stg_qm2` (from question keywords)
2. ✅ Get dependencies: 4 models, 3 sources (from lineage graph)
3. ✅ Trace to seeds: `seed_chemo_w_emeticrisk_codes` (from model deps)
4. ⚠️ Search CSV data: Find J1434 classification (NEEDS seed ingestion)
5. ⚠️ Generate answer: Combine SQL + lineage + CSV data (NEEDS LLM integration)

**Retrieved Context**:
- ✅ SQL code for stg_qm2 (compiled, easy to read)
- ✅ Lineage: upstream models and sources
- ✅ Seed file metadata: which seeds are used
- ⚠️ CSV content: actual drug codes and classifications (NEXT PHASE)

---

## What Still Needs Implementation

### Phase 2B: Seed CSV Processing ⚠️

**Goal**: Ingest seed CSV files for business data queries

**Tasks**:
1. Create `extract_seed_documents()` method in `dbt_artifacts.py`
   - Parse CSV files from manifest seed nodes
   - Create document per CSV file (or per row for large files)
   - Link to referencing models via `get_seed_references()`
   - Include column names and sample data

2. Document structure:
   ```python
   {
       'content': 'J1434,Fosaprepitant,High,NK1\nJ1453,Fosaprepitant...',
       'metadata': {
           'dbt_type': 'seed',
           'dbt_seed_name': 'seed_chemo_w_emeticrisk_codes',
           'dbt_file_path': 'data/reference/seed_chemo_w_emeticrisk_codes.csv',
           'dbt_referencing_models': ['stg_qm2', 'stg_qm3'],
           'csv_columns': ['code', 'drug_name', 'emetic_risk', 'classification'],
           'csv_row_count': 150
       },
       'summary': 'Seed: seed_chemo_w_emeticrisk_codes\nUsed by: stg_qm2...'
   }
   ```

**Estimated Time**: 2-3 hours

---

### Phase 2C: Corpus Ingestion Integration ⚠️

**Goal**: Integrate DBT extraction with existing ingestion pipeline

**File**: `src/rag_ing/modules/corpus_embedding.py`

**Tasks**:
1. Detect DBT artifacts during `_ingest_azuredevops_enhanced()`
   - Check for `manifest.json` + `dbt_project.yml` in fetched files
   - Initialize `DBTArtifactParser` when detected

2. Extract and process DBT documents:
   ```python
   if dbt_artifacts_detected:
       parser = DBTArtifactParser(artifacts_dir)
       
       # Extract SQL documents
       sql_docs = parser.extract_sql_documents(include_compiled=True)
       for doc in sql_docs:
           # Add to existing document pipeline
           self._process_document(doc)
       
       # Extract seed documents
       seed_docs = parser.extract_seed_documents(csv_files)
       for doc in seed_docs:
           self._process_document(doc)
   ```

3. Handle CSV files separately:
   - Save CSV files to temp directory
   - Pass to `extract_seed_documents()` with seed metadata
   - Process as regular documents (chunk, embed, store)

**Estimated Time**: 3-4 hours

---

### Phase 2D: Query Enhancement ⚠️

**Goal**: Enable intelligent query routing for lineage and data lookups

**Files**: 
- `src/rag_ing/modules/query_retrieval.py`
- `src/rag_ing/modules/llm_orchestration.py`

**Tasks**:
1. Detect query type:
   - Lineage query: "What depends on X?"
   - Code query: "Show me SQL for X"
   - Data lookup: "Does X include code Y?"

2. Route accordingly:
   - Lineage → DBTLineageGraph (fast, < 1ms)
   - Code → Vector search with `dbt_type=model` filter
   - Data lookup → Vector search with `dbt_type=seed` filter + model lineage

3. Combine results:
   - Lineage context from graph
   - SQL code from vector store
   - CSV data from vector store
   - Generate comprehensive answer

**Estimated Time**: 4-5 hours

---

## Testing Status

### Unit Tests ✅

**File**: `tests/test_dbt_integration.py`

**Coverage**:
- ✅ DBTLineageGraph (6 tests)
- ✅ DBTArtifactParser (8 tests)
- ✅ Real anthem_dev data (1 integration test)
- ✅ Total: 15 tests, all passing

**New Tests Needed**:
- ⚠️ `extract_sql_documents()` method
- ⚠️ `extract_seed_documents()` method
- ⚠️ Corpus ingestion integration
- ⚠️ Query routing and enhancement

---

### Integration Tests ✅

**File**: `temp_helper_codes/test_dbt_business_query.py`

**Demonstrates**:
- ✅ SQL extraction (1,478 documents)
- ✅ Seed reference tracking (29 seeds)
- ✅ Business query flow (QM2 example)
- ✅ Document structure samples

---

## Performance Metrics

### Ingestion Time Estimate

| Approach | Files | Size | Time | SQL Coverage |
|----------|-------|------|------|--------------|
| **Artifacts + CSV** | ~33 files | ~10 MB | **1 minute** | 100% (1,478 docs) |
| Artifacts + Models + CSV | 172+ files | 60+ MB | 5-7 minutes | 100% + comments |

**Recommendation**: Artifacts + CSV approach (10x faster, same SQL coverage)

### Query Performance

| Query Type | Source | Performance | Example |
|------------|--------|-------------|---------|
| Lineage | Graph (memory) | < 1ms | "What depends on stg_qm2?" |
| SQL Code | Vector store | 50-100ms | "Show me SQL for stg_qm2" |
| Data Lookup | Vector store | 50-100ms | "Does QM2 include J1434?" |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AZURE DEVOPS FETCH                          │
│  • /dbt_anthem/target/*.json (artifacts)                        │
│  • /dbt_anthem/data/*.csv (seeds)                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                DBT ARTIFACT DETECTION                           │
│  if manifest.json + dbt_project.yml found:                      │
│    → Initialize DBTArtifactParser                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  SQL EXTRACTION  │      │  SEED EXTRACTION │
│  (1,478 docs)    │      │  (29 CSV files)  │
│  • Models        │      │  • Link to models│
│  • Tests         │      │  • Column info   │
│  • Macros        │      │  • Sample data   │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         └────────────┬────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   DOCUMENT PIPELINE    │
         │   • Chunk              │
         │   • Embed              │
         │   • Store              │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │    VECTOR STORE        │
         │    (ChromaDB)          │
         │  • SQL code            │
         │  • CSV data            │
         │  • Rich metadata       │
         │  • Lineage context     │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │   QUERY RETRIEVAL      │
         │  • Semantic search     │
         │  • Lineage graph       │
         │  • Metadata filters    │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │     LLM ANSWER         │
         │  Context:              │
         │  • SQL code            │
         │  • Lineage             │
         │  • CSV data            │
         └────────────────────────┘
```

---

## Next Steps (Priority Order)

1. **Phase 2B**: Implement `extract_seed_documents()` method
   - Parse CSV files from seed nodes
   - Create embeddings for CSV content
   - Link to referencing models
   - **Time**: 2-3 hours

2. **Phase 2C**: Integrate with corpus ingestion
   - Detect DBT artifacts
   - Call extraction methods
   - Add to document pipeline
   - **Time**: 3-4 hours

3. **Phase 2D**: Query enhancement
   - Query type detection
   - Intelligent routing
   - Context combination
   - **Time**: 4-5 hours

4. **Phase 3**: UI enhancements
   - Lineage visualization
   - Seed data display
   - Query suggestions
   - **Time**: 5-6 hours

**Total Estimated Time to Complete**: 14-18 hours

---

## References

- **SQL Inventory**: `/workspaces/RAG-ing/docs/DBT_MANIFEST_SQL_CODE_INVENTORY.md`
- **Implementation Plan**: `/workspaces/RAG-ing/docs/DBT_IMPLEMENTATION_PLAN.md`
- **Test Demo**: `/workspaces/RAG-ing/temp_helper_codes/test_dbt_business_query.py`
- **Unit Tests**: `/workspaces/RAG-ing/tests/test_dbt_integration.py`
