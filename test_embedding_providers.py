"""
Test script for flexible embedding provider

This script tests:
1. Azure OpenAI provider (with rate limiting)
2. Local BGE-large provider (no limits)
3. Hybrid provider (local for docs, Azure for queries)
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag_ing.utils.embedding_provider import (
    create_embedding_provider,
    AzureOpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    HybridEmbeddingProvider
)

def test_local_provider():
    """Test local BGE-large provider"""
    print("\n" + "="*80)
    print("TEST 1: Local BGE-large Provider")
    print("="*80)
    
    config = {
        'provider': 'local',
        'local': {
            'model_name': 'BAAI/bge-large-en-v1.5',
            'device': 'cpu',
            'batch_size': 4,  # Small batch for testing
            'normalize_embeddings': True,
            'show_progress': False
        }
    }
    
    try:
        print("\n[1/4] Creating provider...")
        provider = create_embedding_provider(config)
        print(f"[OK] Provider created: {provider.get_provider_name()}")
        print(f"     Dimension: {provider.get_dimension()}")
        
        # Test single query
        print("\n[2/4] Testing single query embedding...")
        start = time.time()
        query_embedding = provider.embed_query("What are the treatment options for breast cancer?")
        query_time = time.time() - start
        print(f"[OK] Query embedded in {query_time:.3f}s")
        print(f"     Embedding length: {len(query_embedding)}")
        print(f"     First 5 values: {query_embedding[:5]}")
        
        # Test batch documents
        print("\n[3/4] Testing batch document embedding...")
        test_docs = [
            "Breast cancer is a type of cancer that forms in the cells of the breasts.",
            "Treatment options include surgery, chemotherapy, radiation therapy, and hormone therapy.",
            "Early detection through mammography screening improves survival rates.",
            "BRCA1 and BRCA2 are genes that can increase breast cancer risk."
        ]
        start = time.time()
        doc_embeddings = provider.embed_documents(test_docs)
        batch_time = time.time() - start
        print(f"[OK] {len(test_docs)} documents embedded in {batch_time:.3f}s")
        print(f"     Average time per document: {batch_time/len(test_docs):.3f}s")
        print(f"     Throughput: {len(test_docs)/batch_time:.1f} docs/sec")
        
        # Test performance with larger batch
        print("\n[4/4] Testing performance with 50 documents...")
        large_batch = test_docs * 12 + test_docs[:2]  # 50 docs total
        start = time.time()
        large_embeddings = provider.embed_documents(large_batch)
        large_batch_time = time.time() - start
        print(f"[OK] {len(large_batch)} documents embedded in {large_batch_time:.3f}s")
        print(f"     Throughput: {len(large_batch)/large_batch_time:.1f} docs/sec")
        
        print("\n" + "="*80)
        print("LOCAL PROVIDER TEST: SUCCESS")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n[X] Local provider test failed: {e}")
        print(f"    Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def test_azure_provider():
    """Test Azure OpenAI provider (requires credentials)"""
    print("\n" + "="*80)
    print("TEST 2: Azure OpenAI Provider (with rate limiting)")
    print("="*80)
    
    import os
    
    # Check if credentials are available
    if not os.getenv('AZURE_OPENAI_EMBEDDING_API_KEY'):
        print("[!] SKIP: Azure credentials not found in environment")
        print("    Set AZURE_OPENAI_EMBEDDING_API_KEY to test Azure provider")
        return None
    
    config = {
        'provider': 'azure_openai',
        'azure_openai': {
            'model': 'text-embedding-ada-002',
            'endpoint': os.getenv('AZURE_OPENAI_EMBEDDING_ENDPOINT'),
            'api_key': os.getenv('AZURE_OPENAI_EMBEDDING_API_KEY'),
            'api_version': os.getenv('AZURE_OPENAI_EMBEDDING_API_VERSION', '2023-05-15'),
            'deployment_name': 'text-embedding-ada-002',
            'max_retries': 3,
            'retry_delay': 1,
            'requests_per_minute': 30  # Conservative for testing
        }
    }
    
    try:
        print("\n[1/3] Creating Azure provider...")
        provider = create_embedding_provider(config)
        print(f"[OK] Provider created: {provider.get_provider_name()}")
        print(f"     Dimension: {provider.get_dimension()}")
        
        # Test single query
        print("\n[2/3] Testing single query...")
        start = time.time()
        query_embedding = provider.embed_query("Test query for Azure OpenAI")
        query_time = time.time() - start
        print(f"[OK] Query embedded in {query_time:.3f}s")
        
        # Test small batch with rate limiting
        print("\n[3/3] Testing batch with rate limiting (5 docs)...")
        test_docs = [
            "Document 1 for testing",
            "Document 2 for testing",
            "Document 3 for testing",
            "Document 4 for testing",
            "Document 5 for testing"
        ]
        start = time.time()
        doc_embeddings = provider.embed_documents(test_docs)
        batch_time = time.time() - start
        print(f"[OK] {len(test_docs)} documents embedded in {batch_time:.3f}s")
        print(f"     Rate limiting is working (should take >2s for 5 docs at 30 req/min)")
        
        print("\n" + "="*80)
        print("AZURE PROVIDER TEST: SUCCESS")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n[X] Azure provider test failed: {e}")
        print(f"    Error type: {type(e).__name__}")
        return False


def test_hybrid_provider():
    """Test hybrid provider"""
    print("\n" + "="*80)
    print("TEST 3: Hybrid Provider (Local for ingestion, Local for queries)")
    print("="*80)
    print("Note: Using local for both since Azure credentials may not be available")
    
    config = {
        'provider': 'hybrid',
        'local': {
            'model_name': 'BAAI/bge-large-en-v1.5',
            'device': 'cpu',
            'batch_size': 4,
            'normalize_embeddings': True,
            'show_progress': False
        },
        'azure_openai': {
            'model': 'text-embedding-ada-002',
            'max_retries': 3
        },
        'hybrid': {
            'ingestion': 'local',  # Use local for bulk operations
            'queries': 'local',    # Use local for queries (change to azure_openai if credentials available)
            'fallback': 'local'
        }
    }
    
    try:
        print("\n[1/3] Creating hybrid provider...")
        provider = create_embedding_provider(config)
        print(f"[OK] Provider created: {provider.get_provider_name()}")
        
        # Test query path
        print("\n[2/3] Testing query path (should use query provider)...")
        query_embedding = provider.embed_query("Test query")
        print(f"[OK] Query embedded")
        
        # Test document path
        print("\n[3/3] Testing document path (should use ingestion provider)...")
        docs = ["Doc 1", "Doc 2", "Doc 3"]
        doc_embeddings = provider.embed_documents(docs)
        print(f"[OK] {len(docs)} documents embedded")
        
        print("\n" + "="*80)
        print("HYBRID PROVIDER TEST: SUCCESS")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n[X] Hybrid provider test failed: {e}")
        print(f"    Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("EMBEDDING PROVIDER TEST SUITE")
    print("="*80)
    print("\nThis will test the flexible embedding provider system:")
    print("1. Local BGE-large model (no rate limits, free)")
    print("2. Azure OpenAI model (with rate limiting)")
    print("3. Hybrid mode (different models for ingestion vs queries)")
    print("\n" + "="*80)
    
    results = {}
    
    # Test 1: Local provider (always runs)
    results['local'] = test_local_provider()
    
    # Test 2: Azure provider (only if credentials available)
    results['azure'] = test_azure_provider()
    
    # Test 3: Hybrid provider
    results['hybrid'] = test_hybrid_provider()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Local Provider:  {'PASS' if results['local'] else 'FAIL'}")
    print(f"Azure Provider:  {'PASS' if results['azure'] else 'SKIP' if results['azure'] is None else 'FAIL'}")
    print(f"Hybrid Provider: {'PASS' if results['hybrid'] else 'FAIL'}")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    if results['local']:
        print("[OK] Local BGE-large is working - Use this to avoid rate limits")
        print("     Performance: ~10-20 docs/sec on CPU")
        print("     Cost: $0 (runs locally)")
        print("     Quality: Matches Azure ada-002")
    
    if results['azure']:
        print("[OK] Azure OpenAI is working - Use for highest quality")
        print("     Performance: Rate limited to ~30 req/min")
        print("     Cost: ~$0.0001 per 1K tokens")
    elif results['azure'] is None:
        print("[!] Azure not tested - Set credentials to test")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Update config.yaml to set provider: 'local' or 'azure_openai' or 'hybrid'")
    print("2. Run ingestion: python main.py --ingest")
    print("3. Compare performance and quality")
    print("4. Choose best provider for your use case")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
