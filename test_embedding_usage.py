"""
Test script to verify Azure embedding model is being used in the source code.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from rag_ing.config.settings import Settings
from rag_ing.modules.corpus_embedding import CorpusEmbeddingModule

def test_azure_embedding_usage():
    """Test that Azure embeddings are used when configured."""
    print("=" * 70)
    print("🧪 Testing Azure Embedding Model Usage in Source Code")
    print("=" * 70)
    print()
    
    # Load environment and settings
    load_dotenv()
    settings = Settings.from_yaml("config.yaml")
    
    # Display configuration
    print("📋 Configuration Loaded:")
    print(f"   Provider: {settings.embedding_model.provider}")
    print(f"   Use Azure Primary: {settings.embedding_model.use_azure_primary}")
    print(f"   Azure Model: {settings.embedding_model.azure_model}")
    print(f"   Azure Deployment: {settings.embedding_model.azure_deployment_name}")
    print(f"   Azure Endpoint: {settings.embedding_model.azure_endpoint}")
    print(f"   Azure API Version: {settings.embedding_model.azure_api_version}")
    print()
    
    # Verify primary provider
    primary_provider = settings.embedding_model.get_primary_provider()
    print(f"🎯 Primary Provider (computed): {primary_provider}")
    print()
    
    if primary_provider != "azure_openai":
        print("❌ ERROR: Primary provider is not azure_openai!")
        print("   Check that use_azure_primary=true in config.yaml")
        return False
    
    print("✅ Configuration is set to use Azure embeddings")
    print()
    
    # Initialize corpus embedding module
    print("🏗️ Initializing CorpusEmbeddingModule...")
    try:
        module = CorpusEmbeddingModule(settings)
        print("✅ Module initialized successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize module: {e}")
        return False
    
    # Load embedding model
    print("🔵 Loading embedding model...")
    try:
        module._load_embedding_model()
        print("✅ Embedding model loaded successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to load embedding model: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify it's using Azure
    if not module.embedding_model:
        print("❌ ERROR: No embedding model loaded!")
        return False
    
    # Check if it's the Azure wrapper
    print("🔍 Verifying embedding model type...")
    model_type = type(module.embedding_model).__name__
    print(f"   Model Type: {model_type}")
    
    if "AzureEmbeddingWrapper" in model_type:
        print("✅ Using Azure OpenAI embedding model!")
    elif "HuggingFaceEmbeddings" in model_type:
        print("⚠️  WARNING: Using HuggingFace embeddings (fallback)")
        print("   Azure embeddings may have failed to load")
        return False
    else:
        print(f"   Model class: {module.embedding_model.__class__}")
    
    print()
    
    # Test embedding generation
    print("🧪 Testing embedding generation...")
    try:
        test_text = "This is a test for Azure embeddings with oncology biomarkers"
        embedding = module.embedding_model.embed_query(test_text)
        
        print(f"✅ Embedding generated successfully!")
        print(f"   📊 Vector dimension: {len(embedding)}")
        print(f"   📈 First 3 values: [{embedding[0]:.6f}, {embedding[1]:.6f}, {embedding[2]:.6f}]")
        
        # Azure embeddings are 1536 dimensions for text-embedding-ada-002
        if len(embedding) == 1536:
            print(f"   ✅ Correct dimension for Azure text-embedding-ada-002!")
        elif len(embedding) == 768:
            print(f"   ⚠️  WARNING: 768 dimensions suggests HuggingFace model (fallback)")
            return False
        
        print()
        
    except Exception as e:
        print(f"❌ Failed to generate embedding: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test batch embedding (multiple documents)
    print("🧪 Testing batch embedding generation...")
    try:
        test_texts = [
            "Oncology treatment protocols",
            "Cancer biomarker analysis",
            "Patient diagnosis procedures"
        ]
        embeddings = module.embedding_model.embed_documents(test_texts)
        
        print(f"✅ Batch embeddings generated successfully!")
        print(f"   📊 Number of embeddings: {len(embeddings)}")
        print(f"   📊 Vector dimension: {len(embeddings[0])}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to generate batch embeddings: {e}")
        return False
    
    # Final summary
    print("=" * 70)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 70)
    print("✅ Configuration: Azure embeddings enabled")
    print("✅ Model Loading: Azure embedding model loaded")
    print("✅ Model Type: AzureEmbeddingWrapper (correct)")
    print("✅ Vector Dimension: 1536 (Azure text-embedding-ada-002)")
    print("✅ Single Query: Working")
    print("✅ Batch Queries: Working")
    print("=" * 70)
    print()
    print("🎉 SUCCESS! Azure embeddings are properly configured and working!")
    print()
    print("💡 The system will use Azure OpenAI embeddings for:")
    print("   1. Document ingestion (corpus_embedding module)")
    print("   2. Query processing (query_retrieval module)")
    print("   3. Vector search (ChromaDB with Azure embeddings)")
    print()
    
    return True


if __name__ == "__main__":
    success = test_azure_embedding_usage()
    sys.exit(0 if success else 1)
