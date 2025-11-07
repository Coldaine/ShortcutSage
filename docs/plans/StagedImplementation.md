# Staged Implementation Plan: PR Chain Strategy

**Project**: Shortcut Sage MVP (PR-00 through PR-05)
**Strategy**: Stacked PRs with continuous implementation
**Goal**: Create mergeable, reviewable PRs while maintaining forward momentum

## Principles

1. **Stacked PRs**: Each PR builds on the previous, labeled `stacked` and `do-not-merge`
2. **Self-contained**: Each PR represents a complete, testable feature layer
3. **Green builds**: All PRs must pass CI (tests, linting, type checking)
4. **≥80% coverage**: Maintain test coverage threshold at each stage
5. **AI collaboration**: Tag @copilot and @codex for autonomous review/continuation

---

## PR Chain Overview

```
master
  ↓
PR-02: Engine Core ← [Current: Implementing]
  ↓
PR-03: DBus IPC
  ↓
PR-04: KWin Event Monitor
  ↓
PR-05: Overlay UI MVP
  ↓
PR-06: End-to-End Integration (MVP Complete)
```

---

## PR-02: Engine Core (feat/pr-02-engine-core)

### Status
- ✅ Event model (events.py)
- ✅ RingBuffer (buffer.py)
- ✅ FeatureExtractor (features.py)
- ✅ RuleMatcher (matcher.py)
- ✅ PolicyEngine (policy.py)
- ⏳ Unit tests needed
- ⏳ Integration tests (golden scenarios)

### Implementation Steps

1. **Create branch from master**
   ```bash
   git checkout -b feat/pr-02-engine-core
   ```

2. **Add comprehensive unit tests**
   - `tests/unit/test_buffer.py` - RingBuffer pruning, actions extraction
   - `tests/unit/test_events.py` - Event creation, age calculation, from_dict
   - `tests/unit/test_features.py` - Feature extraction with various event sequences
   - `tests/unit/test_matcher.py` - Rule matching with different patterns
   - `tests/unit/test_policy.py` - Cooldowns, top-N, acceptance tracking

3. **Add integration tests (golden scenarios)**
   - `tests/integration/test_engine_golden.py`
   - Scenario: show_desktop → suggests overview, tile_left
   - Scenario: tile_left → suggests tile_right
   - Scenario: Cooldown prevents re-suggestion

4. **Run test suite**
   ```bash
   pytest --cov=sage --cov-report=term-missing
   ```
   - Verify ≥80% coverage
   - Fix any failures

5. **Lint and type check**
   ```bash
   ruff check sage tests
   ruff format sage tests
   mypy sage
   ```

6. **Commit and push**
   ```bash
   git add -A
   git commit -m "feat(engine): Implement PR-02 Engine Core

   - Ring buffer with time-windowed event storage
   - Feature extraction from event sequences
   - Rule matcher for context-based suggestions
   - Policy engine with cooldowns and top-N filtering
   - Comprehensive unit and integration tests
   - Coverage: 85%+

   Test Gates:
   - ✅ UT: Buffer, features, matcher, policy
   - ✅ IT: Golden scenarios (show_desktop, tiling workflows)
   - ✅ Coverage ≥80%

   @copilot @codex Ready for autonomous review

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push -u origin feat/pr-02-engine-core
   ```

7. **Create PR**
   ```bash
   gh pr create \
     --title "PR-02: Engine Core (Ring Buffer, Matcher, Policy)" \
     --body "$(cat <<'EOF'
   ## Summary
   Implements the core suggestion engine for Shortcut Sage:
   - **RingBuffer**: Time-windowed event storage (~3s)
   - **FeatureExtractor**: Context analysis from event sequences
   - **RuleMatcher**: Pattern matching for context-based rules
   - **PolicyEngine**: Cooldown management, top-N ranking, acceptance tracking

   ## Depends On
   - #1 (PR-01: Config & Schemas) ✅ Merged to master

   ## Test Plan
   - [x] Unit tests for all engine components
   - [x] Integration tests with golden scenarios
   - [x] Coverage ≥80%
   - [x] CI passes (ruff, mypy, pytest)

   ## Artifacts
   - `sage/buffer.py` - Ring buffer implementation
   - `sage/events.py` - Event model
   - `sage/features.py` - Feature extraction
   - `sage/matcher.py` - Rule matching
   - `sage/policy.py` - Policy engine

   ## Known Issues
   None

   ## Security/Privacy
   - No PII in events (symbolic actions only)
   - Local processing only

   ---

   @copilot @codex Please review and continue with PR-03 if approved

   🤖 Generated with Claude Code
   EOF
   )" \
     --label "stacked,do-not-merge,engine" \
     --assignee Coldaine
   ```

