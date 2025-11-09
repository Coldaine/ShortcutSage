# PR-05: Overlay UI Execution Plan

Prepared: 2025-11-08  
Source context: `docs/updates/2025-11-08-project-status.md`

## Objective
Finalize the Overlay UI MVP so PR-05 can be opened immediately after PR-04. This work is documentation- and test-heavy because the PySide6 overlay already exists in `sage/overlay.py`; the focus is proving it, documenting it, and wiring it into the stacked PR flow.

## Deliverables
- ✅ PySide6 overlay window (`sage/overlay.py`) – frameless, top-left, max 3 chips
- ✅ CLI entry points (`shortcut-sage daemon|overlay`) with argparse and help text
- ✅ Unit coverage (`tests/unit/test_overlay.py`)
- ⏳ Manual testing evidence (screenshots/checklist)
- ✅ README/docs updates describing overlay behavior & test plan
- ✅ E2E signal smoke (DBus Suggestions → overlay paint) – lightweight harness acceptable

## Task Breakdown

| Task | Details | Status |
| --- | --- | --- |
| Overlay code sanity pass | Re-read `sage/overlay.py`, confirm logging, fallback path | ✅ Done 2025-11-08 |
| CLI plumbing | Extend `sage/__main__.py` (argparse) + expose overlay entry point | ✅ Done 2025-11-08 |
| CLI docs | Expand README usage + overlay section | ✅ Done 2025-11-08 |
| Manual test checklist | Define reproducible steps + expected results | ⏳ (documented below; needs execution evidence) |
| Screenshot / artifact | Capture overlay rendering on KDE | ⏳ |
| E2E signal test | Add `tests/e2e/test_overlay_signal.py` to verify DBus listener → UI | ✅ Done 2025-11-08 |
| PR narrative | Prep `PR-05` template, include Known Issues & security note | ⏳ |

## Manual Testing Checklist (to execute on KDE Plasma 5.27+)

| Step | Command / Action | Expected Result |
| --- | --- | --- |
| 1 | `shortcut-sage daemon --config ~/.config/shortcut-sage` | Daemon logs DBus bus name + waits for events |
| 2 | `shortcut-sage overlay` (separate terminal) | Overlay window renders in top-left, transparent background |
| 3 | Trigger dev shortcut (`Meta+Shift+S`) or run `python scripts/test_kwin_integration.py --event demo_toggle` | DBus `SendEvent` acknowledged in daemon logs |
| 4 | Observe overlay | Receives `Suggestions` signal, displays up to 3 chips with key + description |
| 5 | Clear events (wait > cooldown) | Overlay hides (chips removed) after `Suggestions` empty payload |
| 6 | Move focus between windows rapidly | Overlay remains always-on-top and does not steal focus |

Record run logs + screenshot; attach to PR as artifacts.

## Execution Steps
1. Branching:
   ```bash
   git checkout -b feat/pr-05-overlay-ui origin/master
   ```
2. Documentation updates:
   - README “Project Status” table → mark PR-02..PR-04 ✅, highlight PR-05 in-progress
   - New “Overlay UI” section describing behavior + how to run in demo mode (`shortcut-sage overlay --demo`)
   - Link this plan from `docs/updates/README.md` for discoverability
3. Testing:
   ```bash
   pytest tests/unit/test_overlay.py
   pytest tests/e2e/test_overlay_signal.py  # new
   ```
4. Manual verification per checklist above (capture screenshot + notes).
5. PR body template (drop into `.github/pull_request_template.md` or ad-hoc text) covering Summary, Depends On (#3), Test Plan, Artifacts, Known Issues.

## Risks & Mitigations
- **DBus not available on Windows dev box** → use fallback mode for unit tests; run E2E on Linux (Nobara desktop).
- **PySide6 CI requirements** → ensure `xvfb-run` is used in GitHub Actions matrix (already configured in `.github/workflows/ci.yml`).
- **Overlay steals focus** → confirm `Qt.WindowDoesNotAcceptFocus` flag remains set; add regression test if behavior changes.

## Definition of Done
- PR-05 branch pushed with updated docs/tests/checklist artifacts.
- CI green (pytest, mypy, ruff); coverage stays ≥75%.
- Manual validation evidence attached to PR.
- Status doc updated to reflect PR-05 opened and in review queue.
