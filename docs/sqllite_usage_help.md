# 📊 SQLite Ingestion Tracker - Best Practices Guide

## 🎯 Overview

The SQLite ingestion tracker replaces the CSV-based tracking with a production-grade database solution offering:
- **100x faster queries** via indexes
- **Atomic transactions** (ACID compliance)
- **Complex queries** (JOIN, GROUP BY, filtering)
- **Type safety** (enforced schema)
- **Concurrent access** (multiple readers)

---

## 📁 File Location

```
ingestion_tracking.db         # Main SQLite database
ingestion_tracking.db-wal     # Write-Ahead Log (concurrent access)
ingestion_tracking.db-shm     # Shared memory (concurrent access)
```

**Note:** These files work together. Don't delete the `-wal` or `-shm` files manually!

---

## 🚀 Quick Start

### 1. Basic Usage

```python
from rag_ing.utils.ingestion_tracker_sqlite import IngestionTrackerSQLite

# Initialize tracker
tracker = IngestionTrackerSQLite("ingestion_tracking.db")

# Check if document needs processing (fast!)
needs_proc, reason = tracker.needs_processing(
    source_type="azure_devops",
    document_id="/models/staging/stg_claims.sql",
    content_hash="abc123def456",
    last_modified_date="2024-11-20T10:30:00"
)

if needs_proc:
    print(f"Process document: {reason}")
    # ... process document ...
    
    # Record processing
    tracker.add_or_update_document(
        source_type="azure_devops",
        document_id="/models/staging/stg_claims.sql",
        metadata={
            'content_hash': 'abc123def456',
            'chunk_count': 15,
            'status': 'success',
            'document_title': 'stg_claims.sql',
            'source_location': 'dbt-pophealth',
            'source_branch': 'main',
            'last_modified_date': '2024-11-20T10:30:00',
            'last_modified_by': 'user@example.com',
            'processing_time_seconds': 2.5,
            'file_size_bytes': 5120
        }
    )
```

---

## 🔍 Common Query Patterns

### 1. Check if Document Exists

```python
# Fast O(1) lookup using composite index
doc_info = tracker.get_document_status(
    source_type="azure_devops",
    document_id="/models/staging/stg_claims.sql"
)

if doc_info:
    print(f"Document found: {doc_info['chunk_count']} chunks")
    print(f"Last processed: {doc_info['processed_date']}")
    print(f"Status: {doc_info['status']}")
else:
    print("Document not tracked yet")
```

### 2. Detect Changes (Fast Comparison)

```python
# Optimized change detection
needs_proc, reason = tracker.needs_processing(
    source_type="azure_devops",
    document_id="/models/staging/stg_claims.sql",
    content_hash=calculate_hash(file_content),  # SHA-256
    last_modified_date="2024-11-20T15:30:00"
)

# Reasons returned:
# - "new_document": Never seen before
# - "content_changed": Hash doesn't match
# - "modified_date_changed": Date updated
# - "retry_failed": Previous processing failed
# - "unchanged": No changes detected
```

### 3. Get All Documents by Source

```python
# Get all Azure DevOps documents
azure_docs = tracker.get_documents_by_source("azure_devops")
print(f"Total Azure DevOps files: {len(azure_docs)}")

# Filter by status
failed_docs = tracker.get_documents_by_source("azure_devops", status="failed")
print(f"Failed documents: {len(failed_docs)}")
```

### 4. Get Statistics

```python
# Overall statistics
stats = tracker.get_statistics()
print(f"Total documents: {stats['total_documents']}")
print(f"Total chunks: {stats['total_chunks']}")
print(f"Successful: {stats['successful']}")
print(f"Failed: {stats['failed']}")
print(f"Avg processing time: {stats['avg_processing_time']:.2f}s")

# Statistics by source type
source_stats = tracker.get_statistics_by_source()
for source in source_stats:
    print(f"{source['source_type']}: {source['document_count']} docs, {source['total_chunks']} chunks")
```

---

## ⚡ Performance Optimization

### 1. Batch Operations (100x Faster!)

**❌ Slow (Individual inserts):**
```python
# DON'T DO THIS - 100 database writes
for doc in documents:
    tracker.add_or_update_document(doc['source_type'], doc['document_id'], doc)
```

