# Retrieval Techniques: Hybrid Search, Reranking, and Optimization

## Overview

This document explains the retrieval pipeline that finds the most relevant documents for user queries using advanced techniques including hybrid search, cross-encoder reranking, and domain-specific optimization.

**Entry Point**: User query → `RAGOrchestrator.query_documents()` → `QueryRetrievalModule.process_query()`  
**Average Latency**: 150-250ms (retrieval only)  
**Accuracy**: 85-95% hit rate (answer in top-5 results)

---

## Retrieval Architecture

```
User Query
    ↓
Query Embedding (Azure OpenAI)
    ↓
    ┌─────────────────┴─────────────────┐
    ↓                                   ↓
Semantic Search                    Keyword Search
(Vector Similarity)                (BM25-style)
    └─────────────────┬─────────────────┘
                      ↓
            Weighted Merge (60/40)
                      ↓
            Domain Boosting (optional)
                      ↓
            Metadata Filtering
                      ↓
            Cross-Encoder Reranking
                      ↓
            Top-K Results
                      ↓
            Context Assembly
```

---

## Phase 1: Query Preprocessing

### Query Reception

**Route**: `/api/search` (POST)

**Request**:
```json
{
  "query": "What is dbt?",
  "filters": {
    "source_type": ["azure_devops"],
    "file_type": [".sql"],
    "date_from": "2025-01-01"
  }
}
```

### Query Normalization

**Process**:
1. Trim whitespace
2. Convert to lowercase (for keyword matching)
3. Remove special characters (for BM25)
4. Preserve original for display

**Example**:
```
Original: "  What is dbt?  "
Normalized: "what is dbt"
```

### Query Embedding

**Model**: Same as corpus embedding (`text-embedding-ada-002`)

**Code**: `query_retrieval.py` lines 140-150

```python
query_embedding = self.embedding_model.embed_query(query_text)
# Returns: [0.123, -0.456, ...] (1,536 dimensions)
```

**Importance**: Query and documents **must** use the same embedding model for accurate similarity

---

## Phase 2: Hybrid Retrieval

### Why Hybrid?

**Problem**: Pure semantic search misses exact keyword matches  
**Problem**: Pure keyword search misses semantic similarities

**Solution**: Combine both and weight results

**Configuration**:
```yaml
retrieval:
  hybrid_search:
    enabled: true
    semantic_weight: 0.6   # 60% weight to vector similarity
    keyword_weight: 0.4    # 40% weight to keyword matching
```

### Technique 1: Semantic Search

**Algorithm**: Cosine similarity in vector space

**Process**:
1. Query embedding: `q = [0.123, -0.456, ...]`
2. For each document embedding `d`:
   - Compute: `similarity = cosine(q, d)`
   - Cosine formula: `dot(q, d) / (||q|| * ||d||)`
3. Sort by similarity descending
4. Return top-k documents

**ChromaDB Implementation**:
```python
results = self.vector_store.similarity_search_with_score(
    query_embedding,
    k=self.top_k * 2  # Over-fetch for reranking (e.g., 20 for top_k=5)
)
# Returns: [(document, similarity_score), ...]
```

**Example Scores**:
```
Document 1: "dbt is a data transformation tool..." → 0.92
Document 2: "dbt models are SQL SELECT statements..." → 0.89
Document 3: "data build tool documentation..." → 0.75
```

**Strengths**:
- Finds semantic matches even with different wording
- Handles synonyms and paraphrases
- Works across languages

**Weaknesses**:
- May miss exact keyword matches
- Less effective for short queries (< 5 words)
- Requires quality embeddings

### Technique 2: Keyword Search (BM25-style)

**Algorithm**: BM25 (Best Matching 25) - industry-standard ranking function

