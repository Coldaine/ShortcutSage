"""Configuration loading and validation."""

import yaml
from pathlib import Path
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError

from sage.models import ShortcutsConfig, RulesConfig

T = TypeVar("T", bound=BaseModel)


class ConfigError(Exception):
    """Configuration error."""

    pass


class ConfigLoader:
    """Loads and validates YAML configs."""

    def __init__(self, config_dir: Path | str):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise ConfigError(f"Config directory does not exist: {self.config_dir}")
        if not self.config_dir.is_dir():
            raise ConfigError(f"Config path is not a directory: {self.config_dir}")

    def load(self, filename: str, model: Type[T]) -> T:
        """
        Load and validate a config file.

        Args:
            filename: Config filename (e.g., 'shortcuts.yaml')
            model: Pydantic model class to validate against

        Returns:
            Validated config model instance

        Raises:
            ConfigError: If file not found or validation fails
        """
        path = self.config_dir / filename

        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {filename}: {e}") from e
        except Exception as e:
            raise ConfigError(f"Failed to read {filename}: {e}") from e

        if data is None:
            raise ConfigError(f"Config file is empty: {filename}")

        try:
            return model.model_validate(data)
        except ValidationError as e:
            raise ConfigError(f"Invalid config in {filename}: {e}") from e

    def load_shortcuts(self) -> ShortcutsConfig:
        """
        Load shortcuts.yaml configuration.

        Returns:
            Validated ShortcutsConfig

        Raises:
            ConfigError: If loading or validation fails
        """
        return self.load("shortcuts.yaml", ShortcutsConfig)

    def load_rules(self) -> RulesConfig:
        """
        Load rules.yaml configuration.

        Returns:
            Validated RulesConfig

        Raises:
            ConfigError: If loading or validation fails
        """
        return self.load("rules.yaml", RulesConfig)

    def reload(self) -> tuple[ShortcutsConfig, RulesConfig]:
        """
        Reload both config files.

        Returns:
            Tuple of (shortcuts_config, rules_config)

        Raises:
            ConfigError: If loading or validation fails
        """
        return self.load_shortcuts(), self.load_rules()
