"""Shortcut research and export functionality for KDE Plasma."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from sage.models import Shortcut, ShortcutsConfig


@dataclass
class DiscoveredShortcut:
    """Represents a shortcut discovered from KDE system."""

    action_id: str
    key_sequence: str
    description: str
    category: str
    source: str  # Where it was found (e.g., "kglobalaccel", "kwin", "kglobalshortcutsrc")


class ShortcutExporter:
    """Tool to enumerate and export KDE shortcuts."""

    def __init__(self):
        self.discovered_shortcuts: list[DiscoveredShortcut] = []

    def discover_from_kglobalaccel(self) -> list[DiscoveredShortcut]:
        """Discover shortcuts using kglobalaccel command."""
        discovered = []

        try:
            # Use qdbus to get global accelerator info
            # This might not work without a running Plasma session, so we'll handle it gracefully
            result = subprocess.run(
                [
                    "qdbus",
                    "org.kde.kglobalaccel",
                    "/kglobalaccel",
                    "org.kde.kglobalaccel.shortcuts",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse the output to extract shortcuts
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if ":" in line:
                        parts = line.strip().split(":", 2)
                        if len(parts) >= 3:
                            action_id = parts[0].strip()
                            key_sequence = parts[1].strip()
                            description = parts[2].strip() if len(parts) > 2 else action_id

                            discovered.append(
                                DiscoveredShortcut(
                                    action_id=action_id.lower().replace(" ", "_").replace("-", "_"),
                                    key_sequence=key_sequence,
                                    description=description,
                                    category="system",
                                    source="kglobalaccel",
                                )
                            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # This is expected on systems without KDE Plasma
            print(
                "Warning: Could not access kglobalaccel (not running KDE Plasma?)", file=sys.stderr
            )

        return discovered

    def discover_from_config_files(self) -> list[DiscoveredShortcut]:
        """Discover shortcuts from KDE configuration files."""
        discovered = []

        # Common KDE config file locations
        config_paths = [
            Path.home() / ".config/kglobalshortcutsrc",
            Path.home() / ".config/kwinrc",
        ]

        for config_path in config_paths:
            if config_path.exists():
                discovered.extend(self._parse_kde_config(config_path))

        return discovered

    def _parse_kde_config(self, config_path: Path) -> list[DiscoveredShortcut]:
        """Parse KDE config file for shortcuts."""
        discovered = []

        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            # This is a simplified parser for KDE config files
            # Format: [Category] followed by action=shortcut,description,comment
            lines = content.split("\n")
            current_category = "unknown"

            for line in lines:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    # New section
                    current_category = line[1:-1]
                elif "=" in line and not line.startswith("#"):
                    # Potential shortcut line
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        action_id = parts[0].strip()
                        value_part = parts[1].strip()

                        # KDE shortcut format is usually: key,comment,friendly_name
                        value_parts = value_part.split(",", 2)
                        if len(value_parts) >= 1:
                            key_sequence = value_parts[0]
                            description = value_parts[2] if len(value_parts) > 2 else action_id

                            discovered.append(
                                DiscoveredShortcut(
                                    action_id=action_id.lower().replace(" ", "_").replace("-", "_"),
                                    key_sequence=key_sequence,
                                    description=description,
                                    category=current_category,
                                    source=str(config_path),
                                )
                            )
        except Exception as e:
            print(f"Warning: Could not parse config file {config_path}: {e}", file=sys.stderr)

        return discovered

    def discover_shortcuts(self) -> list[DiscoveredShortcut]:
        """Discover all available shortcuts from various sources."""
        all_discovered = []

        print("Discovering shortcuts from kglobalaccel...")
        all_discovered.extend(self.discover_from_kglobalaccel())

        print("Discovering shortcuts from config files...")
        all_discovered.extend(self.discover_from_config_files())

        # Filter out empty key sequences and deduplicate
        unique_shortcuts = {}
        for shortcut in all_discovered:
            # Use the action_id as key to deduplicate
            if (
                shortcut.key_sequence
                and shortcut.key_sequence.strip()
                and shortcut.action_id not in unique_shortcuts
            ):
                unique_shortcuts[shortcut.action_id] = shortcut

        self.discovered_shortcuts = list(unique_shortcuts.values())
        print(f"Discovered {len(self.discovered_shortcuts)} unique shortcuts")
        return self.discovered_shortcuts

    def export_to_yaml(self, output_file: Path, deduplicate: bool = True) -> bool:
        """Export discovered shortcuts to shortcuts.yaml format."""
        try:
            # Convert discovered shortcuts to our model format
            shortcut_models = []
            for ds in self.discovered_shortcuts:
                try:
                    shortcut = Shortcut(
                        key=ds.key_sequence,
                        action=ds.action_id,
                        description=ds.description,
                        category=ds.category,
                    )
                    shortcut_models.append(shortcut)
                except ValidationError as e:
                    print(f"Skipping invalid shortcut {ds.action_id}: {e}", file=sys.stderr)
                    continue

            # Create the config model
            config = ShortcutsConfig(version="1.0", shortcuts=shortcut_models)

            # Write to YAML file
            import yaml

            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)

            print(f"Exported {len(config.shortcuts)} shortcuts to {output_file}")
            return True

        except Exception as e:
            print(f"Error exporting shortcuts: {e}", file=sys.stderr)
            return False


def main():
    """Main entry point for the export-shortcuts tool."""
    if len(sys.argv) != 2:
        print("Usage: export-shortcuts <output_file.yaml>")
        sys.exit(1)

    output_file = Path(sys.argv[1])

    print("Shortcut Sage - Shortcut Exporter")
    print("=" * 40)

    exporter = ShortcutExporter()

    # Discover shortcuts
    discovered = exporter.discover_shortcuts()

    if not discovered:
        print("No shortcuts found. This may be because:")
        print("- You're not running KDE Plasma")
        print("- DBus is not available")
        print("- No shortcuts are configured")
        print("Creating a basic shortcuts file anyway...")

        # Create a minimal shortcuts file if nothing found
        import yaml

        basic_shortcuts = {
            "version": "1.0",
            "shortcuts": [
                {
                    "key": "Meta+D",
                    "action": "show_desktop",
                    "description": "Show desktop",
                    "category": "desktop",
                }
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(basic_shortcuts, f, default_flow_style=False)

        print(f"Created basic shortcuts file at {output_file}")
    else:
        # Export to YAML
        success = exporter.export_to_yaml(output_file)
        if success:
            print(f"Successfully exported shortcuts to {output_file}")
        else:
            print(f"Failed to export shortcuts to {output_file}")
            sys.exit(1)


if __name__ == "__main__":
    main()
