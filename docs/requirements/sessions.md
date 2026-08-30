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
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_SESSION_LIFECYCLE

**Statement.** Remembered turns shall be available to later requests; a caller shall be able to ignore history for one request; forks shall diverge independently; clearing shall leave the session reusable; and concurrent requests shall not mix session state.

**Rationale.** Conversation history is useful only when its inclusion and lifecycle remain explicit; accidental sharing or irreversible mutation would make session behavior unsafe and difficult to reason about.

**Verification intent.** Exercise the public session API across remembering, one-shot history suppression, forking, clearing, reuse, and concurrent requests, and verify the observable histories remain independent where required.
```

```{req} Session persistence round-trips state
:id: REQ_SESSION_PERSISTENCE
:status: accepted
:revision: 1
:required_evidence: impl;bdd;property
:derives: FEAT_SESSION_LIFECYCLE

**Statement.** Saving and loading a session shall preserve its system prompt, conversation history, generated text, metadata, and supported embedded media across the serialized representation.

**Rationale.** Persisted sessions are useful only if restoring them preserves the conversation semantics needed for subsequent requests.

**Verification intent.** Save and restore representative sessions through the public lifecycle and use property-based coverage to verify supported state round-trips across varied content and metadata.
```

```{treq} Session serialization rejects incompatible data
:id: TREQ_SESSION_SERIALIZATION
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_SESSION_PERSISTENCE

**Constraint.** Session serialization shall preserve supported embedded media bytes and reject unsupported serialization versions rather than loading incompatible state.

**Rationale.** Binary media and versioned serialized data are low-level compatibility boundaries where silent coercion or best-effort loading could corrupt restored session state.

**Verification intent.** Directly verify supported media serialization and explicit rejection of unsupported serialized versions.
```
