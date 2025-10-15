"""Comprehensive tests for engine components."""

import pytest
from datetime import datetime, timedelta

from sage.events import Event
from sage.buffer import RingBuffer
from sage.features import FeatureExtractor
from sage.matcher import RuleMatcher
from sage.policy import PolicyEngine, SuggestionResult
from sage.models import (
    Rule,
    Suggestion,
    ContextMatch,
    Shortcut,
)


class TestEvent:
    """Test Event dataclass."""

    def test_create_event(self) -> None:
        """Test creating an event."""
        now = datetime.now()
        event = Event(
            timestamp=now,
            type="window_focus",
            action="show_desktop",
            metadata={"test": "value"},
        )

        assert event.timestamp == now
        assert event.type == "window_focus"
        assert event.action == "show_desktop"
        assert event.metadata == {"test": "value"}

    def test_event_age_seconds(self) -> None:
        """Test age calculation."""
        past = datetime.now() - timedelta(seconds=5)
        event = Event(timestamp=past, type="test", action="test")

        now = datetime.now()
        age = event.age_seconds(now)

        assert 4.9 < age < 5.1  # Allow small time variance

    def test_from_dict(self) -> None:
        """Test creating event from dictionary."""
        data = {
            "timestamp": "2025-10-14T04:30:00Z",
            "type": "window_focus",
            "action": "show_desktop",
            "metadata": {"key": "value"},
        }

        event = Event.from_dict(data)

        assert event.type == "window_focus"
        assert event.action == "show_desktop"
        assert event.metadata == {"key": "value"}

    def test_from_dict_without_metadata(self) -> None:
        """Test creating event without metadata."""
        data = {
            "timestamp": "2025-10-14T04:30:00Z",
            "type": "test",
            "action": "test_action",
        }

        event = Event.from_dict(data)
        assert event.metadata is None


class TestFeatureExtractor:
    """Test FeatureExtractor."""

    def test_extract_empty_buffer(self) -> None:
        """Test extraction from empty buffer."""
        buffer = RingBuffer()
        extractor = FeatureExtractor(buffer)

        features = extractor.extract()

        assert features["recent_actions"] == []
        assert features["event_count"] == 0
        assert features["last_action"] is None
        assert features["action_sequence"] == ""

    def test_extract_single_event(self) -> None:
        """Test extraction with single event."""
        buffer = RingBuffer()
        now = datetime.now()
        buffer.add(Event(timestamp=now, type="test", action="show_desktop"))

        extractor = FeatureExtractor(buffer)
        features = extractor.extract()

        assert features["recent_actions"] == ["show_desktop"]
        assert features["event_count"] == 1
        assert features["last_action"] == "show_desktop"
        assert features["action_sequence"] == "show_desktop"

    def test_extract_multiple_events(self) -> None:
        """Test extraction with multiple events."""
        buffer = RingBuffer()
        now = datetime.now()

        actions = ["show_desktop", "overview", "tile_left"]
        for i, action in enumerate(actions):
            buffer.add(Event(timestamp=now + timedelta(seconds=i * 0.5), type="test", action=action))

        extractor = FeatureExtractor(buffer)
        features = extractor.extract()

        assert features["recent_actions"] == actions
        assert features["event_count"] == 3
        assert features["last_action"] == "tile_left"
        assert features["action_sequence"] == "show_desktop_overview_tile_left"

    def test_extract_action_sequence_max_three(self) -> None:
        """Test that action sequence includes max 3 actions."""
        buffer = RingBuffer()
        now = datetime.now()

        actions = ["action1", "action2", "action3", "action4", "action5"]
        for i, action in enumerate(actions):
            buffer.add(Event(timestamp=now + timedelta(seconds=i * 0.5), type="test", action=action))

        extractor = FeatureExtractor(buffer)
        features = extractor.extract()

        # Should only include last 3
        assert features["action_sequence"] == "action3_action4_action5"


class TestRuleMatcher:
    """Test RuleMatcher."""

    def test_match_no_rules(self) -> None:
        """Test matching with no rules."""
        matcher = RuleMatcher([])
        features = {"recent_actions": ["show_desktop"]}

        matches = matcher.match(features)
        assert matches == []

    def test_match_single_pattern_string(self) -> None:
        """Test matching with single string pattern."""
        rule = Rule(
            name="test_rule",
            context=ContextMatch(type="event_sequence", pattern="show_desktop"),
            suggest=[Suggestion(action="overview", priority=80)],
        )

        matcher = RuleMatcher([rule])
        features = {"recent_actions": ["show_desktop", "tile_left"]}

        matches = matcher.match(features)

        assert len(matches) == 1
        assert matches[0][0].name == "test_rule"
        assert matches[0][1].action == "overview"

    def test_match_pattern_list(self) -> None:
        """Test matching with list of patterns."""
        rule = Rule(
            name="test_rule",
            context=ContextMatch(
                type="event_sequence",
                pattern=["tile_left", "tile_right"],
            ),
            suggest=[Suggestion(action="overview", priority=80)],
        )

        matcher = RuleMatcher([rule])

        # Match tile_left
        features1 = {"recent_actions": ["tile_left"]}
        matches1 = matcher.match(features1)
        assert len(matches1) == 1

        # Match tile_right
        features2 = {"recent_actions": ["tile_right"]}
        matches2 = matcher.match(features2)
        assert len(matches2) == 1

        # No match
        features3 = {"recent_actions": ["show_desktop"]}
        matches3 = matcher.match(features3)
        assert len(matches3) == 0

    def test_match_multiple_suggestions(self) -> None:
        """Test rule with multiple suggestions."""
        rule = Rule(
            name="test_rule",
            context=ContextMatch(type="event_sequence", pattern="show_desktop"),
            suggest=[
                Suggestion(action="overview", priority=80),
                Suggestion(action="tile_left", priority=60),
                Suggestion(action="tile_right", priority=60),
            ],
        )

        matcher = RuleMatcher([rule])
        features = {"recent_actions": ["show_desktop"]}

        matches = matcher.match(features)

        assert len(matches) == 3
        assert {m[1].action for m in matches} == {"overview", "tile_left", "tile_right"}


