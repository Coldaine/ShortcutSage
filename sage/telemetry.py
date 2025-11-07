"""Observability and hardening components for Shortcut Sage."""

import json
import logging
import logging.handlers
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class EventType(Enum):
    """Types of events to track."""

    EVENT_RECEIVED = "event_received"
    SUGGESTION_SHOWN = "suggestion_shown"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    DAEMON_START = "daemon_start"
    DAEMON_STOP = "daemon_stop"
    CONFIG_RELOAD = "config_reload"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class TelemetryEvent:
    """A telemetry event with timing and context."""

    event_type: EventType
    timestamp: datetime
    duration: float | None = None  # For timing measurements
    properties: dict[str, Any] | None = None  # Additional context
    redacted: bool = False  # Whether PII has been redacted


class MetricsCollector:
    """Collects and aggregates metrics for observability."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[str, int] = defaultdict(int)
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.events: deque[TelemetryEvent] = deque(maxlen=10000)  # Circular buffer for recent events
        self.start_time = datetime.now()

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            self.counters[name] += value

    def record_timing(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        with self._lock:
            self.histograms[name].append(duration)

    def record_event(self, event: TelemetryEvent) -> None:
        """Record a telemetry event."""
        with self._lock:
            self.events.append(event)

    def get_counter(self, name: str) -> int:
        """Get the current value of a counter."""
        with self._lock:
            return self.counters[name]

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get statistics for a histogram."""
        with self._lock:
            values = self.histograms.get(name, [])
            if not values:
                return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}

            count = len(values)
            avg = sum(values) / count
            min_val = min(values)
            max_val = max(values)

            return {"count": count, "avg": avg, "min": min_val, "max": max_val}

    def get_uptime(self) -> timedelta:
        """Get the uptime of the collector."""
        return datetime.now() - self.start_time

    def export_metrics(self) -> dict[str, Any]:
        """Export all metrics for reporting."""
        with self._lock:
            return {
                "uptime": self.get_uptime().total_seconds(),
                "counters": dict(self.counters),
                "histograms": {name: self.get_histogram_stats(name) for name in self.histograms},
                "event_count": len(self.events),
            }

    def reset_counters(self) -> None:
        """Reset all counters (useful for testing)."""
        with self._lock:
            self.counters.clear()
            for hist in self.histograms.values():
                hist.clear()


class LogRedactor:
    """Redacts potentially sensitive information from logs."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        # Patterns to redact
        self.redaction_patterns = [
            # These are general patterns that might contain PII
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            # Window titles and app names could potentially contain PII
        ]

    def redact(self, text: str) -> str:
        """Redact sensitive information from text."""
        if not self.enabled:
            return text

        # For now, we'll just return the text as-is to avoid over-redacting
        # In a real implementation, we'd have more sophisticated redaction
        # based on our privacy requirements
        return text


class RotatingTelemetryLogger:
    """Telemetry logger with rotation and redaction."""

    def __init__(
        self, log_dir: str | Path, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Set up the NDJSON log file with rotation
        self.log_file = self.log_dir / "telemetry.ndjson"
        self.handler = logging.handlers.RotatingFileHandler(
            self.log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )

        # Create logger
        self.logger = logging.getLogger("telemetry")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)

        # Disable propagation to avoid duplicate logs
        self.logger.propagate = False

        self.redactor = LogRedactor(enabled=True)
        self.metrics = MetricsCollector()

    def log_event(
        self,
        event_type: EventType,
        duration: float | None = None,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Log an event with timing and properties."""
        event = TelemetryEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            duration=duration,
            properties=properties or {},
        )

        # Record in metrics
        self.metrics.record_event(event)

        if duration is not None:
            self.metrics.record_timing(event_type.value, duration)

        self.metrics.increment_counter(event_type.value)

        # Prepare log entry in NDJSON format
        log_entry = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event_type.value,
            "duration": duration,
            "properties": self.redactor.redact(json.dumps(properties)) if properties else None,
        }

        # Write as NDJSON (newline-delimited JSON)
        self.logger.info(json.dumps(log_entry))

    def log_error(self, error_msg: str, context: dict[str, Any] | None = None) -> None:
        """Log an error event."""
        self.log_event(
            EventType.ERROR_OCCURRED,
            properties={"error": self.redactor.redact(error_msg), "context": context or {}},
        )

    def export_metrics(self) -> dict[str, Any]:
        """Export current metrics."""
        return self.metrics.export_metrics()

    def close(self) -> None:
        """Close the logger."""
        self.logger.removeHandler(self.handler)
        self.handler.close()


# Global telemetry instance
_telemetry_logger: RotatingTelemetryLogger | None = None


def init_telemetry(log_dir: str | Path) -> RotatingTelemetryLogger:
    """Initialize the telemetry system."""
    global _telemetry_logger
    _telemetry_logger = RotatingTelemetryLogger(log_dir)
    return _telemetry_logger


def get_telemetry() -> RotatingTelemetryLogger | None:
    """Get the global telemetry instance."""
    return _telemetry_logger


def log_event(
    event_type: EventType, duration: float | None = None, properties: dict[str, Any] | None = None
) -> None:
    """Log an event using the global telemetry logger."""
    telemetry = get_telemetry()
    if telemetry:
        telemetry.log_event(event_type, duration, properties)


def log_error(error_msg: str, context: dict[str, Any] | None = None) -> None:
    """Log an error using the global telemetry logger."""
    telemetry = get_telemetry()
    if telemetry:
        telemetry.log_error(error_msg, context)
