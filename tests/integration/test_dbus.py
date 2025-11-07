"""Integration tests for DBus IPC."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from sage.dbus_client import DBUS_AVAILABLE

# Skip all tests if DBus is not available
pytestmark = pytest.mark.skipif(not DBUS_AVAILABLE, reason="DBus not available")


if DBUS_AVAILABLE:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib  # type: ignore[import-not-found]

    from sage.dbus_client import DBusClient
    from sage.dbus_daemon import Daemon


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with test configuration."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal shortcuts.yaml
    shortcuts_yaml = config_dir / "shortcuts.yaml"
    shortcuts_yaml.write_text(
        """version: "1.0"
shortcuts:
  - key: "Meta+Tab"
    action: "overview"
    description: "Show overview"
    category: "desktop"
  - key: "Meta+Left"
    action: "tile_left"
    description: "Tile window left"
    category: "window"
"""
    )

    # Create minimal rules.yaml
    rules_yaml = config_dir / "rules.yaml"
    rules_yaml.write_text(
        """version: "1.0"
rules:
  - name: "after_show_desktop"
    context:
      type: "event_sequence"
      pattern: ["show_desktop"]
      window: 3
    suggest:
      - action: "overview"
        priority: 80
    cooldown: 300
"""
    )

    return config_dir


@pytest.fixture
def daemon_process(temp_config_dir: Path) -> Daemon:
    """Start a daemon process for testing."""
    # Initialize DBus main loop
    DBusGMainLoop(set_as_default=True)

    # Create daemon with test configuration
    log_dir = temp_config_dir.parent / "logs"
    daemon = Daemon(str(temp_config_dir), enable_dbus=True, log_dir=log_dir)

    # Start the daemon in a background thread
    daemon.start()

    # Give daemon time to initialize
    time.sleep(0.5)

    yield daemon

    # Cleanup
    daemon.stop()


@pytest.fixture
def dbus_client() -> DBusClient:
    """Create a DBus client for testing."""
    return DBusClient()


def test_ping(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test the Ping method."""
    result = dbus_client.ping()
    assert result == "pong"


def test_send_event_valid_json(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test SendEvent with valid JSON."""
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "window_focus",
        "action": "show_desktop",
        "metadata": {},
    }

    # Should not raise an exception
    dbus_client.send_event(event_data)

    # Give daemon time to process
    time.sleep(0.1)

    # Verify event was added to buffer
    assert len(daemon_process.buffer.events) == 1
    assert daemon_process.buffer.events[0].action == "show_desktop"


def test_send_event_valid_json_string(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test SendEvent with valid JSON string."""
    event_json = json.dumps(
        {
            "timestamp": datetime.now().isoformat(),
            "type": "window_focus",
            "action": "tile_left",
            "metadata": {},
        }
    )

    # Should not raise an exception
    dbus_client.send_event(event_json)

    # Give daemon time to process
    time.sleep(0.1)

    # Verify event was added to buffer
    assert len(daemon_process.buffer.events) == 1
    assert daemon_process.buffer.events[0].action == "tile_left"


def test_send_event_malformed_json(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test SendEvent with malformed JSON."""
    # Send malformed JSON - should not crash but should log error
    dbus_client.send_event("{invalid json}")

    # Give daemon time to process
    time.sleep(0.1)

    # Buffer should be empty (event was rejected)
    assert len(daemon_process.buffer.events) == 0


def test_send_event_missing_fields(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test SendEvent with missing required fields."""
    # Missing 'action' field
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "window_focus",
        "metadata": {},
    }

    # Should not crash but should handle error gracefully
    dbus_client.send_event(event_data)

    # Give daemon time to process
    time.sleep(0.1)

    # Buffer should be empty (event was rejected)
    assert len(daemon_process.buffer.events) == 0


def test_suggestions_signal(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test Suggestions signal emission."""
    received_suggestions: list[Any] = []

    def callback(suggestions_json: str) -> None:
        suggestions = json.loads(suggestions_json)
        received_suggestions.extend(suggestions)

    # Subscribe to suggestions signal
    dbus_client.subscribe_suggestions(callback)

    # Send an event that should trigger suggestions
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "window_focus",
        "action": "show_desktop",
        "metadata": {},
    }

    dbus_client.send_event(event_data)

    # Process pending DBus messages
    context = GLib.MainContext.default()
    for _ in range(10):  # Try up to 10 iterations
        context.iteration(False)
        time.sleep(0.05)

    # Should have received suggestion for "overview" after "show_desktop"
    assert len(received_suggestions) > 0
    assert any(s["action"] == "overview" for s in received_suggestions)


def test_multiple_events_sequence(daemon_process: Daemon, dbus_client: DBusClient) -> None:
    """Test sending multiple events in sequence."""
    events = [
        {
            "timestamp": datetime.now().isoformat(),
            "type": "window_focus",
            "action": "show_desktop",
            "metadata": {},
        },
        {
            "timestamp": datetime.now().isoformat(),
            "type": "window_focus",
            "action": "tile_left",
            "metadata": {},
        },
        {
            "timestamp": datetime.now().isoformat(),
            "type": "window_focus",
            "action": "tile_right",
            "metadata": {},
        },
    ]

    for event in events:
        dbus_client.send_event(event)
        time.sleep(0.05)

    # Verify all events were processed
    assert len(daemon_process.buffer.events) == 3


def test_daemon_is_running() -> None:
    """Test checking if daemon is running."""
    # This test doesn't need a daemon fixture
    # Just test the utility method
    # Note: May be False if no daemon is actually running
    result = DBusClient.is_daemon_running()
    assert isinstance(result, bool)


def test_dbus_error_handling(temp_config_dir: Path) -> None:
    """Test error handling when daemon is not running."""
    # Don't start daemon
    with pytest.raises((dbus.DBusException, dbus.exceptions.DBusException)):  # type: ignore[attr-defined]
        client = DBusClient()
        client.ping()
