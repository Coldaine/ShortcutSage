"""Ring buffer for time-windowed events."""

from collections import deque
from datetime import datetime, timedelta

from sage.events import Event


class RingBuffer:
    """Time-windowed event buffer with automatic pruning."""

    def __init__(self, window_seconds: float = 3.0):
        """
        Initialize ring buffer.

        Args:
            window_seconds: Time window to keep events (default 3.0 seconds)
        """
        if window_seconds <= 0:
            raise ValueError("Window size must be positive")

        self.window = timedelta(seconds=window_seconds)
        self._events: deque[Event] = deque()

    def add(self, event: Event) -> None:
        """
        Add event to buffer and prune old events.

        Args:
            event: Event to add
        """
        self._events.append(event)
        self._prune()

    def _prune(self) -> None:
        """Remove events outside the time window."""
        if not self._events:
            return

        cutoff = self._events[-1].timestamp - self.window

        while self._events and self._events[0].timestamp <= cutoff:
            self._events.popleft()

    def recent(self) -> list[Event]:
        """
        Get all events in current window.

        Returns:
            List of recent events (oldest to newest)
        """
        self._prune()
        return list(self._events)

    def actions(self) -> list[str]:
        """
        Get sequence of recent action IDs.

        Returns:
            List of action IDs from recent events
        """
        return [e.action for e in self.recent()]

    def clear(self) -> None:
        """Clear all events from buffer."""
        self._events.clear()

    def __len__(self) -> int:
        """Get number of events in buffer."""
        return len(self._events)
