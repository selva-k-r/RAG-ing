"""Main orchestration module for the RAG-ing Modular PoC.

This module coordinates all 5 core modules to provide a complete RAG system:
- Module 1: Corpus & Embedding Lifecycle
- Module 2: Query Processing & Retrieval  
- Module 3: LLM Orchestration
- Module 4: UI Layer
- Module 5: Evaluation & Logging
"""

import time
import hashlib
from typing import Dict, List, Any, Optional
import logging

from .config.settings import Settings
from .modules import (
    CorpusEmbeddingModule,
    QueryRetrievalModule,
    LLMOrchestrationModule,
    UILayerModule,
    EvaluationLoggingModule
)
from .modules.evaluation_logging import QueryEvent, RetrievalMetrics, GenerationMetrics
from .utils.exceptions import RAGError, UIError
from .utils.activity_logger import ActivityLogger

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Main orchestrator that coordinates all RAG modules."""
    
    def __init__(self, config_path: str = "./config.yaml"):
        """Initialize the RAG orchestrator with all modules.
        
        Args:
            config_path: Path to YAML configuration file
        """
        # Load configuration
        try:
            self.settings = Settings.from_yaml(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}, using defaults: {e}")
            self.settings = Settings()
        
        # Initialize all 5 modules
        self.corpus_embedding = CorpusEmbeddingModule(self.settings)
        self.query_retrieval = QueryRetrievalModule(self.settings)
        self.llm_orchestration = LLMOrchestrationModule(self.settings)
        self.ui_layer = UILayerModule(self.settings)
        self.evaluation_logging = EvaluationLoggingModule(self.settings)
        
        # Initialize activity logger
        if self.settings.activity_logging.enabled:
            self.activity_logger = ActivityLogger(
                log_dir=self.settings.activity_logging.log_dir
            )
            logger.info("Activity logging enabled")
        else:
            self.activity_logger = None
            logger.info("Activity logging disabled")
        
        logger.info("RAG Orchestrator initialized with all 5 modules")
    
    def ingest_corpus(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Ingest and embed the document corpus.
        
        Args:
            force_rebuild: Whether to rebuild the entire corpus from scratch
            
        Returns:
            Dict containing ingestion statistics
        """
        logger.info("Starting corpus ingestion...")
        start_time = time.time()
        
        try:
            # Module 1: Corpus & Embedding Lifecycle
            ingestion_stats = self.corpus_embedding.process_corpus()
            
            ingestion_time = time.time() - start_time
            
            # Log to evaluation module
            self.evaluation_logging.update_system_metrics(
                success=True, 
                processing_time=ingestion_time
            )
            
            logger.info(f"Corpus ingestion completed in {ingestion_time:.2f}s")
            return {
                "success": True,
                "processing_time": ingestion_time,
                **ingestion_stats
            }
            
        except Exception as e:
            self.evaluation_logging.update_system_metrics(success=False)
            logger.error(f"Corpus ingestion failed: {e}")
            raise RAGError(f"Corpus ingestion failed: {e}")
    
    def query_documents(self, query: str, 
                       user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Complete query processing pipeline.
        
        Args:
            query: User query
            user_context: Additional user context
            
        Returns:
            Complete response with metadata
        """
        start_time = time.time()
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        logger.info(f"Processing query [{query_hash}]: {query[:100]}...")
        
        try:
            # Module 2: Query Processing & Retrieval
            retrieval_start = time.time()
            retrieval_result = self.query_retrieval.process_query(query)
            retrieval_time = time.time() - retrieval_start
            
            retrieved_docs = retrieval_result["documents"]
            retrieval_stats = retrieval_result["stats"]
            
            # Calculate retrieval metrics (Module 5)
            retrieval_metrics = self.evaluation_logging.calculate_retrieval_metrics(
                query=query,
                retrieved_docs=retrieved_docs,
                retrieval_time=retrieval_time
            )
            
            # Module 3: LLM Orchestration
            generation_start = time.time()
            
            # Convert retrieved documents to context string
            context = "\n\n".join([doc.page_content for doc in retrieved_docs])
            
            # Module 3: LLM Orchestration
            llm_response = self.llm_orchestration.generate_response(
                query=query,
                context=context
            )
            generation_time = time.time() - generation_start
            
            # Calculate generation metrics (Module 5)
            generation_metrics = self.evaluation_logging.calculate_generation_metrics(
                response=llm_response["response"],
                sources=retrieved_docs,
                generation_time=generation_time,
                model_name=llm_response.get("model") or llm_response.get("model_used", "unknown")  # Support both "model" and "model_used"
            )
            
            # Calculate safety score
            safety_score = self.evaluation_logging.calculate_safety_score(
                response=llm_response["response"],
                query=query
            )
            generation_metrics.safety_score = safety_score
            
            # Total processing time
            total_time = time.time() - start_time
            
            # Create complete response
            complete_response = {
                "query": query,
                "query_hash": query_hash,
                "response": llm_response["response"],
                "sources": retrieved_docs,
                "metadata": {
                    "retrieval_stats": retrieval_stats,
                    "generation_stats": llm_response.get("stats", {}),
                    "total_processing_time": total_time,
                    "safety_score": safety_score,
                    "model_used": llm_response.get("model_used")
                },
                "timestamp": time.time()
            }
            
            # Log complete query event (Module 5)
            query_event = QueryEvent(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                query=query,
                query_hash=query_hash,
                retrieval_metrics=retrieval_metrics,
                generation_metrics=generation_metrics,
                system_metadata={
                    "total_processing_time": total_time,
                    "retrieval_time": retrieval_time,
                    "generation_time": generation_time
                }
            )
            
            self.evaluation_logging.log_query_event(query_event)
            self.evaluation_logging.update_system_metrics(
                success=True,
                processing_time=total_time
            )
            
            # Log user activity for analytics
            if self.activity_logger:
                import uuid
                session_id = (user_context or {}).get('session_id', str(uuid.uuid4()))
                self.activity_logger.log_search(
                    query=query,
                    results=retrieved_docs,
                    session_id=session_id,
                    retrieval_time=retrieval_time,
                    generation_time=generation_time,
                    user_context=user_context
                )
            
            logger.info(f"Query [{query_hash}] processed successfully in {total_time:.2f}s")
            return complete_response
            
        except Exception as e:
            self.evaluation_logging.update_system_metrics(success=False)
            logger.error(f"Query processing failed: {e}")
            raise RAGError(f"Query processing failed: {e}")
    
    def collect_feedback(self, query_hash: str, feedback: Dict[str, Any]) -> None:
        """Collect user feedback for a query.
        
        Args:
            query_hash: Hash of the original query
            feedback: User feedback dictionary
        """
        logger.info(f"Collecting feedback for query [{query_hash}]")
        
        try:
            # Find the query event and update it
            for event in self.evaluation_logging._query_events:
                if event.query_hash == query_hash:
                    event.user_feedback = feedback
                    # Re-log the updated event
                    self.evaluation_logging.log_query_event(event)
                    logger.info(f"Feedback collected for query [{query_hash}]")
                    return
            
            logger.warning(f"Query [{query_hash}] not found for feedback collection")
            
        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status and metrics.
        
        Returns:
            System status dictionary
        """
        return {
            "modules_initialized": True,
            "corpus_status": self.corpus_embedding.get_corpus_status(),
            "session_summary": self.evaluation_logging.get_session_summary(),
            "enabled_metrics": self.evaluation_logging.get_enabled_metrics(),
            "logging_enabled": self.evaluation_logging.is_logging_enabled(),
            "configuration": {
                "embedding_model": self.settings.embedding_model.name,
                "vector_store": self.settings.vector_store.type,
                "llm_provider": self.settings.llm.provider
            }
        }
    
    def run_web_app(self) -> None:
        """Launch the FastAPI web application.
        
        This passes control to Module 4: UI Layer (FastAPI implementation)
        """
        import subprocess
        import sys
        
        logger.info("Launching FastAPI web application...")
        
        try:
            # Run the new modular FastAPI app
            web_cmd = [
                sys.executable, "ui/app.py"
            ]
            
            logger.info(f"Starting web app with command: {' '.join(web_cmd)}")
            
            # Run FastAPI web app
            subprocess.run(web_cmd, check=True)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Web app failed to start: {e}")
            raise UIError(f"Web app failed to start: {e}")
        except Exception as e:
            logger.error(f"Failed to launch web app: {e}")
            raise UIError(f"Failed to launch web app: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check on all modules.
        
        Returns:
            Health check results with module status and overall system health
        """
        logger.info("Performing health check on all modules...")
        
        health_results = {
            "overall": "healthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modules": {}
        }
        
        # Check each module
        modules_to_check = [
            ("corpus_embedding", self.corpus_embedding),
            ("query_retrieval", self.query_retrieval),
            ("llm_orchestration", self.llm_orchestration),
            ("ui_layer", self.ui_layer),
            ("evaluation_logging", self.evaluation_logging)
        ]
        
        overall_healthy = True
        
        for module_name, module_instance in modules_to_check:
            try:
                # Basic health check - verify module is initialized
                if hasattr(module_instance, 'config'):
                    health_results["modules"][module_name] = {
                        "status": "healthy",
                        "initialized": True
                    }
                else:
                    health_results["modules"][module_name] = {
                        "status": "warning",
                        "initialized": False,
                        "error": "Module may not be properly initialized"
                    }
                    overall_healthy = False
                    
            except Exception as e:
                health_results["modules"][module_name] = {
                    "status": "error",
                    "initialized": False,
                    "error": str(e)
                }
                overall_healthy = False
        
        health_results["overall"] = "healthy" if overall_healthy else "unhealthy"
        logger.info(f"Health check completed. Overall status: {health_results['overall']}")
        return health_results
    
    def export_session_data(self, format_type: str = "json") -> str:
        """Export session metrics and logs.
        
        Args:
            format_type: Export format (json, csv, etc.)
            
        Returns:
            Exported data as string
        """
        logger.info(f"Exporting session data in {format_type} format")
        return self.evaluation_logging.export_metrics(format_type)
    
    def clear_session(self) -> None:
        """Clear all session data and reset metrics."""
        logger.info("Clearing session data...")
        self.evaluation_logging.clear_session_data()
        logger.info("Session data cleared")


# Convenience function for quick setup
def create_rag_system(config_path: str = "./config.yaml") -> RAGOrchestrator:
    """Create and return a configured RAG system.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configured RAGOrchestrator instance
    """
    return RAGOrchestrator(config_path)


# CLI entry point
def main():
    """Main entry point for the RAG system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG-ing Modular PoC")
    parser.add_argument("--config", default="./config.yaml", help="Configuration file path")
    parser.add_argument("--ingest", action="store_true", help="Run corpus ingestion")
    parser.add_argument("--ui", action="store_true", help="Launch UI application")
    parser.add_argument("--status", action="store_true", help="Show system status")
    
    args = parser.parse_args()
    
    # Initialize RAG system
    rag = create_rag_system(args.config)
    
    if args.ingest:
        print("🔄 Starting corpus ingestion...")
        result = rag.ingest_corpus()
        print(f"[OK] Ingestion completed: {result}")
        
    elif args.status:
        print("System Status:")
        status = rag.get_system_status()
        print(status)
        
    elif args.ui:
        print("🌐 Launching UI...")
        rag.run_web_app()
        
    else:
        print("RAG System initialized. Use --help for options.")


if __name__ == "__main__":
    main()