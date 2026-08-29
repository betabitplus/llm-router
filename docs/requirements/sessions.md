# Session requirements

```{goal} Preserve conversational state without cross-request contamination
:id: GOAL_SESSION_CONTINUITY

Callers must be able to remember, fork, persist, clear, and concurrently use sessions while retaining explicit control over history.
```

```{feature} Session lifecycle
:id: FEAT_SESSION_LIFECYCLE
:derives: GOAL_SESSION_CONTINUITY

A session owns conversation history and exposes explicit lifecycle operations without changing the router contract.
```

```{req} Session history remains explicit and isolated
:id: REQ_SESSION_LIFECYCLE
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_SESSION_LIFECYCLE

Remembered turns must be available to later requests, history may be ignored for one request, forks must diverge independently, clearing must leave the session reusable, and concurrent requests must not mix session state.
```

```{req} Session persistence round-trips state
:id: REQ_SESSION_PERSISTENCE
:revision: 1
:needs_artifacts: impl;bdd;property
:derives: FEAT_SESSION_LIFECYCLE

Saving and loading a session must preserve its system prompt, history, generated text, metadata, and supported embedded media across the serialized representation.
```

```{treq} Session serialization rejects incompatible data
:id: TREQ_SESSION_SERIALIZATION
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_SESSION_PERSISTENCE

Session serialization must preserve supported embedded media bytes and reject unsupported serialization versions rather than loading incompatible state.
```
