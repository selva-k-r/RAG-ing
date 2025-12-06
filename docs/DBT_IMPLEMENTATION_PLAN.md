# DBT Artifacts Integration - Implementation Plan

**Date**: December 4, 2025  
**Branch**: feature/using-dbt-artifacts  
**Status**: Planning Phase  

---

## Current System Understanding

### Architecture Overview

**5-Module Production System**:
1. **CorpusEmbeddingModule** - Multi-source ingestion with hierarchical storage
2. **QueryRetrievalModule** - Hybrid search with reranking
3. **LLMOrchestrationModule** - Azure OpenAI with fallback
4. **UILayerModule** - FastAPI web interface
5. **EvaluationLoggingModule** - Performance tracking

### Current Ingestion Flow

```
orchestrator.ingest_corpus()
  ↓
CorpusEmbeddingModule.process_corpus()
  ↓
_ingest_documents_multi_source()  ← Multi-source support already exists!
  ↓
  ├─ _ingest_local_files_enhanced(source)
  ├─ _ingest_confluence_enhanced(source)
  ├─ _ingest_jira_enhanced(source)
  └─ _ingest_azuredevops_enhanced(source)  ← We'll enhance this!
       ↓
     AzureDevOpsConnector.fetch_documents()
       ↓
     Returns: List[Document] with metadata
```

### Current Features Already Implemented

✅ **Multi-source support**: `config.yaml` → `data_source.sources[]` array  
✅ **Path filtering**: `include_paths`, `exclude_paths`  
✅ **File type filtering**: `include_file_types`, `exclude_file_types`  
✅ **Commit history**: `fetch_commit_history`, `commits_per_file`  
✅ **Batch processing**: `enable_streaming`, `batch_size`  
✅ **Hierarchical storage**: DocumentSummarizer with type-specific logic  
✅ **Duplicate detection**: DuplicateDetector with SQLite tracking  
✅ **Ingestion tracking**: IngestionTrackerSQLite for resume capability  

### Key Components to Understand

**1. AzureDevOpsConnector** (`connectors/azuredevops_connector.py`):
- Fetches files from Azure DevOps repos
- Supports path/file type filtering
- Returns `List[Document]` with metadata

**2. DocumentSummarizer** (`utils/document_summarizer.py`):
- Type-specific summarization (SQL, Python, YAML, PDF)
- Extracts keywords, topics, business context
- Used for hierarchical storage (summary + details)

**3. CorpusEmbeddingModule** (`modules/corpus_embedding.py`):
- Orchestrates ingestion, chunking, embedding
- Supports duplicate detection
- Integrates with ingestion tracker

**4. Config Management** (`config/settings.py`):
- Pydantic models for YAML validation
- Multi-source support via `sources[]` array
- Environment variable expansion `${VAR}`

---

## DBT Artifacts Integration Strategy

### Phase 1: DBT Artifact Loader (Week 1, Days 1-2)

**Goal**: Load and parse DBT artifacts (manifest, catalog, graph_summary)

**New Components**:

#### 1.1. DBTLineageGraph (`src/rag_ing/utils/dbt_lineage.py`)
```python
class DBTLineageGraph:
    """In-memory graph for fast lineage queries"""
    
    def __init__(self, graph_summary_path: str):
        self.nodes = self._load_graph(graph_summary_path)
        self.name_to_id = self._build_name_index()
        self.predecessors = self._build_reverse_index()
    
    def get_upstream(self, model_name: str, recursive: bool = False,
                    filter_type: Optional[str] = None) -> List[str]:
        """Get upstream dependencies (0.01ms)"""
        ...
    
    def get_downstream(self, model_name: str, recursive: bool = False,
                      filter_type: Optional[str] = None) -> List[str]:
        """Get downstream dependencies (0.01ms)"""
        ...
    
    def get_lineage_stats(self, model_name: str) -> Dict:
        """Get summary statistics for model"""
        ...
```