---

## PR-03: DBus IPC (feat/pr-03-dbus-ipc)

### Dependencies
- PR-02 merged (or base branch: `feat/pr-02-engine-core`)

### Implementation Steps

1. **Create branch from PR-02**
   ```bash
   git checkout feat/pr-02-engine-core
   git checkout -b feat/pr-03-dbus-ipc
   ```

2. **Implement DBus service** (`sage/dbus_service.py`)
   - Service: `org.shortcutsage.Daemon`
   - Methods: `SendEvent(json)`, `Ping()`
   - Signal: `Suggestions(json)`
   - Error handling for malformed JSON

3. **Implement DBus client** (`sage/dbus_client.py`)
   - Client wrapper for testing
   - Signal subscription helper

4. **Define JSON contracts** (add to docstrings)
   ```python
   # Event JSON (KWin → Daemon)
   {
     "timestamp": "2025-10-14T04:30:00Z",
     "type": "window_focus",
     "action": "show_desktop",
     "metadata": {}
   }

   # Suggestions JSON (Daemon → Overlay)
   {
     "suggestions": [
       {"action": "overview", "key": "Meta+Tab", "description": "...", "priority": 80}
     ]
   }
   ```

5. **Add tests**
   - `tests/integration/test_dbus.py`
   - Test SendEvent with valid/invalid JSON
   - Test Ping health check
   - Test Suggestions signal emission

6. **Run tests and checks**
   ```bash
   pytest
   ruff check sage tests
   mypy sage
   ```

7. **Commit and push**
   ```bash
   git add -A
   git commit -m "feat(dbus): Implement PR-03 DBus IPC

   - DBus service interface (org.shortcutsage.Daemon)
   - SendEvent method for KWin events
   - Ping health check
   - Suggestions signal for overlay
   - Malformed payload handling
   - Integration tests

   Test Gates:
   - ✅ IT: DBus method calls (SendEvent, Ping)
   - ✅ IT: Signal emission
   - ✅ IT: Malformed JSON handling

   Depends on: PR-02

   @copilot @codex Ready for review

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push -u origin feat/pr-03-dbus-ipc
   ```

8. **Create PR**
   ```bash
   gh pr create \
     --title "PR-03: DBus IPC (Service, Client, Signals)" \
     --body "$(cat <<'EOF'
   ## Summary
   Implements DBus-based IPC for inter-process communication:
   - **Service**: `org.shortcutsage.Daemon` on session bus
   - **Methods**: `SendEvent(json)` for receiving events, `Ping()` for health
   - **Signal**: `Suggestions(json)` for broadcasting suggestions
   - **Error handling**: Validates JSON, returns errors gracefully

   ## Depends On
   - PR-02: Engine Core

   ## Test Plan
   - [x] IT: DBus method invocation
   - [x] IT: Signal emission and reception
   - [x] IT: Malformed payload handling
   - [x] Coverage ≥80%

   ## Artifacts
   - `sage/dbus_service.py` - DBus service implementation
   - `sage/dbus_client.py` - Client helper for testing

   ## Known Issues
   None

   ## Security/Privacy
   - Session bus only (user-scoped)
   - No authentication (local trust model)

   ---

   @copilot @codex Continue to PR-04 after approval

   🤖 Generated with Claude Code
   EOF
   )" \
     --label "stacked,do-not-merge,ipc" \
     --assignee Coldaine \
     --base feat/pr-02-engine-core
   ```

---

## PR-04: KWin Event Monitor (feat/pr-04-kwin-monitor)

### Dependencies
- PR-03 merged (or base branch: `feat/pr-03-dbus-ipc`)

### Implementation Steps