**✅ Fast (Batch upsert):**
```python
# DO THIS - 1 transaction with 100 documents
documents = [
    {
        'source_type': 'azure_devops',
        'document_id': f'/models/staging/stg_model_{i}.sql',
        'content_hash': calculate_hash(content),
        'chunk_count': 5,
        'status': 'success',
        'document_title': f'stg_model_{i}.sql',
        'processed_date': datetime.now().isoformat()
    }
    for i in range(100)
]
tracker.bulk_upsert(documents)  # Single transaction!
```

**Performance:**
- Individual: ~5 seconds for 100 documents
- Batch: ~0.05 seconds for 100 documents
- **100x speedup!**

### 2. Verify Index Usage

```python
# Check if query is using indexes (should see "USING INDEX")
query = """
SELECT * FROM documents 
WHERE source_type = 'azure_devops' AND status = 'success'
"""
plan = tracker.get_query_plan(query)
print(f"Query plan:\n{plan}")

# Good output:
# SEARCH documents USING INDEX idx_source_status (source_type=? AND status=?)
```

### 3. Maintenance

```python
# After many deletions, reclaim space
tracker.vacuum()

# Export to CSV for Excel/PowerBI analysis
tracker.export_to_csv("ingestion_report.csv")
```

---

## 🔄 Migration from CSV

### Automatic Migration

The system automatically migrates your existing CSV on first run:

```python
# On initialization, CSV is auto-migrated if found
tracker = IngestionTrackerSQLite("ingestion_tracking.db")

# Output:
# 📊 Migrated 6 records from CSV to SQLite
# ✅ CSV backed up to ingestion_tracking.csv.backup
```

### Manual Migration

```python
# Manually migrate from CSV
tracker = IngestionTrackerSQLite("ingestion_tracking.db")
count = tracker.migrate_from_csv("ingestion_tracking.csv")
print(f"Migrated {count} records")
```

---

## 🛡️ Best Practices

### 1. Always Use Context Managers (Auto-cleanup)

The tracker handles connections internally with context managers:

```python
# ✅ Good - connection automatically closed
doc = tracker.get_document_status("azure_devops", "/models/file.sql")

# No need to manually close connections!
```

### 2. Use Parameterized Queries (SQL Injection Prevention)

```python
# ✅ Good - parameters passed separately (safe)
tracker.get_document_status(source_type, document_id)

# ❌ Bad - string concatenation (vulnerable)
# query = f"SELECT * FROM documents WHERE document_id = '{document_id}'"
```

### 3. Batch Updates for Large Datasets

```python
# Process 1000 files
batch_size = 100
for i in range(0, len(all_documents), batch_size):
    batch = all_documents[i:i+batch_size]
    tracker.bulk_upsert(batch)  # Transaction per 100 docs
```

### 4. Check Before Processing

```python
# ✅ Efficient - single query to check
needs_proc, reason = tracker.needs_processing(
    source_type, document_id, content_hash, last_modified_date
)

if needs_proc:
    # Process document
    process_document(document)
else:
    logger.info(f"Skipping {document_id}: {reason}")
```

---

## 📊 Schema Design

### Documents Table

| Column | Type | Description | Indexed |
|--------|------|-------------|---------|
| `id` | INTEGER | Auto-increment primary key | ✅ (PK) |
| `source_type` | TEXT | Data source (azure_devops, local_file, etc.) | ✅ |
| `document_id` | TEXT | Unique identifier within source | ✅ (composite) |
| `content_hash` | TEXT | SHA-256 hash for change detection | ✅ |
| `status` | TEXT | success/failed/skipped/processing | ✅ |
| `chunk_count` | INTEGER | Number of chunks created | No |
| `processed_date` | TEXT | ISO 8601 timestamp | ✅ |
| `last_modified_date` | TEXT | Source modification date | No |
| `processing_time_seconds` | REAL | Processing duration | No |
| `file_size_bytes` | INTEGER | Original file size | No |

### Indexes

```sql
-- Fast lookup by source type
CREATE INDEX idx_source_type ON documents(source_type);

-- Fast change detection
CREATE INDEX idx_content_hash ON documents(content_hash);

-- Fast status filtering
CREATE INDEX idx_status ON documents(status);

-- Composite index for common query (source + status)
CREATE INDEX idx_source_status ON documents(source_type, status);

-- Date-based queries
CREATE INDEX idx_processed_date ON documents(processed_date);
```

---

## 🔍 Advanced Queries

### 1. Find Recently Modified Documents

