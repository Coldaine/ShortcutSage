# Research Request: DBus Buffer Introspection Failures

## Context
- Repo: ShortcutSage (PySide6 overlay + DBus daemon for KDE shortcut suggestions)
- Current phase: PR-05 (overlay UI + CLI wiring).
- Recent changes added a CLI (`shortcut-sage daemon|overlay`) plus a convenience DBus method (`GetBufferState`) so tests can verify the daemon's in-memory ring buffer via integration tests (`tests/integration/test_dbus.py`).

## Problem Summary
When the integration suite calls `DBusClient.get_buffer_state()`, the DBus daemon crashes the method invocation with:
```
org.freedesktop.DBus.Python.AttributeError: 'RingBuffer' object has no attribute 'events'
```
Even after adding a compatibility `RingBuffer.events` property that returns `recent()`, the AttributeError persists in the DBus process. The daemon runs in a background `multiprocessing.Process` via `run_daemon`, so debugging cross-process attribute access is non-trivial. As long as this call fails, every integration test that inspects the buffer state (valid JSON, malformed JSON handling, Suggestions signal, etc.) fails.

Secondary issue: `tests/integration/test_dbus.py::test_dbus_error_handling` expects `DBusClient()` to raise when no daemon is running, but the new per-test daemon process keeps the bus name claimed, so the expectation never triggers.

## What We Need
1. **Examples/patterns for exposing internal state over DBus for tests**
   - How to safely surface transient in-memory data (like a ring buffer) without derailing DBus serialization? Examples from Python DBus services that expose structured data for test harnesses would help.
   - Best practices for marshalling custom Python objects over DBus: should we serialize in the daemon before returning (e.g., JSON) vs. rely on DBus auto-marshalling of dicts/lists? Any gotchas when the service runs inside a subprocess with its own event loop?

2. **Guidance on reliable DBus test harnesses**
   - Ways to start/stop a DBus service in pytest without leaking the well-known name between tests. Should we spin up a private session bus (e.g., via `dbus-run-session`) or mock DBus entirely for state checks?
   - Patterns for asserting "daemon not running" when the test suite itself is managing a child process.

3. **Concrete remediation ideas**
   - Examples/code snippets from other projects that implement a `GetBufferState`-style diagnostic method successfully.
   - Suggestions on alternative verification strategies (e.g., writing buffer snapshots to a temp file or exposing a UNIX socket) that keep the integration tests meaningful without needing DBus round-trips for diagnostics.

## Deliverable Expectations
Looking for referenced blog posts, OSS repos, or documentation that demonstrate:
- Python DBus services exposing structured data safely
- Testing patterns for DBus services with pytest (especially handling session bus isolation)
- Approaches for negative-path testing when the DBus name may already be claimed

The goal is to adopt one of these patterns to unblock the integration suite and finalize PR-05.
