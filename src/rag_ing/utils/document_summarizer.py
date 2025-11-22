"""Document summarizer for hierarchical storage.

Creates concise summaries of documents for fast high-level search.
Detailed chunks are fetched only when summary indicates relevance.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """Generates document summaries for hierarchical retrieval."""
    
    def __init__(self, llm_client: Any, summary_prompt: str):
        """Initialize summarizer with LLM client.
        
        Args:
            llm_client: LLM client for generating summaries
            summary_prompt: Prompt template for summarization
        """
        self.llm_client = llm_client
        self.summary_prompt = summary_prompt
        logger.info("DocumentSummarizer initialized")
    
    def summarize_document(self, document: Document) -> str:
        """Generate concise summary of document.
        
        Args:
            document: Document to summarize
            
        Returns:
            Summary string (2-3 sentences)
        """
        try:
            # Build prompt
            prompt = f"{self.summary_prompt}\n\nDocument:\n{document.page_content}"
            
            # Generate summary
            # Use the client's completion method
            if hasattr(self.llm_client, 'chat'):
                # OpenAI-style chat
                response = self.llm_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
            else:
                # Fallback: use the document title + first 200 chars
                logger.warning("LLM client not available - using fallback summarization")
                summary = self._fallback_summary(document)
            
            logger.debug(f"Generated summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}. Using fallback.")
            return self._fallback_summary(document)
    
    def _fallback_summary(self, document: Document) -> str:
        """Generate simple summary without LLM.
        
        Args:
            document: Document to summarize
            
        Returns:
            First 200 characters as summary
        """
        content = document.page_content
        metadata = document.metadata
        
        # Extract title if available
        title = metadata.get('title', metadata.get('filename', 'Document'))
        
        # Use first 200 characters
        excerpt = content[:200].strip()
        if len(content) > 200:
            excerpt += "..."
        
        return f"{title}: {excerpt}"
    
    def create_summary_documents(
        self, 
        documents: List[Document],
        batch_size: int = 5
    ) -> List[Document]:
        """Create summary documents for a list of source documents.
        
        Args:
            documents: List of documents to summarize
            batch_size: Process in batches to avoid rate limits
            
        Returns:
            List of summary documents with metadata linking to originals
        """
        summary_docs = []
        
        for i, doc in enumerate(documents):
            try:
                # Generate summary
                summary_text = self.summarize_document(doc)
                
                # Create summary document with link to original
                summary_doc = Document(
                    page_content=summary_text,
                    metadata={
                        **doc.metadata,  # Preserve original metadata
                        "is_summary": True,
                        "original_doc_id": doc.metadata.get('source', f'doc_{i}'),
                        "summary_method": "llm" if hasattr(self.llm_client, 'chat') else "fallback"
                    }
                )
                
                summary_docs.append(summary_doc)
                
                # Log progress
                if (i + 1) % batch_size == 0:
                    logger.info(f"Summarized {i + 1}/{len(documents)} documents")
                    
            except Exception as e:
                logger.error(f"Failed to summarize document {i}: {e}")
                continue
        
        logger.info(f"Created {len(summary_docs)} summaries from {len(documents)} documents")
        return summary_docs



