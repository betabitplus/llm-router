# Configuration requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Make effective request configuration predictable
:id: GOAL_CONFIGURATION_PREDICTABILITY
:collapse: true

Callers must be able to understand which settings and credentials are effective without hidden precedence or stale cached configuration.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Configuration predictability idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_CONFIGURATION_PREDICTABILITY
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Configuration predictability from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_CONFIGURATION_PREDICTABILITY' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Configuration executable behavior <living-specs-area-configuration>`

```{feature} Configuration precedence and validation
:id: FEAT_CONFIGURATION_PRECEDENCE
:collapse: true
:derives: GOAL_CONFIGURATION_PREDICTABILITY

Router, route, request, credential, and installed configuration are resolved into one validated runtime view.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_CONFIGURATION_PRECEDENCE' in derives"
```

```{req} Request overrides preserve explicit intent
:id: REQ_REQUEST_OVERRIDE_PRECEDENCE
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd;property
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Request-level settings shall override router and route defaults, while an explicitly supplied empty or null value shall remain distinguishable from an omitted override.

**Rationale.** Callers need predictable precedence and must be able to deliberately clear or null a value rather than have that intent mistaken for “use the default.”

**Verification intent.** Exercise the public configuration path with competing router, route, and request values, including explicit empty/null values, and use property-based coverage for combinations where omission and explicit values must remain distinct.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_REQUEST_OVERRIDE_PRECEDENCE' in derives or 'REQ_REQUEST_OVERRIDE_PRECEDENCE' in implements or 'REQ_REQUEST_OVERRIDE_PRECEDENCE' in verifies"
```

::::

```{req} Invalid configuration fails through the public boundary
:id: REQ_INVALID_CONFIGURATION_ERRORS
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** llm-router shall reject an effective request configuration that violates an applicable configuration constraint with a public configuration error before initiating provider execution.

**Rationale.** Configuration defects should fail close to their source and through stable public error types instead of leaking into provider-specific execution failures.
```

::::{dropdown} Follow this contract to proof

{doc}`Verification profile → <../verification-profiles/invalid-configuration>`

```{needlist}
:filter: "'REQ_INVALID_CONFIGURATION_ERRORS' in derives or 'REQ_INVALID_CONFIGURATION_ERRORS' in implements or 'REQ_INVALID_CONFIGURATION_ERRORS' in verifies"
```

::::

### Derived configuration constraints

```{treq} Configured provider identity is internally consistent
:id: TREQ_CONFIG_PROVIDER_IDENTITY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl
:derives: REQ_INVALID_CONFIGURATION_ERRORS

**Statement.** Each configured provider entry shall identify the same provider as the key under which that entry is registered.

**Rationale.** A configuration that associates one provider key with another provider identity is ambiguous and cannot be executed deterministically.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_PROVIDER_IDENTITY' in derives or 'TREQ_CONFIG_PROVIDER_IDENTITY' in implements or 'TREQ_CONFIG_PROVIDER_IDENTITY' in verifies"
```

::::

```{treq} Requested model is declared by the effective configuration
:id: TREQ_CONFIG_MODEL_DECLARATION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl
:derives: REQ_INVALID_CONFIGURATION_ERRORS

**Statement.** A requested model shall be accepted only when it is declared by the effective configuration.

**Rationale.** Treating an undeclared model as executable would defer a configuration defect into provider-specific behavior.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_MODEL_DECLARATION' in derives or 'TREQ_CONFIG_MODEL_DECLARATION' in implements or 'TREQ_CONFIG_MODEL_DECLARATION' in verifies"
```

::::

```{treq} Required provider base URL is present
:id: TREQ_CONFIG_REQUIRED_BASE_URL
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl
:derives: REQ_INVALID_CONFIGURATION_ERRORS

**Statement.** When a configured provider requires an explicit base URL, the effective configuration shall provide one.

**Rationale.** A provider that requires an explicit endpoint cannot be addressed deterministically without that endpoint.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_REQUIRED_BASE_URL' in derives or 'TREQ_CONFIG_REQUIRED_BASE_URL' in implements or 'TREQ_CONFIG_REQUIRED_BASE_URL' in verifies"
```

