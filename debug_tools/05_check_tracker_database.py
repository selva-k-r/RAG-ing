#!/usr/bin/env python3
"""
Tracker Database Validator for RAG-ing Pipeline

Validates the SQLite ingestion tracking database, tests operations,
and reports on current ingestion status.

Usage:
    python debug_tools/05_check_tracker_database.py
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ASCII-safe status indicators
STATUS_OK = "[OK]"
STATUS_ERROR = "[X]"
STATUS_WARNING = "[!]"
STATUS_INFO = "[i]"


def print_header(title):
    """Print section header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def check_sqlite_available():
    """Check if SQLite is available."""
    try:
        import sqlite3
        version = sqlite3.sqlite_version
        print(f"{STATUS_OK} SQLite available: version {version}")
        return True
    except ImportError:
        print(f"{STATUS_ERROR} SQLite not available")
        print(f"\nSolution:")
        print(f"  SQLite should be included with Python")
        print(f"  Check Python installation")
        return False


def check_database_file(db_path):
    """Check if database file exists."""
    path = Path(db_path)
    
    if not path.exists():
        print(f"{STATUS_WARNING} Database file not found: {db_path}")
        print(f"    This is normal for first run - will be auto-created")
        return False
    
    if not path.is_file():
        print(f"{STATUS_ERROR} Path exists but is not a file: {db_path}")
        return False
    
    file_size = path.stat().st_size
    print(f"{STATUS_OK} Database file exists: {db_path}")
    print(f"    Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
    return True


def test_database_connection(db_path):
    """Test database connection."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        
        conn.close()
        print(f"{STATUS_OK} Database connection successful")
        print(f"    SQLite version: {version}")
        return True
    except sqlite3.Error as e:
        print(f"{STATUS_ERROR} Database connection failed")
        print(f"    Error: {e}")
        return False


def validate_schema(db_path):
    """Validate database schema."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if main table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='documents'
        """)
        
        if not cursor.fetchone():
            print(f"{STATUS_WARNING} Table 'documents' not found")
            print(f"    Schema will be auto-created on first use")
            conn.close()
            return False
        
        print(f"{STATUS_OK} Table 'documents' exists")
        
        # Check columns
        cursor.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'id', 'source_type', 'document_id', 'source_location',
            'content_hash', 'last_modified_date', 'processed_date',
            'chunk_count', 'status', 'document_title'
        ]
        
        actual_columns = [col['name'] for col in columns]
        
        print(f"    Columns found: {len(actual_columns)}")
        
        missing = set(expected_columns) - set(actual_columns)
        if missing:
            print(f"{STATUS_WARNING} Missing columns: {missing}")
        else:
            print(f"{STATUS_OK} All expected columns present")
        
        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='documents'
        """)
        indexes = cursor.fetchall()
        print(f"    Indexes: {len(indexes)}")
        for idx in indexes:
            print(f"      - {idx['name']}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"{STATUS_ERROR} Schema validation failed")
        print(f"    Error: {e}")
        return False


def get_statistics(db_path):
    """Get ingestion statistics from database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_documents,
                SUM(chunk_count) as total_chunks,
                SUM(file_size_bytes) as total_size_bytes,
                COUNT(DISTINCT source_type) as unique_sources,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                MAX(processed_date) as last_processed_date
            FROM documents
        """)
        
        stats = cursor.fetchone()
        
        if stats['total_documents'] == 0:
            print(f"{STATUS_WARNING} No documents tracked yet")
            print(f"    Run ingestion first: python main.py --ingest")
            conn.close()
            return {}
        
        print(f"{STATUS_OK} Tracking statistics:")
        print(f"    Total documents: {stats['total_documents']:,}")
        print(f"    Total chunks: {stats['total_chunks']:,}")
        print(f"    Total size: {stats['total_size_bytes']:,} bytes")
        print(f"    Unique sources: {stats['unique_sources']}")
        print(f"    Successful: {stats['successful']:,}")
        print(f"    Failed: {stats['failed']:,}")
        print(f"    Skipped: {stats['skipped']:,}")
        print(f"    Last processed: {stats['last_processed_date']}")
        
        # Per-source statistics
        cursor.execute("""
            SELECT 
                source_type,
                COUNT(*) as document_count,
                SUM(chunk_count) as total_chunks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful
            FROM documents
            GROUP BY source_type
            ORDER BY document_count DESC
        """)
        
        sources = cursor.fetchall()
        
        print(f"\n{STATUS_INFO} Per-source breakdown:")
        for source in sources:
            print(f"    {source['source_type']}: {source['document_count']:,} docs, "
                  f"{source['total_chunks']:,} chunks, "
                  f"{source['successful']:,} successful")
        
        conn.close()
        
        return {
            'total_documents': stats['total_documents'],
            'total_chunks': stats['total_chunks'],
            'total_size_bytes': stats['total_size_bytes'],
            'unique_sources': stats['unique_sources'],
            'successful': stats['successful'],
            'failed': stats['failed'],
            'skipped': stats['skipped']
        }
        
    except sqlite3.Error as e:
        print(f"{STATUS_ERROR} Failed to retrieve statistics")
        print(f"    Error: {e}")
        return {}


