#!/usr/bin/env python3
"""
Master Debug Orchestrator for RAG-ing Pipeline

Runs all diagnostic checks and generates a comprehensive report.
This is the main entry point for debugging the ingest pipeline.

Usage:
    python debug_tools/run_all_checks.py
    
    Options:
        --quick     Run essential checks only (config, tracker, vector store)
        --full      Run all checks including connectivity tests
        --save      Save detailed report (default: terminal only)
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
import json
import argparse

# ASCII-safe status indicators
STATUS_OK = "[OK]"
STATUS_ERROR = "[X]"
STATUS_WARNING = "[!]"
STATUS_INFO = "[i]"


def print_header(title, char="="):
    """Print section header."""
    print(f"\n{char*80}")
    print(f" {title}")
    print(f"{char*80}\n")


def run_check(script_path, description):
    """Run a diagnostic check script and capture results."""
    print_header(description, char="-")
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout per check
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Print output
        print(result.stdout)
        
        if result.stderr:
            print(f"{STATUS_WARNING} Stderr output:")
            print(result.stderr)
        
        success = result.returncode == 0
        
        status = STATUS_OK if success else STATUS_ERROR
        print(f"\n{status} {description} - Exit code: {result.returncode} - Duration: {duration:.2f}s")
        
        return {
            'script': script_path,
            'description': description,
            'success': success,
            'exit_code': result.returncode,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"{STATUS_ERROR} {description} - TIMEOUT (exceeded 120s)")
        return {
            'script': script_path,
            'description': description,
            'success': False,
            'exit_code': -1,
            'duration': 120,
            'error': 'timeout'
        }
    except Exception as e:
        print(f"{STATUS_ERROR} {description} - EXCEPTION: {e}")
        return {
            'script': script_path,
            'description': description,
            'success': False,
            'exit_code': -1,
            'duration': 0,
            'error': str(e)
        }


def main():
    """Main orchestration routine."""
    parser = argparse.ArgumentParser(
        description="Run all RAG-ing pipeline diagnostic checks"
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run essential checks only (faster)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run all checks including connectivity tests (default)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save detailed report to file'
    )
    
    args = parser.parse_args()
    
    # Default to full if neither specified
    if not args.quick and not args.full:
        args.full = True
    
    print_header("RAG-ing Pipeline Diagnostic Suite")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'Quick' if args.quick else 'Full'}")
    
    overall_start = datetime.now()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'mode': 'quick' if args.quick else 'full',
        'checks': []
    }
    
    # Essential checks (always run)
    essential_checks = [
        ('debug_tools/01_check_config.py', 'Configuration Validation'),
        ('debug_tools/05_check_tracker_database.py', 'Tracker Database Validation'),
    ]
    
    # Full checks (optional)
    full_checks = [
        ('debug_tools/02_check_data_sources.py', 'Data Source Connectivity'),
        ('debug_tools/03_check_embedding_model.py', 'Embedding Model Validation'),
        ('debug_tools/04_check_vector_store.py', 'Vector Store Validation'),
        ('debug_tools/06_test_end_to_end.py', 'End-to-End Pipeline Test'),
    ]
    
    # Determine which checks to run
    checks_to_run = essential_checks[:]
    if args.full:
        checks_to_run.extend(full_checks)
    
    print(f"\n{STATUS_INFO} Running {len(checks_to_run)} diagnostic checks...\n")
    
    # Run all checks
    for script_path, description in checks_to_run:
        # Check if script exists
        if not Path(script_path).exists():
            print(f"{STATUS_WARNING} Skipping {description} - script not found: {script_path}")
            results['checks'].append({
                'script': script_path,
                'description': description,
                'success': False,
                'error': 'script_not_found'
            })
            continue
        
        # Run check
        check_result = run_check(script_path, description)
        results['checks'].append(check_result)
        
        # Add separator
        print()
    
    # Calculate overall statistics
    overall_end = datetime.now()
    total_duration = (overall_end - overall_start).total_seconds()
    
    total_checks = len(results['checks'])
    passed_checks = sum(1 for c in results['checks'] if c.get('success', False))
    failed_checks = total_checks - passed_checks
    
    results['summary'] = {
        'total_checks': total_checks,
        'passed': passed_checks,
        'failed': failed_checks,
        'success_rate': (passed_checks / total_checks * 100) if total_checks > 0 else 0,
        'total_duration': total_duration
    }
    
    # Print final summary
    print_header("Final Summary")
    
    print(f"{STATUS_INFO} Checks Summary:")
    print(f"    Total checks: {total_checks}")
    print(f"    Passed: {passed_checks}")
    print(f"    Failed: {failed_checks}")
    print(f"    Success rate: {results['summary']['success_rate']:.1f}%")
    print(f"    Total duration: {total_duration:.2f}s")
    
    print(f"\n{STATUS_INFO} Check Results:")
    for check in results['checks']:
        status = STATUS_OK if check.get('success') else STATUS_ERROR
        duration = check.get('duration', 0)
        print(f"  {status} {check['description']} ({duration:.1f}s)")
    
    # Save detailed report if requested
    if args.save:
        output_dir = Path('./debug_tools/reports')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_dir / f'diagnostic_report_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{STATUS_INFO} Detailed report saved to: {report_file}")
    
    # Print recommendations
    print_header("Recommendations")
    
    if failed_checks == 0:
        print(f"{STATUS_OK} All checks passed! Your RAG-ing pipeline is properly configured.")
        print(f"\nNext steps:")
        print(f"  1. Run ingestion: python main.py --ingest")
        print(f"  2. Launch UI: python main.py --ui")
        print(f"  3. Test queries")
    else:
        print(f"{STATUS_WARNING} {failed_checks} check(s) failed. Please address the issues above.")
        print(f"\nRecommended actions:")
        
        # Specific recommendations based on failures
        for check in results['checks']:
            if not check.get('success'):
                desc = check['description']
                
                if 'Configuration' in desc:
                    print(f"  - Fix configuration issues in config.yaml and .env")
                elif 'Tracker Database' in desc:
                    print(f"  - Check write permissions in project directory")
                    print(f"  - Database will auto-create on first ingestion")
                elif 'Data Source' in desc:
                    print(f"  - Verify data source credentials and connectivity")
                elif 'Embedding' in desc:
                    print(f"  - Check Azure OpenAI credentials and deployment")
                elif 'Vector Store' in desc:
                    print(f"  - Check vector_store/ directory permissions")
                elif 'End-to-End' in desc:
                    print(f"  - Fix component issues first, then retry")
    
    print(f"\n{STATUS_INFO} For detailed help, see: debug_tools/README.md")
    
    # Exit with appropriate code
    exit_code = 0 if failed_checks == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