class TestPolicyEngine:
    """Test PolicyEngine."""

    @pytest.fixture
    def shortcuts(self) -> dict[str, Shortcut]:
        """Sample shortcuts dictionary."""
        return {
            "overview": Shortcut(
                key="Meta+Tab",
                action="overview",
                description="Show overview",
            ),
            "tile_left": Shortcut(
                key="Meta+Left",
                action="tile_left",
                description="Tile window to left",
            ),
            "tile_right": Shortcut(
                key="Meta+Right",
                action="tile_right",
                description="Tile window to right",
            ),
        }

    def test_apply_empty_matches(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test applying policy with no matches."""
        engine = PolicyEngine(shortcuts)
        results = engine.apply([])

        assert results == []

    def test_apply_single_match(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test applying policy with single match."""
        engine = PolicyEngine(shortcuts)

        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[Suggestion(action="overview", priority=80)],
        )

        matches = [(rule, rule.suggest[0])]
        results = engine.apply(matches)

        assert len(results) == 1
        assert results[0].action == "overview"
        assert results[0].key == "Meta+Tab"
        assert results[0].description == "Show overview"
        assert results[0].priority == 80

    def test_apply_top_n_filtering(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test top-N filtering."""
        engine = PolicyEngine(shortcuts)

        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[
                Suggestion(action="overview", priority=80),
                Suggestion(action="tile_left", priority=70),
                Suggestion(action="tile_right", priority=60),
            ],
        )

        matches = [(rule, s) for s in rule.suggest]

        # Top 2
        results = engine.apply(matches, top_n=2)
        assert len(results) == 2
        assert results[0].priority == 80
        assert results[1].priority == 70

    def test_apply_cooldown(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test cooldown prevents re-suggestion."""
        engine = PolicyEngine(shortcuts)

        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[Suggestion(action="overview", priority=80)],
            cooldown=10,  # 10 seconds
        )

        matches = [(rule, rule.suggest[0])]
        now = datetime.now()

        # First suggestion succeeds
        results1 = engine.apply(matches, now=now)
        assert len(results1) == 1

        # Second suggestion within cooldown is blocked
        results2 = engine.apply(matches, now=now + timedelta(seconds=5))
        assert len(results2) == 0

        # Third suggestion after cooldown succeeds
        results3 = engine.apply(matches, now=now + timedelta(seconds=11))
        assert len(results3) == 1

    def test_apply_priority_sorting(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test that suggestions are sorted by priority."""
        engine = PolicyEngine(shortcuts)

        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[
                Suggestion(action="tile_left", priority=50),
                Suggestion(action="overview", priority=90),
                Suggestion(action="tile_right", priority=70),
            ],
        )

        matches = [(rule, s) for s in rule.suggest]
        results = engine.apply(matches)

        # Should be sorted: 90, 70, 50
        assert results[0].priority == 90
        assert results[1].priority == 70
        assert results[2].priority == 50

    def test_mark_accepted(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test marking suggestions as accepted."""
        engine = PolicyEngine(shortcuts)

        assert engine.get_acceptance_count("overview") == 0

        engine.mark_accepted("overview", "test_rule")
        assert engine.get_acceptance_count("overview") == 1

        engine.mark_accepted("overview", "test_rule")
        assert engine.get_acceptance_count("overview") == 2

    def test_clear_cooldowns(self, shortcuts: dict[str, Shortcut]) -> None:
        """Test clearing cooldown timers."""
        engine = PolicyEngine(shortcuts)

        rule = Rule(
            name="test",
            context=ContextMatch(type="event_sequence", pattern="test"),
            suggest=[Suggestion(action="overview", priority=80)],
            cooldown=10,
        )

        matches = [(rule, rule.suggest[0])]
        now = datetime.now()

        # Trigger cooldown
        engine.apply(matches, now=now)

        # Clear cooldowns
        engine.clear_cooldowns()

        # Should be able to suggest again immediately
        results = engine.apply(matches, now=now)
        assert len(results) == 1
