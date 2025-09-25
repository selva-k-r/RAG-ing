"""
RAG-ing: A comprehensive RAG application with modular architecture.

Modular RAG PoC with 5 core modules:
- Module 1: Corpus & Embedding Lifecycle
- Module 2: Query Processing & Retrieval  
- Module 3: LLM Orchestration
- Module 4: UI Layer
- Module 5: Evaluation & Logging
"""

__version__ = "0.1.0"
__author__ = "RAG-ing Team"
__email__ = "team@rag-ing.com"

# Main orchestrator and configuration
from .orchestrator import RAGOrchestrator, create_rag_system
from .config.settings import Settings

# Individual modules for advanced usage
from .modules import (
    CorpusEmbeddingModule,
    QueryRetrievalModule,
    LLMOrchestrationModule,
    UILayerModule,
    EvaluationLoggingModule
)

__all__ = [
    # Main API
    "RAGOrchestrator",
    "create_rag_system",
    "Settings",
    
    # Individual modules
    "CorpusEmbeddingModule",
    "QueryRetrievalModule", 
    "LLMOrchestrationModule",
    "UILayerModule",
    "EvaluationLoggingModule",
]