# Claude Code Hooks for Shortcut Sage

This document describes proposed hooks for automating development workflows with Claude Code.

## Proposed Hooks

### 1. Pre-Push Visual Test Hook

**Purpose**: Run visual tests before pushing to ensure overlay UI hasn't regressed.

**File**: `.claude/hooks/pre-push-visual-test.sh`

```bash
#!/bin/bash
# Pre-push hook: Run visual tests if overlay code changed

# Check if overlay-related files changed
OVERLAY_FILES=$(git diff --cached --name-only | grep -E "(overlay|visual_test|validate_screenshots)")

if [ -n "$OVERLAY_FILES" ]; then
    echo "Overlay code changed - running visual tests..."

    # Check if we have a display (graphical env or xvfb)
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        python scripts/visual_test_overlay.py
        if [ $? -ne 0 ]; then
            echo "Visual tests failed! Fix before pushing."
            exit 1
        fi
    else
        echo "No display available - skipping visual tests"
        echo "Run 'xvfb-run python scripts/visual_test_overlay.py' manually"
    fi
fi

exit 0
```

### 2. Post-Checkout Environment Reminder

**Purpose**: Remind about environment setup after checking out.

**File**: `.claude/hooks/post-checkout.sh`

```bash
#!/bin/bash
# Post-checkout hook: Remind about environment setup

echo ""
echo "=== Shortcut Sage Development Environment ==="
echo ""

# Check for venv
if [ ! -d ".venv" ]; then
    echo "No virtual environment found."
    echo "Run: just setup"
fi

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "ANTHROPIC_API_KEY not set - Claude validation disabled"
    echo "Set with: export ANTHROPIC_API_KEY='your-key'"
fi

echo ""
```

### 3. Claude Code Session Start Hook

**Purpose**: Verify environment when starting a Claude Code session.

**Hook Type**: `SessionStart` (Claude Code built-in)

**Configuration** (`.claude/settings.json`):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "bash",
        "args": ["-c", "source .venv/bin/activate 2>/dev/null && python -c 'import sage' 2>/dev/null && echo 'Environment ready' || echo 'Run: just setup'"],
        "timeout": 5000
      }
    ]
  }
}
```

### 4. Pre-Commit Lint Hook

**Purpose**: Run linting before commits.

**File**: `.claude/hooks/pre-commit.sh`

```bash
#!/bin/bash
# Pre-commit hook: Run linting

# Check if Python files changed
PYTHON_FILES=$(git diff --cached --name-only | grep -E "\.py$")

if [ -n "$PYTHON_FILES" ]; then
    echo "Running ruff on staged Python files..."

    # Run ruff check
    ruff check $PYTHON_FILES
    if [ $? -ne 0 ]; then
        echo "Linting failed! Fix issues or run 'just format'"
        exit 1
    fi

    # Run ruff format check
    ruff format --check $PYTHON_FILES
    if [ $? -ne 0 ]; then
        echo "Formatting issues found! Run 'just format'"
        exit 1
    fi
fi

exit 0
```

### 5. Visual Test Validation Hook (Claude Code)

**Purpose**: After visual tests run, automatically validate screenshots with Claude.

**Hook Type**: Custom tool completion hook

**Configuration** (`.claude/settings.json`):

```json
{
  "hooks": {
    "AfterToolCall": [
      {
        "matcher": "scripts/visual_test_overlay.py",
        "command": "python",
        "args": ["scripts/validate_screenshots.py", "screenshots/", "--output", "screenshots/validation_report.json"],
        "env": {
          "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
        },
        "timeout": 120000
      }
    ]
  }
}
```

## Installation

### For Git Hooks

```bash
# Create hooks directory
mkdir -p .git/hooks

# Copy and make executable
cp .claude/hooks/pre-commit.sh .git/hooks/pre-commit
cp .claude/hooks/pre-push-visual-test.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

### For Claude Code Hooks

1. Create `.claude/settings.json` with the hook configuration
2. Claude Code will automatically load hooks on session start

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API for visual validation | For validation |
| `DISPLAY` or `WAYLAND_DISPLAY` | Graphical environment for Qt | For visual tests |

## Justfile Integration

The justfile provides recipes that work well with these hooks:

```bash
# Run what pre-commit hook does
just lint

# Run what pre-push hook does
just test-visual

# Simulate full CI
just ci
```

## Recommended Workflow

1. **On checkout**: `just setup` (or hook reminder)
2. **Before commit**: `just format && just lint` (or pre-commit hook)
3. **Before push**: `just test-visual` (or pre-push hook)
4. **In CI**: Workflow runs all tests + Claude validation
