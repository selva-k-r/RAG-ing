# Temporary Helper Codes

This folder contains **all temporary files** created during development, testing, and experimentation. These files are not part of the core RAG system functionality but are useful for development, prototyping, and quick testing.

## Purpose

🎯 **Designated temporary files directory** - As configured in `config.yaml`, this folder is the centralized location for:
- Development scripts and prototypes
- Testing utilities and experimental code  
- Temporary Python files, markdown, HTML, JSON, and text files
- Helper scripts for debugging and analysis
- Any files not directly related to the core project structure

## Contents

### 🧪 Testing Scripts
- **`test_confluence.py`** - Script to test Confluence API connectivity and explore available spaces
- **`test_server.py`** - Server testing utilities and endpoint validation
- **`demo.py`** - Demonstration script for system capabilities

### 🌐 HTML Testing Files
- **`index.html`** - Basic HTML interface testing
- **`faq1.html` - `faq5.html`** - FAQ response testing pages for prompt engineering analysis

### 📚 Content Fetching Utilities
- **`get_hl7_content.py`** - Script to fetch HL7 FHIR content from public endpoints when Confluence API was blocked

### 🌐 Legacy UI Components
- **`web_app_old.py`** - Original monolithic FastAPI application (replaced by modular ui/ structure)

### 📖 Development Documentation
- **`PROMPT_ENGINEERING_ANALYSIS.md`** - Analysis of FAQ response patterns for prompt engineering
- **`AZURE_OPENAI_SETUP.md`** - Azure OpenAI configuration guide and setup instructions

## Automatic Management

The system includes utilities for managing temporary files:

```python
# Import temporary file utilities
from rag_ing.utils import get_temp_path, create_temp_file, cleanup_temp_files

# Create a temporary file
temp_path = create_temp_file("my_script.py", "print('Hello from temp!')")

# Get path for temporary file
file_path = get_temp_path("test_data.json")

# Clean up temporary files by pattern
deleted_count = cleanup_temp_files("*.log")
```

## Configuration

Temporary files behavior is controlled in `config.yaml`:

```yaml
temp_files:
  directory: "./temp_helper_codes"
  auto_cleanup: false  # Set to true for automatic cleanup
  file_types: ["*.py", "*.md", "*.txt", "*.html", "*.json", "*.yaml", "*.log"]
```

## Usage

These scripts can be run independently for testing purposes:

```bash
# Test Confluence connectivity
python temp_helper_codes/test_confluence.py

# Fetch additional HL7 content
python temp_helper_codes/get_hl7_content.py

# Run demo functionality
python temp_helper_codes/demo.py
```

## Note

⚠️ **All new temporary files should be created in this directory** to maintain project organization and enable automated cleanup when needed.

These files are kept for reference and potential future use but are not required for the core RAG system operation. The main system operates through:
- `main.py` - CLI interface
- `web_app.py` - FastAPI web interface
- `src/rag_ing/` - Core modules

## Clean Up

These files can be safely deleted if not needed for development purposes, as they don't affect the core system functionality.