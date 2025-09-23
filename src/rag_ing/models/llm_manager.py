"""LLM manager for dynamic LLM selection."""

from typing import Optional, Dict, Any, List
from langchain.llms.base import BaseLLM
from langchain_openai import ChatOpenAI
from langchain_community.llms import Anthropic
import logging

from ..config.settings import LLMConfig

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages different LLM models and provides a unified interface."""
    
    def __init__(self):
        self._models: Dict[str, BaseLLM] = {}
        self._current_model: Optional[BaseLLM] = None
        self._current_config: Optional[LLMConfig] = None
    
    def load_model(self, config: LLMConfig) -> BaseLLM:
        """Load an LLM based on configuration."""
        model_key = f"{config.provider}_{config.model_name}"
        
        if model_key in self._models:
            logger.info(f"Using cached LLM: {model_key}")
            self._current_model = self._models[model_key]
            self._current_config = config
            return self._current_model
        
        logger.info(f"Loading new LLM: {config.provider}/{config.model_name}")
        
        if config.provider.lower() == "openai":
            model = self._load_openai_llm(config)
        elif config.provider.lower() == "anthropic":
            model = self._load_anthropic_llm(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
        self._models[model_key] = model
        self._current_model = model
        self._current_config = config
        
        return model
    
    def _load_openai_llm(self, config: LLMConfig) -> ChatOpenAI:
        """Load OpenAI LLM."""
        return ChatOpenAI(
            model_name=config.model_name,
            openai_api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    def _load_anthropic_llm(self, config: LLMConfig) -> Anthropic:
        """Load Anthropic LLM."""
        return Anthropic(
            model=config.model_name,
            anthropic_api_key=config.api_key,
            temperature=config.temperature,
            max_tokens_to_sample=config.max_tokens or 1000,
        )
    
    def generate(self, prompt: str) -> str:
        """Generate text using the current LLM."""
        if not self._current_model:
            raise ValueError("No LLM loaded. Call load_model() first.")
        
        if hasattr(self._current_model, 'invoke'):
            # For newer LangChain versions with chat models
            response = self._current_model.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        else:
            # For older LangChain versions or text completion models
            return self._current_model(prompt)
    
    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently loaded model."""
        if not self._current_config:
            return None
        
        return {
            "provider": self._current_config.provider,
            "model_name": self._current_config.model_name,
            "temperature": self._current_config.temperature,
            "max_tokens": self._current_config.max_tokens,
        }
    
    def list_available_providers(self) -> List[str]:
        """List available LLM providers."""
        return ["openai", "anthropic"]
    
    def get_recommended_models(self, provider: str) -> List[str]:
        """Get recommended models for a provider."""
        recommendations = {
            "openai": [
                "gpt-3.5-turbo",
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-4o-mini"
            ],
            "anthropic": [
                "claude-3-sonnet-20240229",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-instant-1.2"
            ]
        }
        return recommendations.get(provider.lower(), [])


# Global LLM manager instance
llm_manager = LLMManager()