**Formula**:
```
BM25(q, d) = Σ IDF(qi) * (f(qi, d) * (k1 + 1)) / (f(qi, d) + k1 * (1 - b + b * |d| / avgdl))

Where:
- q = query terms
- d = document
- f(qi, d) = term frequency of qi in d
- IDF(qi) = inverse document frequency of qi
- |d| = document length
- avgdl = average document length
- k1 = 1.5 (term frequency saturation)
- b = 0.75 (length normalization)
```

**Process**:
1. Tokenize query: "what is dbt" → ["what", "is", "dbt"]
2. Remove stop words: ["dbt"]
3. For each document:
   - Calculate term frequencies
   - Apply BM25 formula
4. Sort by score descending

**ChromaDB Limitation**: No native BM25, so we implement via metadata filtering + keyword matching

**Workaround**:
```python
def _keyword_retrieval(self, query_text: str, k: int):
    keywords = self._extract_keywords(query_text)
    results = []
    for keyword in keywords:
        matches = self.vector_store.get(
            where={"$contains": keyword}  # Metadata filter
        )
        results.extend(matches)
    return self._score_bm25(results, keywords)
```

**Example Scores**:
```
Document 1: "dbt is..." (keyword: "dbt" appears 5 times) → 0.85
Document 2: "data build tool..." (keyword: "dbt" appears 1 time) → 0.60
Document 3: "SQL models..." (keyword: "dbt" not found) → 0.0
```

**Strengths**:
- Excellent for exact keyword matching
- Finds technical terms, acronyms, product names
- Fast (metadata index lookup)

**Weaknesses**:
- Misses semantic matches
- Requires exact word forms (no synonym handling)
- Poor for long, natural language queries

### Technique 3: Weighted Merge

**Algorithm**: Reciprocal Rank Fusion (RRF) with custom weights

**Process**:
1. **Normalize Scores**:
   - Semantic scores already 0-1 (cosine similarity)
   - BM25 scores normalized: `score / max_score`

2. **Apply Weights**:
   ```
   final_score = (semantic_score * 0.6) + (keyword_score * 0.4)
   ```

3. **Deduplicate**:
   - If same document in both results, use weighted score
   - If only in one result, use that score * weight

4. **Sort and Truncate**:
   - Sort by `final_score` descending
   - Return top-k (e.g., 20 for reranking)

**Example Merge**:

| Document | Semantic | Keyword | Weighted | Rank |
|----------|----------|---------|----------|------|
| Doc A | 0.92 | 0.85 | (0.92×0.6) + (0.85×0.4) = **0.892** | 1 |
| Doc B | 0.89 | 0.60 | (0.89×0.6) + (0.60×0.4) = **0.774** | 2 |
| Doc C | 0.75 | 0.00 | (0.75×0.6) + (0.00×0.4) = **0.450** | 3 |

**Code**: `query_retrieval.py` lines 500-550

```python
def _merge_retrieval_results(semantic_results, keyword_results):
    merged = {}
    for doc, score in semantic_results:
        doc_id = doc.metadata.get("id")
        merged[doc_id] = {
            "document": doc,
            "semantic_score": score,
            "keyword_score": 0.0
        }
    
    for doc, score in keyword_results:
        doc_id = doc.metadata.get("id")
        if doc_id in merged:
            merged[doc_id]["keyword_score"] = score
        else:
            merged[doc_id] = {
                "document": doc,
                "semantic_score": 0.0,
                "keyword_score": score
            }
    
    # Calculate weighted scores
    for doc_id in merged:
        sem = merged[doc_id]["semantic_score"]
        kw = merged[doc_id]["keyword_score"]
        merged[doc_id]["final_score"] = (sem * 0.6) + (kw * 0.4)
    
    # Sort and return
    sorted_docs = sorted(merged.values(), 
                         key=lambda x: x["final_score"], 
                         reverse=True)
    return [(d["document"], d["final_score"]) for d in sorted_docs]
```

**Tuning Weights**:
- **More semantic** (0.7/0.3): For conceptual questions
- **More keyword** (0.4/0.6): For technical lookups
- **Balanced** (0.6/0.4): Default, works well for most queries

---

