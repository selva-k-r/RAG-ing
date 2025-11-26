# Debug Tools for RAG-ing Ingest Pipeline

This directory contains debugging utilities for the RAG-ing ingest pipeline to help developers identify and resolve issues.

## Directory Structure

```
debug_tools/
├── README.md                          # This file
├── run_all_checks.py                  # Master orchestrator - runs all checks
├── 01_check_config.py                 # Validate configuration files
├── 02_check_data_sources.py           # Test data source connectivity
├── 03_check_embedding_model.py        # Validate embedding model
├── 04_check_vector_store.py           # Test vector database
├── 05_check_tracker_database.py       # Validate SQLite tracker
├── 06_test_end_to_end.py              # Full pipeline test
├── logs/                              # Debug execution logs (gitignored)
└── reports/                           # Test reports and diagnostics (gitignored)
```

## Quick Start

### Run All Checks (Recommended)
```bash
# From project root
python debug_tools/run_all_checks.py
```

This runs all diagnostic checks and generates a comprehensive report.

### Run Individual Component Checks
```bash
# Check configuration only
python debug_tools/01_check_config.py

# Check data sources
python debug_tools/02_check_data_sources.py

# Check embedding model
python debug_tools/03_check_embedding_model.py

# Check vector store
python debug_tools/04_check_vector_store.py

# Check tracker database
python debug_tools/05_check_tracker_database.py

# Test end-to-end pipeline
python debug_tools/06_test_end_to_end.py
```

## What Each Tool Checks

### 01_check_config.py - Configuration Validation
- Validates config.yaml exists and is readable
- Checks all required fields are present
- Validates environment variables
- Reports missing or invalid settings
- **Fixes**: Missing Azure credentials, incorrect paths, invalid YAML syntax

### 02_check_data_sources.py - Data Source Connectivity
- Tests local file system access
- Validates Azure DevOps connectivity (if enabled)
- Checks Confluence connectivity (if enabled)
- Validates authentication tokens
- **Fixes**: Connection failures, authentication errors, path issues

### 03_check_embedding_model.py - Embedding Model Validation
- Tests Azure OpenAI embedding endpoint
- Validates API keys and deployment names
- Tests fallback models
- Measures embedding generation speed
- **Fixes**: API connection issues, authentication problems, model configuration

### 04_check_vector_store.py - Vector Database Testing
- Checks vector_store/ directory exists
- Tests ChromaDB initialization
- Validates existing collections
- Tests basic CRUD operations
- **Fixes**: Database corruption, permission issues, missing collections

### 05_check_tracker_database.py - SQLite Tracker Validation
- Checks ingestion_tracking.db exists
- Validates database schema
- Tests read/write operations
- Reports tracking statistics
- **Fixes**: Database corruption, missing tables, permission issues

### 06_test_end_to_end.py - Full Pipeline Test
- Runs complete ingestion on sample data
- Measures performance at each stage
- Validates data flows between components
- Reports final statistics
- **Fixes**: Integration issues, data flow problems

## Common Issues and Solutions

### Issue: Tracker Database Not Created
**Symptoms**: No ingestion_tracking.db file, errors during ingest
**Check**: `python debug_tools/05_check_tracker_database.py`
**Common Causes**:
- Write permission issues in project directory
- Database path not writable
- SQLite not installed

**Solutions**:
1. Check directory permissions: `ls -la /workspaces/RAG-ing/`
2. Create database manually: Script will auto-create
3. Check SQLite installation: `python -c "import sqlite3; print(sqlite3.version)"`

### Issue: No Documents Ingested
**Symptoms**: "0 documents processed" message
**Check**: `python debug_tools/02_check_data_sources.py`
**Common Causes**:
- Data source not enabled in config.yaml
- Wrong paths or credentials
- No files matching filter criteria

**Solutions**:
1. Check data_source.sources in config.yaml
2. Verify `enabled: true` for desired sources
3. Check include_paths and file_types filters

### Issue: Embedding Model Fails
**Symptoms**: "Failed to generate embeddings" errors
**Check**: `python debug_tools/03_check_embedding_model.py`
**Common Causes**:
- Missing Azure OpenAI credentials
- Wrong deployment name
- API quota exceeded

**Solutions**:
1. Check environment variables in .env file
2. Verify deployment name matches Azure portal
3. Check Azure OpenAI quota and limits

### Issue: Vector Store Errors
**Symptoms**: ChromaDB errors, "Collection not found"
**Check**: `python debug_tools/04_check_vector_store.py`
**Common Causes**:
- Corrupted ChromaDB files
- Wrong collection name
- Disk space full

**Solutions**:
1. Delete vector_store/ directory and reingest
2. Check collection_name in config.yaml
3. Check disk space: `df -h`

## Understanding the Ingest Pipeline Flow

```
1. main.py (Entry Point)
   └─> Parses CLI arguments (--ingest flag)
   
2. orchestrator.py (Coordination Layer)
   └─> Loads config.yaml
   └─> Initializes all 5 modules
   └─> Calls corpus_embedding.process_corpus()
   
3. corpus_embedding.py (Module 1)
   └─> Initializes IngestionTrackerSQLite
   └─> Loads data from enabled sources
   └─> Chunks documents
   └─> Generates embeddings
   └─> Stores in vector database
   └─> Updates tracker database
   
4. ingestion_tracker_sqlite.py (Tracking Layer)
   └─> Creates ingestion_tracking.db
   └─> Tracks documents processed
   └─> Detects duplicates
   └─> Provides statistics
```

## Debug Output Locations

All debug outputs are stored in this directory and are gitignored:

- **Logs**: `debug_tools/logs/` - Detailed execution logs
- **Reports**: `debug_tools/reports/` - HTML/JSON diagnostic reports
- **Test Data**: `debug_tools/test_data/` - Sample data for testing

## Tips for Effective Debugging

1. **Start with run_all_checks.py**: Gets complete system overview
2. **Read the logs**: Check `debug_tools/logs/` for detailed errors
3. **Run checks after fixes**: Verify your changes work
4. **Check environment first**: Most issues are configuration-related
5. **Enable debug logging**: Use `--debug` flag with main.py

## Adding New Debug Tools

To add a new debug tool:

1. Create a new script following the naming pattern: `07_check_feature.py`
2. Follow the structure of existing scripts
3. Add to run_all_checks.py
4. Update this README with description
5. Use ASCII-safe output (no emojis)

## Developer Notes

- **All scripts are standalone**: Can run independently
- **No emojis in code**: Uses ASCII characters only for Windows compatibility
- **Clear error messages**: Includes system error + solution
- **JSON output**: Structured for automation/CI
- **Git-ignored outputs**: Debug data stays local
