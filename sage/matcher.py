"""Rule matching engine."""

from typing import Any

from sage.models import Rule, Suggestion


class RuleMatcher:
    """Matches context features against rules to find suggestions."""

    def __init__(self, rules: list[Rule]):
        """
        Initialize rule matcher.

        Args:
            rules: List of rules to match against
        """
        self.rules = rules

    def match(self, features: dict[str, Any]) -> list[tuple[Rule, Suggestion]]:
        """
        Find matching rules and their suggestions based on features.

        Args:
            features: Context features extracted from events

        Returns:
            List of (rule, suggestion) tuples for matching rules
        """
        matches: list[tuple[Rule, Suggestion]] = []

        for rule in self.rules:
            if self._matches_context(rule.context, features):
                for suggestion in rule.suggest:
                    matches.append((rule, suggestion))

        return matches

    def _matches_context(self, context: Any, features: dict[str, Any]) -> bool:
        """
        Check if context pattern matches features.

        Args:
            context: ContextMatch from rule
            features: Extracted features

        Returns:
            True if context matches
        """
        if context.type == "event_sequence":
            return self._match_event_sequence(context.pattern, features)
        elif context.type == "recent_window":
            return self._match_recent_window(context.pattern, features)
        elif context.type == "desktop_state":
            return self._match_desktop_state(context.pattern, features)

        return False

    def _match_event_sequence(
        self, pattern: str | list[str], features: dict[str, Any]
    ) -> bool:
        """Match event sequence pattern."""
        recent = features.get("recent_actions", [])
        if not recent:
            return False

        patterns = [pattern] if isinstance(pattern, str) else pattern

        # Simple substring match: any pattern in recent actions
        return any(p in recent for p in patterns)

    def _match_recent_window(
        self, pattern: str | list[str], features: dict[str, Any]
    ) -> bool:
        """Match recent window pattern (stub for MVP)."""
        # MVP: Same as event_sequence
        return self._match_event_sequence(pattern, features)

    def _match_desktop_state(
        self, pattern: str | list[str], features: dict[str, Any]
    ) -> bool:
        """Match desktop state pattern (stub for MVP)."""
        # MVP: Same as event_sequence
        return self._match_event_sequence(pattern, features)
