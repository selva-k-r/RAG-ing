
"""Module 2: Query Processing & Retrieval

Objective: Convert user query to embedding and retrieve relevant chunks.
"""

import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from ..config.settings import Settings, RetrievalConfig
from ..utils.exceptions import RetrievalError

logger = logging.getLogger(__name__)


class QueryRetrievalModule:
    """Module for YAML-driven query processing and document retrieval."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.retrieval_config = config.retrieval
        
        # Initialize vector store and embedding model internally
        self.vector_store = None
        self.embedding_model = None
        self._initialize_components()
        
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
    
    def _initialize_components(self):
        """Initialize vector store and embedding model based on configuration."""
        logger.info("Initializing vector store and embedding model components...")
        
        try:
            # Initialize embedding model with fallback
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                
                embedding_config = self.config.embedding_model
                
                # Map model names to actual HuggingFace model identifiers
                model_mapping = {
                    "pubmedbert": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
                    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
                    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2"
                }
                
                model_name = model_mapping.get(embedding_config.name, embedding_config.name)
                logger.info(f"Loading embedding model: {model_name}")
                
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={'device': embedding_config.device}
                )
                logger.info(f"Embedding model loaded: {embedding_config.name}")
            except Exception as e:
                logger.warning(f"Failed to load HuggingFaceEmbeddings: {e}")
                # Fallback to a simple mock embedding for demo purposes
                logger.info("Using mock embedding model for demonstration")
                self.embedding_model = self._create_mock_embedding_model()
            
            # Initialize vector store
            vector_store_config = self.config.vector_store
            
            if vector_store_config.type == "chroma":
                try:
                    from langchain_chroma import Chroma
                except ImportError:
                    try:
                        from langchain_community.vectorstores import Chroma
                    except ImportError:
                        logger.warning("ChromaDB integration not available, using mock vector store")
                        self.vector_store = self._create_mock_vector_store()
                        return
                
                import chromadb
                from pathlib import Path
                
                # Setup ChromaDB
                persist_directory = Path(vector_store_config.path)
                persist_directory.mkdir(parents=True, exist_ok=True)
                
                # Connect to existing ChromaDB collection if it exists
                try:
                    self.vector_store = Chroma(
                        collection_name=vector_store_config.collection_name,
                        persist_directory=str(persist_directory),
                        embedding_function=self.embedding_model
                    )
                    logger.info(f"ChromaDB vector store loaded from {persist_directory}")
                except Exception as e:
                    logger.warning(f"Failed to load existing vector store: {e}")
                    logger.info("Using mock vector store for demonstration")
                    self.vector_store = self._create_mock_vector_store()
                    
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self.embedding_model = None
            self.vector_store = None
    
    def _create_mock_embedding_model(self):
        """Create a simple mock embedding model for demonstration purposes."""
        class MockEmbeddingModel:
            def embed_query(self, text):
                # Simple mock embedding - in production this would use real embeddings
                import hashlib
                import numpy as np
                
                # Create a deterministic "embedding" from text hash
                hash_obj = hashlib.md5(text.encode())
                seed = int(hash_obj.hexdigest(), 16) % 2**32
                np.random.seed(seed)
                return np.random.rand(768).tolist()  # Mock 768-dim embedding to match PubMedBERT
                
            def embed_documents(self, texts):
                return [self.embed_query(text) for text in texts]
        
        return MockEmbeddingModel()
    
    def _create_mock_vector_store(self):
        """Create a simple mock vector store for demonstration purposes."""
        class MockVectorStore:
            def __init__(self):
                # Mock some sample documents for demonstration
                self.documents = [
                    {"content": "This document discusses oncology treatment protocols, chemotherapy options, and patient care management.", "metadata": {"source": "sample.txt"}},
                    {"content": "Cancer research shows promising results with immunotherapy and targeted treatments for various cancer types.", "metadata": {"source": "sample.pdf"}}, 
                    {"content": "Clinical trials demonstrate effectiveness of combination therapy approaches in oncology practice.", "metadata": {"source": "sample.md"}}
                ]
            
            def similarity_search(self, query, k=3, **kwargs):
                # Mock similarity search - return all documents for demo
                from langchain.schema import Document
                return [Document(page_content=doc["content"], metadata=doc["metadata"]) for doc in self.documents[:k]]
        
        return MockVectorStore()
    
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
        

        class QueryRetrievalModule:
            """Module for YAML-driven query processing and document retrieval."""
            def __init__(self, config: Settings, vector_store: VectorStore, embedding_model: Embeddings):
                self.config = config
                self.retrieval_config = config.retrieval
                self.vector_store = vector_store
                self.embedding_model = embedding_model
                self._query_cache = {}
                self._cache_ttl = 300  # 5 minutes
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
            normalized_query = self._normalize_query(query)
            query_hash = self._generate_query_hash(normalized_query, filters)
            cached_result = self._get_cached_result(query_hash)
            if cached_result:
                self._metrics["cache_hits"] += 1
                logger.info("Retrieved result from cache")
                return cached_result
            query_embedding = self._convert_to_embedding(normalized_query)
            retrieved_docs = self._retrieve_documents(query_embedding, filters)
            context_result = self._package_context(query, retrieved_docs)
            retrieval_time = time.time() - start_time
            self._update_metrics(retrieval_time, len(retrieved_docs))
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
        """Retrieve cached result if available and not expired."""
        if query_hash not in self._query_cache:
            return None
        
        cached_data = self._query_cache[query_hash]
        if time.time() - cached_data['timestamp'] > self._cache_ttl:
            del self._query_cache[query_hash]
            return None
        
        return cached_data['result']
    
    def _convert_to_embedding(self, query: str) -> List[float]:
        """Convert query text to embedding using the embedding model."""
        try:
            embeddings = self.embedding_model.embed_query(query)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to convert query to embedding: {e}")
            raise RetrievalError(f"Embedding conversion failed: {e}")
    
    def _retrieve_documents(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Retrieve relevant documents using vector similarity search."""
        try:
            # Perform similarity search
            retrieval_params = {
                "k": self.retrieval_config.top_k,
            }
            
            # Add metadata filters if provided
            if filters:
                retrieval_params["filter"] = filters
            
            # Get similar documents
            docs = self.vector_store.similarity_search_by_vector(
                query_embedding, 
                **retrieval_params
            )
            
            logger.info(f"Retrieved {len(docs)} documents using {self.retrieval_config.strategy} strategy")
            return docs
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            raise RetrievalError(f"Document retrieval failed: {e}")
    
    def _package_context(self, query: str, retrieved_docs: List[Document]) -> Dict[str, Any]:
        """Package retrieved documents into context for LLM."""
        return {
            "query": query,
            "documents": retrieved_docs,
            "stats": {
                "num_documents": len(retrieved_docs),
                "retrieval_strategy": self.retrieval_config.strategy,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _update_metrics(self, retrieval_time: float, num_docs: int) -> None:
        """Update internal metrics tracking."""
        self._metrics["total_queries"] += 1
        self._metrics["avg_retrieval_time"] = (
            (self._metrics["avg_retrieval_time"] * (self._metrics["total_queries"] - 1) + retrieval_time) 
            / self._metrics["total_queries"]
        )
        
        if num_docs > 0:
            self._metrics["hit_rate"] = self._metrics["total_queries"] / (self._metrics["total_queries"] + 1)
    
    def _cache_result(self, query_hash: str, result: Dict[str, Any]) -> None:
        """Cache query result for future use."""
        self._query_cache[query_hash] = {
            "result": result,
            "timestamp": time.time()
        }
        
        # Prevent cache from growing too large
        if len(self._query_cache) > 100:
            oldest_key = min(self._query_cache.keys(), 
                           key=lambda k: self._query_cache[k]['timestamp'])
            del self._query_cache[oldest_key]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current retrieval metrics."""
        return self._metrics.copy()
    
    def clear_cache(self) -> None:
        """Clear the query cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")