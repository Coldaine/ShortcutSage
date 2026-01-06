#!/usr/bin/env python3
"""Visual test harness for overlay screenshot validation.

Run this on a graphical KDE Plasma environment (e.g., Nobara desktop).
It launches the overlay in demo mode, takes screenshots, and saves them
for visual review.

Usage:
    python scripts/visual_test_overlay.py

Output:
    screenshots/overlay_test_*.png - Screenshots for visual validation

Requirements:
    - PySide6 (pip install PySide6)
    - scrot or spectacle for screenshots (usually pre-installed on KDE)
    - Running KDE Plasma session
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def ensure_screenshot_dir() -> Path:
    """Create screenshots directory if needed."""
    screenshots_dir = PROJECT_ROOT / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    return screenshots_dir


def take_screenshot(name: str, screenshots_dir: Path) -> Path | None:
    """Take a screenshot using available tools."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = screenshots_dir / f"overlay_test_{name}_{timestamp}.png"

    # Try different screenshot tools
    tools = [
        ["spectacle", "-b", "-n", "-o", str(filename)],  # KDE
        ["scrot", "-o", str(filename)],                   # Generic X11
        ["gnome-screenshot", "-f", str(filename)],        # GNOME
        ["import", "-window", "root", str(filename)],     # ImageMagick
    ]

    for tool_cmd in tools:
        try:
            result = subprocess.run(
                tool_cmd,
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0 and filename.exists():
                print(f"  ✓ Screenshot saved: {filename.name}")
                return filename
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    print(f"  ✗ Failed to take screenshot (tried spectacle, scrot, gnome-screenshot, import)")
    return None


def run_visual_tests() -> dict[str, Path | None]:
    """Run visual tests and collect screenshots."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from sage.overlay import DEMO_SUGGESTIONS, OverlayWindow

    print("=" * 60)
    print("Shortcut Sage - Overlay Visual Test")
    print("=" * 60)
    print()

    screenshots_dir = ensure_screenshot_dir()
    results: dict[str, Path | None] = {}

    # Initialize Qt application
    app = QApplication([sys.argv[0]])
    app.setApplicationName("ShortcutSageVisualTest")

    # Create overlay in fallback mode (no DBus needed)
    print("1. Creating overlay window...")
    overlay = OverlayWindow(dbus_available=False)

    # Test sequence
    def test_sequence():
        nonlocal results

        # Test 1: Empty overlay
        print("\n2. Test: Empty overlay (no suggestions)")
        overlay.show()
        overlay.raise_()
        app.processEvents()
        time.sleep(0.5)
        results["01_empty"] = take_screenshot("01_empty", screenshots_dir)

        # Test 2: With demo suggestions
        print("\n3. Test: Overlay with demo suggestions")
        overlay.set_suggestions_fallback(DEMO_SUGGESTIONS)
        app.processEvents()
        time.sleep(0.5)
        results["02_with_suggestions"] = take_screenshot("02_suggestions", screenshots_dir)

        # Test 3: Single suggestion
        print("\n4. Test: Single suggestion")
        overlay.set_suggestions_fallback([DEMO_SUGGESTIONS[0]])
        app.processEvents()
        time.sleep(0.5)
        results["03_single"] = take_screenshot("03_single", screenshots_dir)

        # Test 4: Three suggestions (max)
        print("\n5. Test: Maximum suggestions (3)")
        three_suggestions = DEMO_SUGGESTIONS + [
            {
                "action": "tile_right",
                "key": "Meta+Right",
                "description": "Tile window to right half",
                "priority": 50,
            }
        ]
        overlay.set_suggestions_fallback(three_suggestions)
        app.processEvents()
        time.sleep(0.5)
        results["04_max_three"] = take_screenshot("04_max_three", screenshots_dir)

        # Test 5: Clear suggestions
        print("\n6. Test: Cleared suggestions")
        overlay.set_suggestions_fallback([])
        app.processEvents()
        time.sleep(0.5)
        results["05_cleared"] = take_screenshot("05_cleared", screenshots_dir)

        # Done
        print("\n" + "=" * 60)
        print("Visual tests complete!")
        print("=" * 60)

        # Summary
        print("\nScreenshots saved:")
        for name, path in results.items():
            status = "✓" if path else "✗"
            print(f"  {status} {name}: {path.name if path else 'FAILED'}")

        print(f"\nScreenshot directory: {screenshots_dir}")
        print("\nNext steps:")
        print("1. Review the screenshots visually")
        print("2. Share them for AI-assisted validation")
        print("3. Delete screenshots/ when done")

        app.quit()

    # Run test sequence after event loop starts
    QTimer.singleShot(500, test_sequence)

    # Run event loop
    app.exec()

    return results


def check_environment() -> bool:
    """Check that we're in a graphical environment."""
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not display:
        print("ERROR: No display available (DISPLAY or WAYLAND_DISPLAY not set)")
        print("This script must be run in a graphical session.")
        return False

    print(f"Display: {display}")
    return True


def main() -> int:
    """Main entry point."""
    print("Checking environment...")

    if not check_environment():
        return 1

    try:
        results = run_visual_tests()

        # Return success if at least some screenshots were taken
        successful = sum(1 for r in results.values() if r is not None)
        if successful > 0:
            print(f"\n✓ {successful}/{len(results)} screenshots captured successfully")
            return 0
        else:
            print("\n✗ No screenshots were captured")
            return 1

    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("Install with: pip install PySide6")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