## Phase 3: Domain-Specific Boosting

**Status**: ✓ Completed (generalized from medical domain)

**Purpose**: Boost documents containing domain-specific codes, identifiers, or patterns

**Configuration**:
```yaml
retrieval:
  domain_boost:
    enabled: true
    boost_multiplier: 1.5
    code_patterns:
      - "ERR-\\d{3,6}"          # Error codes: ERR-12345
      - "TICKET-\\d+"           # Ticket IDs: TICKET-999
      - "v\\d+\\.\\d+\\.\\d+"   # Version numbers: v1.2.3
```

### Boosting Algorithm

**Process**:
1. Extract codes from query using regex patterns
2. For each retrieved document:
   - Check if document contains matching codes
   - If found, multiply score by `boost_multiplier`

**Example**:

**Query**: "Fix for ERR-12345?"

**Extracted Codes**: `["ERR-12345"]`

**Documents**:
- Doc A: Contains "ERR-12345" → score 0.75 × 1.5 = **1.125** (boosted)
- Doc B: No error code → score 0.80 × 1.0 = **0.800** (unchanged)
- **Result**: Doc A ranks higher despite lower base score

**Code**: `query_retrieval.py` lines 570-620

```python
def _apply_domain_boosting(self, documents, query_text):
    # Extract codes from query
    codes = self._extract_domain_codes(query_text)
    if not codes:
        return documents
    
    boosted = []
    for doc, score in documents:
        content = doc.page_content
        metadata = doc.metadata
        
        # Check for code matches
        matched = any(code in content for code in codes)
        if matched:
            boosted_score = score * self.boost_multiplier
        else:
            boosted_score = score
        
        boosted.append((doc, boosted_score))
    
    return sorted(boosted, key=lambda x: x[1], reverse=True)
```

---

## Phase 4: Metadata Filtering

**Purpose**: Narrow results by source, date, file type, etc.

**Supported Filters**:

### Filter 1: Source Type
```python
filters = {"source_type": ["azure_devops"]}
# Returns only docs from Azure DevOps, excludes local files
```

### Filter 2: Date Range
```python
filters = {
    "date_from": "2025-01-01",
    "date_to": "2025-11-26"
}
# Returns only docs modified in this range
```

### Filter 3: File Type
```python
filters = {"file_type": [".sql", ".py"]}
# Returns only SQL and Python files
```

### Filter 4: Repository/Path
```python
filters = {
    "repository": "analytics-dbt",
    "path_contains": "/models/staging"
}
# Returns only docs from specific repo and path
```

**Implementation**:
```python
def _apply_filters(self, documents, filters):
    if not filters:
        return documents
    
    filtered = []
    for doc, score in documents:
        metadata = doc.metadata
        
        # Check each filter
        if "source_type" in filters:
            if metadata.get("source") not in filters["source_type"]:
                continue
        
        if "date_from" in filters:
            doc_date = metadata.get("last_modified")
            if doc_date < filters["date_from"]:
                continue
        
        # ... more filter checks
        
        filtered.append((doc, score))
    
    return filtered
```

---

## Phase 5: Cross-Encoder Reranking

**Status**: ✓ Completed (optional feature)

**Purpose**: Re-score documents using more sophisticated model for higher precision

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

**Configuration**:
```yaml
retrieval:
  reranking:
    enabled: true
    model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_k_initial: 20    # Documents to rerank
    top_k_final: 5       # Final results after reranking
    relevance_threshold: 0.3  # Minimum score to keep
```

### Why Rerank?

**Embedding Search Limitations**:
- Embeddings compress meaning into fixed-size vectors (1,536 dims)
- May lose nuance for long documents
- No direct query-document interaction