#### 1.2. DBTArtifactParser (`src/rag_ing/utils/dbt_artifacts.py`)
```python
class DBTArtifactParser:
    """Parser for DBT artifacts with lineage support"""
    
    def __init__(self, artifacts_dir: str):
        self.manifest = self._load_manifest()
        self.catalog = self._load_catalog()
        self.graph = DBTLineageGraph(graph_summary_path)
        self.project_config = self._load_project_yml()
    
    def get_model_metadata(self, model_name: str) -> Dict:
        """Get complete model metadata from all artifacts"""
        return {
            'name': model_name,
            'description': manifest['description'],
            'tags': manifest['tags'],
            'owner': manifest['meta'].get('owner'),
            'schema': manifest['schema'],
            'materialization': self._get_materialization(model_name),
            'columns': catalog['columns'],
            'upstream_models': self.graph.get_upstream(model_name, filter_type='model'),
            'upstream_sources': self.graph.get_upstream(model_name, filter_type='source'),
            'downstream_models': self.graph.get_downstream(model_name, filter_type='model'),
            'downstream_tests': self.graph.get_downstream(model_name, filter_type='test')
        }
    
    def detect_dbt_artifacts(self, file_list: List[str]) -> Optional[str]:
        """Detect if repo contains DBT artifacts"""
        required_files = ['manifest.json', 'catalog.json', 'dbt_project.yml']
        if all(any(f.endswith(req) for f in file_list) for req in required_files):
            return self._extract_artifacts_dir(file_list)
        return None
```

**Integration Points**:
- Load artifacts once at module initialization
- Cache parsed data in memory (967 nodes = 150 KB)
- Expose metadata enrichment methods

---

### Phase 2: Azure DevOps Multi-Repo Support (Week 1, Day 3)

**Goal**: Support fetching from multiple Azure DevOps repositories

**Config Enhancement**:

```yaml
data_source:
  sources:
    - type: "azure_devops"
      enabled: true
      azure_devops:
        organization: "${AZURE_DEVOPS_ORG}"
        project: "${AZURE_DEVOPS_PROJECT}"
        pat_token: "${AZURE_DEVOPS_PAT}"
        
        # NEW: Multiple repositories support
        repositories:
          - name: "dbt-pophealth"
            branch: "spike/rag_search"
            include_paths:
              - "/dbt_anthem/target/"  # DBT artifacts
              - "/dbt_anthem/models/"  # DBT models
            description: "DBT transformations and artifacts"
          
          - name: "analytics-warehouse"
            branch: "main"
            include_paths:
              - "/sql/"
              - "/docs/"
            description: "Warehouse SQL and documentation"
          
          - name: "data-quality"
            branch: "main"
            include_file_types: [".sql", ".py", ".md"]
            description: "Data quality checks"
        
        # Shared settings (apply to all repos)
        include_file_types: [".sql", ".py", ".yml", ".md"]
        exclude_file_types: [".dll", ".exe", ".bin"]
        fetch_commit_history: true
        commits_per_file: 10
```

**Settings Model Enhancement** (`config/settings.py`):

```python
class AzureDevOpsRepoConfig(BaseModel):
    """Configuration for a single Azure DevOps repository"""
    name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Branch to fetch from")
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    include_file_types: Optional[List[str]] = None  # Override shared settings
    exclude_file_types: Optional[List[str]] = None  # Override shared settings
    description: str = Field(default="", description="Repository description")

class AzureDevOpsConfig(BaseModel):
    """Azure DevOps configuration with multi-repo support"""
    organization: str
    project: str
    pat_token: str
    
    # NEW: Support both single repo (backward compatible) and multi-repo
    repo_name: Optional[str] = None  # Legacy single repo
    branch: Optional[str] = "main"   # Legacy single repo branch
    repositories: Optional[List[AzureDevOpsRepoConfig]] = None  # Multi-repo
    
    # Shared settings
    include_paths: List[str] = Field(default_factory=list)
    exclude_paths: List[str] = Field(default_factory=list)
    include_file_types: List[str] = Field(default_factory=list)
    exclude_file_types: List[str] = Field(default_factory=list)
    fetch_commit_history: bool = True
    commits_per_file: int = 10
    
    @field_validator('repositories')
    @classmethod
    def validate_repo_config(cls, v, info):
        """Ensure either repo_name or repositories is specified"""
        values = info.data
        if not v and not values.get('repo_name'):
            raise ValueError("Either 'repo_name' or 'repositories' must be specified")
        return v
    
    def get_repositories(self) -> List[Dict]:
        """Get list of repositories to process"""
        if self.repositories:
            return [repo.dict() for repo in self.repositories]
        elif self.repo_name:
            # Backward compatibility: convert single repo to list
            return [{
                'name': self.repo_name,
                'branch': self.branch or 'main',
                'include_paths': self.include_paths,
                'exclude_paths': self.exclude_paths,
                'description': f'Legacy repo: {self.repo_name}'
            }]
        return []
```

