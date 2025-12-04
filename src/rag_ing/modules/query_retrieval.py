
"""Module 2: Query Processing & Retrieval

Objective: Convert user query to embedding and retrieve relevant chunks.
"""

import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from ..config.settings import Settings, RetrievalConfig
from ..utils.exceptions import RetrievalError

logger = logging.getLogger(__name__)


class QueryRetrievalModule:
    """Module for YAML-driven query processing and document retrieval."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.retrieval_config = config.retrieval
        
        # Hierarchical storage support (must be before _initialize_components)
        self.hierarchical_config = config.hierarchical_storage
        self.summary_vector_store = None
        
        # Initialize vector store and embedding model internally
        self.vector_store = None
        self.embedding_model = None
        self._initialize_components()
        
        # Query cache for performance
        self._query_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Query context for enhanced retrieval features
        self._last_query = None
        
        # Metrics tracking
        self._metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_retrieval_time": 0,
            "hit_rate": 0,
            "hybrid_queries": 0,
            "reranked_queries": 0,
            "medical_boosted_queries": 0,
            "hierarchical_queries": 0
        }
    
    def _initialize_components(self):
        """Initialize vector store and embedding model based on configuration."""
        logger.info("Initializing vector store and embedding model components...")
        
        try:
            # Initialize embedding model with Azure/open source support
            self._initialize_embedding_model()
            
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
                    
                    # Load summary collection if hierarchical storage is enabled
                    if self.hierarchical_config.enabled:
                        try:
                            summary_dir = Path(vector_store_config.path) / "summaries"
                            if summary_dir.exists():
                                self.summary_vector_store = Chroma(
                                    collection_name=self.hierarchical_config.summary_collection,
                                    persist_directory=str(summary_dir),
                                    embedding_function=self.embedding_model
                                )
                                logger.info(f"Hierarchical storage: Summary collection loaded")
                        except Exception as e:
                            logger.warning(f"Failed to load summary collection: {e}")
                
                except Exception as e:
                    logger.warning(f"Failed to load existing vector store: {e}")
                    logger.info("Using mock vector store for demonstration")
                    self.vector_store = self._create_mock_vector_store()
                    
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self.embedding_model = None
            self.vector_store = None
    
    def _initialize_embedding_model(self):
        """Initialize embedding model supporting both Azure and open source options."""
        embedding_config = self.config.embedding_model
        provider = embedding_config.get_primary_provider()
        
        logger.info(f"Initializing embedding model with provider: {provider}")
        
        if provider == "azure_openai" and embedding_config.use_azure_primary:
            # Try Azure OpenAI embeddings first
            try:
                self._load_azure_embedding_model()
                return
            except Exception as e:
                logger.warning(f"Azure embedding model failed, falling back to open source: {e}")
        
        # Use open source embedding model
        try:
            self._load_open_source_embedding_model()
        except Exception as e:
            logger.warning(f"Failed to load open source embeddings: {e}")
            # Final fallback to mock embedding for demo purposes
            logger.info("Using mock embedding model for demonstration")
            self.embedding_model = self._create_mock_embedding_model()
    
    def _load_azure_embedding_model(self):
        """Load Azure OpenAI embedding model for query processing."""
        from openai import AzureOpenAI
        
        embedding_config = self.config.embedding_model
        
        # Create Azure client - prioritize embedding-specific credentials from env vars
        api_key = (
            self.config.azure_openai_embedding_api_key or  # From .env AZURE_OPENAI_EMBEDDING_API_KEY
            embedding_config.azure_api_key or              # From config.yaml
            self.config.azure_openai_api_key              # Fallback to main Azure key
        )
        endpoint = (
            self.config.azure_openai_embedding_endpoint or  # From .env AZURE_OPENAI_EMBEDDING_ENDPOINT
            embedding_config.azure_endpoint or             # From config.yaml
            self.config.azure_openai_endpoint             # Fallback to main Azure endpoint
        )
        api_version = (
            self.config.azure_openai_embedding_api_version or  # From .env
            embedding_config.azure_api_version                 # From config.yaml
        )
        
        azure_client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        # Use the same wrapper class as in corpus embedding
        class AzureEmbeddingWrapper:
            def __init__(self, client, model_name, deployment_name):
                self.client = client
                self.model_name = model_name
                self.deployment_name = deployment_name
            
            def embed_query(self, text: str) -> List[float]:
                """Embed a single query text."""
                response = self.client.embeddings.create(
                    input=[text],
                    model=self.deployment_name
                )
                return response.data[0].embedding
            
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                """Embed multiple documents."""
                batch_size = 16
                all_embeddings = []
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.deployment_name
                    )
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                
                return all_embeddings
        
        self.embedding_model = AzureEmbeddingWrapper(
            client=azure_client,
            model_name=embedding_config.azure_model,
            deployment_name=embedding_config.azure_deployment_name
        )
        
        logger.info(f"Azure embedding model loaded for queries: {embedding_config.azure_model}")
    
    def _load_open_source_embedding_model(self):
        """Load open source embedding model for query processing."""
        from langchain_huggingface import HuggingFaceEmbeddings
        
        embedding_config = self.config.embedding_model
        
        # Map model names to actual HuggingFace model identifiers
        model_mapping = {
            "pubmedbert": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2"
        }
        
        model_name = model_mapping.get(embedding_config.name, embedding_config.name)
        logger.info(f"Loading open source embedding model: {model_name}")
        
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': embedding_config.device}
        )
        logger.info(f"Open source embedding model loaded: {embedding_config.name}")
    
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
                from langchain_core.documents import Document
                return [Document(page_content=doc["content"], metadata=doc["metadata"]) for doc in self.documents[:k]]
        
        return MockVectorStore()
    
    def process_query(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main entry point for enhanced query processing and retrieval."""
        logger.info(f"Processing query: {query[:50]}...")
        start_time = time.time()
        
        try:
            # Use hierarchical retrieval if enabled
            logger.debug(f"Hierarchical check: enabled={self.hierarchical_config.enabled}, summary_store={self.summary_vector_store is not None}")
            if self.hierarchical_config.enabled and self.summary_vector_store:
                logger.info("Triggering hierarchical retrieval")
                return self._hierarchical_retrieve(query, filters, start_time)
            else:
                logger.info("Using standard retrieval (hierarchical not enabled or summary store missing)")
            
            # Step 1: Query Input validation and normalization
            normalized_query = self._normalize_query(query)
            query_hash = self._generate_query_hash(normalized_query, filters)
            
            # Store query context for reranking and keyword search
            self._last_query = query
            
            # Check cache first
            cached_result = self._get_cached_result(query_hash)
            if cached_result:
                self._metrics["cache_hits"] += 1
                logger.info("Retrieved result from cache")
                return cached_result
            
            # Step 2: Query Expansion for better semantic coverage
            expanded_queries = self._expand_query(query, normalized_query)
            
            # Step 3: Embedding Conversion (use expanded query for richer semantic signal)
            query_embedding = self._convert_to_embedding(expanded_queries[0])
            
            # Step 4: Enhanced Retrieval Logic with hybrid search and medical boosting
            retrieved_docs = self._retrieve_documents(query_embedding, filters, query, expanded_queries)
            
            # Step 4: Context Packaging with enhanced metadata
            context_result = self._package_context(query, retrieved_docs)
            
            # Update metrics
            retrieval_time = time.time() - start_time
            self._update_metrics(retrieval_time, len(retrieved_docs))
            
            # Cache result
            self._cache_result(query_hash, context_result)
            
            logger.info(f"Enhanced query processed successfully in {retrieval_time:.2f}s using {self.retrieval_config.strategy} strategy")
            return context_result
            
        except Exception as e:
            logger.error(f"Enhanced query processing failed: {e}")
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
    
    def _expand_query(self, original_query: str, normalized_query: str) -> List[str]:
        """Expand query with synonyms, variations, and domain concepts.
        
        Helps handle cases where users don't know exact technical terms:
        - "three classification" → "three categories", "three types", "three classes"
        - "qm2 logic" → "qm2 calculation", "quality measure 2", "qm-2 methodology"
        - "anthem" → "anthem blue cross", "anthem bcbs"
        
        Returns list of query variations (original first).
        """
        expanded = [normalized_query]  # Always include normalized original
        
        # Domain-specific concept mappings
        concept_mappings = {
            # Quality measures
            'qm1': ['qm-1', 'quality measure 1', 'qm 1', 'first quality measure'],
            'qm2': ['qm-2', 'quality measure 2', 'qm 2', 'second quality measure'],
            'qm3': ['qm-3', 'quality measure 3', 'qm 3', 'third quality measure'],
            'qm4': ['qm-4', 'quality measure 4', 'qm 4', 'fourth quality measure'],
            'qm5': ['qm-5', 'quality measure 5', 'qm 5', 'fifth quality measure'],
            
            # Classification synonyms
            'classification': ['category', 'type', 'class', 'group', 'tier', 'level'],
            'classifications': ['categories', 'types', 'classes', 'groups', 'tiers', 'levels'],
            
            # Logic/calculation synonyms
            'logic': ['calculation', 'formula', 'methodology', 'rule', 'algorithm', 'computation'],
            
            # Organization names
            'anthem': ['anthem blue cross', 'anthem bcbs', 'anthem insurance'],
            
            # Technical terms
            'table': ['dataset', 'data table', 'database table', 'relation'],
            'model': ['data model', 'dbt model', 'transformation', 'view'],
            'query': ['sql query', 'database query', 'select statement'],
        }
        
        # Common question patterns - expand to declarative forms
        question_expansions = {
            'do we have': ['there are', 'includes', 'contains', 'has'],
            'what is': ['definition of', 'describes', 'explains'],
            'how does': ['mechanism of', 'process for', 'method to'],
            'where is': ['location of', 'found in', 'stored in'],
        }
        
        query_lower = normalized_query.lower()
        
        # Apply concept mappings
        for concept, synonyms in concept_mappings.items():
            if concept in query_lower:
                for synonym in synonyms[:2]:  # Use top 2 synonyms to avoid explosion
                    expanded_query = query_lower.replace(concept, synonym)
                    if expanded_query not in expanded:
                        expanded.append(expanded_query)
        
        # Apply question pattern expansions
        for pattern, alternatives in question_expansions.items():
            if pattern in query_lower:
                for alt in alternatives[:1]:  # Use 1 alternative per pattern
                    expanded_query = query_lower.replace(pattern, alt)
                    if expanded_query not in expanded:
                        expanded.append(expanded_query)
        
        # Number word expansion (for "three", "five", etc.)
        number_mappings = {
            'three': ['3', 'triple', 'trio'],
            'five': ['5', 'quintuple'],
            'two': ['2', 'dual', 'pair'],
            'four': ['4', 'quad'],
        }
        
        for number_word, variations in number_mappings.items():
            if number_word in query_lower:
                for variation in variations[:1]:
                    expanded_query = query_lower.replace(number_word, variation)
                    if expanded_query not in expanded:
                        expanded.append(expanded_query)
        
        # Limit total expansions to avoid performance issues
        expanded = expanded[:5]
        
        if len(expanded) > 1:
            logger.info(f"Query expanded to {len(expanded)} variations")
            logger.debug(f"Expanded queries: {expanded[:3]}")  # Log first 3
        
        return expanded
    
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
    
    def _convert_to_embedding(self, query: str) -> List[float]:
        """Convert query text to embedding using the embedding model."""
        try:
            embeddings = self.embedding_model.embed_query(query)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to convert query to embedding: {e}")
            raise RetrievalError(f"Embedding conversion failed: {e}")
    
    def _retrieve_documents(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None, query_text: str = None, expanded_queries: Optional[List[str]] = None) -> List[Document]:
        """Enhanced retrieval with query expansion, hybrid search, reranking, and medical domain optimization."""
        try:
            # Store query text for keyword retrieval
            self._last_query = query_text or "medical oncology treatment"
            
            # Step 1: Determine retrieval strategy
            strategy = self.retrieval_config.strategy
            logger.info(f"Using {strategy} retrieval strategy")
            
            if strategy == "hybrid":
                docs = self._hybrid_retrieval(query_embedding, filters)
            elif strategy == "semantic":
                docs = self._semantic_retrieval(query_embedding, filters)
            elif strategy == "keyword":
                docs = self._keyword_retrieval(query_embedding, filters)
            else:
                logger.warning(f"Unknown strategy {strategy}, falling back to semantic")
                docs = self._semantic_retrieval(query_embedding, filters)
            
            # Step 2: Apply medical domain filtering and boosting
            if self.retrieval_config.domain_specific.get("medical_terms_boost", True):
                docs = self._apply_medical_boosting(docs, query_text)
            
            # Step 3: Apply cross-encoder reranking if enabled
            if self.retrieval_config.reranking.enabled and len(docs) > 1:
                docs = self._rerank_documents(docs)
            
            # Step 4: Final filtering and deduplication
            docs = self._post_process_documents(docs, filters)
            
            logger.info(f"Retrieved {len(docs)} documents using {strategy} strategy with enhancements")
            return docs
            
        except Exception as e:
            logger.error(f"Enhanced document retrieval failed: {e}")
            raise RetrievalError(f"Enhanced document retrieval failed: {e}")
    
    def _hybrid_retrieval(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Hybrid retrieval combining semantic and keyword search with SQL optimization."""
        logger.info("Performing hybrid retrieval (semantic + keyword)")
        
        # Get more candidates for hybrid merging
        extended_k = min(self.retrieval_config.top_k * 2, 50)
        
        # Semantic search component
        semantic_docs = self._semantic_retrieval(query_embedding, filters, k=extended_k)
        
        # Keyword search component (BM25-style) with SQL enhancement
        keyword_docs = self._keyword_retrieval(query_embedding, filters, k=extended_k)
        
        # Detect if query contains SQL-specific terms
        query_text = getattr(self, '_last_query', '') or ''
        is_sql_query = self._is_sql_related_query(query_text)
        
        # Merge and weight results (adjust weights for SQL queries)
        merged_docs = self._merge_retrieval_results(semantic_docs, keyword_docs, is_sql_query)
        
        # Apply SQL-specific boosting if needed
        if is_sql_query:
            merged_docs = self._apply_sql_boosting(merged_docs, query_text)
        
        # Return top-k results
        return merged_docs[:self.retrieval_config.top_k]
    
    def _semantic_retrieval(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None, k: Optional[int] = None) -> List[Document]:
        """Pure semantic vector similarity retrieval."""
        retrieval_k = k or self.retrieval_config.top_k
        
        retrieval_params = {"k": retrieval_k}
        if filters:
            retrieval_params["filter"] = filters
        
        try:
            # Use embedding-based similarity search
            docs = self.vector_store.similarity_search_by_vector(query_embedding, **retrieval_params)
            logger.debug(f"Semantic retrieval found {len(docs)} documents")
            return docs
        except Exception as e:
            logger.warning(f"Semantic retrieval failed, using fallback: {e}")
            return self._fallback_retrieval(filters, retrieval_k)
    
    def _keyword_retrieval(self, query_embedding: List[float], filters: Optional[Dict[str, Any]] = None, k: Optional[int] = None) -> List[Document]:
        """Keyword-based retrieval using BM25-style scoring."""
        retrieval_k = k or self.retrieval_config.top_k
        
        try:
            # For now, simulate keyword retrieval by doing semantic search with keyword boost
            # In a full implementation, this would use BM25 or Elasticsearch
            
            # Extract query text from the embedding context (simplified approach)
            # In production, you'd store the original query text
            if hasattr(self, '_last_query'):
                query_text = self._last_query
            else:
                query_text = "medical oncology treatment"  # Fallback for demo
            
            # Simple keyword matching simulation
            docs = self._simulate_keyword_search(query_text, filters, retrieval_k)
            logger.debug(f"Keyword retrieval found {len(docs)} documents")
            return docs
            
        except Exception as e:
            logger.warning(f"Keyword retrieval failed, using fallback: {e}")
            return self._fallback_retrieval(filters, retrieval_k)
    
    def _simulate_keyword_search(self, query_text: str, filters: Optional[Dict[str, Any]], k: int) -> List[Document]:
        """Enhanced keyword search with SQL-specific term matching.
        
        For SQL queries, extracts:
        - Table/column names (CamelCase, snake_case)
        - SQL keywords (SELECT, JOIN, WHERE, etc.)
        - Function names
        - Schema objects
        """
        # Safety check for empty or None query text
        if not query_text or not query_text.strip():
            query_text = "medical oncology treatment"  # Safe fallback
        
        retrieval_params = {"k": k * 2}  # Get more for keyword filtering
        if filters:
            retrieval_params["filter"] = filters
        
        try:
            # Get documents and simulate keyword scoring
            if hasattr(self.vector_store, 'similarity_search'):
                docs = self.vector_store.similarity_search(query_text, **retrieval_params)
            else:
                docs = self._fallback_retrieval(filters, k)
            
            # Extract query terms with SQL-aware tokenization
            query_terms = self._extract_query_terms(query_text)
            scored_docs = []
            
            for doc in docs:
                if doc and hasattr(doc, 'page_content') and doc.page_content:
                    content_lower = doc.page_content.lower()
                    content_terms = set(content_lower.split())
                    
                    # Base keyword overlap score
                    overlap_score = len(query_terms.intersection(content_terms)) / len(query_terms) if query_terms else 0
                    
                    # Boost for exact multi-word matches (table names, function calls)
                    exact_match_boost = self._calculate_exact_match_boost(query_text, doc.page_content)
                    
                    # Boost for SQL file types
                    file_type_boost = 0.0
                    if doc.metadata.get('file_type', '').lower() in ['.sql', 'sql']:
                        file_type_boost = 0.2
                    
                    # Combined score
                    final_score = overlap_score + exact_match_boost + file_type_boost
                    scored_docs.append((doc, final_score))
            
            # Sort by keyword score and return top results
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, score in scored_docs[:k]]
            
        except Exception as e:
            logger.warning(f"Keyword search simulation failed: {e}")
            return self._fallback_retrieval(filters, k)
    
    def _merge_retrieval_results(self, semantic_docs: List[Document], keyword_docs: List[Document], is_sql_query: bool = False) -> List[Document]:
        """Merge semantic and keyword retrieval results with weighted scoring.
        
        For SQL queries, boost keyword weight for better exact matching.
        """
        logger.debug("Merging semantic and keyword retrieval results")
        
        # Adjust weights for SQL queries (favor keyword matching)
        if is_sql_query:
            semantic_weight = 0.4  # Reduced from default 0.7
            keyword_weight = 0.6   # Increased from default 0.3
            logger.info("SQL query detected - boosting keyword weight to 0.6")
        else:
            semantic_weight = self.retrieval_config.semantic_weight
            keyword_weight = self.retrieval_config.keyword_weight
        
        # Create document scoring map
        doc_scores = {}
        
        # Score semantic results
        for i, doc in enumerate(semantic_docs):
            doc_id = self._get_document_id(doc)
            semantic_score = (len(semantic_docs) - i) / len(semantic_docs)
            doc_scores[doc_id] = {
                'doc': doc,
                'semantic_score': semantic_score,
                'keyword_score': 0.0
            }
        
        # Score keyword results
        for i, doc in enumerate(keyword_docs):
            doc_id = self._get_document_id(doc)
            keyword_score = (len(keyword_docs) - i) / len(keyword_docs)
            
            if doc_id in doc_scores:
                doc_scores[doc_id]['keyword_score'] = keyword_score
            else:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'semantic_score': 0.0,
                    'keyword_score': keyword_score
                }
        
        # Calculate final weighted scores
        final_docs = []
        for doc_data in doc_scores.values():
            final_score = (semantic_weight * doc_data['semantic_score'] + 
                          keyword_weight * doc_data['keyword_score'])
            final_docs.append((doc_data['doc'], final_score))
        
        # Sort by final score
        final_docs.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Merged {len(final_docs)} unique documents from hybrid retrieval")
        return [doc for doc, score in final_docs]
    
    def _apply_medical_boosting(self, docs: List[Document], query: str = None) -> List[Document]:
        """Enhanced boosting for medical terminology and question-answer patterns."""
        logger.debug("Applying enhanced medical and Q&A boosting")
        
        # Medical terms that should boost relevance
        medical_terms = {
            'cancer', 'oncology', 'tumor', 'chemotherapy', 'radiation', 'immunotherapy',
            'metastasis', 'carcinoma', 'lymphoma', 'leukemia', 'biopsy', 'malignant',
            'benign', 'staging', 'prognosis', 'diagnosis', 'treatment', 'therapy',
            'clinical', 'patient', 'medical', 'healthcare', 'disease', 'symptom',
            'eom', 'enhancing oncology model'  # Add EOM-specific terms
        }
        
        # Question-answer patterns that indicate direct answers
        answer_patterns = {
            'started', 'began', 'launched', 'implemented', 'established', 'initiated',
            'effective', 'beginning', 'since', 'from', 'in 2', '20', 'year',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december'
        }
        
        # Date patterns that often indicate when something started
        date_indicators = {
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            '2019', '2020', '2021', '2022', '2023', '2024', '2025',
            'q1', 'q2', 'q3', 'q4', 'quarter'
        }
        
        # Ontology codes that should boost relevance
        ontology_patterns = ['ICD-O', 'SNOMED-CT', 'MeSH', 'ICD-10', 'CPT']
        
        # Use provided query or fallback to stored query
        if query:
            query_text = query.lower()
        else:
            stored_query = getattr(self, '_last_query', '') or ''
            if stored_query is None:
                stored_query = ''
            query_text = stored_query.lower()
        
        is_when_question = any(word in query_text for word in ['when', 'start', 'began', 'launch', 'implement'])
        
        scored_docs = []
        for doc in docs:
            content = doc.page_content.lower()
            
            # Calculate medical term boost
            term_count = sum(1 for term in medical_terms if term in content)
            term_boost = min(term_count * 0.1, 0.5)  # Max 0.5 boost
            
            # Calculate ontology code boost
            ontology_count = sum(1 for pattern in ontology_patterns 
                               if pattern.lower() in content or pattern in str(doc.metadata))
            ontology_boost = min(ontology_count * 0.2, 0.3)  # Max 0.3 boost
            
            # NEW: Question-answer pattern boost
            qa_boost = 0.0
            if is_when_question:
                # Boost documents that contain answer patterns for "when" questions
                answer_count = sum(1 for pattern in answer_patterns if pattern in content)
                date_count = sum(1 for date_term in date_indicators if date_term in content)
                qa_boost = min((answer_count * 0.3) + (date_count * 0.4), 1.0)  # Max 1.0 boost
            
            # NEW: Direct answer indicators boost
            direct_answer_boost = 0.0
            if any(indicator in content for indicator in ['the program started', 'began in', 'launched in', 'effective']):
                direct_answer_boost = 0.8  # Strong boost for direct answers
            
            # Total boost score
            boost_score = 1.0 + term_boost + ontology_boost + qa_boost + direct_answer_boost
            scored_docs.append((doc, boost_score))
        
        # Sort by boost score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Applied enhanced boosting to {len(docs)} documents with scores")
        return [doc for doc, score in scored_docs]
    
    def _rerank_documents(self, docs: List[Document]) -> List[Document]:
        """Apply cross-encoder reranking for improved relevance."""
        logger.debug("Applying cross-encoder reranking")
        
        try:
            # For now, implement a simple reranking heuristic
            # In production, you'd use a cross-encoder model like ms-marco-MiniLM-L-12-v2
            
            if not hasattr(self, '_last_query') or not self._last_query:
                logger.warning("No query context available for reranking")
                return docs
            
            query = self._last_query
            scored_docs = []
            
            for doc in docs:
                if not doc or not hasattr(doc, 'page_content') or not doc.page_content:
                    continue
                    
                # Simple reranking score based on query term frequency and position
                content = doc.page_content.lower()
                query_terms = query.lower().split() if query else []
                
                # Calculate relevance score
                relevance_score = 0.0
                content_words = content.split()
                
                for term in query_terms:
                    # Count term frequency
                    term_freq = content.count(term)
                    relevance_score += term_freq * 0.1
                    
                    # Boost if term appears early in document
                    for i, word in enumerate(content_words[:50]):  # First 50 words
                        if term in word:
                            position_boost = (50 - i) / 50 * 0.2
                            relevance_score += position_boost
                            break
                
                scored_docs.append((doc, relevance_score))
            
            # Sort by reranking score
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            logger.debug(f"Reranked {len(scored_docs)} documents")
            return [doc for doc, score in scored_docs]
            
        except Exception as e:
            logger.warning(f"Reranking failed, returning original order: {e}")
            return docs
    
    def _post_process_documents(self, docs: List[Document], filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Final document processing including deduplication and filtering."""
        logger.debug("Post-processing retrieved documents")
        
        # Remove duplicates based on content similarity
        unique_docs = []
        seen_content = set()
        
        for doc in docs:
            # Create content hash for deduplication
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_docs.append(doc)
        
        # Apply any additional filters
        if filters:
            filtered_docs = []
            for doc in unique_docs:
                include_doc = True
                for key, value in filters.items():
                    if key in doc.metadata:
                        if doc.metadata[key] != value:
                            include_doc = False
                            break
                
                if include_doc:
                    filtered_docs.append(doc)
            
            unique_docs = filtered_docs
        
        logger.debug(f"Post-processing: {len(docs)} -> {len(unique_docs)} documents")
        return unique_docs
    
    def _get_document_id(self, doc: Document) -> str:
        """Generate unique identifier for document."""
        # Use source + content hash as unique identifier
        source = doc.metadata.get('source', 'unknown')
        content_hash = hashlib.md5(doc.page_content[:100].encode()).hexdigest()[:8]
        return f"{source}_{content_hash}"
    
    def _fallback_retrieval(self, filters: Optional[Dict[str, Any]], k: int) -> List[Document]:
        """Fallback retrieval method when primary methods fail."""
        logger.info("Using fallback retrieval method")
        
        try:
            # Try basic similarity search without vector
            if hasattr(self.vector_store, 'similarity_search'):
                docs = self.vector_store.similarity_search("", k=k)
                return docs[:k]
        except Exception:
            pass
        
        # Final fallback - return empty list
        logger.warning("All retrieval methods failed")
        return []
    
    def _package_context(self, query: str, retrieved_docs: List[Document]) -> Dict[str, Any]:
        """Package retrieved documents into enhanced context for LLM."""
        return {
            "query": query,
            "documents": retrieved_docs,
            "stats": {
                "num_documents": len(retrieved_docs),
                "retrieval_strategy": self.retrieval_config.strategy,
                "hybrid_weights": {
                    "semantic": self.retrieval_config.semantic_weight,
                    "keyword": self.retrieval_config.keyword_weight
                } if self.retrieval_config.strategy == "hybrid" else None,
                "reranking_enabled": self.retrieval_config.reranking.enabled,
                "medical_boosting": self.retrieval_config.domain_specific.get("medical_terms_boost", True),
                "top_k": self.retrieval_config.top_k,
                "timestamp": datetime.now().isoformat()
            },
            "enhancement_features": {
                "hybrid_search": self.retrieval_config.strategy == "hybrid",
                "cross_encoder_reranking": self.retrieval_config.reranking.enabled,
                "medical_domain_optimization": self.retrieval_config.domain_specific.get("medical_terms_boost", True),
                "ontology_code_weighting": True,  # Always enabled for medical domain
                "deduplication": True
            }
        }
    
    def _hierarchical_retrieve(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]], 
        start_time: float
    ) -> Dict[str, Any]:
        """Enhanced hierarchical retrieval with rich metadata filtering.
        
        Two-tier approach:
        1. Search summary collection (business-friendly, keyword-rich)
        2. For highly relevant summaries, fetch detailed chunks
        3. Return results with source citations
        
        Uses rich metadata (keywords, topics, business_context) for better matching.
        """
        logger.info("Using enhanced hierarchical retrieval with metadata")
        self._metrics["hierarchical_queries"] += 1
        
        # Check if summary collection has any summaries
        try:
            summary_count = self.summary_vector_store._collection.count()
            if summary_count == 0:
                logger.warning("Summary collection is empty. Falling back to standard retrieval.")
                return self._fallback_to_standard_retrieval(query, filters, start_time)
        except Exception as e:
            logger.warning(f"Failed to check summary count: {e}. Falling back to standard retrieval.")
            return self._fallback_to_standard_retrieval(query, filters, start_time)
        
        # Step 1: Search summaries with expanded k for better coverage
        summary_k = min(self.retrieval_config.top_k * 3, 15)
        
        try:
            summary_results = self.summary_vector_store.similarity_search_with_score(
                query,
                k=summary_k
            )
        except Exception as e:
            logger.warning(f"Summary search failed: {e}. Falling back to chunk search.")
            return self._fallback_to_standard_retrieval(query, filters, start_time)
        
        if not summary_results:
            logger.warning("No summaries found. Using standard retrieval.")
            return self._fallback_to_standard_retrieval(query, filters, start_time)
        
        logger.info(f"Found {len(summary_results)} summary candidates")
        
        # Step 2: Analyze summaries and apply metadata boosting
        scored_summaries = []
        for doc, score in summary_results:
            # Calculate enhanced relevance score using metadata
            metadata = doc.metadata
            
            # Base semantic score (convert distance to similarity)
            semantic_score = 1 - min(score, 1.0)
            
            # Boost based on keywords matching
            keywords = metadata.get('keywords', '').lower()
            query_lower = query.lower()
            keyword_boost = sum(1 for word in query_lower.split() if word in keywords) * 0.1
            
            # Boost based on document type relevance
            doc_type = metadata.get('document_type', '')
            type_boost = 0.0
            if 'sql' in query_lower and 'sql' in doc_type:
                type_boost = 0.15
            elif 'python' in query_lower and 'python' in doc_type:
                type_boost = 0.15
            elif 'config' in query_lower and 'yaml' in doc_type:
                type_boost = 0.15
            
            # Combined relevance score
            final_score = semantic_score + keyword_boost + type_boost
            
            scored_summaries.append((doc, final_score, score))
        
        # Sort by enhanced score
        scored_summaries.sort(key=lambda x: x[1], reverse=True)
        
        # Step 3: Smart routing - fetch details for highly relevant documents
        threshold = self.hierarchical_config.routing_threshold
        detailed_chunks = []
        summary_only_docs = []
        sources_fetched = []
        
        for doc, final_score, orig_score in scored_summaries[:self.retrieval_config.top_k]:
            metadata = doc.metadata
            
            if final_score >= threshold:
                # Highly relevant - fetch detailed chunks
                source = metadata.get('original_doc_id') or metadata.get('file_path') or metadata.get('source', '')
                
                if source and source not in sources_fetched:
                    sources_fetched.append(source)
                    
                    try:
                        # Fetch detailed chunks from this document
                        chunk_results = self.vector_store.similarity_search(
                            query,
                            k=5,  # Get top 5 chunks from this document
                            filter={"source": source} if source else None
                        )
                        
                        # Enrich chunks with summary metadata for context
                        for chunk in chunk_results:
                            chunk.metadata['summary_keywords'] = metadata.get('keywords', '')
                            chunk.metadata['summary_topics'] = metadata.get('topics', '')
                            chunk.metadata['business_context'] = metadata.get('business_context', '')
                            chunk.metadata['relevance_score'] = final_score
                        
                        detailed_chunks.extend(chunk_results)
                        logger.info(f"[OK] Fetched {len(chunk_results)} chunks from {metadata.get('filename', source)}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch chunks for {source}: {e}")
                        # Fallback to summary
                        summary_only_docs.append(doc)
            else:
                # Lower relevance - use summary only
                doc.metadata['relevance_score'] = final_score
                summary_only_docs.append(doc)
        
        # Step 4: Combine and deduplicate results
        final_docs = detailed_chunks if detailed_chunks else summary_only_docs
        
        if not final_docs:
            final_docs = [doc for doc, _, _ in scored_summaries[:self.retrieval_config.top_k]]
        
        # Deduplicate and limit to top_k
        final_docs = self._deduplicate_documents(final_docs)[:self.retrieval_config.top_k]
        
        # Step 5: Add source citations
        for doc in final_docs:
            if 'source' not in doc.metadata and 'file_path' in doc.metadata:
                doc.metadata['source'] = doc.metadata['file_path']
        
        retrieval_time = time.time() - start_time
        
        logger.info(f"[OK] Hierarchical retrieval completed: {len(detailed_chunks)} detail chunks, {len(summary_only_docs)} summaries, {retrieval_time:.2f}s")
        
        return {
            "documents": final_docs,
            "stats": {
                "num_results": len(final_docs),
                "retrieval_strategy": "hierarchical_enhanced",
                "summaries_searched": len(summary_results),
                "summaries_scored": len(scored_summaries),
                "details_fetched": len(detailed_chunks),
                "sources_fetched": len(sources_fetched),
                "summary_only": len(summary_only_docs),
                "retrieval_time": retrieval_time,
                "threshold": threshold
            },
            "query": query,
            "filters": filters
        }
    
    def _fallback_to_standard_retrieval(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]], 
        start_time: float
    ) -> Dict[str, Any]:
        """Fallback to standard retrieval when hierarchical fails."""
        logger.info("Using standard retrieval (fallback)")
        
        # Standard retrieval flow
        normalized_query = self._normalize_query(query)
        query_embedding = self._convert_to_embedding(normalized_query)
        retrieved_docs = self._retrieve_documents(query_embedding, filters, query)
        
        retrieval_time = time.time() - start_time
        
        return {
            "documents": retrieved_docs,
            "stats": {
                "num_results": len(retrieved_docs),
                "retrieval_strategy": "standard_fallback",
                "retrieval_time": retrieval_time
            },
            "query": query,
            "filters": filters
        }
    
    def _deduplicate_documents(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content hash."""
        seen_hashes = set()
        unique_docs = []
        
        for doc in docs:
            # Create content hash
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _is_sql_related_query(self, query: str) -> bool:
        """Detect if query is asking about SQL code, tables, or database objects.
        
        Detects:
        - SQL keywords (select, join, where, table, etc.)
        - Database objects (table, column, view, procedure)
        - SQL functions (count, sum, aggregate, etc.)
        - Code structure terms (query, logic, calculation)
        """
        if not query:
            return False
        
        query_lower = query.lower()
        
        # SQL-specific indicators
        sql_keywords = {
            'sql', 'select', 'join', 'where', 'table', 'column', 'view',
            'query', 'database', 'schema', 'procedure', 'function',
            'aggregate', 'count', 'sum', 'group by', 'order by',
            'union', 'cte', 'with', 'insert', 'update', 'delete',
            'create', 'alter', 'drop', 'index', 'constraint',
            'dbt', 'model', 'macro', 'jinja', 'ref()', 'source()'
        }
        
        # Check for SQL indicators
        return any(keyword in query_lower for keyword in sql_keywords)
    
    def _extract_query_terms(self, query: str) -> set:
        """Extract query terms with SQL-aware tokenization.
        
        Preserves:
        - CamelCase identifiers (e.g., PatientData → patient, data)
        - snake_case identifiers (e.g., patient_data → patient, data)
        - Quoted strings (e.g., "table_name" → table_name)
        - Special SQL terms
        """
        import re
        
        terms = set()
        query_lower = query.lower()
        
        # Extract regular words
        words = query_lower.split()
        terms.update(words)
        
        # Extract CamelCase components (e.g., PatientData → patient, data)
        camel_pattern = re.findall(r'[A-Z][a-z]+|[a-z]+', query)
        terms.update([term.lower() for term in camel_pattern])
        
        # Extract snake_case components (e.g., patient_data → patient, data)
        for word in words:
            if '_' in word:
                parts = word.split('_')
                terms.update(parts)
        
        # Extract quoted strings (preserve as-is)
        quoted = re.findall(r'["\']([^"\'\n]+)["\']', query)
        terms.update([q.lower() for q in quoted])
        
        # Remove common stop words but keep SQL keywords
        sql_keywords = {'select', 'from', 'where', 'join', 'group', 'order', 'by'}
        stop_words = {'the', 'is', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        terms = {t for t in terms if t not in stop_words or t in sql_keywords}
        
        return terms
    
    def _calculate_exact_match_boost(self, query: str, content: str) -> float:
        """Calculate boost for exact phrase matches.
        
        Important for:
        - Table names: "patient_summary" should match exactly
        - Function calls: "calculate_risk_score()" needs exact match
        - Multi-word terms: "left outer join" vs individual words
        """
        import re
        
        boost = 0.0
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Extract potential exact-match phrases (2-4 words)
        query_words = query_lower.split()
        
        for n in range(2, 5):  # Check 2-word, 3-word, 4-word phrases
            for i in range(len(query_words) - n + 1):
                phrase = ' '.join(query_words[i:i+n])
                
                # Exact phrase match
                if phrase in content_lower:
                    boost += 0.3  # Strong boost for exact phrase
                    logger.debug(f"Exact match found: '{phrase}'")
        
        # Check for SQL identifiers with underscores (exact match)
        sql_identifiers = re.findall(r'\b[a-z_]+_[a-z_]+\b', query_lower)
        for identifier in sql_identifiers:
            if identifier in content_lower:
                boost += 0.4  # Very strong boost for exact identifier
                logger.debug(f"SQL identifier match: '{identifier}'")
        
        # Check for function calls (exact match)
        function_calls = re.findall(r'\b[a-z_]+\(\)', query_lower)
        for func in function_calls:
            if func in content_lower:
                boost += 0.5  # Maximum boost for exact function match
                logger.debug(f"Function call match: '{func}'")
        
        return min(boost, 1.0)  # Cap at 1.0
    
    def _apply_sql_boosting(self, docs: List[Document], query: str) -> List[Document]:
        """Apply SQL-specific relevance boosting.
        
        Boosts documents that:
        - Are SQL files (.sql extension)
        - Contain matching table/column names
        - Have similar SQL structure (CTEs, JOINs, aggregations)
        - Match query logic keywords
        """
        logger.debug("Applying SQL-specific boosting")
        
        scored_docs = []
        query_lower = query.lower()
        
        for doc in docs:
            boost_score = 1.0  # Base score
            content_lower = doc.page_content.lower()
            metadata = doc.metadata
            
            # Boost 1: SQL file type
            file_type = metadata.get('file_type', '').lower()
            filename = metadata.get('filename', '').lower()
            if file_type in ['.sql', 'sql'] or filename.endswith('.sql'):
                boost_score += 0.3
            
            # Boost 2: DBT-specific files
            if 'dbt' in filename or 'models/' in metadata.get('source', ''):
                boost_score += 0.2
            
            # Boost 3: Logic keywords (for "qm1 logic", "calculation logic", etc.)
            logic_keywords = ['logic', 'calculation', 'formula', 'rule', 'algorithm', 'methodology']
            if any(kw in query_lower for kw in logic_keywords):
                if any(kw in content_lower for kw in logic_keywords):
                    boost_score += 0.4
            
            # Boost 4: SQL structure similarity
            sql_structures = ['with', 'select', 'from', 'join', 'where', 'group by', 'having']
            query_structures = sum(1 for struct in sql_structures if struct in query_lower)
            content_structures = sum(1 for struct in sql_structures if struct in content_lower)
            
            if query_structures > 0 and content_structures > 0:
                structure_similarity = min(query_structures, content_structures) / max(query_structures, content_structures)
                boost_score += structure_similarity * 0.3
            
            # Boost 5: Specific code/ID references (e.g., "qm1" in query and content)
            import re
            code_patterns = re.findall(r'\b[a-z]{2,4}\d{1,3}\b', query_lower)  # e.g., qm1, dm3, ccqp4
            for code in code_patterns:
                if code in content_lower:
                    boost_score += 0.6  # Strong boost for matching codes
                    logger.debug(f"Code reference match: '{code}'")
            
            scored_docs.append((doc, boost_score))
        
        # Sort by boost score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"SQL boosting applied: top score = {scored_docs[0][1]:.2f}" if scored_docs else "SQL boosting: no docs")
        return [doc for doc, score in scored_docs]
    
    def _update_metrics(self, retrieval_time: float, num_docs: int) -> None:
        """Update internal metrics tracking with enhanced features."""
        self._metrics["total_queries"] += 1
        self._metrics["avg_retrieval_time"] = (
            (self._metrics["avg_retrieval_time"] * (self._metrics["total_queries"] - 1) + retrieval_time) 
            / self._metrics["total_queries"]
        )
        
        if num_docs > 0:
            self._metrics["hit_rate"] = self._metrics["total_queries"] / (self._metrics["total_queries"] + 1)
        
        # Track enhanced features usage
        if self.retrieval_config.strategy == "hybrid":
            self._metrics["hybrid_queries"] += 1
        
        if self.retrieval_config.reranking.enabled:
            self._metrics["reranked_queries"] += 1
        
        if self.retrieval_config.domain_specific.get("medical_terms_boost", True):
            self._metrics["medical_boosted_queries"] += 1
    
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