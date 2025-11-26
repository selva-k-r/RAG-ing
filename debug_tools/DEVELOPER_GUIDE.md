# Developer Debugging Guide for RAG-ing Ingest Pipeline

## Overview

This guide helps developers debug the RAG-ing document ingestion pipeline step by step. The pipeline has 5 main components that work together to process documents.

## Pipeline Architecture

```
User Input (--ingest)
    |
    v
main.py (CLI Entry Point)
    |
    v
orchestrator.py (Coordination)
    |
    v
corpus_embedding.py (Module 1)
    |
    +-> Data Sources (local/Azure DevOps/Confluence)
    +-> Chunking (recursive/semantic)
    +-> Embedding (Azure OpenAI/HuggingFace)
    +-> Vector Store (ChromaDB/FAISS)
    +-> Tracker Database (SQLite)
```

## Quick Debugging

### Step 1: Run All Checks
```bash
python debug_tools/run_all_checks.py
```

This runs all diagnostic checks and reports issues. Start here!

### Step 2: Fix Issues Based on Output

The tool will tell you which components failed. Fix them in this order:

1. **Configuration** - Always fix first
2. **Tracker Database** - Core tracking system
3. **Data Sources** - Where documents come from
4. **Embedding Model** - How documents are vectorized
5. **Vector Store** - Where embeddings are saved

### Step 3: Re-run Checks
```bash
python debug_tools/run_all_checks.py
```

Verify all checks pass before running ingestion.

### Step 4: Run Ingestion
```bash
python main.py --ingest
```

Monitor output for errors.

---

## Component-by-Component Debugging

### Component 1: Configuration (config.yaml + .env)

**What it does**: Central configuration for all components

**Debug command**:
```bash
python debug_tools/01_check_config.py
```

**Common issues**:

1. **config.yaml not found**
   - **Symptom**: "Configuration file not found"
   - **Check**: `ls -la config.yaml`
   - **Fix**: Ensure you're in project root directory

2. **Invalid YAML syntax**
   - **Symptom**: "YAML syntax: INVALID"
   - **Check**: YAML structure and indentation
   - **Fix**: Use spaces not tabs, validate at yamllint.com

3. **Missing environment variables**
   - **Symptom**: "NOT SET (required)"
   - **Check**: `.env` file exists and contains values
   - **Fix**: Copy from `env.example`, fill in actual values
   ```bash
   cp env.example .env
   # Edit .env with real credentials
   ```

4. **No data sources enabled**
   - **Symptom**: "No data sources enabled"
   - **Check**: `data_source.sources[].enabled` in config.yaml
   - **Fix**: Set `enabled: true` for at least one source

**Expected output when working**:
```
[OK] config.yaml: Found and readable
[OK] YAML syntax: Valid
[OK] Pydantic validation: PASSED
[OK] All configuration checks passed!
```

---

### Component 2: Tracker Database (SQLite)

**What it does**: Tracks which documents have been processed to avoid duplicates and enable incremental updates

**Debug command**:
```bash
python debug_tools/05_check_tracker_database.py
```

**Common issues**:

1. **Database file not created**
   - **Symptom**: "Database file not found"
   - **Status**: This is NORMAL on first run
   - **What happens**: Database auto-creates during first ingestion
   - **No action needed**: Just run ingestion

2. **Write permission denied**
   - **Symptom**: "Write permissions: DENIED"
   - **Check**: Directory permissions
   ```bash
   ls -la /workspaces/RAG-ing/
   ```
   - **Fix**: Run from writable directory or fix permissions

3. **Schema errors**
   - **Symptom**: "Table 'documents' not found"
   - **Status**: Normal if database is brand new
   - **Fix**: Schema auto-creates on first use

4. **No documents tracked**
   - **Symptom**: "No documents tracked yet"
   - **Status**: Normal before first ingestion
   - **Action**: Run `python main.py --ingest`

**Expected output when working**:
```
[OK] SQLite available: version 3.x.x
[OK] Write permissions: OK
[OK] Tracker class working
[!] Database will be created on first ingestion
```

**After first ingestion**:
```
[OK] Database file exists: ./ingestion_tracking.db
[OK] Table 'documents' exists
[OK] Tracking statistics:
    Total documents: 150
    Total chunks: 1,234
```

---

### Component 3: Data Sources

**What it does**: Fetches documents from various sources (local files, Azure DevOps, Confluence)

**Debug command**:
```bash
python debug_tools/02_check_data_sources.py
```

**Common issues**:

1. **Local files not found**
   - **Symptom**: "Directory not found: ./data/"
   - **Check**: Data directory exists with files
   ```bash
   ls -la ./data/
   ```
   - **Fix**: Create directory and add sample files
   ```bash
   mkdir -p ./data
   cp sample_doc.txt ./data/
   ```

