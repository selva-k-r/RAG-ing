"""Enhanced Hybrid Retrieval System

This module implements advanced retrieval capabilities including:
- Hybrid search combining semantic similarity and BM25 keyword search
- Cross-encoder reranking for improved relevance
- Query enhancement and expansion
- Domain-specific boosting for medical content
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logging.warning("BM25 not available. Install with: pip install rank-bm25")

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logging.warning("CrossEncoder not available. Install with: pip install sentence-transformers")

from langchain.docstore.document import Document
from ..config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass 
class RetrievalResult:
    """Container for retrieval results with scores and metadata."""
    documents: List[Document]
    semantic_scores: List[float]
    keyword_scores: List[float] 
    rerank_scores: List[float]
    total_time: float
    method: str  # 'semantic', 'keyword', 'hybrid', 'reranked'


class HybridRetriever:
    """Advanced hybrid retrieval system with semantic + keyword search and reranking."""
    
    def __init__(self, config: Settings, vector_store, embedding_model):
        """Initialize hybrid retriever.
        
        Args:
            config: System configuration
            vector_store: Vector store for semantic search
            embedding_model: Embedding model for query encoding
        """
        self.config = config
        self.retrieval_config = config.retrieval
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        
        # BM25 keyword search
        self.bm25_index = None
        self.documents_corpus = []
        self.bm25_available = BM25_AVAILABLE
        
        # Cross-encoder reranking
        self.reranker = None
        self.reranking_enabled = (
            self.retrieval_config.reranking.enabled and CROSS_ENCODER_AVAILABLE
        )
        
        if self.reranking_enabled:
            self._initialize_reranker()
            
        # Medical domain terms for boosting
        self.medical_terms = {
            'oncology', 'cancer', 'tumor', 'malignant', 'benign', 'chemotherapy',
            'radiation', 'metastasis', 'carcinoma', 'sarcoma', 'leukemia',
            'lymphoma', 'biopsy', 'staging', 'prognosis', 'treatment', 'therapy'
        }
        
        logger.info(f"Hybrid retriever initialized - BM25: {self.bm25_available}, "
                   f"Reranking: {self.reranking_enabled}")
    
    def _initialize_reranker(self):
        """Initialize cross-encoder model for reranking."""
        try:
            reranker_model = self.retrieval_config.reranking.model
            self.reranker = CrossEncoder(reranker_model)
            logger.info(f"Reranker initialized: {reranker_model}")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            self.reranking_enabled = False
    
    def build_bm25_index(self, documents: List[Document]):
        """Build BM25 index from document corpus.
        
        Args:
            documents: List of documents to index
        """
        if not self.bm25_available:
            logger.warning("BM25 not available - keyword search disabled")
            return
            
        try:
            # Tokenize documents for BM25
            corpus = []
            self.documents_corpus = documents
            
            for doc in documents:
                # Simple tokenization (could be enhanced with spaCy/NLTK)
                tokens = doc.page_content.lower().split()
                corpus.append(tokens)
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(corpus)
            logger.info(f"BM25 index built with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            self.bm25_available = False
    
    def enhance_query(self, query: str) -> str:
        """Enhance query with domain-specific expansion.
        
        Args:
            query: Original user query
            
        Returns:
            Enhanced query string
        """
        # Medical domain query expansion
        enhanced = query.lower()
        
        # Add medical context if relevant terms detected
        if any(term in enhanced for term in self.medical_terms):
            # Add relevant medical context
            if 'cancer' in enhanced and 'treatment' not in enhanced:
                enhanced += " treatment therapy"
            if 'tumor' in enhanced and 'stage' not in enhanced:
                enhanced += " staging classification"
                
        return enhanced
    
    def semantic_search(self, query: str, k: int = 10) -> Tuple[List[Document], List[float]]:
        """Perform semantic similarity search.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            Tuple of (documents, similarity_scores)
        """
        try:
            # Use vector store similarity search with scores
            if hasattr(self.vector_store, 'similarity_search_with_score'):
                docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k)
                docs = [doc for doc, score in docs_and_scores]
                scores = [score for doc, score in docs_and_scores]
            else:
                # Fallback to basic similarity search
                docs = self.vector_store.similarity_search(query, k=k)
                scores = [1.0] * len(docs)  # Default scores
                
            return docs, scores
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return [], []
    
    def keyword_search(self, query: str, k: int = 10) -> Tuple[List[Document], List[float]]:
        """Perform BM25 keyword search.
        
        Args:
            query: Search query  
            k: Number of documents to retrieve
            
        Returns:
            Tuple of (documents, bm25_scores)
        """
        if not self.bm25_available or self.bm25_index is None:
            return [], []
            
        try:
            # Tokenize query
            query_tokens = query.lower().split()
            
            # Get BM25 scores for all documents
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k documents
            top_indices = scores.argsort()[-k:][::-1]
            
            docs = [self.documents_corpus[i] for i in top_indices]
            top_scores = [scores[i] for i in top_indices]
            
            return docs, top_scores
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return [], []
    
    def hybrid_search(self, query: str, k: int = 10) -> RetrievalResult:
        """Perform hybrid search combining semantic and keyword approaches.
        
        Args:
            query: Search query
            k: Number of final documents to return
            
        Returns:
            RetrievalResult with combined results
        """
        start_time = time.time()
        
        # Enhanced query
        enhanced_query = self.enhance_query(query)
        
        # Get more documents initially for better hybrid combination
        initial_k = min(k * 2, 20)
        
        # Semantic search
        semantic_docs, semantic_scores = self.semantic_search(enhanced_query, k=initial_k)
        
        # Keyword search  
        keyword_docs, keyword_scores = self.keyword_search(enhanced_query, k=initial_k)
        
        # Combine and score documents
        combined_docs = []
        combined_scores = []
        
        # Create document score map
        doc_scores = {}
        
        # Add semantic results
        for i, doc in enumerate(semantic_docs):
            doc_key = self._doc_key(doc)
            semantic_score = semantic_scores[i] if i < len(semantic_scores) else 0.0
            
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {
                    'doc': doc,
                    'semantic': semantic_score * self.retrieval_config.semantic_weight,
                    'keyword': 0.0
                }
        
        # Add keyword results
        for i, doc in enumerate(keyword_docs):
            doc_key = self._doc_key(doc) 
            keyword_score = keyword_scores[i] if i < len(keyword_scores) else 0.0
            
            if doc_key in doc_scores:
                doc_scores[doc_key]['keyword'] = keyword_score * self.retrieval_config.keyword_weight
            else:
                doc_scores[doc_key] = {
                    'doc': doc,
                    'semantic': 0.0,
                    'keyword': keyword_score * self.retrieval_config.keyword_weight
                }
        
        # Calculate combined scores and sort
        for doc_data in doc_scores.values():
            combined_score = doc_data['semantic'] + doc_data['keyword']
            
            # Apply domain-specific boosting
            if self._has_medical_content(doc_data['doc']):
                combined_score *= 1.2  # Medical content boost
                
            combined_docs.append(doc_data['doc'])
            combined_scores.append(combined_score)
        
        # Sort by combined score and take top-k
        sorted_indices = sorted(range(len(combined_scores)), 
                              key=lambda i: combined_scores[i], reverse=True)
        
        final_docs = [combined_docs[i] for i in sorted_indices[:k]]
        final_semantic = [semantic_scores[i] if i < len(semantic_scores) else 0.0 
                         for i in sorted_indices[:k]]
        final_keyword = [keyword_scores[i] if i < len(keyword_scores) else 0.0
                        for i in sorted_indices[:k]]
        
        total_time = time.time() - start_time
        
        return RetrievalResult(
            documents=final_docs,
            semantic_scores=final_semantic,
            keyword_scores=final_keyword,
            rerank_scores=[],
            total_time=total_time,
            method='hybrid'
        )
    
    def rerank_documents(self, query: str, documents: List[Document], 
                        scores: List[float]) -> Tuple[List[Document], List[float]]:
        """Rerank documents using cross-encoder model.
        
        Args:
            query: Original query
            documents: Documents to rerank
            scores: Original retrieval scores
            
        Returns:
            Tuple of (reranked_documents, rerank_scores)
        """
        if not self.reranking_enabled or not documents:
            return documents, scores
            
        try:
            # Prepare query-document pairs for reranking
            pairs = [(query, doc.page_content[:512]) for doc in documents]  # Truncate for efficiency
            
            # Get reranking scores
            rerank_scores = self.reranker.predict(pairs)
            
            # Filter by relevance threshold if configured
            threshold = self.retrieval_config.reranking.relevance_threshold
            if threshold > 0:
                filtered_indices = [i for i, score in enumerate(rerank_scores) 
                                  if score >= threshold]
            else:
                filtered_indices = list(range(len(rerank_scores)))
            
            # Sort by rerank scores
            sorted_indices = sorted(filtered_indices, 
                                  key=lambda i: rerank_scores[i], reverse=True)
            
            # Apply final top-k limit
            final_k = self.retrieval_config.reranking.top_k_final
            final_indices = sorted_indices[:final_k]
            
            reranked_docs = [documents[i] for i in final_indices]
            final_scores = [rerank_scores[i] for i in final_indices]
            
            return reranked_docs, final_scores
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents, scores
    
    def retrieve(self, query: str) -> RetrievalResult:
        """Main retrieval method with full hybrid + reranking pipeline.
        
        Args:
            query: User query
            
        Returns:
            RetrievalResult with best matching documents
        """
        start_time = time.time()
        
        # Step 1: Hybrid search
        k_initial = self.retrieval_config.reranking.top_k_initial if self.reranking_enabled else self.retrieval_config.top_k
        hybrid_result = self.hybrid_search(query, k=k_initial)
        
        # Step 2: Reranking (if enabled)
        if self.reranking_enabled and hybrid_result.documents:
            reranked_docs, rerank_scores = self.rerank_documents(
                query, hybrid_result.documents, hybrid_result.semantic_scores
            )
            
            return RetrievalResult(
                documents=reranked_docs,
                semantic_scores=hybrid_result.semantic_scores[:len(reranked_docs)],
                keyword_scores=hybrid_result.keyword_scores[:len(reranked_docs)],
                rerank_scores=rerank_scores,
                total_time=time.time() - start_time,
                method='hybrid_reranked'
            )
        
        return hybrid_result
    
    def _doc_key(self, doc: Document) -> str:
        """Create unique key for document deduplication."""
        content_hash = hash(doc.page_content[:100])  # First 100 chars
        source = doc.metadata.get('source', 'unknown')
        return f"{source}_{content_hash}"
    
    def _has_medical_content(self, doc: Document) -> bool:
        """Check if document contains medical content for boosting."""
        content = doc.page_content.lower()
        return any(term in content for term in self.medical_terms)


def create_hybrid_retriever(config: Settings, vector_store, embedding_model) -> HybridRetriever:
    """Factory function to create hybrid retriever.
    
    Args:
        config: System configuration
        vector_store: Vector store instance
        embedding_model: Embedding model instance
        
    Returns:
        Configured HybridRetriever instance
    """
    return HybridRetriever(config, vector_store, embedding_model)