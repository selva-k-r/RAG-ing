#!/usr/bin/env python3
"""
Main FastAPI application entry point.
Serves the RAG system with transformer UI and real-time progress tracking.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    """Initialize the RAG system on startup and cleanup on shutdown with validation."""
    global rag_system
    
    print("=" * 70)
    print(" Starting iConnect RAG System")
    print("=" * 70)
    
    try:
        print("\n Loading configuration from config.yaml...")
        rag_system = RAGOrchestrator('./config.yaml')
        print(" Configuration loaded")
        
        # Validate LLM connectivity
        print("\n Validating LLM provider connectivity...")
        llm_module = rag_system.llm_orchestration
        provider = llm_module.llm_config.provider
        model = llm_module.llm_config.model
        
        print(f"   Provider: {provider}")
        print(f"   Model: {model}")
        
        if not llm_module.client:
            raise ConnectionError(
                f" [FAIL] LLM provider '{provider}' failed to initialize!\n\n"
                f"Current configuration:\n"
                f"  - Provider: {provider}\n"
                f"  - Model: {model}\n\n"
                f"Action required:\n"
                f"  - For Azure OpenAI: Run 'python setup_azure_openai.py'\n"
                f"  - For KoboldCpp: Start server at {llm_module.llm_config.api_url}\n\n"
                f"See FIX_404_ERROR.md for complete instructions."
            )
        
        print(f" [OK] LLM provider '{provider}' connected")
        
        # Test LLM connection
        print("\n Testing LLM connection...")
        try:
            test_result = llm_module.test_connection()
            if test_result:
                print(" [OK] LLM connection test: PASSED")
            else:
                print("  [WARN] LLM connection test: FAILED (but initialization succeeded)")
                print("   The system will start but queries may fail.")
        except Exception as test_error:
            print(f"  [WARN] LLM connection test failed: {test_error}")
            print("   The system will start but queries may fail.")
        
        print("\n" + "=" * 70)
        print(" RAG system initialized successfully")
        print("=" * 70)
        print(f"\n Frontend: http://localhost:8000")
        print(f" API Docs: http://localhost:8000/docs")
        print(f" Health Check: http://localhost:8000/api/health")
        print("\n" + "=" * 70 + "\n")
        
        yield
        
    except (ValueError, ConnectionError) as e:
        print("\n" + "=" * 70)
        print(" STARTUP FAILED - Configuration Error")
        print("=" * 70)
        print(f"\n{str(e)}\n")
        print("=" * 70)
        print("The server will start in degraded mode.")
        print("All queries will fail until configuration is fixed.")
        print("=" * 70 + "\n")
        rag_system = None
        yield
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(" STARTUP FAILED - Unexpected Error")
        print("=" * 70)
        print(f"\nError: {e}\n")
        import traceback
        print("Traceback:")
        print(traceback.format_exc())
        print("=" * 70)
        print("The server will start in degraded mode.")
        print("=" * 70 + "\n")
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

# Include progress routes
from api.simple_progress import router as progress_router
app.include_router(progress_router, prefix="/api", tags=["Progress"])

# Global function to access RAG system
def get_rag_system():
    return rag_system

if __name__ == "__main__":
    import uvicorn
    print(" Frontend: http://localhost:8000")
    print(" API Docs: http://localhost:8000/docs")
    print(" Performance: Maximum - Clean modular architecture")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=False
    )