2. **Azure DevOps connection failed**
   - **Symptom**: "Authentication failed" or "Connection timeout"
   - **Check**: Environment variables and network
   ```bash
   echo $AZURE_DEVOPS_PAT
   curl -u :$AZURE_DEVOPS_PAT https://dev.azure.com/$AZURE_DEVOPS_ORG
   ```
   - **Fix**: 
     - Verify PAT token is valid
     - Check organization/project names
     - Verify network connectivity

3. **No files match filter criteria**
   - **Symptom**: "0 files found matching criteria"
   - **Check**: `include_file_types` and `include_paths` in config.yaml
   - **Fix**: Adjust filters or add matching files

**Expected output when working**:
```
[OK] Local file source: 3 files found
[OK] Azure DevOps: Connected
[OK] Repository accessible: dbt-pophealth
    Files matching filter: 152
```

---

### Component 4: Embedding Model

**What it does**: Converts text chunks into vector embeddings for semantic search

**Debug command**:
```bash
python debug_tools/03_check_embedding_model.py
```

**Common issues**:

1. **Azure OpenAI credentials missing**
   - **Symptom**: "Authentication failed"
   - **Check**: Environment variables
   ```bash
   echo $AZURE_OPENAI_EMBEDDING_API_KEY
   echo $AZURE_OPENAI_EMBEDDING_ENDPOINT
   ```
   - **Fix**: Set credentials in .env file

2. **Wrong deployment name**
   - **Symptom**: "Deployment not found"
   - **Check**: config.yaml vs Azure portal
   - **Fix**: Update `azure_deployment_name` in config.yaml to match Azure

3. **API quota exceeded**
   - **Symptom**: "Rate limit exceeded" or "429 error"
   - **Check**: Azure portal quota usage
   - **Fix**: Wait or increase quota

4. **Fallback model download failed**
   - **Symptom**: "Failed to load model" (HuggingFace)
   - **Check**: Internet connectivity
   - **Fix**: Ensure network access or pre-download model

**Expected output when working**:
```
[OK] Azure OpenAI endpoint: Reachable
[OK] API key: Valid
[OK] Deployment: text-embedding-ada-002
[OK] Test embedding: Generated successfully (1536 dimensions)
```

---

### Component 5: Vector Store

**What it does**: Stores document embeddings and enables similarity search

**Debug command**:
```bash
python debug_tools/04_check_vector_store.py
```

**Common issues**:

1. **ChromaDB directory not found**
   - **Symptom**: "Vector store directory not found"
   - **Status**: Normal before first ingestion
   - **Fix**: Auto-creates during ingestion

2. **Collection not found**
   - **Symptom**: "Collection 'rag_documents' not found"
   - **Status**: Normal before first ingestion
   - **Action**: Run ingestion to create

3. **Corrupted database**
   - **Symptom**: "Failed to open database" or "Integrity error"
   - **Check**: Database files
   ```bash
   ls -la ./vector_store/
   ```
   - **Fix**: Delete and rebuild
   ```bash
   rm -rf ./vector_store/
   python main.py --ingest
   ```

4. **Disk space full**
   - **Symptom**: "No space left on device"
   - **Check**: Disk usage
   ```bash
   df -h
   ```
   - **Fix**: Free up space or use different location

**Expected output when working**:
```
[OK] ChromaDB: Available
[OK] Vector store directory: ./vector_store
[OK] Collection 'rag_documents': Found (1,234 chunks)
[OK] Test query: Working
```

---

## End-to-End Pipeline Test

**Debug command**:
```bash
python debug_tools/06_test_end_to_end.py
```

This runs a complete ingestion on sample data and reports performance metrics.

**What it tests**:
1. Load configuration
2. Fetch documents from enabled sources
3. Chunk documents
4. Generate embeddings
5. Store in vector database
6. Update tracker database
7. Verify data flows

**Expected output**:
```
[OK] Configuration loaded
[OK] Documents fetched: 3 files
[OK] Chunks created: 42 chunks
[OK] Embeddings generated: 42 vectors
[OK] Vector store updated: 42 chunks stored
[OK] Tracker updated: 3 documents tracked
[OK] Pipeline test: PASSED
```

---

## Troubleshooting Workflow

### Problem: "No documents processed"

**Symptom**: Ingestion completes but reports "0 documents processed"

**Debug steps**:

1. Check data sources are enabled:
   ```bash
   python debug_tools/01_check_config.py | grep "enabled"
   ```

2. Verify data source connectivity:
   ```bash
   python debug_tools/02_check_data_sources.py
   ```

3. Check file filters:
   - Look at `include_paths` and `include_file_types` in config.yaml
   - Ensure files exist that match these criteria

4. Check logs:
   ```bash
   tail -50 logs/evaluation.jsonl
   ```

