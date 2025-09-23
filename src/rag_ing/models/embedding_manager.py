"""Embedding model manager for dynamic embedding model selection."""

from typing import List, Optional, Dict, Any
from langchain.embeddings.base import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
import logging

from ..config.settings import EmbeddingModelConfig

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages different embedding models and provides a unified interface."""
    
    def __init__(self):
        self._models: Dict[str, Embeddings] = {}
        self._current_model: Optional[Embeddings] = None
        self._current_config: Optional[EmbeddingModelConfig] = None
    
    def load_model(self, config: EmbeddingModelConfig) -> Embeddings:
        """Load an embedding model based on configuration."""
        model_key = f"{config.provider}_{config.model_name}"
        
        if model_key in self._models:
            logger.info(f"Using cached embedding model: {model_key}")
            self._current_model = self._models[model_key]
            self._current_config = config
            return self._current_model
        
        logger.info(f"Loading new embedding model: {config.provider}/{config.model_name}")
        
        if config.provider.lower() == "openai":
            model = self._load_openai_embeddings(config)
        elif config.provider.lower() == "huggingface":
            model = self._load_huggingface_embeddings(config)
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")
        
        self._models[model_key] = model
        self._current_model = model
        self._current_config = config
        
        return model
    
    def _load_openai_embeddings(self, config: EmbeddingModelConfig) -> OpenAIEmbeddings:
        """Load OpenAI embeddings."""
        return OpenAIEmbeddings(
            model=config.model_name,
            openai_api_key=config.api_key,
            dimensions=config.dimensions
        )
    
    def _load_huggingface_embeddings(self, config: EmbeddingModelConfig) -> HuggingFaceEmbeddings:
        """Load HuggingFace embeddings."""
        return HuggingFaceEmbeddings(
            model_name=config.model_name,
            encode_kwargs={'normalize_embeddings': True}
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if not self._current_model:
            raise ValueError("No embedding model loaded. Call load_model() first.")
        
        return self._current_model.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        if not self._current_model:
            raise ValueError("No embedding model loaded. Call load_model() first.")
        
        return self._current_model.embed_query(text)
    
    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently loaded model."""
        if not self._current_config:
            return None
        
        return {
            "provider": self._current_config.provider,
            "model_name": self._current_config.model_name,
            "dimensions": self._current_config.dimensions,
        }
    
    def list_available_providers(self) -> List[str]:
        """List available embedding providers."""
        return ["openai", "huggingface"]
    
    def get_recommended_models(self, provider: str) -> List[str]:
        """Get recommended models for a provider."""
        recommendations = {
            "openai": [
                "text-embedding-ada-002",
                "text-embedding-3-small",
                "text-embedding-3-large"
            ],
            "huggingface": [
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "BAAI/bge-small-en-v1.5",
                "BAAI/bge-base-en-v1.5"
            ]
        }
        return recommendations.get(provider.lower(), [])


# Global embedding manager instance
embedding_manager = EmbeddingManager()