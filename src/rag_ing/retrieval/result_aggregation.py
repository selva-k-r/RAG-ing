"""Result Aggregation Module

Aggregates multi-query retrieval results using frequency × relevance scoring.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from langchain_core.documents import Document

from .multi_query_retrieval import ScoredDocument

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResult:
    """Aggregated document with combined scoring."""
    document: Document
    chunk_id: str
    frequency: int  # Number of queries that returned this chunk
    avg_score: float  # Average relevance score across appearances
    final_score: float  # frequency × avg_score
    query_indices: List[int]  # Which queries returned this chunk
    scores: List[float]  # Individual scores from each query


class ResultAggregator:
    """Aggregate multi-query results using frequency × relevance scoring."""
    
    def __init__(self, config):
        """Initialize result aggregator.
        
        Args:
            config: Settings object with multi_query configuration
        """
        self.config = config
        self.multi_query_config = config.retrieval.multi_query
        
        logger.info(
            f"[OK] ResultAggregator initialized "
            f"(method={self.multi_query_config.aggregation_method}, "
            f"min_freq={self.multi_query_config.min_frequency_threshold})"
        )
    
    def aggregate_by_frequency_relevance(
        self,
        multi_query_results: List[List[ScoredDocument]],
        top_k: int = 10
    ) -> List[AggregatedResult]:
        """Aggregate results using frequency × relevance scoring.
        
        Algorithm:
            1. Group documents by chunk_id (same chunk appearing multiple times)
            2. Calculate frequency = number of appearances
            3. Calculate avg_relevance = mean of scores across appearances
            4. Calculate final_score = frequency × avg_relevance
            5. Sort by final_score DESC
            6. Return top K
            
        Args:
            multi_query_results: Results from each query variation
            top_k: Number of top results to return
            
        Returns:
            List of AggregatedResult objects sorted by final_score
        """
        logger.info(f"[...] Aggregating {len(multi_query_results)} query results")
        
        # Group documents by chunk_id
        chunk_groups = defaultdict(lambda: {
            'document': None,
            'scores': [],
            'query_indices': []
        })
        
        for query_idx, query_results in enumerate(multi_query_results):
            for scored_doc in query_results:
                chunk_id = scored_doc.chunk_id
                
                # Store document (first occurrence)
                if chunk_groups[chunk_id]['document'] is None:
                    chunk_groups[chunk_id]['document'] = scored_doc.document
                
                # Accumulate scores and query indices
                chunk_groups[chunk_id]['scores'].append(scored_doc.score)
                chunk_groups[chunk_id]['query_indices'].append(query_idx)
        
        # Calculate aggregated scores
        aggregated_results = []
        
        for chunk_id, group_data in chunk_groups.items():
            frequency = len(group_data['scores'])
            
            # Apply minimum frequency threshold
            if frequency < self.multi_query_config.min_frequency_threshold:
                continue
            
            # Calculate average score
            avg_score = sum(group_data['scores']) / frequency
            
            # Calculate final score based on aggregation method
            final_score = self._calculate_final_score(
                frequency, avg_score, group_data['scores']
            )
            
            aggregated_results.append(
                AggregatedResult(
                    document=group_data['document'],
                    chunk_id=chunk_id,
                    frequency=frequency,
                    avg_score=avg_score,
                    final_score=final_score,
                    query_indices=group_data['query_indices'],
                    scores=group_data['scores']
                )
            )
        
        # Sort by final_score descending
        aggregated_results.sort(key=lambda x: x.final_score, reverse=True)
        
        # Return top K
        top_results = aggregated_results[:top_k]
        
        logger.info(
            f"[OK] Aggregation complete: {len(aggregated_results)} unique chunks, "
            f"returning top {len(top_results)}"
        )
        
        # Log top results for debugging
        if top_results:
            logger.debug("[...] Top 3 aggregated results:")
            for i, result in enumerate(top_results[:3]):
                logger.debug(
                    f"  {i+1}. freq={result.frequency}, "
                    f"avg_score={result.avg_score:.3f}, "
                    f"final_score={result.final_score:.3f}"
                )
        
        return top_results
    
    def _calculate_final_score(
        self,
        frequency: int,
        avg_score: float,
        scores: List[float]
    ) -> float:
        """Calculate final score based on aggregation method.
        
        Args:
            frequency: Number of times chunk appeared
            avg_score: Average relevance score
            scores: Individual scores from each query
            
        Returns:
            Final aggregated score
        """
        method = self.multi_query_config.aggregation_method
        
        if method == 'frequency_relevance':
            # Frequency × Average Relevance
            return frequency * avg_score
        
        elif method == 'max_score':
            # Maximum score across all queries
            return max(scores)
        
        elif method == 'avg_score':
            # Simple average (frequency not considered)
            return avg_score
        
        else:
            logger.warning(f"[!] Unknown aggregation method: {method}, using frequency_relevance")
            return frequency * avg_score
    
    def aggregate_results(
        self,
        multi_query_results: List[List[ScoredDocument]],
        top_k: int = 10
    ) -> List[AggregatedResult]:
        """Main aggregation method (routes to specific aggregation method).
        
        Args:
            multi_query_results: Results from each query variation
            top_k: Number of top results to return
            
        Returns:
            List of AggregatedResult objects
        """
        # Currently only supports frequency_relevance, but can be extended
        return self.aggregate_by_frequency_relevance(multi_query_results, top_k)
    
    def get_aggregation_stats(
        self,
        aggregated_results: List[AggregatedResult]
    ) -> Dict[str, Any]:
        """Calculate statistics about aggregation results.
        
        Args:
            aggregated_results: List of aggregated results
            
        Returns:
            Dictionary with statistics
        """
        if not aggregated_results:
            return {
                'total_results': 0,
                'avg_frequency': 0,
                'avg_score': 0,
                'avg_final_score': 0
            }
        
        frequencies = [r.frequency for r in aggregated_results]
        avg_scores = [r.avg_score for r in aggregated_results]
        final_scores = [r.final_score for r in aggregated_results]
        
        return {
            'total_results': len(aggregated_results),
            'avg_frequency': sum(frequencies) / len(frequencies),
            'max_frequency': max(frequencies),
            'min_frequency': min(frequencies),
            'avg_score': sum(avg_scores) / len(avg_scores),
            'max_score': max(avg_scores),
            'min_score': min(avg_scores),
            'avg_final_score': sum(final_scores) / len(final_scores),
            'max_final_score': max(final_scores),
            'min_final_score': min(final_scores),
            'frequency_distribution': self._get_frequency_distribution(frequencies)
        }
    
    def _get_frequency_distribution(self, frequencies: List[int]) -> Dict[int, int]:
        """Get distribution of chunk frequencies.
        
        Args:
            frequencies: List of frequency values
            
        Returns:
            Dictionary mapping frequency to count
        """
        distribution = defaultdict(int)
        for freq in frequencies:
            distribution[freq] += 1
        return dict(distribution)
    
    def convert_to_documents(
        self,
        aggregated_results: List[AggregatedResult]
    ) -> List[Document]:
        """Convert aggregated results back to Document objects.
        
        Adds aggregation metadata to document metadata.
        
        Args:
            aggregated_results: List of aggregated results
            
        Returns:
            List of Document objects with enriched metadata
        """
        documents = []
        
        for result in aggregated_results:
            # Create new document with enriched metadata
            doc = Document(
                page_content=result.document.page_content,
                metadata={
                    **result.document.metadata,
                    # Add aggregation metadata
                    'aggregation_frequency': result.frequency,
                    'aggregation_avg_score': result.avg_score,
                    'aggregation_final_score': result.final_score,
                    'aggregation_query_indices': result.query_indices
                }
            )
            documents.append(doc)
        
        return documents
    
    def filter_by_threshold(
        self,
        aggregated_results: List[AggregatedResult],
        min_frequency: Optional[int] = None,
        min_avg_score: Optional[float] = None,
        min_final_score: Optional[float] = None
    ) -> List[AggregatedResult]:
        """Filter aggregated results by thresholds.
        
        Args:
            aggregated_results: List of aggregated results
            min_frequency: Minimum frequency threshold
            min_avg_score: Minimum average score threshold
            min_final_score: Minimum final score threshold
            
        Returns:
            Filtered list of aggregated results
        """
        filtered = aggregated_results
        
        if min_frequency is not None:
            filtered = [r for r in filtered if r.frequency >= min_frequency]
            logger.debug(f"[...] After frequency filter (>={min_frequency}): {len(filtered)} results")
        
        if min_avg_score is not None:
            filtered = [r for r in filtered if r.avg_score >= min_avg_score]
            logger.debug(f"[...] After avg_score filter (>={min_avg_score}): {len(filtered)} results")
        
        if min_final_score is not None:
            filtered = [r for r in filtered if r.final_score >= min_final_score]
            logger.debug(f"[...] After final_score filter (>={min_final_score}): {len(filtered)} results")
        
        return filtered
