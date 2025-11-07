"""Feature extraction from event sequences."""

from typing import Any

from sage.buffer import RingBuffer


class FeatureExtractor:
    """Extracts context features from event buffer."""

    def __init__(self, buffer: RingBuffer):
        """
        Initialize feature extractor.

        Args:
            buffer: RingBuffer containing recent events
        """
        self.buffer = buffer

    def extract(self) -> dict[str, Any]:
        """
        Extract context features from recent events.

        Returns:
            Dictionary of extracted features
        """
        events = self.buffer.recent()
        actions = self.buffer.actions()

        if not events:
            return {
                "recent_actions": [],
                "event_count": 0,
                "last_action": None,
                "action_sequence": "",
            }

        return {
            "recent_actions": actions,
            "event_count": len(events),
            "last_action": actions[-1] if actions else None,
            "action_sequence": "_".join(actions[-3:]),  # Last 3 actions
            "unique_actions": list(set(actions)),
        }
