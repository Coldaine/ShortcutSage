"""Integration tests for DBus IPC."""

from __future__ import annotations

import json
import multiprocessing
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from sage.dbus_client import DBUS_AVAILABLE

# Skip all tests if DBus is not available
pytestmark = pytest.mark.skipif(not DBUS_AVAILABLE, reason="DBus not available")

pytest_plugins = ["dbusmock.pytest_fixtures"]

if DBUS_AVAILABLE:
    import dbus
    from gi.repository import GLib  # type: ignore[import-not-found]

    from sage.dbus_client import DBusClient
    from sage.dbus_daemon import run_daemon


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


def _wait_for_daemon(timeout: float = 5.0) -> None:
    """Wait until the DBus service is reachable."""
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            client = DBusClient()
            client.ping()
            return
        except Exception as exc:  # pragma: no cover - diagnostics only
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Daemon failed to start: {last_error}")


@pytest.fixture
def daemon_process(temp_config_dir: Path, dbusmock_session):
    """Start the daemon in a separate process against an isolated bus."""
    log_dir = temp_config_dir.parent / "logs"
    process = multiprocessing.Process(
        target=run_daemon,
        args=(str(temp_config_dir),),
        kwargs={"log_dir": str(log_dir)},
    )
    process.start()

    try:
        _wait_for_daemon()
    except Exception:
        process.terminate()
        process.join(timeout=5)
        raise

    yield process

    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()


@pytest.fixture
def dbus_client(daemon_process) -> DBusClient:  # noqa: PT004 - fixture ensures daemon running
    """Create a DBus client for testing."""
    return DBusClient()


def test_ping(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
    """Test the Ping method."""
    result = dbus_client.ping()
    assert result == "pong"


def test_send_event_valid_json(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
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
    buffer = dbus_client.get_buffer_state()
    assert len(buffer) == 1
    assert buffer[0]["action"] == "show_desktop"


def test_send_event_valid_json_string(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
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

    buffer = dbus_client.get_buffer_state()
    assert len(buffer) == 1
    assert buffer[0]["action"] == "tile_left"


def test_send_event_malformed_json(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
    """Test SendEvent with malformed JSON."""
    # Send malformed JSON - should not crash but should log error
    dbus_client.send_event("{invalid json}")

    # Give daemon time to process
    time.sleep(0.1)

    assert dbus_client.get_buffer_state() == []


def test_send_event_missing_fields(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
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

    assert dbus_client.get_buffer_state() == []


def test_suggestions_signal(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
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


def test_multiple_events_sequence(daemon_process, dbus_client: DBusClient) -> None:  # noqa: ARG001
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
    buffer = dbus_client.get_buffer_state()
    assert len(buffer) == 3


def test_daemon_is_running() -> None:
    """Test checking if daemon is running."""
    # This test doesn't need a daemon fixture
    # Just test the utility method
    # Note: May be False if no daemon is actually running
    result = DBusClient.is_daemon_running()
    assert isinstance(result, bool)


def test_dbus_error_handling(dbusmock_session) -> None:
    """Ensure client errors cleanly when daemon is not available."""
    with pytest.raises(dbus.DBusException) as exc_info:
        client = DBusClient()
        client.ping()

    assert "org.freedesktop.DBus.Error.NameHasNoOwner" in str(exc_info.value)