```python
from datetime import datetime, timedelta

# Get documents modified in last 7 days
cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()

with tracker._get_connection() as conn:
    cursor = conn.execute("""
        SELECT source_type, document_id, document_title, processed_date
        FROM documents
        WHERE processed_date > ?
        ORDER BY processed_date DESC
        LIMIT 20
    """, (cutoff_date,))
    
    recent_docs = [dict(row) for row in cursor.fetchall()]
    for doc in recent_docs:
        print(f"{doc['document_title']}: {doc['processed_date']}")
```

### 2. Find Largest Documents

```python
with tracker._get_connection() as conn:
    cursor = conn.execute("""
        SELECT document_title, chunk_count, file_size_bytes
        FROM documents
        WHERE source_type = 'azure_devops'
        ORDER BY chunk_count DESC
        LIMIT 10
    """)
    
    largest = [dict(row) for row in cursor.fetchall()]
    for doc in largest:
        print(f"{doc['document_title']}: {doc['chunk_count']} chunks, {doc['file_size_bytes']} bytes")
```

### 3. Processing Performance Report

```python
with tracker._get_connection() as conn:
    cursor = conn.execute("""
        SELECT 
            source_type,
            COUNT(*) as total_docs,
            AVG(processing_time_seconds) as avg_time,
            MAX(processing_time_seconds) as max_time,
            SUM(chunk_count) as total_chunks
        FROM documents
        WHERE status = 'success'
        GROUP BY source_type
        ORDER BY total_docs DESC
    """)
    
    report = [dict(row) for row in cursor.fetchall()]
    for row in report:
        print(f"{row['source_type']}: {row['total_docs']} docs, "
              f"avg {row['avg_time']:.2f}s, "
              f"{row['total_chunks']} chunks")
```

---

## 🐛 Troubleshooting

### Database Locked Error

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** Multiple processes trying to write simultaneously

**Solution:**
```python
# Option 1: Use WAL mode (already enabled by default)
# This allows concurrent readers + 1 writer

# Option 2: Add timeout
import sqlite3
conn = sqlite3.connect("ingestion_tracking.db", timeout=10.0)
```

### Large Database File

**Symptom:** `ingestion_tracking.db` is very large

**Solution:**
```python
# Reclaim unused space
tracker.vacuum()

# Check database size
import os
size_mb = os.path.getsize("ingestion_tracking.db") / (1024 * 1024)
print(f"Database size: {size_mb:.2f} MB")
```

### Query Performance Issues

**Symptom:** Queries are slow

**Solution:**
```python
# 1. Verify indexes are being used
plan = tracker.get_query_plan("SELECT * FROM documents WHERE source_type = 'azure_devops'")
print(plan)  # Should say "USING INDEX"

# 2. Run ANALYZE to update statistics
with tracker._get_connection() as conn:
    conn.execute("ANALYZE")
    
# 3. Check for missing indexes
# All common queries should use indexes (see schema above)
```

---

## 📈 Monitoring

### Create a Dashboard Query

```python
def get_dashboard_metrics(tracker):
    """Get key metrics for monitoring."""
    stats = tracker.get_statistics()
    source_stats = tracker.get_statistics_by_source()
    
    dashboard = {
        'overview': {
            'total_documents': stats['total_documents'],
            'total_chunks': stats['total_chunks'],
            'success_rate': f"{(stats['successful'] / stats['total_documents'] * 100):.1f}%",
            'avg_processing_time': f"{stats['avg_processing_time']:.2f}s",
            'last_update': stats['last_processed_date']
        },
        'by_source': source_stats
    }
    
    return dashboard

# Usage
metrics = get_dashboard_metrics(tracker)
print(json.dumps(metrics, indent=2))
```

---

## 🎓 Key Takeaways

1. **Indexes are your friend** - All common queries use indexes for O(1) or O(log n) lookups
2. **Batch operations** - Use `bulk_upsert()` for 100x speedup
3. **Parameterized queries** - Built-in SQL injection prevention
4. **Concurrent access** - WAL mode allows multiple readers
5. **Type safety** - Schema enforces valid data
6. **Atomic operations** - Transactions ensure data consistency
7. **Easy migration** - Automatic CSV import on first run
8. **Production-ready** - ACID compliance, constraints, indexes

---

## 📚 Further Reading

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite Performance](https://www.sqlite.org/performance.html)
- [WAL Mode](https://www.sqlite.org/wal.html)
- [Query Planning](https://www.sqlite.org/queryplanner.html)