def test_write_operation(db_path):
    """Test write operation to database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try to insert test record
        test_doc_id = f"test_debug_{datetime.now().isoformat()}"
        
        cursor.execute("""
            INSERT INTO documents (
                source_type, document_id, content_hash, 
                processed_date, chunk_count, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'debug_test', test_doc_id, 'test_hash',
            datetime.now().isoformat(), 0, 'success'
        ))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("""
            SELECT * FROM documents 
            WHERE source_type = 'debug_test' AND document_id = ?
        """, (test_doc_id,))
        
        result = cursor.fetchone()
        
        if result:
            print(f"{STATUS_OK} Write operation successful")
            
            # Clean up test record
            cursor.execute("""
                DELETE FROM documents 
                WHERE source_type = 'debug_test' AND document_id = ?
            """, (test_doc_id,))
            conn.commit()
            print(f"{STATUS_OK} Test record cleaned up")
        else:
            print(f"{STATUS_ERROR} Write operation failed - record not found")
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"{STATUS_ERROR} Write operation failed")
        print(f"    Error: {e}")
        return False


def test_tracker_class():
    """Test IngestionTrackerSQLite class."""
    try:
        from rag_ing.utils.ingestion_tracker_sqlite import IngestionTrackerSQLite
        
        # Initialize tracker (will create DB if needed)
        tracker = IngestionTrackerSQLite(db_path="./ingestion_tracking.db")
        
        print(f"{STATUS_OK} IngestionTrackerSQLite class initialized")
        
        # Get statistics
        stats = tracker.get_statistics()
        print(f"{STATUS_OK} Statistics method working")
        
        # Test needs_processing
        needs_proc, reason = tracker.needs_processing(
            source_type="debug_test",
            document_id="test_doc",
            content_hash="test_hash"
        )
        
        print(f"{STATUS_OK} needs_processing method working")
        print(f"    Result: {needs_proc}, Reason: {reason}")
        
        return True
        
    except Exception as e:
        print(f"{STATUS_ERROR} Tracker class test failed")
        print(f"    Error: {e}")
        return False


def check_write_permissions():
    """Check write permissions in project directory."""
    test_file = Path("./test_write_permission.tmp")
    
    try:
        # Try to create a test file
        with open(test_file, 'w') as f:
            f.write("test")
        
        # Clean up
        test_file.unlink()
        
        print(f"{STATUS_OK} Write permissions: OK")
        return True
        
    except Exception as e:
        print(f"{STATUS_ERROR} Write permissions: DENIED")
        print(f"    Error: {e}")
        print(f"\nSolution:")
        print(f"  Check directory permissions: ls -la")
        print(f"  Run from writable directory")
        return False


def main():
    """Main validation routine."""
    print_header("RAG-ing Tracker Database Validator")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    db_path = "./ingestion_tracking.db"
    
    # Check 1: SQLite available
    print_header("SQLite Availability")
    sqlite_ok = check_sqlite_available()
    results['checks']['sqlite_available'] = sqlite_ok
    
    if not sqlite_ok:
        sys.exit(1)
    
    # Check 2: Write permissions
    print_header("Write Permissions")
    write_perm_ok = check_write_permissions()
    results['checks']['write_permissions'] = write_perm_ok
    
    # Check 3: Database file
    print_header("Database File")
    db_exists = check_database_file(db_path)
    results['checks']['db_exists'] = db_exists
    
    # Check 4: Database connection
    if db_exists:
        print_header("Database Connection")
        conn_ok = test_database_connection(db_path)
        results['checks']['connection_ok'] = conn_ok
        
        # Check 5: Schema validation
        if conn_ok:
            print_header("Schema Validation")
            schema_ok = validate_schema(db_path)
            results['checks']['schema_ok'] = schema_ok
            
            # Check 6: Statistics
            if schema_ok:
                print_header("Ingestion Statistics")
                stats = get_statistics(db_path)
                results['statistics'] = stats
                
                # Check 7: Write operation
                print_header("Write Operation Test")
                write_ok = test_write_operation(db_path)
                results['checks']['write_ok'] = write_ok
    else:
        print(f"\n{STATUS_INFO} Database will be created on first ingestion run")
        results['checks']['connection_ok'] = None
        results['checks']['schema_ok'] = None
        results['checks']['write_ok'] = None
    
    # Check 8: Tracker class
    print_header("Tracker Class Test")
    tracker_ok = test_tracker_class()
    results['checks']['tracker_class_ok'] = tracker_ok
    
    # Final summary
    print_header("Validation Summary")
    
    all_checks = [
        ('SQLite available', sqlite_ok),
        ('Write permissions', write_perm_ok),
        ('Database file exists', db_exists or tracker_ok),  # OK if created by tracker
        ('Tracker class working', tracker_ok)
    ]
    
    passed = sum(1 for _, ok in all_checks if ok)
    total = len(all_checks)
    
    for check_name, ok in all_checks:
        status = STATUS_OK if ok else STATUS_ERROR
        print(f"{status} {check_name}")
    
    print(f"\n{STATUS_INFO} Result: {passed}/{total} checks passed")
    
    results['summary'] = {
        'total_checks': total,
        'passed': passed,
        'failed': total - passed
    }
    
    # Save results
    output_dir = Path('./debug_tools/reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'tracker_database_validation.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{STATUS_INFO} Results saved to: {output_file}")
    
    if passed == total:
        print(f"\n{STATUS_OK} All tracker database checks passed!")
        
        # Check if database actually exists now
        if Path(db_path).exists():
            print(f"{STATUS_OK} Database file confirmed at: {db_path}")
        else:
            print(f"{STATUS_WARNING} Database will be created on first ingestion")
        
        return 0
    else:
        print(f"\n{STATUS_WARNING} Some checks failed - review above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
