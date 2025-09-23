"""Command line interface for RAG-ing application."""

import argparse
import logging
import sys
import os
from typing import Optional

from .ui.streamlit_app import main as streamlit_main


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


def run_streamlit_app(port: int = 8501, host: str = "localhost"):
    """Run the Streamlit application."""
    try:
        import streamlit.web.cli as stcli
        
        # Set environment variables for streamlit
        os.environ['STREAMLIT_SERVER_PORT'] = str(port)
        os.environ['STREAMLIT_SERVER_ADDRESS'] = host
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
        
        # Get path to streamlit app
        app_path = os.path.join(os.path.dirname(__file__), 'ui', 'streamlit_app.py')
        
        # Run streamlit
        sys.argv = ['streamlit', 'run', app_path, '--server.port', str(port), '--server.address', host]
        stcli.main()
        
    except ImportError:
        print("Error: Streamlit not installed. Install with: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Streamlit app: {e}")
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
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    
    if args.ui == 'streamlit':
        run_streamlit_app(port=args.port, host=args.host)
    else:
        print(f"Error: Unsupported UI type: {args.ui}")
        sys.exit(1)


if __name__ == "__main__":
    main()