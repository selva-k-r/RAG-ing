"""
RAG-ing: A comprehensive RAG application with multiple connectors and dynamic model selection.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .config.settings import Settings
from .models.embedding_manager import EmbeddingManager
from .models.llm_manager import LLMManager
from .storage.vector_store import VectorStoreManager
from .chunking import ChunkingService

__all__ = [
    "Settings",
    "EmbeddingManager", 
    "LLMManager",
    "VectorStoreManager",
    "ChunkingService",
]