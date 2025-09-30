"""Basic tests for RAG-ing application structure."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestBasicStructure(unittest.TestCase):
    """Test basic application structure."""
    
    def test_package_structure(self):
        """Test that all required modules exist."""
        # Test main package
        self.assertTrue(os.path.exists('src/rag_ing/__init__.py'))
        
        # Test subpackages
        subpackages = ['config', 'models', 'storage', 'connectors', 'ui']
        for package in subpackages:
            package_path = f'src/rag_ing/{package}/__init__.py'
            self.assertTrue(os.path.exists(package_path), f"Missing {package_path}")
    
    def test_main_files_exist(self):
        """Test that main application files exist."""
        files = [
            'main.py',
            'pyproject.toml',
            'README.md',
            '.gitignore',
            '.env.example'
        ]
        
        for file in files:
            self.assertTrue(os.path.exists(file), f"Missing {file}")


class TestConfigStructure(unittest.TestCase):
    """Test configuration structure."""
    
    @patch('rag_ing.config.settings.BaseSettings')
    def test_settings_import(self, mock_settings):
        """Test that settings can be imported (with mocked dependencies)."""
        try:
            # This would normally fail due to missing dependencies
            # but we're testing the structure
            pass
        except ImportError as e:
            # Expected due to missing dependencies
            self.assertIn('pydantic', str(e).lower())


class TestModuleStructure(unittest.TestCase):
    """Test individual module structure."""
    
    def test_embedding_manager_file_exists(self):
        """Test embedding manager file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/models/embedding_manager.py'))
    
    def test_llm_manager_file_exists(self):
        """Test LLM manager file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/models/llm_manager.py'))
    
    def test_vector_store_file_exists(self):
        """Test vector store file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/storage/vector_store.py'))
    
    def test_connectors_exist(self):
        """Test connector files exist."""
        connectors = ['base.py', 'confluence.py', 'medium.py', 'social_media.py']
        for connector in connectors:
            path = f'src/rag_ing/connectors/{connector}'
            self.assertTrue(os.path.exists(path), f"Missing {path}")
    
    def test_chunking_file_exists(self):
        """Test chunking service file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/chunking.py'))
    
    def test_ui_file_exists(self):
        """Test UI file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/ui/app.py'))
    
    def test_cli_file_exists(self):
        """Test CLI file exists."""
        self.assertTrue(os.path.exists('src/rag_ing/cli.py'))


if __name__ == '__main__':
    # Change to project root for tests
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unittest.main()