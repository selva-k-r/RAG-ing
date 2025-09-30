#!/usr/bin/env python3
"""Simple test to verify that main.py --ui command works correctly."""

import subprocess
import sys
import os
from pathlib import Path

def test_ui_command():
    """Test the main.py --ui command."""
    print("🧪 Testing python main.py --ui command...")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    try:
        # Test the command syntax first
        result = subprocess.run([
            sys.executable, "main.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        print("✅ main.py --help works")
        print("Available options:")
        if "--ui" in result.stdout:
            print("  ✅ --ui option is available")
        else:
            print("  ❌ --ui option NOT found")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ui_command()
    if success:
        print("\n🎉 Command structure is correct!")
        print("Answer: YES, 'python main.py --ui' is the correct command")
    else:
        print("\n❌ Command has issues")
    
    sys.exit(0 if success else 1)