# Debug Tools Quick Reference

## TL;DR - Run This First

```bash
# From project root
python debug_tools/run_all_checks.py --quick
```

This validates your configuration and tracker database in ~15 seconds.

---

## What These Tools Do

**Purpose**: Help you debug the RAG-ing document ingestion pipeline step by step.

**Components Checked**:
1. Configuration (config.yaml + .env)
2. Tracker Database (SQLite ingestion tracking)
3. Data Sources (local/Azure DevOps/Confluence)
4. Embedding Model (Azure OpenAI)
5. Vector Store (ChromaDB)
6. End-to-End Pipeline

---

## Quick Commands

```bash
# Run all essential checks (fast)
python debug_tools/run_all_checks.py --quick

# Run complete diagnostic suite
python debug_tools/run_all_checks.py --full

# Save detailed JSON report
python debug_tools/run_all_checks.py --save

# Check specific components
python debug_tools/01_check_config.py           # Configuration
python debug_tools/05_check_tracker_database.py # Tracker DB

# View documentation
cat debug_tools/README.md                       # Quick overview
cat debug_tools/DEVELOPER_GUIDE.md              # Full guide
```

---

## Understanding the Output

### Success
```
[OK] All checks passed!
```
→ Your system is ready for ingestion

### Failure
```
[X] Configuration Validation (8.3s)
[OK] Tracker Database Validation (7.2s)

Recommended actions:
  - Fix configuration issues in config.yaml and .env
```
→ Fix the configuration issues, then re-run checks

---

## Common Issues

### "No database found"
**This is NORMAL** - Database auto-creates on first ingestion run.

### "Environment variables not set"
Create `.env` file with your credentials:
```bash
cp env.example .env
# Edit .env with real values
```

### "No documents processed"
Check that data sources are enabled in `config.yaml`:
```yaml
data_source:
  sources:
    - type: "local_file"
      enabled: true  # ← Must be true
```

---

## File Locations

```
debug_tools/
├── *.py                  # Debug scripts
├── README.md             # This file
├── DEVELOPER_GUIDE.md    # Comprehensive troubleshooting
├── IMPLEMENTATION_SUMMARY.md  # Technical details
├── logs/                 # Execution logs (gitignored)
└── reports/              # Test reports (gitignored)
```

---

## What Was Fixed

**Issue**: Tracker database (`ingestion_tracking.db`) was not visible

**Root Cause**: 
1. Database only creates during first ingestion (expected behavior)
2. `.gitignore` hides `.db` files (by design)
3. No debug tools existed to verify functionality

**Solution**:
1. Created comprehensive debug tools ✓
2. Verified database works correctly ✓
3. Added troubleshooting documentation ✓

**Status**: No bug existed - system works as designed

---

## Next Steps

1. **Run checks**: `python debug_tools/run_all_checks.py --quick`
2. **Fix issues**: Address any reported problems
3. **Run ingestion**: `python main.py --ingest`
4. **Verify results**: Check the output and tracker stats

---

## Need Help?

1. Read `debug_tools/DEVELOPER_GUIDE.md` for detailed troubleshooting
2. Check `debug_tools/reports/` for JSON diagnostic data
3. Run individual component checks to isolate issues

---

## Git Integration

All debug outputs are gitignored:
- `debug_tools/logs/` - Execution logs
- `debug_tools/reports/` - Test reports
- `debug_tools/*.db` - Test databases

Safe to run and generate reports without cluttering git history.