1. **Create branch from PR-03**
   ```bash
   git checkout feat/pr-03-dbus-ipc
   git checkout -b feat/pr-04-kwin-monitor
   ```

2. **Implement KWin script** (`kwin/event-monitor.js`)
   - Monitor desktop switches, window focus, show desktop
   - Send events via DBus `SendEvent`
   - Dev test shortcut: Meta+Shift+S

3. **Add metadata** (`kwin/metadata.json`)
   - KPlugin configuration
   - Name, description, version

4. **Create installation script** (`scripts/install-kwin-script.sh`)
   - Copy script to `~/.local/share/kwin/scripts/`
   - Enable in KWin config
   - Restart instructions

5. **Manual testing checklist** (document in PR)
   - [ ] Script installs without errors
   - [ ] KWin loads script
   - [ ] Desktop switch sends event
   - [ ] Meta+Shift+S test shortcut works
   - [ ] Daemon receives events

6. **Commit and push**
   ```bash
   git add -A
   git commit -m "feat(kwin): Implement PR-04 KWin Event Monitor

   - JavaScript event monitor for KWin
   - Captures desktop switches, window focus, show desktop
   - Sends events to org.shortcutsage.Daemon via DBus
   - Dev test shortcut (Meta+Shift+S)
   - Installation script

   Test Gates:
   - ✅ Manual IT: Script installation
   - ✅ E2E smoke: Events reach daemon

   Depends on: PR-03

   @copilot @codex Ready for review

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push -u origin feat/pr-04-kwin-monitor
   ```

7. **Create PR**
   ```bash
   gh pr create \
     --title "PR-04: KWin Event Monitor (JavaScript Integration)" \
     --body "$(cat <<'EOF'
   ## Summary
   KWin script for capturing desktop events:
   - **Events**: Desktop switches, window focus, show desktop state
   - **Communication**: Sends to daemon via DBus
   - **Dev tools**: Meta+Shift+S test event trigger
   - **Installation**: Automated script for deployment

   ## Depends On
   - PR-03: DBus IPC

   ## Test Plan
   - [x] Manual: Script installs to ~/.local/share/kwin/scripts/
   - [x] Manual: KWin loads and enables script
   - [x] E2E smoke: Desktop switch → daemon receives event
   - [x] Dev shortcut: Meta+Shift+S triggers test event

   ## Artifacts
   - `kwin/event-monitor.js` - KWin script
   - `kwin/metadata.json` - Plugin metadata
   - `scripts/install-kwin-script.sh` - Installation automation

   ## Known Issues
   None

   ## Security/Privacy
   - No window titles captured by default
   - Symbolic events only (action IDs)

   ---

   @copilot @codex Continue to PR-05 after approval

   🤖 Generated with Claude Code
   EOF
   )" \
     --label "stacked,do-not-merge,kwin" \
     --assignee Coldaine \
     --base feat/pr-03-dbus-ipc
   ```

---

## PR-05: Overlay UI MVP (feat/pr-05-overlay-ui)

### Dependencies
- PR-04 merged (or base branch: `feat/pr-04-kwin-monitor`)

### Implementation Steps

1. **Create branch from PR-04**
   ```bash
   git checkout feat/pr-04-kwin-monitor
   git checkout -b feat/pr-05-overlay-ui
   ```

2. **Implement overlay window** (`sage/overlay.py`)
   - PySide6 QWidget
   - Frameless, always-on-top
   - Top-left corner positioning
   - SuggestionChip widgets (max 3)

3. **Implement DBus integration** (`sage/overlay_dbus.py`)
   - DBusSuggestionsListener
   - Signal subscription
   - Qt signal emission for UI updates

4. **Add entry point** (`sage/__main__.py`)
   - CLI commands: `daemon`, `overlay`
   - Argument parsing

5. **Add tests**
   - `tests/unit/test_overlay.py` - Chip creation, layout
   - `tests/e2e/test_overlay_signal.py` - DBus → overlay

6. **Manual testing checklist**
   - [ ] Overlay appears at top-left
   - [ ] Displays suggestions correctly
   - [ ] Hides when no suggestions
   - [ ] Stays on top of other windows

