"""Dev audit batch processing for Shortcut Sage telemetry."""

import json
import logging
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditReport:
    """Structure for audit report results."""
    timestamp: datetime
    summary: dict[str, Any]
    suggestions: list[str]
    issues: list[str]


class TelemetryBatchProcessor:
    """Process telemetry data from NDJSON files in batch."""

    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)

    def read_telemetry_files(self) -> Iterator[dict[str, Any]]:
        """Read all telemetry entries from NDJSON files."""
        # Look for current and rotated log files
        for log_path in self.log_dir.glob("telemetry*.ndjson"):
            with open(log_path, encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in {log_path}:{line_num}: {e}")
                            continue

    def generate_report(self) -> AuditReport:
        """Generate an audit report from telemetry data."""
        events = list(self.read_telemetry_files())

        if not events:
            return AuditReport(
                timestamp=datetime.now(),
                summary={"total_events": 0},
                suggestions=[],
                issues=["No telemetry data found"]
            )

        # Calculate metrics
        total_events = len(events)

        # Count event types
        event_counts = defaultdict(int)
        durations = defaultdict(list)

        for event in events:
            event_type = event.get('event_type', 'unknown')
            event_counts[event_type] += 1

            duration = event.get('duration')
            if duration is not None:
                durations[event_type].append(duration)

        # Calculate average durations
        avg_durations = {}
        for event_type, duration_list in durations.items():
            if duration_list:
                avg_durations[event_type] = sum(duration_list) / len(duration_list)

        # Identify potential issues
        issues = []
        suggestions = []

        # Check for error frequency
        error_count = event_counts.get('error_occurred', 0)
        if error_count > 0:
            error_rate = error_count / total_events
            if error_rate > 0.05:  # More than 5% errors
                issues.append(f"High error rate: {error_rate:.2%} ({error_count}/{total_events})")

        # Check for performance issues
        slow_processing_threshold = 1.0  # 1 second
        slow_events = [(et, avg) for et, avg in avg_durations.items()
                      if avg > slow_processing_threshold]
        for event_type, avg_duration in slow_events:
            issues.append(f"Slow {event_type}: avg {avg_duration:.2f}s")
            suggestions.append(f"Optimize {event_type} processing")

        # Check for suggestion acceptance patterns
        suggestion_count = event_counts.get('suggestion_shown', 0)
        if suggestion_count > 0:
            # If we had suggestions, recommend reviewing them
            suggestions.append(f"Review {suggestion_count} shown suggestions for relevance")

        # Summary data
        summary = {
            "total_events": total_events,
            "event_type_counts": dict(event_counts),
            "average_durations": {k: round(v, 3) for k, v in avg_durations.items()},
            "time_range": self._get_time_range(events),
            "error_count": error_count
        }

        return AuditReport(
            timestamp=datetime.now(),
            summary=summary,
            suggestions=suggestions,
            issues=issues
        )

    def _get_time_range(self, events: list[dict[str, Any]]) -> dict[str, str]:
        """Get the time range of the events."""
        timestamps = []
        for event in events:
            ts_str = event.get('timestamp')
            if ts_str:
                try:
                    timestamps.append(datetime.fromisoformat(ts_str.replace('Z', '+00:00')))
                except ValueError:
                    continue

        if not timestamps:
            return {}

        start_time = min(timestamps)
        end_time = max(timestamps)

        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration_hours": (end_time - start_time).total_seconds() / 3600
        }

    def generate_dev_report(self) -> str:
        """Generate a developer-focused audit report."""
        report = self.generate_report()

        output_lines = [
            "Shortcut Sage - Dev Audit Report",
            f"Generated: {report.timestamp.isoformat()}",
            "",
            "Summary:",
            f"  Total Events: {report.summary['total_events']}",
        ]

        if 'time_range' in report.summary and report.summary['time_range']:
            time_range = report.summary['time_range']
            output_lines.append(f"  Time Range: {time_range['start']} to {time_range['end']}")
            output_lines.append(f"  Duration: {time_range.get('duration_hours', 0):.2f} hours")

        output_lines.append(f"  Error Count: {report.summary['error_count']}")

        # Event type breakdown
        output_lines.append("")
        output_lines.append("Event Type Counts:")
        for event_type, count in sorted(report.summary['event_type_counts'].items()):
            output_lines.append(f"  {event_type}: {count}")

        # Average durations
        if report.summary['average_durations']:
            output_lines.append("")
            output_lines.append("Average Durations:")
            for event_type, avg_duration in sorted(report.summary['average_durations'].items()):
                output_lines.append(f"  {event_type}: {avg_duration:.3f}s")

        # Issues
        if report.issues:
            output_lines.append("")
            output_lines.append("Issues Found:")
            for issue in report.issues:
                output_lines.append(f"  - {issue}")

        # Suggestions
        if report.suggestions:
            output_lines.append("")
            output_lines.append("Suggestions:")
            for suggestion in report.suggestions:
                output_lines.append(f"  - {suggestion}")

        output_lines.append("")
        output_lines.append("End of Report")

        return "\n".join(output_lines)


def main():
    """Main entry point for the dev audit batch processor."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: dev-audit <log_directory>")
        sys.exit(1)

    log_dir = Path(sys.argv[1])

    if not log_dir.exists():
        print(f"Error: Log directory does not exist: {log_dir}")
        sys.exit(1)

    print(f"Processing telemetry from: {log_dir}")

    processor = TelemetryBatchProcessor(log_dir)
    report_text = processor.generate_dev_report()

    print(report_text)


if __name__ == "__main__":
    main()
