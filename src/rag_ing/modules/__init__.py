"""Modular RAG PoC - Five core modules as specified in Requirement.md

Module 1: Corpus & Embedding Lifecycle - Document ingestion and embedding generation
Module 2: Query Processing & Retrieval - Query processing and document retrieval  
Module 3: LLM Orchestration - Language model integration and response generation
Module 4: UI Layer - User interface with audience toggle and feedback collection
Module 5: Evaluation & Logging - Performance tracking and structured logging
"""

from .corpus_embedding import CorpusEmbeddingModule
from .query_retrieval import QueryRetrievalModule
from .llm_orchestration import LLMOrchestrationModule
from .ui_layer import UILayerModule
from .evaluation_logging import EvaluationLoggingModule

# Note: RAGOrchestrator removed to prevent circular import
# Import RAGOrchestrator directly from orchestrator module when needed

__all__ = [
    "CorpusEmbeddingModule",
    "QueryRetrievalModule", 
    "LLMOrchestrationModule",
    "UILayerModule",
    "EvaluationLoggingModule"
]