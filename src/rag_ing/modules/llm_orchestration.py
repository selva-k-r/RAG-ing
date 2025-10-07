"""Module 3: LLM Orchestration

Objective: Generate grounded response using selected model.
"""

import logging
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from ..config.settings import Settings, LLMConfig
from ..utils.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMOrchestrationModule:
    """Module for YAML-driven LLM model loading and response generation."""
    
    def __init__(self, config: Settings):
        self.config = config
        self.llm_config = config.llm
        self.client = None
        self.prompt_template = None
        self._stats = {
            "total_requests": 0,
            "avg_response_time": 0,
            "total_tokens_used": 0,
            "successful_requests": 0,
            "reasoning_tokens_used": 0,  # GPT-4o nano specific
            "smart_truncation_applied": 0,
            "context_optimization_applied": 0,
            "medical_disclaimers_added": 0
        }
        
        # Initialize the LLM client
        logger.info(f"Initializing LLM orchestration with provider: {self.llm_config.provider}")
        logger.info(f"Model: {self.llm_config.model} | Max tokens: {self.llm_config.max_tokens}")
        logger.info(f"Smart truncation: {self.llm_config.use_smart_truncation} | Context optimization: {self.llm_config.context_optimization}")
        
        if not self.initialize_model():
            logger.warning("LLM client initialization failed, will attempt lazy initialization")
    
    def initialize_model(self) -> bool:
        """Initialize the LLM model based on configuration."""
        provider = self.llm_config.provider
        
        try:
            logger.info(f"Initializing LLM provider: {provider}")
            
            if provider == "koboldcpp":
                return self._initialize_koboldcpp()
            elif provider == "openai":
                return self._initialize_openai()
            elif provider == "azure_openai":
                return self._initialize_azure_openai()
            elif provider == "anthropic":
                return self._initialize_anthropic()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return False
    
    def _initialize_koboldcpp(self) -> bool:
        """Initialize KoboldCpp client."""
        try:
            # Test connection to KoboldCpp server
            response = requests.get(
                f"{self.llm_config.api_url}/model", 
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Connected to KoboldCpp at {self.llm_config.api_url}")
                self.client = "koboldcpp"
                return True
            else:
                logger.error(f"KoboldCpp server returned status {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to connect to KoboldCpp server: {e}")
            return False
    
    def _initialize_openai(self) -> bool:
        """Initialize OpenAI client."""
        try:
            # Import and initialize OpenAI client
            from openai import OpenAI
            
            api_key = self.config.get_api_key("openai")
            if not api_key:
                raise ValueError("OpenAI API key not found")
            
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            return False
    
    def _initialize_azure_openai(self) -> bool:
        """Initialize Azure OpenAI client."""
        try:
            # Import and initialize Azure OpenAI client
            from openai import AzureOpenAI
            
            api_key = self.config.get_api_key("azure_openai")
            endpoint = self.config.azure_openai_endpoint
            api_version = self.config.azure_openai_api_version
            
            logger.info(f"Azure OpenAI initialization attempt:")
            logger.info(f"  API Key: {'*' * (len(api_key) if api_key else 0) if api_key else 'None'}")
            logger.info(f"  Endpoint: {endpoint}")
            logger.info(f"  API Version: {api_version}")
            
            if not api_key:
                raise ValueError("Azure OpenAI API key not found")
            if not endpoint:
                raise ValueError("Azure OpenAI endpoint not found")
            
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version
            )
            logger.info("Azure OpenAI client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    def _initialize_anthropic(self) -> bool:
        """Initialize Anthropic client."""
        try:
            # Import and initialize Anthropic client
            try:
                import anthropic
            except ImportError:
                logger.error("Anthropic package not installed. Install with: pip install anthropic")
                return False
            
            api_key = self.config.get_api_key("anthropic")
            if not api_key:
                raise ValueError("Anthropic API key not found")
            
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("Anthropic client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            return False
    
    def load_prompt_template(self) -> str:
        """Load prompt template from configured path."""
        template_path = Path(self.llm_config.prompt_template)
        
        if not template_path.exists():
            # Create default oncology template if none exists
            template_path.parent.mkdir(parents=True, exist_ok=True)
            default_template = self._get_default_oncology_template()
            template_path.write_text(default_template)
            logger.info(f"Created default prompt template at {template_path}")
        
        self.prompt_template = template_path.read_text(encoding='utf-8')
        logger.info(f"Loaded prompt template from {template_path}")
        return self.prompt_template
    
    def _get_default_oncology_template(self) -> str:
        """Get default oncology-focused prompt template."""
        return '''Context Information:
{context}

Query: {query}

Please provide a clear, direct answer based on the context above.'''
    
    def generate_response(self, query: str, context: str, 
                         audience: str = "clinical") -> Dict[str, Any]:
        """Generate grounded response using the selected model."""
        start_time = time.time()
        
        try:
            # Store audience for use in invocation
            self._current_audience = audience
            
            # Step 1: Construct prompt
            prompt = self._construct_prompt(query, context, audience)
            
            # Step 2: Invoke model
            response = self._invoke_model(prompt)
            
            # Step 3: Parse response
            parsed_response = self._parse_response(response)
            
            # Update statistics
            response_time = time.time() - start_time
            self._update_stats(response_time, len(response))
            
            logger.info(f"Generated response in {response_time:.2f}s")
            
            return {
                "response": parsed_response,
                "query": query,
                "audience": audience,
                "model": self.llm_config.model,
                "provider": self.llm_config.provider,
                "metadata": {
                    "response_time": response_time,
                    "model_config": self.llm_config.dict(),
                    "prompt_length": len(prompt),
                    "response_length": len(response)
                }
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            raise LLMError(f"Failed to generate response: {e}")
    
    def _construct_prompt(self, query: str, context: str, audience: str) -> str:
        """Construct prompt using template and context with smart truncation for GPT-4o nano."""
        if not self.prompt_template:
            self.load_prompt_template()
        
        # Apply smart context truncation for GPT-4o nano's 12K token limit
        if self.llm_config.use_smart_truncation and self.llm_config.max_tokens >= 10000:
            context = self._apply_smart_context_truncation(context, query, audience)
        
        # Format the prompt template (only context and query now)
        prompt = self.prompt_template.format(
            context=context,
            query=query
        )
        
        # Final token management check
        if self.llm_config.context_optimization:
            prompt = self._optimize_context_for_model(prompt, query, audience)
        
        return prompt
    
    def _apply_smart_context_truncation(self, context: str, query: str, audience: str) -> str:
        """Apply smart context truncation optimized for GPT-4o nano's 12K context window."""
        logger.debug("Applying smart context truncation for GPT-4o nano")
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        max_context_tokens = self.llm_config.max_tokens - self.llm_config.token_buffer
        max_context_chars = max_context_tokens * 4
        
        if len(context) <= max_context_chars:
            logger.debug(f"Context fits within limits: {len(context)} chars")
            return context
        
        logger.info(f"Context too long ({len(context)} chars), applying smart truncation")
        
        # Split context into documents/chunks
        documents = self._extract_documents_from_context(context)
        
        # Apply relevance scoring for truncation
        scored_docs = self._score_documents_for_relevance(documents, query, audience)
        
        # Build truncated context prioritizing most relevant content
        truncated_context = self._build_truncated_context(scored_docs, max_context_chars)
        
        logger.info(f"Context truncated: {len(context)} -> {len(truncated_context)} chars")
        return truncated_context
    
    def _extract_documents_from_context(self, context: str) -> list:
        """Extract individual documents from context string."""
        # Simple approach: split by common document separators
        separators = ["---", "Document:", "Source:", "===", "###"]
        
        # Try to split by separators
        documents = []
        current_doc = context
        
        for separator in separators:
            if separator in current_doc:
                docs = current_doc.split(separator)
                documents = [doc.strip() for doc in docs if doc.strip()]
                break
        
        # If no separators found, treat as single document
        if not documents:
            documents = [context]
        
        return documents
    
    def _score_documents_for_relevance(self, documents: list, query: str, audience: str) -> list:
        """Score documents by relevance for smart truncation."""
        query_terms = set(query.lower().split())
        
        # Medical terms get higher weight for clinical audience
        medical_terms = {
            'cancer', 'oncology', 'tumor', 'chemotherapy', 'radiation', 'immunotherapy',
            'metastasis', 'carcinoma', 'lymphoma', 'leukemia', 'biopsy', 'malignant',
            'benign', 'staging', 'prognosis', 'diagnosis', 'treatment', 'therapy',
            'clinical', 'patient', 'medical', 'healthcare', 'disease', 'symptom'
        }
        
        # Technical terms get higher weight for technical audience
        technical_terms = {
            'configuration', 'setup', 'database', 'server', 'deployment', 'api',
            'integration', 'system', 'architecture', 'implementation', 'framework',
            'protocol', 'authentication', 'endpoint', 'middleware', 'repository'
        }
        
        scored_docs = []
        for doc in documents:
            doc_lower = doc.lower()
            score = 0.0
            
            # Query term matching
            for term in query_terms:
                score += doc_lower.count(term) * 2.0
            
            # Audience-specific term boosting
            if audience == "clinical":
                for term in medical_terms:
                    score += doc_lower.count(term) * 1.5
            elif audience == "technical":
                for term in technical_terms:
                    score += doc_lower.count(term) * 1.5
            
            # Document length penalty (prefer concise, relevant docs)
            length_penalty = len(doc) / 10000  # Penalty for very long docs
            score = max(0, score - length_penalty)
            
            scored_docs.append((doc, score))
        
        # Sort by relevance score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        logger.debug(f"Scored {len(scored_docs)} documents for relevance")
        
        return scored_docs
    
    def _build_truncated_context(self, scored_docs: list, max_chars: int) -> str:
        """Build truncated context from highest-scoring documents."""
        truncated_context = ""
        remaining_chars = max_chars
        
        for doc, score in scored_docs:
            # Reserve space for document separator
            separator = "\n\n--- Document ---\n"
            needed_chars = len(doc) + len(separator)
            
            if needed_chars <= remaining_chars:
                # Include full document
                truncated_context += separator + doc
                remaining_chars -= needed_chars
            else:
                # Include partial document if there's significant space left
                if remaining_chars > 500:  # Only if we have substantial space
                    partial_doc = doc[:remaining_chars - len(separator) - 20] + "...[truncated]"
                    truncated_context += separator + partial_doc
                break
        
        return truncated_context.strip()
    
    def _optimize_context_for_model(self, prompt: str, query: str, audience: str) -> str:
        """Apply final context optimization for the specific model."""
        logger.debug("Applying model-specific context optimization")
        
        # For GPT-4o nano, optimize for medical reasoning if applicable
        if "nano" in self.llm_config.model.lower():
            # Add reasoning prompt hints for medical queries
            if audience == "clinical" or any(term in query.lower() for term in 
                                           ['cancer', 'treatment', 'therapy', 'medical', 'clinical']):
                optimization_prefix = """[Medical Context Analysis Required]
The following information requires careful medical reasoning. Consider:
- Clinical evidence and safety implications
- Biomedical mechanisms and pathways  
- Patient safety and contraindications
- Evidence quality and limitations

"""
                prompt = optimization_prefix + prompt
        
        # Final token count check
        estimated_tokens = len(prompt) // 4
        max_allowed = self.llm_config.max_tokens - self.llm_config.token_buffer
        
        if estimated_tokens > max_allowed:
            logger.warning(f"Prompt still too long ({estimated_tokens} tokens), applying final truncation")
            # Emergency truncation - keep query and essential context
            lines = prompt.split('\n')
            truncated_lines = []
            current_tokens = 0
            
            # Always keep the first few lines (system instruction)
            for i, line in enumerate(lines[:10]):
                truncated_lines.append(line)
                current_tokens += len(line) // 4
            
            # Add query at the end
            query_section = f"\n\nQuery: {query}\n\nResponse:"
            truncated_lines.append(query_section)
            
            prompt = '\n'.join(truncated_lines)
        
        logger.debug(f"Final prompt length: {len(prompt)} chars (~{len(prompt)//4} tokens)")
        return prompt
    
    def _invoke_model(self, prompt: str) -> str:
        """Invoke the configured model with retry logic."""
        provider = self.llm_config.provider
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if provider == "koboldcpp":
                    return self._invoke_koboldcpp(prompt)
                elif provider == "openai":
                    return self._invoke_openai(prompt)
                elif provider == "azure_openai":
                    return self._invoke_azure_openai(prompt)
                elif provider == "anthropic":
                    return self._invoke_anthropic(prompt)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Model invocation failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _invoke_koboldcpp(self, prompt: str) -> str:
        """Invoke KoboldCpp API."""
        try:
            payload = {
                "prompt": prompt,
                "max_length": self.llm_config.max_tokens or 512,
                "temperature": self.llm_config.temperature,
                "top_p": 0.9,
                "rep_pen": 1.1,
                "stop_sequence": ["\\n\\nUser:", "\\n\\nQuery:", "\\n\\nHuman:"]
            }
            
            response = requests.post(
                f"{self.llm_config.api_url}/api/v1/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("results", [{}])[0].get("text", "")
            
            if not generated_text:
                raise ValueError("Empty response from KoboldCpp")
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"KoboldCpp invocation failed: {e}")
            raise
    
    def _invoke_openai(self, prompt: str) -> str:
        """Invoke OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens
            )
            
            generated_text = response.choices[0].message.content
            
            # Track token usage
            if hasattr(response, 'usage'):
                self._stats["total_tokens_used"] += response.usage.total_tokens
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"OpenAI invocation failed: {e}")
            raise
    
    def _invoke_azure_openai(self, prompt: str) -> str:
        """Invoke Azure OpenAI API with standard optimization."""
        try:
            logger.info(f"Invoking Azure OpenAI model: {self.llm_config.model}")
            
            # Customize system instruction based on audience
            audience = getattr(self, '_current_audience', 'clinical')
            if audience == "clinical":
                system_instruction = ("You are an AI assistant that provides well-formatted answers using Markdown. "
                                    "Use **bold** for key terms, *italics* for emphasis, tables for data, and bullet points for lists. "
                                    "Focus on clinical relevance and practical applications. "
                                    "Start with a direct answer, then provide supporting details in a structured format.")
            elif audience == "technical":
                system_instruction = ("You are an AI assistant that provides well-formatted answers using Markdown. "
                                    "Use **bold** for key terms, *italics* for emphasis, `code blocks` for technical terms, "
                                    "tables for comparisons, numbered lists for procedures, and Mermaid diagrams for workflows. "
                                    "Focus on technical implementation and system configuration. "
                                    "Start with a direct answer, then provide detailed structured information.")
            else:
                system_instruction = self.llm_config.system_instruction
            
            # Build proper message structure
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
            
            # Standard parameters
            params = {
                "model": self.llm_config.model,
                "messages": messages,
            }
            
            # Handle different token parameter names for different models
            if "nano" in self.llm_config.model.lower():
                params["max_completion_tokens"] = self.llm_config.max_tokens
                # gpt-5-nano only supports temperature = 1.0 (default)
                # Don't add temperature parameter for nano model
            else:
                params["max_tokens"] = self.llm_config.max_tokens
                # Add temperature parameter for standard models
                if self.llm_config.temperature != 1.0:
                    params["temperature"] = self.llm_config.temperature
            
            logger.debug(f"Azure OpenAI request parameters: {params}")
            
            response = self.client.chat.completions.create(**params)
            
            # Standard logging
            logger.info(f"Azure OpenAI response received")
            logger.debug(f"Response structure: {response}")
            
            if response.choices and len(response.choices) > 0:
                logger.debug(f"Response choices: {len(response.choices)}")
                logger.debug(f"First choice message: {response.choices[0].message}")
                logger.debug(f"Finish reason: {response.choices[0].finish_reason}")
            
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"Token usage: {response.usage}")
            
            generated_text = response.choices[0].message.content
            
            # Handle empty responses
            if generated_text is None or generated_text == "":
                logger.warning("Received empty response from Azure OpenAI")
                generated_text = "I apologize, but I wasn't able to generate a response. Please try rephrasing your question."
            
            # Post-process the response for medical context
            generated_text = self._post_process_response(generated_text)
            
            # Track token usage
            if hasattr(response, 'usage'):
                total_tokens = response.usage.total_tokens
                self._stats["total_tokens_used"] += total_tokens
            
            return generated_text.strip() if generated_text else "No response generated."
            
        except Exception as e:
            logger.error(f"Azure OpenAI invocation failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _post_process_response(self, response: str) -> str:
        """Post-process responses for consistency and quality."""
        if not response or response == "No response generated.":
            return response
        
        # Add medical disclaimer for clinical responses
        if any(term in response.lower() for term in ['treatment', 'therapy', 'diagnosis', 'medication', 'clinical']):
            disclaimer = "\n\n⚠️ **Medical Disclaimer**: This information is for educational purposes only and should not replace professional medical advice. Always consult with qualified healthcare professionals for medical decisions."
            
            # Only add if not already present
            if "medical disclaimer" not in response.lower() and "consult" not in response.lower():
                response += disclaimer
        
        # Enhance response structure for better readability
        if len(response) > 500 and response.count('\n') < 3:
            # Add paragraph breaks for long responses without structure
            sentences = response.split('. ')
            structured_response = ""
            sentence_count = 0
            
            for sentence in sentences:
                structured_response += sentence
                if not sentence.endswith('.'):
                    structured_response += '.'
                sentence_count += 1
                
                # Add paragraph break every 3-4 sentences
                if sentence_count % 3 == 0 and sentence != sentences[-1]:
                    structured_response += '\n\n'
                else:
                    structured_response += ' '
            
            response = structured_response.strip()
        
        return response
    def _invoke_anthropic(self, prompt: str) -> str:
        """Invoke Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.llm_config.model,
                max_tokens=self.llm_config.max_tokens or 1024,
                temperature=self.llm_config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            generated_text = response.content[0].text
            
            # Track token usage
            if hasattr(response, 'usage'):
                self._stats["total_tokens_used"] += response.usage.total_tokens
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic invocation failed: {e}")
            raise
    
    def _parse_response(self, response: str) -> str:
        """Parse and clean the model response."""
        # Basic response cleaning
        cleaned_response = response.strip()
        
        # Remove common artifacts
        artifacts = [
            "Assistant:", "AI:", "Response:", "Answer:",
            "Human:", "User:", "Query:"
        ]
        
        for artifact in artifacts:
            if cleaned_response.startswith(artifact):
                cleaned_response = cleaned_response[len(artifact):].strip()
        
        # Ensure response is not empty
        if not cleaned_response:
            raise ValueError("Generated response is empty after parsing")
        
        return cleaned_response
    
    def _update_stats(self, response_time: float, response_length: int) -> None:
        """Update generation statistics with enhanced metrics."""
        self._stats["total_requests"] += 1
        self._stats["successful_requests"] += 1
        
        # Update average response time
        total_requests = self._stats["total_requests"]
        prev_avg = self._stats["avg_response_time"]
        self._stats["avg_response_time"] = ((prev_avg * (total_requests - 1)) + response_time) / total_requests
        
        # Track GPT-4o nano specific features
        if self.llm_config.use_smart_truncation:
            self._stats["smart_truncation_applied"] += 1
        
        if self.llm_config.context_optimization:
            self._stats["context_optimization_applied"] += 1
    
    def test_connection(self) -> bool:
        """Test connection to the configured LLM provider."""
        try:
            if not self.client:
                return self.initialize_model()
            
            # Simple test query
            test_prompt = "Respond with 'OK' if you can process this request."
            response = self._invoke_model(test_prompt)
            
            return "ok" in response.lower()
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "provider": self.llm_config.provider,
            "model": self.llm_config.model,
            "api_url": self.llm_config.api_url if self.llm_config.provider == "koboldcpp" else None,
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens,
            "is_initialized": self.client is not None,
            "prompt_template_path": self.llm_config.prompt_template
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset statistics tracking."""
        self._stats = {
            "total_requests": 0,
            "avg_response_time": 0,
            "total_tokens_used": 0,
            "successful_requests": 0
        }
        logger.info("Statistics reset")