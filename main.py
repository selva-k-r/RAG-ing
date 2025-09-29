#!/usr/bin/env python3
"""Main entry point for RAG-ing Modular PoC application.

This application implements a 5-module oncology-focused RAG system as specified in Requirement.md:
- Module 1: Corpus & Embedding Lifecycle 
- Module 2: Query Processing & Retrieval
- Module 3: LLM Orchestration  
- Module 4: UI Layer
- Module 5: Evaluation & Logging
"""

import sys
import os
import argparse
import logging
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_configuration(config_path: str) -> Settings:
    """Load and validate configuration."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("💡 Please ensure config.yaml exists or provide a valid path with --config")
        sys.exit(1)
    
    try:
        settings = Settings.from_yaml(config_path)
        print(f"✅ Configuration loaded from: {config_path}")
        return settings
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG-ing: Modular RAG PoC with 5 core modules for oncology domain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔬 Modular Architecture:
  Module 1: Corpus & Embedding Lifecycle - Document ingestion with PubMedBERT
  Module 2: Query Processing & Retrieval - Semantic search with domain filtering  
  Module 3: LLM Orchestration - KoboldCpp integration with medical prompts
  Module 4: UI Layer - Clinical/Technical audience toggle with feedback
  Module 5: Evaluation & Logging - Performance tracking and safety monitoring

📋 Examples:
  python main.py --ui                    # Launch Streamlit interface
  python main.py --ingest               # Process corpus and build vector store
  python main.py --query "cancer treatment options"  # Single query via CLI
  python main.py --status               # Show system status and metrics
  python main.py --config custom.yaml   # Use custom configuration file
  python main.py --export-metrics       # Export session metrics to JSON
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='./config.yaml',
        help='Path to YAML configuration file (default: ./config.yaml)'
    )
    
    parser.add_argument(
        '--ui',
        action='store_true',
        help='Launch Streamlit UI application'
    )
    
    parser.add_argument(
        '--ingest',
        action='store_true', 
        help='Run corpus ingestion and embedding generation'
    )
    
    parser.add_argument(
        '--query',
        type=str,
        help='Execute a single query via CLI'
    )
    
    parser.add_argument(
        '--audience',
        choices=['clinical', 'technical'],
        default='clinical',
        help='Target audience for queries (default: clinical)'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status and performance metrics'
    )
    
    parser.add_argument(
        '--export-metrics',
        action='store_true',
        help='Export session metrics to JSON file'
    )
    
    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Perform health check on all modules'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    print("� RAG-ing Modular PoC - Oncology-Focused RAG System")
    print("=" * 60)
    print(f"📁 Configuration: {args.config}")
    print(f"🐛 Debug Mode: {args.debug}")
    
    # Load configuration and initialize orchestrator
    try:
        settings = load_configuration(args.config)
        print(f"🏗️  Initializing RAG Orchestrator with 5 modules...")
        
        orchestrator = RAGOrchestrator(args.config)
        print("✅ RAG Orchestrator initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Execute requested action
    try:
        if args.ingest:
            print("\n📚 Starting corpus ingestion...")
            results = orchestrator.ingest_corpus()
            print("✅ Corpus ingestion completed successfully")
            print(f"📊 Processing time: {results['processing_time']:.2f}s")
            if 'statistics' in results:
                stats = results['statistics']
                print(f"📄 Documents processed: {stats.get('documents_processed', 'N/A')}")
                print(f"🧩 Chunks created: {stats.get('chunks_created', 'N/A')}")
                print(f"🔢 Embeddings generated: {stats.get('embeddings_generated', 'N/A')}")
        
        elif args.query:
            print(f"\n🔍 Processing query for {args.audience} audience...")
            print(f"❓ Query: {args.query}")
            
            result = orchestrator.query_documents(
                query=args.query,
                audience=args.audience
            )
            
            print("✅ Query processed successfully")
            print(f"⏱️  Total time: {result['metadata']['total_time']:.2f}s")
            print(f"📋 Sources found: {result['metadata']['num_sources']}")
            print(f"🤖 Model used: {result['metadata']['model_used']}")
            print(f"🛡️  Safety score: {result['metadata']['safety_score']:.2f}")
            print("\n📝 Response:")
            print("-" * 40)
            print(result['response'])
            print("-" * 40)
            
            if result['sources']:
                print(f"\n📚 Sources ({len(result['sources'])}):")
                for i, source in enumerate(result['sources'][:3], 1):  # Show first 3 sources
                    print(f"  {i}. {source.get('source', 'Unknown source')}")
                    if len(result['sources']) > 3:
                        print(f"  ... and {len(result['sources']) - 3} more sources")
        
        elif args.status:
            print("\n📊 System Status:")
            status = orchestrator.get_system_status()
            
            # System overview
            system_info = status['system']
            print(f"🟢 Status: {system_info['status']}")
            print(f"⏰ Uptime: {system_info['uptime_formatted']}")
            print(f"🏗️  Modules: {system_info['modules_initialized']}/5")
            
            # Performance metrics
            if 'performance' in status:
                perf = status['performance']
                print(f"\n📈 Performance Metrics:")
                print(f"  Total queries: {perf.get('system_metrics', {}).get('total_queries', 0)}")
                print(f"  Success rate: {100 * (1 - perf.get('system_metrics', {}).get('error_rate', 0)):.1f}%")
                print(f"  Avg response time: {perf.get('avg_end_to_end_time', 0):.2f}s")
                
        elif args.export_metrics:
            print("\n📤 Exporting session metrics...")
            metrics = orchestrator.export_session_data()
            
            output_file = f"metrics_{int(time.time())}.json"
            with open(output_file, 'w') as f:
                f.write(metrics)
            
            print(f"✅ Metrics exported to: {output_file}")
            
        elif args.health_check:
            print("\n🏥 Performing health check...")
            health = orchestrator.health_check()
            
            print(f"Overall Status: {health['overall'].upper()}")
            print(f"Timestamp: {health['timestamp']}")
            print("\nModule Status:")
            for module, status in health['modules'].items():
                status_icon = "🟢" if status['status'] == 'healthy' else "🔴"
                print(f"  {status_icon} {module}: {status['status']}")
                if 'error' in status:
                    print(f"    ❌ {status['error']}")
        
        elif args.ui:
            print("\n🚀 Launching UI Layer (Module 4)...")
            print("🌐 Streamlit interface will open in your browser")
            print("🛑 Press Ctrl+C to stop the application")
            orchestrator.run_ui()
            
        else:
            print("\n❓ No action specified. Use --help for available options.")
            print("\n💡 Quick start:")
            print("  python main.py --ingest    # First, ingest your corpus")
            print("  python main.py --ui        # Then, launch the UI")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Application interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        print("\n👋 Thank you for using RAG-ing Modular PoC!")

if __name__ == "__main__":
    main()