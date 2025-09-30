# Temporary Helper Codes

This folder contains temporary and helper scripts created during development and testing phases. These files are not part of the core RAG system functionality but were useful for development, testing, and experimentation.

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

## Purpose

These files were created to:
- Test external API integrations (Confluence, HL7)
- Experiment with different UI approaches
- Validate system connectivity and functionality
- Support prompt engineering and response analysis
- Document setup procedures for Azure OpenAI integration
- Analyze response patterns for improving AI outputs

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

These files are kept for reference and potential future use but are not required for the core RAG system operation. The main system operates through:
- `main.py` - CLI interface
- `web_app.py` - FastAPI web interface
- `src/rag_ing/` - Core modules

## Clean Up

These files can be safely deleted if not needed for development purposes, as they don't affect the core system functionality.