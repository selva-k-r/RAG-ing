"""Retrieval package for advanced document retrieval.

This package contains:
- Hybrid retrieval combining semantic and keyword search
- Cross-encoder reranking for improved relevance
- Query enhancement and expansion
"""

from .hybrid_retrieval import HybridRetriever, RetrievalResult, create_hybrid_retriever

__all__ = [
    'HybridRetriever',
    'RetrievalResult',
    'create_hybrid_retriever'
]