**Connector Enhancement** (`connectors/azuredevops_connector.py`):

```python
class AzureDevOpsConnector:
    def __init__(self, config: Dict[str, Any]):
        # Existing initialization...
        
        # NEW: Multi-repo support
        self.repositories = self._parse_repository_config(config)
    
    def _parse_repository_config(self, config: Dict) -> List[Dict]:
        """Parse repository configuration (single or multiple)"""
        if 'repositories' in config and config['repositories']:
            return config['repositories']
        elif config.get('repo_name'):
            # Backward compatibility
            return [{
                'name': config['repo_name'],
                'branch': config.get('branch', 'main'),
                'include_paths': config.get('include_paths', []),
                'exclude_paths': config.get('exclude_paths', []),
                'include_file_types': config.get('include_file_types', []),
                'exclude_file_types': config.get('exclude_file_types', [])
            }]
        return []
    
    def fetch_documents(self) -> List[Document]:
        """Fetch documents from all configured repositories"""
        all_documents = []
        
        for repo_config in self.repositories:
            repo_name = repo_config['name']
            branch = repo_config.get('branch', 'main')
            
            logger.info(f"Fetching from repository: {repo_name} (branch: {branch})")
            
            try:
                # Fetch files for this repo
                docs = self._fetch_repository_files(repo_config)
                all_documents.extend(docs)
                
                logger.info(f"  {repo_name}: {len(docs)} documents fetched")
                
            except Exception as e:
                logger.error(f"  Failed to fetch from {repo_name}: {e}")
                continue
        
        return all_documents
    
    def _fetch_repository_files(self, repo_config: Dict) -> List[Document]:
        """Fetch files from a single repository"""
        # Existing fetch logic, but with repo-specific config
        ...
```

---

### Phase 3: DBT Metadata Enrichment (Week 1, Days 4-5)

**Goal**: Enrich DBT documents with artifact metadata during ingestion

**Enhancement to CorpusEmbeddingModule**:

