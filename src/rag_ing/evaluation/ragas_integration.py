"""RAGAS Integration for RAG System Evaluation

This module integrates RAGAS (RAG Assessment) framework for comprehensive
evaluation of retrieval and generation quality.

Key Features:
- Context Precision/Recall evaluation
- Faithfulness and Answer Relevancy scoring
- Continuous evaluation with configurable sampling
- Medical domain-specific metrics
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        context_recall, 
        faithfulness,
        answer_relevancy,
        answer_correctness,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
        AnswerRelevancy,
        AnswerCorrectness
    )
    from ragas.llms import LangchainLLMWrapper
    from ragas import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logging.warning("RAGAS not available. Install with: pip install ragas")

from ..config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class RAGASScores:
    """Container for RAGAS evaluation scores."""
    context_precision: float = 0.0
    context_recall: float = 0.0
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    answer_correctness: float = 0.0
    overall_score: float = 0.0


class RAGASEvaluator:
    """RAGAS-based evaluation system for RAG pipeline assessment."""
    
    def __init__(self, config: Settings):
        """Initialize RAGAS evaluator with configuration.
        
        Args:
            config: System settings including evaluation parameters
        """
        self.config = config
        self.evaluation_config = config.evaluation
        self.ragas_available = RAGAS_AVAILABLE
        
        if not self.ragas_available:
            logger.warning("RAGAS evaluation disabled - package not installed")
            return
            
        # Initialize RAGAS metrics based on configuration
        self.metrics = self._initialize_metrics()
        
        # Continuous evaluation settings
        self.continuous_enabled = self.evaluation_config.continuous_eval.enabled
        self.sample_rate = self.evaluation_config.continuous_eval.sample_rate
        
        logger.info(f"RAGAS evaluator initialized with {len(self.metrics)} metrics")
    
    def _initialize_metrics(self) -> List[Any]:
        """Initialize RAGAS metrics based on configuration."""
        if not self.ragas_available:
            return []
            
        metrics = []
        
        # Retrieval metrics
        if self.evaluation_config.retrieval_metrics.context_precision:
            metrics.append(context_precision)
        if self.evaluation_config.retrieval_metrics.context_recall:
            metrics.append(context_recall)
            
        # Generation metrics  
        if self.evaluation_config.generation_metrics.faithfulness:
            metrics.append(faithfulness)
        if self.evaluation_config.generation_metrics.answer_relevancy:
            metrics.append(answer_relevancy)
        if self.evaluation_config.generation_metrics.answer_correctness:
            metrics.append(answer_correctness)
            
        return metrics
    
    def should_evaluate_query(self) -> bool:
        """Determine if current query should be evaluated based on sampling rate."""
        import random
        return random.random() < self.sample_rate
    
    async def evaluate_rag_response(
        self,
        query: str,
        response: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> RAGASScores:
        """Evaluate a single RAG response using RAGAS metrics.
        
        Args:
            query: User query
            response: Generated response
            contexts: Retrieved context documents
            ground_truth: Optional ground truth answer for comparison
            
        Returns:
            RAGASScores object with evaluation results
        """
        if not self.ragas_available:
            logger.warning("RAGAS evaluation requested but not available")
            return RAGASScores()
            
        try:
            # Prepare evaluation dataset
            eval_data = {
                "question": [query],
                "answer": [response], 
                "contexts": [contexts],
            }
            
            if ground_truth:
                eval_data["ground_truth"] = [ground_truth]
                
            dataset = Dataset.from_dict(eval_data)
            
            # Run evaluation
            result = await asyncio.to_thread(
                evaluate,
                dataset=dataset,
                metrics=self.metrics
            )
            
            # Extract scores
            scores = RAGASScores()
            result_dict = result.to_pandas().iloc[0].to_dict()
            
            scores.context_precision = result_dict.get('context_precision', 0.0)
            scores.context_recall = result_dict.get('context_recall', 0.0) 
            scores.faithfulness = result_dict.get('faithfulness', 0.0)
            scores.answer_relevancy = result_dict.get('answer_relevancy', 0.0)
            scores.answer_correctness = result_dict.get('answer_correctness', 0.0)
            
            # Calculate overall score as weighted average
            scores.overall_score = self._calculate_overall_score(scores)
            
            return scores
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return RAGASScores()
    
    def _calculate_overall_score(self, scores: RAGASScores) -> float:
        """Calculate overall score from individual RAGAS metrics."""
        # Weighted average based on importance
        weights = {
            'faithfulness': 0.3,     # Most important - factual accuracy
            'answer_relevancy': 0.25, # High importance - relevance  
            'context_precision': 0.2, # Important - retrieval quality
            'answer_correctness': 0.15, # Moderate - when ground truth available
            'context_recall': 0.1     # Lower weight - completeness
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        if scores.faithfulness > 0:
            total_score += scores.faithfulness * weights['faithfulness']
            total_weight += weights['faithfulness']
            
        if scores.answer_relevancy > 0:
            total_score += scores.answer_relevancy * weights['answer_relevancy'] 
            total_weight += weights['answer_relevancy']
            
        if scores.context_precision > 0:
            total_score += scores.context_precision * weights['context_precision']
            total_weight += weights['context_precision']
            
        if scores.answer_correctness > 0:
            total_score += scores.answer_correctness * weights['answer_correctness']
            total_weight += weights['answer_correctness']
            
        if scores.context_recall > 0:
            total_score += scores.context_recall * weights['context_recall']
            total_weight += weights['context_recall']
            
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def check_quality_thresholds(self, scores: RAGASScores) -> Dict[str, bool]:
        """Check if scores meet configured quality thresholds.
        
        Args:
            scores: RAGAS evaluation scores
            
        Returns:
            Dictionary indicating which thresholds were met
        """
        thresholds = self.evaluation_config.thresholds
        
        return {
            'faithfulness_ok': scores.faithfulness >= thresholds.faithfulness,
            'answer_relevancy_ok': scores.answer_relevancy >= thresholds.answer_relevancy,
            'context_precision_ok': scores.context_precision >= thresholds.context_precision,
            'overall_quality_ok': scores.overall_score >= 0.75  # Overall threshold
        }
    
    def log_evaluation_results(self, scores: RAGASScores, query: str, query_hash: str):
        """Log RAGAS evaluation results for monitoring.
        
        Args:
            scores: RAGAS evaluation scores
            query: Original user query
            query_hash: Unique query identifier
        """
        log_data = {
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )),
            "query_hash": query_hash,
            "query": query,
            "ragas_scores": {
                "context_precision": scores.context_precision,
                "context_recall": scores.context_recall,
                "faithfulness": scores.faithfulness,
                "answer_relevancy": scores.answer_relevancy,
                "answer_correctness": scores.answer_correctness,
                "overall_score": scores.overall_score
            },
            "quality_thresholds": self.check_quality_thresholds(scores)
        }
        
        logger.info(f"RAGAS evaluation: {log_data}")
        
        # Write to dedicated RAGAS log file
        if self.evaluation_config.logging.include_ragas_scores:
            import json
            ragas_log_path = f"{self.evaluation_config.logging.path}/ragas_evaluation.jsonl"
            
            try:
                with open(ragas_log_path, 'a') as f:
                    f.write(json.dumps(log_data) + '\n')
            except Exception as e:
                logger.error(f"Failed to write RAGAS log: {e}")


def create_ragas_evaluator(config: Settings) -> RAGASEvaluator:
    """Factory function to create RAGAS evaluator.
    
    Args:
        config: System configuration
        
    Returns:
        Configured RAGASEvaluator instance
    """
    return RAGASEvaluator(config)