"""Unit tests for DBT lineage graph and artifact parser.

Tests the core DBT integration components:
- DBTLineageGraph: In-memory graph traversal
- DBTArtifactParser: Artifact parsing and metadata extraction
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from src.rag_ing.utils.dbt_lineage import DBTLineageGraph
from src.rag_ing.utils.dbt_artifacts import DBTArtifactParser


# Test fixtures
@pytest.fixture
def sample_graph_data():
    """Sample graph_summary.json data."""
    return {
        "_invocation_id": "test-invocation-123",
        "linked": {
            "0": {
                "name": "source.test_project.raw.customers",
                "type": "source",
                "succ": [1]
            },
            "1": {
                "name": "model.test_project.stg_customers",
                "type": "model",
                "succ": [2, 3]
            },
            "2": {
                "name": "model.test_project.dim_customers",
                "type": "model",
                "succ": [4]
            },
            "3": {
                "name": "test.test_project.unique_stg_customers",
                "type": "test",
                "succ": []
            },
            "4": {
                "name": "model.test_project.fct_orders",
                "type": "model",
                "succ": []
            }
        }
    }


@pytest.fixture
def sample_manifest_data():
    """Sample manifest.json data."""
    return {
        "nodes": {
            "model.test_project.dim_customers": {
                "name": "dim_customers",
                "description": "Customer dimension table",
                "schema": "analytics",
                "database": "warehouse",
                "resource_type": "model",
                "package_name": "test_project",
                "tags": ["dimension", "customer"],
                "meta": {"owner": "data_team"},
                "config": {"materialized": "table"},
                "columns": {
                    "customer_id": {
                        "name": "customer_id",
                        "description": "Unique customer identifier"
                    },
                    "customer_name": {
                        "name": "customer_name",
                        "description": "Customer full name"
                    }
                },
                "depends_on": {
                    "nodes": ["model.test_project.stg_customers"]
                }
            }
        },
        "sources": {
            "source.test_project.raw.customers": {
                "name": "customers",
                "source_name": "raw",
                "schema": "raw_data",
                "database": "warehouse"
            }
        }
    }


@pytest.fixture
def sample_catalog_data():
    """Sample catalog.json data."""
    return {
        "nodes": {
            "model.test_project.dim_customers": {
                "columns": {
                    "customer_id": {
                        "name": "customer_id",
                        "type": "INTEGER",
                        "index": 1
                    },
                    "customer_name": {
                        "name": "customer_name",
                        "type": "VARCHAR",
                        "index": 2
                    }
                },
                "metadata": {
                    "type": "TABLE",
                    "schema": "analytics"
                }
            }
        }
    }


@pytest.fixture
def temp_artifacts_dir(sample_graph_data, sample_manifest_data, sample_catalog_data):
    """Create temporary directory with sample artifacts."""
    temp_dir = tempfile.mkdtemp()
    
    # Write graph_summary.json
    with open(Path(temp_dir) / 'graph_summary.json', 'w') as f:
        json.dump(sample_graph_data, f)
    
    # Write manifest.json
    with open(Path(temp_dir) / 'manifest.json', 'w') as f:
        json.dump(sample_manifest_data, f)
    
    # Write catalog.json
    with open(Path(temp_dir) / 'catalog.json', 'w') as f:
        json.dump(sample_catalog_data, f)
    
    # Write dbt_project.yml
    with open(Path(temp_dir) / 'dbt_project.yml', 'w') as f:
        f.write('name: test_project\nversion: 1.0.0\n')
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestDBTLineageGraph:
    """Tests for DBTLineageGraph class."""
    
    def test_load_graph(self, temp_artifacts_dir):
        """Test loading graph from file."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        assert graph.invocation_id == "test-invocation-123"
        assert len(graph.nodes) == 5
        assert len(graph.name_to_id) == 5
    
    def test_get_node(self, temp_artifacts_dir):
        """Test getting node by name."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        node = graph.get_node('model.test_project.dim_customers')
        assert node is not None
        assert node['name'] == 'model.test_project.dim_customers'
        assert node['type'] == 'model'
        assert node['id'] == '2'
    
    def test_get_downstream(self, temp_artifacts_dir):
        """Test getting downstream dependencies."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        # Test direct downstream
        downstream = graph.get_downstream('model.test_project.stg_customers')
        assert len(downstream) == 2
        assert 'model.test_project.dim_customers' in downstream
        assert 'test.test_project.unique_stg_customers' in downstream
        
        # Test filtered downstream (models only)
        models_only = graph.get_downstream(
            'model.test_project.stg_customers',
            filter_type='model'
        )
        assert len(models_only) == 1
        assert 'model.test_project.dim_customers' in models_only
    
    def test_get_upstream(self, temp_artifacts_dir):
        """Test getting upstream dependencies."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        # Test direct upstream
        upstream = graph.get_upstream('model.test_project.dim_customers')
        assert len(upstream) == 1
        assert 'model.test_project.stg_customers' in upstream
        
        # Test recursive upstream
        all_upstream = graph.get_upstream(
            'model.test_project.dim_customers',
            recursive=True
        )
        assert len(all_upstream) >= 2  # stg_customers + source
        
        # Test filtered upstream (sources only)
        sources = graph.get_upstream(
            'model.test_project.dim_customers',
            recursive=True,
            filter_type='source'
        )
        assert len(sources) == 1
        assert 'source.test_project.raw.customers' in sources
    
    def test_get_lineage_stats(self, temp_artifacts_dir):
        """Test getting lineage statistics."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        stats = graph.get_lineage_stats('model.test_project.dim_customers')
        
        assert stats['name'] == 'model.test_project.dim_customers'
        assert stats['type'] == 'model'
        assert stats['direct_upstream'] == 1
        assert stats['direct_downstream'] == 1
        assert stats['upstream_sources'] == 1
    
    def test_get_graph_summary(self, temp_artifacts_dir):
        """Test getting overall graph summary."""
        graph_path = Path(temp_artifacts_dir) / 'graph_summary.json'
        graph = DBTLineageGraph(str(graph_path))
        
        summary = graph.get_graph_summary()
        
        assert summary['total_nodes'] == 5
        assert summary['node_types']['model'] == 3
        assert summary['node_types']['source'] == 1
        assert summary['node_types']['test'] == 1


