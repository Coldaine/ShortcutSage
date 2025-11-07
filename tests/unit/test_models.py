"""Test configuration models."""

import pytest
from pydantic import ValidationError

from sage.models import (
    ContextMatch,
    Rule,
    RulesConfig,
    Shortcut,
    ShortcutsConfig,
    Suggestion,
)


class TestShortcut:
    """Test Shortcut model."""

    def test_valid_shortcut(self) -> None:
        """Test creating a valid shortcut."""
        shortcut = Shortcut(
            key="Meta+D", action="show_desktop", description="Show desktop"
        )
        assert shortcut.key == "Meta+D"
        assert shortcut.action == "show_desktop"
        assert shortcut.description == "Show desktop"
        assert shortcut.category == "general"

    def test_shortcut_with_category(self) -> None:
        """Test shortcut with custom category."""
        shortcut = Shortcut(
            key="Meta+Tab",
            action="overview",
            description="Show overview",
            category="desktop",
        )
        assert shortcut.category == "desktop"

    def test_empty_key_fails(self) -> None:
        """Test that empty key fails validation."""
        with pytest.raises(ValidationError, match="Key combination cannot be empty"):
            Shortcut(key="", action="test", description="Test")

    def test_empty_action_fails(self) -> None:
        """Test that empty action fails validation."""
        with pytest.raises(ValidationError, match="Action ID cannot be empty"):
            Shortcut(key="Meta+D", action="", description="Test")

    def test_action_normalized_to_lowercase(self) -> None:
        """Test that action is normalized to lowercase."""
        shortcut = Shortcut(
            key="Meta+D", action="Show_Desktop", description="Test"
        )
        assert shortcut.action == "show_desktop"

    def test_invalid_action_characters(self) -> None:
        """Test that action with invalid characters fails."""
        with pytest.raises(ValidationError, match="must be alphanumeric"):
            Shortcut(key="Meta+D", action="show desktop!", description="Test")


class TestShortcutsConfig:
    """Test ShortcutsConfig model."""

    def test_valid_config(self) -> None:
        """Test valid shortcuts configuration."""
        config = ShortcutsConfig(
            shortcuts=[
                Shortcut(key="Meta+D", action="show_desktop", description="Show desktop"),
                Shortcut(key="Meta+Tab", action="overview", description="Overview"),
            ]
        )
        assert len(config.shortcuts) == 2
        assert config.version == "1.0"

    def test_empty_shortcuts_fails(self) -> None:
        """Test that empty shortcuts list fails validation."""
        with pytest.raises(ValidationError):
            ShortcutsConfig(shortcuts=[])

    def test_duplicate_actions_fails(self) -> None:
        """Test that duplicate action IDs fail validation."""
        with pytest.raises(ValidationError, match="Duplicate action IDs"):
            ShortcutsConfig(
                shortcuts=[
                    Shortcut(key="Meta+D", action="show_desktop", description="First"),
                    Shortcut(
                        key="Meta+Shift+D", action="show_desktop", description="Second"
                    ),
                ]
            )


class TestContextMatch:
    """Test ContextMatch model."""

    def test_valid_context_string_pattern(self) -> None:
        """Test context with string pattern."""
        context = ContextMatch(type="event_sequence", pattern="show_desktop")
        assert context.type == "event_sequence"
        assert context.pattern == "show_desktop"
        assert context.window == 3

    def test_valid_context_list_pattern(self) -> None:
        """Test context with list pattern."""
        context = ContextMatch(
            type="event_sequence", pattern=["show_desktop", "overview"]
        )
        assert isinstance(context.pattern, list)
        assert len(context.pattern) == 2

    def test_custom_window_size(self) -> None:
        """Test custom window size."""
        context = ContextMatch(type="event_sequence", pattern="test", window=5)
        assert context.window == 5

    def test_window_size_bounds(self) -> None:
        """Test window size bounds."""
        with pytest.raises(ValidationError):
            ContextMatch(type="event_sequence", pattern="test", window=0)

        with pytest.raises(ValidationError):
            ContextMatch(type="event_sequence", pattern="test", window=11)

    def test_empty_pattern_fails(self) -> None:
        """Test that empty pattern fails validation."""
        with pytest.raises(ValidationError, match="Pattern cannot be empty"):
            ContextMatch(type="event_sequence", pattern="")

    def test_empty_list_pattern_fails(self) -> None:
        """Test that empty list pattern fails validation."""
        with pytest.raises(ValidationError, match="Pattern list cannot be empty"):
            ContextMatch(type="event_sequence", pattern=[])