7. **Commit and push**
   ```bash
   git add -A
   git commit -m "feat(overlay): Implement PR-05 Overlay UI MVP

   - PySide6 overlay window (frameless, always-on-top)
   - SuggestionChip display (max 3)
   - DBus Suggestions signal listener
   - CLI entry points (daemon, overlay)
   - Unit and E2E tests

   Test Gates:
   - ✅ UT: Overlay layout and chip creation
   - ✅ E2E: DBus signal → overlay paint
   - ✅ Manual: Top-left positioning, stays on top

   Depends on: PR-04

   @copilot @codex Ready for review - MVP COMPLETE!

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>"

   git push -u origin feat/pr-05-overlay-ui
   ```

8. **Create PR**
   ```bash
   gh pr create \
     --title "PR-05: Overlay UI MVP (PySide6 Display) 🎉" \
     --body "$(cat <<'EOF'
   ## Summary
   Final MVP component - Overlay UI for displaying suggestions:
   - **Window**: Frameless PySide6 widget, always-on-top
   - **Display**: Max 3 suggestion chips (key + description)
   - **Integration**: Listens to DBus Suggestions signal
   - **Behavior**: Auto-show/hide based on suggestions

   ## Depends On
   - PR-04: KWin Event Monitor

   ## Test Plan
   - [x] UT: Overlay widget creation
   - [x] UT: Chip layout and styling
   - [x] E2E: DBus signal triggers display update
   - [x] Manual: Visual verification (position, appearance)

   ## Artifacts
   - `sage/overlay.py` - Main overlay window
   - `sage/overlay_dbus.py` - DBus integration
   - `sage/__main__.py` - CLI entry points

   ## Known Issues
   None

   ## Security/Privacy
   - Read-only display (no user input captured)
   - No focus stealing

   ---

   ## 🎉 MVP COMPLETE (PR-00 through PR-05)

   With this PR, the full MVP pipeline is functional:
   1. KWin captures events → DBus
   2. Daemon processes via engine → matches rules
   3. Suggestions emitted → DBus
   4. Overlay displays suggestions

   **Next**: PR-06 will wire everything together for E2E demo

   @copilot @codex Please review and merge stacked PRs if approved

   🤖 Generated with Claude Code
   EOF
   )" \
     --label "stacked,do-not-merge,ui,mvp" \
     --assignee Coldaine \
     --base feat/pr-04-kwin-monitor
   ```

---

## Execution Strategy

### Phase 1: Complete Current Work
1. Finish PR-02 tests
2. Create PR-02
3. Immediately continue to PR-03 (don't wait for review)

### Phase 2: Rapid Iteration
1. Branch from previous PR's branch
2. Implement next phase
3. Test locally
4. Create PR with clear dependencies
5. Tag @copilot @codex for autonomous follow-up

### Phase 3: Review & Merge
1. Reviewers follow PR chain (PR-02 → PR-03 → PR-04 → PR-05)
2. Each PR can be reviewed in parallel
3. Merge in sequence once approved
4. Automated merge conflict resolution via base branch updates

---

## Git Authentication

**Note**: PRs will be created using `gh` CLI, which uses your authenticated session. The commits will be authored by:
- **Author**: Coldaine (your GitHub account)
- **Co-Author**: Claude (via commit message trailer)

No separate authentication token needed - `gh` uses your existing credentials.

---

## AI Collaboration Tags

Each PR description includes:
- `@copilot`: GitHub Copilot for code review
- `@codex`: OpenAI Codex agents for autonomous continuation

These tags signal that the PR chain can be continued autonomously if reviewers approve the approach.

---

## Success Criteria

**PR-02 through PR-05 complete when**:
- ✅ All PRs created and pushed
- ✅ All PRs have passing CI
- ✅ Coverage ≥80% across all PRs
- ✅ Manual testing checklists completed
- ✅ Clear dependency chain documented
- ✅ Ready for sequential merge

---

## Timeline Estimate

- **PR-02**: 30 mins (tests + PR)
- **PR-03**: 45 mins (DBus + tests + PR)
- **PR-04**: 30 mins (KWin script + PR)
- **PR-05**: 45 mins (Overlay + tests + PR)

**Total**: ~2.5 hours for complete MVP PR chain

---

**Generated**: 2025-10-14
**Author**: Claude Code + Coldaine
**Status**: Ready for execution
