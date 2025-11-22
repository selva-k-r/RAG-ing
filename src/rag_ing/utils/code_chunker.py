"""Code-aware chunking for Azure DevOps files.

Preserves code structure (functions, classes, SQL queries) and tracks line numbers
for precise citation in RAG responses.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class CodeChunker:
    """Intelligent code chunking that preserves structure and line numbers."""
    
    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        """Initialize code chunker.
        
        Args:
            chunk_size: Target characters per chunk (larger for code)
            overlap: Overlap between chunks for context continuity
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_code_file(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Chunk code file preserving structure and adding line numbers.
        
        Args:
            content: Full file content
            metadata: File metadata (file_path, repository, etc.)
            
        Returns:
            List of Document chunks with line number metadata
        """
        file_path = metadata.get('file_path', 'unknown')
        file_type = self._detect_language(file_path)
        
        logger.debug(f"Chunking {file_type} file: {file_path}")
        
        # Route to appropriate chunking strategy
        if file_type == 'python':
            chunks = self._chunk_python(content)
        elif file_type == 'sql':
            chunks = self._chunk_sql(content)
        elif file_type in ['yaml', 'yml']:
            chunks = self._chunk_yaml_macros(content)
        else:
            # Generic code chunking with line awareness
            chunks = self._chunk_generic_code(content)
        
        # Convert to Documents with enhanced metadata
        documents = []
        for chunk_content, start_line, end_line, chunk_type in chunks:
            doc = Document(
                page_content=chunk_content,
                metadata={
                    **metadata,
                    'start_line': start_line,
                    'end_line': end_line,
                    'line_count': end_line - start_line + 1,
                    'chunk_type': chunk_type,
                    'language': file_type,
                    'citation': f"{file_path}:L{start_line}-L{end_line}"
                }
            )
            documents.append(doc)
        
        logger.debug(f"Created {len(documents)} chunks from {file_path}")
        return documents
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = file_path.lower().split('.')[-1]
        
        language_map = {
            'py': 'python',
            'sql': 'sql',
            'yaml': 'yaml',
            'yml': 'yaml',
            'json': 'json',
            'md': 'markdown',
            'txt': 'text',
            'cs': 'csharp',
            'java': 'java'
        }
        
        return language_map.get(ext, 'code')
    
    def _chunk_python(self, content: str) -> List[Tuple[str, int, int, str]]:
        """Chunk Python code by functions, classes, and logical blocks.
        
        Returns:
            List of (content, start_line, end_line, type) tuples
        """
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_start = 1
        chunk_type = 'module'
        
        # Regex patterns for Python structure
        class_pattern = re.compile(r'^class\s+\w+')
        function_pattern = re.compile(r'^def\s+\w+')
        decorator_pattern = re.compile(r'^@\w+')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            
            # Detect class or function definition
            if class_pattern.match(stripped):
                # Save previous chunk if exists
                if current_chunk and len('\n'.join(current_chunk)) > 100:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i,
                        chunk_type
                    ))
                
                # Start new class chunk
                current_chunk = [line]
                current_start = i + 1
                chunk_type = 'class'
                
            elif function_pattern.match(stripped):
                # Check if we should save previous chunk
                if current_chunk and len('\n'.join(current_chunk)) > self.chunk_size:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i,
                        chunk_type
                    ))
                    current_chunk = []
                    current_start = i + 1
                
                current_chunk.append(line)
                chunk_type = 'function'
                
            elif decorator_pattern.match(stripped):
                # Include decorators with their functions
                current_chunk.append(line)
                
            else:
                current_chunk.append(line)
                
                # Check if chunk is getting too large
                if len('\n'.join(current_chunk)) > self.chunk_size:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i + 1,
                        chunk_type
                    ))
                    
                    # Keep overlap lines
                    overlap_lines = min(self.overlap // 50, len(current_chunk))
                    current_chunk = current_chunk[-overlap_lines:]
                    current_start = i + 1 - overlap_lines
            
            i += 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append((
                '\n'.join(current_chunk),
                current_start,
                len(lines),
                chunk_type
            ))
        
        return chunks
    
    def _chunk_sql(self, content: str) -> List[Tuple[str, int, int, str]]:
        """Chunk SQL code by statements, CTEs, and logical blocks.
        
        Preserves:
        - Complete SELECT/INSERT/UPDATE/DELETE statements
        - WITH clauses (CTEs)
        - CREATE statements
        - Comments and documentation
        """
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_start = 1
        in_statement = False
        statement_type = 'sql'
        
        # SQL patterns
        statement_start = re.compile(r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|WITH|ALTER|DROP)', re.IGNORECASE)
        comment_pattern = re.compile(r'^\s*--')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Detect statement start
            if statement_start.match(line):
                # Save previous chunk if it's large enough
                if current_chunk and len('\n'.join(current_chunk)) > self.chunk_size:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i - 1,
                        statement_type
                    ))
                    current_chunk = []
                    current_start = i
                
                in_statement = True
                statement_type = statement_start.match(line).group(1).lower()
            
            current_chunk.append(line)
            
            # Check for statement end (semicolon or GO)
            if stripped.endswith(';') or stripped.upper() == 'GO':
                if len('\n'.join(current_chunk)) > 200:  # Minimum chunk size
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i,
                        statement_type
                    ))
                    current_chunk = []
                    current_start = i + 1
                    in_statement = False
        
        # Add remaining chunk
        if current_chunk:
            chunks.append((
                '\n'.join(current_chunk),
                current_start,
                len(lines),
                statement_type
            ))
        
        return chunks if chunks else [(content, 1, len(lines), 'sql')]
    
    def _chunk_yaml_macros(self, content: str) -> List[Tuple[str, int, int, str]]:
        """Chunk YAML/dbt macro files by top-level keys and macro definitions.
        
        For dbt projects, preserves:
        - Model configurations
        - Macro definitions
        - Test definitions
        """
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_start = 1
        chunk_type = 'config'
        
        # Pattern for dbt macros
        macro_pattern = re.compile(r'{%\s*macro\s+\w+')
        endmacro_pattern = re.compile(r'{%\s*endmacro\s*%}')
        
        in_macro = False
        
        for i, line in enumerate(lines, 1):
            # Detect macro start
            if macro_pattern.search(line):
                # Save previous chunk
                if current_chunk and len('\n'.join(current_chunk)) > 100:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i - 1,
                        chunk_type
                    ))
                    current_chunk = []
                    current_start = i
                
                in_macro = True
                chunk_type = 'macro'
            
            current_chunk.append(line)
            
            # Detect macro end
            if endmacro_pattern.search(line):
                if in_macro:
                    chunks.append((
                        '\n'.join(current_chunk),
                        current_start,
                        i,
                        chunk_type
                    ))
                    current_chunk = []
                    current_start = i + 1
                    in_macro = False
                    chunk_type = 'config'
            
            # Check size limit
            elif not in_macro and len('\n'.join(current_chunk)) > self.chunk_size:
                chunks.append((
                    '\n'.join(current_chunk),
                    current_start,
                    i,
                    chunk_type
                ))
                current_chunk = []
                current_start = i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append((
                '\n'.join(current_chunk),
                current_start,
                len(lines),
                chunk_type
            ))
        
        return chunks if chunks else [(content, 1, len(lines), 'yaml')]
    
    def _chunk_generic_code(self, content: str) -> List[Tuple[str, int, int, str]]:
        """Generic code chunking with line number tracking.
        
        Falls back to simple line-based chunking while preserving structure.
        """
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_start = 1
        
        target_lines = self.chunk_size // 80  # Assume ~80 chars per line
        overlap_lines = self.overlap // 80
        
        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            
            if len(current_chunk) >= target_lines:
                chunks.append((
                    '\n'.join(current_chunk),
                    current_start,
                    i,
                    'code'
                ))
                
                # Keep overlap
                current_chunk = current_chunk[-overlap_lines:] if overlap_lines > 0 else []
                current_start = i - overlap_lines + 1 if overlap_lines > 0 else i + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append((
                '\n'.join(current_chunk),
                current_start,
                len(lines),
                'code'
            ))
        
        return chunks if chunks else [(content, 1, len(lines), 'code')]

