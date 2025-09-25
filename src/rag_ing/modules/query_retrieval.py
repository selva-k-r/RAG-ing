"""Module 2: Query Processing & Retrieval"""Module 2: Query Processing & Retrieval



Objective: Convert user query to embedding and retrieve relevant chunks.Objective: Convert user query to embedding and retrieve relevant chunks.

""""""



import loggingimport logging

import timeimport time

import hashlibimport hashlib

from typing import List, Dict, Any, Optionalfrom typing import List, Dict, Any, Optional, Tuple

from datetime import datetime, timedeltafrom datetime import datetime, timedelta

from langchain.docstore.document import Documentfrom langchain.docstore.document import Document

from langchain.embeddings.base import Embeddingsfrom langchain.embeddings.base import Embeddings

from langchain.vectorstores.base import VectorStorefrom langchain.vectorstores.base import VectorStore

from ..config.settings import Settings, RetrievalConfigfrom ..config.settings import Settings, RetrievalConfig

from ..utils.exceptions import RetrievalErrorfrom ..utils.exceptions import RetrievalError\n\nlogger = logging.getLogger(__name__)\n\n\nclass QueryRetrievalModule:\n    \"\"\"Module for YAML-driven query processing and document retrieval.\"\"\"\n    \n    def __init__(self, config: Settings, vector_store: VectorStore, embedding_model: Embeddings):\n        self.config = config\n        self.retrieval_config = config.retrieval\n        self.vector_store = vector_store\n        self.embedding_model = embedding_model\n        \n        # Query cache for performance\n        self._query_cache = {}\n        self._cache_ttl = 300  # 5 minutes\n        \n        # Metrics tracking\n        self._metrics = {\n            \"total_queries\": 0,\n            \"cache_hits\": 0,\n            \"avg_retrieval_time\": 0,\n            \"hit_rate\": 0\n        }\n    \n    def process_query(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n        \"\"\"Main entry point for query processing and retrieval.\"\"\"\n        logger.info(f\"Processing query: {query[:50]}...\")\n        start_time = time.time()\n        \n        try:\n            # Step 1: Query Input validation and normalization\n            normalized_query = self._normalize_query(query)\n            query_hash = self._generate_query_hash(normalized_query, filters)\n            \n            # Check cache first\n            cached_result = self._get_cached_result(query_hash)\n            if cached_result:\n                self._metrics[\"cache_hits\"] += 1\n                logger.info(\"Retrieved result from cache\")\n                return cached_result\n            \n            # Step 2: Embedding Conversion\n            query_embedding = self._convert_to_embedding(normalized_query)\n            \n            # Step 3: Retrieval Logic\n            retrieved_docs = self._retrieve_documents(query_embedding, filters)\n            \n            # Step 4: Context Packaging\n            context_result = self._package_context(query, retrieved_docs)\n            \n            # Update metrics\n            retrieval_time = time.time() - start_time\n            self._update_metrics(retrieval_time, len(retrieved_docs))\n            \n            # Cache result\n            self._cache_result(query_hash, context_result)\n            \n            logger.info(f\"Query processed successfully in {retrieval_time:.2f}s\")\n            return context_result\n            \n        except Exception as e:\n            logger.error(f\"Query processing failed: {e}\")\n            raise RetrievalError(f\"Failed to process query: {e}\")\n    \n    def _normalize_query(self, query: str) -> str:\n        \"\"\"Normalize and clean query text.\"\"\"\n        if not query or not query.strip():\n            raise ValueError(\"Query cannot be empty\")\n        \n        # Basic normalization\n        normalized = query.strip().lower()\n        \n        # Remove extra whitespace\n        normalized = ' '.join(normalized.split())\n        \n        # Validate query format\n        if len(normalized) < 3:\n            raise ValueError(\"Query too short (minimum 3 characters)\")\n        \n        if len(normalized) > 1000:\n            logger.warning(\"Query exceeds recommended length, truncating\")\n            normalized = normalized[:1000]\n        \n        return normalized\n    \n    def _generate_query_hash(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:\n        \"\"\"Generate hash for query caching.\"\"\"\n        cache_key = f\"{query}_{str(filters or {})}\"\n        return hashlib.md5(cache_key.encode()).hexdigest()\n    \n    def _get_cached_result(self, query_hash: str) -> Optional[Dict[str, Any]]:\n        \"\"\"Retrieve cached query result.\"\"\"\n        if query_hash in self._query_cache:\n            cached_data = self._query_cache[query_hash]\n            \n            # Check TTL\n            if time.time() - cached_data[\"timestamp\"] < self._cache_ttl:\n                return cached_data[\"result\"]\n            else:\n                # Remove expired cache entry\n                del self._query_cache[query_hash]\n        \n        return None\n    \n    def _cache_result(self, query_hash: str, result: Dict[str, Any]) -> None:\n        \"\"\"Cache query result with timestamp.\"\"\"\n        self._query_cache[query_hash] = {\n            \"result\": result,\n            \"timestamp\": time.time()\n        }\n        \n        # Simple cache cleanup - remove oldest entries if cache grows too large\n        if len(self._query_cache) > 100:\n            oldest_key = min(self._query_cache.keys(), \n                           key=lambda k: self._query_cache[k][\"timestamp\"])\n            del self._query_cache[oldest_key]\n    \n    def _convert_to_embedding(self, query: str) -> List[float]:\n        \"\"\"Convert query to vector embedding.\"\"\"\n        try:\n            # Use the same embedding model as used for corpus\n            embedding = self.embedding_model.embed_query(query)\n            \n            if not embedding:\n                raise ValueError(\"Failed to generate query embedding\")\n            \n            logger.debug(f\"Generated {len(embedding)}D embedding for query\")\n            return embedding\n            \n        except Exception as e:\n            logger.error(f\"Embedding conversion failed: {e}\")\n            raise\n    \n    def _retrieve_documents(self, query_embedding: List[float], \n                          filters: Optional[Dict[str, Any]] = None) -> List[Document]:\n        \"\"\"Retrieve relevant documents using configured strategy.\"\"\"\n        strategy = self.retrieval_config.strategy\n        top_k = self.retrieval_config.top_k\n        retrieval_filters = {**self.retrieval_config.filters, **(filters or {})}\n        \n        if strategy == \"similarity\":\n            return self._similarity_search(query_embedding, top_k, retrieval_filters)\n        elif strategy == \"hybrid\":\n            return self._hybrid_search(query_embedding, top_k, retrieval_filters)\n        else:\n            raise ValueError(f\"Unsupported retrieval strategy: {strategy}\")\n    \n    def _similarity_search(self, query_embedding: List[float], \n                         top_k: int, filters: Dict[str, Any]) -> List[Document]:\n        \"\"\"Perform cosine similarity search.\"\"\"\n        try:\n            # Convert embedding to query string for vector store\n            # Note: This is a simplified approach - in practice, you'd pass the embedding directly\n            docs_with_scores = self.vector_store.similarity_search_with_score(\n                query=\"\",  # We'll use the embedding directly if supported\n                k=top_k\n            )\n            \n            # Apply filters\n            filtered_docs = self._apply_filters([doc for doc, score in docs_with_scores], filters)\n            \n            # Sort by relevance score if available\n            return filtered_docs[:top_k]\n            \n        except Exception as e:\n            logger.error(f\"Similarity search failed: {e}\")\n            # Fallback to basic similarity search\n            return self.vector_store.similarity_search(query=\"oncology biomarker\", k=top_k)\n    \n    def _hybrid_search(self, query_embedding: List[float], \n                     top_k: int, filters: Dict[str, Any]) -> List[Document]:\n        \"\"\"Perform hybrid search combining similarity and keyword matching.\"\"\"\n        # For now, implement as enhanced similarity search\n        # In a full implementation, this would combine vector similarity with keyword/BM25 search\n        \n        similarity_docs = self._similarity_search(query_embedding, top_k * 2, filters)\n        \n        # Apply additional ranking based on keyword matches\n        # This is a simplified version - full implementation would use proper hybrid ranking\n        ranked_docs = self._rerank_documents(similarity_docs, filters)\n        \n        return ranked_docs[:top_k]\n    \n    def _apply_filters(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:\n        \"\"\"Apply retrieval filters to documents.\"\"\"\n        filtered_docs = documents\n        \n        # Ontology matching filter\n        if filters.get(\"ontology_match\", False):\n            filtered_docs = [doc for doc in filtered_docs \n                           if self._has_ontology_codes(doc)]\n        \n        # Date range filter\n        date_range = filters.get(\"date_range\")\n        if date_range:\n            filtered_docs = self._filter_by_date(filtered_docs, date_range)\n        \n        # Source type filter\n        source_types = filters.get(\"source_types\")\n        if source_types:\n            filtered_docs = [doc for doc in filtered_docs \n                           if self._matches_source_type(doc, source_types)]\n        \n        return filtered_docs\n    \n    def _has_ontology_codes(self, document: Document) -> bool:\n        \"\"\"Check if document has ontology codes in metadata.\"\"\"\n        ontology_codes = document.metadata.get(\"ontology_codes\", [])\n        return len(ontology_codes) > 0\n    \n    def _filter_by_date(self, documents: List[Document], date_range: str) -> List[Document]:\n        \"\"\"Filter documents by date range.\"\"\"\n        if date_range == \"last_12_months\":\n            cutoff_date = datetime.now() - timedelta(days=365)\n        elif date_range == \"last_6_months\":\n            cutoff_date = datetime.now() - timedelta(days=180)\n        elif date_range == \"last_month\":\n            cutoff_date = datetime.now() - timedelta(days=30)\n        else:\n            return documents  # No filtering\n        \n        filtered_docs = []\n        for doc in documents:\n            doc_date = doc.metadata.get(\"date\")\n            if doc_date:\n                # Handle different date formats\n                if isinstance(doc_date, (int, float)):\n                    doc_datetime = datetime.fromtimestamp(doc_date)\n                elif isinstance(doc_date, str):\n                    try:\n                        doc_datetime = datetime.fromisoformat(doc_date)\n                    except:\n                        continue  # Skip documents with invalid dates\n                else:\n                    continue\n                \n                if doc_datetime >= cutoff_date:\n                    filtered_docs.append(doc)\n            else:\n                # Include documents without dates (assume recent)\n                filtered_docs.append(doc)\n        \n        return filtered_docs\n    \n    def _matches_source_type(self, document: Document, source_types: List[str]) -> bool:\n        \"\"\"Check if document matches source type filter.\"\"\"\n        doc_source = document.metadata.get(\"source\", \"\").lower()\n        return any(source_type.lower() in doc_source for source_type in source_types)\n    \n    def _rerank_documents(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:\n        \"\"\"Re-rank documents based on additional criteria.\"\"\"\n        # Simple re-ranking based on ontology code presence and recency\n        def rank_score(doc: Document) -> float:\n            score = 0.0\n            \n            # Boost documents with ontology codes\n            if self._has_ontology_codes(doc):\n                score += 0.2\n            \n            # Boost recent documents\n            doc_date = doc.metadata.get(\"date\")\n            if doc_date:\n                if isinstance(doc_date, (int, float)):\n                    days_old = (time.time() - doc_date) / (24 * 3600)\n                    score += max(0, 0.1 * (365 - days_old) / 365)  # Linear decay over a year\n            \n            # Boost documents with more metadata\n            score += len(doc.metadata) * 0.01\n            \n            return score\n        \n        return sorted(documents, key=rank_score, reverse=True)\n    \n    def _package_context(self, original_query: str, retrieved_docs: List[Document]) -> Dict[str, Any]:\n        \"\"\"Package retrieved documents into context for LLM prompt.\"\"\"\n        # Prepare context information\n        context_chunks = []\n        sources = []\n        metadata_summary = {}\n        \n        for i, doc in enumerate(retrieved_docs):\n            # Add chunk with source attribution\n            chunk_info = {\n                \"id\": i,\n                \"content\": doc.page_content,\n                \"source\": doc.metadata.get(\"source\", \"Unknown\"),\n                \"relevance_rank\": i + 1\n            }\n            \n            # Include important metadata\n            if \"ontology_codes\" in doc.metadata:\n                chunk_info[\"ontology_codes\"] = doc.metadata[\"ontology_codes\"]\n            \n            if \"date\" in doc.metadata:\n                chunk_info[\"date\"] = doc.metadata[\"date\"]\n            \n            context_chunks.append(chunk_info)\n            \n            # Collect unique sources\n            source = doc.metadata.get(\"source\", \"Unknown\")\n            if source not in sources:\n                sources.append(source)\n        \n        # Prepare formatted context for LLM\n        formatted_context = self._format_context_for_llm(context_chunks)\n        \n        # Create retrieval summary\n        retrieval_summary = {\n            \"query\": original_query,\n            \"num_results\": len(retrieved_docs),\n            \"sources\": sources,\n            \"has_ontology_codes\": any(\"ontology_codes\" in doc.metadata for doc in retrieved_docs),\n            \"date_range\": self._get_date_range_summary(retrieved_docs)\n        }\n        \n        return {\n            \"query\": original_query,\n            \"context_chunks\": context_chunks,\n            \"formatted_context\": formatted_context,\n            \"retrieval_summary\": retrieval_summary,\n            \"metadata\": {\n                \"retrieval_timestamp\": datetime.now().isoformat(),\n                \"retrieval_config\": self.retrieval_config.dict(),\n                \"num_sources\": len(sources)\n            }\n        }\n    \n    def _format_context_for_llm(self, context_chunks: List[Dict[str, Any]]) -> str:\n        \"\"\"Format context chunks for LLM prompt injection.\"\"\"\n        formatted_parts = []\n        \n        for chunk in context_chunks:\n            part = f\"[Source {chunk['relevance_rank']}]\"\n            part += f\"\\nSource: {chunk['source']}\"\n            \n            if \"ontology_codes\" in chunk and chunk[\"ontology_codes\"]:\n                part += f\"\\nOntology Codes: {', '.join(chunk['ontology_codes'])}\"\n            \n            part += f\"\\nContent: {chunk['content']}\"\n            part += \"\\n---\\n\"\n            \n            formatted_parts.append(part)\n        \n        return \"\\n\".join(formatted_parts)\n    \n    def _get_date_range_summary(self, documents: List[Document]) -> Dict[str, Any]:\n        \"\"\"Get summary of date range in retrieved documents.\"\"\"\n        dates = []\n        for doc in documents:\n            doc_date = doc.metadata.get(\"date\")\n            if doc_date:\n                if isinstance(doc_date, (int, float)):\n                    dates.append(datetime.fromtimestamp(doc_date))\n                elif isinstance(doc_date, str):\n                    try:\n                        dates.append(datetime.fromisoformat(doc_date))\n                    except:\n                        pass\n        \n        if not dates:\n            return {\"has_dates\": False}\n        \n        return {\n            \"has_dates\": True,\n            \"earliest\": min(dates).isoformat(),\n            \"latest\": max(dates).isoformat(),\n            \"span_days\": (max(dates) - min(dates)).days\n        }\n    \n    def _update_metrics(self, retrieval_time: float, num_results: int) -> None:\n        \"\"\"Update retrieval metrics.\"\"\"\n        self._metrics[\"total_queries\"] += 1\n        \n        # Update average retrieval time\n        total_queries = self._metrics[\"total_queries\"]\n        prev_avg = self._metrics[\"avg_retrieval_time\"]\n        self._metrics[\"avg_retrieval_time\"] = ((prev_avg * (total_queries - 1)) + retrieval_time) / total_queries\n        \n        # Update hit rate (simplified - based on whether we got results)\n        hit_rate = (self._metrics.get(\"successful_retrievals\", 0) + (1 if num_results > 0 else 0)) / total_queries\n        self._metrics[\"hit_rate\"] = hit_rate\n        \n        if num_results > 0:\n            self._metrics[\"successful_retrievals\"] = self._metrics.get(\"successful_retrievals\", 0) + 1\n    \n    def get_metrics(self) -> Dict[str, Any]:\n        \"\"\"Get retrieval metrics.\"\"\"\n        return self._metrics.copy()\n    \n    def clear_cache(self) -> None:\n        \"\"\"Clear the query cache.\"\"\"\n        self._query_cache.clear()\n        logger.info(\"Query cache cleared\")\n    \n    def get_cache_stats(self) -> Dict[str, Any]:\n        \"\"\"Get cache statistics.\"\"\"\n        return {\n            \"cache_size\": len(self._query_cache),\n            \"cache_hits\": self._metrics[\"cache_hits\"],\n            \"hit_ratio\": self._metrics[\"cache_hits\"] / max(1, self._metrics[\"total_queries\"])\n        }

