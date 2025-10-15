# Shortcut Sage — PR Train Operator Handbook (Save-only)

> Purpose: Single reference you **save**. The agent prompt will point here for details. Keep this file in-repo (e.g., `docs/pr-train-handbook.md`).

## 1) Delivery pattern
| Pattern | Why it’s exceptional | Apply to your plan (Proposal v2) | Anti-pattern (don’t do / when it won’t work) | Similar-but-different |
|---|---|---|---|---|
| **Stacked PR train** | Small focused diffs. Faster CI feedback. Clear dependencies | Label each PR `stacked` + `do-not-merge`. Base each PR on the immediate predecessor | Blocking on reviews. Mega-PRs. Squashing the entire chain | Trunk-based with feature flags |

## 2) Global rules
- Never wait for review. Never merge during the train.
- Keep CI green when feasible. If gates fail, still open PR and record **Known Issues**.
- Scope: local processing only, symbolic events only, KDE Plasma Wayland focus, no secrets/PII, DBus IPC.
- Coverage floor: **≥80%** on every PR.
- Every PR body must include: Summary, Implements, Depends on, Test Plan (checklist), Artifacts Changed, Known Issues, Security/Privacy Notes.
- Labels: `stacked`, `do-not-merge`. Optional: `phase:XX`, `area:<slug>`, `security`.

## 3) Branching and stacking
- Branch naming: `feat/phase-XX-<slug>`.
- Base for PR-00: `master` (or `main`).
- Base for PR-N (N>00): previous phase branch to keep diffs tight.
- Link dependency chain in each PR body under **Depends on**.

## 4) Global execution loop (bash template)
```bash
# 0) Set variables per phase
PHASE=02
SLUG="engine-core"
TITLE="PR-${PHASE}: Engine Core"
BASE="master"   # or previous phase branch for stacked bases

# 1) Branch
git checkout ${BASE}
git pull
git checkout -b feat/phase-${PHASE}-${SLUG}

# 2) Implement deliverables for this phase (keep changes self-contained)

# 3) Local gates
ruff check .
ruff format .
mypy .
pytest --cov=. --cov-report=term-missing

# 4) Commit
git add -A
git commit -m "feat(${SLUG}): ${TITLE}"

# 5) Push
git push -u origin HEAD

# 6) Open PR with labels and dependency notes
gh pr create \
  --title "${TITLE}" \
  --body-file ./PR_BODY_${PHASE}.md \
  --label "stacked,do-not-merge" \
  --base ${BASE}

# 7) Immediately proceed to the next phase
```

## 5) PR body template (`PR_BODY_<phase>.md`)
```
# Summary
What this phase implements. Why now.

# Implements
Bullets of concrete deliverables completed in this PR.

# Depends on
Link to previous phase PR(s). Note stacking base.

# Test Plan (checklist)
- [ ] Unit tests added/updated
- [ ] Integration/E2E per phase requirements
- [ ] Coverage ≥80%
- [ ] Security/Privacy checks (no secrets/PII)

# Artifacts Changed
Files, scripts, schemas, UI components.

# Known Issues
Gates that failed or items deferred intentionally.

# Security and Privacy Notes
Data boundaries, logging redaction, scopes.
```

## 6) Phase deliverables and gates
- **PR-00 Repo and CI bootstrap**
  - Deliverables: CI config, lint/type/test scaffolding, coverage tooling.
  - Tests: Unit and CI smoke. Coverage ≥80%.
- **PR-01 Config and schemas**
  - Deliverables: Config loaders, schema validation, hot reload.
  - Tests: Config validity UT, hot-reload IT.
- **PR-02 Engine core**
  - Deliverables: Ring buffer, feature extraction, rule matcher, policy engine.
  - Tests: Matcher/policy UT, golden tests IT, perf notes.
- **PR-03 DBus IPC**
  - Deliverables: Service with `SendEvent`, `Ping`, `Suggestions` signal. Strict JSON validation.
  - Tests: Method/signal IT, malformed payload handling.
- **PR-04 KWin event monitor**
  - Deliverables: Single script, dev test shortcut, E2E smoke to daemon.
  - Tests: Manual IT, E2E smoke.
- **PR-05 Overlay UI MVP**
  - Deliverables: PySide6 chip overlay, DBus listener.
  - Tests: Overlay UT and DBus→paint E2E.
- **PR-06 End-to-end demo**
  - Deliverables: Wired pipeline, logs, latency snapshot.
  - Tests: E2E scenarios, rotation, latency snapshot.
- **PR-07 Shortcut research and export**
  - Deliverables: Programmatic discovery, exporter, `shortcuts.yaml`.
  - Tests: Exporter IT, E2E keys from export.
- **PR-08 Observability and hardening**
  - Deliverables: Counters/histograms, rotation, redaction on by default.
  - Tests: Counters UT, rotation IT, security checks.
- **PR-09 Packaging and autostart**
  - Deliverables: `pipx`, `.desktop`, diagnostic doctor.
  - Tests: pipx install, autostart, doctor IT.
- **PR-10 Dev audit batch**
  - Deliverables: NDJSON batch, report stub, redaction.
  - Tests: Batch build IT, redaction.
- **PR-11 Dev hints offline**
  - Deliverables: Dev-only toasts/panel with cooldown.
  - Tests: UT and IT for dev-only behavior.
- **PR-12 Personalization**
  - Deliverables: CTR-decay re-rank.
  - Tests: Order shift IT, perf stability.
- **PR-13 Classifier optional**
  - Deliverables: Flag-gated classifier, graceful fallback.
  - Tests: Flag parity UT/IT.
- **PR-14 Background audit scheduler**
  - Deliverables: Cadence and guardrails.
  - Tests: Cadence and backpressure IT.
- **PR-15 Overlay polish minimal**
  - Deliverables: Autosize, translucency flag, no focus steal.
  - Tests: Autosize UT, E2E focus behavior.
- **PR-16 Security and privacy pass**
  - Deliverables: Threat model, enforced defaults.
  - Tests: SEC doc and scan.
- **PR-17-stretch Hyprland adapter**
  - Deliverables: Alternative event source, experimental.
  - Tests: IT and E2E for adapter.

## 7) Quality, security, privacy
- Logging redaction defaults on. No sensitive payloads in logs.
- Symbolic events only. No raw user content capture.
- Include a simple threat model in PR-16.

## 8) Tooling quick refs
- Lint/format: `ruff check .` then `ruff format .`
- Type checks: `mypy .`
- Tests: `pytest --cov=. --cov-report=term-missing`
- PRs: `gh pr create` with labels `stacked,do-not-merge`

## 9) Artifacts to keep up to date
- `PR_BODY_XX.md` for each phase
- This handbook file
- Any generated reports or NDJSON batches for audit phases

