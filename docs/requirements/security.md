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
:revision: 1
:needs_artifacts: bdd
:derives: FEAT_SENSITIVE_DATA_PROTECTION

Runtime diagnostics and recorded provider traffic must not persist credentials, request contents, or sensitive tool arguments.
```

```{treq} Runtime diagnostics expose only safe metadata
:id: TREQ_RUNTIME_LOG_SAFETY
:revision: 1
:needs_artifacts: impl;bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

Runtime logging and public tool failures must use bounded metadata rather than credential values, request contents, or tool arguments.
```

```{treq} VCR recordings remove provider authentication
:id: TREQ_VCR_AUTH_REDACTION
:revision: 1
:needs_artifacts: bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

Recorded provider interactions must remove authentication headers and equivalent credential material before the cassette becomes durable evidence.
```
