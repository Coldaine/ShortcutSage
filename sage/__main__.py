"""Shortcut Sage CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sage.dbus_daemon import DBUS_AVAILABLE, run_daemon
from sage.overlay import run_overlay

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "shortcut-sage"


def _expand_path(path: str | None, *, default: Path | None = None) -> str:
    """Expand user/relative paths, falling back to default when empty."""
    if path:
        return str(Path(path).expanduser())
    if default is not None:
        return str(default.expanduser())
    raise ValueError("Path cannot be determined")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="shortcut-sage",
        description="Shortcut Sage daemon and overlay controller",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    daemon_parser = subparsers.add_parser("daemon", help="Start the Shortcut Sage daemon")
    daemon_parser.add_argument(
        "--config",
        metavar="DIR",
        default=None,
        help=f"Configuration directory (default: {DEFAULT_CONFIG_DIR})",
    )
    daemon_parser.add_argument(
        "--log-dir",
        metavar="DIR",
        default=None,
        help="Directory for daemon logs (default: ~/.local/share/shortcut-sage/logs)",
    )
    daemon_parser.add_argument(
        "--no-dbus",
        action="store_true",
        help="Disable DBus integration (fallback mode, useful on non-Linux dev machines)",
    )

    overlay_parser = subparsers.add_parser("overlay", help="Launch the overlay UI")
    overlay_parser.add_argument(
        "--demo",
        action="store_true",
        help="Populate overlay with demo suggestions instead of waiting for DBus events",
    )
    overlay_parser.add_argument(
        "--no-dbus",
        action="store_true",
        help="Disable DBus listener and rely solely on demo/fallback suggestions",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint callable from console_scripts."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "daemon":
        config_path = Path(_expand_path(args.config, default=DEFAULT_CONFIG_DIR))
        if not config_path.exists():
            parser.error(f"Config directory not found: {config_path}")
        log_dir = Path(args.log_dir).expanduser() if args.log_dir else None
        run_daemon(
            str(config_path),
            str(log_dir) if log_dir else None,
            enable_dbus=not args.no_dbus,
        )
    elif args.command == "overlay":
        enable_dbus = DBUS_AVAILABLE and not args.no_dbus
        if not DBUS_AVAILABLE and not args.no_dbus:
            print("DBus bindings not available; starting overlay in fallback mode.", file=sys.stderr)
        exit_code = run_overlay(enable_dbus=enable_dbus, demo=args.demo)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
