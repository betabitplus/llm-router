# Security requirements

```{goal} Keep credentials and sensitive request content out of observability artifacts
:id: GOAL_DATA_SAFETY

Debugging, recording, and error reporting must not expose provider credentials or sensitive request and tool contents.
```

```{feature} Sensitive-data protection
:id: FEAT_SENSITIVE_DATA_PROTECTION
:derives: GOAL_DATA_SAFETY

Runtime observability and recorded HTTP evidence are sanitized before they become durable artifacts.
```

```{req} Sensitive observability artifacts exclude protected values
:id: REQ_SENSITIVE_DATA_PROTECTION
:status: accepted
:revision: 1
:required_evidence: bdd
:derives: FEAT_SENSITIVE_DATA_PROTECTION

**Statement.** Runtime diagnostics and recorded provider traffic shall not persist provider credentials, sensitive request content, or sensitive tool arguments.

**Rationale.** Logs, errors, and replay artifacts are routinely retained and shared during debugging, so sensitive values must not become durable merely because a request was observed or recorded.

**Verification intent.** Exercise public requests containing representative credentials and sensitive tool/request values, then inspect the resulting diagnostics and recorded evidence for both expected safe metadata and absence of the protected values.
```

```{treq} Runtime diagnostics expose only safe metadata
:id: TREQ_RUNTIME_LOG_SAFETY
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

**Constraint.** Runtime logging and public tool failures shall use bounded safe metadata rather than credential values, request contents, or tool arguments.

**Rationale.** Runtime diagnostics must remain useful for failure analysis without converting exceptions or log records into a secondary channel for sensitive input.

**Verification intent.** Trigger representative runtime and tool failures through public behavior and verify that observable diagnostics contain the intended safe metadata while excluding protected values.
```

```{treq} VCR recordings remove provider authentication
:id: TREQ_VCR_AUTH_REDACTION
:status: accepted
:revision: 1
:required_evidence: bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

**Constraint.** Recorded provider interactions shall remove authentication headers and equivalent credential material before the cassette becomes durable evidence.

**Rationale.** Replay cassettes are source-controlled test evidence and therefore must be safe to retain independently of the credentials used during a live recording.

**Verification intent.** Record or synthesize provider interactions containing representative authentication material and verify the durable cassette preserves replay-relevant behavior without those protected values.
```
