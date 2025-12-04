"""Document summarizer for hierarchical storage.

Creates rich summaries with business context and metadata for fast high-level search.
Detailed chunks are fetched only when summary indicates relevance.

Features:
- Document-type-specific summarization (SQL, PDF, Python, YAML)
- Business context extraction from filename, path, and content
- Keyword and topic generation for searchable metadata
- Links summaries to source documents and chunks
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """Generates rich document summaries with metadata for hierarchical retrieval."""
    
    def __init__(self, llm_client: Any, config: Optional[Dict] = None):
        """Initialize summarizer with LLM client.
        
        Args:
            llm_client: LLM client for generating summaries
            config: Configuration dict for summarization settings
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.max_summary_length = self.config.get('max_summary_length', 500)
        self.max_keywords = self.config.get('max_keywords', 15)
        self.model = self.config.get('model', 'gpt-4')
        logger.info(f"DocumentSummarizer initialized (model: {self.model})")
    
    def summarize_document(self, document: Document) -> Dict[str, Any]:
        """Generate rich summary with metadata for document.
        
        Args:
            document: Document to summarize
            
        Returns:
            Dict containing:
            - summary: Business-friendly summary text
            - keywords: List of searchable keywords
            - topics: Main topics covered
            - document_type: Classification
            - business_context: Business purpose
            - technical_details: Technical information (if applicable)
        """
        try:
            # Determine document type
            file_path = document.metadata.get('source', document.metadata.get('file_path', ''))
            file_type = self._determine_file_type(file_path, document.metadata)
            
            # Generate type-specific summary
            if file_type == 'sql':
                return self._summarize_sql(document)
            elif file_type == 'python':
                return self._summarize_python(document)
            elif file_type == 'yaml':
                return self._summarize_yaml(document)
            elif file_type == 'pdf':
                return self._summarize_pdf(document)
            else:
                return self._summarize_generic(document, file_type)
                
        except Exception as e:
            logger.warning(f"Rich summarization failed: {e}. Using fallback.")
            return self._create_fallback_summary(document)
    
    def _determine_file_type(self, file_path: str, metadata: Dict) -> str:
        """Determine file type from path and metadata."""
        file_path = file_path.lower()
        
        if file_path.endswith('.sql'):
            return 'sql'
        elif file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith(('.yaml', '.yml')):
            return 'yaml'
        elif file_path.endswith('.pdf'):
            return 'pdf'
        elif file_path.endswith(('.md', '.markdown')):
            return 'markdown'
        else:
            return 'generic'
    
    def _extract_path_context(self, file_path: str) -> str:
        """Extract business context from file path."""
        if not file_path:
            return "unknown context"
        
        parts = Path(file_path).parts
        context_parts = []
        
        # Common path patterns
        if 'dbt' in file_path.lower():
            context_parts.append("dbt project")
        if 'staging' in file_path.lower() or 'stg_' in file_path.lower():
            context_parts.append("staging layer")
        if 'models' in file_path.lower():
            context_parts.append("data models")
        if 'fact' in file_path.lower() or 'dim' in file_path.lower():
            context_parts.append("dimensional model")
        
        # Add project/folder names (first few segments)
        for part in parts[:3]:
            if part and part not in ['.', '..', '/']:
                context_parts.append(part)
        
        return ", ".join(context_parts) if context_parts else "project file"
    
    def _summarize_sql(self, document: Document) -> Dict[str, Any]:
        """Summarize SQL file with business logic and data transformation focus."""
        file_path = document.metadata.get('file_path', document.metadata.get('source', ''))
        filename = Path(file_path).name if file_path else 'unknown'
        path_context = self._extract_path_context(file_path)
        content = document.page_content[:3000]  # Limit to avoid token limits
        
        prompt = f"""Analyze this SQL file and provide a comprehensive summary.

**File Information:**
- Filename: {filename}
- Path: {file_path}
- Path Context: {path_context}

**SQL Content:**
```sql
{content}
```

**Instructions:**
Provide a JSON response with these fields:

1. **summary** (200-300 words): Business-friendly description including:
   - What business problem this SQL solves
   - What data transformation or calculation it performs
   - Who uses this (analysts, reports, dashboards, etc.)
   
2. **keywords** (10-15 terms): Searchable keywords including:
   - Business terms (quality measure, claims, members, etc.)
   - Technical terms (staging, fact, dimension, etc.)
   - Model name and variations
   - Acronyms and abbreviations

3. **topics** (3-5 topics): Main subject areas covered

4. **business_context** (2-3 sentences): Why this exists and business value

5. **technical_details** (object with these fields):
   - tables_used: List of source tables
   - key_metrics: List of key calculations/metrics
   - transformations: List of main data transformations

Return ONLY valid JSON, no additional text.
"""
        
        try:
            response = self._call_llm(prompt)
            summary_data = self._parse_llm_response(response)
            
            # Add metadata
            summary_data['document_type'] = 'dbt_sql_model' if 'dbt' in file_path.lower() else 'sql_query'
            summary_data['filename'] = filename
            summary_data['file_path'] = file_path
            
            return summary_data
        except Exception as e:
            logger.error(f"SQL summarization failed for {filename}: {e}")
            return self._create_fallback_summary(document)
    
    def _summarize_python(self, document: Document) -> Dict[str, Any]:
        """Summarize Python file with focus on purpose and functionality."""
        file_path = document.metadata.get('file_path', document.metadata.get('source', ''))
        filename = Path(file_path).name if file_path else 'unknown'
        path_context = self._extract_path_context(file_path)
        content = document.page_content[:3000]
        
        prompt = f"""Analyze this Python file and provide a comprehensive summary.

**File Information:**
- Filename: {filename}
- Path: {file_path}
- Path Context: {path_context}

**Python Content:**
```python
{content}
```

**Instructions:**
Provide JSON with: summary, keywords (10-15 terms), topics (3-5), business_context (2-3 sentences), 
technical_details (main_classes, main_functions, external_dependencies lists).

Return ONLY valid JSON.
"""
        
        try:
            response = self._call_llm(prompt)
            summary_data = self._parse_llm_response(response)
            summary_data['document_type'] = 'python_module'
            summary_data['filename'] = filename
            summary_data['file_path'] = file_path
            return summary_data
        except Exception as e:
            logger.error(f"Python summarization failed for {filename}: {e}")
            return self._create_fallback_summary(document)
    
    def _summarize_yaml(self, document: Document) -> Dict[str, Any]:
        """Summarize YAML configuration file."""
        file_path = document.metadata.get('file_path', document.metadata.get('source', ''))
        filename = Path(file_path).name if file_path else 'unknown'
        content = document.page_content[:2000]
        
        prompt = f"""Analyze this YAML configuration file.

Filename: {filename}
Path: {file_path}

```yaml
{content}
```

Provide JSON with: summary (150-200 words), keywords (8-12 terms), topics (2-4), 
business_context, technical_details (config_type, key_settings, dependencies).

Return ONLY valid JSON.
"""
        
        try:
            response = self._call_llm(prompt)
            summary_data = self._parse_llm_response(response)
            summary_data['document_type'] = 'yaml_config'
            summary_data['filename'] = filename
            summary_data['file_path'] = file_path
            return summary_data
        except Exception as e:
            logger.error(f"YAML summarization failed for {filename}: {e}")
            return self._create_fallback_summary(document)
    
    def _summarize_pdf(self, document: Document) -> Dict[str, Any]:
        """Summarize PDF document with focus on entities and key information."""
        filename = document.metadata.get('filename', document.metadata.get('title', 'unknown'))
        content = document.page_content[:4000]
        
        prompt = f"""Analyze this PDF document.

Filename: {filename}

Content:
{content}

Provide JSON with: summary (200-300 words covering document type, purpose, key entities), 
keywords (15-20 terms including named entities, domain terms), topics (3-6), business_context,
technical_details (document_category, key_entities, sections).

Return ONLY valid JSON.
"""
        
        try:
            response = self._call_llm(prompt)
            summary_data = self._parse_llm_response(response)
            summary_data['document_type'] = 'pdf_document'
            summary_data['filename'] = filename
            return summary_data
        except Exception as e:
            logger.error(f"PDF summarization failed for {filename}: {e}")
            return self._create_fallback_summary(document)
    
    def _summarize_generic(self, document: Document, file_type: str) -> Dict[str, Any]:
        """Generic summarization for unknown file types."""
        filename = document.metadata.get('filename', document.metadata.get('title', 'unknown'))
        content = document.page_content[:3000]
        
        prompt = f"""Analyze this document.

Filename: {filename}
Type: {file_type}

Content:
{content}

Provide JSON with: summary, keywords, topics, business_context.
Return ONLY valid JSON.
"""
        
        try:
            response = self._call_llm(prompt)
            summary_data = self._parse_llm_response(response)
            summary_data['document_type'] = file_type or 'generic_document'
            summary_data['filename'] = filename
            return summary_data
        except Exception as e:
            logger.error(f"Generic summarization failed for {filename}: {e}")
            return self._create_fallback_summary(document)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the given prompt."""
        try:
            if hasattr(self.llm_client, 'chat') and hasattr(self.llm_client.chat, 'completions'):
                # Prepare base parameters
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a technical documentation analyst. Provide accurate, structured summaries in valid JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_completion_tokens": 1500
                }
                
                # Some models (like gpt-5-nano) don't support custom temperature
                # Try with temperature first, fallback without it
                try:
                    response = self.llm_client.chat.completions.create(**params, temperature=0.3)
                    return response.choices[0].message.content
                except Exception as e:
                    if "temperature" in str(e).lower() or "unsupported" in str(e).lower():
                        logger.debug(f"Temperature not supported, using default")
                        response = self.llm_client.chat.completions.create(**params)
                        return response.choices[0].message.content
                    else:
                        raise
            else:
                raise ValueError("LLM client does not support chat completions")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response into structured dict."""
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*$', '', response)
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response[:200]}")
            raise
    
    def _create_fallback_summary(self, document: Document) -> Dict[str, Any]:
        """Create basic fallback summary when LLM summarization fails."""
        content = document.page_content
        metadata = document.metadata
        filename = metadata.get('filename', metadata.get('title', metadata.get('file_path', 'unknown')))
        
        # Extract basic keywords from content
        words = re.findall(r'\b[a-z_]{3,}\b', content.lower())
        word_freq = {}
        for word in words:
            if word not in ['and', 'the', 'for', 'with', 'from', 'this', 'that', 'are', 'have']:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        keywords = [word for word, _ in top_keywords]
        
        # Get file path if available
        file_path = metadata.get('file_path', metadata.get('source', ''))
        file_type = self._determine_file_type(file_path, metadata)
        
        return {
            'summary': f"Document: {filename}. Content: {content[:200].strip()}...",
            'keywords': keywords,
            'topics': [file_type, 'document'],
            'business_context': f"Document file: {filename}",
            'technical_details': {'method': 'fallback'},
            'document_type': file_type,
            'filename': filename,
            'file_path': file_path
        }
    

    
    def create_summary_documents(
        self, 
        documents: List[Document],
        batch_size: int = 5
    ) -> List[Document]:
        """Create summary documents with rich metadata for hierarchical retrieval.
        
        Args:
            documents: List of documents to summarize
            batch_size: Process in batches (for logging, no rate limiting needed with batch calls)
            
        Returns:
            List of summary documents with metadata linking to originals
        """
        summary_docs = []
        
        logger.info(f"Starting summarization of {len(documents)} documents")
        
        for i, doc in enumerate(documents):
            try:
                # Generate rich summary with metadata
                summary_data = self.summarize_document(doc)
                
                # Create summary text for embedding
                summary_text = self._format_summary_text(summary_data)
                
                # Create summary document with enhanced metadata
                summary_doc = Document(
                    page_content=summary_text,
                    metadata={
                        # Core identification
                        'is_summary': True,
                        'original_doc_id': doc.metadata.get('source', f'doc_{i}'),
                        'filename': summary_data.get('filename', 'unknown'),
                        'file_path': summary_data.get('file_path', ''),
                        'document_type': summary_data.get('document_type', 'generic'),
                        
                        # Searchable metadata
                        'keywords': ', '.join(summary_data.get('keywords', [])),
                        'topics': ', '.join(summary_data.get('topics', [])),
                        'business_context': summary_data.get('business_context', ''),
                        'document_summary': summary_data.get('summary', ''),
                        
                        # Technical details (flattened)
                        **self._flatten_technical_details(summary_data.get('technical_details', {})),
                        
                        # Preserve original metadata selectively
                        'source_type': doc.metadata.get('source_type', 'unknown'),
                        'chunk_index': doc.metadata.get('chunk_index', 0),
                    }
                )
                
                summary_docs.append(summary_doc)
                
                # Log progress
                if (i + 1) % batch_size == 0:
                    logger.info(f"[OK] Summarized {i + 1}/{len(documents)} documents")
                    
            except Exception as e:
                logger.error(f"[X] Failed to summarize document {i} ({doc.metadata.get('source', 'unknown')}): {e}")
                continue
        
        logger.info(f"[OK] Created {len(summary_docs)} summaries from {len(documents)} documents")
        return summary_docs
    
    def _format_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data into text for embedding."""
        parts = []
        
        # Header
        parts.append(f"Document: {summary_data.get('filename', 'Unknown')}")
        parts.append(f"Type: {summary_data.get('document_type', 'Unknown')}")
        parts.append("")
        
        # Summary
        if summary_data.get('summary'):
            parts.append("Summary:")
            parts.append(summary_data['summary'])
            parts.append("")
        
        # Business context
        if summary_data.get('business_context'):
            parts.append("Business Context:")
            parts.append(summary_data['business_context'])
            parts.append("")
        
        # Keywords and topics
        if summary_data.get('keywords'):
            parts.append(f"Keywords: {', '.join(summary_data['keywords'])}")
        if summary_data.get('topics'):
            parts.append(f"Topics: {', '.join(summary_data['topics'])}")
        
        return "\n".join(parts)
    
    def _flatten_technical_details(self, tech_details: Dict) -> Dict[str, str]:
        """Flatten technical details dict for ChromaDB metadata (only strings allowed)."""
        flattened = {}
        
        for key, value in tech_details.items():
            if isinstance(value, list):
                flattened[f'tech_{key}'] = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                # Skip nested dicts for now
                continue
            else:
                flattened[f'tech_{key}'] = str(value)
        
        return flattened




