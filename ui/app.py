#!/usr/bin/env python3
"""
Main FastAPI applicatio# Mount static files
import os
os.makedirs("ui/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="ui/static"), name="static")entry point.
Serves the RAG system with a clean, modular structure.
"""

import sys
import os
from pathlib import Path

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from api.routes import router as api_router
from api.pages import router as pages_router
from rag_ing.config.settings import Settings
from rag_ing.orchestrator import RAGOrchestrator

# Global RAG orchestrator
rag_system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG system on startup and cleanup on shutdown."""
    global rag_system
    try:
        print("🚀 Starting iConnect FastAPI server...")
        rag_system = RAGOrchestrator('./config.yaml')
        print("✅ RAG system initialized successfully")
        yield
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        rag_system = None
        yield
    finally:
        # Cleanup code would go here if needed
        pass

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="iConnect - Enterprise RAG System",
    description="AI-Powered Search with Healthcare & Enterprise Integration",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(pages_router, tags=["Pages"])

# Global function to access RAG system
def get_rag_system():
    return rag_system

if __name__ == "__main__":
    import uvicorn
    print("📱 Frontend: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")
    print("⚡ Performance: Maximum - Clean modular architecture")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=False
    )