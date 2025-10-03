"""YAML-driven configuration management for Modular RAG PoC."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path


class DataSourceConfig(BaseModel):
    """Extended data source configuration supporting multiple sources simultaneously.
    
    Educational note: This follows Python's composition pattern - building complex
    behavior by combining simple, reusable components.
    """
    
    # NEW: Support multiple data sources
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of data sources to process simultaneously"
    )
    
    # EXISTING: Keep for backward compatibility (Python best practice)
    type: Optional[str] = Field(default=None, description="Legacy: Type: confluence or local_file")
    path: Optional[str] = Field(default="./data/", description="Legacy: Path for local files")
    confluence: Optional[Dict[str, Any]] = Field(default=None, description="Legacy: Confluence configuration")
    
    @validator('sources', always=True)
    def convert_legacy_format(cls, v, values):
        """Convert old single-source config to new multi-source format.
        
        Educational note: Pydantic validators ensure data consistency.
        This maintains backward compatibility while enabling new features.
        """
        # If sources is empty but we have legacy fields, convert them
        if not v and values.get('type'):
            legacy_source = {
                'type': values.get('type'),
                'enabled': True,
                'description': f"Legacy {values.get('type')} source"
            }
            
            # Add type-specific configuration
            if values.get('type') == 'local_file':
                legacy_source['path'] = values.get('path', './data/')
                legacy_source['file_types'] = ['.txt', '.md', '.pdf', '.docx']
            elif values.get('type') == 'confluence':
                legacy_source['confluence'] = values.get('confluence', {})
            
            return [legacy_source]
        
        return v
    
    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        """Get only enabled data sources for processing.
        
        Educational note: This method encapsulates business logic,
        making the code easier to test and modify.
        """
        return [source for source in self.sources if source.get('enabled', True)]


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
    """Enhanced embedding model configuration with Azure and open source support."""
    # Provider selection
    provider: str = Field(default="huggingface", description="Provider: azure_openai or huggingface")
    use_azure_primary: bool = Field(default=False, description="Use Azure as primary, fallback to open source")
    
    # Azure OpenAI embedding configuration
    azure_model: str = Field(default="text-embedding-ada-002", description="Azure embedding model")
    azure_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    azure_api_key: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    azure_api_version: str = Field(default="2023-05-15", description="Azure API version")
    azure_deployment_name: str = Field(default="text-embedding-ada-002", description="Azure deployment name")
    
    # Open source model configuration (fallback)
    name: str = Field(default="all-MiniLM-L6-v2", description="Fallback model: all-MiniLM-L6-v2, all-mpnet-base-v2")
    device: str = Field(default="cpu", description="Device: cpu or cuda")
    model_path: Optional[str] = Field(default=None, description="Custom model path")
    
    @validator('azure_model')
    def validate_azure_embedding_models(cls, v):
        """Validate that only standard Azure OpenAI embedding models are used."""
        standard_embedding_models = [
            'text-embedding-ada-002', 'text-embedding-3-large', 'text-embedding-3-small'
        ]
        if v not in standard_embedding_models:
            raise ValueError(f"Azure embedding model '{v}' is not standard. Supported: {standard_embedding_models}")
        return v
    
    @validator('name')
    def validate_fallback_models(cls, v):
        """Validate fallback embedding models."""
        supported_models = [
            'all-MiniLM-L6-v2', 'all-mpnet-base-v2', 'sentence-transformers/all-MiniLM-L6-v2'
        ]
        if v not in supported_models:
            raise ValueError(f"Fallback model '{v}' not supported. Use: {supported_models}")
        return v
    
    def get_primary_provider(self) -> str:
        """Get the primary embedding provider to use."""
        if self.use_azure_primary and self.provider == "azure_openai":
            return "azure_openai"
        return "huggingface"
    
    def get_fallback_model(self) -> str:
        """Get fallback model name for open source embeddings."""
        return self.name


class RetrievalConfig(BaseModel):
    """Enhanced query processing and retrieval configuration."""
    top_k: int = Field(default=5, gt=0)
    strategy: str = Field(default="hybrid", description="Strategy: similarity, keyword, or hybrid")
    
    # Enhanced retrieval parameters
    use_reranking: bool = Field(default=True, description="Enable cross-encoder reranking")
    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # Hybrid search weights
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # Domain-specific boosting
    domain_boost: float = Field(default=1.2, description="Boost factor for domain-relevant results")
    medical_terms_boost: bool = Field(default=True, description="Boost medical terminology matches")
    ontology_codes_weight: float = Field(default=1.5, description="Weight for ICD-O, SNOMED-CT, MeSH codes")
    
    filters: Dict[str, Any] = Field(
        default={"ontology_match": True, "date_range": "last_12_months"},
        description="Retrieval filters"
    )


class LLMConfig(BaseModel):
    """LLM orchestration configuration."""
    model: str = Field(default="gpt-5-nano", description="Model name")
    provider: str = Field(default="azure_openai", description="Provider: azure_openai, openai, anthropic, koboldcpp")
    
    # Model configuration  
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    
    # Token management
    use_smart_truncation: bool = Field(default=True, description="Intelligent context truncation")
    context_optimization: bool = Field(default=True, description="Optimize context for model")
    token_buffer: int = Field(default=2000, description="Reserve tokens for response generation")
    
    # Provider-specific settings
    api_url: str = Field(default="http://localhost:5000/v1", description="API endpoint for local providers")
    azure_endpoint: Optional[str] = Field(default="${AZURE_OPENAI_ENDPOINT}", description="Azure OpenAI endpoint")
    azure_api_key: Optional[str] = Field(default="${AZURE_OPENAI_API_KEY}", description="Azure OpenAI API key")
    azure_api_version: str = Field(default="2024-02-15-preview", description="API version")
    azure_deployment_name: str = Field(default="gpt-5-nano", description="Azure deployment name")
    
    prompt_template: str = Field(default="./prompts/oncology.txt")
    system_instruction: str = Field(
        default="You are an AI-powered enterprise search assistant specializing in oncology, clinical documentation, and technical systems with enhanced RAG capabilities."
    )


class UIConfig(BaseModel):
    """Simplified UI layer configuration for FastAPI."""
    framework: str = Field(default="fastapi", description="UI framework")
    port: int = Field(default=8000, description="FastAPI server port")
    host: str = Field(default="0.0.0.0", description="FastAPI server host")
    debug: bool = Field(default=False, description="Debug mode")
    
    # UI Features
    show_source_metadata: bool = Field(default=True, description="Show document source metadata")
    enable_search_history: bool = Field(default=True, description="Enable search history")
    response_streaming: bool = Field(default=False, description="Stream responses to UI")
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


class TempFilesConfig(BaseModel):
    """Temporary files configuration."""
    directory: str = Field(default="./temp_helper_codes", description="Directory for temporary files")
    auto_cleanup: bool = Field(default=False, description="Automatically clean up temporary files")
    file_types: List[str] = Field(
        default=["*.py", "*.md", "*.txt", "*.html", "*.json", "*.yaml", "*.log"],
        description="File types to manage in temp directory"
    )




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
    temp_files: TempFilesConfig = Field(default_factory=TempFilesConfig)
    
    # Environment variables
    confluence_token: Optional[str] = Field(default=None, alias="CONFLUENCE_TOKEN")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: Optional[str] = Field(default="2024-12-01-preview", alias="AZURE_OPENAI_API_VERSION")
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
        config_dict = self.model_dump(exclude_unset=True)
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