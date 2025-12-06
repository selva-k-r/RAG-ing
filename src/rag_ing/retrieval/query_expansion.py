"""Query Expansion Engine for Multi-Query Retrieval

This module generates multiple variations of user queries to improve retrieval coverage.
It also detects which project/repository the query relates to for metadata filtering.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QueryExpansionResult:
    """Container for query expansion results."""
    original_query: str
    variations: List[str]
    detected_project: str
    confidence: float
    all_queries: List[str]  # Original + variations
    
    def __post_init__(self):
        """Ensure all_queries includes original + variations."""
        if not self.all_queries:
            self.all_queries = [self.original_query] + self.variations


class QueryExpansionEngine:
    """Generate alternative query formulations and detect project context."""
    
    def __init__(self, config, llm_client):
        """Initialize query expansion engine.
        
        Args:
            config: Settings object with query_expansion configuration
            llm_client: LLM client for generating expansions (from LLMOrchestration module)
        """
        self.config = config
        self.expansion_config = config.retrieval.query_expansion
        self.llm_client = llm_client
        
        # Load expansion prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Cache for query expansions (if enabled)
        self._expansion_cache = {}
        
        logger.info(f"[OK] QueryExpansionEngine initialized (variations={self.expansion_config.num_variations})")
    
    def _load_prompt_template(self) -> str:
        """Load query expansion prompt template from file.
        
        Returns:
            Prompt template string
        """
        prompt_path = Path(self.expansion_config.expansion_prompt)
        
        if not prompt_path.exists():
            logger.warning(f"Prompt template not found: {prompt_path}, using default")
            return self._get_default_prompt()
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            logger.info(f"[OK] Loaded expansion prompt from {prompt_path}")
            return prompt
        except Exception as e:
            logger.error(f"[X] Failed to load prompt template: {e}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default prompt template if file loading fails.
        
        Returns:
            Default prompt template string
        """
        return """You are a query expansion expert.

ORIGINAL QUESTION:
{query}

AVAILABLE PROJECTS:
{project_list}

Generate {num_variations} alternative formulations and detect the project.

Output as JSON:
{{
  "variations": ["variation1", "variation2", ...],
  "project": "project_name",
  "confidence": 0.95
}}
"""
    
    def get_available_projects(self, vector_store) -> List[str]:
        """Extract distinct project tags from vector store metadata.
        
        Args:
            vector_store: Vector store instance with metadata
            
        Returns:
            List of unique project tags
        """
        try:
            # Try to get unique project tags from metadata
            # Implementation depends on vector store type (Chroma, FAISS, etc.)
            projects = []
            
            # For ChromaDB
            if hasattr(vector_store, '_collection'):
                collection = vector_store._collection
                # Get all metadata
                results = collection.get(include=['metadatas'])
                if results and results.get('metadatas'):
                    projects = set()
                    for metadata in results['metadatas']:
                        if metadata and 'project_tag' in metadata:
                            projects.add(metadata['project_tag'])
                    projects = sorted(list(projects))
            
            # Default projects if none found in metadata
            if not projects:
                projects = ['anthem', 'upmc', 'pophealth', 'general']
                logger.warning("[!] No projects found in metadata, using defaults")
            
            logger.info(f"[OK] Available projects: {projects}")
            return projects
            
        except Exception as e:
            logger.error(f"[X] Failed to extract projects from vector store: {e}")
            return ['anthem', 'upmc', 'pophealth', 'general']
    
    async def expand_query_with_project(
        self,
        query: str,
        available_projects: Optional[List[str]] = None
    ) -> QueryExpansionResult:
        """Generate query variations and detect project.
        
        Args:
            query: Original user question
            available_projects: List of available project tags (optional)
            
        Returns:
            QueryExpansionResult with variations and detected project
        """
        # Check cache first
        if self.expansion_config.cache_expansions:
            cache_key = self._get_cache_key(query)
            if cache_key in self._expansion_cache:
                logger.info(f"[OK] Cache hit for query expansion")
                return self._expansion_cache[cache_key]
        
        # Default projects if not provided
        if not available_projects:
            available_projects = ['anthem', 'upmc', 'pophealth', 'general']
        
        # Format prompt
        prompt = self.prompt_template.format(
            query=query,
            project_list=", ".join(available_projects),
            num_variations=self.expansion_config.num_variations
        )
        
        try:
            # Call LLM to generate expansions
            logger.info(f"[...] Generating {self.expansion_config.num_variations} query variations")
            
            response = await self._call_llm(prompt)
            
            # Parse JSON response
            result_data = self._parse_llm_response(response)
            
            # Create result object
            result = QueryExpansionResult(
                original_query=query,
                variations=result_data.get('variations', []),
                detected_project=result_data.get('project', 'general'),
                confidence=result_data.get('confidence', 0.5),
                all_queries=[]  # Will be set in __post_init__
            )
            
            logger.info(
                f"[OK] Query expansion complete: {len(result.variations)} variations, "
                f"project={result.detected_project} (confidence={result.confidence:.2f})"
            )
            
            # Cache result
            if self.expansion_config.cache_expansions:
                self._expansion_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"[X] Query expansion failed: {e}")
            # Return fallback result
            return self._get_fallback_result(query)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with expansion prompt.
        
        Args:
            prompt: Formatted prompt for LLM
            
        Returns:
            LLM response string
        """
        try:
            # The llm_client is now the LLMOrchestrationModule
            # It has generate_response(query, context) method (synchronous)
            # We need to run it in an executor since we're in an async context
            
            if hasattr(self.llm_client, 'generate_response'):
                # Run the synchronous method in an executor
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.llm_client.generate_response(
                        query=prompt,
                        context=""  # No context needed for expansion
                    )
                )
                # Extract text from response dict
                return result.get('response', str(result))
            else:
                # Fallback: shouldn't happen if set up correctly
                logger.error("[X] LLM client does not have generate_response method")
                raise AttributeError("Invalid LLM client provided to query expansion")
            
        except Exception as e:
            logger.error(f"[X] LLM call failed in query expansion: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response.
        
        Args:
            response: LLM response string (should be JSON)
            
        Returns:
            Parsed dictionary with variations, project, confidence
        """
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith('```'):
                # Remove markdown code block markers
                lines = cleaned.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned = '\n'.join(lines).strip()
            
            # Try to parse as JSON
            data = json.loads(cleaned)
            
            # Validate structure
            if 'variations' not in data or not isinstance(data['variations'], list):
                raise ValueError("Missing or invalid 'variations' field")
            
            if 'project' not in data:
                logger.warning("[!] No project in response, using 'general'")
                data['project'] = 'general'
            
            if 'confidence' not in data:
                logger.warning("[!] No confidence in response, using 0.5")
                data['confidence'] = 0.5
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"[X] Failed to parse LLM response as JSON: {e}")
            logger.error(f"[DEBUG] Raw response (first 1000 chars): {response[:1000]}")
            
            # Try to extract variations from text
            return self._extract_from_text(response)
    
    def _extract_from_text(self, response: str) -> Dict[str, Any]:
        """Extract variations from non-JSON response (fallback).
        
        Args:
            response: LLM response text
            
        Returns:
            Dictionary with extracted variations
        """
        # Simple heuristic: look for numbered lines or quotes
        lines = response.split('\n')
        variations = []
        
        for line in lines:
            line = line.strip()
            # Look for numbered lists or quotes
            if line and (
                line[0].isdigit() or 
                line.startswith('-') or 
                line.startswith('*') or
                line.startswith('"')
            ):
                # Clean up
                clean_line = line.lstrip('0123456789.-*" ').rstrip('" ')
                if len(clean_line) > 10:  # Minimum length for valid query
                    variations.append(clean_line)
        
        logger.warning(f"[!] Extracted {len(variations)} variations from text (not JSON)")
        
        return {
            'variations': variations[:self.expansion_config.num_variations],
            'project': 'general',
            'confidence': 0.3  # Low confidence for non-JSON parsing
        }
    
    def _get_fallback_result(self, query: str) -> QueryExpansionResult:
        """Generate fallback result if expansion fails.
        
        Args:
            query: Original query
            
        Returns:
            Fallback QueryExpansionResult with simple variations
        """
        logger.warning("[!] Using fallback query expansion")
        
        # Simple rule-based variations
        variations = [
            query,  # Keep original
            f"What is {query}?",
            f"Explain {query}",
            f"Define {query}",
            query.replace('?', ''),
            query.replace('how', 'what'),
            query.replace('is', 'are'),
            query.lower(),
            query.upper().lower()  # Normalize
        ]
        
        # Remove duplicates and limit
        variations = list(dict.fromkeys(variations))[:self.expansion_config.num_variations]
        
        return QueryExpansionResult(
            original_query=query,
            variations=variations[1:],  # Exclude original from variations
            detected_project='general',
            confidence=0.1,
            all_queries=[]
        )
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query.
        
        Args:
            query: User query
            
        Returns:
            Cache key string
        """
        import hashlib
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def clear_cache(self):
        """Clear expansion cache."""
        self._expansion_cache.clear()
        logger.info("[OK] Query expansion cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'cache_size': len(self._expansion_cache),
            'cache_enabled': self.expansion_config.cache_expansions,
            'cache_ttl': self.expansion_config.cache_ttl
        }
