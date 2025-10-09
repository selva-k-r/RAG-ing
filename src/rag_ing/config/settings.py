"""YAML-driven configuration management for Modular RAG PoC."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator
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
    
    @field_validator('sources', mode='before')
    @classmethod 
    def convert_legacy_format(cls, v, info):
        """Convert old single-source config to new multi-source format.
        
        Educational note: Pydantic validators ensure data consistency.
        This maintains backward compatibility while enabling new features.
        """
        # If sources is empty but we have legacy fields, convert them
        values = info.data if info.data else {}
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
    chunk_size: int = Field(default=1200, gt=0)  # Increased from 512
    overlap: int = Field(default=100, ge=0)  # Increased from 64
    prepend_metadata: bool = Field(default=True, description="Prepend document metadata to chunks")
    chunk_size_includes_metadata: bool = Field(default=False, description="Include metadata in chunk size calculation")
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
    
    @field_validator('azure_model')
    @classmethod
    def validate_azure_embedding_models(cls, v):
        """Validate that only standard Azure OpenAI embedding models are used."""
        standard_embedding_models = [
            'text-embedding-ada-002', 'text-embedding-3-large', 'text-embedding-3-small'
        ]
        if v not in standard_embedding_models:
            raise ValueError(f"Azure embedding model '{v}' is not standard. Supported: {standard_embedding_models}")
        return v
    
    @field_validator('name')
    @classmethod
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


class RerankingConfig(BaseModel):
    """Reranking configuration for cross-encoder models."""
    enabled: bool = Field(default=True, description="Enable cross-encoder reranking")
    model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", description="Cross-encoder model")
    top_k_initial: int = Field(default=20, description="Documents to retrieve before reranking")
    top_k_final: int = Field(default=5, description="Final documents after reranking")
    relevance_threshold: float = Field(default=0.7, description="Minimum relevance score")


class RetrievalConfig(BaseModel):
    """Enhanced query processing and retrieval configuration with hybrid search."""
    top_k: int = Field(default=10, gt=0)
    strategy: str = Field(default="hybrid", description="Strategy: similarity, keyword, or hybrid")
    
    # Hybrid search weights
    semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    
    # Reranking configuration
    reranking: RerankingConfig = Field(default_factory=RerankingConfig)
    
    # Context optimization
    max_context_tokens: int = Field(default=12000, description="Maximum context tokens")
    context_precision_threshold: float = Field(default=0.7, description="Context precision threshold")
    
    # Query enhancement
    query_enhancement: Dict[str, float] = Field(
        default={
            "question_keywords_boost": 2.0,
            "date_keywords_boost": 1.8,
            "direct_answer_boost": 2.5
        },
        description="Query enhancement multipliers"
    )
    
    # Domain-specific boosting
    domain_specific: Dict[str, Any] = Field(
        default={
            "medical_terms_boost": True,
            "ontology_codes_weight": 1.5
        },
        description="Domain-specific retrieval enhancements"
    )
    
    # Filtering options
    filters: Dict[str, Any] = Field(
        default={"ontology_match": True, "date_range": "last_12_months"},
        description="Retrieval filters"
    )
    
    @field_validator('keyword_weight')
    def validate_weights_sum(cls, v, info):
        """Ensure semantic and keyword weights sum to 1.0."""
        if info.data and 'semantic_weight' in info.data:
            semantic_weight = info.data['semantic_weight']
            if abs(semantic_weight + v - 1.0) > 0.01:  # Small tolerance for floating point
                raise ValueError(f"semantic_weight ({semantic_weight}) + keyword_weight ({v}) must sum to 1.0")
        return v


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


class RAGASMetricsConfig(BaseModel):
    """RAGAS-specific evaluation metrics configuration."""
    enabled: bool = Field(default=True, description="Enable RAGAS evaluation")
    
    # Core RAGAS metrics
    context_precision: bool = Field(default=True, description="Evaluate context precision")
    context_recall: bool = Field(default=True, description="Evaluate context recall")
    faithfulness: bool = Field(default=True, description="Evaluate response faithfulness")
    answer_relevancy: bool = Field(default=True, description="Evaluate answer relevancy")
    answer_similarity: bool = Field(default=True, description="Evaluate answer similarity")
    answer_correctness: bool = Field(default=True, description="Evaluate factual correctness")
    
    # Advanced RAGAS metrics
    context_entity_recall: bool = Field(default=False, description="Evaluate entity recall")
    noise_sensitivity: bool = Field(default=False, description="Evaluate noise sensitivity")
    
    # Thresholds for quality gates
    thresholds: Dict[str, float] = Field(
        default={
            "context_precision": 0.7,
            "context_recall": 0.7,
            "faithfulness": 0.8,
            "answer_relevancy": 0.75,
            "answer_similarity": 0.8,
            "answer_correctness": 0.7
        },
        description="Quality thresholds for each metric"
    )


class LoggingConfig(BaseModel):
    """Logging configuration for evaluation system."""
    enabled: bool = Field(default=True, description="Enable logging")
    format: str = Field(default="json", description="Log format: json or text")
    path: str = Field(default="./logs/", description="Log file directory")
    include_ragas_scores: bool = Field(default=True, description="Include RAGAS scores in logs")


class ContinuousEvaluationConfig(BaseModel):
    """Continuous evaluation framework configuration."""
    enabled: bool = Field(default=True, description="Enable continuous evaluation")
    
    # Evaluation frequency
    batch_size: int = Field(default=10, description="Queries per evaluation batch")
    evaluation_interval: int = Field(default=100, description="Queries between evaluations")
    
    # Performance monitoring
    performance_window: int = Field(default=1000, description="Queries in performance window")
    degradation_threshold: float = Field(default=0.1, description="Performance degradation threshold")
    
    # Alerting configuration
    alert_on_degradation: bool = Field(default=True, description="Send alerts on performance issues")
    alert_threshold_breaches: int = Field(default=3, description="Consecutive breaches before alert")
    
    # Data collection
    sample_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Fraction of queries to evaluate")
    store_raw_data: bool = Field(default=True, description="Store raw evaluation data")


class EvaluationConfig(BaseModel):
    """Comprehensive RAGAS metrics for RAG evaluation and continuous monitoring."""
    enabled: bool = Field(default=True, description="Enable evaluation system")
    
    # RAGAS integration
    ragas: RAGASMetricsConfig = Field(default_factory=RAGASMetricsConfig)
    
    # Continuous evaluation
    continuous: ContinuousEvaluationConfig = Field(default_factory=ContinuousEvaluationConfig)
    
    # Logging configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Traditional metrics (backward compatibility)
    metrics: List[str] = Field(
        default=[
            "response_time", "token_count", "cost_estimate",
            "retrieval_accuracy", "context_relevance", "safety_score"
        ],
        description="Traditional evaluation metrics"
    )
    
    # Legacy fields for backward compatibility
    log_level: str = Field(default="INFO", description="Evaluation logging level")
    export_interval: int = Field(default=24, description="Hours between metric exports")
    retention_days: int = Field(default=30, description="Days to retain evaluation data")
    
    # Quality gates
    quality_gates: Dict[str, Any] = Field(
        default={
            "min_safety_score": 0.8,
            "max_response_time": 5.0,
            "min_context_relevance": 0.7
        },
        description="Quality gates for system operation"
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
    
    # Azure OpenAI (LLM/GPT)
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: Optional[str] = Field(default="2024-12-01-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # Azure OpenAI (Embeddings) - Separate deployment
    azure_openai_embedding_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_EMBEDDING_API_KEY")
    azure_openai_embedding_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_EMBEDDING_ENDPOINT")
    azure_openai_embedding_api_version: Optional[str] = Field(default="2023-05-15", alias="AZURE_OPENAI_EMBEDDING_API_VERSION")
    
    # Other providers
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
            "azure_openai_embedding": self.azure_openai_embedding_api_key,
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