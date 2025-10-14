"""Event models and types."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

EventType = Literal["window_focus", "desktop_switch", "overview_toggle", "window_move", "test"]


@dataclass(frozen=True)
class Event:
    """Symbolic desktop event."""

    timestamp: datetime
    type: EventType
    action: str
    metadata: dict[str, str] | None = None

    def age_seconds(self, now: datetime) -> float:
        """
        Calculate age of event in seconds from a given time.

        Args:
            now: Current time to compare against

        Returns:
            Age in seconds
        """
        return (now - self.timestamp).total_seconds()

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """
        Create Event from dictionary (e.g., from JSON).

        Args:
            data: Event dictionary with timestamp, type, action, metadata

        Returns:
            Event instance
        """
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        return cls(
            timestamp=timestamp,
            type=data["type"],
            action=data["action"],
            metadata=data.get("metadata"),
        )
