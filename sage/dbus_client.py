"""DBus client for testing and interacting with Shortcut Sage daemon."""

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Try to import DBus, but allow fallback if not available
try:
    import dbus

    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logger.warning("DBus not available, client will not work")


class DBusClient:
    """Client for interacting with Shortcut Sage DBus daemon."""

    BUS_NAME = "org.shortcutsage.Daemon"
    OBJECT_PATH = "/org/shortcutsage/Daemon"
    INTERFACE = "org.shortcutsage.Daemon"

    def __init__(self) -> None:
        """Initialize the DBus client."""
        if not DBUS_AVAILABLE:
            raise ImportError("DBus not available")

        self.bus = dbus.SessionBus()
        self.proxy = self.bus.get_object(self.BUS_NAME, self.OBJECT_PATH)
        self.interface = dbus.Interface(self.proxy, dbus_interface=self.INTERFACE)

    def send_event(self, event_json: str | dict[str, Any]) -> None:
        """Send an event to the daemon.

        Args:
            event_json: Event as JSON string or dict. If dict, will be serialized.

        Raises:
            dbus.DBusException: If the daemon is not running or the call fails.
        """
        if isinstance(event_json, dict):
            event_json = json.dumps(event_json)

        self.interface.SendEvent(event_json)
        logger.debug(f"Sent event: {event_json}")

    def ping(self) -> str:
        """Ping the daemon to check if it's alive.

        Returns:
            "pong" if the daemon is alive.

        Raises:
            dbus.DBusException: If the daemon is not running.
        """
        result = self.interface.Ping()
        logger.debug(f"Ping result: {result}")
        return result

    def subscribe_suggestions(self, callback: Callable[[str], None]) -> None:
        """Subscribe to the Suggestions signal.

        Args:
            callback: Function to call when suggestions are received.
                      Takes a JSON string of suggestions.
        """

        def signal_handler(suggestions_json: str) -> None:
            logger.debug(f"Received suggestions: {suggestions_json}")
            callback(suggestions_json)

        self.bus.add_signal_receiver(
            signal_handler,
            dbus_interface=self.INTERFACE,
            signal_name="Suggestions",
        )

    def get_buffer_state(self) -> list[dict[str, Any]]:
        """Return the daemon's current buffer state."""
        raw_state = self.interface.GetBufferState()
        normalized: list[dict[str, Any]] = []
        for row in raw_state:
            normalized.append({str(key): self._to_python(value) for key, value in row.items()})
        return normalized

    @staticmethod
    def _to_python(value: Any) -> Any:
        """Convert DBus-specific types to plain Python objects."""
        if not DBUS_AVAILABLE:
            return value

        if isinstance(value, dbus.Dictionary):
            return {str(k): DBusClient._to_python(v) for k, v in value.items()}
        if isinstance(value, dbus.Array):
            return [DBusClient._to_python(v) for v in value]
        if isinstance(value, (dbus.String, dbus.ObjectPath)):
            return str(value)
        if isinstance(value, (dbus.Int32, dbus.UInt32, dbus.Int64, dbus.UInt64)):
            return int(value)
        if isinstance(value, dbus.Double):
            return float(value)
        if isinstance(value, dbus.Boolean):
            return bool(value)
        return value

    @staticmethod
    def is_daemon_running() -> bool:
        """Check if the daemon is running.

        Returns:
            True if the daemon is running, False otherwise.
        """
        if not DBUS_AVAILABLE:
            return False

        try:
            bus = dbus.SessionBus()
            return bus.name_has_owner(DBusClient.BUS_NAME)
        except dbus.DBusException:
            return False
