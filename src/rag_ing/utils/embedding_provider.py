"""
Unified Embedding Provider
Supports Azure OpenAI and local open-source models with easy switching
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers"""
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass


class AzureOpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Azure OpenAI Embedding Provider with rate limiting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get('model', 'text-embedding-ada-002')
        self.endpoint = os.getenv('AZURE_OPENAI_EMBEDDING_ENDPOINT', config.get('endpoint'))
        self.api_key = os.getenv('AZURE_OPENAI_EMBEDDING_API_KEY', config.get('api_key'))
        self.deployment_name = config.get('deployment_name', self.model)
        self.api_version = os.getenv('AZURE_OPENAI_EMBEDDING_API_VERSION', 
                                     config.get('api_version', '2023-05-15'))
        
        # Rate limiting config
        self.max_retries = config.get('max_retries', 5)
        self.retry_delay = config.get('retry_delay', 2)
        self.requests_per_minute = config.get('requests_per_minute', 60)
        
        self._last_request_time = 0
        self._request_interval = 60.0 / self.requests_per_minute
        
        # Initialize Azure OpenAI client
        self._init_client()
        
        logger.info(f"[OK] Azure OpenAI Embedding Provider initialized")
        logger.info(f"     Model: {self.model}")
        logger.info(f"     Deployment: {self.deployment_name}")
        logger.info(f"     Rate limit: {self.requests_per_minute} req/min")
    
    def _init_client(self):
        """Initialize Azure OpenAI client"""
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            
            self.client = AzureOpenAIEmbeddings(
                azure_endpoint=self.endpoint,
                azure_deployment=self.deployment_name,
                openai_api_version=self.api_version,
                openai_api_key=self.api_key
            )
            
            # Test with a small query
            test_embedding = self.client.embed_query("test")
            self._dimension = len(test_embedding)
            
            logger.info(f"     Vector dimension: {self._dimension}")
            
        except Exception as e:
            logger.error(f"[X] Failed to initialize Azure OpenAI client: {e}")
            raise
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._request_interval:
            sleep_time = self._request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry function with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if rate limit error
                if 'rate limit' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"[!] Rate limit hit, retrying in {wait_time}s (attempt {attempt+1}/{self.max_retries})")
                        time.sleep(wait_time)
                        continue
                
                # Other errors
                logger.error(f"[X] Azure OpenAI error: {e}")
                raise
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents with rate limiting"""
        return self._retry_with_backoff(self.client.embed_documents, texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query with rate limiting"""
        return self._retry_with_backoff(self.client.embed_query, text)
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"azure_openai ({self.model})"


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local Open-Source Embedding Provider (BGE, E5, etc.)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get('model_name', 'BAAI/bge-large-en-v1.5')
        self.device = config.get('device', 'cpu')
        self.batch_size = config.get('batch_size', 32)
        self.max_length = config.get('max_length', 512)
        self.normalize = config.get('normalize_embeddings', True)
        self.show_progress = config.get('show_progress', True)
        self.num_threads = config.get('num_threads', 4)
        self.cache_folder = config.get('cache_folder', './models/embeddings')
        
        # Create cache folder
        os.makedirs(self.cache_folder, exist_ok=True)
        
        # Initialize model
        self._init_model()
        
        logger.info(f"[OK] Local Embedding Provider initialized")
        logger.info(f"     Model: {self.model_name}")
        logger.info(f"     Device: {self.device}")
        logger.info(f"     Batch size: {self.batch_size}")
        logger.info(f"     Vector dimension: {self._dimension}")
    
    def _init_model(self):
        """Initialize sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            logger.info(f"Loading model: {self.model_name}...")
            
            # Set number of threads for CPU
            if self.device == 'cpu':
                torch.set_num_threads(self.num_threads)
            
            # Load model (downloads if not cached)
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_folder
            )
            
            # Get dimension by encoding test text
            test_embedding = self.model.encode("test", normalize_embeddings=self.normalize)
            self._dimension = len(test_embedding)
            
            logger.info(f"[OK] Model loaded successfully")
            
        except ImportError:
            logger.error("[X] sentence-transformers not installed")
            logger.error("    Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"[X] Failed to load model: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=self.show_progress,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        embedding = self.model.encode(
            text,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True
        )
        return embedding.tolist()
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"local ({self.model_name})"


class HybridEmbeddingProvider(BaseEmbeddingProvider):
    """Hybrid provider that uses different models for ingestion vs queries"""
    
    def __init__(self, config: Dict[str, Any], all_configs: Dict[str, Any]):
        self.config = config
        self.ingestion_provider_name = config.get('ingestion', 'local')
        self.query_provider_name = config.get('queries', 'azure_openai')
        self.fallback_provider_name = config.get('fallback', 'local')
        
        # Initialize providers
        logger.info("[OK] Initializing Hybrid Embedding Provider")
        
        # Ingestion provider
        logger.info(f"     Ingestion: {self.ingestion_provider_name}")
        self.ingestion_provider = self._create_provider(
            self.ingestion_provider_name, all_configs
        )
        
        # Query provider
        logger.info(f"     Queries: {self.query_provider_name}")
        self.query_provider = self._create_provider(
            self.query_provider_name, all_configs
        )
        
        # Fallback provider
        if self.fallback_provider_name:
            logger.info(f"     Fallback: {self.fallback_provider_name}")
            self.fallback_provider = self._create_provider(
                self.fallback_provider_name, all_configs
            )
        else:
            self.fallback_provider = None
        
        # Use ingestion provider dimension as default
        self._dimension = self.ingestion_provider.get_dimension()
        
        logger.info(f"[OK] Hybrid provider ready")
    
    def _create_provider(self, provider_name: str, all_configs: Dict[str, Any]):
        """Create a specific provider"""
        if provider_name == 'azure_openai':
            return AzureOpenAIEmbeddingProvider(all_configs.get('azure_openai', {}))
        elif provider_name == 'local':
            return LocalEmbeddingProvider(all_configs.get('local', {}))
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Use ingestion provider for documents"""
        try:
            return self.ingestion_provider.embed_documents(texts)
        except Exception as e:
            if self.fallback_provider:
                logger.warning(f"[!] Ingestion provider failed, using fallback: {e}")
                return self.fallback_provider.embed_documents(texts)
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Use query provider for queries"""
        try:
            return self.query_provider.embed_query(text)
        except Exception as e:
            if self.fallback_provider:
                logger.warning(f"[!] Query provider failed, using fallback: {e}")
                return self.fallback_provider.embed_query(text)
            raise
    
    def get_dimension(self) -> int:
        return self._dimension
    
    def get_provider_name(self) -> str:
        return f"hybrid (ingestion:{self.ingestion_provider_name}, query:{self.query_provider_name})"


def create_embedding_provider(config: Dict[str, Any]) -> BaseEmbeddingProvider:
    """
    Factory function to create embedding provider based on config
    
    Args:
        config: Embedding configuration dictionary
        
    Returns:
        BaseEmbeddingProvider instance
        
    Example:
        config = {
            'provider': 'local',  # or 'azure_openai' or 'hybrid'
            'local': {...},
            'azure_openai': {...},
            'hybrid': {...}
        }
    """
    provider_type = config.get('provider', 'azure_openai')
    
    logger.info(f"Creating embedding provider: {provider_type}")
    
    if provider_type == 'azure_openai':
        return AzureOpenAIEmbeddingProvider(config.get('azure_openai', {}))
    
    elif provider_type == 'local':
        return LocalEmbeddingProvider(config.get('local', {}))
    
    elif provider_type == 'hybrid':
        return HybridEmbeddingProvider(config.get('hybrid', {}), config)
    
    else:
        raise ValueError(f"Unknown embedding provider: {provider_type}")


# Convenience function for backward compatibility
def get_embedding_model(config: Dict[str, Any]):
    """Legacy function that returns langchain-compatible wrapper"""
    provider = create_embedding_provider(config)
    
    # Return wrapper with langchain interface
    class LangChainWrapper:
        def __init__(self, provider):
            self.provider = provider
        
        def embed_documents(self, texts):
            return self.provider.embed_documents(texts)
        
        def embed_query(self, text):
            return self.provider.embed_query(text)
    
    return LangChainWrapper(provider)
