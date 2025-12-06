"""Multi-Query Retrieval Module

Retrieves documents using multiple query variations in parallel for improved coverage.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass
class ScoredDocument:
    """Document with relevance score."""
    document: Document
    score: float
    query_index: int  # Which query variation retrieved this
    
    @property
    def chunk_id(self) -> str:
        """Get unique chunk identifier."""
        # Use document page_content hash or metadata id
        if hasattr(self.document, 'metadata') and 'chunk_id' in self.document.metadata:
            return self.document.metadata['chunk_id']
        # Fallback: hash of content
        import hashlib
        return hashlib.md5(self.document.page_content.encode()).hexdigest()


@dataclass
class MultiQueryResult:
    """Result from multi-query retrieval."""
    query_results: List[List[ScoredDocument]]  # Results per query
    total_chunks: int
    unique_chunks: int
    queries_executed: int


class MultiQueryRetriever:
    """Retrieve documents using multiple query variations."""
    
    def __init__(self, config, vector_store, embedding_model):
        """Initialize multi-query retriever.
        
        Args:
            config: Settings object with multi_query configuration
            vector_store: Vector store for retrieval
            embedding_model: Embedding model for query encoding
        """
        self.config = config
        self.multi_query_config = config.retrieval.multi_query
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        
        logger.info(
            f"[OK] MultiQueryRetriever initialized "
            f"(k_per_query={self.multi_query_config.k_per_query}, "
            f"parallel={self.multi_query_config.parallel_execution})"
        )
    
    async def retrieve_multi_query(
        self,
        query_variations: List[str],
        project_filter: Optional[str] = None,
        k_per_query: Optional[int] = None
    ) -> MultiQueryResult:
        """Retrieve documents for multiple query variations.
        
        Args:
            query_variations: List of query variations (typically 9-10)
            project_filter: Optional project tag to filter by
            k_per_query: Documents to fetch per query (default from config)
            
        Returns:
            MultiQueryResult with results per query
        """
        k = k_per_query or self.multi_query_config.k_per_query
        
        logger.info(
            f"[...] Starting multi-query retrieval: {len(query_variations)} queries, "
            f"k={k} per query"
        )
        
        try:
            if self.multi_query_config.parallel_execution:
                # Parallel execution (faster)
                query_results = await self._retrieve_parallel(
                    query_variations, project_filter, k
                )
            else:
                # Sequential execution (safer for rate limits)
                query_results = await self._retrieve_sequential(
                    query_variations, project_filter, k
                )
            
            # Calculate statistics
            total_chunks = sum(len(results) for results in query_results)
            unique_chunks = len(self._get_unique_chunk_ids(query_results))
            
            logger.info(
                f"[OK] Multi-query retrieval complete: "
                f"{total_chunks} total chunks, {unique_chunks} unique"
            )
            
            return MultiQueryResult(
                query_results=query_results,
                total_chunks=total_chunks,
                unique_chunks=unique_chunks,
                queries_executed=len(query_variations)
            )
            
        except Exception as e:
            logger.error(f"[X] Multi-query retrieval failed: {e}")
            raise
    
    async def _retrieve_parallel(
        self,
        queries: List[str],
        project_filter: Optional[str],
        k: int
    ) -> List[List[ScoredDocument]]:
        """Retrieve documents for all queries in parallel.
        
        Args:
            queries: List of query strings
            project_filter: Optional project filter
            k: Documents per query
            
        Returns:
            List of results per query
        """
        logger.info(f"[...] Parallel retrieval for {len(queries)} queries")
        
        # Create tasks for parallel execution
        tasks = [
            self._retrieve_single_query(query, idx, project_filter, k)
            for idx, query in enumerate(queries)
        ]
        
        # Execute all queries in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[X] Query {idx} failed: {result}")
                valid_results.append([])  # Empty result for failed query
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _retrieve_sequential(
        self,
        queries: List[str],
        project_filter: Optional[str],
        k: int
    ) -> List[List[ScoredDocument]]:
        """Retrieve documents for all queries sequentially.
        
        Args:
            queries: List of query strings
            project_filter: Optional project filter
            k: Documents per query
            
        Returns:
            List of results per query
        """
        logger.info(f"[...] Sequential retrieval for {len(queries)} queries")
        
        results = []
        for idx, query in enumerate(queries):
            try:
                result = await self._retrieve_single_query(query, idx, project_filter, k)
                results.append(result)
            except Exception as e:
                logger.error(f"[X] Query {idx} failed: {e}")
                results.append([])  # Empty result for failed query
        
        return results
    
    async def _retrieve_single_query(
        self,
        query: str,
        query_index: int,
        project_filter: Optional[str],
        k: int
    ) -> List[ScoredDocument]:
        """Retrieve documents for a single query.
        
        Args:
            query: Query string
            query_index: Index of this query in the list
            project_filter: Optional project filter
            k: Number of documents to retrieve
            
        Returns:
            List of ScoredDocument objects
        """
        try:
            # Generate embedding for query
            query_embedding = await self._get_query_embedding(query)
            
            # Build metadata filter
            metadata_filter = None
            if project_filter:
                metadata_filter = {'project_tag': project_filter}
            
            # Perform similarity search
            results = await self._similarity_search(
                query_embedding, k, metadata_filter
            )
            
            # Convert to ScoredDocument objects
            scored_docs = [
                ScoredDocument(
                    document=doc,
                    score=score,
                    query_index=query_index
                )
                for doc, score in results
            ]
            
            logger.debug(
                f"[OK] Query {query_index}: retrieved {len(scored_docs)} documents "
                f"(filter={project_filter})"
            )
            
            return scored_docs
            
        except Exception as e:
            logger.error(f"[X] Retrieval failed for query {query_index}: {e}")
            raise
    
    async def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query string.
        
        Args:
            query: Query string
            
        Returns:
            Query embedding vector
        """
        try:
            # Check if embedding model has async method
            if hasattr(self.embedding_model, 'aembed_query'):
                embedding = await self.embedding_model.aembed_query(query)
            elif hasattr(self.embedding_model, 'embed_query'):
                # Sync method - wrap in executor
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, self.embedding_model.embed_query, query
                )
            else:
                # Fallback: direct call
                embedding = self.embedding_model(query)
            
            return embedding
            
        except Exception as e:
            logger.error(f"[X] Embedding generation failed: {e}")
            raise
    
    async def _similarity_search(
        self,
        query_embedding: List[float],
        k: int,
        metadata_filter: Optional[Dict[str, Any]]
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search in vector store.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results
            metadata_filter: Optional metadata filter
            
        Returns:
            List of (Document, score) tuples
        """
        try:
            # Use similarity_search_by_vector methods (don't pass query string)
            # This avoids Azure OpenAI embedding API errors
            
            if hasattr(self.vector_store, 'similarity_search_by_vector_with_score'):
                # Best option: search by vector with scores
                if metadata_filter:
                    results = self.vector_store.similarity_search_by_vector_with_score(
                        embedding=query_embedding,
                        k=k,
                        filter=metadata_filter
                    )
                else:
                    results = self.vector_store.similarity_search_by_vector_with_score(
                        embedding=query_embedding,
                        k=k
                    )
            elif hasattr(self.vector_store, 'similarity_search_by_vector'):
                # Search by vector without scores
                if metadata_filter:
                    docs = self.vector_store.similarity_search_by_vector(
                        embedding=query_embedding,
                        k=k,
                        filter=metadata_filter
                    )
                else:
                    docs = self.vector_store.similarity_search_by_vector(
                        embedding=query_embedding,
                        k=k
                    )
                # Assign default scores
                results = [(doc, 1.0) for doc in docs]
            else:
                # Last resort: basic search (may not support filters)
                logger.warning("[!] Vector store doesn't support search by vector, using basic search")
                docs = self.vector_store.similarity_search(
                    query='placeholder',  # Shouldn't be used
                    k=k
                )
                results = [(doc, 1.0) for doc in docs]
            
            return results
            
        except Exception as e:
            logger.error(f"[X] Vector store search failed: {e}")
            raise
    
    def _get_unique_chunk_ids(
        self,
        query_results: List[List[ScoredDocument]]
    ) -> set:
        """Get set of unique chunk IDs across all query results.
        
        Args:
            query_results: Results from all queries
            
        Returns:
            Set of unique chunk IDs
        """
        unique_ids = set()
        for results in query_results:
            for scored_doc in results:
                unique_ids.add(scored_doc.chunk_id)
        return unique_ids
    
    def get_statistics(
        self,
        query_results: List[List[ScoredDocument]]
    ) -> Dict[str, Any]:
        """Calculate statistics about retrieval results.
        
        Args:
            query_results: Results from all queries
            
        Returns:
            Dictionary with statistics
        """
        total_chunks = sum(len(results) for results in query_results)
        unique_ids = self._get_unique_chunk_ids(query_results)
        
        # Calculate frequency distribution
        chunk_frequencies = {}
        for results in query_results:
            for scored_doc in results:
                chunk_id = scored_doc.chunk_id
                chunk_frequencies[chunk_id] = chunk_frequencies.get(chunk_id, 0) + 1
        
        # Find most frequent chunks
        top_chunks = sorted(
            chunk_frequencies.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_chunks': total_chunks,
            'unique_chunks': len(unique_ids),
            'avg_chunks_per_query': total_chunks / len(query_results) if query_results else 0,
            'chunk_frequencies': chunk_frequencies,
            'top_10_frequent': top_chunks,
            'max_frequency': max(chunk_frequencies.values()) if chunk_frequencies else 0,
            'min_frequency': min(chunk_frequencies.values()) if chunk_frequencies else 0
        }
