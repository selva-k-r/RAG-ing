"""Command line interface for RAG-ing application."""

import argparse
import logging
import sys
import os
from typing import Optional

from .modules.ui_layer import UILayerModule
from .config.settings import Settings


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


def run_streamlit_app(config_path: Optional[str] = None, port: int = 8501, host: str = "localhost"):
    """Run the Streamlit application with modular architecture."""
    try:
        import streamlit.web.cli as stcli
        
        # Set environment variables for streamlit
        os.environ['STREAMLIT_SERVER_PORT'] = str(port)
        os.environ['STREAMLIT_SERVER_ADDRESS'] = host
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
        
        # Set config path if provided
        if config_path:
            os.environ['RAG_CONFIG_PATH'] = config_path
        
        # Create temporary streamlit app file that uses our modular UI
        temp_app_content = f'''
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.rag_ing.config.settings import Settings
from src.rag_ing.modules.ui_layer import UILayerModule

# Load configuration
config_path = os.environ.get('RAG_CONFIG_PATH', './config.yaml')
try:
    settings = Settings.from_yaml(config_path)
except FileNotFoundError:
    # Use default settings if no config file
    settings = Settings()

# Initialize and run UI
ui_module = UILayerModule(settings)
ui_module.run_streamlit_interface()
'''
        
        # Write temporary app file
        temp_app_path = "/tmp/rag_streamlit_app.py"
        with open(temp_app_path, 'w') as f:
            f.write(temp_app_content)
        
        # Run streamlit
        sys.argv = ['streamlit', 'run', temp_app_path, '--server.port', str(port), '--server.address', host]
        stcli.main()
        
    except ImportError:
        print("Error: Streamlit not installed. Install with: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Streamlit app: {{e}}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG-ing: A comprehensive RAG application with multiple connectors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rag-ing                          # Run with default settings
  rag-ing --port 8080             # Run on custom port
  rag-ing --debug                 # Enable debug logging
  rag-ing --host 0.0.0.0          # Allow external connections
        """
    )
    
    parser.add_argument(
        '--ui',
        choices=['streamlit'],
        default='streamlit',
        help='UI type to launch (default: streamlit)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='./config.yaml',
        help='Path to YAML configuration file (default: ./config.yaml)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port for the web interface (default: 8501)'
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host for the web interface (default: localhost)'
    )
    
    parser.add_argument(
        '--config',
        default='./config.yaml',
        help='Path to YAML configuration file (default: ./config.yaml)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='RAG-ing 0.1.0'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    print("🔍 Starting RAG-ing application...")
    print(f"UI: {args.ui}")
    print(f"Config: {args.config}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    
    if args.ui == 'streamlit':
        run_streamlit_app(config_path=args.config, port=args.port, host=args.host)
    else:
        print(f"Error: Unsupported UI type: {args.ui}")
        sys.exit(1)


if __name__ == "__main__":
    main()