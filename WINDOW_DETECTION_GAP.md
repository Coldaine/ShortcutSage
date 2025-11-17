# Window Detection Testing Analysis

**Question**: How is window detection tested?

**Answer**: **It's NOT fully tested** - this is a gap in test coverage.

---

## What EXISTS (Infrastructure)

### 1. **KWin Captures Window Metadata**

From `kwin/event-monitor.js`:
```javascript
// Window focus events
workspace.clientActivated.connect(function(client) {
    if (client) {
        sendEvent("window_focus", "window_focus", {
            window: client.caption,        // ← Window title: "Firefox", "Terminal"
            app: client.resourceClass      // ← App class: "firefox", "konsole"
        });
    }
});

// Desktop switch events
workspace.clientDesktopChanged.connect(function(client, desktop) {
    sendEvent("desktop_switch", "switch_desktop", {
        window: client ? client.caption : "unknown",
        desktop: desktop                   // ← Desktop number
    });
});

// Window state changes
workspace.clientStepUserMovedResized.connect(function(client, step) {
    sendEvent("window_state", action, {
        window: client.caption,
        maximized: client.maximizedHorizontally && client.maximizedVertically
    });
});
```

**Conclusion**: KWin DOES capture window information.

---

### 2. **Events Can Store Metadata**

From `sage/events.py`:
```python
@dataclass(frozen=True)
class Event:
    timestamp: datetime
    type: EventType
    action: str
    metadata: dict[str, str] | None = None  # ← Window info goes here
```

**Conclusion**: Events CAN store window metadata.

---

### 3. **Context Types Defined**

From `sage/models.py`:
```python
class ContextMatch(BaseModel):
    type: Literal["event_sequence", "recent_window", "desktop_state"]
    pattern: str | list[str]
    window: int = Field(default=3, ...)
```

**Conclusion**: Schema supports window-based matching.

---

## What's MISSING (Not Implemented/Tested)

### 1. **Feature Extractor Doesn't Extract Metadata**

From `sage/features.py` (the FULL file):
```python
class FeatureExtractor:
    """Extract context features from event buffer."""

    def __init__(self, buffer: RingBuffer):
        self.buffer = buffer

    def extract(self) -> dict[str, Any]:
        """Extract features from recent events."""
        recent = self.buffer.recent()

        return {
            "recent_actions": [e.action for e in recent],
            "event_count": len(recent),
            "last_action": recent[-1].action if recent else None,
            "action_sequence": " ".join(e.action for e in recent),
        }
```

**Notice what's MISSING**:
- ❌ No extraction of `event.metadata`
- ❌ No extraction of window titles
- ❌ No extraction of app names
- ❌ No extraction of desktop numbers

**Conclusion**: Metadata is captured but NOT used.

---

### 2. **Matcher Has Stub Implementations**

From `sage/matcher.py`:
```python
def _match_recent_window(self, pattern: str | list[str], features: dict[str, Any]) -> bool:
    """Match recent window pattern (stub for MVP)."""
    # MVP: Same as event_sequence
    return self._match_event_sequence(pattern, features)

def _match_desktop_state(self, pattern: str | list[str], features: dict[str, Any]) -> bool:
    """Match desktop state pattern (stub for MVP)."""
    # MVP: Same as event_sequence
    return self._match_event_sequence(pattern, features)
```

**Notice**:
- Methods exist but are **stubs labeled "MVP"**
- Both just call `_match_event_sequence()` (ignore window info)
- No actual window title or app matching

**Conclusion**: Window matching is planned but not implemented.

---

### 3. **Tests Don't Validate Metadata**

From `tests/integration/test_dbus.py`:
```python
def test_send_event_valid_json(...):
    event_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "window_focus",
        "action": "show_desktop",
        "metadata": {},  # ← Empty metadata!
    }
    dbus_client.send_event(event_data)
    # ...
```

**All tests use empty metadata**: `"metadata": {}`

**No tests exist for**:
- ❌ Validating metadata is stored in events
- ❌ Validating metadata is extracted by FeatureExtractor
- ❌ Validating window-specific rule matching
- ❌ End-to-end window detection flow

**Conclusion**: Window detection is NOT tested.

---

## The Testing Gap

### What SHOULD be tested (but isn't):

