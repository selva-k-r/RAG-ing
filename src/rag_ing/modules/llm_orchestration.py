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
            "successful_requests": 0
        }
        
        # Initialize the LLM client
        logger.info(f"Initializing LLM orchestration with provider: {self.llm_config.provider}")
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
            import anthropic
            
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
        return '''You are a specialized biomedical assistant with expertise in oncology. Your role is to provide accurate, evidence-based information about cancer diagnosis, treatment, biomarkers, and related medical topics.

Guidelines:
- Always ground your responses in the provided context
- Cite specific sources when making claims
- Use appropriate medical terminology while remaining accessible
- Highlight any limitations or uncertainties in the information
- For clinical questions, emphasize the importance of consulting healthcare professionals
- Include relevant ontology codes (ICD-O, SNOMED-CT) when available

System Instruction: {system_instruction}

Context Information:
{context}

Query: {query}

Response:'''
    
    def generate_response(self, query: str, context: str, 
                         audience: str = "clinical") -> Dict[str, Any]:
        """Generate grounded response using the selected model."""
        start_time = time.time()
        
        try:
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
        """Construct prompt using template and context."""
        if not self.prompt_template:
            self.load_prompt_template()
        
        # Customize system instruction based on audience
        if audience == "clinical":
            system_instruction = ("Focus on clinical relevance, patient safety, and practical "
                                "applications. Use medical terminology appropriate for healthcare professionals.")
        elif audience == "technical":
            system_instruction = ("Focus on technical implementation, system configuration, and "
                                "detailed methodological information.")
        else:
            system_instruction = self.llm_config.system_instruction
        
        # Format the prompt template
        prompt = self.prompt_template.format(
            system_instruction=system_instruction,
            context=context,
            query=query
        )
        
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
        """Invoke Azure OpenAI API."""
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
            logger.error(f"Azure OpenAI invocation failed: {e}")
            raise
    
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
        """Update generation statistics."""
        self._stats["total_requests"] += 1
        self._stats["successful_requests"] += 1
        
        # Update average response time
        total_requests = self._stats["total_requests"]
        prev_avg = self._stats["avg_response_time"]
        self._stats["avg_response_time"] = ((prev_avg * (total_requests - 1)) + response_time) / total_requests
    
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