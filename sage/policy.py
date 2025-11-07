"""Policy engine for suggestion filtering and ranking."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import NamedTuple

from sage.models import Rule, Shortcut, Suggestion

logger = logging.getLogger(__name__)


class SuggestionResult(NamedTuple):
    """Final suggestion result with resolved shortcut info."""

    action: str
    key: str
    description: str
    priority: int
    adjusted_priority: int


class PersonalizationData:
    """Stores personalization data for CTR calculation."""

    def __init__(self) -> None:
        self.suggestion_count: int = 0  # Times suggested
        self.acceptance_count: int = 0  # Times accepted
        self.last_suggested: datetime = datetime.min
        self.last_accepted: datetime = datetime.min


class PolicyEngine:
    """Applies cooldowns, top-N filtering, and acceptance tracking."""

    def __init__(self, shortcuts: dict[str, Shortcut], enable_personalization: bool = True):
        """
        Initialize policy engine.

        Args:
            shortcuts: Dictionary mapping action IDs to Shortcut objects
            enable_personalization: Whether to enable personalization features
        """
        self.shortcuts = shortcuts
        self.enable_personalization = enable_personalization

        # Cooldown tracking
        self._cooldowns: dict[str, datetime] = {}

        # Personalization data
        self._personalization: dict[str, PersonalizationData] = defaultdict(PersonalizationData)

        # Track acceptance for backward compatibility
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
                # Update personalization data
                if self.enable_personalization:
                    personalization = self._personalization[key]
                    personalization.suggestion_count += 1
                    personalization.last_suggested = now

                valid.append((rule, suggestion))
                self._cooldowns[key] = now

        # Apply personalization adjustments to priorities if enabled
        if self.enable_personalization:
            adjusted_valid = []
            for rule, suggestion in valid:
                adjusted_suggestion = self._adjust_priority(rule, suggestion, now)
                adjusted_valid.append((rule, adjusted_suggestion))
            valid = adjusted_valid

        # Sort by adjusted priority (descending)
        valid.sort(key=lambda x: x[1].priority, reverse=True)

        # Take top N and resolve to shortcuts
        results: list[SuggestionResult] = []
        for _rule, suggestion in valid[:top_n]:
            shortcut = self.shortcuts.get(suggestion.action)
            if shortcut:
                results.append(
                    SuggestionResult(
                        action=suggestion.action,
                        key=shortcut.key,
                        description=shortcut.description,
                        priority=suggestion.priority,  # This is now the adjusted priority
                        adjusted_priority=suggestion.priority,  # Same as priority since it's adjusted
                    )
                )

        return results

    def _adjust_priority(self, rule: Rule, suggestion: Suggestion, now: datetime) -> Suggestion:
        """Adjust priority based on personalization data."""
        key = f"{rule.name}:{suggestion.action}"
        personalization = self._personalization[key]

        original_priority = suggestion.priority

        # Only apply significant adjustments when we have meaningful data
        # Start with original priority
        adjusted_priority = original_priority

        # Need at least a few suggestions before making adjustments
        if personalization.suggestion_count >= 5:
            ctr = personalization.acceptance_count / personalization.suggestion_count

            # Apply decay based on time since last acceptance
            time_factor = 1.0
            if personalization.last_accepted != datetime.min:
                time_since_acceptance = (now - personalization.last_accepted).total_seconds()
                # Apply decay: reduce score for suggestions not accepted recently
                # Decay factor reduces by ~10% every week of non-acceptance
                decay_time = max(0, time_since_acceptance - 3600)  # Start decay after 1 hour
                time_decay = 0.9 ** (decay_time / (7 * 24 * 3600))  # Weak weekly decay
                time_factor = time_decay

            # Adjust based on CTR: boost frequently accepted, reduce rarely accepted
            if ctr > 0.4:  # High acceptance rate
                ctr_factor = 1.15  # Boost by 15%
            elif ctr > 0.2:  # Medium acceptance rate
                ctr_factor = 1.0  # No change
            else:  # Low acceptance rate
                ctr_factor = 0.85  # Reduce by 15%

            # Apply adjustments
            base_adjustment = ctr_factor * time_factor
            adjusted_priority = int(original_priority * base_adjustment)

            # Ensure priority stays within bounds
            adjusted_priority = max(0, min(100, adjusted_priority))

        # Return a new Suggestion with the possibly adjusted priority
        return Suggestion(action=suggestion.action, priority=adjusted_priority)

    def mark_accepted(self, action: str, rule_name: str = "unknown") -> None:
        """
        Mark a suggestion as accepted by the user.

        Args:
            action: Action ID that was accepted
            rule_name: Name of the rule that triggered the suggestion (for personalization)
        """
        # Update global acceptance tracking
        self._accepted[action] = self._accepted.get(action, 0) + 1

        # Update personalization data if enabled
        if self.enable_personalization:
            key = f"{rule_name}:{action}"
            personalization = self._personalization[key]
            personalization.acceptance_count += 1
            personalization.last_accepted = datetime.now()

            logger.debug(
                f"Marked suggestion as accepted: {key}, CTR now {personalization.acceptance_count}/{personalization.suggestion_count}"
            )

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
