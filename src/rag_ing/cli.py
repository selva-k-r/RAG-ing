"""Command line interface for RAG-ing application.

Note: This CLI is deprecated. Use main.py instead:
  - python main.py --ingest  # Ingest documents
  - python main.py --ui      # Launch FastAPI web interface
  - python main.py --query "your question"  # Single query
"""

import argparse
import logging
import sys

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
    """Deprecated CLI entry point - redirects to main.py."""
    parser = argparse.ArgumentParser(
        description="RAG-ing: A comprehensive RAG application (DEPRECATED - use main.py)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This CLI is deprecated. Please use main.py instead:

Examples:
  python main.py --ingest              # Process documents
  python main.py --ui                  # Launch web interface (FastAPI on port 8000)
  python main.py --query "question"    # Single query
  python main.py --debug               # Enable debug logging
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
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
    
    print("")
    print("[!] DEPRECATED: This CLI is no longer supported.")
    print("")
    print("Please use main.py instead:")
    print("  - python main.py --ingest  # Process documents")
    print("  - python main.py --ui      # Launch FastAPI web interface")
    print("  - python main.py --query \"your question\"  # Single query")
    print("")
    sys.exit(1)


if __name__ == "__main__":
    main()