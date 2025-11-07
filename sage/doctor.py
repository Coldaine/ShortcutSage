#!/usr/bin/env python3
"""Doctor command for Shortcut Sage - diagnose and fix common issues."""

import os
import subprocess
import sys
from pathlib import Path


def check_system_requirements() -> list[tuple[str, bool, str]]:
    """Check if system requirements are met."""
    results = []

    # Check Python version
    python_ok = sys.version_info >= (3, 11)
    results.append(
        (
            "Python 3.11+",
            python_ok,
            f"Current: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    # Check if we're on Linux (for KDE)
    linux_ok = sys.platform.startswith("linux")
    results.append(("Linux platform", linux_ok, f"Current: {sys.platform}"))

    # Check if DBus is available
    import importlib.util

    dbus_ok = importlib.util.find_spec("dbus") is not None
    if dbus_ok:
        results.append(("DBus Python library", dbus_ok, "Available"))
    else:
        results.append(
            (
                "DBus Python library",
                dbus_ok,
                "Not available - install with: pip install 'shortcut-sage[dbus]'",
            )
        )

    # Check PySide6
    pyside_ok = importlib.util.find_spec("PySide6") is not None
    if pyside_ok:
        results.append(("PySide6 library", pyside_ok, "Available"))
    else:
        results.append(
            ("PySide6 library", pyside_ok, "Not available - install with: pip install PySide6")
        )

    return results


def check_kde_environment() -> list[tuple[str, bool, str]]:
    """Check if running in KDE environment."""
    results = []

    # Check if running under X11/Wayland with KDE
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    results.append(("Session type", True, f"Detected: {session_type}"))

    # Check for KDE-specific environment variables
    has_kde = (
        "KDE" in os.environ.get("DESKTOP_SESSION", "")
        or "plasma" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    )
    results.append(("KDE/Plasma environment", has_kde, "Required for full functionality"))

    # Check if kglobalaccel is running
    try:
        result = subprocess.run(["pgrep", "kglobalaccel5"], capture_output=True)
        kglobalaccel_running = result.returncode == 0
        results.append(
            ("KGlobalAccel running", kglobalaccel_running, "Required for shortcut detection")
        )
    except FileNotFoundError:
        results.append(("KGlobalAccel check", False, "pgrep not found - cannot verify"))

    return results


def check_config_files(config_dir: Path) -> list[tuple[str, bool, str]]:
    """Check if required config files exist."""
    results = []

    shortcuts_file = config_dir / "shortcuts.yaml"
    rules_file = config_dir / "rules.yaml"

    results.append(("shortcuts.yaml exists", shortcuts_file.exists(), str(shortcuts_file)))
    results.append(("rules.yaml exists", rules_file.exists(), str(rules_file)))

    return results


def create_default_configs(config_dir: Path) -> bool:
    """Create default configuration files if they don't exist."""
    config_dir.mkdir(parents=True, exist_ok=True)

    # Default shortcuts config
    shortcuts_default = """# Shortcut Sage - Default Shortcuts Configuration
version: "1.0"

shortcuts:
  # Desktop Navigation
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"

  - key: "Meta+Tab"
    action: "overview"
    description: "Show overview/task switcher"
    category: "desktop"

  - key: "Meta+PgUp"
    action: "switch_desktop_prev"
    description: "Switch to previous desktop"
    category: "desktop"

  - key: "Meta+PgDown"
    action: "switch_desktop_next"
    description: "Switch to next desktop"
    category: "desktop"

  # Window Management
  - key: "Meta+Left"
    action: "tile_left"
    description: "Tile window to left half"
    category: "window"

  - key: "Meta+Right"
    action: "tile_right"
    description: "Tile window to right half"
    category: "window"

  - key: "Meta+Up"
    action: "maximize"
    description: "Maximize window"
    category: "window"

  - key: "Meta+Down"
    action: "minimize"
    description: "Minimize window"
    category: "window"
"""

    # Default rules config
    rules_default = """# Shortcut Sage - Default Rules Configuration
version: "1.0"

rules:
  # After showing desktop, suggest overview
  - name: "after_show_desktop"
    context:
      type: "event_sequence"
      pattern: ["show_desktop"]
      window: 3
    suggest:
      - action: "overview"
        priority: 80
      - action: "tile_left"
        priority: 60
    cooldown: 300

  # After tiling left, suggest tiling right
  - name: "after_tile_left"
    context:
      type: "event_sequence"
      pattern: ["tile_left"]
      window: 5
    suggest:
      - action: "tile_right"
        priority: 85
      - action: "overview"
        priority: 60
    cooldown: 180
"""

    shortcuts_path = config_dir / "shortcuts.yaml"
    rules_path = config_dir / "rules.yaml"

    if not shortcuts_path.exists():
        with open(shortcuts_path, "w", encoding="utf-8") as f:
            f.write(shortcuts_default)
        print(f"Created default shortcuts config: {shortcuts_path}")
    else:
        print(f"Shortcuts config already exists: {shortcuts_path}")

    if not rules_path.exists():
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write(rules_default)
        print(f"Created default rules config: {rules_path}")
    else:
        print(f"Rules config already exists: {rules_path}")

    return True


def main() -> None:
    """Main doctor command."""
    print("Shortcut Sage - Doctor")
    print("=" * 50)

    # Check system requirements
    print("\n1. System Requirements")
    print("-" * 25)
    sys_results = check_system_requirements()
    for name, passed, info in sys_results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {info}")

    # Check KDE environment
    print("\n2. KDE Environment")
    print("-" * 18)
    kde_results = check_kde_environment()
    for name, passed, info in kde_results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {info}")

    # Check config files
    config_dir = Path.home() / ".config" / "shortcut-sage"
    print(f"\n3. Configuration Files (at {config_dir})")
    print("-" * 35)
    config_results = check_config_files(config_dir)
    for name, passed, info in config_results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {info}")

    # Offer to create default configs if missing
    missing_configs = any(not passed for name, passed, info in config_results)
    if missing_configs:
        response = input("\nWould you like to create default configuration files? (y/N): ")
        if response.lower() in ["y", "yes"]:
            create_default_configs(config_dir)

    # Final summary
    all_checks = sys_results + kde_results + config_results
    failed_checks = [name for name, passed, info in all_checks if not passed]

    print("\n4. Summary")
    print("-" * 9)
    if failed_checks:
        print(f"✗ Issues found: {len(failed_checks)}")
        for check in failed_checks:
            print(f"  - {check}")
        print("\nSome functionality may be limited. See documentation for setup instructions.")
    else:
        print("✓ All checks passed! Shortcut Sage should work correctly.")

    print("\nDoctor check complete.")


if __name__ == "__main__":
    main()
