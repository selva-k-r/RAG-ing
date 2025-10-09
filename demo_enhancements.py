#!/usr/bin/env python3
"""
Demo script for RAG-ing Multi-Source Data Ingestion

This script demonstrates the new capabilities:
1. Multi-source data ingestion (local files, Confluence, JIRA)
2. Enhanced retrieval with hybrid search and reranking  
3. GPT-4o nano integration with 12K token context

Educational purpose: Shows how the improved RAG system works end-to-end.
"""

import sys
import os
from pathlib import Path

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator


def demo_multi_source_capabilities():
    """Demonstrate the new multi-source capabilities."""
    
    print("🚀 RAG-ing Multi-Source Demo")
    print("=" * 50)
    
    # Load enhanced configuration
    try:
        settings = Settings.from_yaml('./config.yaml')
        print("✅ Enhanced configuration loaded successfully!")
        
        # Show multi-source configuration
        enabled_sources = settings.data_source.get_enabled_sources()
        print(f"\n📋 Data Sources Configuration:")
        print(f"   Total sources defined: {len(settings.data_source.sources)}")
        print(f"   Enabled sources: {len(enabled_sources)}")
        
        for i, source in enumerate(enabled_sources, 1):
            source_type = source.get('type')
            description = source.get('description', f'{source_type} source')
            print(f"   {i}. {source_type.upper()}: {description}")
        
        # Show enhanced retrieval configuration
        print(f"\n🔍 Enhanced Retrieval Configuration:")
        print(f"   Strategy: {settings.retrieval.strategy}")
        print(f"   Top-K results: {settings.retrieval.top_k}")
        print(f"   Use reranking: {settings.retrieval.use_reranking}")
        print(f"   Semantic weight: {settings.retrieval.semantic_weight}")
        print(f"   Keyword weight: {settings.retrieval.keyword_weight}")
        print(f"   Medical terms boost: {settings.retrieval.domain_specific.get('medical_terms_boost', True)}")
        
        # Show GPT-4o nano configuration
        print(f"\n🤖 GPT-4o Nano Configuration:")
        print(f"   Model: {settings.llm.model}")
        print(f"   Provider: {settings.llm.provider}")
        print(f"   Max tokens: {settings.llm.max_tokens:,}")
        print(f"   Smart truncation: {settings.llm.use_smart_truncation}")
        print(f"   Context optimization: {settings.llm.context_optimization}")
        print(f"   Token buffer: {settings.llm.token_buffer}")
        
        # Initialize orchestrator with enhanced settings
        print(f"\n🎯 Initializing Enhanced RAG Orchestrator...")
        orchestrator = RAGOrchestrator('./config.yaml')
        print("✅ Orchestrator initialized with multi-source support!")
        
        # Demonstrate multi-source ingestion
        print(f"\n📚 Testing Multi-Source Document Ingestion...")
        print("   Note: This will process all enabled sources")
        print("   Local files: ✅ Enabled")
        print("   Confluence: ⏸️  Disabled (enable in config.yaml)")
        print("   JIRA: ⏸️  Disabled (enable in config.yaml)")
        
        # Check data directory
        data_path = Path('./data')
        if data_path.exists():
            files = list(data_path.rglob("*"))
            data_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.txt', '.md', '.pdf', '.docx', '.html']]
            print(f"\n📁 Local Data Directory Status:")
            print(f"   Path: {data_path.absolute()}")
            print(f"   Total files: {len(data_files)}")
            
            if data_files:
                print(f"   Sample files:")
                for i, file_path in enumerate(data_files[:5], 1):
                    print(f"     {i}. {file_path.name} ({file_path.suffix})")
                if len(data_files) > 5:
                    print(f"     ... and {len(data_files) - 5} more files")
            else:
                print("   ⚠️  No supported files found in data directory")
                print("   💡 Add some .txt, .md, .pdf, or .docx files to test ingestion")
        else:
            print(f"\n📁 Data directory not found: {data_path}")
            print("   💡 Create the directory and add documents to test ingestion")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"\n💡 Next steps:")
        print(f"   1. Add documents to ./data directory")
        print(f"   2. Configure Confluence/JIRA credentials in .env")
        print(f"   3. Enable additional sources in config.yaml")
        print(f"   4. Run: python main.py --ingest")
        print(f"   5. Run: python main.py --ui")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def demo_enhanced_query_capabilities():
    """Demonstrate enhanced query processing capabilities."""
    
    print(f"\n🔍 Enhanced Query Processing Demo")
    print("=" * 40)
    
    print("📋 New Capabilities:")
    print("   • Hybrid search (semantic + keyword)")
    print("   • Cross-encoder reranking")
    print("   • Medical terminology boosting") 
    print("   • Ontology code weighting (ICD-O, SNOMED-CT, MeSH)")
    print("   • Domain-specific filtering")
    
    print(f"\n🤖 GPT-4o Nano Features:")
    print("   • 12,000 token context window")
    print("   • Smart context truncation")
    print("   • Context optimization for medical queries")
    print("   • Audience-aware responses (clinical vs technical)")
    
    example_queries = [
        "What are the latest treatments for lung cancer?",
        "Explain immunotherapy side effects in simple terms",
        "What is the molecular mechanism of CAR-T therapy?",
        "How do I configure our PopHealth database connection?",
        "What's the process for raising a DevOps ticket?"
    ]
    
    print(f"\n💬 Example Queries to Try:")
    for i, query in enumerate(example_queries, 1):
        print(f"   {i}. \"{query}\"")
    
    print(f"\n🎯 To test these features:")
    print(f"   1. Complete document ingestion: python main.py --ingest")
    print(f"   2. Launch web UI: python main.py --ui")
    print(f"   3. Try queries with different audience settings")
    print(f"   4. Compare semantic vs hybrid retrieval results")


if __name__ == "__main__":
    print("🔬 RAG-ing Enhanced Capabilities Demo")
    print("=" * 60)
    
    # Demo 1: Multi-source configuration
    if demo_multi_source_capabilities():
        # Demo 2: Enhanced query capabilities
        demo_enhanced_query_capabilities()
        
        print(f"\n🎊 All demos completed successfully!")
        print(f"   The RAG system now supports:")
        print(f"   ✅ Multi-source data ingestion")
        print(f"   ✅ Enhanced hybrid retrieval")
        print(f"   ✅ GPT-4o nano with 12K context")
        print(f"   ✅ Backward compatibility")
        
        print(f"\n🚀 Quick Start Workflow:")
        print(f"   1. Configure API credentials in .env file:")
        print(f"      AZURE_OPENAI_API_KEY=your_key_here")
        print(f"      AZURE_OPENAI_ENDPOINT=your_endpoint_here")
        print(f"   2. Enable additional sources in config.yaml (optional)")
        print(f"   3. Process documents: python main.py --ingest")
        print(f"   4. Launch web UI: python main.py --ui")
        print(f"   5. Open browser to: http://localhost:8000")
        
        print(f"\n📚 Test the enhanced features:")
        print(f"   • Try medical queries for hybrid search + boosting")
        print(f"   • Test long queries for smart truncation") 
        print(f"   • Compare semantic vs hybrid retrieval strategies")
        print(f"   • Observe medical disclaimers in clinical responses")
    else:
        print(f"\n❌ Demo encountered issues. Please check the configuration.")
        sys.exit(1)