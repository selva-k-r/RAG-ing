#!/bin/bash

# Simple Docker deployment script for RAG-ing
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    cat << EOF
Usage: $0 [COMMAND]

COMMANDS:
    build       Build Docker image
    start       Start the application
    stop        Stop the application
    restart     Restart the application
    logs        Show application logs
    clean       Remove containers and volumes

EXAMPLES:
    $0 build        # Build the image
    $0 start        # Start the application
    $0 logs         # View logs

EOF
}

case "${1:-help}" in
    build)
        print_info "Building RAG-ing Docker image..."
        docker-compose build
        print_info "Build completed successfully"
        ;;
    start)
        print_info "Starting RAG-ing application..."
        docker-compose up -d
        print_info "Application started at: http://localhost:8000"
        ;;
    stop)
        print_info "Stopping RAG-ing application..."
        docker-compose down
        print_info "Application stopped"
        ;;
    restart)
        print_info "Restarting RAG-ing application..."
        docker-compose down
        docker-compose up -d
        print_info "Application restarted at: http://localhost:8000"
        ;;
    logs)
        print_info "Showing application logs..."
        docker-compose logs -f rag-app
        ;;
    clean)
        print_info "Cleaning up containers and volumes..."
        docker-compose down -v
        docker system prune -f
        print_info "Cleanup completed"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac