"""Test enhanced settings configuration for hybrid retrieval and RAGAS evaluation."""

import pytest
import yaml
from pathlib import Path
from src.rag_ing.config.settings import Settings, RetrievalConfig, EvaluationConfig


def test_retrieval_config_defaults():
    """Test RetrievalConfig default values and validation."""
    config = RetrievalConfig()
    
    # Test default values
    assert config.top_k == 10
    assert config.strategy == "hybrid"
    assert config.semantic_weight == 0.6
    assert config.keyword_weight == 0.4
    
    # Test weights sum to 1.0
    assert abs(config.semantic_weight + config.keyword_weight - 1.0) < 0.01
    
    # Test reranking defaults
    assert config.reranking.enabled is True
    assert config.reranking.top_k_initial == 20
    assert config.reranking.top_k_final == 5


def test_retrieval_config_validation():
    """Test RetrievalConfig weight validation."""
    # Test valid weights
    config = RetrievalConfig(semantic_weight=0.7, keyword_weight=0.3)
    assert config.semantic_weight == 0.7
    assert config.keyword_weight == 0.3
    
    # Test invalid weights (should raise error)
    with pytest.raises(ValueError, match="must sum to 1.0"):
        RetrievalConfig(semantic_weight=0.8, keyword_weight=0.3)


def test_evaluation_config_defaults():
    """Test EvaluationConfig default values."""
    config = EvaluationConfig()
    
    # Test RAGAS configuration
    assert config.ragas.enabled is True
    assert config.ragas.context_precision is True
    assert config.ragas.faithfulness is True
    assert config.ragas.thresholds["faithfulness"] == 0.8
    
    # Test continuous evaluation
    assert config.continuous.enabled is True
    assert config.continuous.batch_size == 10
    assert config.continuous.sample_rate == 0.1
    
    # Test quality gates
    assert config.quality_gates["min_safety_score"] == 0.8


def test_settings_with_enhanced_config():
    """Test full Settings configuration with enhanced features."""
    # Create test YAML content
    test_config = {
        "embedding_model": {
            "azure_model": "text-embedding-ada-002",
            "azure_deployment_name": "text-embedding-ada-002"
        },
        "chunking": {
            "chunk_size": 1200,
            "overlap": 100,
            "prepend_metadata": True
        },
        "retrieval": {
            "top_k": 15,
            "strategy": "hybrid",
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "reranking": {
                "enabled": True,
                "top_k_initial": 25,
                "top_k_final": 8
            }
        },
        "evaluation": {
            "ragas": {
                "enabled": True,
                "faithfulness": True,
                "thresholds": {
                    "faithfulness": 0.85
                }
            },
            "continuous": {
                "batch_size": 20,
                "sample_rate": 0.2
            }
        }
    }
    
    # Write test config to temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_path = f.name
    
    try:
        # Load settings from test config
        settings = Settings.from_yaml(temp_path)
        
        # Validate enhanced configurations
        assert settings.embedding_model.azure_model == "text-embedding-ada-002"
        assert settings.chunking.chunk_size == 1200
        assert settings.chunking.prepend_metadata is True
        
        assert settings.retrieval.top_k == 15
        assert settings.retrieval.semantic_weight == 0.7
        assert settings.retrieval.reranking.top_k_initial == 25
        
        assert settings.evaluation.ragas.enabled is True
        assert settings.evaluation.ragas.thresholds["faithfulness"] == 0.85
        assert settings.evaluation.continuous.batch_size == 20
        
    finally:
        # Clean up temporary file
        import os
        os.unlink(temp_path)


def test_backward_compatibility():
    """Test that existing configurations still work."""
    # Test minimal config (should use defaults)
    minimal_config = {}
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(minimal_config, f)
        temp_path = f.name
    
    try:
        settings = Settings.from_yaml(temp_path)
        
        # Should use all defaults
        assert settings.retrieval.strategy == "hybrid"
        assert settings.evaluation.ragas.enabled is True
        assert settings.chunking.chunk_size == 1200  # New default
        
    finally:
        import os
        os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])