```python
class CorpusEmbeddingModule:
    def __init__(self, config: Settings):
        # Existing initialization...
        
        # NEW: DBT artifact parser (lazy loaded)
        self._dbt_parser = None
    
    def _ingest_azuredevops_enhanced(self, source: Dict) -> List[Document]:
        """Enhanced Azure DevOps ingestion with DBT detection"""
        # Fetch documents from connector
        connector = AzureDevOpsConnector(source.get('azure_devops'))
        documents = connector.fetch_documents()
        
        # NEW: Detect DBT artifacts in fetched files
        file_paths = [doc.metadata.get('file_path', '') for doc in documents]
        dbt_artifacts_dir = self._detect_dbt_artifacts(file_paths, documents)
        
        if dbt_artifacts_dir:
            logger.info(f"[OK] Detected DBT artifacts in {dbt_artifacts_dir}")
            self._dbt_parser = self._initialize_dbt_parser(dbt_artifacts_dir, documents)
        
        # Enrich documents with DBT metadata
        enriched_docs = []
        for doc in documents:
            if self._is_dbt_model(doc):
                doc = self._enrich_with_dbt_metadata(doc)
            enriched_docs.append(doc)
        
        return enriched_docs
    
    def _detect_dbt_artifacts(self, file_paths: List[str], 
                             documents: List[Document]) -> Optional[str]:
        """Detect if DBT artifacts exist in fetched files"""
        required_artifacts = ['manifest.json', 'catalog.json', 'dbt_project.yml']
        
        # Check if all required artifacts are present
        found_artifacts = {}
        for doc in documents:
            file_path = doc.metadata.get('file_path', '')
            for artifact in required_artifacts:
                if file_path.endswith(artifact):
                    found_artifacts[artifact] = doc
        
        if len(found_artifacts) == len(required_artifacts):
            # Extract directory path
            manifest_path = found_artifacts['manifest.json'].metadata.get('file_path', '')
            artifacts_dir = str(Path(manifest_path).parent)
            return artifacts_dir
        
        return None
    
    def _initialize_dbt_parser(self, artifacts_dir: str, 
                              documents: List[Document]) -> DBTArtifactParser:
        """Initialize DBT parser from fetched artifact documents"""
        # Save artifacts to temp directory for parsing
        temp_dir = Path('./temp/dbt_artifacts')
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Find and save artifact documents
        for doc in documents:
            file_path = doc.metadata.get('file_path', '')
            if any(file_path.endswith(f) for f in 
                   ['manifest.json', 'catalog.json', 'graph_summary.json', 
                    'dbt_project.yml', 'run_results.json']):
                artifact_name = Path(file_path).name
                save_path = temp_dir / artifact_name
                with open(save_path, 'w') as f:
                    f.write(doc.page_content)
                logger.info(f"  Saved DBT artifact: {artifact_name}")
        
        # Initialize parser
        from ..utils.dbt_artifacts import DBTArtifactParser
        parser = DBTArtifactParser(str(temp_dir))
        logger.info(f"[OK] DBT parser initialized with {len(parser.graph.nodes)} nodes")
        
        return parser
    
    def _is_dbt_model(self, doc: Document) -> bool:
        """Check if document is a DBT model"""
        file_path = doc.metadata.get('file_path', '')
        return ('/models/' in file_path and file_path.endswith('.sql')) or \
               ('/seeds/' in file_path and file_path.endswith('.csv'))
    
    def _enrich_with_dbt_metadata(self, doc: Document) -> Document:
        """Enrich document with DBT metadata from artifacts"""
        if not self._dbt_parser:
            return doc
        
        file_path = doc.metadata.get('file_path', '')
        model_name = self._extract_model_name_from_path(file_path)
        
        if not model_name:
            return doc
        
        try:
            # Get metadata from DBT artifacts
            dbt_metadata = self._dbt_parser.get_model_metadata(model_name)
            
            # Enrich document metadata
            doc.metadata.update({
                'dbt_model': model_name,
                'dbt_description': dbt_metadata.get('description', ''),
                'dbt_tags': dbt_metadata.get('tags', []),
                'dbt_owner': dbt_metadata.get('owner', ''),
                'dbt_schema': dbt_metadata.get('schema', ''),
                'dbt_materialization': dbt_metadata.get('materialization', ''),
                'dbt_upstream_models': dbt_metadata.get('upstream_models', [])[:5],
                'dbt_upstream_sources': dbt_metadata.get('upstream_sources', [])[:5],
                'dbt_downstream_models': dbt_metadata.get('downstream_models', [])[:3],
                'lineage_depth': len(dbt_metadata.get('upstream_models', [])),
                'has_tests': len(dbt_metadata.get('downstream_tests', [])) > 0
            })
            
            logger.debug(f"  Enriched DBT model: {model_name}")
            
        except Exception as e:
            logger.warning(f"  Failed to enrich {model_name}: {e}")
        
        return doc
    
    def _extract_model_name_from_path(self, file_path: str) -> Optional[str]:
        """Extract DBT model name from file path"""
        # Examples:
        # /dbt_anthem/models/staging/stg_billing_provider.sql 
        #   -> model.anthem_dev.stg_billing_provider
        # /dbt_anthem/seeds/seed_anthem_excluded_cancer_code.csv
        #   -> seed.anthem_dev.seed_anthem_excluded_cancer_code
        
        if '/models/' in file_path:
            model_file = Path(file_path).stem
            # Get project name from dbt_project.yml (parsed)
            project_name = self._dbt_parser.project_config.get('name', 'anthem_dev')
            return f"model.{project_name}.{model_file}"
        elif '/seeds/' in file_path:
            seed_file = Path(file_path).stem
            project_name = self._dbt_parser.project_config.get('name', 'anthem_dev')
            return f"seed.{project_name}.{seed_file}"
        
        return None
```

**DocumentSummarizer Enhancement**:

```python
class DocumentSummarizer:
    def _summarize_sql(self, document: Document) -> Dict[str, Any]:
        """Summarize SQL document with DBT lineage context"""
        # Existing SQL summarization...
        
        # NEW: Add DBT lineage to summary
        if 'dbt_model' in document.metadata:
            dbt_context = self._format_dbt_lineage_context(document.metadata)
            summary['business_context'] += f"\n\n{dbt_context}"
            summary['keywords'].extend(document.metadata.get('dbt_tags', []))
        
        return summary
    
    def _format_dbt_lineage_context(self, metadata: Dict) -> str:
        """Format DBT lineage information for summary"""
        lines = []
        lines.append(f"DBT Model: {metadata['dbt_model']}")
        
        if metadata.get('dbt_description'):
            lines.append(f"Purpose: {metadata['dbt_description']}")
        
        if metadata.get('dbt_upstream_sources'):
            sources = ', '.join(metadata['dbt_upstream_sources'])
            lines.append(f"Data Sources: {sources}")
        
        if metadata.get('dbt_upstream_models'):
            upstream = ', '.join(metadata['dbt_upstream_models'])
            lines.append(f"Depends On: {upstream}")
        
        if metadata.get('dbt_downstream_models'):
            downstream = ', '.join(metadata['dbt_downstream_models'])
            lines.append(f"Used By: {downstream}")
        
        return '\n'.join(lines)
```

