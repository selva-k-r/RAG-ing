"""
Generic enhanced RAG response generator for web interface.
This module provides a flexible, domain-agnostic response generation system.
"""

import logging
from typing import Dict, List, Any
from langchain.docstore.document import Document
import re

logger = logging.getLogger(__name__)

class EnhancedResponseGenerator:
    """Generic enhanced response generator that works for any domain and query type."""
    
    def __init__(self):
        # Generic templates that work for any domain
        self.response_templates = {
            'default': {
                'title': '## Search Results',
                'intro': 'Based on the retrieved documents, here\'s what I found:'
            }
        }
    
    def generate_response(self, query: str, docs: List[Document], audience: str = "technical") -> str:
        """Generate enhanced response based on query and retrieved documents - completely generic."""
        
        if not docs:
            return self._generate_no_docs_response(query)
        
        # Combine all content
        all_content = "\n".join([doc.page_content for doc in docs])
        
        # Build generic response structure
        template = self.response_templates['default']
        response_parts = [template['title'], "", template['intro'], ""]
        
        # Extract key information generically
        key_info = self._extract_key_information(all_content, query)
        if key_info:
            response_parts.extend([
                "**Key Information:**"
            ])
            for info in key_info:
                response_parts.append(f"• {info}")
            response_parts.append("")
        
        # Add relevant quotes/excerpts
        relevant_excerpts = self._extract_relevant_excerpts(all_content, query)
        if relevant_excerpts:
            response_parts.extend([
                "**Relevant Details:**"
            ])
            for excerpt in relevant_excerpts:
                response_parts.append(f"• {excerpt}")
            response_parts.append("")
        
        # Add document context
        response_parts.extend(self._add_document_context(docs))
        
        # Add metadata
        response_parts.extend([
            "",
            "---",
            f"*Response generated from {len(docs)} document(s) | Audience: {audience.title()}*"
        ])
        
        return "\n".join(response_parts)
    
    def _extract_key_information(self, content: str, query: str) -> List[str]:
        """Extract key information relevant to any query - completely generic approach."""
        key_info = []
        
        # Split content into sentences
        sentences = self._split_into_sentences(content)
        query_words = set(word.lower() for word in query.split() if len(word) > 2)
        
        # Score sentences based on query word overlap
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.strip()) < 20:  # Skip very short sentences
                continue
                
            sentence_words = set(word.lower() for word in sentence.split())
            overlap_score = len(query_words.intersection(sentence_words))
            
            if overlap_score > 0:
                scored_sentences.append((overlap_score, sentence.strip()))
        
        # Return top scored sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        for score, sentence in scored_sentences[:5]:  # Top 5 relevant sentences
            if sentence and not sentence.endswith('.'):
                sentence += '.'
            key_info.append(sentence)
        
        return key_info
    
    def _extract_relevant_excerpts(self, content: str, query: str) -> List[str]:
        """Extract relevant excerpts using generic text analysis."""
        excerpts = []
        
        # Look for sentences that contain query terms or similar concepts
        sentences = self._split_into_sentences(content)
        query_lower = query.lower()
        
        for sentence in sentences:
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 30:  # Skip very short sentences
                continue
                
            sentence_lower = sentence_clean.lower()
            
            # Check if sentence contains any significant words from query
            query_significant_words = [word for word in query_lower.split() if len(word) > 3]
            if any(word in sentence_lower for word in query_significant_words):
                if sentence_clean and not sentence_clean.endswith('.'):
                    sentence_clean += '.'
                excerpts.append(sentence_clean)
        
        # Return unique excerpts, limited to avoid overwhelming response
        unique_excerpts = []
        for excerpt in excerpts:
            if excerpt not in unique_excerpts:
                unique_excerpts.append(excerpt)
        
        return unique_excerpts[:4]  # Limit to 4 excerpts
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences using generic approach."""
        # Replace newlines with spaces and split on periods
        content_clean = re.sub(r'\s+', ' ', content.replace('\n', ' '))
        sentences = re.split(r'[.!?]+', content_clean)
        return [s.strip() for s in sentences if s.strip()]
    
    def _add_document_context(self, docs: List[Document]) -> List[str]:
        """Add generic document context information."""
        response_parts = []
        
        # Get unique source files
        unique_sources = set()
        for doc in docs:
            source = doc.metadata.get('source', doc.metadata.get('filename', 'Unknown'))
            if source != 'Unknown':
                unique_sources.add(source)
        
        if unique_sources:
            response_parts.extend([
                "**Source Documents:**"
            ])
            for source in sorted(unique_sources):
                # Extract just the filename for cleaner display
                filename = source.split('/')[-1] if '/' in source else source
                response_parts.append(f"• {filename}")
            response_parts.append("")
        
        return response_parts
    
    def _generate_no_docs_response(self, query: str) -> str:
        """Generate response when no documents are found."""
        return f"""## Search Results

I wasn't able to find relevant documents for your query: "{query}"

**Suggestions:**
• Try rephrasing your question with different keywords
• Check for typos in your search terms
• Use more general terms if your query was very specific
• Contact support if you believe this information should be available

**System Status:**
• ✅ Search system is operational
• ✅ Document index is accessible
• ❌ No matching documents found for this query

---
*Search completed - no relevant documents found*"""

# Global instance
enhanced_generator = EnhancedResponseGenerator()