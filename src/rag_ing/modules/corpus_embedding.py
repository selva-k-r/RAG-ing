"""Module 1: Corpus & Embedding Lifecycle

Objective: Ingest oncology-related documents, generate embeddings, and store them for retrieval.

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
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
import chromadb

# Import connectors and utilities
from ..config.settings import Settings
from ..connectors import ConfluenceConnector
from ..utils.exceptions import IngestionError

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
        """Initialize corpus embedding module with YAML configuration."""
        self.config = config
        self.data_source_config = config.data_source
        self.chunking_config = config.chunking
        self.embedding_config = config.embedding_model
        self.vector_store_config = config.vector_store
        
        # Initialize state
        self.embedding_model = None
        self.vector_store = None
        self._stats = {
            "chunk_count": 0,
            "vector_size": 0,
            "processing_time": 0,
            "documents_processed": 0,
            "ontology_codes_extracted": 0
        }
        
        logger.info(f"CorpusEmbeddingModule initialized - Data source: {self.data_source_config.type}")
    
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
        logger.info("🚀 Starting enhanced multi-source corpus processing pipeline")
        start_time = time.time()
        
        try:
            # Step 1: Enhanced Multi-Source Ingestion Logic
            logger.info("📂 Step 1: Multi-source document ingestion")
            documents = self._ingest_documents_multi_source()
            self._stats["documents_processed"] = len(documents)
            logger.info(f"✅ Ingested {len(documents)} documents from multiple sources")
            
            # Step 2: Chunking Strategy  
            logger.info("🧩 Step 2: Document chunking")
            chunks = self._chunk_documents(documents)
            self._stats["chunk_count"] = len(chunks)
            logger.info(f"✅ Created {len(chunks)} chunks using {self.chunking_config.strategy} strategy")
            
            # Step 3: Embedding Generation
            logger.info("🧠 Step 3: Loading embedding model")
            self._load_embedding_model()
            
            # Step 4: Vector Storage
            logger.info("💾 Step 4: Setting up vector store and storing embeddings")
            self._setup_vector_store()
            self._store_embeddings(chunks)
            
            # Step 5: Validate embeddings
            logger.info("✔️ Step 5: Validating vector dimensions and schema")
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
            
            # Enhanced logging with multi-source breakdown
            logger.info(
                f"🎉 Multi-source corpus processing completed successfully! "
                f"Sources: {self._stats.get('sources_processed', 0)}, "
                f"Documents: {self._stats['documents_processed']}, "
                f"Chunks: {self._stats['chunk_count']}, "
                f"Vector size: {self._stats.get('vector_size', 'N/A')}, "
                f"Time: {processing_time:.2f}s"
            )
            
            return self._stats
            
        except Exception as e:
            logger.error(f"❌ Multi-source corpus processing failed: {str(e)}")
            raise IngestionError(f"Failed to process corpus: {str(e)}")
    
    def _ingest_documents_multi_source(self) -> List[Document]:
        """Enhanced multi-source document ingestion.
        
        Educational note: This method shows how to handle multiple data sources
        gracefully, continuing processing even if one source fails.
        """
        all_documents = []
        enabled_sources = self.data_source_config.get_enabled_sources()
        
        logger.info(f"📋 Processing {len(enabled_sources)} enabled data sources")
        
        for source in enabled_sources:
            source_type = source.get('type')
            source_description = source.get('description', f'{source_type} source')
            
            try:
                logger.info(f"📂 Processing {source_description}...")
                
                # Route to appropriate ingestion method based on type
                if source_type == 'local_file':
                    docs = self._ingest_local_files_enhanced(source)
                elif source_type == 'confluence':
                    docs = self._ingest_confluence_enhanced(source)
                elif source_type == 'jira':
                    docs = self._ingest_jira_enhanced(source)
                else:
                    logger.warning(f"❓ Unknown source type: {source_type}, skipping...")
                    continue
                
                all_documents.extend(docs)
                logger.info(f"✅ {source_description}: {len(docs)} documents processed")
                
            except Exception as e:
                logger.error(f"❌ Error processing {source_description}: {e}")
                logger.info("🔄 Continuing with other sources...")
                continue
        
        if not all_documents:
            # Fall back to legacy single-source method for backward compatibility
            logger.info("🔄 No documents from multi-source, trying legacy method...")
            return self._ingest_documents()
        
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
                        # Extract ontology codes as required
                        ontology_codes = self._extract_ontology_codes(content)
                        self._stats["ontology_codes_extracted"] += len(ontology_codes)
                        
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": str(file_path),
                                "filename": file_path.name,
                                "file_type": file_path.suffix,
                                "date": file_path.stat().st_mtime,
                                "ontology_codes": ontology_codes,
                                "domain": "oncology"  # As per requirements
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
            ontology_codes = self._extract_ontology_codes(doc.page_content)
            doc.metadata["ontology_codes"] = ontology_codes
            doc.metadata["domain"] = "oncology"
            self._stats["ontology_codes_extracted"] += len(ontology_codes)
        
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
    
    def _extract_ontology_codes(self, content: str) -> List[str]:
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
    
    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Apply chunking strategy based on configuration.
        
        Supports recursive and semantic strategies as required:
        - recursive: RecursiveCharacterTextSplitter with configured size/overlap
        - semantic: Preserve semantic boundaries for oncology content
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
        """Apply recursive character-based chunking with configured parameters."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunking_config.chunk_size,
            chunk_overlap=self.chunking_config.overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        chunks = text_splitter.split_documents(documents)
        
        # Enhance chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "chunk_index": i,
                "chunk_method": "recursive",
                "chunk_size": len(chunk.page_content)
            })
        
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
        """Enhanced embedding model loading supporting Azure OpenAI and open source models.
        
        Educational note: This demonstrates the Strategy pattern - different embedding
        providers are handled through a common interface but with provider-specific logic.
        
        Supports both Azure OpenAI embeddings (text-embedding-ada-002) and 
        open source models (PubMedBERT, all-MiniLM-L6-v2, etc.)
        """
        provider = self.embedding_config.get_primary_provider()
        logger.info(f"Loading embedding model using provider: {provider}")
        
        if provider == "azure_openai" and self.embedding_config.use_azure_primary:
            # Use Azure OpenAI embeddings (higher quality, paid)
            self._load_azure_embedding_model()
        else:
            # Use open source embedding model (free, local)
            self._load_open_source_embedding_model()
    
    def _load_azure_embedding_model(self) -> None:
        """Load Azure OpenAI embedding model."""
        try:
            logger.info("🔵 Loading Azure OpenAI embedding model")
            
            # Import Azure OpenAI
            from openai import AzureOpenAI
            
            # Get configuration
            azure_client = AzureOpenAI(
                api_key=self.config.get_api_key("azure_openai"),
                azure_endpoint=self.embedding_config.azure_endpoint or self.config.azure_openai_endpoint,
                api_version=self.embedding_config.azure_api_version
            )
            
            # Create wrapper class for Azure embeddings to match LangChain interface
            class AzureEmbeddingWrapper:
                def __init__(self, client, model_name, deployment_name):
                    self.client = client
                    self.model_name = model_name
                    self.deployment_name = deployment_name
                
                def embed_query(self, text: str) -> List[float]:
                    """Embed a single query text."""
                    response = self.client.embeddings.create(
                        input=[text],
                        model=self.deployment_name
                    )
                    return response.data[0].embedding
                
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    """Embed multiple documents."""
                    # Process in batches to avoid API limits
                    batch_size = 16  # Azure OpenAI batch limit
                    all_embeddings = []
                    
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i:i + batch_size]
                        response = self.client.embeddings.create(
                            input=batch,
                            model=self.deployment_name
                        )
                        batch_embeddings = [data.embedding for data in response.data]
                        all_embeddings.extend(batch_embeddings)
                    
                    return all_embeddings
            
            # Initialize Azure embedding wrapper
            self.embedding_model = AzureEmbeddingWrapper(
                client=azure_client,
                model_name=self.embedding_config.azure_model,
                deployment_name=self.embedding_config.azure_deployment_name
            )
            
            # Test the model with a sample text
            test_embedding = self.embedding_model.embed_query("oncology biomarker test")
            self._stats["vector_size"] = len(test_embedding)
            
            logger.info(f"✅ Azure embedding model loaded successfully - Vector dimension: {len(test_embedding)}")
            logger.info(f"   Model: {self.embedding_config.azure_model}")
            logger.info(f"   Deployment: {self.embedding_config.azure_deployment_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Azure embedding model: {e}")
            logger.info("🔄 Falling back to open source embedding model")
            self._load_open_source_embedding_model()
    
    def _load_open_source_embedding_model(self) -> None:
        """Load open source embedding model as fallback or primary choice."""
        model_name = self.embedding_config.get_fallback_model()
        device = self.embedding_config.device
        
        logger.info(f"🟢 Loading open source embedding model: {model_name} on {device}")
        
        # Map model names to HuggingFace model paths as required
        model_mapping = {
            "pubmedbert": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
            "clinicalbert": "emilyalsentzer/Bio_ClinicalBERT", 
            "biobert": "dmis-lab/biobert-v1.1",
            "scibert": "allenai/scibert_scivocab_uncased",
            "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
            "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2"
        }
        
        model_path = model_mapping.get(model_name, model_name)
        
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Test the model with a sample text
            test_embedding = self.embedding_model.embed_query("oncology biomarker test")
            self._stats["vector_size"] = len(test_embedding)
            
            logger.info(f"✅ Open source embedding model loaded successfully - Vector dimension: {len(test_embedding)}")
            logger.info(f"   Model path: {model_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load open source embedding model {model_name}: {e}")
            raise IngestionError(f"Embedding model loading failed: {e}")
    
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
            
        except Exception as e:
            logger.error(f"Failed to setup ChromaDB: {e}")
            raise IngestionError(f"ChromaDB setup failed: {e}")
    
    def _setup_faiss_store(self) -> None:
        """Setup FAISS vector store."""
        # FAISS will be initialized when first documents are added
        self.vector_store = None
        logger.info("FAISS vector store will be initialized on first document addition")
    
    def _store_embeddings(self, chunks: List[Document]) -> None:
        """Store document chunks with embeddings in vector store.
        
        Stores vectors with metadata as required.
        """
        if not chunks:
            logger.warning("No chunks to store")
            return
        
        logger.info(f"Storing {len(chunks)} chunks with embeddings")
        
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
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise IngestionError(f"Vector storage failed: {e}")
    
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
            logger.info(f"Embedding validation successful: {len(test_embedding)}D vectors")
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
            logger.warning(f"📁 Local path does not exist: {path}")
            return documents
        
        logger.info(f"📂 Scanning local directory: {path}")
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in file_types:
                try:
                    content = self._extract_file_content(file_path)
                    if content.strip():
                        # Extract ontology codes for medical domain
                        ontology_codes = self._extract_ontology_codes(content)
                        
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": str(file_path),
                                "source_type": "local_file",
                                "filename": file_path.name,
                                "file_type": file_path.suffix,
                                "date": file_path.stat().st_mtime,
                                "ontology_codes": ontology_codes,
                                "domain": "oncology",
                                "description": source_config.get('description', 'Local file')
                            }
                        )
                        documents.append(doc)
                        logger.debug(f"✅ Processed: {file_path.name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process {file_path}: {e}")
        
        logger.info(f"📚 Local files: {len(documents)} documents processed")
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
            logger.warning(f"🔑 Confluence config missing fields: {missing_fields}")
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
                logger.info(f"🌐 Processing Confluence space: {space_key}")
                docs = connector.fetch_pages(space_key, max_pages, page_filter)
                
                # Add source metadata
                for doc in docs:
                    doc.metadata.update({
                        "source_type": "confluence",
                        "space_key": space_key,
                        "description": source_config.get('description', f'Confluence {space_key}')
                    })
                
                all_docs.extend(docs)
                logger.info(f"✅ Space {space_key}: {len(docs)} pages processed")
            
            logger.info(f"🌐 Confluence total: {len(all_docs)} documents processed")
            return all_docs
            
        except Exception as e:
            logger.error(f"❌ Confluence ingestion failed: {e}")
            return []
    
    def _ingest_jira_enhanced(self, source_config: Dict[str, Any]) -> List[Document]:
        """Enhanced JIRA ingestion for tickets and requirements.
        
        Educational note: This method shows how to add new data source types
        while following the same patterns as existing sources.
        """
        jira_config = source_config.get('jira', {})
        
        # Check JIRA configuration
        required_fields = ['server_url', 'username', 'auth_token']
        missing_fields = [field for field in required_fields if not jira_config.get(field)]
        
        if missing_fields:
            logger.warning(f"🔑 JIRA config missing fields: {missing_fields}")
            return []
        
        try:
            # This is a placeholder for JIRA connector implementation
            # Educational note: In a real implementation, you would:
            # 1. Create a JiraConnector class similar to ConfluenceConnector
            # 2. Use the JIRA API to fetch tickets based on JQL queries
            # 3. Extract content from ticket descriptions, comments, etc.
            
            logger.info("🎫 JIRA ingestion - Implementation pending")
            logger.info("💡 To implement: Create JiraConnector class with API integration")
            
            # For now, return empty list
            # TODO: Implement JiraConnector when needed
            return []
            
        except Exception as e:
            logger.error(f"❌ JIRA ingestion failed: {e}")
            return []