---

### Phase 4: Query Understanding Enhancement (Week 2, Days 1-2)

**Goal**: Detect and handle DBT-specific queries

**New Component: QueryUnderstanding** (`utils/query_understanding.py`):

```python
class QueryUnderstanding:
    """Analyze user query to detect intent and extract context"""
    
    def __init__(self, dbt_parser: Optional[DBTArtifactParser] = None):
        self.dbt_parser = dbt_parser
        self.patterns = self._load_patterns()
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query and return intent + context"""
        query_lower = query.lower()
        
        # Detect DBT lineage intent
        if any(kw in query_lower for kw in ['upstream', 'feeds into', 'sources']):
            return self._analyze_upstream_query(query)
        
        if any(kw in query_lower for kw in ['downstream', 'depends on', 'uses']):
            return self._analyze_downstream_query(query)
        
        if 'lineage' in query_lower or 'data flow' in query_lower:
            return self._analyze_lineage_query(query)
        
        # Standard semantic search
        return {'intent': 'semantic_search', 'query': query}
    
    def _analyze_upstream_query(self, query: str) -> Dict:
        """Analyze upstream lineage query"""
        model_name = self._extract_model_from_query(query)
        
        if model_name and self.dbt_parser:
            upstream = self.dbt_parser.graph.get_upstream(
                model_name, recursive=True, filter_type='source'
            )
            return {
                'intent': 'upstream_lineage',
                'model': model_name,
                'upstream_sources': upstream,
                'context_filter': {'dbt_model': model_name}
            }
        
        return {'intent': 'semantic_search', 'query': query}
```

**Integration with QueryRetrievalModule**:

```python
class QueryRetrievalModule:
    def __init__(self, config: Settings):
        # Existing initialization...
        
        # NEW: Query understanding
        self.query_understanding = None  # Lazy loaded
    
    def set_dbt_parser(self, dbt_parser: DBTArtifactParser):
        """Set DBT parser for lineage-aware queries"""
        from ..utils.query_understanding import QueryUnderstanding
        self.query_understanding = QueryUnderstanding(dbt_parser)
        logger.info("[OK] Query understanding enabled with DBT lineage")
    
    def query(self, query_text: str, filters: Optional[Dict] = None) -> Dict:
        """Enhanced query with intent detection"""
        # NEW: Analyze query intent
        if self.query_understanding:
            intent_result = self.query_understanding.analyze_query(query_text)
            
            if intent_result['intent'] == 'upstream_lineage':
                return self._handle_lineage_query(intent_result)
        
        # Existing semantic search logic
        return self._semantic_search(query_text, filters)
    
    def _handle_lineage_query(self, intent: Dict) -> Dict:
        """Handle DBT lineage query with graph context"""
        model = intent['model']
        sources = intent['upstream_sources']
        
        # Retrieve documents about this model and its sources
        context_docs = self._retrieve_by_metadata(intent['context_filter'])
        
        # Build answer from graph + documents
        return {
            'intent': 'upstream_lineage',
            'model': model,
            'sources': sources,
            'context': context_docs,
            'answer': f"The model {model} depends on these data sources: {', '.join(sources)}"
        }
```

---

## Implementation Timeline

### Week 1: Core DBT Integration

**Day 1-2**: DBT Artifact Parser
- [x] Analyze artifacts (DONE - see analysis docs)
- [ ] Create `DBTLineageGraph` class
- [ ] Create `DBTArtifactParser` class
- [ ] Unit tests for parsing and lineage queries

**Day 3**: Multi-Repo Support
- [ ] Enhance `AzureDevOpsConfig` Pydantic model
- [ ] Update `AzureDevOpsConnector` for multi-repo
- [ ] Update `config.yaml` with multi-repo example
- [ ] Test fetching from multiple repos

**Day 4-5**: Metadata Enrichment
- [ ] Add DBT detection to `_ingest_azuredevops_enhanced()`
- [ ] Implement `_enrich_with_dbt_metadata()`
- [ ] Enhance `DocumentSummarizer` for DBT context
- [ ] Test with real DBT models (anthem_dev)

### Week 2: Query Enhancement

