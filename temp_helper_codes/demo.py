#!/usr/bin/env python3
"""
Demo script to showcase RAG-ing project structure and features.
This script works without external dependencies.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def print_separator(title=""):
    """Print a visual separator."""
    print("=" * 60)
    if title:
        print(f" {title} ".center(60, "="))
        print("=" * 60)
    print()

def show_project_structure():
    """Display the project structure."""
    print_separator("RAG-ing Project Structure")
    
    structure = {
        "📦 RAG-ing/": {
            "🔧 src/rag_ing/": {
                "⚙️ config/": ["Settings management", "Model configurations"],
                "🔗 connectors/": ["Confluence", "Medium", "Twitter", "Reddit"],
                "🤖 models/": ["Embedding manager", "LLM manager"],
                "🗄️ storage/": ["Vector stores", "Snowflake integration"],
                "🎨 ui/": ["FastAPI web interface"],
                "✂️ chunking.py": ["Text chunking service"]
            },
            "🧪 tests/": ["Unit tests", "Integration tests"],
            "📄 Configuration": ["pyproject.toml", ".env.example", "README.md"]
        }
    }
    
    def print_structure(items, indent=0):
        """Recursively print structure."""
        prefix = "  " * indent
        for key, value in items.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}")
                print_structure(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}")
                for item in value:
                    print(f"{prefix}  • {item}")
            else:
                print(f"{prefix}{key}: {value}")
    
    print_structure(structure)

def show_features():
    """Display key features."""
    print_separator("Key Features")
    
    features = [
        "🔗 Multiple Document Connectors",
        "   • Confluence integration with API support",
        "   • Medium article extraction",
        "   • Twitter/X post retrieval",
        "   • Reddit post collection",
        "",
        "🤖 Dynamic Model Selection",
        "   • OpenAI embeddings (text-embedding-ada-002, etc.)",
        "   • HuggingFace embeddings (sentence-transformers)",
        "   • OpenAI LLMs (GPT-3.5, GPT-4)",
        "   • Anthropic LLMs (Claude models)",
        "",
        "🗄️ Flexible Vector Storage",
        "   • Snowflake integration for enterprise",
        "   • FAISS for local deployment",
        "   • ChromaDB for development",
        "",
        "⚙️ Advanced Processing",
        "   • Configurable text chunking",
        "   • Smart overlap strategies",
        "   • Metadata preservation",
        "",
        "🎛️ User Interface",
        "   • FastAPI web interface",
        "   • Real-time configuration",
        "   • Interactive querying"
    ]
    
    for feature in features:
        print(feature)
    print()

def show_usage_examples():
    """Show usage examples."""
    print_separator("Usage Examples")
    
    examples = [
        "🚀 Quick Start:",
        "   python main.py",
        "   # Opens FastAPI interface on http://localhost:8000",
        "",
        "🔧 Custom Configuration:",
        "   python main.py --port 8080 --host 0.0.0.0",
        "   # Run on custom port with external access",
        "",
        "🐛 Debug Mode:",
        "   python main.py --debug",
        "   # Enable detailed logging",
        "",
        "📊 Programmatic Usage:",
        "   from rag_ing import EmbeddingManager, LLMManager",
        "   from rag_ing.connectors import ConfluenceConnector",
        "",
        "   # Configure embedding model",
        "   embedding_manager.load_model(config)",
        "",
        "   # Connect to data source",
        "   connector = ConfluenceConnector(config)",
        "   documents = connector.fetch_documents()",
        "",
        "   # Process and store",
        "   chunks = chunking_service.chunk_documents(documents)",
        "   vector_store.add_documents(chunks)"
    ]
    
    for example in examples:
        print(example)
    print()

def show_file_counts():
    """Show file statistics."""
    print_separator("Project Statistics")
    
    def count_files(directory, extension):
        """Count files with specific extension."""
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len([f for f in files if f.endswith(extension)])
        return count
    
    try:
        python_files = count_files('src', '.py')
        total_files = count_files('.', '')
        
        print(f"📄 Python files: {python_files}")
        print(f"📁 Total files: {total_files}")
        
        # Show module breakdown
        modules = {
            'config': count_files('src/rag_ing/config', '.py'),
            'connectors': count_files('src/rag_ing/connectors', '.py'),
            'models': count_files('src/rag_ing/models', '.py'),
            'storage': count_files('src/rag_ing/storage', '.py'),
            'ui': count_files('src/rag_ing/ui', '.py'),
        }
        
        print("\n📊 Module breakdown:")
        for module, count in modules.items():
            print(f"   {module}: {count} files")
        
    except Exception as e:
        print(f"Error counting files: {e}")
    
    print()

def show_architecture():
    """Show system architecture."""
    print_separator("System Architecture")
    
    architecture = """
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   Document      │    │    Medium       │    │   Social Media  │
    │   Confluence    │    │   Articles      │    │  Twitter/Reddit │
    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                            ┌─────────▼───────┐
                            │   Connectors    │
                            │   Management    │
                            └─────────┬───────┘
                                      │
                            ┌─────────▼───────┐
                            │  Text Chunking  │
                            │    Service      │
                            └─────────┬───────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
          ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
          │ Snowflake │         │   FAISS   │         │ ChromaDB  │
          │  Vector   │         │  Vector   │         │ Vector    │
          │   Store   │         │   Store   │         │  Store    │
          └─────┬─────┘         └─────┬─────┘         └─────┬─────┘
                └─────────────────────┼─────────────────────┘
                                      │
                            ┌─────────▼───────┐
                            │   Embedding     │
                            │    Models       │
                            │ OpenAI/HuggingF │
                            └─────────┬───────┘
                                      │
                            ┌─────────▼───────┐
                            │      LLM        │
                            │    Models       │
                            │ OpenAI/Anthropic│
                            └─────────┬───────┘
                                      │
                            ┌─────────▼───────┐
                            │   FastAPI      │
                            │   Interface     │
                            └─────────────────┘
    """
    
    print(architecture)
    print()

def main():
    """Main demo function."""
    print_separator()
    print("🔍 RAG-ing Project Demo")
    print("A comprehensive RAG application with multiple connectors")
    print_separator()
    
    show_project_structure()
    show_features()
    show_architecture()
    show_usage_examples()
    show_file_counts()
    
    print_separator("Next Steps")
    print("1. 📦 Install dependencies: pip install -e .")
    print("2. ⚙️ Configure API keys in .env file")
    print("3. 🚀 Run the application: python main.py")
    print("4. 🌐 Open http://localhost:8501 in your browser")
    print("5. 🔗 Connect your data sources and start querying!")
    print()
    print("For more information, see README.md")
    print_separator()

if __name__ == "__main__":
    main()