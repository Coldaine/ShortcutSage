"""Golden scenario integration tests for engine."""

from datetime import datetime, timedelta

from sage.events import Event
from sage.buffer import RingBuffer
from sage.features import FeatureExtractor
from sage.matcher import RuleMatcher
from sage.policy import PolicyEngine
from sage.models import Shortcut, Rule, Suggestion, ContextMatch


class TestEngineGoldenScenarios:
    """Integration tests with golden scenarios."""

    def test_show_desktop_suggests_overview(self) -> None:
        """Golden: show_desktop event → suggests overview and tiling."""
        # Setup
        shortcuts = {
            "overview": Shortcut(
                key="Meta+Tab", action="overview", description="Show overview"
            ),
            "tile_left": Shortcut(
                key="Meta+Left", action="tile_left", description="Tile left"
            ),
        }

        rules = [
            Rule(
                name="after_show_desktop",
                context=ContextMatch(type="event_sequence", pattern=["show_desktop"]),
                suggest=[
                    Suggestion(action="overview", priority=80),
                    Suggestion(action="tile_left", priority=60),
                ],
                cooldown=300,
            )
        ]

        buffer = RingBuffer(window_seconds=3.0)
        extractor = FeatureExtractor(buffer)
        matcher = RuleMatcher(rules)
        policy = PolicyEngine(shortcuts)

        # Simulate event
        now = datetime.now()
        buffer.add(Event(timestamp=now, type="desktop_state", action="show_desktop"))

        # Extract features
        features = extractor.extract()
        assert "show_desktop" in features["recent_actions"]

        # Match rules
        matches = matcher.match(features)
        assert len(matches) == 2

        # Apply policy
        results = policy.apply(matches, now=now, top_n=3)

        # Verify suggestions
        assert len(results) == 2
        assert results[0].action == "overview"
        assert results[0].priority == 80
        assert results[1].action == "tile_left"
        assert results[1].priority == 60

    def test_tile_left_suggests_tile_right(self) -> None:
        """Golden: tile_left → suggests tile_right."""
        shortcuts = {
            "tile_right": Shortcut(
                key="Meta+Right", action="tile_right", description="Tile right"
            ),
            "overview": Shortcut(
                key="Meta+Tab", action="overview", description="Overview"
            ),
        }

        rules = [
            Rule(
                name="after_tile_left",
                context=ContextMatch(type="event_sequence", pattern=["tile_left"]),
                suggest=[
                    Suggestion(action="tile_right", priority=85),
                    Suggestion(action="overview", priority=60),
                ],
                cooldown=180,
            )
        ]

        buffer = RingBuffer()
        extractor = FeatureExtractor(buffer)
        matcher = RuleMatcher(rules)
        policy = PolicyEngine(shortcuts)

        # Event
        now = datetime.now()
        buffer.add(Event(timestamp=now, type="window_move", action="tile_left"))

        # Process
        features = extractor.extract()
        matches = matcher.match(features)
        results = policy.apply(matches, now=now)

        # Verify
        assert len(results) == 2
        assert results[0].action == "tile_right"
        assert results[0].key == "Meta+Right"

    def test_cooldown_prevents_duplicate_suggestion(self) -> None:
        """Golden: Cooldown blocks repeated suggestions."""
        shortcuts = {
            "overview": Shortcut(
                key="Meta+Tab", action="overview", description="Overview"
            ),
        }

        rules = [
            Rule(
                name="test_rule",
                context=ContextMatch(type="event_sequence", pattern=["test_action"]),
                suggest=[Suggestion(action="overview", priority=80)],
                cooldown=5,  # 5 seconds
            )
        ]

        buffer = RingBuffer()
        extractor = FeatureExtractor(buffer)
        matcher = RuleMatcher(rules)
        policy = PolicyEngine(shortcuts)

        now = datetime.now()

        # First event - suggestion appears
        buffer.add(Event(timestamp=now, type="test", action="test_action"))
        features1 = extractor.extract()
        matches1 = matcher.match(features1)
        results1 = policy.apply(matches1, now=now)
        assert len(results1) == 1

        # Second event 2 seconds later - cooldown blocks
        buffer.add(Event(timestamp=now + timedelta(seconds=2), type="test", action="test_action"))
        features2 = extractor.extract()
        matches2 = matcher.match(features2)
        results2 = policy.apply(matches2, now=now + timedelta(seconds=2))
        assert len(results2) == 0

        # Third event 6 seconds later - cooldown expired
        buffer.add(Event(timestamp=now + timedelta(seconds=6), type="test", action="test_action"))
        features3 = extractor.extract()
        matches3 = matcher.match(features3)
        results3 = policy.apply(matches3, now=now + timedelta(seconds=6))
        assert len(results3) == 1

    def test_multiple_rules_priority_sorting(self) -> None:
        """Golden: Multiple matching rules sorted by priority."""
        shortcuts = {
            "action_a": Shortcut(key="A", action="action_a", description="A"),
            "action_b": Shortcut(key="B", action="action_b", description="B"),
            "action_c": Shortcut(key="C", action="action_c", description="C"),
            "action_d": Shortcut(key="D", action="action_d", description="D"),
        }

        rules = [
            Rule(
                name="rule1",
                context=ContextMatch(type="event_sequence", pattern=["trigger"]),
                suggest=[
                    Suggestion(action="action_a", priority=50),
                    Suggestion(action="action_b", priority=90),
                ],
                cooldown=300,
            ),
            Rule(
                name="rule2",
                context=ContextMatch(type="event_sequence", pattern=["trigger"]),
                suggest=[
                    Suggestion(action="action_c", priority=70),
                    Suggestion(action="action_d", priority=40),
                ],
                cooldown=300,
            ),
        ]

        buffer = RingBuffer()
        extractor = FeatureExtractor(buffer)
        matcher = RuleMatcher(rules)
        policy = PolicyEngine(shortcuts)

        # Event
        now = datetime.now()
        buffer.add(Event(timestamp=now, type="test", action="trigger"))

        # Process
        features = extractor.extract()
        matches = matcher.match(features)
        results = policy.apply(matches, now=now, top_n=3)

        # Verify sorted by priority: 90, 70, 50 (40 excluded by top_n=3)
        assert len(results) == 3
        assert results[0].priority == 90
        assert results[0].action == "action_b"
        assert results[1].priority == 70
        assert results[1].action == "action_c"
        assert results[2].priority == 50
        assert results[2].action == "action_a"

    def test_window_pruning_affects_matches(self) -> None:
        """Golden: Old events pruned from window don't match rules."""
        shortcuts = {
            "overview": Shortcut(key="Meta+Tab", action="overview", description="Overview"),
        }

        rules = [
            Rule(
                name="recent_only",
                context=ContextMatch(type="event_sequence", pattern=["old_action"]),
                suggest=[Suggestion(action="overview", priority=80)],
                cooldown=300,
            )
        ]

        buffer = RingBuffer(window_seconds=2.0)
        extractor = FeatureExtractor(buffer)
        matcher = RuleMatcher(rules)
        policy = PolicyEngine(shortcuts)

        now = datetime.now()

        # Add old event (outside window)
        buffer.add(Event(timestamp=now - timedelta(seconds=3), type="test", action="old_action"))

        # Add recent event
        buffer.add(Event(timestamp=now, type="test", action="new_action"))

        # Process
        features = extractor.extract()

        # Old action should be pruned
        assert "old_action" not in features["recent_actions"]
        assert "new_action" in features["recent_actions"]

        # Rule shouldn't match
        matches = matcher.match(features)
        assert len(matches) == 0
