"""Module 1: Corpus & Embedding Lifecycle

Objective: Ingest documents from multiple sources, generate embeddings, and store them for retrieval.

Implementation of requirements from Requirement.md:
- YAML-Driven Ingestion Logic: Parse data_source.type (confluence/local_file)
- Chunking Strategy: Use recursive or semantic splitter with configured size/overlap
- Embedding Generation: Load PubMedBERT and convert chunks to vectors
- Vector Storage: Use Chroma or FAISS with metadata validation
- Best Practices: Pydantic validation, modular design, comprehensive logging
"""

import logging
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
import chromadb

# Import connectors and utilities
from ..config.settings import Settings
from ..connectors import ConfluenceConnector
from ..utils.exceptions import IngestionError
from ..utils.duplicate_detector import DuplicateDetector
from ..utils.document_summarizer import DocumentSummarizer
from ..utils.code_chunker import CodeChunker
from ..utils.embedding_provider import create_embedding_provider, get_embedding_model

logger = logging.getLogger(__name__)


class CorpusEmbeddingModule:
    """Module for YAML-driven document ingestion and embedding generation.
    
    Implements all requirements from Requirement.md Module 1:
    - YAML-driven ingestion for confluence and local_file sources
    - Recursive and semantic chunking strategies
    - PubMedBERT embedding model loading
    - Chroma/FAISS vector storage with validation
    - Comprehensive statistics logging
    """
    
    def __init__(self, config: Settings):
        """Initialize corpus embedding module."""
        self.config = config
        self.data_source_config = config.data_source
        self.chunking_config = config.chunking
        self.embedding_config = config.embedding_model
        self.vector_store_config = config.vector_store
        
        # Initialize duplicate detector
        if config.duplicate_detection.enabled:
            db_path = config.duplicate_detection.storage.get('database_path', './vector_store/document_hashes.db')
            self.duplicate_detector = DuplicateDetector(
                config=config.duplicate_detection.dict(),
                db_path=db_path
            )
            logger.info("Duplicate detection enabled")
        else:
            self.duplicate_detector = None
            logger.info("Duplicate detection disabled")
        
        # Initialize hierarchical storage
        self.hierarchical_config = config.hierarchical_storage
        if self.hierarchical_config.enabled:
            self.summary_vector_store = None  # Separate store for summaries
            self.document_summarizer = None  # Will be initialized when LLM client is provided
            logger.info("Hierarchical storage enabled")
        else:
            self.summary_vector_store = None
            self.document_summarizer = None
        
        # Initialize state
        self.embedding_model = None
        self.vector_store = None  # For detailed chunks
        self._stats = {
            "chunk_count": 0,
            "summary_count": 0,
            "vector_size": 0,
            "processing_time": 0,
            "documents_processed": 0,
            "duplicates_skipped": 0,
            "ontology_codes_extracted": 0
        }
        
        logger.info(f"CorpusEmbeddingModule initialized - Data source: {self.data_source_config.type}")
    
    def set_llm_client(self, llm_client: Any) -> None:
        """Set LLM client for document summarization.
        
        Args:
            llm_client: LLM client from LLMOrchestrationModule
        """
        if self.hierarchical_config.enabled:
            summarizer_config = {
                'model': self.config.llm.model,
                'max_summary_length': 500,
                'max_keywords': 15
            }
            self.document_summarizer = DocumentSummarizer(llm_client, summarizer_config)
            logger.info(f"[OK] DocumentSummarizer initialized with {self.config.llm.model}")
    
    def process_corpus(self) -> Dict[str, Any]:
        """Enhanced main entry point supporting multi-source corpus processing.
        
        Educational note: This method demonstrates the Template Method pattern -
        the overall algorithm stays the same, but individual steps are enhanced
        to support multiple data sources.
        
        Implements enhanced workflow:
        1. Multi-Source YAML-Driven Ingestion Logic  
        2. Chunking Strategy 
        3. Embedding Generation
        4. Vector Storage
        5. Validation of embeddings
        
        Returns:
            Dict containing comprehensive processing statistics
        """
        logger.info("Starting enhanced multi-source corpus processing pipeline")
        start_time = time.time()
        
        # Initialize universal ingestion tracker (SQLite)
        from ..utils.ingestion_tracker_sqlite import IngestionTrackerSQLite
        self._ingestion_tracker = IngestionTrackerSQLite(db_path="ingestion_tracking.db")
        
        # Get statistics
        stats = self._ingestion_tracker.get_statistics()
        logger.info(f" Loaded tracking database: {stats.get('total_documents', 0)} documents, {stats.get('total_chunks', 0)} chunks")
        
        try:
            # Step 1: Enhanced Multi-Source Ingestion Logic
            logger.info(" Step 1: Multi-source document ingestion")
            documents = self._ingest_documents_multi_source()
            self._stats["documents_processed"] = len(documents)
            logger.info(f"Ingested {len(documents)} documents from multiple sources")
            
            # Step 2: Chunking Strategy  
            logger.info(" Step 2: Document chunking")
            chunks = self._chunk_documents(documents)
            self._stats["chunk_count"] = len(chunks)
            logger.info(f"Created {len(chunks)} chunks using {self.chunking_config.strategy} strategy")
            
            # Step 3: Embedding Generation
            logger.info(" Step 3: Loading embedding model")
            self._load_embedding_model()
            
            # Step 4: Vector Storage
            logger.info("Step 4: Setting up vector store and storing embeddings")
            self._setup_vector_store()
            self._store_embeddings(chunks)
            
            # Step 5: Validate embeddings
            logger.info("Step 5: Validating embedding model (test API call only)")
            logger.info("Note: This tests if embedding API is accessible, NOT processing documents")
            validation_success = self.validate_embeddings()
            
            # Calculate final statistics
            processing_time = time.time() - start_time
            self._stats.update({
                "processing_time": processing_time,
                "validation_success": validation_success,
                "sources_processed": len(self.data_source_config.get_enabled_sources()),
                "embedding_model": self.embedding_config.name,
                "vector_store_type": self.vector_store_config.type
            })
            
            # Enhanced logging with multi-source breakdown - CLEAR STATUS
            docs_count = self._stats['documents_processed']
            chunks_count = self._stats['chunk_count']
            duplicates_skipped = self._stats.get('duplicates_skipped', 0)
            
            # Get total documents already in database
            existing_docs_count = 0
            existing_chunks_count = 0
            if hasattr(self, '_ingestion_tracker'):
                stats = self._ingestion_tracker.get_statistics()
                existing_docs_count = stats.get('total_documents', 0)
                existing_chunks_count = stats.get('total_chunks', 0)
            
            if docs_count == 0:
                if duplicates_skipped > 0 or existing_docs_count > 0:
                    # All documents were duplicates - system already has content
                    logger.info(f"\n{'='*80}")
                    logger.info(f"CORPUS PROCESSING COMPLETED - NO NEW DOCUMENTS TO PROCESS")
                    logger.info(f"{'='*80}")
                    logger.info(f"Documents already processed: {existing_docs_count}")
                    logger.info(f"Chunks already available: {existing_chunks_count}")
                    logger.info(f"Duplicates skipped this run: {duplicates_skipped}")
                    logger.info(f"Processing time: {processing_time:.2f}s")
                    logger.info(f"\n✓ SYSTEM READY - All documents already indexed and searchable")
                    logger.info(f"✓ No new content to store - incremental ingestion working correctly")
                    logger.info(f"\nTo re-ingest all files, delete: ingestion_tracking.db and vector_store/")
                    logger.info(f"{'='*80}\n")
                else:
                    # No documents found at all - this is a problem
                    logger.warning(f"\n{'='*80}")
                    logger.warning(f"CORPUS PROCESSING COMPLETED BUT NO DOCUMENTS FOUND")
                    logger.warning(f"{'='*80}")
                    logger.warning(f"Sources enabled: {self._stats.get('sources_processed', 0)}")
                    logger.warning(f"Documents fetched: 0")
                    logger.warning(f"Chunks created: 0")
                    logger.warning(f"Processing time: {processing_time:.2f}s")
                    logger.warning(f"\nNOTHING TO SEARCH - No documents available for queries")
                    logger.warning(f"Check source configurations and error logs above")
                    logger.warning(f"{'='*80}\n")
            elif chunks_count == 0:
                logger.warning(f"\n{'='*80}")
                logger.warning(f"DOCUMENTS FETCHED BUT NO CHUNKS CREATED")
                logger.warning(f"{'='*80}")
                logger.warning(f"Documents fetched: {docs_count}")
                logger.warning(f"Chunks created: 0")
                logger.warning(f"\nNOTHING TO SEARCH - Check chunking configuration")
                logger.warning(f"{'='*80}\n")
            else:
                logger.info(f"\n{'='*80}")
                logger.info(f"CORPUS PROCESSING COMPLETED SUCCESSFULLY")
                logger.info(f"{'='*80}")
                logger.info(f"Sources processed: {self._stats.get('sources_processed', 0)}")
                logger.info(f"Documents ingested: {docs_count}")
                logger.info(f"Chunks created: {chunks_count}")
                logger.info(f"Vector dimension: {self._stats.get('vector_size', 'N/A')}")
                logger.info(f"Processing time: {processing_time:.2f}s")
                logger.info(f"\nREADY TO SEARCH - {chunks_count} chunks available for queries")
                logger.info(f"{'='*80}\n")
            
            return self._stats
            
        except Exception as e:
            logger.error(f"Multi-source corpus processing failed: {str(e)}")
            raise IngestionError(f"Failed to process corpus: {str(e)}")
    
    def _ingest_documents_multi_source(self) -> List[Document]:
        """Enhanced multi-source document ingestion.
        
        Educational note: This method shows how to handle multiple data sources
        gracefully, continuing processing even if one source fails.
        """
        all_documents = []
        enabled_sources = self.data_source_config.get_enabled_sources()
        
        logger.info(f" Processing {len(enabled_sources)} enabled data sources")
        
        for source in enabled_sources:
            source_type = source.get('type')
            source_description = source.get('description', f'{source_type} source')
            
            try:
                logger.info(f" Processing {source_description}...")
                
                # Route to appropriate ingestion method based on type
                if source_type == 'local_file':
                    docs = self._ingest_local_files_enhanced(source)
                elif source_type == 'confluence':
                    docs = self._ingest_confluence_enhanced(source)
                elif source_type == 'jira':
                    docs = self._ingest_jira_enhanced(source)
                elif source_type == 'azure_devops':
                    docs = self._ingest_azuredevops_enhanced(source)
                else:
                    logger.warning(f" Unknown source type: {source_type}, skipping...")
                    continue
                
                all_documents.extend(docs)
                logger.info(f"{source_description}: {len(docs)} documents processed")
                
            except Exception as e:
                logger.error(f"Error processing {source_description}: {e}")
                logger.info("Continuing with other sources...")
                continue
        
        if not all_documents:
            # No documents ingested from any source
            logger.warning("No documents ingested from any enabled source")
            return []
        
        return all_documents
        """YAML-driven document ingestion.
        
        Parses data_source.type as required:
        - confluence: authenticate and fetch pages by space key and filter
        - local_file: read from configured path
        """
        data_source_type = self.data_source_config.type
        logger.info(f"Ingesting documents from {data_source_type} source")
        
        if data_source_type == "local_file":
            return self._ingest_local_files()
        elif data_source_type == "confluence":
            return self._ingest_confluence_docs()
        else:
            raise ValueError(f"Unsupported data source type: {data_source_type}")
    
    def _ingest_local_files(self) -> List[Document]:
        """Ingest documents from local file path."""
        path = Path(self.data_source_config.path)
        documents = []
        
        if not path.exists():
            raise FileNotFoundError(f"Data path does not exist: {path}")
        
        logger.info(f"Scanning directory: {path}")
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".txt", ".md", ".pdf", ".html", ".htm"]:
                try:
                    content = self._extract_file_content(file_path)
                    if content.strip():  # Only process non-empty content
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": str(file_path),
                                "filename": file_path.name,
                                "file_type": file_path.suffix,
                                "date": file_path.stat().st_mtime,
                                "domain": "general"
                            }
                        )
                        documents.append(doc)
                        logger.debug(f"Processed file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to process file {file_path}: {e}")
        
        logger.info(f"Successfully ingested {len(documents)} local files")
        return documents
    
    def _ingest_confluence_docs(self) -> List[Document]:
        """Ingest documents from Confluence with authentication and filtering."""
        confluence_config = self.data_source_config.confluence
        if not confluence_config:
            raise ValueError("Confluence configuration is required for confluence data source")
        
        logger.info(f"Connecting to Confluence: {confluence_config.get('base_url')}")
        connector = ConfluenceConnector(confluence_config)
        
        # Authenticate and connect as required
        if not connector.connect():
            raise ConnectionError("Failed to connect to Confluence")
        
        # Fetch documents with space key and page filters as specified
        documents = connector.fetch_documents(
            space_key=confluence_config.get("space_key"),
            page_filter=confluence_config.get("page_filter", [])
        )
        
        # Enhance metadata with ontology codes as required
        for doc in documents:
            # Extract domain codes if present (medical codes, error codes, etc.)
            domain_codes = self._extract_domain_codes(doc.page_content)
            doc.metadata["domain_codes"] = domain_codes
            doc.metadata["domain"] = "general"
            self._stats["domain_codes_extracted"] += len(domain_codes)
        
        logger.info(f"Successfully ingested {len(documents)} Confluence documents")
        return documents
    
    def _extract_file_content(self, file_path: Path) -> str:
        """Extract content from different file types.
        
        Implements proper PDF extraction using pdfplumber for better text extraction.
        """
        if file_path.suffix in [".txt", ".md"]:
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try alternative encodings
                for encoding in ['latin1', 'cp1252']:
                    try:
                        return file_path.read_text(encoding=encoding)
                    except UnicodeDecodeError:
                        continue
                logger.warning(f"Could not decode file {file_path}")
                return ""
        elif file_path.suffix in [".pdf", ".PDF"]:
            try:
                import pdfplumber
                content_parts = []
                
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            # Extract text with error handling for PDF parsing issues
                            text = page.extract_text()
                            if text:
                                content_parts.append(f"--- Page {page_num} ---\n{text}")
                        except Exception as page_error:
                            logger.warning(f"Failed to extract page {page_num} from {file_path}: {page_error}")
                            # Try alternative extraction method
                            try:
                                # Use crop method to avoid color space issues
                                cropped = page.crop((0, 0, page.width, page.height))
                                text = cropped.extract_text()
                                if text:
                                    content_parts.append(f"--- Page {page_num} (alt method) ---\n{text}")
                            except Exception as alt_error:
                                logger.warning(f"Alternative extraction also failed for page {page_num}: {alt_error}")
                                content_parts.append(f"--- Page {page_num} ---\n[Text extraction failed: {str(page_error)}]")
                
                content = "\n\n".join(content_parts)
                if content.strip():
                    logger.info(f"Successfully extracted {len(content)} characters from PDF: {file_path.name}")
                    return content
                else:
                    logger.warning(f"No text content extracted from PDF: {file_path.name}")
                    return f"PDF file: {file_path.name} - No extractable text content found"
                
            except ImportError:
                logger.error("pdfplumber not installed. Install with: pip install pdfplumber")
                return f"PDF content from {file_path.name} - pdfplumber not available"
            except Exception as e:
                logger.error(f"Failed to extract PDF content from {file_path}: {e}")
                # Fallback to basic file info
                return f"PDF file: {file_path.name} - Size: {file_path.stat().st_size} bytes - Extraction failed due to: {str(e)}"
        elif file_path.suffix in [".html", ".htm"]:
            try:
                from bs4 import BeautifulSoup
                html_content = file_path.read_text(encoding='utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text
            except Exception as e:
                logger.warning(f"Failed to extract HTML content from {file_path}: {e}")
                return file_path.read_text(encoding='utf-8', errors='ignore')
        else:
            return ""
    
    def _extract_domain_codes(self, content: str) -> List[str]:
        """Extract medical ontology codes from content.
        
        Implements extraction for ICD-O, SNOMED-CT, and UMLS as specified
        in requirements. Uses regex patterns for common medical codes.
        """
        ontology_codes = []
        
        # ICD-O codes (International Classification of Diseases for Oncology)
        # Format: C78.0, C50.9, etc.
        icd_o_pattern = r'C\d{2}\.\d'
        ontology_codes.extend(re.findall(icd_o_pattern, content, re.IGNORECASE))
        
        # SNOMED-CT codes (Systematized Nomenclature of Medicine Clinical Terms)
        # Format: SNOMED: 123456789 or SNOMED-CT: 123456789
        snomed_pattern = r'SNOMED(?:-CT)?[:\s]+(\d{6,})'
        ontology_codes.extend(re.findall(snomed_pattern, content, re.IGNORECASE))
        
        # MeSH terms (Medical Subject Headings) - basic detection
        mesh_pattern = r'MeSH[:\s]+([A-Z]\d{2}\.[A-Z0-9\.]+)'
        ontology_codes.extend(re.findall(mesh_pattern, content, re.IGNORECASE))
        
        # Additional oncology-specific patterns
        # Cancer staging: TNM classification
        tnm_pattern = r'T[0-4]N[0-3]M[0-1]'
        ontology_codes.extend(re.findall(tnm_pattern, content, re.IGNORECASE))
        
        # Remove duplicates and return
        return list(set([code for code in ontology_codes if code.strip()]))
    
    def _process_document_batch(self, batch: List[Document]) -> None:
        """
        Process a batch of documents immediately: chunk, embed, and store.
        
        This enables streaming/incremental ingestion where batches are processed
        as they're fetched, providing faster feedback and fault tolerance.
        
        Args:
            batch: List of documents to process
        """
        if not batch:
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f" BATCH PROCESSING: {len(batch)} documents")
        logger.info(f"{'='*80}")
        start_time = time.time()
        
        # Log files in this batch
        logger.info(f"\n STAGE 1/4: DOCUMENTS FETCHED")
        for i, doc in enumerate(batch[:5], 1):  # Show first 5
            title = doc.metadata.get('title', 'unknown')
            language = doc.metadata.get('language', 'unknown')
            lines = doc.metadata.get('total_lines', 0)
            commits = doc.metadata.get('commit_count', 0)
            logger.info(f"   {i}. {title} ({language}, {lines} lines, {commits} commits)")
        if len(batch) > 5:
            logger.info(f"   ... and {len(batch) - 5} more files")
        
        try:
            # Step 1: Chunk documents
            chunks = self._chunk_documents(batch)
            logger.info(f"   Chunked into {len(chunks)} chunks")
            
            # Step 2: Store in vector DB (which handles embedding internally)
            self._store_embeddings(chunks)
            logger.info(f"   Stored {len(chunks)} chunks in vector store")
            
            # Step 3: Record in tracking database
            # Build document_chunks_map for tracking
            document_chunks_map = {}
            for doc in batch:
                metadata = doc.metadata
                key = (
                    'azure_devops',
                    metadata.get('file_path'),
                    metadata.get('repository'),
                    metadata.get('branch')
                )
                # Find chunks for this document
                doc_chunks = [c for c in chunks if c.metadata.get('file_path') == metadata.get('file_path')]
                document_chunks_map[key] = {
                    'chunks': doc_chunks,
                    'metadata': metadata
                }
            
            self._record_processed_documents(document_chunks_map)
            
            elapsed = time.time() - start_time
            logger.info(f"   Batch processed in {elapsed:.1f}s ({len(batch)} docs -> {len(chunks)} chunks)")
            
        except Exception as e:
            logger.error(f"   Batch processing failed: {e}")
            raise
    
    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Apply chunking strategy based on configuration.
        
        Supports recursive and semantic strategies as required:
        - recursive: RecursiveCharacterTextSplitter with configured size/overlap
        - semantic: Preserve semantic boundaries for structured content
        """
        strategy = self.chunking_config.strategy
        logger.info(f"Applying {strategy} chunking strategy")
        
        if strategy == "recursive":
            return self._recursive_chunking(documents)
        elif strategy == "semantic":
            return self._semantic_chunking(documents)
        else:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")
    
    def _recursive_chunking(self, documents: List[Document]) -> List[Document]:
        """Apply recursive character-based chunking with configured parameters.
        
        Uses code-aware chunking for Azure DevOps files to preserve structure
        and add line number metadata for citations.
        """
        chunks = []
        code_chunker = CodeChunker(
            chunk_size=self.chunking_config.chunk_size,
            overlap=self.chunking_config.overlap
        )
        
        for doc in documents:
            # Check if this is a code file from Azure DevOps
            is_code_file = (
                doc.metadata.get('type') == 'azure_devops_file' and
                doc.metadata.get('is_code', False)
            )
            
            if is_code_file:
                # Use code-aware chunking with line numbers
                logger.debug(f"Using code chunking for {doc.metadata.get('file_path')}")
                code_chunks = code_chunker.chunk_code_file(doc.page_content, doc.metadata)
                chunks.extend(code_chunks)
            else:
                # Standard recursive chunking for non-code documents
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunking_config.chunk_size,
                    chunk_overlap=self.chunking_config.overlap,
                    separators=["\n\n", "\n", ". ", " ", ""],
                    keep_separator=True
                )
                
                doc_chunks = text_splitter.split_documents([doc])
                
                # Enhance chunk metadata
                for i, chunk in enumerate(doc_chunks):
                    chunk.metadata.update({
                        "chunk_index": i,
                        "chunk_method": "recursive",
                        "chunk_size": len(chunk.page_content)
                    })
                
                chunks.extend(doc_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def _semantic_chunking(self, documents: List[Document]) -> List[Document]:
        """Apply semantic boundary-aware chunking for oncology content.
        
        Preserves semantic boundaries as specified in requirements.
        Uses medical section boundaries for better context preservation.
        """
        chunks = []
        
        # Define oncology-specific semantic boundaries
        semantic_boundaries = [
            "## Diagnosis", "## Treatment", "## Biomarkers", "## Prognosis",
            "DIAGNOSIS:", "TREATMENT:", "FINDINGS:", "CONCLUSION:",
            "Abstract", "Introduction", "Methods", "Results", "Discussion"
        ]
        
        for doc in documents:
            content = doc.page_content
            
            # Split by semantic boundaries first
            sections = [content]
            for boundary in semantic_boundaries:
                new_sections = []
                for section in sections:
                    parts = section.split(boundary)
                    if len(parts) > 1:
                        # Keep the boundary with the content
                        new_sections.append(parts[0])
                        for part in parts[1:]:
                            new_sections.append(boundary + part)
                    else:
                        new_sections.append(section)
                sections = [s.strip() for s in new_sections if s.strip()]
            
            # Apply size-based chunking within sections if needed
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunking_config.chunk_size,
                chunk_overlap=self.chunking_config.overlap
            )
            
            for i, section in enumerate(sections):
                if len(section) > self.chunking_config.chunk_size:
                    # Further split large sections
                    section_chunks = text_splitter.split_text(section)
                    for j, chunk_text in enumerate(section_chunks):
                        chunk = Document(
                            page_content=chunk_text,
                            metadata={
                                **doc.metadata,
                                "chunk_id": f"{doc.metadata.get('source', 'unknown')}_{i}_{j}",
                                "section_id": i,
                                "chunk_method": "semantic",
                                "chunk_size": len(chunk_text)
                            }
                        )
                        chunks.append(chunk)
                else:
                    chunk = Document(
                        page_content=section,
                        metadata={
                            **doc.metadata,
                            "chunk_id": f"{doc.metadata.get('source', 'unknown')}_{i}",
                            "section_id": i,
                            "chunk_method": "semantic",
                            "chunk_size": len(section)
                        }
                    )
                    chunks.append(chunk)
        
        return chunks
    
    def _load_embedding_model(self) -> None:
        """Setup embedding model using unified provider system.
        
        Supports Azure OpenAI, local open-source models, and hybrid mode.
        Configuration is driven by config.yaml embedding_model section.
        
        Educational note: This uses the unified embedding provider which handles:
        - Provider switching (Azure OpenAI / Local / Hybrid)
        - Rate limiting for Azure OpenAI
        - Automatic fallback on errors
        - Performance tracking
        """
        logger.info("Setting up embedding model")
        
        try:
            # Create embedding provider from config
            # Extract azure_openai config
            azure_config = getattr(self.embedding_config, 'azure_openai', None)
            if azure_config:
                azure_dict = {
                    'model': azure_config.model,
                    'endpoint': azure_config.endpoint or self.config.azure_openai_embedding_endpoint or self.config.azure_openai_endpoint,
                    'api_key': azure_config.api_key or self.config.azure_openai_embedding_api_key or self.config.azure_openai_api_key,
                    'api_version': azure_config.api_version or self.config.azure_openai_embedding_api_version,
                    'deployment_name': azure_config.deployment_name,
                    'max_retries': azure_config.max_retries,
                    'retry_delay': azure_config.retry_delay,
                    'requests_per_minute': azure_config.requests_per_minute
                }
            else:
                # Fallback to legacy fields
                azure_dict = {
                    'model': self.embedding_config.azure_model,
                    'endpoint': self.config.azure_openai_embedding_endpoint or self.config.azure_openai_endpoint,
                    'api_key': self.config.azure_openai_embedding_api_key or self.config.azure_openai_api_key,
                    'api_version': self.config.azure_openai_embedding_api_version,
                    'deployment_name': self.embedding_config.azure_deployment_name,
                    'max_retries': 5,
                    'retry_delay': 2,
                    'requests_per_minute': 60
                }
            
            # Extract local config
            local_config = getattr(self.embedding_config, 'local', None)
            local_dict = local_config.model_dump() if local_config else {
                'model_name': 'BAAI/bge-large-en-v1.5',
                'device': getattr(self.embedding_config, 'device', 'cpu'),
                'batch_size': 32,
                'normalize_embeddings': True
            }
            
            # Extract hybrid config
            hybrid_config = getattr(self.embedding_config, 'hybrid', None)
            hybrid_dict = hybrid_config.model_dump() if hybrid_config else {}
            
            embedding_config_dict = {
                'provider': self.embedding_config.provider,
                'azure_openai': azure_dict,
                'local': local_dict,
                'hybrid': hybrid_dict
            }
            
            # Create unified provider
            self.embedding_model = get_embedding_model(embedding_config_dict)
            self.embedding_provider = create_embedding_provider(embedding_config_dict)
            
            # Test the model with a sample text
            test_embedding = self.embedding_model.embed_query("document embedding test")
            self._stats["vector_size"] = len(test_embedding)
            
            logger.info(f"[OK] Embedding model initialized")
            logger.info(f"     Provider: {self.embedding_provider.get_provider_name()}")
            logger.info(f"     Vector dimension: {len(test_embedding)}")
            
        except Exception as e:
            logger.error(f"[X] Failed to setup embedding model: {e}")
            logger.error(f"     Provider: {self.embedding_config.provider}")
            import traceback
            logger.error(f"     Traceback: {traceback.format_exc()}")
            raise IngestionError(f"Embedding model setup failed: {e}")
    
    def _load_azure_embedding_model(self) -> None:
        """DEPRECATED: This method is kept for backward compatibility.
        Use the unified embedding provider in _load_embedding_model() instead.
        """
        logger.warning("[!] _load_azure_embedding_model() is deprecated")
        logger.warning("    Using unified embedding provider system instead")
        # Fallback to unified system
        self._load_embedding_model()
    
    def _load_open_source_embedding_model(self) -> None:
        """DEPRECATED: This method is kept for backward compatibility.
        Use the unified embedding provider in _load_embedding_model() instead.
        """
        logger.warning("[!] _load_open_source_embedding_model() is deprecated")
        logger.warning("    Using unified embedding provider system instead")
        # Fallback to unified system
        self._load_embedding_model()
    
    def _setup_vector_store(self) -> None:
        """Setup vector store based on configuration.
        
        Supports Chroma and FAISS as specified in requirements.
        """
        store_type = self.vector_store_config.type
        logger.info(f"Setting up {store_type} vector store")
        
        if store_type == "chroma":
            self._setup_chroma_store()
        elif store_type == "faiss":
            self._setup_faiss_store()
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
    
    def _setup_chroma_store(self) -> None:
        """Setup ChromaDB vector store with persistent storage."""
        persist_directory = self.vector_store_config.path
        collection_name = self.vector_store_config.collection_name
        
        # Ensure directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(path=persist_directory)
            
            self.vector_store = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embedding_model
            )
            
            logger.info(f"ChromaDB vector store initialized at {persist_directory}")
            
            # Setup hierarchical storage with dual collections
            if self.hierarchical_config.enabled:
                self._setup_hierarchical_chroma()
            
        except Exception as e:
            logger.error(f"Failed to setup ChromaDB: {e}")
            raise IngestionError(f"ChromaDB setup failed: {e}")
    
    def _setup_hierarchical_chroma(self) -> None:
        """Setup dual ChromaDB collections for hierarchical storage."""
        try:
            persist_directory = Path(self.vector_store_config.path) / "summaries"
            persist_directory.mkdir(parents=True, exist_ok=True)
            
            # Create summary collection
            client = chromadb.PersistentClient(path=str(persist_directory))
            summary_collection = self.hierarchical_config.summary_collection
            
            self.summary_vector_store = Chroma(
                client=client,
                collection_name=summary_collection,
                embedding_function=self.embedding_model
            )
            
            logger.info(f"Hierarchical storage: Summary collection '{summary_collection}' initialized")
            
        except Exception as e:
            logger.warning(f"Failed to setup hierarchical storage: {e}. Continuing with single collection.")
            self.summary_vector_store = None
    
    def _store_hierarchical(self, chunks: List[Document]) -> None:
        """Store documents in hierarchical format with rich summaries.
        
        Groups chunks by source document, creates LLM-generated summaries with metadata,
        stores both summaries and chunks.
        """
        logger.info("Storing in hierarchical format with rich summaries...")
        
        # Group chunks by source document
        doc_groups = {}
        for chunk in chunks:
            doc_id = chunk.metadata.get('source', 'unknown')
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk)
        
        logger.info(f"Grouped {len(chunks)} chunks into {len(doc_groups)} documents")
        
        # Create summaries for each document group
        summaries = []
        
        if self.document_summarizer:
            # Use LLM-based summarization for rich metadata
            logger.info("Generating rich summaries with LLM...")
            
            for doc_id, doc_chunks in doc_groups.items():
                try:
                    # Combine chunks into full document
                    full_text = "\n\n".join([c.page_content for c in doc_chunks])
                    full_doc = Document(
                        page_content=full_text,
                        metadata=doc_chunks[0].metadata  # Use metadata from first chunk
                    )
                    
                    # Generate rich summary with metadata using DocumentSummarizer
                    summary_list = self.document_summarizer.create_summary_documents([full_doc])
                    
                    if summary_list:
                        summary_doc = summary_list[0]
                        # Add chunk linking
                        summary_doc.metadata['chunk_count'] = len(doc_chunks)
                        summary_doc.metadata['chunk_ids'] = ', '.join([
                            c.metadata.get('chunk_id', f'chunk_{i}') 
                            for i, c in enumerate(doc_chunks)
                        ])
                        summaries.append(summary_doc)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate summary for {doc_id}: {e}. Using fallback.")
                    # Fallback to simple summary
                    summaries.append(self._create_simple_summary(full_text, doc_chunks[0].metadata, len(doc_chunks)))
            
            logger.info(f"[OK] Generated {len(summaries)} rich summaries")
        else:
            # Fallback: Use simple summarization (truncation)
            logger.warning("DocumentSummarizer not available. Using simple truncation fallback.")
            
            for doc_id, doc_chunks in doc_groups.items():
                full_text = "\n\n".join([c.page_content for c in doc_chunks])
                summaries.append(self._create_simple_summary(full_text, doc_chunks[0].metadata, len(doc_chunks)))
            
            logger.info(f"Created {len(summaries)} simple summaries (fallback method)")
        
        # Store summaries in summary collection
        try:
            cleaned_summaries = self._clean_metadata_for_chroma(summaries)
            self.summary_vector_store.add_documents(cleaned_summaries)
            self._stats["summary_count"] += len(summaries)
            logger.info(f"[OK] Stored {len(summaries)} summaries in '{self.hierarchical_config.summary_collection}'")
        except Exception as e:
            logger.error(f"[X] Failed to store summaries: {e}")
        
        # Store detailed chunks in main collection
        try:
            cleaned_chunks = self._clean_metadata_for_chroma(chunks)
            self.vector_store.add_documents(cleaned_chunks)
            self._stats["chunk_count"] += len(chunks)
            logger.info(f"[OK] Stored {len(chunks)} detailed chunks in '{self.vector_store_config.collection_name}'")
        except Exception as e:
            logger.error(f"[X] Failed to store chunks: {e}")
    
    def _create_simple_summary(self, full_text: str, metadata: Dict, chunk_count: int) -> Document:
        """Create simple fallback summary when LLM is not available."""
        summary = full_text[:300]
        if len(full_text) > 300:
            summary += "..."
        
        return Document(
            page_content=summary,
            metadata={
                **metadata,
                "is_summary": True,
                "chunk_count": chunk_count,
                "summary_method": "simple_truncation"
            }
        )
    
    def _clean_metadata_for_chroma(self, docs: List[Document]) -> List[Document]:
        """Clean metadata for ChromaDB compatibility."""
        cleaned = []
        for doc in docs:
            cleaned_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, list):
                    cleaned_metadata[key] = ", ".join(str(v) for v in value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    cleaned_metadata[key] = value
                else:
                    cleaned_metadata[key] = str(value)
            cleaned.append(Document(page_content=doc.page_content, metadata=cleaned_metadata))
        return cleaned
    
    # =============================================================================
    # FAISS VECTOR STORE - OPTIONAL PRODUCTION SCALING FEATURE
    # =============================================================================
    # STATUS: Available but not currently used (config.yaml set to "chroma")
    #
    # WHEN TO USE FAISS:
    #   - Document corpus > 50,000 documents
    #   - Query latency requirement < 10ms
    #   - Production deployment with high QPS (queries per second)
    #   - Need specialized indices (IVF, HNSW, PQ for compression)
    #
    # WHEN TO USE CHROMADB (CURRENT DEFAULT):
    #   - Document corpus < 50,000 documents
    #   - PoC/Development phase (current status)
    #   - Need persistent storage with minimal setup
    #   - Metadata filtering is primary use case
    #
    # TO SWITCH TO FAISS:
    #   1. Change config.yaml: vector_store.type = "faiss"
    #   2. Re-run corpus ingestion to build FAISS index
    #   3. Index saved to: ./vector_store/faiss_index/
    #
    # PERFORMANCE COMPARISON:
    #   - ChromaDB: ~50ms query time, persistent, easy setup
    #   - FAISS: ~5-10ms query time, requires save/load, production-grade
    #
    # MAINTAINED FOR: Future production scaling when corpus grows beyond 50K docs
    # =============================================================================
    
    def _setup_faiss_store(self) -> None:
        """Setup FAISS vector store."""
        # FAISS will be initialized when first documents are added
        self.vector_store = None
        logger.info("FAISS vector store will be initialized on first document addition")
    
    def _delete_old_vectors(self, source_type: str, document_id: str, source_location: str, source_branch: str) -> int:
        """Delete old vectors for a document being updated.
        
        Args:
            source_type: Source type (azure_devops, confluence, etc.)
            document_id: Document identifier
            source_location: Source location
            source_branch: Branch/version
            
        Returns:
            Number of vectors deleted
        """
        if self.vector_store_config.type != "chroma":
            logger.warning("Vector cleanup only supported for ChromaDB")
            return 0
        
        try:
            # Build query based on source type
            if source_type == 'azure_devops':
                query_filter = {
                    "$and": [
                        {"file_path": document_id},
                        {"repository": source_location},
                        {"branch": source_branch}
                    ]
                }
            elif source_type == 'confluence':
                query_filter = {
                    "$and": [
                        {"page_id": document_id},
                        {"space_key": source_location}
                    ]
                }
            elif source_type == 'local_file':
                query_filter = {"source": document_id}
            else:
                # Generic fallback
                query_filter = {"source": document_id}
            
            # Query for existing chunks matching this document
            results = self.vector_store._collection.get(where=query_filter)
            
            if results and results['ids']:
                # Delete matching vectors
                self.vector_store._collection.delete(ids=results['ids'])
                deleted_count = len(results['ids'])
                logger.info(f"Deleted {deleted_count} old vectors for [{source_type}]: {document_id}")
                return deleted_count
            
            return 0
        
        except Exception as e:
            logger.warning(f"Failed to delete old vectors for [{source_type}]: {document_id}: {e}")
            return 0
    
    def _store_embeddings(self, chunks: List[Document]) -> None:
        """Store document chunks with embeddings in vector store.
        
        Handles:
        - Cleanup of old vectors for updated files
        - Recording processed files in tracker
        - Hierarchical storage if enabled
        """
        if not chunks:
            logger.warning("No chunks to store")
            return
        
        logger.info(f"Storing {len(chunks)} chunks with embeddings")
        
        # Group chunks by source document for cleanup and tracking
        document_chunks_map = {}
        for chunk in chunks:
            metadata = chunk.metadata
            
            # Determine source type and identifiers (check both 'type' and 'source_type' for compatibility)
            doc_type = metadata.get('type') or metadata.get('source_type')
            
            if doc_type == 'azure_devops_file' or doc_type == 'azure_devops':
                source_type = 'azure_devops'
                document_id = metadata.get('file_path', metadata.get('source'))
                source_location = metadata.get('repository', 'unknown')
                source_branch = metadata.get('branch', '')
            elif doc_type == 'confluence':
                source_type = 'confluence'
                document_id = metadata.get('page_id', metadata.get('source'))
                source_location = metadata.get('space_key', '')
                source_branch = ''
            elif doc_type == 'local_file':
                source_type = 'local_file'
                document_id = metadata.get('source', metadata.get('filename', 'unknown'))
                source_location = 'local'
                source_branch = ''
            else:
                # Skip unknown types
                logger.debug(f"Skipping chunk with unknown type: {doc_type}")
                continue
            
            key = (source_type, document_id, source_location, source_branch)
            if key not in document_chunks_map:
                document_chunks_map[key] = {
                    'chunks': [],
                    'needs_cleanup': metadata.get('needs_vector_cleanup', False),
                    'metadata': metadata
                }
            document_chunks_map[key]['chunks'].append(chunk)
        
        # Handle vector cleanup for updated documents
        total_deleted = 0
        for (source_type, document_id, source_location, source_branch), doc_data in document_chunks_map.items():
            if doc_data['needs_cleanup']:
                deleted = self._delete_old_vectors(source_type, document_id, source_location, source_branch)
                total_deleted += deleted
        
        if total_deleted > 0:
            logger.info(f"Cleaned up {total_deleted} old vectors for updated documents")
        
        # Handle hierarchical storage first
        if self.hierarchical_config.enabled and self.summary_vector_store:
            self._store_hierarchical(chunks)
            # Record in tracker after successful storage
            self._record_processed_documents(document_chunks_map)
            return
        
        try:
            if self.vector_store_config.type == "chroma":
                # Clean metadata for ChromaDB compatibility (no lists, complex objects)
                cleaned_chunks = []
                for chunk in chunks:
                    cleaned_metadata = {}
                    for key, value in chunk.metadata.items():
                        if isinstance(value, list):
                            # Convert lists to comma-separated strings
                            cleaned_metadata[key] = ", ".join(str(v) for v in value)
                        elif isinstance(value, (str, int, float, bool)) or value is None:
                            cleaned_metadata[key] = value
                        else:
                            # Convert complex objects to strings
                            cleaned_metadata[key] = str(value)
                    
                    cleaned_chunk = Document(page_content=chunk.page_content, metadata=cleaned_metadata)
                    cleaned_chunks.append(cleaned_chunk)
                
                # Add documents to ChromaDB
                self.vector_store.add_documents(cleaned_chunks)
                
            elif self.vector_store_config.type == "faiss":
                # Create FAISS index from documents
                self.vector_store = FAISS.from_documents(chunks, self.embedding_model)
                
                # Save FAISS index to disk
                index_path = Path(self.vector_store_config.path) / "faiss_index"
                index_path.parent.mkdir(parents=True, exist_ok=True)
                self.vector_store.save_local(str(index_path))
            
            logger.info(f"Successfully stored {len(chunks)} chunks in {self.vector_store_config.type}")
            
            # Record processed documents in tracker after successful storage
            self._record_processed_documents(document_chunks_map)
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise IngestionError(f"Vector storage failed: {e}")
    
    def _record_processed_documents(self, document_chunks_map: Dict) -> None:
        """Record processed documents in universal ingestion tracker.
        
        Supports all source types: Azure DevOps, Confluence, local files, Jira.
        
        Args:
            document_chunks_map: Map of document info to chunks and metadata
        """
        if not hasattr(self, '_ingestion_tracker'):
            logger.warning("Ingestion tracker not initialized - skipping recording")
            return
        
        tracker = self._ingestion_tracker
        
        for (source_type, document_id, source_location, source_branch), doc_data in document_chunks_map.items():
            metadata = doc_data['metadata']
            chunk_count = len(doc_data['chunks'])
            
            # Get the original document content for hash computation
            # Use first chunk's full content or reconstruct
            content = '\n'.join(chunk.page_content for chunk in doc_data['chunks'])
            
            # Get document title
            document_title = metadata.get('title', metadata.get('filename', document_id))
            
            tracker.record_processed_document(
                source_type=source_type,
                document_id=document_id,
                source_location=source_location,
                source_branch=source_branch,
                content=content,
                chunk_count=chunk_count,
                last_modified_date=metadata.get('last_modified_date'),
                last_modified_by=metadata.get('last_modified_by'),
                document_title=document_title,
                status='success'
            )
        
        # Save tracker to CSV
        tracker.save()
        logger.info(f"Updated tracking file for {len(document_chunks_map)} documents")
    
    def validate_embeddings(self) -> bool:
        """Validate vector dimensions and schema as required by Requirement.md.
        
        Tests embedding generation and validates vector dimensions.
        This implements the specific requirement: "Validate vector dimensions and schema"
        """
        if not self.vector_store or not self.embedding_model:
            logger.error("Vector store or embedding model not initialized for validation")
            return False
        
        try:
            # Test embedding generation with oncology-specific content
            test_texts = [
                "Oncology biomarker analysis for breast cancer",
                "Melanoma treatment protocol with immunotherapy",
                "BRCA1 gene mutation screening results"
            ]
            
            for test_text in test_texts:
                test_embedding = self.embedding_model.embed_query(test_text)
                
                # Validate vector dimensions
                expected_dim = 768  # Standard for BERT-based models
                actual_dim = len(test_embedding)
                
                if actual_dim != expected_dim and expected_dim not in [384, 512, 768, 1024]:
                    logger.warning(f"Unexpected embedding dimension: {actual_dim}")
                
                # Validate vector values (should be normalized)
                if not all(-1.0 <= val <= 1.0 for val in test_embedding):
                    logger.warning("Embedding values outside expected range [-1, 1]")
            
            self._stats["vector_size"] = len(test_embedding)
            logger.info(f"   Embedding API validated: {len(test_embedding)}D vectors (test call successful)")
            logger.info(f"   Note: This was a validation test, NOT embedding of your documents")
            return True
            
        except Exception as e:
            logger.error(f"Embedding validation failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics as required by best practices."""
        return self._stats.copy()
    
    def get_vector_store(self):
        """Get the initialized vector store."""
        return self.vector_store
    
    def get_corpus_status(self) -> Dict[str, Any]:
        """Get current corpus status for system monitoring."""
        return {
            "stats": self.get_stats(),
            "vector_store_initialized": self.vector_store is not None,
            "embedding_model_loaded": self.embedding_model is not None,
            "data_source_type": self.data_source_config.type,
            "data_source_path": self.data_source_config.path,
            "chunking_strategy": self.chunking_config.strategy,
            "embedding_model_name": self.embedding_config.name,
            "enabled_sources": len(self.data_source_config.get_enabled_sources())
        }
    
    # Enhanced multi-source ingestion methods
    
    def _ingest_local_files_enhanced(self, source_config: Dict[str, Any]) -> List[Document]:
        """Enhanced local file ingestion with source-specific configuration.
        
        Educational note: This method shows how to handle source-specific
        configuration while maintaining the same interface.
        """
        path = Path(source_config.get('path', './data/'))
        file_types = source_config.get('file_types', ['.txt', '.md', '.pdf', '.docx', '.html'])
        documents = []
        
        if not path.exists():
            logger.warning(f" Local path does not exist: {path}")
            return documents
        
        logger.info(f" Scanning local directory: {path}")
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in file_types:
                try:
                    content = self._extract_file_content(file_path)
                    if not content.strip():
                        continue
                    
                    # Check for duplicates
                    if self.duplicate_detector:
                        if self.duplicate_detector.is_exact_duplicate(content):
                            logger.debug(f"Skipping duplicate: {file_path.name}")
                            self._stats["duplicates_skipped"] += 1
                            continue
                    
                    # Create document
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "type": "local_file",  # Standardized field name
                            "source_type": "local_file",  # Keep for backward compatibility
                            "filename": file_path.name,
                            "file_type": file_path.suffix,
                            "date": file_path.stat().st_mtime,
                            "domain": "general",
                            "description": source_config.get('description', 'Local file'),
                            "title": file_path.name  # For tracking
                        }
                    )
                    documents.append(doc)
                    
                    # Mark as processed for future duplicate checks
                    if self.duplicate_detector:
                        self.duplicate_detector.mark_as_processed(
                            content,
                            {"source": str(file_path), "source_url": str(file_path.absolute())}
                        )
                    
                    logger.debug(f"Processed: {file_path.name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")
        
        # Log results
        if self.duplicate_detector and self._stats["duplicates_skipped"] > 0:
            logger.info(f" Local files: {len(documents)} documents processed, {self._stats['duplicates_skipped']} duplicates skipped")
        else:
            logger.info(f" Local files: {len(documents)} documents processed")
        return documents
    
    def _ingest_confluence_enhanced(self, source_config: Dict[str, Any]) -> List[Document]:
        """Enhanced Confluence ingestion with multiple space support.
        
        Educational note: This method demonstrates how to handle external API
        integration with proper error handling and configuration management.
        """
        confluence_config = source_config.get('confluence', {})
        
        # Check if Confluence is properly configured
        required_fields = ['base_url', 'username', 'auth_token']
        missing_fields = [field for field in required_fields if not confluence_config.get(field)]
        
        if missing_fields:
            logger.warning(f" Confluence config missing fields: {missing_fields}")
            return []
        
        try:
            # Initialize Confluence connector
            connector = ConfluenceConnector(confluence_config)
            
            # Process multiple spaces if configured
            space_keys = confluence_config.get('space_keys', [confluence_config.get('space_key', 'DOCS')])
            max_pages = confluence_config.get('max_pages', 100)
            page_filter = confluence_config.get('page_filter', [])
            
            all_docs = []
            for space_key in space_keys:
                logger.info(f" Processing Confluence space: {space_key}")
                docs = connector.fetch_pages(space_key, max_pages, page_filter)
                
                # Add source metadata
                for doc in docs:
                    doc.metadata.update({
                        "source_type": "confluence",
                        "space_key": space_key,
                        "description": source_config.get('description', f'Confluence {space_key}')
                    })
                
                all_docs.extend(docs)
                logger.info(f"Space {space_key}: {len(docs)} pages processed")
            
            logger.info(f" Confluence total: {len(all_docs)} documents processed")
            return all_docs
            
        except Exception as e:
            logger.error(f"Confluence ingestion failed: {e}")
            return []
    
    def _ingest_jira_enhanced(self, source_config: Dict[str, Any]) -> List[Document]:
        """
        JIRA ingestion - NOT IMPLEMENTED (Placeholder for future)
        
        TODO: Implement when JIRA integration is required
        
        Implementation steps:
        1. Create JiraConnector class in src/rag_ing/connectors/jira_connector.py
           - Similar to ConfluenceConnector architecture
           - Use JIRA REST API (https://developer.atlassian.com/server/jira/platform/rest-apis/)
        
        2. Required functionality:
           - Authenticate with JIRA API (OAuth, basic auth, or API token)
           - Fetch issues using JQL queries from config
           - Extract content from:
             * Issue descriptions
             * Comments
             * Custom fields
             * Attachments (if needed)
           - Map issue metadata (status, priority, assignee, labels) to document metadata
        
        3. Configuration (already in config.yaml):
           - server_url: JIRA instance URL
           - username: Authentication username
           - auth_token: API token or password
           - project_keys: List of project keys to ingest
           - issue_types: Types of issues to include
           - jql_filter: Custom JQL query for filtering
        
        4. Similar to Confluence pattern:
           - Return List[Document] with metadata
           - Handle pagination for large result sets
           - Include error handling and logging
        
        For now, this returns empty list to avoid breaking multi-source ingestion.
        """
        jira_config = source_config.get('jira', {})
        
        # Check JIRA configuration
        required_fields = ['server_url', 'username', 'auth_token']
        missing_fields = [field for field in required_fields if not jira_config.get(field)]
        
        if missing_fields:
            logger.debug(f" JIRA config incomplete (missing: {missing_fields}) - skipping")
            return []
        
        # Placeholder - not implemented
        logger.info("JIRA ingestion requested but not yet implemented - skipping")
        logger.debug("See docstring for implementation steps")
        return []
    
    def _ingest_azuredevops_enhanced(self, source_config: Dict[str, Any]) -> List[Document]:
        """Enhanced Azure DevOps ingestion with incremental processing and change tracking.
        
        Features:
        - Tracks processed files in CSV for incremental ingestion
        - Only processes new or modified files
        - Deletes old vectors when files are updated
        - Records processing metadata (who, when, commit info)
        """
        azuredevops_config = source_config.get('azure_devops', {})
        
        # Check if Azure DevOps is properly configured
        required_fields = ['organization', 'project', 'pat_token']
        missing_fields = [field for field in required_fields if not azuredevops_config.get(field)]
        
        if missing_fields:
            logger.warning(f" Azure DevOps config missing fields: {missing_fields}")
            return []
        
        try:
            # Initialize Azure DevOps connector
            from ..connectors.azuredevops_connector import AzureDevOpsConnector
            
            connector = AzureDevOpsConnector(azuredevops_config)
            connector.connect()
            
            # Use the global ingestion tracker
            tracker = self._ingestion_tracker
            
            # Get repository configuration
            repo_name = azuredevops_config.get('repo_name')
            branch = azuredevops_config.get('branch', 'main')
            include_paths = azuredevops_config.get('include_paths', ['/'])
            enable_streaming = azuredevops_config.get('enable_streaming', False)
            batch_size = azuredevops_config.get('batch_size', 50)
            
            all_docs = []
            files_processed = 0
            files_skipped = 0
            files_updated = 0
            files_with_commit_history = 0
            total_commits_fetched = 0
            
            # Fetch files from repository
            if repo_name:
                if enable_streaming:
                    logger.info(f" Streaming from Azure DevOps repository: {repo_name} (batch size: {batch_size})")
                    
                    # CRITICAL FIX: Initialize embedding model and vector store BEFORE streaming
                    # Without this, _process_document_batch() fails with NoneType error
                    if not self.embedding_model:
                        logger.info("Initializing embedding model for streaming mode...")
                        self._load_embedding_model()
                    
                    if not self.vector_store:
                        logger.info("Initializing vector store for streaming mode...")
                        self._setup_vector_store()
                    
                    # STREAMING MODE: Process batches as they come in
                    for path in include_paths:
                        batch_num = 0
                        for batch in connector.fetch_repository_files_streaming(
                            repo_name=repo_name,
                            branch=branch,
                            path=path,
                            recursive=True,
                            include_commit_info=True,
                            batch_size=batch_size
                        ):
                            batch_num += 1
                            logger.info(f" Processing batch #{batch_num} ({len(batch)} files)")
                            
                            # Process this batch immediately
                            batch_docs_to_process = []
                            for doc in batch:
                                metadata = doc.metadata
                                file_path = metadata.get('file_path')
                                repository = metadata.get('repository')
                                branch_name = metadata.get('branch')
                                content = doc.page_content
                                last_modified = metadata.get('last_modified_date')
                                
                                # Compute content hash
                                import hashlib
                                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                                
                                # Check if needs processing
                                should_process, reason = tracker.needs_processing(
                                    source_type='azure_devops',
                                    document_id=file_path,
                                    content_hash=content_hash,
                                    last_modified_date=last_modified
                                )
                                
                                if should_process:
                                    # Check if update or new
                                    existing_doc = tracker.get_document_status('azure_devops', file_path)
                                    is_update = existing_doc is not None
                                    
                                    if is_update:
                                        logger.info(f" Updating: {file_path} (reason: {reason})")
                                        files_updated += 1
                                        doc.metadata['needs_vector_cleanup'] = True
                                    else:
                                        logger.debug(f" New file: {file_path}")
                                        files_processed += 1
                                    
                                    # Track commit history
                                    if metadata.get('commit_history'):
                                        files_with_commit_history += 1
                                        total_commits_fetched += len(metadata['commit_history'])
                                    
                                    batch_docs_to_process.append(doc)
                                else:
                                    files_skipped += 1
                            
                            # PROCESS THIS BATCH NOW (chunk + embed + store)
                            if batch_docs_to_process:
                                logger.info(f"Chunk+Embed+Store batch #{batch_num}: {len(batch_docs_to_process)} files")
                                self._process_document_batch(batch_docs_to_process)
                            
                            all_docs.extend(batch_docs_to_process)
                else:
                    logger.info(f" Fetching from Azure DevOps repository: {repo_name} (non-streaming mode)")
                    # ORIGINAL MODE: Fetch all first, then process
                    for path in include_paths:
                        raw_docs = connector.fetch_repository_files(
                            repo_name=repo_name,
                            branch=branch,
                            path=path,
                            recursive=True,
                            include_commit_info=True
                        )
                    
                    # Filter based on tracking status
                    for doc in raw_docs:
                        metadata = doc.metadata
                        file_path = metadata.get('file_path')
                        repository = metadata.get('repository')
                        branch_name = metadata.get('branch')
                        content = doc.page_content
                        last_modified = metadata.get('last_modified_date')
                        
                        # Check if file needs processing
                        # Compute content hash for change detection
                        import hashlib
                        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                        
                        should_process, reason = tracker.needs_processing(
                            source_type='azure_devops',
                            document_id=file_path,
                            content_hash=content_hash,
                            last_modified_date=last_modified
                        )
                        
                        if should_process:
                            # Check if this is an update (existing document) or new
                            existing_doc = tracker.get_document_status('azure_devops', file_path)
                            is_update = existing_doc is not None
                            
                            if is_update:
                                logger.info(f" Updating: {file_path} (reason: {reason})")
                                files_updated += 1
                                # Mark for vector cleanup (existing vectors need to be removed)
                                doc.metadata['needs_vector_cleanup'] = True
                            else:
                                logger.debug(f" New file: {file_path}")
                                files_processed += 1
                            
                            # Track commit history stats
                            if metadata.get('commit_history'):
                                files_with_commit_history += 1
                                total_commits_fetched += len(metadata['commit_history'])
                            
                            all_docs.append(doc)
                        else:
                            files_skipped += 1
                    
                    logger.info(f"    {path}: {len(raw_docs)} files found, {len([d for d in all_docs if d.metadata.get('file_path', '').startswith(path)])} to process")
            else:
                # Fetch from all repositories
                repos = connector.list_repositories()
                logger.info(f" Found {len(repos)} repositories in project")
                
                for repo in repos[:5]:  # Limit to first 5 repos
                    repo_name = repo['name']
                    logger.info(f"   Fetching from: {repo_name}")
                    
                    for path in include_paths:
                        raw_docs = connector.fetch_repository_files(
                            repo_name=repo_name,
                            branch=branch,
                            path=path,
                            recursive=True,
                            include_commit_info=True
                        )
                        
                        # Same filtering logic as above
                        for doc in raw_docs:
                            metadata = doc.metadata
                            
                            # Compute content hash for change detection
                            import hashlib
                            content_hash = hashlib.sha256(doc.page_content.encode('utf-8')).hexdigest()
                            
                            should_process, reason = tracker.needs_processing(
                                source_type='azure_devops',
                                document_id=metadata.get('file_path'),
                                content_hash=content_hash,
                                last_modified_date=metadata.get('last_modified_date')
                            )
                            
                            if should_process:
                                # Check if this is an update or new file
                                existing_doc = tracker.get_document_status('azure_devops', metadata.get('file_path'))
                                is_update = existing_doc is not None
                                
                                if is_update:
                                    logger.info(f" Updating: {metadata.get('file_path')} (reason: {reason})")
                                    files_updated += 1
                                    doc.metadata['needs_vector_cleanup'] = True
                                else:
                                    logger.debug(f" New file: {metadata.get('file_path')}")
                                    files_processed += 1
                                
                                # Track commit history stats
                                if metadata.get('commit_history'):
                                    files_with_commit_history += 1
                                    total_commits_fetched += len(metadata['commit_history'])
                                
                                all_docs.append(doc)
                            else:
                                files_skipped += 1
            
            # Log summary with commit history stats
            logger.info(f"Azure DevOps: {len(all_docs)} files to process ({files_processed} new, {files_updated} updated, {files_skipped} skipped)")
            
            if files_with_commit_history > 0:
                avg_commits = total_commits_fetched / files_with_commit_history if files_with_commit_history > 0 else 0
                logger.info(f" Commit History: {files_with_commit_history} files with history ({total_commits_fetched} total commits, avg {avg_commits:.1f} commits/file)")
            
            # ================================================================
            # DBT ARTIFACT DETECTION AND PROCESSING
            # ================================================================
            dbt_docs = self._process_dbt_artifacts(all_docs)
            if dbt_docs:
                logger.info(f"[OK] DBT: Extracted {len(dbt_docs)} additional documents (SQL + seeds)")
                all_docs.extend(dbt_docs)
            
            return all_docs
            
        except Exception as e:
            logger.error(f"Azure DevOps ingestion failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _process_dbt_artifacts(self, documents: List[Document]) -> List[Document]:
        """Detect and process DBT artifacts from fetched documents.
        
        Args:
            documents: List of raw documents fetched from Azure DevOps
            
        Returns:
            List of synthetic DBT documents (models, tests, macros, seeds)
        """
        try:
            from ..utils.dbt_artifacts import DBTArtifactParser
            import tempfile
            import os
            from pathlib import Path
            
            # Step 1: Detect DBT artifacts
            dbt_files = {}
            csv_files = {}
            
            for doc in documents:
                file_path = doc.metadata.get('file_path', '')
                content = doc.page_content
                
                # Collect DBT artifact files
                if file_path.endswith('manifest.json'):
                    dbt_files['manifest.json'] = content
                elif file_path.endswith('catalog.json'):
                    dbt_files['catalog.json'] = content
                elif file_path.endswith('graph_summary.json'):
                    dbt_files['graph_summary.json'] = content
                elif file_path.endswith('dbt_project.yml'):
                    dbt_files['dbt_project.yml'] = content
                
                # Collect seed CSV files
                elif file_path.endswith('.csv') and '/data/' in file_path:
                    # Extract seed name from path
                    csv_files[file_path] = content
            
            # Step 2: Check if DBT project detected
            if 'manifest.json' not in dbt_files or 'dbt_project.yml' not in dbt_files:
                logger.debug("No DBT artifacts detected (need manifest.json + dbt_project.yml)")
                return []
            
            logger.info("[OK] DBT project detected! Processing artifacts...")
            logger.info(f"   Artifacts: {', '.join(dbt_files.keys())}")
            logger.info(f"   Seed CSVs: {len(csv_files)}")
            
            # Step 3: Save artifacts to temp directory
            temp_dir = tempfile.mkdtemp(prefix='dbt_artifacts_')
            try:
                for filename, content in dbt_files.items():
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Step 4: Initialize DBT parser
                parser = DBTArtifactParser(temp_dir)
                
                # Step 5: Extract SQL documents (models, tests, macros)
                sql_documents = parser.extract_sql_documents(include_compiled=True)
                logger.info(f"   SQL documents: {len(sql_documents)}")
                
                # Step 6: Extract seed documents (CSV files)
                seed_documents = parser.extract_seed_documents(csv_files) if csv_files else []
                logger.info(f"   Seed documents: {len(seed_documents)}")
                
                # Step 7: Convert to Langchain Document format
                dbt_docs = []
                
                for sql_doc in sql_documents:
                    doc = Document(
                        page_content=sql_doc['content'],
                        metadata={
                            'source': 'dbt_manifest',
                            'source_type': 'azure_devops',
                            **sql_doc['metadata']
                        }
                    )
                    dbt_docs.append(doc)
                
                for seed_doc in seed_documents:
                    doc = Document(
                        page_content=seed_doc['content'],
                        metadata={
                            'source': 'dbt_seed',
                            'source_type': 'azure_devops',
                            **seed_doc['metadata']
                        }
                    )
                    dbt_docs.append(doc)
                
                return dbt_docs
                
            finally:
                # Cleanup temp directory
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
        
        except Exception as e:
            logger.error(f"DBT processing failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