**Solution**: Enable at least one data source and ensure files match filter criteria

---

### Problem: "Tracker database not working"

**Symptom**: Errors mentioning "ingestion_tracking.db" or duplicate processing

**Debug steps**:

1. Run tracker check:
   ```bash
   python debug_tools/05_check_tracker_database.py
   ```

2. Check if database exists:
   ```bash
   ls -la ingestion_tracking.db
   ```

3. Check write permissions:
   ```bash
   touch test_write.tmp && rm test_write.tmp
   ```

4. Try manual initialization:
   ```python
   from src.rag_ing.utils.ingestion_tracker_sqlite import IngestionTrackerSQLite
   tracker = IngestionTrackerSQLite()
   print(tracker.get_statistics())
   ```

**Solution**: Database should auto-create. If permission errors, fix directory permissions.

---

### Problem: "Embedding generation failed"

**Symptom**: Errors during embedding generation

**Debug steps**:

1. Check embedding model:
   ```bash
   python debug_tools/03_check_embedding_model.py
   ```

2. Verify Azure credentials:
   ```bash
   cat .env | grep AZURE_OPENAI_EMBEDDING
   ```

3. Test API manually:
   ```bash
   curl -X POST $AZURE_OPENAI_EMBEDDING_ENDPOINT/openai/deployments/$AZURE_OPENAI_DEPLOYMENT/embeddings?api-version=2023-05-15 \
     -H "api-key: $AZURE_OPENAI_EMBEDDING_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": "test"}'
   ```

**Solution**: Fix credentials or deployment name in config.yaml

---

## Understanding Log Output

### Normal Ingestion Logs

```
[OK] Configuration loaded from: ./config.yaml
Step 1: Multi-source document ingestion
[OK] Loaded tracking database: 0 documents, 0 chunks
[OK] Fetching from local_file source
[OK] Found 3 files matching criteria
Step 2: Document chunking
[OK] Created 42 chunks using recursive strategy
Step 3: Loading embedding model
[OK] Azure OpenAI embedding model loaded
Step 4: Setting up vector store and storing embeddings
[OK] Vector store initialized
[OK] Stored 42 embeddings
Step 5: Validating embedding model
[OK] Validation test passed

CORPUS PROCESSING COMPLETED SUCCESSFULLY
Documents ingested: 3
Chunks created: 42
READY TO SEARCH - 42 chunks available for queries
```

### Error Logs

```
[X] Failed to fetch documents from azure_devops
    Error: Authentication failed
    System Error: HTTP 401 Unauthorized
    
Solution:
  - Check AZURE_DEVOPS_PAT environment variable
  - Verify PAT token has 'Code (Read)' permissions
  - Check organization and project names
```

---

## Best Practices for Debugging

1. **Always start with configuration check**
   - Most issues stem from configuration
   - Quick to run and validates everything

2. **Check one component at a time**
   - Isolate the problem
   - Easier to understand and fix

3. **Read the error messages carefully**
   - System error codes are included
   - Solutions are provided

4. **Use debug mode for detailed logs**
   ```bash
   python main.py --ingest --debug
   ```

5. **Check the tracker database for ingestion history**
   ```bash
   python debug_tools/05_check_tracker_database.py
   ```

6. **Re-run checks after fixes**
   - Verify your solution worked
   - Ensure no new issues introduced

7. **Keep debug outputs local**
   - debug_tools/ is gitignored
   - Safe to generate reports and logs

---

## Getting Help

If you're still stuck after trying these debugging steps:

1. **Collect diagnostic information**:
   ```bash
   python debug_tools/run_all_checks.py --save
   ```

2. **Check the generated report**:
   ```
   debug_tools/reports/diagnostic_report_TIMESTAMP.json
   ```

3. **Share relevant logs** from:
   - debug_tools/logs/
   - logs/evaluation.jsonl
   - Terminal output

4. **Include system information**:
   - Python version: `python --version`
   - OS: `uname -a`
   - Disk space: `df -h`

---

## Quick Reference Commands

```bash
# Run all checks
python debug_tools/run_all_checks.py

# Quick checks only (essential components)
python debug_tools/run_all_checks.py --quick

# Save detailed report
python debug_tools/run_all_checks.py --save

# Individual component checks
python debug_tools/01_check_config.py
python debug_tools/05_check_tracker_database.py

# Run ingestion with debug logging
python main.py --ingest --debug

# Check tracker statistics
python debug_tools/05_check_tracker_database.py

# View recent ingestion logs
tail -50 logs/evaluation.jsonl
```

---

## Developer Notes

This debugging system was designed with these principles:

- **No emojis**: ASCII-safe output for all terminals
- **Clear errors**: System error + explanation + solution
- **Standalone scripts**: Each tool works independently
- **JSON output**: Machine-readable for automation
- **Git-ignored**: Debug data stays local
