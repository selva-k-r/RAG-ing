"""Hybrid Context Builder

Combines semantic search results with keyword search results using configurable weights.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass
class HybridContextResult:
    """Result from hybrid context assembly."""
    documents: List[Document]
    semantic_count: int
    keyword_count: int
    duplicates_removed: int
    total_count: int


class HybridContextBuilder:
    """Combine semantic and keyword search results with configurable weights."""
    
    def __init__(self, config):
        """Initialize hybrid context builder.
        
        Args:
            config: Settings object with hybrid_context configuration
        """
        self.config = config
        self.hybrid_config = config.retrieval.hybrid_context
        
        logger.info(
            f"[OK] HybridContextBuilder initialized "
            f"(semantic={self.hybrid_config.semantic_weight:.1%}, "
            f"keyword={self.hybrid_config.keyword_weight:.1%}, "
            f"total={self.hybrid_config.total_chunks})"
        )
    
    def build_hybrid_context(
        self,
        semantic_results: List[Document],
        keyword_results: List[Document]
    ) -> HybridContextResult:
        """Combine semantic and keyword results with 70/30 split.
        
        Algorithm:
            1. Calculate how many chunks from each source (e.g., 7 semantic, 3 keyword)
            2. Take top N semantic results
            3. Take top M keyword results that are NOT in semantic (avoid duplicates)
            4. If insufficient unique keyword results, backfill from semantic
            5. Return combined list of total_chunks
            
        Args:
            semantic_results: Semantic search results (from aggregation)
            keyword_results: Keyword search results (from BM25)
            
        Returns:
            HybridContextResult with combined documents
        """
        total_chunks = self.hybrid_config.total_chunks
        semantic_weight = self.hybrid_config.semantic_weight
        keyword_weight = self.hybrid_config.keyword_weight
        
        # Calculate target counts
        semantic_count = int(total_chunks * semantic_weight)
        keyword_count = int(total_chunks * keyword_weight)
        
        # Ensure we get exactly total_chunks (handle rounding)
        if semantic_count + keyword_count < total_chunks:
            semantic_count += 1
        
        logger.info(
            f"[...] Building hybrid context: "
            f"{semantic_count} semantic + {keyword_count} keyword = {total_chunks} total"
        )
        
        # Step 1: Take top N semantic results
        selected_semantic = semantic_results[:semantic_count]
        
        # Step 2: Get unique keyword results (not in semantic)
        if self.hybrid_config.deduplication:
            unique_keyword = self._get_unique_keyword_results(
                selected_semantic, keyword_results, keyword_count
            )
        else:
            unique_keyword = keyword_results[:keyword_count]
        
        # Step 3: Backfill if needed
        combined_documents = list(selected_semantic)
        combined_documents.extend(unique_keyword)
        
        duplicates_removed = 0
        
        # If we don't have enough unique keyword results, backfill from semantic
        if len(combined_documents) < total_chunks:
            remaining_needed = total_chunks - len(combined_documents)
            backfill_start = semantic_count
            backfill_docs = semantic_results[backfill_start:backfill_start + remaining_needed]
            combined_documents.extend(backfill_docs)
            
            logger.debug(
                f"[...] Backfilled {len(backfill_docs)} documents from semantic "
                f"(insufficient unique keyword results)"
            )
        
        # Trim to exact count if needed
        combined_documents = combined_documents[:total_chunks]
        
        if self.hybrid_config.deduplication:
            duplicates_removed = keyword_count - len(unique_keyword)
        
        logger.info(
            f"[OK] Hybrid context built: "
            f"{len(selected_semantic)} semantic + {len(unique_keyword)} keyword "
            f"(removed {duplicates_removed} duplicates)"
        )
        
        return HybridContextResult(
            documents=combined_documents,
            semantic_count=len(selected_semantic),
            keyword_count=len(unique_keyword),
            duplicates_removed=duplicates_removed,
            total_count=len(combined_documents)
        )
    
    def _get_unique_keyword_results(
        self,
        semantic_docs: List[Document],
        keyword_docs: List[Document],
        target_count: int
    ) -> List[Document]:
        """Get keyword results that are not in semantic results.
        
        Args:
            semantic_docs: Already selected semantic documents
            keyword_docs: Candidate keyword documents
            target_count: How many unique keyword docs to get
            
        Returns:
            List of unique keyword documents
        """
        # Get content hashes of semantic documents for comparison
        semantic_hashes = set(self._get_doc_hash(doc) for doc in semantic_docs)
        
        # Filter keyword documents
        unique_keyword = []
        for doc in keyword_docs:
            if len(unique_keyword) >= target_count:
                break
            
            doc_hash = self._get_doc_hash(doc)
            if doc_hash not in semantic_hashes:
                unique_keyword.append(doc)
        
        return unique_keyword
    
    def _get_doc_hash(self, doc: Document) -> str:
        """Get hash identifier for document (for deduplication).
        
        Args:
            doc: Document object
            
        Returns:
            Hash string
        """
        # Try to use metadata ID first
        if hasattr(doc, 'metadata'):
            if 'chunk_id' in doc.metadata:
                return doc.metadata['chunk_id']
            if 'id' in doc.metadata:
                return doc.metadata['id']
        
        # Fallback: hash of content
        import hashlib
        return hashlib.md5(doc.page_content.encode()).hexdigest()
    
    def get_context_stats(
        self,
        result: HybridContextResult
    ) -> Dict[str, Any]:
        """Get statistics about hybrid context.
        
        Args:
            result: HybridContextResult object
            
        Returns:
            Dictionary with statistics
        """
        semantic_percentage = (result.semantic_count / result.total_count * 100) if result.total_count > 0 else 0
        keyword_percentage = (result.keyword_count / result.total_count * 100) if result.total_count > 0 else 0
        
        return {
            'total_documents': result.total_count,
            'semantic_documents': result.semantic_count,
            'keyword_documents': result.keyword_count,
            'semantic_percentage': semantic_percentage,
            'keyword_percentage': keyword_percentage,
            'duplicates_removed': result.duplicates_removed,
            'target_split': f"{self.hybrid_config.semantic_weight:.0%}/{self.hybrid_config.keyword_weight:.0%}",
            'actual_split': f"{semantic_percentage:.0f}%/{keyword_percentage:.0f}%"
        }
    
    def build_context_string(
        self,
        documents: List[Document],
        include_metadata: bool = True,
        separator: str = "\n\n---\n\n"
    ) -> str:
        """Build context string from documents for LLM.
        
        Args:
            documents: List of documents
            include_metadata: Include metadata in context
            separator: Separator between documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            if include_metadata and hasattr(doc, 'metadata'):
                metadata = doc.metadata
                # Format metadata
                metadata_str = f"[Document {i}]"
                if 'source' in metadata:
                    metadata_str += f"\nSource: {metadata['source']}"
                if 'file_path' in metadata:
                    metadata_str += f"\nFile: {metadata['file_path']}"
                if 'project_tag' in metadata:
                    metadata_str += f"\nProject: {metadata['project_tag']}"
                
                context_parts.append(f"{metadata_str}\n\n{doc.page_content}")
            else:
                context_parts.append(doc.page_content)
        
        return separator.join(context_parts)
    
    def adjust_weights(
        self,
        semantic_weight: float,
        keyword_weight: float
    ):
        """Adjust semantic/keyword weights dynamically.
        
        Args:
            semantic_weight: New semantic weight (0.0 to 1.0)
            keyword_weight: New keyword weight (0.0 to 1.0)
            
        Raises:
            ValueError: If weights don't sum to 1.0
        """
        if abs(semantic_weight + keyword_weight - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0: semantic={semantic_weight}, keyword={keyword_weight}"
            )
        
        self.hybrid_config.semantic_weight = semantic_weight
        self.hybrid_config.keyword_weight = keyword_weight
        
        logger.info(
            f"[OK] Hybrid weights adjusted: "
            f"semantic={semantic_weight:.1%}, keyword={keyword_weight:.1%}"
        )
