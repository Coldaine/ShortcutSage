"""Shared pytest fixtures."""

import pytest
from pathlib import Path
from typing import Generator


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory for tests."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_shortcuts_yaml(tmp_config_dir: Path) -> Path:
    """Create a sample shortcuts.yaml file."""
    shortcuts_file = tmp_config_dir / "shortcuts.yaml"
    shortcuts_file.write_text("""version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"
  - key: "Meta+Tab"
    action: "overview"
    description: "Show overview"
    category: "desktop"
  - key: "Meta+Left"
    action: "tile_left"
    description: "Tile window to left"
    category: "window"
""")
    return shortcuts_file


@pytest.fixture
def sample_rules_yaml(tmp_config_dir: Path) -> Path:
    """Create a sample rules.yaml file."""
    rules_file = tmp_config_dir / "rules.yaml"
    rules_file.write_text("""version: "1.0"
rules:
  - name: "after_show_desktop"
    context:
      type: "event_sequence"
      pattern: ["show_desktop"]
      window: 3
    suggest:
      - action: "overview"
        priority: 80
      - action: "tile_left"
        priority: 50
    cooldown: 300
""")
    return rules_file
