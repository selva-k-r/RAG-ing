"""Continuous Evaluation Framework

This module provides real-time evaluation capabilities for monitoring
RAG system performance in production.

Features:
- Configurable sampling for performance evaluation
- Threshold-based alerting
- Trend analysis and performance degradation detection
- Integration with RAGAS metrics
"""

import logging
import time
import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from ..config.settings import Settings
from .ragas_integration import RAGASEvaluator, RAGASScores

logger = logging.getLogger(__name__)


@dataclass
class EvaluationEvent:
    """Container for evaluation event data."""
    timestamp: str
    query_hash: str
    query: str
    response: str
    contexts: List[str]
    ragas_scores: RAGASScores
    processing_time: float
    threshold_alerts: Dict[str, bool]


@dataclass
class PerformanceTrend:
    """Container for performance trend analysis."""
    metric_name: str
    current_value: float
    trend_direction: str  # 'improving', 'declining', 'stable'
    change_percentage: float
    alert_triggered: bool


class ContinuousEvaluationFramework:
    """Real-time evaluation and monitoring system for RAG performance."""
    
    def __init__(self, config: Settings):
        """Initialize continuous evaluation framework.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.evaluation_config = config.evaluation
        
        # Initialize RAGAS evaluator
        self.ragas_evaluator = RAGASEvaluator(config)
        
        # Evaluation state
        self.enabled = self.evaluation_config.continuous_eval.enabled
        self.sample_rate = self.evaluation_config.continuous_eval.sample_rate
        
        # Performance tracking
        self.recent_evaluations = []
        self.max_recent_evaluations = 100  # Keep last 100 evaluations
        
        # Trend analysis
        self.trend_window_hours = 24  # Analyze trends over 24 hours
        self.performance_history = []
        
        # Alerting
        self.alert_cooldown = 300  # 5 minutes between similar alerts
        self.last_alerts = {}
        
        # Metrics aggregation
        self.metrics_summary = {
            'total_evaluations': 0,
            'average_scores': {},
            'threshold_violations': {},
            'trend_analysis': {}
        }
        
        logger.info(f"Continuous evaluation framework initialized - "
                   f"Enabled: {self.enabled}, Sample rate: {self.sample_rate}")
    
    async def evaluate_query_response(
        self,
        query: str,
        response: str,
        contexts: List[str],
        query_hash: str,
        processing_time: float
    ) -> Optional[EvaluationEvent]:
        """Evaluate a query response if selected for sampling.
        
        Args:
            query: User query
            response: Generated response
            contexts: Retrieved context documents
            query_hash: Unique query identifier
            processing_time: Time taken to process query
            
        Returns:
            EvaluationEvent if evaluation was performed, None otherwise
        """
        if not self.enabled:
            return None
            
        # Check if this query should be evaluated
        if not self.ragas_evaluator.should_evaluate_query():
            return None
            
        try:
            # Perform RAGAS evaluation
            ragas_scores = await self.ragas_evaluator.evaluate_rag_response(
                query=query,
                response=response,
                contexts=contexts
            )
            
            # Check quality thresholds
            threshold_alerts = self.ragas_evaluator.check_quality_thresholds(ragas_scores)
            
            # Create evaluation event
            eval_event = EvaluationEvent(
                timestamp=datetime.now().isoformat(),
                query_hash=query_hash,
                query=query,
                response=response,
                contexts=contexts,
                ragas_scores=ragas_scores,
                processing_time=processing_time,
                threshold_alerts=threshold_alerts
            )
            
            # Store evaluation
            await self._store_evaluation(eval_event)
            
            # Check for alerts
            await self._check_and_send_alerts(eval_event)
            
            # Update metrics
            self._update_metrics_summary(eval_event)
            
            return eval_event
            
        except Exception as e:
            logger.error(f"Continuous evaluation failed: {e}")
            return None
    
    async def _store_evaluation(self, eval_event: EvaluationEvent):
        """Store evaluation event for trend analysis and monitoring.
        
        Args:
            eval_event: Evaluation event to store
        """
        # Add to recent evaluations (in-memory)
        self.recent_evaluations.append(eval_event)
        
        # Maintain sliding window
        if len(self.recent_evaluations) > self.max_recent_evaluations:
            self.recent_evaluations.pop(0)
        
        # Persist to file
        log_path = Path(self.evaluation_config.logging.path) / "continuous_evaluation.jsonl"
        
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a') as f:
                log_data = asdict(eval_event)
                # Convert nested dataclass to dict
                log_data['ragas_scores'] = asdict(eval_event.ragas_scores)
                f.write(json.dumps(log_data) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to persist evaluation event: {e}")
    
    async def _check_and_send_alerts(self, eval_event: EvaluationEvent):
        """Check for threshold violations and send alerts.
        
        Args:
            eval_event: Evaluation event to check
        """
        current_time = time.time()
        
        # Check each threshold
        for metric, is_ok in eval_event.threshold_alerts.items():
            if not is_ok:  # Threshold violated
                alert_key = f"threshold_{metric}"
                
                # Check cooldown
                if (alert_key in self.last_alerts and 
                    current_time - self.last_alerts[alert_key] < self.alert_cooldown):
                    continue
                
                # Send alert
                await self._send_alert(
                    alert_type="threshold_violation",
                    metric=metric,
                    current_value=getattr(eval_event.ragas_scores, metric.replace('_ok', ''), 0.0),
                    threshold=getattr(self.evaluation_config.thresholds, metric.replace('_ok', ''), 0.0),
                    query_hash=eval_event.query_hash
                )
                
                self.last_alerts[alert_key] = current_time
    
    async def _send_alert(self, alert_type: str, **kwargs):
        """Send alert about performance issue.
        
        Args:
            alert_type: Type of alert
            **kwargs: Alert-specific parameters
        """
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": "warning",
            **kwargs
        }
        
        # Log alert
        logger.warning(f"Performance alert: {alert_data}")
        
        # Store alert for monitoring dashboard
        alert_log_path = Path(self.evaluation_config.logging.path) / "alerts.jsonl"
        
        try:
            with open(alert_log_path, 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    def _update_metrics_summary(self, eval_event: EvaluationEvent):
        """Update running metrics summary.
        
        Args:
            eval_event: Evaluation event to incorporate
        """
        self.metrics_summary['total_evaluations'] += 1
        
        # Update average scores
        scores = asdict(eval_event.ragas_scores)
        for metric, value in scores.items():
            if metric not in self.metrics_summary['average_scores']:
                self.metrics_summary['average_scores'][metric] = []
            
            self.metrics_summary['average_scores'][metric].append(value)
            
            # Keep sliding window
            if len(self.metrics_summary['average_scores'][metric]) > 50:
                self.metrics_summary['average_scores'][metric].pop(0)
        
        # Update threshold violations
        for metric, is_violated in eval_event.threshold_alerts.items():
            if not is_violated:  # Violation occurred
                if metric not in self.metrics_summary['threshold_violations']:
                    self.metrics_summary['threshold_violations'][metric] = 0
                self.metrics_summary['threshold_violations'][metric] += 1
    
    def analyze_performance_trends(self) -> List[PerformanceTrend]:
        """Analyze performance trends over recent evaluations.
        
        Returns:
            List of performance trends for key metrics
        """
        if len(self.recent_evaluations) < 10:
            return []  # Need minimum data for trend analysis
        
        trends = []
        
        # Analyze trends for key metrics
        metrics_to_analyze = ['faithfulness', 'answer_relevancy', 'context_precision', 'overall_score']
        
        for metric in metrics_to_analyze:
            try:
                # Get recent values
                recent_values = []
                for eval_event in self.recent_evaluations[-20:]:  # Last 20 evaluations
                    value = getattr(eval_event.ragas_scores, metric, 0.0)
                    recent_values.append(value)
                
                if not recent_values:
                    continue
                
                # Calculate trend
                current_avg = sum(recent_values[-5:]) / 5  # Last 5 evaluations
                historical_avg = sum(recent_values[:-5]) / len(recent_values[:-5])  # Previous evaluations
                
                change_pct = ((current_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0
                
                # Determine trend direction
                if abs(change_pct) < 2:  # Less than 2% change
                    direction = 'stable'
                elif change_pct > 0:
                    direction = 'improving'
                else:
                    direction = 'declining'
                
                # Check if alert should be triggered (>10% decline)
                alert_triggered = direction == 'declining' and change_pct < -10
                
                trend = PerformanceTrend(
                    metric_name=metric,
                    current_value=current_avg,
                    trend_direction=direction,
                    change_percentage=change_pct,
                    alert_triggered=alert_triggered
                )
                
                trends.append(trend)
                
            except Exception as e:
                logger.error(f"Failed to analyze trend for {metric}: {e}")
        
        return trends
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary.
        
        Returns:
            Dictionary with performance metrics and trends
        """
        # Calculate current averages
        current_averages = {}
        for metric, values in self.metrics_summary['average_scores'].items():
            if values:
                current_averages[metric] = sum(values) / len(values)
        
        # Get recent trends
        trends = self.analyze_performance_trends()
        trend_summary = {trend.metric_name: {
            'direction': trend.trend_direction,
            'change_pct': trend.change_percentage,
            'alert': trend.alert_triggered
        } for trend in trends}
        
        return {
            'evaluation_summary': {
                'total_evaluations': self.metrics_summary['total_evaluations'],
                'recent_evaluations': len(self.recent_evaluations),
                'sample_rate': self.sample_rate,
                'enabled': self.enabled
            },
            'current_performance': current_averages,
            'threshold_violations': self.metrics_summary['threshold_violations'],
            'trends': trend_summary,
            'last_updated': datetime.now().isoformat()
        }
    
    async def run_performance_analysis(self):
        """Run periodic performance analysis and alerting."""
        while self.enabled:
            try:
                # Analyze trends
                trends = self.analyze_performance_trends()
                
                # Send alerts for significant declines
                for trend in trends:
                    if trend.alert_triggered:
                        await self._send_alert(
                            alert_type="performance_decline",
                            metric=trend.metric_name,
                            current_value=trend.current_value,
                            change_percentage=trend.change_percentage,
                            trend_direction=trend.trend_direction
                        )
                
                # Sleep for analysis interval (30 minutes)
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Performance analysis failed: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry


def create_continuous_evaluator(config: Settings) -> ContinuousEvaluationFramework:
    """Factory function to create continuous evaluation framework.
    
    Args:
        config: System configuration
        
    Returns:
        Configured ContinuousEvaluationFramework instance
    """
    return ContinuousEvaluationFramework(config)