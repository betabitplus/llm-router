# Configuration requirements

```{goal} Make effective request configuration predictable
:id: GOAL_CONFIGURATION_PREDICTABILITY

Callers must be able to understand which settings and credentials are effective without hidden precedence or stale cached configuration.
```

```{feature} Configuration precedence and validation
:id: FEAT_CONFIGURATION_PRECEDENCE
:derives: GOAL_CONFIGURATION_PREDICTABILITY

Router, route, request, credential, and installed configuration are resolved into one validated runtime view.
```

```{req} Request overrides preserve explicit intent
:id: REQ_REQUEST_OVERRIDE_PRECEDENCE
:status: accepted
:revision: 1
:required_evidence: impl;bdd;property
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Request-level settings shall override router and route defaults, while an explicitly supplied empty or null value shall remain distinguishable from an omitted override.

**Rationale.** Callers need predictable precedence and must be able to deliberately clear or null a value rather than have that intent mistaken for “use the default.”

**Verification intent.** Exercise the public configuration path with competing router, route, and request values, including explicit empty/null values, and use property-based coverage for combinations where omission and explicit values must remain distinct.
```

```{req} Invalid configuration fails through the public boundary
:id: REQ_INVALID_CONFIGURATION_ERRORS
:status: accepted
:revision: 1
:required_evidence: impl;bdd;unit
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Invalid provider, model, base-URL, timeout, and retry-policy configuration shall be rejected deterministically with public configuration errors before provider execution.

**Rationale.** Configuration defects should fail close to their source and through stable public error types instead of leaking into provider-specific execution failures.

**Verification intent.** Exercise representative invalid configuration through the public API and directly verify boundary validation rules that are cheaper and clearer to cover below the public scenario layer.
```

```{req} Credentials resolve deterministically
:id: REQ_CREDENTIAL_RESOLUTION
:status: accepted
:revision: 1
:required_evidence: impl;bdd;unit
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Configured fixed keys, custom environment names, optional credentials, and automatically rotated keys shall resolve deterministically. A missing required credential shall surface as the public missing-key error.

**Rationale.** Credential selection affects both correctness and provider availability; hidden precedence or stale selection would make requests difficult to reproduce and diagnose.

**Verification intent.** Exercise the public credential boundary for successful and missing-key cases and directly verify key-source precedence and rotation semantics across representative configurations.
```

```{req} Installed configuration invalidates dependent runtime caches
:id: REQ_CONFIG_INSTALLATION_COHERENCE
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Installing a new active configuration shall round-trip through the public configuration API and invalidate provider-adapter caches whose behavior depends on that configuration.

**Rationale.** A newly installed configuration is not effective if cached provider objects continue using values derived from the previous configuration.

**Verification intent.** Install configuration through the public API and verify both round-trip visibility and invalidation of configuration-dependent adapter caches.
```
