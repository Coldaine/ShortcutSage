"""Developer hints and debugging panel for Shortcut Sage."""

import sys
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from sage.telemetry import get_telemetry


class DevHintsPanel(QWidget):
    """Developer debugging panel showing internal state and hints."""
    
    def __init__(self):
        super().__init__()
        
        self.telemetry = get_telemetry()
        self.setup_ui()
        self.setup_refresh_timer()
    
    def setup_ui(self):
        """Set up the UI for the dev hints panel."""
        self.setWindowTitle("Shortcut Sage - Dev Hints Panel")
        self.setGeometry(100, 100, 800, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Shortcut Sage - Developer Hints & Debug Info")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Stats section
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        main_layout.addWidget(QLabel("Runtime Statistics:"))
        main_layout.addWidget(self.stats_text)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(divider)
        
        # Suggestions trace
        self.suggestions_trace = QTextEdit()
        self.suggestions_trace.setMaximumHeight(150)
        self.suggestions_trace.setReadOnly(True)
        main_layout.addWidget(QLabel("Recent Suggestions Trace:"))
        main_layout.addWidget(self.suggestions_trace)
        
        # Divider
        main_layout.addWidget(divider)
        
        # Event trace
        self.events_trace = QTextEdit()
        self.events_trace.setReadOnly(True)
        main_layout.addWidget(QLabel("Recent Events Trace:"))
        
        # Scroll area for event trace
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.events_trace)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        self.clear_btn = QPushButton("Clear Traces")
        self.clear_btn.clicked.connect(self.clear_traces)
        
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
    
    def setup_refresh_timer(self):
        """Set up automatic refresh timer."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds
    
    def refresh_data(self):
        """Refresh all displayed data."""
        self.update_stats()
        self.update_traces()
    
    def update_stats(self):
        """Update the statistics display."""
        if self.telemetry:
            metrics = self.telemetry.export_metrics()
            
            stats_text = f"""Runtime Statistics:
Uptime: {metrics.get('uptime', 0):.1f}s
Total Events Processed: {metrics['counters'].get('event_received', 0)}
Suggestions Shown: {metrics['counters'].get('suggestion_shown', 0)}
Suggestions Accepted: {metrics['counters'].get('suggestion_accepted', 0)}
Errors: {metrics['counters'].get('error_occurred', 0)}

Performance:
Event Processing Time: {metrics['histograms'].get('event_received', {}).get('avg', 0):.3f}s avg
Last 10 Events: {len(self.telemetry.events)}"""
            
            self.stats_text.setPlainText(stats_text)
        else:
            self.stats_text.setPlainText("Telemetry not initialized - start the daemon first")
    
    def update_traces(self):
        """Update the trace displays."""
        if self.telemetry:
            # Get recent events
            recent_events = list(self.telemetry.events)[-20:]  # Last 20 events
            
            # Format events
            event_lines = []
            suggestion_lines = []
            
            for event in recent_events:
                timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]  # Show ms
                event_line = f"[{timestamp}] {event.event_type.value}"
                
                if event.duration:
                    event_line += f" (took {event.duration:.3f}s)"
                
                if event.properties:
                    event_line += f" - {event.properties}"
                
                event_lines.append(event_line)
                
                # Extract suggestion info
                if event.event_type.value == 'suggestion_shown' and event.properties:
                    suggestion_lines.append(
                        f"[{timestamp}] SUGGESTION: {event.properties.get('action', 'N/A')} "
                        f"({event.properties.get('key', 'N/A')}) priority={event.properties.get('priority', 'N/A')}"
                    )
            
            # Update text areas
            self.events_trace.setPlainText("\n".join(reversed(event_lines)))
            self.suggestions_trace.setPlainText("\n".join(reversed(suggestion_lines[-10:])))  # Last 10 suggestions
        else:
            self.events_trace.setPlainText("No telemetry data available")
            self.suggestions_trace.setPlainText("No suggestion data available")
    
    def clear_traces(self):
        """Clear all trace information."""
        if self.telemetry:
            self.telemetry.events.clear()
        self.events_trace.clear()
        self.suggestions_trace.clear()


def show_dev_hints():
    """Show the developer hints panel."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    panel = DevHintsPanel()
    panel.show()
    
    return app, panel


def main():
    """Main entry point for dev hints panel."""
    app = QApplication(sys.argv)
    
    panel = DevHintsPanel()
    panel.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()