"""YAML-driven configuration management for Modular RAG PoC."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path


class DataSourceConfig(BaseModel):
    """Data source configuration for corpus ingestion."""
    type: str = Field(..., description="Type: confluence or local_file")
    path: Optional[str] = Field(default="./data/", description="Path for local files")
    confluence: Optional[Dict[str, Any]] = Field(default=None, description="Confluence configuration")


class ChunkingConfig(BaseModel):
    """Text chunking configuration."""
    strategy: str = Field(default="recursive", description="Strategy: recursive or semantic")
    chunk_size: int = Field(default=512, gt=0)
    overlap: int = Field(default=64, ge=0)
    semantic_boundaries: List[str] = Field(
        default=["## Diagnosis", "## Treatment", "## Biomarkers", "## Prognosis"],
        description="Semantic boundaries for oncology content"
    )


class EmbeddingModelConfig(BaseModel):
    """Embedding model configuration."""
    name: str = Field(default="pubmedbert", description="Model name: pubmedbert, clinicalbert, etc.")
    device: str = Field(default="cpu", description="Device: cpu or cuda")
    provider: Optional[str] = Field(default="huggingface", description="Provider")
    model_path: Optional[str] = Field(default=None, description="Custom model path")


class RetrievalConfig(BaseModel):
    """Query processing and retrieval configuration."""
    top_k: int = Field(default=5, gt=0)
    strategy: str = Field(default="similarity", description="Strategy: similarity or hybrid")
    filters: Dict[str, Any] = Field(
        default={"ontology_match": True, "date_range": "last_12_months"},
        description="Retrieval filters"
    )


class LLMConfig(BaseModel):
    """LLM orchestration configuration."""
    model: str = Field(default="biomistral", description="Model name")
    provider: str = Field(default="koboldcpp", description="Provider: koboldcpp, openai, azure_openai, anthropic")
    api_url: str = Field(default="http://localhost:5000/v1", description="API endpoint")
    prompt_template: str = Field(default="./prompts/oncology.txt", description="Prompt template path")
    system_instruction: str = Field(
        default="You are a biomedical assistant specializing in oncology. Provide evidence-based responses with proper citations.",
        description="System instruction"
    )
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=512)


class UIConfig(BaseModel):
    """UI layer configuration."""
    framework: str = Field(default="streamlit", description="UI framework")
    audience_toggle: bool = Field(default=True, description="Enable clinical vs technical toggle")
    feedback_enabled: bool = Field(default=True, description="Enable feedback collection")
    show_chunk_metadata: bool = Field(default=True, description="Show chunk metadata")
    default_model: str = Field(default="biomistral")
    default_source: str = Field(default="confluence")


class EvaluationConfig(BaseModel):
    """Evaluation and logging configuration."""
    metrics: Dict[str, bool] = Field(
        default={
            "precision_at_k": True,
            "citation_coverage": True,
            "clarity_rating": True,
            "latency": True,
            "safety": True
        },
        description="Enabled metrics"
    )
    logging: Dict[str, Any] = Field(
        default={"enabled": True, "format": "json", "path": "./logs/"},
        description="Logging configuration"
    )


class VectorStoreConfig(BaseModel):
    """Vector storage configuration."""
    type: str = Field(default="chroma", description="Type: chroma, faiss, or snowflake")
    path: str = Field(default="./vector_store", description="Storage path")
    collection_name: str = Field(default="oncology_docs", description="Collection name")




class Settings(BaseSettings):
    """Main YAML-driven application settings for Modular RAG PoC."""
    
    # Module configurations
    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding_model: EmbeddingModelConfig = Field(default_factory=EmbeddingModelConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    
    # Environment variables
    confluence_token: Optional[str] = Field(default=None, alias="CONFLUENCE_TOKEN")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: Optional[str] = Field(default="2024-02-01", alias="AZURE_OPENAI_API_VERSION")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    huggingface_api_key: Optional[str] = Field(default=None, alias="HUGGINGFACE_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of forbidding them
    
    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Settings":
        """Load configuration from YAML file."""
        if not Path(config_path).exists():
            # Return default settings if no config file
            return cls()
            
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Replace environment variable placeholders
        config_data = cls._replace_env_vars(config_data)
        
        return cls(**config_data)
    
    @staticmethod
    def _replace_env_vars(data: Any) -> Any:
        """Replace ${VAR} placeholders with environment variables."""
        if isinstance(data, dict):
            return {k: Settings._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Settings._replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            return os.getenv(var_name, data)
        return data
    
    def to_yaml(self, config_path: str = "config.yaml") -> None:
        """Save configuration to YAML file."""
        config_dict = self.dict(exclude_unset=True)
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_mapping = {
            "openai": self.openai_api_key,
            "azure_openai": self.azure_openai_api_key,
            "anthropic": self.anthropic_api_key,
            "huggingface": self.huggingface_api_key,
        }
        return key_mapping.get(provider.lower())


# Global settings instance - will be initialized on first use
settings = None

def get_settings(config_path: str = "config.yaml") -> "Settings":
    """Get global settings instance, creating it if necessary."""
    global settings
    if settings is None:
        settings = Settings.from_yaml(config_path)
    return settings