"""Pydantic models for configuration schemas."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Shortcut(BaseModel):
    """A keyboard shortcut definition."""

    key: str = Field(description="Key combination (e.g., 'Meta+D')")
    action: str = Field(description="Semantic action ID")
    description: str = Field(description="Human-readable description")
    category: str = Field(default="general", description="Shortcut category")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate key combination format."""
        if not v or not v.strip():
            raise ValueError("Key combination cannot be empty")
        return v.strip()

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action ID format."""
        if not v or not v.strip():
            raise ValueError("Action ID cannot be empty")
        # Action IDs should be lowercase with underscores
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Action ID must be alphanumeric with underscores/hyphens")
        return v.strip().lower()


class ShortcutsConfig(BaseModel):
    """shortcuts.yaml schema."""

    version: Literal["1.0"] = "1.0"
    shortcuts: list[Shortcut] = Field(min_length=1, description="List of shortcuts")

    @field_validator("shortcuts")
    @classmethod
    def validate_unique_actions(cls, v: list[Shortcut]) -> list[Shortcut]:
        """Ensure action IDs are unique."""
        actions = [s.action for s in v]
        if len(actions) != len(set(actions)):
            duplicates = {a for a in actions if actions.count(a) > 1}
            raise ValueError(f"Duplicate action IDs found: {duplicates}")
        return v


class ContextMatch(BaseModel):
    """Context matching condition."""

    type: Literal["event_sequence", "recent_window", "desktop_state"]
    pattern: str | list[str] = Field(description="Pattern to match")
    window: int = Field(default=3, ge=1, le=10, description="Rolling window size (seconds)")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str | list[str]) -> str | list[str]:
        """Validate pattern is not empty."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Pattern cannot be empty")
            return v.strip()
        elif isinstance(v, list):
            if not v:
                raise ValueError("Pattern list cannot be empty")
            return [p.strip() for p in v if p.strip()]
        return v


class Suggestion(BaseModel):
    """A suggestion to surface."""

    action: str = Field(description="References shortcuts.yaml action")
    priority: int = Field(default=50, ge=0, le=100, description="Suggestion priority (0-100)")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action ID format."""
        if not v or not v.strip():
            raise ValueError("Action ID cannot be empty")
        return v.strip().lower()


class Rule(BaseModel):
    """Context-based suggestion rule."""

    name: str = Field(description="Unique rule name")
    context: ContextMatch
    suggest: list[Suggestion] = Field(min_length=1, description="Suggestions to surface")
    cooldown: int = Field(
        default=300, ge=0, le=3600, description="Seconds before re-suggesting"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate rule name is not empty."""
        if not v or not v.strip():
            raise ValueError("Rule name cannot be empty")
        return v.strip()


class RulesConfig(BaseModel):
    """rules.yaml schema."""

    version: Literal["1.0"] = "1.0"
    rules: list[Rule] = Field(min_length=1, description="List of rules")

    @field_validator("rules")
    @classmethod
    def validate_unique_names(cls, v: list[Rule]) -> list[Rule]:
        """Ensure rule names are unique."""
        names = [r.name for r in v]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate rule names found: {duplicates}")
        return v
