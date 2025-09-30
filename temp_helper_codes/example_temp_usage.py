#!/usr/bin/env python3
"""
Example script showing how to use the temporary files utilities.

This demonstrates the proper way to create and manage temporary files
within the RAG-ing project structure.
"""

import sys
import os
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rag_ing.utils import get_temp_path, create_temp_file, cleanup_temp_files, temp_manager


def demo_temp_files():
    """Demonstrate temporary file operations."""
    print("🗂️  Temporary Files Management Demo")
    print("=" * 50)
    
    # 1. Create a temporary Python script
    print("\n1. Creating temporary Python script...")
    script_content = '''#!/usr/bin/env python3
"""A temporary test script."""

def hello_world():
    print("Hello from temporary script!")
    return "success"

if __name__ == "__main__":
    result = hello_world()
    print(f"Script result: {result}")
'''
    
    temp_script = create_temp_file("test_script.py", script_content)
    print(f"   ✅ Created: {temp_script}")
    
    # 2. Create a temporary markdown file
    print("\n2. Creating temporary markdown file...")
    md_content = """# Temporary Documentation
    
This is a test markdown file for demonstration purposes.

## Features
- Auto-managed in temp_helper_codes directory
- Can be cleaned up automatically
- Follows project organization standards
"""
    
    temp_md = create_temp_file("test_docs.md", md_content)
    print(f"   ✅ Created: {temp_md}")
    
    # 3. Create a temporary JSON file
    print("\n3. Creating temporary JSON configuration...")
    json_content = """{
    "test_config": {
        "enabled": true,
        "version": "1.0.0",
        "description": "Temporary configuration for testing"
    }
}"""
    
    temp_json = create_temp_file("test_config.json", json_content)
    print(f"   ✅ Created: {temp_json}")
    
    # 4. List all temporary files
    print("\n4. Listing all temporary files...")
    temp_files = temp_manager.list_temp_files()
    for temp_file in temp_files:
        size = temp_file.stat().st_size if temp_file.is_file() else 0
        print(f"   📄 {temp_file.name} ({size} bytes)")
    
    # 5. Show total size
    total_size = temp_manager.get_temp_size()
    print(f"\n   📊 Total temp directory size: {total_size:,} bytes")
    
    # 6. Get specific temp file path (without creating it)
    print("\n5. Getting path for future temp file...")
    future_path = get_temp_path("future_file.txt")
    print(f"   📍 Future file path: {future_path}")
    
    print("\n" + "=" * 50)
    print("✅ Demo completed! Check temp_helper_codes/ directory to see the files.")
    print("\nTo clean up test files, run:")
    print("   python -c \"from rag_ing.utils import cleanup_temp_files; cleanup_temp_files('test_*')\"")


if __name__ == "__main__":
    demo_temp_files()