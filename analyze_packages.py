#!/usr/bin/env python3
"""
Package Status Analyzer
Categorizes packages into:
- 🔴 RED: Deprecated packages
- 🟡 YELLOW: Stable but not latest version
- 🟢 GREEN: Latest stable version
"""

import json
import re
import subprocess
import sys
from typing import Dict, List, Tuple
import toml

# Color codes for terminal output
RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'


def extract_package_name(dep: str) -> Tuple[str, str]:
    """Extract package name and version constraint from dependency string."""
    # Handle various formats: package>=1.0.0, package==1.0.0, package, etc.
    match = re.match(r'^([a-zA-Z0-9\-_]+)([>=<~!]+)?(.+)?$', dep)
    if match:
        name = match.group(1)
        constraint = match.group(3) if match.group(3) else "any"
        return name, constraint
    return dep, "any"


def get_pypi_package_info(package_name: str) -> Dict:
    """Get package information from PyPI API."""
    try:
        import urllib.request
        import json
        
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"  ⚠️  Warning: Could not fetch info for {package_name}: {e}", file=sys.stderr)
        return {}


def is_deprecated(package_info: Dict) -> bool:
    """Check if a package is deprecated."""
    info = package_info.get('info', {})
    
    # Check classifiers for deprecation status (most reliable)
    classifiers = info.get('classifiers', [])
    for classifier in classifiers:
        # Only check Development Status classifiers
        if 'Development Status' in classifier:
            if any(status in classifier for status in ['7 - Inactive', '6 - Mature']):
                # Check if explicitly marked as deprecated in description
                description = info.get('description', '').lower()
                summary = info.get('summary', '').lower()
                if 'deprecated' in description or 'deprecated' in summary:
                    return True
    
    # Check for explicit strong deprecation markers only
    description = info.get('description', '').lower()
    summary = info.get('summary', '').lower()
    
    strong_deprecation_keywords = [
        'this package is deprecated',
        'no longer maintained',
        'package has been deprecated',
        'obsolete and unmaintained'
    ]
    
    for keyword in strong_deprecation_keywords:
        if keyword in description or keyword in summary:
            return True
    
    return False


def get_latest_version(package_info: Dict) -> str:
    """Get the latest stable version of a package."""
    info = package_info.get('info', {})
    return info.get('version', 'unknown')


def compare_versions(current: str, latest: str) -> bool:
    """Compare if current version constraint allows the latest version."""
    # If no constraint specified, it's outdated
    if current == "any":
        return False
    
    # Extract the minimum version from constraint
    version_match = re.search(r'(\d+\.\d+\.\d+)', current)
    if not version_match:
        return False
    
    current_min = version_match.group(1)
    
    # Simple version comparison (major.minor.patch)
    try:
        current_parts = [int(x) for x in current_min.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]
        
        # Check if versions match exactly or current is very close
        if current_parts == latest_parts:
            return True
        
        # Check if only patch version differs (still considered reasonably up-to-date)
        if current_parts[0] == latest_parts[0] and current_parts[1] == latest_parts[1]:
            # Allow patch version differences within 5
            if abs(current_parts[2] - latest_parts[2]) <= 5:
                return True
        
        return False
    except:
        return False


