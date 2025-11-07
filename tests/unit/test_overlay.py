"""Test the overlay functionality."""

import json

import pytest
from PySide6.QtWidgets import QApplication

from sage.overlay import OverlayWindow, SuggestionChip


class TestSuggestionChip:
    """Test SuggestionChip class."""

    @pytest.fixture(autouse=True)
    def setup_qapp(self):
        """Set up QApplication before tests."""
        if not QApplication.instance():
            self.app = QApplication([])

    def test_chip_creation(self):
        """Test creating a suggestion chip."""
        # Create a chip
        chip = SuggestionChip("Ctrl+C", "Copy", 80)

        assert chip.key == "Ctrl+C"
        assert chip.description == "Copy"
        assert chip.priority == 80


class TestOverlayWindow:
    """Test OverlayWindow class."""

    @pytest.fixture(autouse=True)
    def setup_qapp(self):
        """Set up QApplication before tests."""
        if not QApplication.instance():
            self.app = QApplication([])

    def test_overlay_initialization(self):
        """Test overlay initialization."""
        # Create overlay in fallback mode
        overlay = OverlayWindow(dbus_available=False)

        assert overlay is not None
        assert not overlay.dbus_available

    def test_update_suggestions(self):
        """Test updating suggestions."""
        overlay = OverlayWindow(dbus_available=False)

        suggestions = [
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

        overlay.set_suggestions_fallback(suggestions)

        # Check that chips were created
        assert len(overlay.chips) == 2
        assert overlay.chips[0].key == "Meta+Tab"
        assert overlay.chips[1].description == "Tile window to left half"

    def test_on_suggestions_json(self):
        """Test processing suggestions from JSON."""
        overlay = OverlayWindow(dbus_available=False)

        suggestions_json = json.dumps(
            [
                {
                    "action": "test_action",
                    "key": "Ctrl+T",
                    "description": "Test shortcut",
                    "priority": 75,
                }
            ]
        )

        overlay.on_suggestions(suggestions_json)

        assert len(overlay.chips) == 1
        assert overlay.chips[0].key == "Ctrl+T"
