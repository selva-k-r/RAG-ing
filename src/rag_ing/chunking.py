"""Text chunking service for processing documents."""

from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.docstore.document import Document
import logging

from .config.settings import ChunkingConfig

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking documents into smaller pieces."""
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunking service with configuration."""
        self.config = config or ChunkingConfig()
        self._splitters: Dict[str, Any] = {}
    
    def chunk_documents(self, documents: List[Document], 
                       chunk_method: str = "recursive") -> List[Document]:
        """
        Chunk a list of documents.
        
        Args:
            documents: List of documents to chunk
            chunk_method: Method to use for chunking ("recursive", "character")
        
        Returns:
            List of chunked documents
        """
        if not documents:
            return []
        
        splitter = self._get_splitter(chunk_method)
        
        try:
            chunked_docs = []
            for doc in documents:
                chunks = splitter.split_documents([doc])
                
                # Add chunk metadata
                for i, chunk in enumerate(chunks):
                    chunk.metadata.update({
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_method": chunk_method,
                        "original_doc_id": doc.metadata.get("id", "unknown")
                    })
                
                chunked_docs.extend(chunks)
            
            logger.info(f"Chunked {len(documents)} documents into {len(chunked_docs)} chunks")
            return chunked_docs
        
        except Exception as e:
            logger.error(f"Error chunking documents: {e}")
            return documents  # Return original documents if chunking fails
    
    def chunk_text(self, text: str, chunk_method: str = "recursive", 
                   metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Chunk a single text string.
        
        Args:
            text: Text to chunk
            chunk_method: Method to use for chunking
            metadata: Optional metadata to add to chunks
        
        Returns:
            List of chunked documents
        """
        if not text.strip():
            return []
        
        # Create a document from the text
        doc = Document(page_content=text, metadata=metadata or {})
        
        return self.chunk_documents([doc], chunk_method)
    
    def _get_splitter(self, chunk_method: str):
        """Get or create a text splitter."""
        if chunk_method in self._splitters:
            return self._splitters[chunk_method]
        
        if chunk_method == "recursive":
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separators=self.config.separators,
                length_function=len
            )
        elif chunk_method == "character":
            splitter = CharacterTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separator="\n\n",
                length_function=len
            )
        else:
            raise ValueError(f"Unsupported chunk method: {chunk_method}")
        
        self._splitters[chunk_method] = splitter
        return splitter
    
    def get_chunk_statistics(self, documents: List[Document]) -> Dict[str, Any]:
        """Get statistics about chunked documents."""
        if not documents:
            return {}
        
        chunk_sizes = [len(doc.page_content) for doc in documents]
        
        stats = {
            "total_chunks": len(documents),
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_characters": sum(chunk_sizes)
        }
        
        # Count chunks by source
        sources = {}
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        stats["chunks_by_source"] = sources
        
        return stats
    
    def update_config(self, new_config: ChunkingConfig):
        """Update chunking configuration and clear cached splitters."""
        self.config = new_config
        self._splitters.clear()
        logger.info("Updated chunking configuration")
    
    def get_available_methods(self) -> List[str]:
        """Get list of available chunking methods."""
        return ["recursive", "character"]


# Global chunking service instance
chunking_service = ChunkingService()