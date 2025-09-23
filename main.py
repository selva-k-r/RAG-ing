#!/usr/bin/env python3
"""Main entry point for RAG-ing application."""

import sys
import os
import argparse
import logging

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rag_ing.ui.streamlit_app import main as streamlit_main


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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG-ing: A comprehensive RAG application"
    )
    
    parser.add_argument(
        '--ui',
        choices=['streamlit'],
        default='streamlit',
        help='UI type to launch (default: streamlit)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port for Streamlit app (default: 8501)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    if args.ui == 'streamlit':
        # Import and run streamlit
        import streamlit.web.cli as stcli
        import streamlit.web.bootstrap as bootstrap
        
        # Set streamlit config
        os.environ['STREAMLIT_SERVER_PORT'] = str(args.port)
        os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
        
        # Path to streamlit app
        app_path = os.path.join(
            os.path.dirname(__file__), 
            'src', 
            'rag_ing', 
            'ui', 
            'streamlit_app.py'
        )
        
        # Run streamlit
        sys.argv = ['streamlit', 'run', app_path, '--server.port', str(args.port)]
        stcli.main()


if __name__ == "__main__":
    main()