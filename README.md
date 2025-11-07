# Shortcut Sage

> Context-aware keyboard shortcut suggestions for KDE Plasma (Wayland)

[![CI](https://github.com/Coldaine/ShortcutSage/actions/workflows/ci.yml/badge.svg)](https://github.com/Coldaine/ShortcutSage/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Shortcut Sage** is a lightweight, privacy-first desktop tool that watches your workflow and suggests relevant keyboard shortcuts at the perfect moment. Think of it as "autocomplete for your hands."

## Features

- **Context-aware suggestions**: Suggests up to 3 shortcuts based on your recent actions
- **Privacy by design**: Only symbolic events (no keylogging), all local processing
- **Config-driven**: Rules defined in YAML, not hard-coded
- **Minimal UI**: Small always-on-top overlay, top-left corner
- **KDE Plasma integration**: Native KWin script for event monitoring

## Architecture

```
KWin Script → DBus → Daemon (rules engine) → DBus → Overlay UI
```

- **KWin Event Monitor**: JavaScript script that captures desktop events
- **Daemon**: Python service that matches contexts to suggestions
- **Overlay**: PySide6 window displaying suggestions

## Requirements

- **OS**: Linux with KDE Plasma (Wayland) 5.27+
- **Python**: 3.11 or higher
- **Dependencies**: DBus, PySide6, Pydantic

## Installation

### Development Setup

```bash
# Clone repository
git clone https://github.com/Coldaine/ShortcutSage.git
cd ShortcutSage

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Install KWin script
bash scripts/install-kwin-script.sh
```

### Configuration

Create your config files in `~/.config/shortcut-sage/`:

**shortcuts.yaml**: Define your shortcuts
```yaml
version: "1.0"
shortcuts:
  - key: "Meta+D"
    action: "show_desktop"
    description: "Show desktop"
    category: "desktop"
```

**rules.yaml**: Define context-based suggestion rules
```yaml
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
```

## Usage

```bash
# Start the daemon
shortcut-sage daemon

# Start the overlay (in another terminal)
shortcut-sage overlay

# Test event (Meta+Shift+S in KDE)
# Should trigger test event
```

## Development

### Running Tests

```bash
# All tests with coverage
pytest

# Unit tests only
pytest tests/unit

# Integration tests
pytest tests/integration

# End-to-end tests (requires KDE)
pytest tests/e2e
```

### Code Quality

```bash
# Lint
ruff check sage tests

# Format
ruff format sage tests

# Type check
mypy sage
```

## Project Status

Currently implementing **MVP (PR-00 through PR-06)**:

- ✅ PR-00: Repository & CI Bootstrap
- 🚧 PR-01: Config & Schemas
- ⏳ PR-02: Engine Core
- ⏳ PR-03: DBus IPC
- ⏳ PR-04: KWin Event Monitor
- ⏳ PR-05: Overlay UI
- ⏳ PR-06: End-to-End Demo

See [implementation-plan.md](implementation-plan.md) for full roadmap.

## Documentation

- [Product Bible](shortcut-sage-bible.md): Vision, principles, and architecture
- [Implementation Plan](implementation-plan.md): Phased development plan
- [Agent Prompt](agent-prompt-pr-train.md): Instructions for autonomous development

## Privacy & Security

- **No keylogging**: Only symbolic events (window focus, desktop switch)
- **Local processing**: No cloud, no telemetry
- **Redacted by default**: Window titles not logged
- **Open source**: Audit the code yourself

## Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [PySide6](https://wiki.qt.io/Qt_for_Python) - UI framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [pytest](https://pytest.org/) - Testing framework
- [ruff](https://github.com/astral-sh/ruff) - Linting & formatting

---

**Status**: 🚧 Alpha - Active Development

For questions or issues, please open an issue on GitHub.
