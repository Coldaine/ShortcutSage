# Shortcut Sage — Product & Engineering Bible (MVP-first)

## 0) One-liner
Context-aware helper for **KDE Plasma (Wayland)** that watches recent actions and suggests the next useful keyboard shortcut. **Config-driven. Minimal UI. YAGNI all the way.**

## 1) Vision
### 1.1 What Shortcut Sage is
A lightweight, local-first **suggestion daemon** + tiny overlay that:
- Observes **symbolic** desktop events (desktop view, overview toggle, window moves).
- Matches contexts against **config-defined rules**.
- Surfaces ≤3 **next-step shortcuts** that users can accept simply by pressing them.

### 1.2 What it is not (now)
- Not a keylogger; not app automation.
- Not an AI assistant in the hot path.
- Not a customizable GUI app (MVP has **no in-app settings**).
- Not cross-DE (initially **KDE Plasma (Wayland) only**).

### 1.3 Long-term north star
- Be the “autocomplete for your hands.”  
- Eventually learn personal rhythms; offer subtle, trustworthy nudges.  
- Optional offline audits with slower, smarter LLMs for **dev-only** insights.

## 2) Principles
- **YAGNI**: ship the simplest working loop; only optimize what hurts.
- **Config > Code**: rules in YAML, engine in code; zero hard-coded rules.
- **Privacy by design**: symbolic events only; logs local; redact by default.
- **Separation of concerns**: KWin script (signals) → daemon (logic) → overlay (display).
- **Fail soft**: invalid rules skip safely with explicit warnings.

## 3) Scope & Goals
### 3.1 MVP Goals (Must)
- Ingest **symbolic events** from KWin/DBus.
- **Ring buffer** (~3s) + feature extraction.
- **Rule engine** (config-driven `rules.yaml`) → **policy** (cooldowns, top-N, acceptance).
- **Overlay** (PySide6) small, top-left, always-on-top, read-only, ≤3 suggestions.
- **Shortcuts import** via `shortcuts.yaml` (from export script).
- **Validation** + **NDJSON logs** with rotation.

### 3.2 Post-MVP (Should/Could)
- Dev-only **batch audits** → slower LLM → rationales + short hints (periodic, not inline).
- Personalization (CTR decay).
- Tiny classifier / small local LLM re-rank (if needed).
- Transparency/blur polish.
- Settings UI / rule editor (later).

## 4) Requirements
### 4.1 Functional (F)
F1–F10 per Implementation Plan (see separate doc).

### 4.2 Non-Functional (NF)
NF1–NF8 per Implementation Plan (see separate doc).

## 5) Monorepo Integration (Cold Apps)
```
cold-apps/
  packages/
    cold-core/
    cold-ipc/
    cold-ui/
  apps/
    shortcut-sage/
      docs/
      kwin/
      sage/
      scripts/
      tests/
```
(Details in Implementation Plan.)

## 6) System Architecture (High Level)
KWin event-monitor.js → DBus → Daemon (ring buffer → features → rules → policy) → DBus signal → PySide6 overlay.

## 7) Interfaces & Contracts
DBus service `org.shortcutsage.Daemon` with `SendEvent(json)`, `Ping()`, and `Suggestions(json)` signal. Event & Suggestion JSON contracts as specified in Implementation Plan.

## 8) Config Schemas
`shortcuts.yaml` (authoritative actions map) and `rules.yaml` (contexts→suggestions) per Implementation Plan.

## 9–20
See Implementation Plan for detailed algorithm, UX, telemetry, performance, security, testing, packaging, milestones, risks, open questions, DoD, glossary.
