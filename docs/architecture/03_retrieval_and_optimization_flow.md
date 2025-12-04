# Retrieval & Optimization Flow

## Overview

This flow describes how user queries are processed, documents retrieved from the vector store, reranked, and used to generate grounded responses.

**Entry Point**: `RAGOrchestrator.query_documents()` → `QueryRetrievalModule.process_query()` → `LLMOrchestrationModule.generate_response()`

---

## Query Processing Pipeline

### Step 1: Query Reception

**Entry**: User submits query via UI → FastAPI `/api/search` endpoint → `routes.py`

**Code**: `ui/api/routes.py` lines 45-50

```python
@router.post("/api/search")
async def search(request: SearchRequest):
    query = request.query
    result = rag_system.query_documents(query)
```

**Passes to**: `RAGOrchestrator.query_documents()` in `orchestrator.py`

### Step 2: Orchestrator Preparation

**Code**: `orchestrator.py` lines 126-140

**Process**:
1. Record retrieval start time
2. Call `query_retrieval.process_query(query, user_context)`
3. Measure retrieval time
4. Log retrieval event

```python
retrieval_start = time.time()
retrieval_result = self.query_retrieval.process_query(
    query_text=query,
    user_context=user_context
)
retrieval_time = time.time() - retrieval_start
```

### Step 3: Query Embedding

**Module**: `QueryRetrievalModule` in `src/rag_ing/modules/query_retrieval.py`

**Code**: Lines 140-150

**Process**:
1. Load same embedding model used during ingestion
2. Generate query embedding vector
3. Uses Azure OpenAI `text-embedding-ada-002` (primary) or HuggingFace fallback

```python
query_embedding = self.embedding_model.embed_query(query_text)
# Returns: 1536-dimensional vector for ada-002
```

### Step 4: Hybrid Retrieval

**Code**: `_hybrid_retrieval()` method, lines 350-400

**Retrieval Strategy**: Parallel semantic + keyword search, then weighted merge

#### 4a. Semantic Retrieval

**Method**: `_semantic_retrieval()` lines 420-450

**Process**:
1. Query ChromaDB collection with embedding vector
2. Cosine similarity search
3. Fetch top-k documents (configured in `retrieval.top_k`)
4. Returns documents with similarity scores

```python
results = self.vector_store.similarity_search_with_score(
    query_embedding,
    k=self.top_k * 2  # Over-fetch for reranking
)
```

#### 4b. Keyword Retrieval

**Method**: `_keyword_retrieval()` lines 460-490

**Process**:
1. Extract keywords from query (tokenize, remove stopwords)
2. BM25-style scoring using document metadata
3. Fetch documents matching keywords
4. Returns documents with BM25 scores

**Note**: ChromaDB doesn't have native BM25, so this uses metadata filtering + keyword matching

#### 4c. Weighted Merge

**Method**: `_merge_retrieval_results()` lines 500-550

**Configuration** (from `config.yaml`):
- `retrieval.hybrid_search.semantic_weight`: 0.6
- `retrieval.hybrid_search.keyword_weight`: 0.4

**Process**:
1. Combine semantic and keyword results
2. Normalize scores to [0, 1]
3. Compute weighted score:
   ```
   final_score = (semantic_score * 0.6) + (keyword_score * 0.4)
   ```
4. Sort by final_score descending
5. Deduplicate by document_id
6. Return top-k merged results

### Step 5: Domain-Specific Boosting (Optional)

**Code**: `_apply_medical_boosting()` method, lines 570-620

**Triggered when**: `retrieval.medical_domain_boost.enabled: true` (legacy, generalized in latest)

**Current Implementation** (generic domain codes):
- Extracts domain codes from query (error codes, ticket IDs, version numbers)
- Boosts documents containing matching codes
- Applies boost multiplier (e.g., 1.5x) to relevance scores

**Configuration**:
```yaml
retrieval:
  domain_boost:
    enabled: true
    boost_multiplier: 1.5
    code_patterns:
      - "ERR-\\d{3,6}"
      - "TICKET-\\d+"
      - "v\\d+\\.\\d+\\.\\d+"
```

### Step 6: Filtering

**Code**: `_apply_filters()` method, lines 630-670

**Available Filters** (from query metadata):
- **Date range**: `date_from`, `date_to` → filters `processed_date` metadata
- **Source type**: `source_type` → filters by "local_file", "azure_devops", etc.
- **File type**: `file_types` → filters by extension (".sql", ".py")

**Process**:
1. For each document in results:
   - Check metadata against filters
   - Drop if doesn't match
2. Return filtered list

### Step 7: Cross-Encoder Reranking (Optional)

**Code**: `_rerank_documents()` method, lines 700-750

**Triggered when**: `retrieval.reranking.enabled: true`

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (default)

**Configuration**:
```yaml
retrieval:
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20  # Documents to rerank
    top_k_final: 5     # Final results
    relevance_threshold: 0.3
```

**Process**:
1. Take top-k_initial documents (e.g., 20)
2. For each document:
   - Compute relevance score: `cross_encoder.predict([query, doc_text])`
   - Returns score 0-1 (higher = more relevant)