```python
# Test that metadata is captured and stored
def test_event_stores_window_metadata():
    event = Event(
        timestamp=datetime.now(),
        type="window_focus",
        action="window_focus",
        metadata={"window": "Firefox", "app": "firefox"}
    )

    buffer.add(event)
    assert buffer.recent()[0].metadata["window"] == "Firefox"
    assert buffer.recent()[0].metadata["app"] == "firefox"


# Test that features include window info
def test_extractor_includes_window_metadata():
    buffer.add(Event(
        timestamp=datetime.now(),
        type="window_focus",
        action="focus",
        metadata={"window": "Terminal", "app": "konsole"}
    ))

    features = extractor.extract()
    assert features["recent_windows"] == ["Terminal"]  # ← Doesn't exist!
    assert features["recent_apps"] == ["konsole"]      # ← Doesn't exist!


# Test window-specific suggestions
def test_window_specific_suggestion():
    # Rule: When Firefox is focused, suggest browser shortcuts
    rule = Rule(
        name="firefox_shortcuts",
        context=ContextMatch(
            type="recent_window",
            pattern=["Firefox"]  # ← Match window title
        ),
        suggest=[Suggestion(action="new_tab", priority=80)]
    )

    # Simulate Firefox focus
    buffer.add(Event(
        timestamp=datetime.now(),
        type="window_focus",
        action="focus",
        metadata={"window": "Firefox", "app": "firefox"}
    ))

    features = extractor.extract()
    matches = matcher.match(features)

    assert len(matches) > 0  # ← Would currently FAIL!
    assert matches[0][1].action == "new_tab"
```

---

## Why This Gap Exists

Looking at the codebase, this is **intentional MVP scoping**:

1. **Phase 1 (Current)**: Event sequence matching only
   - Test: "After show_desktop, suggest overview"
   - Works with: Action sequences (no metadata needed)

2. **Phase 2 (Future)**: Window-aware suggestions
   - Planned: "When Firefox is focused, suggest browser shortcuts"
   - Requires: Metadata extraction + window matching

The code comments say **"stub for MVP"** - this feature is planned but not yet implemented.

---

## How to Prove This Gap

Run this test and watch it fail:

```python
from datetime import datetime
from sage.buffer import RingBuffer
from sage.events import Event
from sage.features import FeatureExtractor

# Add event with window metadata
buffer = RingBuffer()
buffer.add(Event(
    timestamp=datetime.now(),
    type="window_focus",
    action="focus",
    metadata={"window": "Firefox", "app": "firefox"}
))

# Try to extract window features
extractor = FeatureExtractor(buffer)
features = extractor.extract()

print("Features extracted:", features.keys())
# Output: dict_keys(['recent_actions', 'event_count', 'last_action', 'action_sequence'])
# Notice: NO 'recent_windows', NO 'recent_apps', NO metadata

print("Metadata from event:", buffer.recent()[0].metadata)
# Output: {'window': 'Firefox', 'app': 'firefox'}
# ✅ Metadata IS stored in event

print("Does extractor use it?", 'recent_windows' in features)
# Output: False
# ❌ But extractor doesn't expose it
```

---

## Summary

### ✅ What IS Tested:
1. **Event storage**: Events are stored in RingBuffer
2. **Action extraction**: Recent actions are extracted
3. **Action-based matching**: Rules match based on action sequences
4. **Full pipeline**: Event → Features → Matching → Policy

### ❌ What is NOT Tested:
1. **Metadata storage validation**: No test verifies metadata is preserved
2. **Window feature extraction**: FeatureExtractor doesn't extract window info
3. **Window-based matching**: Matcher stubs don't use window patterns
4. **App-specific suggestions**: No end-to-end test for window-aware rules

### 📋 Current State:
- **Infrastructure exists**: KWin captures it, Events store it
- **Feature not implemented**: Extractor and Matcher don't use it
- **Tests accurately reflect reality**: Tests pass because they only test what's implemented (action sequences)

---

## The Answer

**Window detection is captured but not tested or used** because:

1. KWin **DOES** capture window titles and app names
2. Events **CAN** store this in metadata field
3. But FeatureExtractor **DOESN'T** extract it
4. And RuleMatcher **DOESN'T** use it for matching
5. So tests **DON'T** validate it (correctly - since it's not implemented)

This is an **intentional MVP limitation**, not a test gap. The tests are honest - they test what's implemented (action sequences), not what's planned (window matching).

---

## What This Means for "Real Testing"

This is actually **good testing practice**:
- ✅ Tests validate implemented features only
- ✅ Stubs are clearly labeled ("MVP")
- ✅ No false positives (tests don't pretend feature works)

But it also shows:
- ⚠️  Window-specific suggestions are **not yet functional**
- ⚠️  Tests would **fail** if you tried to use window patterns
- ⚠️  This feature is **planned for later phase**

**The tests are real - they just test a smaller scope than you might expect.**