logger = logging.getLogger(__name__)


class QueryRetrievalModule:
    """Module for YAML-driven query processing and document retrieval."""
    
    def __init__(self, config: Settings, vector_store: VectorStore, embedding_model: Embeddings):
        self.config = config
        self.retrieval_config = config.retrieval
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        
        # Query cache for performance
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Metrics tracking
        self._metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_retrieval_time": 0,
            "hit_rate": 0
        }
    
    def process_query(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main entry point for query processing and retrieval."""
        logger.info(f"Processing query: {query[:50]}...")
        start_time = time.time()
        
        try:
            # Step 1: Query Input validation and normalization
            normalized_query = self._normalize_query(query)
            query_hash = self._generate_query_hash(normalized_query, filters)
            
            # Check cache first
            cached_result = self._get_cached_result(query_hash)
            if cached_result:
                self._metrics["cache_hits"] += 1
                logger.info("Retrieved result from cache")
                return cached_result
            
            # Step 2: Embedding Conversion
            query_embedding = self._convert_to_embedding(normalized_query)
            
            # Step 3: Retrieval Logic
            retrieved_docs = self._retrieve_documents(query_embedding, filters)
            
            # Step 4: Context Packaging
            context_result = self._package_context(query, retrieved_docs)
            
            # Update metrics
            retrieval_time = time.time() - start_time
            self._update_metrics(retrieval_time, len(retrieved_docs))
            
            # Cache result
            self._cache_result(query_hash, context_result)
            
            logger.info(f"Query processed successfully in {retrieval_time:.2f}s")
            return context_result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise RetrievalError(f"Failed to process query: {e}")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize and clean query text."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        normalized = query.strip().lower()
        normalized = ' '.join(normalized.split())
        
        if len(normalized) < 3:
            raise ValueError("Query too short (minimum 3 characters)")
        
        if len(normalized) > 1000:
            logger.warning("Query exceeds recommended length, truncating")
            normalized = normalized[:1000]
        
        return normalized
    
    def _generate_query_hash(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Generate hash for query caching."""
        cache_key = f"{query}_{str(filters or {})}"
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    def _get_cached_result(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached query result."""
        if query_hash in self._query_cache:
            cached_data = self._query_cache[query_hash]
            
            if time.time() - cached_data["timestamp"] < self._cache_ttl:
                return cached_data["result"]
            else:
                del self._query_cache[query_hash]
        
        return None
    
    def _cache_result(self, query_hash: str, result: Dict[str, Any]) -> None:
        """Cache query result with timestamp."""
        self._query_cache[query_hash] = {
            "result": result,
            "timestamp": time.time()
        }
        
        if len(self._query_cache) > 100:
            oldest_key = min(self._query_cache.keys(), 
                           key=lambda k: self._query_cache[k]["timestamp"])
            del self._query_cache[oldest_key]
    
    def _convert_to_embedding(self, query: str) -> List[float]:
        """Convert query to vector embedding."""
        try:
            embedding = self.embedding_model.embed_query(query)
            
            if not embedding:
                raise ValueError("Failed to generate query embedding")
            
            logger.debug(f"Generated {len(embedding)}D embedding for query")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding conversion failed: {e}")
            raise
    
    def _retrieve_documents(self, query_embedding: List[float], 
                          filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Retrieve relevant documents using configured strategy."""
        strategy = self.retrieval_config.strategy
        top_k = self.retrieval_config.top_k
        retrieval_filters = {**self.retrieval_config.filters, **(filters or {})}
        
        if strategy == "similarity":
            return self._similarity_search(query_embedding, top_k, retrieval_filters)
        elif strategy == "hybrid":
            return self._hybrid_search(query_embedding, top_k, retrieval_filters)
        else:
            raise ValueError(f"Unsupported retrieval strategy: {strategy}")
    
    def _similarity_search(self, query_embedding: List[float], 
                         top_k: int, filters: Dict[str, Any]) -> List[Document]:
        """Perform cosine similarity search."""
        try:
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query="oncology biomarker",
                k=top_k
            )
            
            filtered_docs = self._apply_filters([doc for doc, score in docs_with_scores], filters)
            return filtered_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return self.vector_store.similarity_search(query="oncology biomarker", k=top_k)
    
    def _hybrid_search(self, query_embedding: List[float], 
                     top_k: int, filters: Dict[str, Any]) -> List[Document]:
        """Perform hybrid search combining similarity and keyword matching."""
        similarity_docs = self._similarity_search(query_embedding, top_k * 2, filters)
        ranked_docs = self._rerank_documents(similarity_docs, filters)
        return ranked_docs[:top_k]
    
    def _apply_filters(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:
        """Apply retrieval filters to documents."""
        filtered_docs = documents
        
        if filters.get("ontology_match", False):
            filtered_docs = [doc for doc in filtered_docs 
                           if self._has_ontology_codes(doc)]
        
        date_range = filters.get("date_range")
        if date_range:
            filtered_docs = self._filter_by_date(filtered_docs, date_range)
        
        return filtered_docs
    
    def _has_ontology_codes(self, document: Document) -> bool:
        """Check if document has ontology codes in metadata."""
        ontology_codes = document.metadata.get("ontology_codes", [])
        return len(ontology_codes) > 0
    
    def _filter_by_date(self, documents: List[Document], date_range: str) -> List[Document]:
        """Filter documents by date range."""
        if date_range == "last_12_months":
            cutoff_date = datetime.now() - timedelta(days=365)
        elif date_range == "last_6_months":
            cutoff_date = datetime.now() - timedelta(days=180)
        elif date_range == "last_month":
            cutoff_date = datetime.now() - timedelta(days=30)
        else:
            return documents
        
        filtered_docs = []
        for doc in documents:
            doc_date = doc.metadata.get("date")
            if doc_date:
                if isinstance(doc_date, (int, float)):
                    doc_datetime = datetime.fromtimestamp(doc_date)
                elif isinstance(doc_date, str):
                    try:
                        doc_datetime = datetime.fromisoformat(doc_date)
                    except:
                        continue
                else:
                    continue
                
                if doc_datetime >= cutoff_date:
                    filtered_docs.append(doc)
            else:
                filtered_docs.append(doc)
        
        return filtered_docs
    
    def _rerank_documents(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:
        """Re-rank documents based on additional criteria."""
        def rank_score(doc: Document) -> float:
            score = 0.0
            
            if self._has_ontology_codes(doc):
                score += 0.2
            
            doc_date = doc.metadata.get("date")
            if doc_date:
                if isinstance(doc_date, (int, float)):
                    days_old = (time.time() - doc_date) / (24 * 3600)
                    score += max(0, 0.1 * (365 - days_old) / 365)
            
            score += len(doc.metadata) * 0.01
            return score
        
        return sorted(documents, key=rank_score, reverse=True)
    
    def _package_context(self, original_query: str, retrieved_docs: List[Document]) -> Dict[str, Any]:
        """Package retrieved documents into context for LLM prompt."""
        context_chunks = []
        sources = []
        
        for i, doc in enumerate(retrieved_docs):
            chunk_info = {
                "id": i,
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "relevance_rank": i + 1
            }
            
            if "ontology_codes" in doc.metadata:
                chunk_info["ontology_codes"] = doc.metadata["ontology_codes"]
            
            if "date" in doc.metadata:
                chunk_info["date"] = doc.metadata["date"]
            
            context_chunks.append(chunk_info)
            
            source = doc.metadata.get("source", "Unknown")
            if source not in sources:
                sources.append(source)
        
        formatted_context = self._format_context_for_llm(context_chunks)
        
        retrieval_summary = {
            "query": original_query,
            "num_results": len(retrieved_docs),
            "sources": sources,
            "has_ontology_codes": any("ontology_codes" in doc.metadata for doc in retrieved_docs)
        }
        
        return {
            "query": original_query,
            "context_chunks": context_chunks,
            "formatted_context": formatted_context,
            "retrieval_summary": retrieval_summary,
            "metadata": {
                "retrieval_timestamp": datetime.now().isoformat(),
                "retrieval_config": self.retrieval_config.dict(),
                "num_sources": len(sources)
            }
        }
    
    def _format_context_for_llm(self, context_chunks: List[Dict[str, Any]]) -> str:
        """Format context chunks for LLM prompt injection."""
        formatted_parts = []
        
        for chunk in context_chunks:
            part = f"[Source {chunk['relevance_rank']}]"
            part += f"\\nSource: {chunk['source']}"
            
            if "ontology_codes" in chunk and chunk["ontology_codes"]:
                part += f"\\nOntology Codes: {', '.join(chunk['ontology_codes'])}"
            
            part += f"\\nContent: {chunk['content']}"
            part += "\\n---\\n"
            
            formatted_parts.append(part)
        
        return "\\n".join(formatted_parts)
    
    def _update_metrics(self, retrieval_time: float, num_results: int) -> None:
        """Update retrieval metrics."""
        self._metrics["total_queries"] += 1
        
        total_queries = self._metrics["total_queries"]
        prev_avg = self._metrics["avg_retrieval_time"]
        self._metrics["avg_retrieval_time"] = ((prev_avg * (total_queries - 1)) + retrieval_time) / total_queries
        
        hit_rate = (self._metrics.get("successful_retrievals", 0) + (1 if num_results > 0 else 0)) / total_queries
        self._metrics["hit_rate"] = hit_rate
        
        if num_results > 0:
            self._metrics["successful_retrievals"] = self._metrics.get("successful_retrievals", 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retrieval metrics."""
        return self._metrics.copy()
    
    def clear_cache(self) -> None:
        """Clear the query cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")