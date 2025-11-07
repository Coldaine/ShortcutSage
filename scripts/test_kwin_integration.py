"""Test script to ensure KWin integration works properly."""

import os
import sys
from pathlib import Path


def test_kwin_script():
    """Test that the KWin script exists and is properly formatted."""
    kwin_script_path = Path("kwin/event-monitor.js")
    
    if not kwin_script_path.exists():
        print("ERROR: KWin script not found at kwin/event-monitor.js")
        return False
    
    content = kwin_script_path.read_text()
    
    # Check for essential components
    required_parts = [
        "Shortcut Sage",
        "SendEvent",
        "DAEMON_SERVICE",
        "DAEMON_PATH",
        "registerShortcut",
        "Ctrl+Alt+S"
    ]
    
    missing_parts = []
    for part in required_parts:
        if part not in content:
            missing_parts.append(part)
    
    if missing_parts:
        print(f"ERROR: Missing required parts in KWin script: {missing_parts}")
        return False
    
    print("SUCCESS: KWin script contains all required components")
    return True


if __name__ == "__main__":
    success = test_kwin_script()
    sys.exit(0 if success else 1)