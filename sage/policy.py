"""Policy engine for suggestion filtering and ranking."""

from datetime import datetime, timedelta
from typing import NamedTuple

from sage.models import Rule, Suggestion, Shortcut


class SuggestionResult(NamedTuple):
    """Final suggestion result with resolved shortcut info."""

    action: str
    key: str
    description: str
    priority: int


class PolicyEngine:
    """Applies cooldowns, top-N filtering, and acceptance tracking."""

    def __init__(self, shortcuts: dict[str, Shortcut]):
        """
        Initialize policy engine.

        Args:
            shortcuts: Dictionary mapping action IDs to Shortcut objects
        """
        self.shortcuts = shortcuts
        self._cooldowns: dict[str, datetime] = {}
        self._accepted: dict[str, int] = {}  # Track acceptance count

    def apply(
        self,
        matches: list[tuple[Rule, Suggestion]],
        now: datetime | None = None,
        top_n: int = 3,
    ) -> list[SuggestionResult]:
        """
        Apply policy and return top N suggestions.

        Args:
            matches: List of (rule, suggestion) tuples from matcher
            now: Current time (defaults to datetime.now())
            top_n: Maximum number of suggestions to return

        Returns:
            List of SuggestionResult objects (max top_n)
        """
        if now is None:
            now = datetime.now()

        # Filter by cooldown
        valid: list[tuple[Rule, Suggestion]] = []
        for rule, suggestion in matches:
            key = f"{rule.name}:{suggestion.action}"
            last_suggested = self._cooldowns.get(key)

            if last_suggested is None or (now - last_suggested).total_seconds() >= rule.cooldown:
                valid.append((rule, suggestion))
                self._cooldowns[key] = now

        # Sort by priority (descending)
        valid.sort(key=lambda x: x[1].priority, reverse=True)

        # Take top N and resolve to shortcuts
        results: list[SuggestionResult] = []
        for rule, suggestion in valid[:top_n]:
            shortcut = self.shortcuts.get(suggestion.action)
            if shortcut:
                results.append(
                    SuggestionResult(
                        action=suggestion.action,
                        key=shortcut.key,
                        description=shortcut.description,
                        priority=suggestion.priority,
                    )
                )

        return results

    def mark_accepted(self, action: str) -> None:
        """
        Mark a suggestion as accepted by the user.

        Args:
            action: Action ID that was accepted
        """
        self._accepted[action] = self._accepted.get(action, 0) + 1

    def get_acceptance_count(self, action: str) -> int:
        """
        Get number of times an action was accepted.

        Args:
            action: Action ID

        Returns:
            Acceptance count
        """
        return self._accepted.get(action, 0)

    def clear_cooldowns(self) -> None:
        """Clear all cooldown timers (useful for testing)."""
        self._cooldowns.clear()
