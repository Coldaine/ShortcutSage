"""End-to-end smoke test for daemon → overlay signal flow."""

from __future__ import annotations

import json
import os
from datetime import datetime

from PySide6.QtWidgets import QApplication

from sage.dbus_daemon import Daemon
from sage.overlay import OverlayWindow

# Ensure headless platforms can render the overlay during tests.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_daemon_event_updates_overlay(
    tmp_config_dir,
    sample_shortcuts_yaml,  # noqa: ARG001 - fixtures ensure config exists
    sample_rules_yaml,  # noqa: ARG001
) -> None:
    """Verify that daemon events propagate to the overlay in fallback mode."""
    app = _ensure_app()

    daemon = Daemon(str(tmp_config_dir), enable_dbus=False, log_events=False)
    overlay = OverlayWindow(dbus_available=False)

    received_payload: list[dict[str, int | str]] = []

    def capture_suggestions(suggestions) -> None:
        payload = [
            {
                "action": s.action,
                "key": s.key,
                "description": s.description,
                "priority": s.priority,
            }
            for s in suggestions
        ]
        received_payload.extend(payload)
        overlay.set_suggestions_fallback(payload)

    daemon.set_suggestions_callback(capture_suggestions)

    event_json = json.dumps(
        {
            "timestamp": datetime.now().isoformat(),
            "type": "test",
            "action": "show_desktop",
            "metadata": {},
        }
    )

    daemon.send_event(event_json)

    app.processEvents()

    assert received_payload, "Daemon did not produce any suggestions"
    assert overlay.chips, "Overlay did not render any suggestion chips"
    assert overlay.chips[0].key in {"Meta+Tab", "Meta+Left"}

    overlay.close()
