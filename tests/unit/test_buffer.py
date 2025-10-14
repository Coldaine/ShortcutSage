"""Test ring buffer."""

import pytest
from datetime import datetime, timedelta

from sage.buffer import RingBuffer
from sage.events import Event


class TestRingBuffer:
    """Test RingBuffer class."""

    def test_init_default_window(self) -> None:
        """Test initialization with default window size."""
        buffer = RingBuffer()
        assert buffer.window == timedelta(seconds=3.0)
        assert len(buffer) == 0

    def test_init_custom_window(self) -> None:
        """Test initialization with custom window size."""
        buffer = RingBuffer(window_seconds=5.0)
        assert buffer.window == timedelta(seconds=5.0)

    def test_init_invalid_window(self) -> None:
        """Test that invalid window size raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            RingBuffer(window_seconds=0)

        with pytest.raises(ValueError, match="must be positive"):
            RingBuffer(window_seconds=-1)

    def test_add_single_event(self) -> None:
        """Test adding a single event."""
        buffer = RingBuffer()
        now = datetime.now()
        event = Event(timestamp=now, type="test", action="test_action")

        buffer.add(event)
        assert len(buffer) == 1
        assert buffer.recent() == [event]

    def test_add_multiple_events(self) -> None:
        """Test adding multiple events."""
        buffer = RingBuffer()
        now = datetime.now()

        events = [
            Event(timestamp=now, type="test", action="action1"),
            Event(timestamp=now + timedelta(seconds=1), type="test", action="action2"),
            Event(timestamp=now + timedelta(seconds=2), type="test", action="action3"),
        ]

        for event in events:
            buffer.add(event)

        assert len(buffer) == 3
        assert buffer.recent() == events

    def test_prune_old_events(self) -> None:
        """Test that old events are pruned automatically."""
        buffer = RingBuffer(window_seconds=2.0)
        now = datetime.now()

        # Add events spanning 5 seconds
        events = [
            Event(timestamp=now, type="test", action="old1"),
            Event(timestamp=now + timedelta(seconds=1), type="test", action="old2"),
            Event(timestamp=now + timedelta(seconds=2), type="test", action="within"),
            Event(timestamp=now + timedelta(seconds=3), type="test", action="recent1"),
            Event(timestamp=now + timedelta(seconds=4), type="test", action="recent2"),
        ]

        for event in events:
            buffer.add(event)

        # Only last 2 seconds should remain (last 2 events)
        recent = buffer.recent()
        assert len(recent) == 2
        assert recent[0].action == "recent1"
        assert recent[1].action == "recent2"

    def test_actions_returns_action_list(self) -> None:
        """Test that actions() returns list of action IDs."""
        buffer = RingBuffer()
        now = datetime.now()

        events = [
            Event(timestamp=now, type="test", action="action1"),
            Event(timestamp=now + timedelta(seconds=0.5), type="test", action="action2"),
            Event(timestamp=now + timedelta(seconds=1), type="test", action="action3"),
        ]

        for event in events:
            buffer.add(event)

        assert buffer.actions() == ["action1", "action2", "action3"]

    def test_clear_empties_buffer(self) -> None:
        """Test that clear removes all events."""
        buffer = RingBuffer()
        now = datetime.now()

        buffer.add(Event(timestamp=now, type="test", action="test"))
        assert len(buffer) == 1

        buffer.clear()
        assert len(buffer) == 0
        assert buffer.recent() == []
        assert buffer.actions() == []

    def test_recent_prunes_on_call(self) -> None:
        """Test that recent() triggers pruning."""
        buffer = RingBuffer(window_seconds=1.0)
        now = datetime.now()

        # Add old event
        buffer.add(Event(timestamp=now - timedelta(seconds=2), type="test", action="old"))

        # Add recent event
        buffer.add(Event(timestamp=now, type="test", action="recent"))

        # Calling recent() should prune old event
        recent = buffer.recent()
        assert len(recent) == 1
        assert recent[0].action == "recent"
