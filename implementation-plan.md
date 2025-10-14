# Shortcut Sage — Phased Implementation Plan (PR-gated)

> This plan is designed for continuous PR creation (do-not-merge; reviewers follow behind).

## Phases & Gates (Summary)
- **PR-00:** Repo/CI Bootstrap — CI passes; coverage ≥80%.
- **PR-01:** Config & Schemas — loaders, validation, hot-reload.
- **PR-02:** Engine Core — ring buffer, features, matcher, policy.
- **PR-03:** IPC (DBus) — SendEvent/Ping, Suggestions signal.
- **PR-04:** KWin Event Monitor — single script; dev test shortcut.
- **PR-05:** Overlay UI MVP — PySide6 chip; DBus listener.
- **PR-06:** End-to-End Demo — wired pipeline; logs; latency snapshot. **(MVP)**
- **PR-07:** Shortcut Research & Export — programmatic discovery & exporter.
- **PR-08:** Observability & Hardening — counters/hist; rotation; redaction.
- **PR-09:** Packaging & Autostart — pipx; .desktop; doctor.
- **PR-10:** Dev Audit Batch — NDJSON batch; report stub.
- **PR-11:** Dev Hints (offline) — dev-only toasts/panel.
- **PR-12:** Personalization — CTR-decay re-rank.
- **PR-13:** Classifier (optional) — flag-gated; graceful fallback.
- **PR-14:** Background Audit Scheduler — cadence & guardrails (dev-only).
- **PR-15:** Overlay Polish (minimal) — autosize; minor translucency flag.
- **PR-16:** Security/Privacy Pass — threat model; defaults enforced.
- **PR-17-stretch:** Hyprland Adapter — alternative EventSource; experimental.

## Required Tests per Phase
(As listed in the earlier “Phased Implementation Plan,” reproduced in brief here.)
- PR-00: UT/CI green; coverage gate.
- PR-01: UT config validity; IT hot-reload.
- PR-02: UT matcher/policy; IT goldens; perf note.
- PR-03: IT DBus method/signal; malformed payload handling.
- PR-04: Manual IT KWin hook; E2E smoke.
- PR-05: UT overlay layout; E2E signal→paint.
- PR-06: E2E scenarios; log rotation; latency snapshot.
- PR-07: IT exporter correctness; E2E keys from export.
- PR-08: UT counters; IT rotation; SEC redaction-on-by-default.
- PR-09: IT pipx install; autostart; doctor.
- PR-10: IT batch build; report stub; SEC redaction.
- PR-11: UT/IT hints dev-only; cooldown.
- PR-12: IT CTR order shift; perf stable.
- PR-13: UT/IT feature-flag parity; fallback.
- PR-14: IT scheduler cadence & backpressure.
- PR-15: UT autosize; E2E no focus steal.
- PR-16: SEC doc+scan; defaults enforced.
- PR-17: IT/E2E Hyprland adapter; experimental tag.

## Shortcut Research & Export (Programmatic Discovery)
- Enumerate KDE sources: KGlobalAccel/DBus, KConfig (`~/.config/kglobalshortcutsrc`).
- Build `export-shortcuts` to map actions→keys, dedupe conflicts, and write `shortcuts.yaml`.
- IT: verify export on controlled fixtures; ensure no PII.

## Stretch Goal: Hyprland
- Abstract EventSource; implement `HyprlandSource` using IPC socket/`hyprctl` for focus/workspace and a test shortcut path; keep engine unchanged.
