"""Test the DBus daemon functionality."""

import json
from datetime import datetime

from sage.dbus_daemon import Daemon


class TestDaemon:
    """Test Daemon class."""

    def test_daemon_initialization(self, tmp_path):
        """Test daemon initialization."""
        # Create config files for testing
        shortcuts_file = tmp_path / "shortcuts.yaml"
        rules_file = tmp_path / "rules.yaml"
        
        shortcuts_content = """
version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"
"""
        rules_content = """
version: "1.0"
rules:
  - name: "test_rule"
    context:
      type: "event_sequence"
      pattern: "show_desktop"
      window: 3
    suggest:
      - action: "overview"
        priority: 80
    cooldown: 300
"""
        
        shortcuts_file.write_text(shortcuts_content)
        rules_file.write_text(rules_content)

        # Initialize daemon in fallback mode
        daemon = Daemon(str(tmp_path), enable_dbus=False)
        
        assert daemon is not None
        assert len(daemon.policy_engine.shortcuts) > 0
        assert daemon.enable_dbus is False

    def test_ping_method(self, tmp_path):
        """Test ping method."""
        # Create config files for testing
        shortcuts_file = tmp_path / "shortcuts.yaml"
        rules_file = tmp_path / "rules.yaml"
        
        shortcuts_content = """
version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"
"""
        rules_content = """
version: "1.0"
rules:
  - name: "test_rule"
    context:
      type: "event_sequence"
      pattern: "show_desktop"
      window: 3
    suggest:
      - action: "overview"
        priority: 80
    cooldown: 300
"""
        
        shortcuts_file.write_text(shortcuts_content)
        rules_file.write_text(rules_content)

        # Initialize daemon in fallback mode
        daemon = Daemon(str(tmp_path), enable_dbus=False)
        
        result = daemon.ping()
        assert result == "pong"

    def test_send_event_method(self, tmp_path, caplog):
        """Test send_event method."""
        # Create config files for testing
        shortcuts_file = tmp_path / "shortcuts.yaml"
        rules_file = tmp_path / "rules.yaml"
        
        shortcuts_content = """
version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"
  - key: "Meta+Tab"
    action: "overview"
    description: "Show overview"
    category: "desktop"
"""
        rules_content = """
version: "1.0"
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
        
        shortcuts_file.write_text(shortcuts_content)
        rules_file.write_text(rules_content)

        # Initialize daemon in fallback mode
        daemon = Daemon(str(tmp_path), enable_dbus=False)
        
        # Create a test event
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "type": "test",
            "action": "show_desktop",
            "metadata": {}
        }
        
        event_json = json.dumps(event_data)
        
        # Capture suggestions
        suggestions_captured = []
        def suggestions_callback(suggestions):
            suggestions_captured.extend(suggestions)
        
        daemon.set_suggestions_callback(suggestions_callback)
        
        # Send the event
        daemon.send_event(event_json)
        
        # Check that suggestions were generated 
        assert len(suggestions_captured) > 0
        assert suggestions_captured[0].action == "overview"