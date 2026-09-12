# Security requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Keep credentials and sensitive request content out of observability artifacts
:id: GOAL_DATA_SAFETY
:collapse: true

Debugging, recording, and error reporting must not expose provider credentials or sensitive request and tool contents.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Data safety idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_DATA_SAFETY
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Data safety from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_DATA_SAFETY' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Security executable behavior <living-specs-area-security>`

```{feature} Sensitive-data protection
:id: FEAT_SENSITIVE_DATA_PROTECTION
:collapse: true
:derives: GOAL_DATA_SAFETY

Runtime observability and recorded HTTP evidence are sanitized before they become durable artifacts.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_SENSITIVE_DATA_PROTECTION' in derives"
```

```{req} Sensitive observability artifacts exclude protected values
:id: REQ_SENSITIVE_DATA_PROTECTION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: bdd
:derives: FEAT_SENSITIVE_DATA_PROTECTION

**Statement.** Runtime diagnostics and recorded provider traffic shall not persist provider credentials, sensitive request content, or sensitive tool arguments.

**Rationale.** Logs, errors, and replay artifacts are routinely retained and shared during debugging, so sensitive values must not become durable merely because a request was observed or recorded.

**Verification intent.** Exercise public requests containing representative credentials and sensitive tool/request values, then inspect the resulting diagnostics and recorded evidence for both expected safe metadata and absence of the protected values.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_SENSITIVE_DATA_PROTECTION' in derives or 'REQ_SENSITIVE_DATA_PROTECTION' in implements or 'REQ_SENSITIVE_DATA_PROTECTION' in verifies"
```

::::

```{treq} Runtime diagnostics expose only safe metadata
:id: TREQ_RUNTIME_LOG_SAFETY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

**Statement.** Runtime logging and public tool failures shall use bounded safe metadata rather than credential values, request contents, or tool arguments.

**Rationale.** Runtime diagnostics must remain useful for failure analysis without converting exceptions or log records into a secondary channel for sensitive input.

**Verification intent.** Trigger representative runtime and tool failures through public behavior and verify that observable diagnostics contain the intended safe metadata while excluding protected values.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_RUNTIME_LOG_SAFETY' in derives or 'TREQ_RUNTIME_LOG_SAFETY' in implements or 'TREQ_RUNTIME_LOG_SAFETY' in verifies"
```

::::

```{treq} VCR recordings remove provider authentication
:id: TREQ_VCR_AUTH_REDACTION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: bdd
:derives: REQ_SENSITIVE_DATA_PROTECTION

**Statement.** Recorded provider interactions shall remove authentication headers and equivalent credential material before the cassette becomes durable evidence.

**Rationale.** Replay cassettes are source-controlled test evidence and therefore must be safe to retain independently of the credentials used during a live recording.

**Verification intent.** Record or synthesize provider interactions containing representative authentication material and verify the durable cassette preserves replay-relevant behavior without those protected values.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_VCR_AUTH_REDACTION' in derives or 'TREQ_VCR_AUTH_REDACTION' in implements or 'TREQ_VCR_AUTH_REDACTION' in verifies"
```

::::

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Tool orchestration <tools>` — tool arguments and public tool failures.
- {doc}`Provider portability <providers>` — provider credentials and recorded traffic.
- {doc}`Session continuity <sessions>` — sensitive conversation state.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