class TestSuggestion:
    """Test Suggestion model."""

    def test_valid_suggestion(self) -> None:
        """Test creating a valid suggestion."""
        suggestion = Suggestion(action="overview", priority=80)
        assert suggestion.action == "overview"
        assert suggestion.priority == 80

    def test_default_priority(self) -> None:
        """Test default priority value."""
        suggestion = Suggestion(action="test")
        assert suggestion.priority == 50

    def test_priority_bounds(self) -> None:
        """Test priority bounds."""
        with pytest.raises(ValidationError):
            Suggestion(action="test", priority=-1)

        with pytest.raises(ValidationError):
            Suggestion(action="test", priority=101)

    def test_action_normalized(self) -> None:
        """Test that action is normalized."""
        suggestion = Suggestion(action="Show_Desktop")
        assert suggestion.action == "show_desktop"


class TestRule:
    """Test Rule model."""

    def test_valid_rule(self) -> None:
        """Test creating a valid rule."""
        rule = Rule(
            name="test_rule",
            context=ContextMatch(type="event_sequence", pattern="show_desktop"),
            suggest=[Suggestion(action="overview", priority=80)],
            cooldown=300,
        )
        assert rule.name == "test_rule"
        assert len(rule.suggest) == 1
        assert rule.cooldown == 300

    def test_default_cooldown(self) -> None:
        """Test default cooldown value."""
        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[Suggestion(action="test")],
        )
        assert rule.cooldown == 300

    def test_cooldown_bounds(self) -> None:
        """Test cooldown bounds."""
        with pytest.raises(ValidationError):
            Rule(
                name="test",
                context=ContextMatch(type="event_sequence", pattern="test"),
                suggest=[Suggestion(action="test")],
                cooldown=-1,
            )

        with pytest.raises(ValidationError):
            Rule(
                name="test",
                context=ContextMatch(type="event_sequence", pattern="test"),
                suggest=[Suggestion(action="test")],
                cooldown=3601,
            )

    def test_empty_suggestions_fails(self) -> None:
        """Test that empty suggestions list fails validation."""
        with pytest.raises(ValidationError):
            Rule(
                name="test",
                context=ContextMatch(type="event_sequence", pattern="test"),
                suggest=[],
            )


class TestRulesConfig:
    """Test RulesConfig model."""

    def test_valid_config(self) -> None:
        """Test valid rules configuration."""
        config = RulesConfig(
            rules=[
                Rule(
                    name="rule1",
                    context=ContextMatch(type="event_sequence", pattern="test1"),
                    suggest=[Suggestion(action="action1")],
                ),
                Rule(
                    name="rule2",
                    context=ContextMatch(type="event_sequence", pattern="test2"),
                    suggest=[Suggestion(action="action2")],
                ),
            ]
        )
        assert len(config.rules) == 2
        assert config.version == "1.0"

    def test_empty_rules_fails(self) -> None:
        """Test that empty rules list fails validation."""
        with pytest.raises(ValidationError):
            RulesConfig(rules=[])

    def test_duplicate_names_fails(self) -> None:
        """Test that duplicate rule names fail validation."""
        with pytest.raises(ValidationError, match="Duplicate rule names"):
            RulesConfig(
                rules=[
                    Rule(
                        name="same_name",
                        context=ContextMatch(type="event_sequence", pattern="test1"),
                        suggest=[Suggestion(action="action1")],
                    ),
                    Rule(
                        name="same_name",
                        context=ContextMatch(type="event_sequence", pattern="test2"),
                        suggest=[Suggestion(action="action2")],
                    ),
                ]
            )