def analyze_packages():
    """Analyze all packages from pyproject.toml."""
    print(f"\n{BOLD}{'='*80}")
    print("📦 PACKAGE STATUS ANALYSIS")
    print(f"{'='*80}{RESET}\n")
    
    # Read pyproject.toml
    try:
        with open('pyproject.toml', 'r') as f:
            pyproject = toml.load(f)
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return
    
    dependencies = pyproject.get('project', {}).get('dependencies', [])
    dev_dependencies = pyproject.get('project', {}).get('optional-dependencies', {}).get('dev', [])
    
    # Categorize packages
    deprecated_packages = []
    stable_not_latest = []
    latest_stable = []
    
    print(f"🔍 Analyzing {len(dependencies)} main dependencies...")
    print(f"🔍 Analyzing {len(dev_dependencies)} dev dependencies...")
    print()
    
    all_deps = dependencies + dev_dependencies
    
    for idx, dep in enumerate(all_deps, 1):
        package_name, constraint = extract_package_name(dep)
        print(f"[{idx}/{len(all_deps)}] Checking {package_name}...", end='\r')
        
        package_info = get_pypi_package_info(package_name)
        if not package_info:
            continue
        
        latest = get_latest_version(package_info)
        
        # Check deprecation
        if is_deprecated(package_info):
            deprecated_packages.append({
                'name': package_name,
                'constraint': constraint,
                'latest': latest,
                'reason': 'Package marked as deprecated'
            })
        # Check if at latest version
        elif compare_versions(constraint, latest):
            latest_stable.append({
                'name': package_name,
                'constraint': constraint,
                'latest': latest
            })
        else:
            stable_not_latest.append({
                'name': package_name,
                'constraint': constraint,
                'latest': latest
            })
    
    print(" " * 80, end='\r')  # Clear the progress line
    
    # Print results
    print(f"\n{BOLD}{'='*80}")
    print("📊 ANALYSIS RESULTS")
    print(f"{'='*80}{RESET}\n")
    
    # Deprecated packages (RED)
    print(f"{RED}{BOLD}🔴 DEPRECATED PACKAGES ({len(deprecated_packages)}){RESET}")
    print(f"{RED}{'─'*80}{RESET}")
    if deprecated_packages:
        for pkg in deprecated_packages:
            print(f"{RED}  ❌ {pkg['name']:30} | Current: {pkg['constraint']:15} | Latest: {pkg['latest']:10}")
            print(f"     Reason: {pkg['reason']}{RESET}")
    else:
        print(f"{GREEN}  ✅ No deprecated packages found!{RESET}")
    
    print()
    
    # Stable but not latest (YELLOW)
    print(f"{YELLOW}{BOLD}🟡 STABLE BUT NOT LATEST VERSION ({len(stable_not_latest)}){RESET}")
    print(f"{YELLOW}{'─'*80}{RESET}")
    if stable_not_latest:
        for pkg in stable_not_latest:
            print(f"{YELLOW}  ⚠️  {pkg['name']:30} | Current: {pkg['constraint']:15} | Latest: {pkg['latest']:10}{RESET}")
    else:
        print(f"{GREEN}  ✅ All packages are at latest version!{RESET}")
    
    print()
    
    # Latest stable (GREEN)
    print(f"{GREEN}{BOLD}🟢 LATEST STABLE VERSION ({len(latest_stable)}){RESET}")
    print(f"{GREEN}{'─'*80}{RESET}")
    if latest_stable:
        for pkg in latest_stable:
            print(f"{GREEN}  ✓ {pkg['name']:30} | Version: {pkg['constraint']:15} | Latest: {pkg['latest']:10}{RESET}")
    
    print(f"\n{BOLD}{'='*80}")
    print("📈 SUMMARY")
    print(f"{'='*80}{RESET}")
    print(f"  Total packages analyzed: {len(all_deps)}")
    print(f"  {RED}🔴 Deprecated:{RESET} {len(deprecated_packages)}")
    print(f"  {YELLOW}🟡 Stable but outdated:{RESET} {len(stable_not_latest)}")
    print(f"  {GREEN}🟢 Latest stable:{RESET} {len(latest_stable)}")
    print()
    
    # Generate markdown report
    generate_markdown_report(deprecated_packages, stable_not_latest, latest_stable, len(all_deps))


def generate_markdown_report(deprecated, stable_outdated, latest, total):
    """Generate a markdown report file."""
    with open('PACKAGE_STATUS_REPORT.md', 'w') as f:
        f.write("# 📦 Package Status Report\n\n")
        f.write(f"*Generated: {subprocess.check_output(['date']).decode().strip()}*\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total Packages**: {total}\n")
        f.write(f"- 🔴 **Deprecated**: {len(deprecated)}\n")
        f.write(f"- 🟡 **Stable but Outdated**: {len(stable_outdated)}\n")
        f.write(f"- 🟢 **Latest Stable**: {len(latest)}\n\n")
        
        f.write("---\n\n")
        
        # Deprecated
        f.write("## 🔴 Deprecated Packages\n\n")
        if deprecated:
            f.write("| Package | Current Constraint | Latest Version | Notes |\n")
            f.write("|---------|-------------------|----------------|-------|\n")
            for pkg in deprecated:
                f.write(f"| {pkg['name']} | {pkg['constraint']} | {pkg['latest']} | {pkg['reason']} |\n")
        else:
            f.write("✅ No deprecated packages found!\n")
        
        f.write("\n---\n\n")
        
        # Stable but outdated
        f.write("## 🟡 Stable but Not Latest Version\n\n")
        if stable_outdated:
            f.write("| Package | Current Constraint | Latest Version |\n")
            f.write("|---------|-------------------|----------------|\n")
            for pkg in stable_outdated:
                f.write(f"| {pkg['name']} | {pkg['constraint']} | {pkg['latest']} |\n")
        else:
            f.write("✅ All packages are at latest version!\n")
        
        f.write("\n---\n\n")
        
        # Latest stable
        f.write("## 🟢 Latest Stable Version\n\n")
        if latest:
            f.write("| Package | Version Constraint | Latest Version |\n")
            f.write("|---------|-------------------|----------------|\n")
            for pkg in latest:
                f.write(f"| {pkg['name']} | {pkg['constraint']} | {pkg['latest']} |\n")
        
        f.write("\n---\n\n")
        f.write("## Recommendations\n\n")
        f.write("1. **Deprecated Packages**: Replace these immediately with maintained alternatives\n")
        f.write("2. **Outdated Packages**: Consider updating to latest stable versions\n")
        f.write("3. **Latest Packages**: Continue monitoring for security updates\n\n")
    
    print(f"✅ Markdown report saved to: PACKAGE_STATUS_REPORT.md")


if __name__ == '__main__':
    try:
        import toml
    except ImportError:
        print("Installing required dependency: toml")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'toml'])
        import toml
    
    analyze_packages()