**Day 1-2**: Query Understanding
- [ ] Create `QueryUnderstanding` class
- [ ] Add pattern detection for lineage queries
- [ ] Integrate with `QueryRetrievalModule`
- [ ] Test lineage queries

**Day 3-4**: UI Integration
- [ ] Add "Show Lineage" feature to UI
- [ ] Display upstream/downstream in results
- [ ] Add DBT metadata to document display

**Day 5**: Testing & Documentation
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] Update README and developer guide

---

## Configuration Changes Required

### Update config.yaml

```yaml
data_source:
  sources:
    - type: "azure_devops"
      enabled: true
      azure_devops:
        organization: "${AZURE_DEVOPS_ORG}"
        project: "${AZURE_DEVOPS_PROJECT}"
        pat_token: "${AZURE_DEVOPS_PAT}"
        
        # NEW: Multi-repository support
        repositories:
          - name: "dbt-pophealth"
            branch: "spike/rag_search"
            include_paths:
              - "/dbt_anthem/target/"  # DBT artifacts
              - "/dbt_anthem/models/"  # DBT models
            description: "DBT analytics transformations"
          
          - name: "data-warehouse"
            branch: "main"
            include_paths: ["/sql/", "/docs/"]
            description: "Warehouse SQL and docs"
        
        # Shared settings
        include_file_types: [".sql", ".py", ".yml", ".md", ".json"]
        fetch_commit_history: true
        commits_per_file: 10
        batch_size: 50

# NEW: DBT-specific configuration
dbt_integration:
  enabled: true
  auto_detect_artifacts: true  # Detect DBT artifacts during ingestion
  enrich_metadata: true        # Add lineage to document metadata
  parse_lineage: true          # Build in-memory lineage graph
  cache_artifacts: true        # Cache parsed artifacts in temp/
```

---

## Key Decisions

### ✅ Confirmed Decisions

1. **In-Memory Graph**: Use in-memory lineage graph (not SQLite/Neo4j)
   - Fast: 0.01ms queries
   - Simple: No additional database
   - Scalable: 967 nodes = 150 KB RAM

2. **Multi-Repo Support**: Allow multiple Azure DevOps repositories
   - Flexible: Different repos for DBT, warehouse SQL, docs
   - Backward compatible: Single `repo_name` still works

3. **Lazy Loading**: Load DBT parser only if artifacts detected
   - Efficient: No overhead if no DBT projects
   - Flexible: Works with non-DBT repositories

4. **Metadata Enrichment**: Add DBT context during ingestion
   - Complete: Lineage, descriptions, tags, owners
   - Searchable: Keywords and topics include DBT metadata

### 📋 Open Questions

1. **Artifact Refresh**: How often to reload DBT artifacts?
   - Option A: Reload on every ingestion (simple, fresh)
   - Option B: Check file hash, reload if changed (efficient)
   - Option C: Manual reload command (explicit control)

2. **Multi-Project DBT**: How to handle multiple DBT projects in same repo?
   - Detect all `dbt_project.yml` files
   - Build separate parser for each project
   - Prefix model names with project

3. **Lineage Visualization**: Add visual graph to UI?
   - Week 3 feature (after core implementation)
   - Use D3.js or Cytoscape.js
   - Interactive exploration

---

## Success Metrics

### Phase 1 (Week 1)
- ✅ Load 6 DBT artifacts without errors
- ✅ Parse 139 models with metadata
- ✅ Build lineage graph with 967 nodes
- ✅ Enrich 100+ DBT documents during ingestion
- ✅ Multi-repo fetch from 2+ repositories

### Phase 2 (Week 2)
- ✅ Detect "upstream" queries with 90% accuracy
- ✅ Return lineage results in < 100ms
- ✅ Display DBT metadata in UI
- ✅ Integration tests pass

---

## Next Steps

**Immediate** (Today):
1. Create `DBTLineageGraph` class with graph traversal
2. Create `DBTArtifactParser` class with manifest/catalog parsing
3. Add unit tests for parsing and lineage queries

**This Week**:
1. Multi-repo support in config and connector
2. DBT detection and enrichment during ingestion
3. Test with real anthem_dev DBT project (139 models)

**Next Week**:
1. Query understanding for lineage queries
2. UI enhancements for DBT metadata display
3. Documentation and performance benchmarks

---

**Status**: Ready to implement  
**Blockers**: None  
**Dependencies**: All DBT artifacts downloaded and analyzed