3. Filter out documents below `relevance_threshold`
4. Sort by reranked score descending
5. Return top-k_final documents (e.g., 5)

**Performance**: ~50ms for 20 documents on CPU

### Step 8: Context Assembly

**Code**: End of `process_query()` method, lines 180-220

**Process**:
1. Extract `page_content` from each retrieved document
2. Concatenate with separators:
   ```
   Document 1: [source]
   {content}
   ---
   Document 2: [source]
   {content}
   ```
3. Enforce max context length:
   - `llm.max_context_tokens`: 6000 (configurable)
   - Truncate if exceeds limit (smart truncation preserves full documents when possible)
4. Return structured result:

```python
{
    "documents": [{"content": "...", "metadata": {...}, "score": 0.95}, ...],
    "query": "original query",
    "retrieval_time": 0.15,
    "context": "concatenated document texts"
}
```

---

## LLM Response Generation

### Step 9: Prompt Construction

**Module**: `LLMOrchestrationModule` in `src/rag_ing/modules/llm_orchestration.py`

**Code**: `generate_response()` method, lines 300-350

**Process**:
1. Load prompt template from `prompts/general.txt`
2. Replace placeholders:
   - `{context}` → assembled context from Step 8
   - `{query}` → user's original query
3. Enforce strict grounding instruction:
   ```
   You MUST answer ONLY from the provided context.
   If information is not in context, say:
   "I cannot find information about [topic] in available documents.
   However, I found related information about [closest topic].
   You might want to rephrase your question as: '[suggested question]'"
   ```

**Prompt Template Structure**:
```
SYSTEM INSTRUCTION:
{strict grounding rules}

CONTEXT:
{retrieved documents}

USER QUERY:
{query}

INSTRUCTIONS:
- Answer from context only
- Cite sources
- Provide document references
```

### Step 10: LLM API Call

**Code**: `_call_azure_openai()` or `_call_koboldcpp()` methods

**Primary**: Azure OpenAI
- Model: `gpt-4` or `gpt-4o` (from config)
- Endpoint: `AZURE_OPENAI_API_BASE`
- API Key: `AZURE_OPENAI_API_KEY`
- Deployment: `AZURE_OPENAI_DEPLOYMENT_NAME`

**Fallback**: KoboldCpp (local)
- Endpoint: `http://localhost:5001/api/v1/generate`
- Used if Azure fails or unavailable

**Process**:
1. Send prompt to LLM
2. Parse response
3. Extract answer text
4. Handle errors with detailed messages

### Step 11: Response Formatting

**Code**: End of `generate_response()` method

**Returns**:
```python
{
    "answer": "LLM-generated answer text",
    "sources": [
        {"title": "doc1.sql", "content": "...", "score": 0.95},
        ...
    ],
    "context_used": "assembled context",
    "generation_time": 1.2,
    "model": "gpt-4"
}
```

---

## Evaluation & Logging (Module 5)

### Step 12: Calculate Metrics

**Module**: `EvaluationLoggingModule` in `src/rag_ing/modules/evaluation_logging.py`

**Code**: `log_query_event()` method

#### Retrieval Metrics
- **hit_rate**: Did retrieved docs contain answer? (binary 0/1)
- **context_precision**: Relevance of top-k documents
- **retrieval_time**: Time to fetch and rerank
- **documents_retrieved**: Count of documents returned

#### Generation Metrics
- **safety_score**: Content policy compliance (0-1)
- **clarity**: Readability score (0-1)
- **response_length**: Character count
- **generation_time**: LLM API latency
- **model_used**: "gpt-4" or "koboldcpp"

### Step 13: Write JSONL Logs

**Writes to**:
- `logs/evaluation.jsonl` - complete query event
- `logs/retrieval_metrics.jsonl` - retrieval performance
- `logs/generation_metrics.jsonl` - LLM response quality

**Format**:
```json
{
  "query_hash": "abc123",
  "query": "What is dbt?",
  "retrieval_time": 0.15,
  "hit_rate": 1.0,
  "generation_time": 1.2,
  "answer_length": 256,
  "timestamp": "2025-11-26T10:30:00"
}
```

---

## Configuration Summary

All retrieval behavior controlled by `config.yaml`:

```yaml
retrieval:
  top_k: 5
  hybrid_search:
    enabled: true
    semantic_weight: 0.6
    keyword_weight: 0.4
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20
    top_k_final: 5
  domain_boost:
    enabled: true
    boost_multiplier: 1.5

llm:
  provider: "azure_openai"
  model: "gpt-4"
  max_context_tokens: 6000
  prompt_template: "./prompts/general.txt"
```

---

## Key Files

- **Main orchestration**: `src/rag_ing/orchestrator.py`
- **Retrieval module**: `src/rag_ing/modules/query_retrieval.py`
- **LLM module**: `src/rag_ing/modules/llm_orchestration.py`
- **Evaluation module**: `src/rag_ing/modules/evaluation_logging.py`
- **API routes**: `ui/api/routes.py`
- **Prompt templates**: `prompts/general.txt`
