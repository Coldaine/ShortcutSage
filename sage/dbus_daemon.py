"""DBus daemon for Shortcut Sage (with fallback for systems without DBus)."""

from __future__ import annotations

import json
import logging
import signal
import sys
import threading
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
    from dbus.mainloop.glib import DBusGMainLoop, threads_init
    from gi.repository import GLib  # type: ignore[import-not-found]

    threads_init()
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
        self._dbus_loop: GLib.MainLoop | None = None
        self._dbus_thread: threading.Thread | None = None
        self._dbus_service: dbus.service.Object | None = None

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
        logger.debug("DBus service metadata initialized")

    def _buffer_snapshot(self) -> list[dict[str, Any]]:
        """Return the ring buffer contents as JSON-serializable dictionaries."""
        snapshot: list[dict[str, Any]] = []
        for event in self.buffer.recent():
            snapshot.append(
                {
                    "action": event.action,
                    "type": event.type,
                    "timestamp": event.timestamp.isoformat(),
                    "metadata": dict(event.metadata or {}),
                }
            )
        return snapshot

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

    def send_event(self, event_json: str) -> str:
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
            suggestions_json = self.emit_suggestions(suggestions)

            logger.debug(f"Processed event: {event.action}")

            return suggestions_json

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
            raise

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
            self._start_dbus_loop()
            logger.info(f"Daemon started on {self.BUS_NAME}")
        else:
            logger.info("Daemon started (fallback mode)")

    def stop(self) -> None:
        """Stop the daemon."""
        if self.enable_dbus and self._dbus_loop is not None:
            self._dbus_loop.quit()
            if self._dbus_thread:
                self._dbus_thread.join(timeout=5.0)
            self._dbus_loop = None
            self._dbus_thread = None
            self._dbus_service = None
        self.watcher.stop()
        logger.info("Daemon stopped")

    def _start_dbus_loop(self) -> None:
        """Start the GLib main loop in a background thread for DBus."""
        if not self.enable_dbus:
            return

        if self._dbus_thread is not None:
            return

        ready = threading.Event()
        daemon = self

        def _loop() -> None:
            try:
                DBusGMainLoop(set_as_default=True)

                class DBusService(dbus.service.Object):  # type: ignore[misc]
                    """DBus wrapper exposing daemon methods and signals."""

                    def __init__(self) -> None:
                        bus_name = dbus.service.BusName(daemon.BUS_NAME, bus=dbus.SessionBus())
                        super().__init__(bus_name, daemon.OBJECT_PATH)

                    @dbus.service.method(  # type: ignore[misc]
                        "org.shortcutsage.Daemon",
                        in_signature="s",
                        out_signature="",
                    )
                    def SendEvent(self, event_json: str) -> None:  # noqa: N802 - DBus convention
                        """DBus method to send an event."""
                        logger.info("DBus SendEvent invoked")
                        suggestions_json = daemon.send_event(event_json)
                        if suggestions_json:
                            self.Suggestions(suggestions_json)

                    @dbus.service.method(  # type: ignore[misc]
                        "org.shortcutsage.Daemon",
                        in_signature="",
                        out_signature="s",
                    )
                    def Ping(self) -> str:  # noqa: N802 - DBus convention
                        """DBus method to ping."""
                        logger.info("DBus Ping invoked")
                        result = daemon.ping()
                        logger.info("DBus Ping returning %s", result)
                        return dbus.String(result)

                    @dbus.service.signal(  # type: ignore[misc]
                        "org.shortcutsage.Daemon",
                        signature="s",
                    )
                    def Suggestions(self, suggestions_json: str) -> None:  # noqa: N802 - DBus convention
                        """Suggestions signal fired after each processed event."""
                        return None

                    @dbus.service.method(  # type: ignore[misc]
                        "org.shortcutsage.Daemon",
                        in_signature="",
                        out_signature="aa{sv}",
                    )
                    def GetBufferState(self) -> dbus.Array:  # noqa: N802 - DBus convention
                        """Return the current buffer contents for debugging/tests."""
                        payload = dbus.Array(signature="a{sv}")
                        for event_dict in daemon._buffer_snapshot():
                            entry = dbus.Dictionary(signature="sv")
                            for key, value in event_dict.items():
                                if isinstance(value, dict):
                                    entry[key] = dbus.Dictionary(value, signature="sv")
                                else:
                                    entry[key] = value
                            payload.append(entry)
                        return payload

                self._dbus_service = DBusService()
                self._dbus_loop = GLib.MainLoop()
                ready.set()
                self._dbus_loop.run()
            except Exception as exc:
                logger.exception("DBus loop crashed: %s", exc)
                ready.set()
                raise

        self._dbus_thread = threading.Thread(target=_loop, daemon=True)
        self._dbus_thread.start()
        ready.wait(timeout=2.0)


def run_daemon(
    config_dir: str,
    log_dir: str | None = None,
    *,
    enable_dbus: bool | None = None,
    log_events: bool = True,
) -> None:
    """Run the daemon with the provided configuration."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    effective_dbus = DBUS_AVAILABLE if enable_dbus is None else enable_dbus

    daemon = Daemon(config_dir, enable_dbus=effective_dbus, log_events=log_events, log_dir=log_dir)

    def _signal_handler(signum: int, frame: Any) -> None:
        logger.info("Received signal %s, shutting down daemon", signum)
        log_event(EventType.DAEMON_STOP, properties={"signal": signum})
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    daemon.start()

    logger.info(
        "Daemon running (%s). Press Ctrl+C to stop.",
        "DBus" if daemon.enable_dbus else "fallback",
    )
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down daemon")
        log_event(EventType.DAEMON_STOP, properties={"signal": "SIGINT"})
        daemon.stop()


def main() -> None:
    """Legacy CLI entry point for direct module execution."""
    if len(sys.argv) not in [2, 3]:
        print("Usage: python -m sage.dbus_daemon <config_dir> [log_dir]")
        sys.exit(1)

    config_dir = sys.argv[1]
    log_dir = sys.argv[2] if len(sys.argv) > 2 else None
    run_daemon(config_dir, log_dir)
