"""PySide6 overlay for Shortcut Sage suggestions."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

logger = logging.getLogger(__name__)

# Try to import DBus, but allow fallback if not available
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop

    DBUS_AVAILABLE = True
    logger.info("DBus support available for overlay")
except ImportError:
    DBUS_AVAILABLE = False
    logger.info("DBus support not available for overlay")


class SuggestionChip(QWidget):
    """A chip displaying a single shortcut suggestion."""

    def __init__(self, key: str, description: str, priority: int):
        super().__init__()

        self.key = key
        self.description = description
        self.priority = priority

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the UI for the chip."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Key label (the actual shortcut)
        self.key_label = QLabel(self.key)
        key_font = QFont()
        key_font.setBold(True)
        key_font.setPointSize(12)
        self.key_label.setFont(key_font)
        self.key_label.setStyleSheet("color: #4CAF50;")

        # Description label
        self.desc_label = QLabel(self.description)
        desc_font = QFont()
        desc_font.setPointSize(10)
        self.desc_label.setFont(desc_font)
        self.desc_label.setStyleSheet("color: white;")
        self.desc_label.setWordWrap(True)

        layout.addWidget(self.key_label)
        layout.addWidget(self.desc_label)

        # Styling
        self.setStyleSheet(
            """
            QWidget {
                background-color: rgba(30, 30, 30, 0.9);
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px;
            }
            """
        )


class OverlayWindow(QWidget):
    """Main overlay window that displays shortcut suggestions."""

    def __init__(self, dbus_available: bool = True) -> None:
        super().__init__()

        self.dbus_available = dbus_available and DBUS_AVAILABLE
        self.dbus_interface = None

        self.setup_window()
        self.setup_ui()
        self.connect_dbus()

        logger.info(f"Overlay initialized (DBus: {self.dbus_available})")

    def setup_window(self) -> None:
        """Configure window properties for overlay."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Position at top-left corner
        self.setGeometry(20, 20, 300, 120)

    def setup_ui(self) -> None:
        """Set up the UI elements."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)

        # Initially empty - suggestions will be added dynamically
        self.chips: list[SuggestionChip] = []

        # Styling
        self.setStyleSheet("background-color: transparent;")

    def connect_dbus(self) -> None:
        """Connect to DBus if available."""
        if not self.dbus_available:
            logger.info("Running overlay in fallback mode (no DBus)")
            return

        try:
            DBusGMainLoop(set_as_default=True)

            bus = dbus.SessionBus()
            self.dbus_interface = bus.get_object(
                "org.shortcutsage.Daemon", "/org/shortcutsage/Daemon"
            )

            # Connect to the suggestions signal
            bus.add_signal_receiver(
                self.on_suggestions,
                signal_name="Suggestions",
                dbus_interface="org.shortcutsage.Daemon",
                path="/org/shortcutsage/Daemon",
            )

            logger.info("Connected to Shortcut Sage daemon via DBus")

        except Exception as e:
            logger.error(f"Failed to connect to DBus: {e}")
            self.dbus_available = False

    def on_suggestions(self, suggestions_json: str) -> None:
        """Handle incoming suggestions from DBus."""
        try:
            suggestions = json.loads(suggestions_json)
            self.update_suggestions(suggestions)
        except Exception as e:
            logger.error(f"Error processing suggestions: {e}")

    def update_suggestions(self, suggestions: list[dict[str, Any]]) -> None:
        """Update the UI with new suggestions."""
        # Clear existing chips
        for chip in self.chips:
            chip.setParent(None)  # Remove from parent but don't delete immediately
            chip.deleteLater()

        self.chips.clear()

        # Create new chips for suggestions
        for suggestion in suggestions[:3]:  # Limit to 3 suggestions
            chip = SuggestionChip(
                key=suggestion["key"],
                description=suggestion["description"],
                priority=suggestion["priority"],
            )
            layout = self.layout()
            if layout:
                layout.addWidget(chip)
            self.chips.append(chip)

        # Adjust size to fit content
        self.adjustSize()

    def set_suggestions_fallback(self, suggestions: list[dict[str, Any]]) -> None:
        """Update suggestions when not using DBus (for testing)."""
        self.update_suggestions(suggestions)

    def fade_in(self) -> None:
        """Apply fade-in animation."""
        self.setWindowOpacity(0.0)  # Start transparent

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_animation.start()

    def fade_out(self) -> None:
        """Apply fade-out animation."""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_animation.finished.connect(self.hide)


DEMO_SUGGESTIONS = [
    {
        "action": "overview",
        "key": "Meta+Tab",
        "description": "Show application overview",
        "priority": 80,
    },
    {
        "action": "tile_left",
        "key": "Meta+Left",
        "description": "Tile window to left half",
        "priority": 60,
    },
]


def run_overlay(*, enable_dbus: bool = True, demo: bool = False) -> int:
    """Launch the overlay UI."""
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("ShortcutSageOverlay")
    app.setQuitOnLastWindowClosed(False)  # type: ignore[attr-defined]

    overlay = OverlayWindow(dbus_available=enable_dbus)
    overlay.show()

    if demo:
        overlay.set_suggestions_fallback(DEMO_SUGGESTIONS)

    return app.exec()


def main() -> None:
    """Legacy CLI entry point for running directly."""
    demo = "--demo" in sys.argv
    sys.exit(run_overlay(enable_dbus=DBUS_AVAILABLE, demo=demo))


if __name__ == "__main__":
    main()
