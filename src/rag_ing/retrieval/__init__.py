"""Retrieval package for advanced document retrieval.

This package contains:
- Hybrid retrieval combining semantic and keyword search
- Cross-encoder reranking for improved relevance
- Query enhancement and expansion
- Multi-query retrieval with aggregation
- Hybrid context assembly
"""

from .hybrid_retrieval import HybridRetriever, RetrievalResult, create_hybrid_retriever
from .query_expansion import QueryExpansionEngine, QueryExpansionResult
from .multi_query_retrieval import MultiQueryRetriever, ScoredDocument, MultiQueryResult
from .result_aggregation import ResultAggregator, AggregatedResult
from .hybrid_context import HybridContextBuilder, HybridContextResult

__all__ = [
    'HybridRetriever',
    'RetrievalResult',
    'create_hybrid_retriever',
    'QueryExpansionEngine',
    'QueryExpansionResult',
    'MultiQueryRetriever',
    'ScoredDocument',
    'MultiQueryResult',
    'ResultAggregator',
    'AggregatedResult',
    'HybridContextBuilder',
    'HybridContextResult',
]