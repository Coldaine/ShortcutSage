"""DBus daemon for Shortcut Sage (with fallback for systems without DBus)."""

import json
import logging
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sage.buffer import RingBuffer
from sage.config import ConfigLoader
from sage.features import FeatureExtractor
from sage.matcher import RuleMatcher
from sage.policy import PolicyEngine, SuggestionResult
from sage.telemetry import EventType, init_telemetry, log_event

logger = logging.getLogger(__name__)

# Try to import DBus, but allow fallback if not available
try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib  # type: ignore[import-not-found]

    DBUS_AVAILABLE = True
    logger.info("DBus support available")
except ImportError:
    DBUS_AVAILABLE = False
    logger.info("DBus support not available, using fallback")


class Daemon:
    """DBus service for Shortcut Sage daemon (with fallback implementation)."""

    def __init__(
        self,
        config_dir: str,
        enable_dbus: bool = True,
        log_events: bool = True,
        log_dir: str | Path | None = None,
    ) -> None:
        """Initialize the daemon."""
        self.enable_dbus = enable_dbus and DBUS_AVAILABLE
        self.log_events = log_events  # Whether to log events and suggestions

        # Initialize telemetry
        if log_dir is None:
            # Default log directory
            log_dir = Path.home() / ".local" / "share" / "shortcut-sage" / "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.telemetry = init_telemetry(self.log_dir)

        # Log daemon start
        log_event(
            EventType.DAEMON_START,
            properties={"dbus_enabled": self.enable_dbus, "config_dir": str(config_dir)},
        )

        # Load configuration
        self.config_loader = ConfigLoader(config_dir)
        self.shortcuts_config, self.rules_config = self.config_loader.reload()

        # Initialize engine components
        self.buffer = RingBuffer(window_seconds=3.0)
        self.feature_extractor = FeatureExtractor(self.buffer)
        self.rule_matcher = RuleMatcher(self.rules_config.rules)
        self.policy_engine = PolicyEngine({s.action: s for s in self.shortcuts_config.shortcuts})

        # Set up config reload callback
        self._setup_config_reload()

        # Store callback for suggestions (to be set by caller if not using DBus)
        self.suggestions_callback: Callable[[list[SuggestionResult]], None] | None = None

        if self.enable_dbus:
            self._init_dbus_service()

        logger.info(f"Daemon initialized (DBus: {self.enable_dbus}, logging: {self.log_events})")

    def _init_dbus_service(self) -> None:
        """Initialize the DBus service if available."""
        if not self.enable_dbus:
            return

        # Initialize the D-Bus main loop
        DBusGMainLoop(set_as_default=True)

        # Define the D-Bus service name and object path
        self.BUS_NAME = "org.shortcutsage.Daemon"
        self.OBJECT_PATH = "/org/shortcutsage/Daemon"

        # Create the DBus service object
        bus_name = dbus.service.BusName(self.BUS_NAME, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

    def _setup_config_reload(self) -> None:
        """Set up configuration reload callback."""
        from sage.watcher import ConfigWatcher

        def reload_config(filename: str) -> None:
            """Reload config when file changes."""
            try:
                if filename == "shortcuts.yaml":
                    shortcuts_config = self.config_loader.load_shortcuts()
                    self.policy_engine.shortcuts = {s.action: s for s in shortcuts_config.shortcuts}
                elif filename == "rules.yaml":
                    rules_config = self.config_loader.load_rules()
                    self.rule_matcher = RuleMatcher(rules_config.rules)
                logger.info(f"Reloaded config: {filename}")
            except Exception as e:
                logger.error(f"Failed to reload config {filename}: {e}")

        self.watcher = ConfigWatcher(self.config_loader.config_dir, reload_config)

    def send_event(self, event_json: str) -> None:
        """Receive and process an event from KWin or other sources."""
        start_time = time.time()

        try:
            # Parse the event JSON
            event_data = json.loads(event_json)

            # Create an event object
            from datetime import datetime

            from sage.events import Event

            timestamp_str = event_data["timestamp"]
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = timestamp_str

            event = Event(
                timestamp=timestamp,
                type=event_data["type"],
                action=event_data["action"],
                metadata=event_data.get("metadata"),
            )

            # Add event to buffer
            self.buffer.add(event)

            # Extract features and match rules
            features = self.feature_extractor.extract()
            matches = self.rule_matcher.match(features)
            suggestions = self.policy_engine.apply(matches, now=datetime.now())

            # Calculate processing metrics
            processing_time = time.time() - start_time
            latency = (datetime.now() - timestamp).total_seconds()

            # Log the event processing if enabled
            if self.log_events:
                logger.info(
                    f"Event processed: {event.action} -> {len(suggestions)} suggestions "
                    f"(processing_time: {processing_time:.3f}s, "
                    f"latency: {latency:.3f}s)"
                )

                # Log detailed suggestions if any
                for i, suggestion in enumerate(suggestions):
                    logger.debug(
                        f"Suggestion {i + 1}: {suggestion.action} ({suggestion.key}) - priority {suggestion.priority}"
                    )

            # Log to telemetry
            log_event(
                EventType.EVENT_RECEIVED,
                duration=processing_time,
                properties={
                    "action": event.action,
                    "type": event.type,
                    "suggestions_count": len(suggestions),
                    "processing_time": processing_time,
                    "latency": latency,
                },
            )

            # Log each suggestion shown
            for suggestion in suggestions:
                log_event(
                    EventType.SUGGESTION_SHOWN,
                    properties={
                        "action": suggestion.action,
                        "key": suggestion.key,
                        "priority": suggestion.priority,
                    },
                )

            # Emit the suggestions
            self.emit_suggestions(suggestions)

            logger.debug(f"Processed event: {event.action}")

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            if self.log_events:
                processing_time = time.time() - start_time
                logger.error(f"Event processing failed after {processing_time:.3f}s: {e}")

            # Log error to telemetry
            log_event(
                EventType.ERROR_OCCURRED,
                duration=time.time() - start_time,
                properties={"error": str(e), "error_type": type(e).__name__},
            )

    def ping(self) -> str:
        """Simple ping method to check if daemon is alive."""
        return "pong"

    def emit_suggestions(self, suggestions: list[SuggestionResult]) -> str:
        """Emit suggestions (as signal if DBus available, or via callback)."""
        # Convert suggestions to JSON
        suggestions_json = json.dumps(
            [
                {
                    "action": s.action,
                    "key": s.key,
                    "description": s.description,
                    "priority": s.priority,
                }
                for s in suggestions
            ]
        )
        logger.debug(f"Emitted suggestions: {suggestions_json}")

        # If not using DBus, call the callback if available
        if not self.enable_dbus and self.suggestions_callback:
            self.suggestions_callback(suggestions)

        return suggestions_json

    def set_suggestions_callback(self, callback: Callable[[list[SuggestionResult]], None]) -> None:
        """Set callback for suggestions (used when DBus is not available)."""
        self.suggestions_callback = callback

    def start(self) -> None:
        """Start the daemon."""
        self.watcher.start()
        if self.enable_dbus:
            logger.info(f"Daemon started on {self.BUS_NAME}")
        else:
            logger.info("Daemon started (fallback mode)")

    def stop(self) -> None:
        """Stop the daemon."""
        self.watcher.stop()
        logger.info("Daemon stopped")


def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) not in [2, 3]:
        print("Usage: shortcut-sage <config_dir> [log_dir]")
        sys.exit(1)

    config_dir = sys.argv[1]
    log_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # Create the daemon
    daemon = Daemon(config_dir, enable_dbus=DBUS_AVAILABLE, log_dir=log_dir)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: Any) -> None:
        print(f"Received signal {signum}, shutting down...")
        # Log daemon stop
        from sage.telemetry import EventType, log_event

        log_event(EventType.DAEMON_STOP, properties={"signal": signum})
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the daemon
    daemon.start()

    # If DBus is available, run the main loop with DBus methods
    if daemon.enable_dbus:
        # Define the DBus service methods dynamically
        class DBusService(dbus.service.Object):  # type: ignore[misc]
            def __init__(self, daemon_instance: Daemon) -> None:
                self._daemon = daemon_instance
                bus_name = dbus.service.BusName(self._daemon.BUS_NAME, bus=dbus.SessionBus())
                dbus.service.Object.__init__(self, bus_name, self._daemon.OBJECT_PATH)

            @dbus.service.method(  # type: ignore[misc]
                "org.shortcutsage.Daemon",
                in_signature="s",
                out_signature="",
            )
            def SendEvent(self, event_json: str) -> None:  # noqa: N802 - DBus API requires capitalized method names
                """DBus method to send an event."""
                self._daemon.send_event(event_json)

            @dbus.service.method(  # type: ignore[misc]
                "org.shortcutsage.Daemon",
                in_signature="",
                out_signature="s",
            )
            def Ping(self) -> str:  # noqa: N802 - DBus API requires capitalized method names
                """DBus method to ping."""
                return self._daemon.ping()

            @dbus.service.signal(  # type: ignore[misc]
                "org.shortcutsage.Daemon",
                signature="s",
            )
            def Suggestions(self, suggestions_json: str) -> None:  # noqa: N802 - DBus API requires capitalized method names
                """DBus signal for suggestions."""
                pass

        # Create the DBus service with daemon instance
        # Keep reference to prevent garbage collection
        dbus_service = DBusService(daemon)  # noqa: F841 - Must keep in scope for DBus service to remain active

        try:
            loop = GLib.MainLoop()
            loop.run()
        except KeyboardInterrupt:
            print("Interrupted, shutting down...")
            # Log daemon stop
            from sage.telemetry import EventType, log_event

            log_event(EventType.DAEMON_STOP, properties={"signal": "SIGINT"})
            daemon.stop()
    else:
        # In fallback mode, just keep the process alive
        print("Running in fallback mode (no DBus). Process will exit immediately.")
        print(
            "In a real implementation, you might want to set up a different IPC mechanism or event loop."
        )