class TestDBTArtifactParser:
    """Tests for DBTArtifactParser class."""
    
    def test_load_artifacts(self, temp_artifacts_dir):
        """Test loading all artifacts."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        
        assert parser.manifest is not None
        assert parser.catalog is not None
        assert parser.graph is not None
        assert parser.project_config is not None
    
    def test_get_model_metadata(self, temp_artifacts_dir):
        """Test getting complete model metadata."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        
        # Test with full name
        metadata = parser.get_model_metadata('model.test_project.dim_customers')
        
        assert metadata['name'] == 'dim_customers'
        assert metadata['description'] == 'Customer dimension table'
        assert metadata['schema'] == 'analytics'
        assert metadata['materialization'] == 'table'
        assert 'dimension' in metadata['tags']
        assert metadata['owner'] == 'data_team'
        
        # Check column metadata
        assert 'customer_id' in metadata['columns']
        assert metadata['columns']['customer_id']['description'] == 'Unique customer identifier'
        assert metadata['columns']['customer_id']['type'] == 'INTEGER'
        
        # Check lineage
        assert 'model.test_project.stg_customers' in metadata['upstream_models']
        assert 'model.test_project.fct_orders' in metadata['downstream_models']
    
    def test_get_model_metadata_by_simple_name(self, temp_artifacts_dir):
        """Test getting metadata by simple model name."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        
        metadata = parser.get_model_metadata('dim_customers')
        assert metadata['name'] == 'dim_customers'
    
    def test_detect_dbt_artifacts(self):
        """Test detecting DBT artifacts in file list."""
        file_paths = [
            '/repo/dbt_project/target/manifest.json',
            '/repo/dbt_project/target/catalog.json',
            '/repo/dbt_project/dbt_project.yml',
            '/repo/dbt_project/models/dim_customers.sql'
        ]
        
        artifacts_dir = DBTArtifactParser.detect_dbt_artifacts(file_paths)
        assert artifacts_dir == '/repo/dbt_project/target'
    
    def test_detect_no_artifacts(self):
        """Test that None is returned when artifacts not found."""
        file_paths = [
            '/repo/project/models/model.sql',
            '/repo/project/README.md'
        ]
        
        artifacts_dir = DBTArtifactParser.detect_dbt_artifacts(file_paths)
        assert artifacts_dir is None
    
    def test_get_project_name(self, temp_artifacts_dir):
        """Test getting project name."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        assert parser.get_project_name() == 'test_project'
    
    def test_get_all_models(self, temp_artifacts_dir):
        """Test getting all model names."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        models = parser.get_all_models()
        
        assert len(models) == 1
        assert 'model.test_project.dim_customers' in models
    
    def test_get_artifact_summary(self, temp_artifacts_dir):
        """Test getting artifact summary."""
        parser = DBTArtifactParser(temp_artifacts_dir)
        summary = parser.get_artifact_summary()
        
        assert summary['project_name'] == 'test_project'
        assert summary['artifacts_loaded']['manifest'] is True
        assert summary['artifacts_loaded']['catalog'] is True
        assert summary['artifacts_loaded']['graph_summary'] is True
        assert summary['total_nodes'] == 1
        assert summary['total_sources'] == 1


class TestDBTIntegration:
    """Integration tests using real DBT artifacts."""
    
    @pytest.mark.skipif(
        not Path('./temp/dbt_samples/manifest.json').exists(),
        reason="Real DBT artifacts not available"
    )
    def test_real_artifacts(self):
        """Test with real anthem_dev artifacts."""
        parser = DBTArtifactParser('./temp/dbt_samples')
        
        # Test loading
        assert parser.manifest is not None
        assert parser.graph is not None
        
        # Test metadata retrieval
        summary = parser.get_artifact_summary()
        assert summary['total_nodes'] > 100  # anthem_dev has 139+ models
        
        # Test lineage
        if parser.graph:
            graph_summary = parser.graph.get_graph_summary()
            assert graph_summary['total_nodes'] > 900  # anthem_dev has 967 nodes
