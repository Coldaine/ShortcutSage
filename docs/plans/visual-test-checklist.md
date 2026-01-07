# PR-05 Visual Test Checklist

## Overview

This document describes the automated visual testing workflow for validating the overlay UI. The system uses:

1. **GitHub Actions** to run tests in a virtual display environment
2. **Claude Vision** to automatically validate screenshots against criteria
3. **Artifacts** for manual review if needed

## Automated Testing via GitHub Actions

### Quick Start (Recommended)

1. **Add API Key** (one-time setup):
   - Go to repo **Settings → Secrets and variables → Actions**
   - Click **New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: Your Anthropic API key

2. **Run the workflow**:
   - Go to **Actions → Visual Tests → Run workflow**
   - Click **Run workflow**
   - Wait for completion (~3-5 minutes)

3. **Review results**:
   - Check the workflow summary for pass/fail
   - Download **overlay-screenshots** artifact if needed
   - View detailed validation report in the summary

### What Happens

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Runner (Ubuntu + xvfb)                      │
│                                                             │
│  1. Install graphics libs (libegl1, libgl1, etc.)           │
│  2. Run visual_test_overlay.py under xvfb                   │
│  3. Capture 5 test screenshots                              │
│  4. Send screenshots to Claude API for validation           │
│  5. Generate pass/fail report                               │
│  6. Upload screenshots as artifacts                         │
└─────────────────────────────────────────────────────────────┘
```

### Validation Criteria (Checked by Claude)

Each screenshot is validated against specific criteria:

| Test | Must Have | Must Not Have |
|------|-----------|---------------|
| **01_empty** | Empty/minimal window | Any shortcut text or chips |
| **02_suggestions** | "Meta+Tab", "Meta+Left", 2 chips | More than 3 chips |
| **03_single** | Exactly 1 chip, "Meta+Tab" | Multiple chips |
| **04_max_three** | Exactly 3 chips | More than 3 chips |
| **05_cleared** | Empty window | Any chips or shortcuts |

## Manual Testing (Alternative)

### On your KDE Plasma machine:

```bash
cd ~/ShortcutSage
source .venv/bin/activate
pip install -e .

# Run visual tests
python scripts/visual_test_overlay.py
```

### Validate locally with Claude:

```bash
pip install anthropic
export ANTHROPIC_API_KEY='your-key'
python scripts/validate_screenshots.py screenshots/
```

## Expected Screenshots

| Screenshot | Description | Expected Result |
|------------|-------------|-----------------|
| `overlay_test_01_empty_*.png` | Empty overlay | Small transparent window, no chips |
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

## Troubleshooting

### GitHub Actions fails to capture screenshots
- Check that `xvfb-run` is installed (should be automatic)
- Verify `QT_QPA_PLATFORM=offscreen` is set
- Review the "Run visual tests" step logs

### Claude validation fails unexpectedly
- Download the screenshots artifact and review manually
- Check if the overlay is rendering correctly
- Validation might fail on edge cases - review the reasoning

### "ANTHROPIC_API_KEY not configured"
- Add the secret in Settings → Secrets → Actions
- Workflow will still capture screenshots without the key
- You can manually review artifacts

### Local: "No display available"
- Run from a graphical session (not SSH without X forwarding)
- Try `export DISPLAY=:0` if in a terminal

### Local: PySide6 import fails
- Ensure you're in the venv: `source .venv/bin/activate`
- Install: `pip install PySide6`

## Files

| File | Purpose |
|------|---------|
| `scripts/visual_test_overlay.py` | Captures screenshots of overlay in various states |
| `scripts/validate_screenshots.py` | Sends screenshots to Claude for validation |
| `.github/workflows/visual-tests.yml` | GitHub Actions workflow |

---

**Last Updated**: 2025-01-07
**Related**: [PR-05-overlay-checklist.md](./PR-05-overlay-checklist.md)
