"""Test configuration loader."""

import pytest
from pathlib import Path

from sage.config import ConfigLoader, ConfigError
from sage.models import ShortcutsConfig, RulesConfig


class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_init_with_valid_directory(self, tmp_config_dir: Path) -> None:
        """Test initialization with valid directory."""
        loader = ConfigLoader(tmp_config_dir)
        assert loader.config_dir == tmp_config_dir

    def test_init_with_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test initialization with non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ConfigError, match="does not exist"):
            ConfigLoader(nonexistent)

    def test_init_with_file_not_directory(self, tmp_path: Path) -> None:
        """Test initialization with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(ConfigError, match="not a directory"):
            ConfigLoader(file_path)

    def test_load_shortcuts_success(
        self, tmp_config_dir: Path, sample_shortcuts_yaml: Path
    ) -> None:
        """Test loading valid shortcuts config."""
        loader = ConfigLoader(tmp_config_dir)
        config = loader.load_shortcuts()

        assert isinstance(config, ShortcutsConfig)
        assert len(config.shortcuts) == 3
        assert config.shortcuts[0].action == "show_desktop"

    def test_load_rules_success(
        self, tmp_config_dir: Path, sample_rules_yaml: Path
    ) -> None:
        """Test loading valid rules config."""
        loader = ConfigLoader(tmp_config_dir)
        config = loader.load_rules()

        assert isinstance(config, RulesConfig)
        assert len(config.rules) == 1
        assert config.rules[0].name == "after_show_desktop"

    def test_load_nonexistent_file(self, tmp_config_dir: Path) -> None:
        """Test loading non-existent config file."""
        loader = ConfigLoader(tmp_config_dir)
        with pytest.raises(ConfigError, match="not found"):
            loader.load("nonexistent.yaml", ShortcutsConfig)

    def test_load_invalid_yaml(self, tmp_config_dir: Path) -> None:
        """Test loading invalid YAML."""
        invalid_yaml = tmp_config_dir / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [")

        loader = ConfigLoader(tmp_config_dir)
        with pytest.raises(ConfigError, match="Invalid YAML"):
            loader.load("invalid.yaml", ShortcutsConfig)

    def test_load_empty_file(self, tmp_config_dir: Path) -> None:
        """Test loading empty config file."""
        empty_file = tmp_config_dir / "empty.yaml"
        empty_file.write_text("")

        loader = ConfigLoader(tmp_config_dir)
        with pytest.raises(ConfigError, match="empty"):
            loader.load("empty.yaml", ShortcutsConfig)

    def test_load_invalid_schema(self, tmp_config_dir: Path) -> None:
        """Test loading config with invalid schema."""
        invalid_config = tmp_config_dir / "invalid_schema.yaml"
        invalid_config.write_text(
            """
version: "1.0"
shortcuts:
  - key: ""
    action: "test"
    description: "Test"
"""
        )

        loader = ConfigLoader(tmp_config_dir)
        with pytest.raises(ConfigError, match="Invalid config"):
            loader.load("invalid_schema.yaml", ShortcutsConfig)

    def test_reload_both_configs(
        self, tmp_config_dir: Path, sample_shortcuts_yaml: Path, sample_rules_yaml: Path
    ) -> None:
        """Test reloading both config files."""
        loader = ConfigLoader(tmp_config_dir)
        shortcuts, rules = loader.reload()

        assert isinstance(shortcuts, ShortcutsConfig)
        assert isinstance(rules, RulesConfig)
        assert len(shortcuts.shortcuts) == 3
        assert len(rules.rules) == 1

    def test_config_with_duplicate_actions_fails(self, tmp_config_dir: Path) -> None:
        """Test that config with duplicate actions fails."""
        duplicate_config = tmp_config_dir / "duplicate.yaml"
        duplicate_config.write_text(
            """
version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "First"
  - key: "Meta+Shift+D"
    action: "show_desktop"
    description: "Second"
"""
        )

        loader = ConfigLoader(tmp_config_dir)
        with pytest.raises(ConfigError, match="Duplicate action IDs"):
            loader.load("duplicate.yaml", ShortcutsConfig)
