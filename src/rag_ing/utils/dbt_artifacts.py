"""DBT artifact parser for metadata enrichment.

Parses DBT artifacts to provide rich metadata for RAG:
- manifest.json: Model descriptions, tags, owners, dependencies
- catalog.json: Column types, statistics, table metadata
- graph_summary.json: Pre-computed lineage graph
- dbt_project.yml: Project configuration

Combines data from all sources to provide complete model information.
"""

import json
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .dbt_lineage import DBTLineageGraph

logger = logging.getLogger(__name__)


class DBTArtifactParser:
    """Parser for DBT artifacts with lineage support.
    
    Loads and parses DBT artifacts to provide complete model metadata:
    - Model descriptions, tags, owners from manifest
    - Column types and statistics from catalog
    - Upstream/downstream dependencies from lineage graph
    - Project configuration from dbt_project.yml
    
    Example:
        parser = DBTArtifactParser('./temp/dbt_samples')
        
        # Get complete model metadata
        metadata = parser.get_model_metadata('model.anthem_dev.dim_billing_provider')
        
        # Detect DBT artifacts in file list
        artifacts_dir = parser.detect_dbt_artifacts(file_paths)
    """
    
    def __init__(self, artifacts_dir: str):
        """Initialize parser from artifacts directory.
        
        Args:
            artifacts_dir: Directory containing DBT artifacts
            
        Expected files:
        - manifest.json (required)
        - catalog.json (optional, but recommended)
        - graph_summary.json (optional, for lineage)
        - dbt_project.yml (optional, for config)
        
        Raises:
            FileNotFoundError: If manifest.json is missing
            ValueError: If artifact format is invalid
        """
        self.artifacts_dir = Path(artifacts_dir)
        if not self.artifacts_dir.exists():
            raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")
        
        # Load artifacts
        self.manifest = self._load_manifest()
        self.catalog = self._load_catalog()
        self.project_config = self._load_project_config()
        
        # Load lineage graph if available
        graph_path = self.artifacts_dir / 'graph_summary.json'
        if graph_path.exists():
            try:
                self.graph = DBTLineageGraph(str(graph_path))
                logger.info(f"[OK] Lineage graph loaded: {len(self.graph.nodes)} nodes")
            except Exception as e:
                logger.warning(f"Failed to load lineage graph: {e}")
                self.graph = None
        else:
            logger.info("No graph_summary.json found, lineage queries disabled")
            self.graph = None
        
        # Build indexes
        self._build_indexes()
        
        logger.info(f"[OK] DBT artifacts parsed: {len(self.manifest.get('nodes', {}))} nodes")
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json.
        
        Returns:
            Dict containing manifest data
            
        Raises:
            FileNotFoundError: If manifest.json doesn't exist
        """
        manifest_path = self.artifacts_dir / 'manifest.json'
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"manifest.json not found in {self.artifacts_dir}. "
                "This file is required for DBT artifact parsing."
            )
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            logger.debug(f"Loaded manifest: {len(manifest.get('nodes', {}))} nodes")
            return manifest
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest.json: {e}")
    
    def _load_catalog(self) -> Optional[Dict[str, Any]]:
        """Load catalog.json (optional).
        
        Returns:
            Dict containing catalog data, or None if not found
        """
        catalog_path = self.artifacts_dir / 'catalog.json'
        if not catalog_path.exists():
            logger.debug("No catalog.json found")
            return None
        
        try:
            with open(catalog_path, 'r') as f:
                catalog = json.load(f)
            
            logger.debug(f"Loaded catalog: {len(catalog.get('nodes', {}))} nodes")
            return catalog
            
        except Exception as e:
            logger.warning(f"Failed to load catalog.json: {e}")
            return None
    
    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """Load dbt_project.yml (optional).
        
        Returns:
            Dict containing project config, or None if not found
        """
        project_path = self.artifacts_dir / 'dbt_project.yml'
        if not project_path.exists():
            logger.debug("No dbt_project.yml found")
            return None
        
        try:
            with open(project_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.debug(f"Loaded project config: {config.get('name', 'unknown')}")
            return config
            
        except Exception as e:
            logger.warning(f"Failed to load dbt_project.yml: {e}")
            return None
    
    def _build_indexes(self) -> None:
        """Build lookup indexes for fast queries."""
        # Build simple name lookup for manifest nodes
        self.nodes_by_name = {}
        for node_id, node_data in self.manifest.get('nodes', {}).items():
            name = node_data.get('name')
            if name:
                self.nodes_by_name[name] = node_id
        
        logger.debug(f"Built indexes: {len(self.nodes_by_name)} nodes by name")
    
    def get_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """Get complete model metadata from all artifacts.
        
        Args:
            model_name: Full model name (e.g., "model.anthem_dev.dim_billing_provider")
                       or simple name (e.g., "dim_billing_provider")
            
        Returns:
            Dict containing:
            - name: Model name
            - description: Model description from manifest
            - tags: List of tags
            - owner: Owner from meta
            - schema: Target schema
            - database: Target database
            - materialization: Materialization strategy (table/view/incremental)
            - columns: Dict of column metadata
            - upstream_models: List of upstream model names
            - upstream_sources: List of upstream source names
            - downstream_models: List of downstream model names
            - downstream_tests: List of downstream test names
            
        Example:
            metadata = parser.get_model_metadata('dim_billing_provider')
            print(metadata['description'])
            print(metadata['upstream_sources'])
        """
        # Find node in manifest
        node_id = model_name if model_name.startswith('model.') else None
        
        # Try to find by simple name if not full name
        if not node_id:
            node_id = self.nodes_by_name.get(model_name)
        
        # Try to find in manifest nodes directly
        if not node_id or node_id not in self.manifest.get('nodes', {}):
            # Search through all nodes
            for nid, node_data in self.manifest.get('nodes', {}).items():
                if node_data.get('name') == model_name or nid == model_name:
                    node_id = nid
                    break
        
        if not node_id or node_id not in self.manifest.get('nodes', {}):
            logger.debug(f"Model not found in manifest: {model_name}")
            return {}
        
        # Get manifest data
        manifest_node = self.manifest['nodes'][node_id]
        
        # Get catalog data (if available)
        catalog_node = None
        if self.catalog:
            catalog_node = self.catalog.get('nodes', {}).get(node_id)
        
        # Build complete metadata
        metadata = {
            'unique_id': node_id,
            'name': manifest_node.get('name', ''),
            'description': manifest_node.get('description', ''),
            'tags': manifest_node.get('tags', []),
            'meta': manifest_node.get('meta', {}),
            'owner': manifest_node.get('meta', {}).get('owner', ''),
            'schema': manifest_node.get('schema', ''),
            'database': manifest_node.get('database', ''),
            'resource_type': manifest_node.get('resource_type', ''),
            'package_name': manifest_node.get('package_name', ''),
            'original_file_path': manifest_node.get('original_file_path', ''),
            'materialization': self._get_materialization(manifest_node),
            'columns': self._get_column_metadata(manifest_node, catalog_node),
            'depends_on': manifest_node.get('depends_on', {}),
        }
        
        # Add lineage data if graph is available
        if self.graph:
            try:
                metadata['upstream_models'] = self.graph.get_upstream(
                    node_id, recursive=False, filter_type='model')
                metadata['upstream_sources'] = self.graph.get_upstream(
                    node_id, recursive=False, filter_type='source')
                metadata['downstream_models'] = self.graph.get_downstream(
                    node_id, recursive=False, filter_type='model')
                metadata['downstream_tests'] = self.graph.get_downstream(
                    node_id, recursive=False, filter_type='test')
                metadata['lineage_depth'] = len(self.graph.get_upstream(
                    node_id, recursive=True))
            except Exception as e:
                logger.debug(f"Failed to get lineage for {node_id}: {e}")
                metadata['upstream_models'] = []
                metadata['upstream_sources'] = []
                metadata['downstream_models'] = []
                metadata['downstream_tests'] = []
        else:
            # Fallback to manifest depends_on
            depends_on = manifest_node.get('depends_on', {})
            metadata['upstream_models'] = [
                n for n in depends_on.get('nodes', []) 
                if n.startswith('model.')
            ]
            metadata['upstream_sources'] = [
                n for n in depends_on.get('nodes', []) 
                if n.startswith('source.')
            ]
            metadata['downstream_models'] = []
            metadata['downstream_tests'] = []
        
        return metadata
    
    def _get_materialization(self, manifest_node: Dict) -> str:
        """Extract materialization strategy from manifest node."""
        config = manifest_node.get('config', {})
        return config.get('materialized', 'view')
    
    def _get_column_metadata(self, manifest_node: Dict, 
                            catalog_node: Optional[Dict]) -> Dict[str, Any]:
        """Combine column metadata from manifest and catalog.
        
        Args:
            manifest_node: Node data from manifest
            catalog_node: Node data from catalog (optional)
            
        Returns:
            Dict mapping column names to metadata
        """
        columns = {}
        
        # Get columns from manifest (descriptions, tests)
        for col_name, col_data in manifest_node.get('columns', {}).items():
            columns[col_name] = {
                'name': col_name,
                'description': col_data.get('description', ''),
                'meta': col_data.get('meta', {}),
                'tags': col_data.get('tags', []),
            }
        
        # Enrich with catalog data (types, stats)
        if catalog_node:
            for col_name, col_data in catalog_node.get('columns', {}).items():
                if col_name not in columns:
                    columns[col_name] = {'name': col_name}
                
                columns[col_name].update({
                    'type': col_data.get('type', ''),
                    'index': col_data.get('index', 0),
                })
        
        return columns
    
    @staticmethod
    def detect_dbt_artifacts(file_paths: List[str]) -> Optional[str]:
        """Detect if file list contains DBT artifacts.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            Directory containing artifacts, or None if not found
            
        Example:
            files = [
                '/repo/dbt_anthem/target/manifest.json',
                '/repo/dbt_anthem/target/catalog.json',
                '/repo/dbt_anthem/dbt_project.yml'
            ]
            artifacts_dir = DBTArtifactParser.detect_dbt_artifacts(files)
            # Returns: '/repo/dbt_anthem/target'
        """
        required_files = ['manifest.json', 'dbt_project.yml']
        
        # Find files
        found_files = {}
        for file_path in file_paths:
            for required in required_files:
                if file_path.endswith(required):
                    found_files[required] = file_path
        
        # Check if all required files found
        if len(found_files) == len(required_files):
            # Extract directory from manifest.json path
            manifest_path = found_files['manifest.json']
            artifacts_dir = str(Path(manifest_path).parent)
            logger.info(f"[OK] Detected DBT artifacts in: {artifacts_dir}")
            return artifacts_dir
        
        return None
    
    def get_project_name(self) -> str:
        """Get DBT project name from config."""
        if self.project_config:
            return self.project_config.get('name', 'unknown_project')
        return 'unknown_project'
    
    def get_all_models(self) -> List[str]:
        """Get list of all model names.
        
        Returns:
            List of model unique IDs
        """
        return [
            node_id for node_id, node_data 
            in self.manifest.get('nodes', {}).items()
            if node_data.get('resource_type') == 'model'
        ]
    
    def get_all_sources(self) -> List[str]:
        """Get list of all source names.
        
        Returns:
            List of source unique IDs
        """
        return [
            source_id for source_id, source_data
            in self.manifest.get('sources', {}).items()
        ]
    
    def extract_sql_documents(self, include_compiled: bool = True) -> List[Dict[str, Any]]:
        """Extract all SQL code from manifest for embedding.
        
        Creates synthetic documents from manifest.json containing:
        - Models: raw_code or compiled_code with metadata
        - Tests: raw_code with validation logic
        - Macros: macro_sql with parameter info
        
        Args:
            include_compiled: If True, prefer compiled_code over raw_code for models
            
        Returns:
            List of documents ready for embedding, each with:
            - content: SQL code (compiled if available, otherwise raw)
            - metadata: Type, name, description, tags, lineage, etc.
            - summary: Human-readable summary with lineage context
            
        Example:
            documents = parser.extract_sql_documents(include_compiled=True)
            for doc in documents:
                if doc['metadata']['dbt_type'] == 'model':
                    print(f"Model: {doc['metadata']['dbt_name']}")
                    print(f"SQL: {doc['content'][:100]}...")
        """
        documents = []
        
        # 1. Extract Models (raw_code and compiled_code)
        for node_id, node in self.manifest.get('nodes', {}).items():
            if node.get('resource_type') != 'model':
                continue
            
            # Choose SQL: compiled_code if available and requested, otherwise raw_code
            sql_code = None
            code_type = 'raw'
            
            if include_compiled and node.get('compiled_code'):
                sql_code = node['compiled_code']
                code_type = 'compiled'
            elif node.get('raw_code'):
                sql_code = node['raw_code']
                code_type = 'raw'
            
            if not sql_code:
                logger.debug(f"No SQL code for model: {node.get('name')}")
                continue
            
            # Get metadata
            metadata = self.get_model_metadata(node_id)
            
            # Build summary with lineage context
            summary_parts = [
                f"DBT Model: {node.get('name')}",
                f"Type: {metadata.get('materialization', 'table')}",
                f"Schema: {node.get('schema', 'N/A')}"
            ]
            
            if node.get('description'):
                summary_parts.append(f"Description: {node['description']}")
            
            if metadata.get('upstream_models'):
                summary_parts.append(f"Depends on models: {', '.join(metadata['upstream_models'][:5])}")
            
            if metadata.get('upstream_sources'):
                summary_parts.append(f"Depends on sources: {', '.join(metadata['upstream_sources'][:5])}")
            
            if metadata.get('downstream_models'):
                summary_parts.append(f"Used by: {', '.join(metadata['downstream_models'][:3])}")
            
            documents.append({
                'content': sql_code,
                'metadata': {
                    'dbt_type': 'model',
                    'dbt_unique_id': node_id,
                    'dbt_name': node.get('name'),
                    'dbt_description': node.get('description', ''),
                    'dbt_tags': node.get('tags', []),
                    'dbt_schema': node.get('schema'),
                    'dbt_database': node.get('database'),
                    'dbt_materialization': metadata.get('materialization'),
                    'dbt_code_type': code_type,
                    'dbt_file_path': node.get('original_file_path', ''),
                    'dbt_upstream_models': metadata.get('upstream_models', []),
                    'dbt_upstream_sources': metadata.get('upstream_sources', []),
                    'dbt_downstream_models': metadata.get('downstream_models', []),
                    'lineage_depth': metadata.get('lineage_depth', 0)
                },
                'summary': '\n'.join(summary_parts)
            })
        
        # 2. Extract Tests (raw_code)
        for node_id, node in self.manifest.get('nodes', {}).items():
            if node.get('resource_type') != 'test':
                continue
            
            sql_code = node.get('raw_code')
            if not sql_code:
                continue
            
            # Get tested model from depends_on
            tested_model = None
            if node.get('depends_on', {}).get('nodes'):
                for dep_id in node['depends_on']['nodes']:
                    if dep_id.startswith('model.'):
                        tested_model = dep_id.split('.')[-1]
                        break
            
            summary_parts = [
                f"DBT Test: {node.get('name')}",
                f"Validates: {tested_model or 'N/A'}"
            ]
            
            if node.get('description'):
                summary_parts.append(f"Purpose: {node['description']}")
            
            documents.append({
                'content': sql_code,
                'metadata': {
                    'dbt_type': 'test',
                    'dbt_unique_id': node_id,
                    'dbt_name': node.get('name'),
                    'dbt_description': node.get('description', ''),
                    'dbt_tags': node.get('tags', []),
                    'dbt_tested_model': tested_model,
                    'dbt_file_path': node.get('original_file_path', '')
                },
                'summary': '\n'.join(summary_parts)
            })
        
        # 3. Extract Macros (macro_sql)
        for macro_id, macro in self.manifest.get('macros', {}).items():
            sql_code = macro.get('macro_sql')
            if not sql_code:
                continue
            
            # Extract argument names
            arg_names = [arg.get('name') for arg in macro.get('arguments', []) if arg.get('name')]
            
            summary_parts = [
                f"DBT Macro: {macro.get('name')}",
            ]
            
            if arg_names:
                summary_parts.append(f"Arguments: {', '.join(arg_names)}")
            
            if macro.get('description'):
                summary_parts.append(f"Description: {macro['description']}")
            
            documents.append({
                'content': sql_code,
                'metadata': {
                    'dbt_type': 'macro',
                    'dbt_unique_id': macro_id,
                    'dbt_name': macro.get('name'),
                    'dbt_description': macro.get('description', ''),
                    'dbt_arguments': arg_names,
                    'dbt_file_path': macro.get('original_file_path', '')
                },
                'summary': '\n'.join(summary_parts)
            })
        
        logger.info(f"[OK] Extracted {len(documents)} SQL documents from manifest")
        return documents
    
    def extract_seed_documents(self, csv_files: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract seed CSV files as documents for embedding.
        
        Args:
            csv_files: Dict mapping seed file paths to their content
                      Example: {'data/reference/seed_antiemetics.csv': 'code,name\nJ1234,...'}
            
        Returns:
            List of documents ready for embedding, each with:
            - content: CSV file content (full file or chunked)
            - metadata: Seed name, referencing models, columns, row count
            - summary: Human-readable summary with usage context
            
        Example:
            csv_files = {
                'data/reference/seed_antiemetics.csv': 'code,drug_name\nJ1234,Drug1\n...'
            }
            seed_docs = parser.extract_seed_documents(csv_files)
        """
        import csv
        from io import StringIO
        
        documents = []
        seed_refs = self.get_seed_references()
        
        # Process each CSV file
        for file_path, content in csv_files.items():
            # Extract seed name from path
            # Example: 'data/reference/seed_antiemetics.csv' -> 'seed_antiemetics'
            file_name = Path(file_path).stem
            
            # Find matching seed in manifest
            seed_node = None
            seed_node_id = None
            for node_id, node in self.manifest.get('nodes', {}).items():
                if node.get('resource_type') == 'seed' and node.get('name') == file_name:
                    seed_node = node
                    seed_node_id = node_id
                    break
            
            if not seed_node:
                logger.debug(f"Seed not found in manifest: {file_name}")
                continue
            
            # Parse CSV to get column info and row count
            try:
                csv_reader = csv.DictReader(StringIO(content))
                rows = list(csv_reader)
                columns = csv_reader.fieldnames or []
                row_count = len(rows)
            except Exception as e:
                logger.warning(f"Failed to parse CSV {file_name}: {e}")
                columns = []
                row_count = 0
                rows = []
            
            # Get models that reference this seed
            referencing_models = seed_refs.get(file_name, [])
            
            # Build summary
            summary_parts = [
                f"DBT Seed: {file_name}",
                f"File: {seed_node.get('original_file_path', file_path)}"
            ]
            
            if seed_node.get('description'):
                summary_parts.append(f"Description: {seed_node['description']}")
            
            if columns:
                summary_parts.append(f"Columns ({len(columns)}): {', '.join(columns)}")
            
            if row_count:
                summary_parts.append(f"Rows: {row_count}")
            
            if referencing_models:
                summary_parts.append(f"Used by models: {', '.join(referencing_models[:5])}")
                if len(referencing_models) > 5:
                    summary_parts.append(f"... and {len(referencing_models) - 5} more")
            
            # For large CSVs, include sample rows in summary
            if rows and len(rows) <= 100:
                # Small CSV - include full content
                doc_content = content
            elif rows:
                # Large CSV - include header + sample rows + statistics
                sample_size = min(10, len(rows))
                sample_rows = rows[:sample_size]
                
                # Format sample as CSV string
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(sample_rows)
                
                doc_content = output.getvalue()
                doc_content += f"\n\n[Note: Showing {sample_size} of {row_count} rows]"
            else:
                doc_content = content
            
            documents.append({
                'content': doc_content,
                'metadata': {
                    'dbt_type': 'seed',
                    'dbt_unique_id': seed_node_id,
                    'dbt_seed_name': file_name,
                    'dbt_description': seed_node.get('description', ''),
                    'dbt_tags': seed_node.get('tags', []),
                    'dbt_schema': seed_node.get('schema'),
                    'dbt_database': seed_node.get('database'),
                    'dbt_file_path': seed_node.get('original_file_path', file_path),
                    'dbt_referencing_models': referencing_models,
                    'csv_columns': columns,
                    'csv_row_count': row_count,
                    'csv_is_sample': row_count > 100
                },
                'summary': '\n'.join(summary_parts)
            })
        
        logger.info(f"[OK] Extracted {len(documents)} seed documents from CSV files")
        return documents
    
    def get_seed_references(self) -> Dict[str, List[str]]:
        """Get mapping of seed names to models that reference them.
        
        Returns:
            Dict mapping seed names to list of model names that use them
            
        Example:
            seed_refs = parser.get_seed_references()
            # {'seed_antiemetics': ['stg_qm2', 'stg_qm3']}
        """
        seed_refs = {}
        
        # Get all seeds
        for node_id, node in self.manifest.get('nodes', {}).items():
            if node.get('resource_type') == 'seed':
                seed_name = node.get('name')
                seed_refs[seed_name] = []
        
        # Find models that reference each seed
        for node_id, node in self.manifest.get('nodes', {}).items():
            if node.get('resource_type') != 'model':
                continue
            
            model_name = node.get('name')
            depends_on = node.get('depends_on', {}).get('nodes', [])
            
            for dep_id in depends_on:
                if dep_id.startswith('seed.'):
                    seed_name = dep_id.split('.')[-1]
                    if seed_name in seed_refs:
                        seed_refs[seed_name].append(model_name)
        
        return seed_refs
    
    def get_artifact_summary(self) -> Dict[str, Any]:
        """Get summary of loaded artifacts.
        
        Returns:
            Dict with counts and metadata
        """
        manifest_nodes = self.manifest.get('nodes', {})
        
        # Count by resource type
        type_counts = {}
        for node_data in manifest_nodes.values():
            resource_type = node_data.get('resource_type', 'unknown')
            type_counts[resource_type] = type_counts.get(resource_type, 0) + 1
        
        summary = {
            'project_name': self.get_project_name(),
            'artifacts_loaded': {
                'manifest': True,
                'catalog': self.catalog is not None,
                'graph_summary': self.graph is not None,
                'project_config': self.project_config is not None
            },
            'node_counts': type_counts,
            'total_nodes': len(manifest_nodes),
            'total_sources': len(self.manifest.get('sources', {})),
            'total_macros': len(self.manifest.get('macros', {}))
        }
        
        if self.graph:
            summary['graph_summary'] = self.graph.get_graph_summary()
        
        return summary