::::

```{treq} Attempt timeout is positive
:id: TREQ_CONFIG_ATTEMPT_TIMEOUT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl
:derives: REQ_INVALID_CONFIGURATION_ERRORS

**Statement.** The effective attempt timeout shall be greater than zero.

**Rationale.** A zero or negative attempt interval cannot represent a meaningful wait budget for provider execution.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_ATTEMPT_TIMEOUT' in derives or 'TREQ_CONFIG_ATTEMPT_TIMEOUT' in implements or 'TREQ_CONFIG_ATTEMPT_TIMEOUT' in verifies"
```

::::

```{treq} Retry attempt limit is positive
:id: TREQ_CONFIG_RETRY_ATTEMPTS
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl
:derives: REQ_INVALID_CONFIGURATION_ERRORS

**Statement.** The effective retry maximum-attempt count shall be at least one.

**Rationale.** A retry policy with no permitted attempt cannot define executable retry behavior.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_RETRY_ATTEMPTS' in derives or 'TREQ_CONFIG_RETRY_ATTEMPTS' in implements or 'TREQ_CONFIG_RETRY_ATTEMPTS' in verifies"
```

::::

```{req} Credentials resolve deterministically
:id: REQ_CREDENTIAL_RESOLUTION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd;unit
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Configured fixed keys, custom environment names, optional credentials, and automatically rotated keys shall resolve deterministically. A missing required credential shall surface as the public missing-key error.

**Rationale.** Credential selection affects both correctness and provider availability; hidden precedence or stale selection would make requests difficult to reproduce and diagnose.

**Verification intent.** Exercise the public credential boundary for successful and missing-key cases and directly verify key-source precedence and rotation semantics across representative configurations.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_CREDENTIAL_RESOLUTION' in derives or 'REQ_CREDENTIAL_RESOLUTION' in implements or 'REQ_CREDENTIAL_RESOLUTION' in verifies"
```

::::

```{req} Installed configuration becomes effective coherently
:id: REQ_CONFIG_INSTALLATION_COHERENCE
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;unit
:derives: FEAT_CONFIGURATION_PRECEDENCE

**Statement.** Installing a new active configuration shall round-trip through the public configuration API and become the effective configuration for subsequent runtime behavior.

**Rationale.** A newly installed configuration is not effective if later requests continue to observe behavior derived from the previous configuration.

**Verification intent.** Install configuration through the public API and verify the active snapshot round-trips as the newly installed configuration. Configuration-dependent cache invalidation is verified by the derived technical requirement below.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_CONFIG_INSTALLATION_COHERENCE' in derives or 'REQ_CONFIG_INSTALLATION_COHERENCE' in implements or 'REQ_CONFIG_INSTALLATION_COHERENCE' in verifies"
```

::::

```{treq} Configuration-dependent caches are invalidated
:id: TREQ_CONFIG_CACHE_INVALIDATION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_CONFIG_INSTALLATION_COHERENCE

**Statement.** Installing a new active configuration shall invalidate provider-adapter caches whose behavior depends on configuration-derived values.

**Rationale.** Reusing provider objects created from an earlier configuration would make the public installation contract observe stale runtime behavior.

**Verification intent.** Directly install a replacement configuration and verify configuration-dependent adapter caches are invalidated before subsequent provider use.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_CONFIG_CACHE_INVALIDATION' in derives or 'TREQ_CONFIG_CACHE_INVALIDATION' in implements or 'TREQ_CONFIG_CACHE_INVALIDATION' in verifies"
```

::::

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Routing reliability <routing>` — how effective policy changes route choice.
- {doc}`Provider portability <providers>` — provider objects and credentials affected by configuration.
- {doc}`Developer usability <developer>` — the public configuration surface callers consume.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
