"""Configuration file watcher for hot-reload."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """Watches config files for changes and triggers callbacks."""

    def __init__(self, config_dir: Path | str, callback: Callable[[str], None]):
        """
        Initialize config watcher.

        Args:
            config_dir: Directory containing config files to watch
            callback: Function to call when a config file changes (receives filename)
        """
        self.config_dir = Path(config_dir)
        self.callback = callback
        self.observer: Observer | None = None  # type: ignore[valid-type]
        self._handler = _ConfigHandler(self.config_dir, self.callback)

    def start(self) -> None:
        """Start watching for file changes."""
        if self.observer is not None:
            logger.warning("Watcher already started")
            return

        self.observer = Observer()
        self.observer.schedule(self._handler, str(self.config_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started watching config directory: {self.config_dir}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self.observer is None:
            logger.warning("Watcher not started")
            return

        self.observer.stop()
        self.observer.join(timeout=5.0)
        self.observer = None
        logger.info("Stopped watching config directory")

    def __enter__(self) -> "ConfigWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit."""
        self.stop()


class _ConfigHandler(FileSystemEventHandler):
    """Internal handler for config file system events."""

    def __init__(self, config_dir: Path, callback: Callable[[str], None]):
        """
        Initialize handler.

        Args:
            config_dir: Config directory path
            callback: Callback function
        """
        super().__init__()
        self.config_dir = config_dir
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Convert src_path to string if it's bytes
        src_path_str = (
            event.src_path if isinstance(event.src_path, str) else event.src_path.decode("utf-8")
        )

        # Only watch YAML files
        if not src_path_str.endswith((".yaml", ".yml")):
            return

        filename = Path(src_path_str).name
        logger.debug(f"Config file modified: {filename}")

        try:
            self.callback(filename)
        except Exception as e:
            logger.error(f"Error in config reload callback for {filename}: {e}")
