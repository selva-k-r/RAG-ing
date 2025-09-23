"""Configuration management for RAG-ing application."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import os


class SnowflakeConfig(BaseModel):
    """Snowflake connection configuration."""
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: Optional[str] = None


class EmbeddingModelConfig(BaseModel):
    """Embedding model configuration."""
    provider: str = Field(default="openai", description="Provider: openai, huggingface, etc.")
    model_name: str = Field(default="text-embedding-ada-002")
    api_key: Optional[str] = None
    dimensions: Optional[int] = None


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str = Field(default="openai", description="Provider: openai, anthropic, etc.")
    model_name: str = Field(default="gpt-3.5-turbo")
    api_key: Optional[str] = None
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: Optional[int] = None


class ConnectorConfig(BaseModel):
    """Document connector configuration."""
    confluence: Optional[Dict[str, str]] = None
    medium: Optional[Dict[str, str]] = None
    social_media: Optional[Dict[str, str]] = None


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)
    separators: List[str] = Field(default=["\n\n", "\n", " ", ""])


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application settings
    app_name: str = "RAG-ing"
    debug: bool = Field(default=False)
    
    # Database settings
    snowflake: Optional[SnowflakeConfig] = None
    
    # Model settings
    embedding_model: EmbeddingModelConfig = Field(default_factory=EmbeddingModelConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Connector settings
    connectors: ConnectorConfig = Field(default_factory=ConnectorConfig)
    
    # Chunking settings
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    
    # API Keys from environment
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    huggingface_api_key: Optional[str] = Field(default=None, alias="HUGGINGFACE_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_mapping = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "huggingface": self.huggingface_api_key,
        }
        return key_mapping.get(provider.lower())


# Global settings instance
settings = Settings()