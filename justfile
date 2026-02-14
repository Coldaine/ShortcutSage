# Shortcut Sage Development Commands
# Usage: just <recipe>
# Install just: https://github.com/casey/just

# Default recipe - show help
default:
    @just --list

# ============================================================================
# Setup & Installation
# ============================================================================

# Create virtual environment and install dependencies
setup:
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e ".[dev]"
    @echo "✓ Setup complete. Activate with: source .venv/bin/activate"

# Install without dbus (for environments without libdbus-1-dev)
setup-minimal:
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install pydantic pyyaml PySide6 watchdog
    .venv/bin/pip install pytest pytest-cov pytest-qt ruff mypy types-PyYAML
    .venv/bin/pip install -e . --no-deps
    @echo "✓ Minimal setup complete (no dbus). Activate with: source .venv/bin/activate"

# Install anthropic for Claude validation
setup-claude:
    .venv/bin/pip install anthropic
    @echo "✓ Anthropic SDK installed"

# ============================================================================
# Testing
# ============================================================================

# Run all tests
test:
    .venv/bin/pytest tests/ -v

# Run unit tests only
test-unit:
    .venv/bin/pytest tests/unit/ -v

# Run integration tests only
test-integration:
    .venv/bin/pytest tests/integration/ -v

# Run tests without Qt/DBus (headless compatible)
test-headless:
    .venv/bin/pytest tests/unit/ tests/integration/ \
        --ignore=tests/unit/test_overlay.py \
        --ignore=tests/integration/test_dbus.py \
        -v --no-cov

# Run tests with coverage
test-cov:
    .venv/bin/pytest tests/ --cov=sage --cov-report=html --cov-report=term-missing
    @echo "✓ Coverage report: htmlcov/index.html"

# Run visual tests (requires graphical environment or xvfb)
test-visual:
    .venv/bin/python scripts/visual_test_overlay.py

# Run visual tests under xvfb
test-visual-xvfb:
    xvfb-run -a --server-args="-screen 0 1920x1080x24" \
        .venv/bin/python scripts/visual_test_overlay.py

# Validate screenshots with Claude (requires ANTHROPIC_API_KEY)
validate-screenshots dir="screenshots":
    .venv/bin/python scripts/validate_screenshots.py {{dir}} --output {{dir}}/validation_report.json

# ============================================================================
# Code Quality
# ============================================================================

# Run all lints
lint: lint-ruff lint-mypy

# Run ruff linter
lint-ruff:
    .venv/bin/ruff check sage tests

# Run ruff formatter check
format-check:
    .venv/bin/ruff format --check sage tests

# Format code with ruff
format:
    .venv/bin/ruff format sage tests
    .venv/bin/ruff check --fix sage tests
    @echo "✓ Code formatted"

# Run mypy type checker
lint-mypy:
    .venv/bin/mypy sage

# Run all checks (lint + test)
check: lint test-headless
    @echo "✓ All checks passed"

# ============================================================================
# Running
# ============================================================================

# Run the daemon
daemon config="~/.config/shortcut-sage":
    .venv/bin/python -m sage daemon --config {{config}}

# Run the overlay
overlay:
    .venv/bin/python -m sage overlay

# Run overlay in demo mode
demo:
    .venv/bin/python -m sage overlay --demo

# Run the doctor diagnostic tool
doctor:
    .venv/bin/shortcut-sage-doctor

# ============================================================================
# Cleanup
# ============================================================================

# Remove generated files
clean:
    rm -rf .pytest_cache htmlcov .coverage coverage.xml
    rm -rf screenshots/*.png
    rm -rf __pycache__ sage/__pycache__ tests/__pycache__
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    @echo "✓ Cleaned"

# Remove virtual environment
clean-venv:
    rm -rf .venv
    @echo "✓ Virtual environment removed"

# Full clean
clean-all: clean clean-venv

# ============================================================================
# CI Simulation
# ============================================================================

# Simulate CI checks locally
ci: format-check lint test-headless
    @echo "✓ CI simulation passed"

# Simulate full visual test CI
ci-visual: test-visual-xvfb
    @echo "✓ Visual test CI simulation complete"
    @echo "  Screenshots in: screenshots/"

# ============================================================================
# Development
# ============================================================================

# Watch for changes and run tests
watch:
    .venv/bin/pytest-watch tests/unit/ -- -v

# Open coverage report in browser
cov-open:
    xdg-open htmlcov/index.html 2>/dev/null || open htmlcov/index.html 2>/dev/null || echo "Open htmlcov/index.html manually"
