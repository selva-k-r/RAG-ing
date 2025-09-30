"""Temporary files management utilities."""

import os
import shutil
import glob
from pathlib import Path
from typing import List, Optional
from ..config.settings import get_settings


class TempFileManager:
    """Manages temporary files in the designated temp_helper_codes directory."""
    
    def __init__(self, settings=None):
        """Initialize with settings."""
        self.settings = settings or get_settings()
        self.temp_dir = Path(self.settings.temp_files.directory)
        self.auto_cleanup = self.settings.temp_files.auto_cleanup
        self.file_types = self.settings.temp_files.file_types
        
        # Ensure temp directory exists
        self.temp_dir.mkdir(exist_ok=True)
    
    def get_temp_path(self, filename: str) -> Path:
        """Get full path for a temporary file."""
        return self.temp_dir / filename
    
    def create_temp_file(self, filename: str, content: str = "") -> Path:
        """Create a temporary file with given content."""
        temp_path = self.get_temp_path(filename)
        
        # Write content to file
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created temporary file: {temp_path}")
        return temp_path
    
    def list_temp_files(self, pattern: str = "*") -> List[Path]:
        """List all temporary files matching pattern."""
        return list(self.temp_dir.glob(pattern))
    
    def cleanup_by_pattern(self, pattern: str) -> int:
        """Clean up temporary files matching pattern. Returns count of deleted files."""
        files = self.list_temp_files(pattern)
        count = 0
        
        for file_path in files:
            try:
                if file_path.is_file():
                    file_path.unlink()
                    count += 1
                    print(f"Deleted temporary file: {file_path}")
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    count += 1
                    print(f"Deleted temporary directory: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        
        return count
    
    def cleanup_all(self, exclude: Optional[List[str]] = None) -> int:
        """Clean up all temporary files except those in exclude list."""
        exclude = exclude or []
        total_deleted = 0
        
        for file_type in self.file_types:
            files = self.list_temp_files(file_type)
            for file_path in files:
                if file_path.name not in exclude:
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                            total_deleted += 1
                            print(f"Deleted temporary file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
        
        return total_deleted
    
    def get_temp_size(self) -> int:
        """Get total size of temporary directory in bytes."""
        total_size = 0
        for file_path in self.temp_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def move_to_temp(self, source_path: str, new_name: Optional[str] = None) -> Path:
        """Move a file to temporary directory."""
        source = Path(source_path)
        target_name = new_name or source.name
        target_path = self.get_temp_path(target_name)
        
        if source.exists():
            shutil.move(str(source), str(target_path))
            print(f"Moved {source} to temporary directory: {target_path}")
        else:
            raise FileNotFoundError(f"Source file not found: {source}")
        
        return target_path


# Global instance for easy access
temp_manager = TempFileManager()


def get_temp_path(filename: str) -> Path:
    """Convenience function to get temporary file path."""
    return temp_manager.get_temp_path(filename)


def create_temp_file(filename: str, content: str = "") -> Path:
    """Convenience function to create temporary file."""
    return temp_manager.create_temp_file(filename, content)


def cleanup_temp_files(pattern: str = "*") -> int:
    """Convenience function to cleanup temporary files."""
    return temp_manager.cleanup_by_pattern(pattern)