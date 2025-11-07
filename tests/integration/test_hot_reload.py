"""Integration tests for config hot-reload."""

import time
from pathlib import Path
from threading import Event

from sage.watcher import ConfigWatcher


class TestConfigWatcher:
    """Test ConfigWatcher hot-reload functionality."""

    def test_watcher_starts_and_stops(self, tmp_config_dir: Path) -> None:
        """Test that watcher can start and stop."""
        callback_called = Event()

        def callback(filename: str) -> None:
            callback_called.set()

        watcher = ConfigWatcher(tmp_config_dir, callback)
        watcher.start()

        assert watcher.observer is not None
        assert watcher.observer.is_alive()

        watcher.stop()
        assert watcher.observer is None

    def test_watcher_context_manager(self, tmp_config_dir: Path) -> None:
        """Test watcher as context manager."""
        callback_called = Event()

        def callback(filename: str) -> None:
            callback_called.set()

        with ConfigWatcher(tmp_config_dir, callback) as watcher:
            assert watcher.observer is not None
            assert watcher.observer.is_alive()

        # After context exit, observer should be stopped
        assert watcher.observer is None

    def test_callback_triggered_on_file_modification(
        self, tmp_config_dir: Path
    ) -> None:
        """Test that callback is triggered when config file is modified."""
        modified_file = None
        callback_called = Event()

        def callback(filename: str) -> None:
            nonlocal modified_file
            modified_file = filename
            callback_called.set()

        # Create a config file
        test_file = tmp_config_dir / "test.yaml"
        test_file.write_text("initial: content\n")

        with ConfigWatcher(tmp_config_dir, callback):
            # Modify the file
            time.sleep(0.1)  # Give watcher time to initialize
            test_file.write_text("modified: content\n")

            # Wait for callback (with timeout)
            assert callback_called.wait(timeout=2.0), "Callback was not triggered"
            assert modified_file == "test.yaml"

    def test_callback_ignores_non_yaml_files(self, tmp_config_dir: Path) -> None:
        """Test that callback ignores non-YAML files."""
        callback_called = Event()

        def callback(filename: str) -> None:
            callback_called.set()

        # Create a non-YAML file
        test_file = tmp_config_dir / "test.txt"
        test_file.write_text("initial content")

        with ConfigWatcher(tmp_config_dir, callback):
            time.sleep(0.1)
            test_file.write_text("modified content")

            # Callback should not be triggered
            assert not callback_called.wait(timeout=0.5), "Callback was triggered for non-YAML file"

    def test_callback_handles_yml_extension(self, tmp_config_dir: Path) -> None:
        """Test that callback handles .yml extension."""
        modified_file = None
        callback_called = Event()

        def callback(filename: str) -> None:
            nonlocal modified_file
            modified_file = filename
            callback_called.set()

        # Create a .yml file
        test_file = tmp_config_dir / "test.yml"
        test_file.write_text("initial: content\n")

        with ConfigWatcher(tmp_config_dir, callback):
            time.sleep(0.1)
            test_file.write_text("modified: content\n")

            assert callback_called.wait(timeout=2.0), "Callback was not triggered"
            assert modified_file == "test.yml"

    def test_callback_error_handling(self, tmp_config_dir: Path, caplog) -> None:  # type: ignore
        """Test that callback errors are logged but don't crash watcher."""
        callback_called = Event()

        def callback(filename: str) -> None:
            callback_called.set()
            raise ValueError("Test error")

        test_file = tmp_config_dir / "test.yaml"
        test_file.write_text("initial: content\n")

        with ConfigWatcher(tmp_config_dir, callback):
            time.sleep(0.1)
            test_file.write_text("modified: content\n")

            # Callback should be called despite error
            assert callback_called.wait(timeout=2.0), "Callback was not triggered"

            # Error should be logged
            time.sleep(0.1)  # Give time for logging
            assert "Error in config reload callback" in caplog.text
