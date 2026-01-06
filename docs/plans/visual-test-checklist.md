# PR-05 Visual Test Checklist

## Overview

This document describes the screenshot-based visual testing workflow for validating the overlay UI. Since automated Qt testing requires a graphical environment, we use a hybrid approach:

1. **Automated screenshot capture** on a KDE Plasma machine
2. **AI-assisted visual review** of the screenshots

## Prerequisites

- KDE Plasma desktop (Nobara, Fedora KDE, Kubuntu, etc.)
- Python 3.11+ with PySide6
- Screenshot tool (spectacle, scrot, or gnome-screenshot)

## Running Visual Tests

### On your KDE Plasma machine:

```bash
# Clone/pull the repo
cd ~/ShortcutSage  # or wherever

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run visual tests
python scripts/visual_test_overlay.py
```

### Expected Output

The script creates `screenshots/` with these test images:

| Screenshot | Description | Expected Result |
|------------|-------------|-----------------|
| `overlay_test_01_empty_*.png` | Empty overlay | Small transparent window, no chips visible |
| `overlay_test_02_suggestions_*.png` | Demo suggestions | 2 chips: "Meta+Tab" and "Meta+Left" |
| `overlay_test_03_single_*.png` | Single suggestion | 1 chip: "Meta+Tab" only |
| `overlay_test_04_max_three_*.png` | Max suggestions | 3 chips displayed |
| `overlay_test_05_cleared_*.png` | Cleared state | Empty, chips removed |

## Visual Validation Criteria

### Position & Layout
- [ ] Overlay appears in top-left corner of screen
- [ ] Window is frameless (no title bar)
- [ ] Window stays on top of other windows
- [ ] Transparent background between chips

### Chip Appearance
- [ ] Key label (e.g., "Meta+Tab") is bold and green (#4CAF50)
- [ ] Description text is white
- [ ] Chips have dark semi-transparent background
- [ ] Rounded corners on chips
- [ ] Proper spacing between chips

### Behavior
- [ ] Suggestions update correctly (chips added/removed)
- [ ] Maximum 3 chips displayed even with more suggestions
- [ ] Empty state shows no chips

## Sharing Screenshots for Review

After running the tests:

1. Find screenshots in `ShortcutSage/screenshots/`
2. Share them in a Claude Code conversation
3. Request visual validation

Example prompt:
> "Here are the overlay screenshots from visual testing. Please review them against the PR-05 acceptance criteria."

## Troubleshooting

### "No display available"
- Run from a graphical session (not SSH without X forwarding)
- Try `export DISPLAY=:0` if in a terminal

### Screenshot tools fail
- Install: `sudo dnf install spectacle` (Fedora/Nobara)
- Or: `sudo apt install scrot` (Debian/Ubuntu)

### PySide6 import fails
- Ensure you're in the venv: `source .venv/bin/activate`
- Check: `pip install PySide6`

## CI/CD Integration

For GitHub Actions, the workflow already includes:
- `xvfb-run` for virtual display
- `libegl1-mesa` for Qt rendering

Visual tests could be automated in CI by:
1. Running `visual_test_overlay.py` under xvfb
2. Uploading screenshots as artifacts
3. Manual review of artifacts before merge

---

**Last Updated**: 2025-01-06
**Related**: [PR-05-overlay-checklist.md](./PR-05-overlay-checklist.md)
