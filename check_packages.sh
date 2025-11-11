#!/bin/bash
# Package Status Analysis Runner
# This script provides an easy way to run package analysis

echo "🔍 Starting Package Status Analysis..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the Python analysis script
python3 analyze_packages.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 Reports generated:"
echo "  - PACKAGE_STATUS_REPORT.md (Markdown format)"
echo "  - PACKAGE_STATUS_REPORT.html (Visual HTML report)"
echo ""
echo "💡 To view the HTML report, open PACKAGE_STATUS_REPORT.html in your browser"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