**Cross-Encoder Advantages**:
- Takes query + document as input pair
- Computes relevance score directly (not via embeddings)
- More accurate but slower (can't pre-compute)

### Reranking Process

**Step 1**: Over-fetch from vector store
```python
initial_results = hybrid_retrieval(query, k=20)  # Get 20 docs
```

**Step 2**: Score each with cross-encoder
```python
from sentence_transformers import CrossEncoder
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

scores = []
for doc in initial_results:
    score = model.predict([query, doc.page_content])
    scores.append((doc, score))
```

**Step 3**: Filter by threshold
```python
filtered = [(doc, s) for doc, s in scores if s >= 0.3]
```

**Step 4**: Sort and truncate
```python
final_results = sorted(filtered, key=lambda x: x[1], reverse=True)[:5]
```

**Example Scores**:

| Document | Hybrid Score | Rerank Score | Keep? |
|----------|--------------|--------------|-------|
| Doc A | 0.89 | **0.95** | ✓ |
| Doc B | 0.85 | **0.88** | ✓ |
| Doc C | 0.80 | **0.65** | ✓ |
| Doc D | 0.75 | **0.45** | ✓ |
| Doc E | 0.70 | **0.35** | ✓ |
| Doc F | 0.68 | **0.25** | ✗ (below threshold) |

**Performance**:
- **Latency**: ~50ms for 20 documents (CPU)
- **Accuracy Improvement**: +5-10% hit rate vs hybrid alone
- **Trade-off**: 50ms added latency for better precision

**When to Use**:
- ✓ High-stakes queries (compliance, audit)
- ✓ Ambiguous queries needing precision
- ✗ Real-time applications (< 100ms requirement)
- ✗ Very large result sets (> 50 docs)

---

## Phase 6: Context Assembly

**Purpose**: Prepare retrieved documents for LLM consumption

**Configuration**:
```yaml
llm:
  max_context_tokens: 6000  # ~24,000 characters
  context_template: |
    Document {index}: {filename}
    Source: {source_type}
    
    {content}
    
    ---
```

### Assembly Process

**Step 1**: Extract content from documents
```python
documents = [
    {"content": "dbt is...", "metadata": {"filename": "dbt_intro.md"}},
    {"content": "Models are...", "metadata": {"filename": "models.sql"}},
    # ...
]
```

**Step 2**: Format with template
```python
context = ""
for i, doc in enumerate(documents):
    context += f"Document {i+1}: {doc['metadata']['filename']}\n"
    context += f"Source: {doc['metadata']['source']}\n\n"
    context += doc['content'] + "\n\n---\n\n"
```

**Step 3**: Token counting
```python
import tiktoken
encoder = tiktoken.encoding_for_model("gpt-4")
tokens = encoder.encode(context)
if len(tokens) > max_context_tokens:
    # Truncate intelligently
    context = smart_truncate(context, max_context_tokens)
```

**Smart Truncation**:
- Preserves complete documents (no mid-document cuts)
- Keeps highest-scored documents
- Adds "..." indicator if truncated

**Example Context**:
```
Document 1: dbt_introduction.md
Source: azure_devops

dbt (data build tool) is a transformation workflow that helps teams quickly and collaboratively deploy analytics code following software engineering best practices like modularity, portability, CI/CD, and documentation.

---

Document 2: models_staging.sql
Source: azure_devops

{{ config(materialized='incremental') }}

SELECT
    claim_id,
    patient_id,
    claim_amount
FROM {{ ref('raw_claims') }}

---

Document 3: dbt_best_practices.md
Source: local_file

Best practices for dbt models:
1. Use staging models for one-to-one source mapping
2. Apply business logic in intermediate models
3. Create marts for end-user consumption

---
```

---

## Phase 7: Retrieval Metrics

**Module**: `EvaluationLoggingModule`

**Metrics Tracked**:

### 1. Hit Rate
**Definition**: Did top-k results contain the answer?

**Calculation**:
```python
hit_rate = 1 if any(doc contains answer for doc in top_k) else 0
```

**Logged Per Query**: Binary 0 or 1

**Aggregated**: Average over all queries

**Example**: 85% hit rate = answer in top-5 for 85% of queries

### 2. Mean Reciprocal Rank (MRR)
**Definition**: Average reciprocal of rank where answer appears

**Formula**:
```
MRR = (1/n) * Σ (1/rank_i)

Where rank_i = position of first relevant document
```

**Example**:
- Query 1: Answer at rank 1 → 1/1 = 1.0
- Query 2: Answer at rank 3 → 1/3 = 0.33
- Query 3: Answer at rank 5 → 1/5 = 0.2
- MRR = (1.0 + 0.33 + 0.2) / 3 = **0.51**

### 3. Precision@K
**Definition**: % of top-k results that are relevant

**Formula**:
```
Precision@K = (# relevant docs in top-k) / k
```

**Example**: 3 relevant docs in top-5 → 3/5 = **0.6**

### 4. Retrieval Time
**Definition**: Latency from query to context assembly

**Components**:
- Embedding: ~50ms
- Semantic search: ~100ms
- Keyword search: ~30ms
- Merge: ~5ms
- Reranking: ~50ms (if enabled)
- **Total**: ~235ms

### 5. Document Count
**Logged**: Number of documents retrieved before/after filtering

**Example**:
```json
{
  "documents_retrieved": 20,
  "documents_after_filter": 18,
  "documents_after_rerank": 5
}
```

---

## Configuration Examples

### High Precision (Compliance, Audit)
```yaml
retrieval:
  top_k: 3  # Fewer, higher-quality results
  hybrid_search:
    semantic_weight: 0.5
    keyword_weight: 0.5  # Balanced for exact matches
  reranking:
    enabled: true
    top_k_final: 3
    relevance_threshold: 0.5  # Stricter threshold
```

### High Recall (Exploratory Search)
```yaml
retrieval:
  top_k: 10  # More results
  hybrid_search:
    semantic_weight: 0.7
    keyword_weight: 0.3  # Favor semantic for broader matches
  reranking:
    enabled: false  # Skip for speed
```

### Fast Queries (Real-Time)
```yaml
retrieval:
  top_k: 5
  hybrid_search:
    enabled: false  # Semantic only
  reranking:
    enabled: false
  # Total latency: ~150ms
```

---

## Troubleshooting

### Issue 1: Low Hit Rate (< 70%)

**Diagnosis**:
```python
# Check if documents are actually relevant
results = retrieval.process_query("query")
for doc in results:
    print(doc.page_content[:200])  # Preview content
```

**Solutions**:
- Increase `top_k` (try 10 instead of 5)
- Adjust hybrid weights (try 0.7/0.3 semantic/keyword)
- Enable reranking
- Check if corpus contains relevant docs

### Issue 2: High Latency (> 500ms)

**Diagnosis**:
```python
import time
start = time.time()
embedding = model.embed_query(query)
print(f"Embedding: {time.time() - start}s")

start = time.time()
results = vector_store.search(embedding)
print(f"Search: {time.time() - start}s")
```

**Solutions**:
- Disable reranking for non-critical queries
- Use FAISS instead of ChromaDB (faster search)
- Reduce `top_k_initial` for reranking
- Optimize ChromaDB index (recreate if corrupted)

### Issue 3: Irrelevant Results

**Diagnosis**: Semantic drift (embeddings not well-tuned)

**Solutions**:
- Switch to `text-embedding-3-large` (better quality)
- Add domain-specific boosting patterns
- Use stricter reranking threshold (0.5 instead of 0.3)
- Re-chunk corpus with smaller `chunk_size`

---

## Summary

The retrieval pipeline achieves 85-95% accuracy through:

1. **Hybrid Search**: 60% semantic + 40% keyword
2. **Domain Boosting**: 1.5x multiplier for code matches
3. **Cross-Encoder Reranking**: ms-marco-MiniLM for precision
4. **Smart Context Assembly**: Preserves complete documents
5. **Comprehensive Metrics**: Hit rate, MRR, precision tracked

**Result**: Sub-250ms retrieval with high relevance for LLM answer generation.
