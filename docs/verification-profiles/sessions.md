(verification-profiles-sessions)=

# Verification profiles · Session continuity

These profiles own verification design for {need}`GOAL_SESSION_CONTINUITY`.
Normative session semantics remain in Requirements; the profile defines the retained
partitions needed to prove lifecycle isolation and persistence without inferring Actual
from Target.

(verification-profile-req-session-lifecycle)=

## Profile · REQ_SESSION_LIFECYCLE

**Verification intent.** Prove every public lifecycle operation that can change or
select conversation history: include history, suppress it for one request, fork,
clear/reuse, and concurrent isolation.

**Models:** {ref}`Session lifecycle <test-plan-session-lifecycle-model>`

### Required coverage

| Test level            | Boundary | Representation | M&S target |          Target |
| --------------------- | -------- | -------------- | ---------- | --------------: |
| Component Integration | Local    | Actual         | —          |  **4 criteria** |
| System                | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Local public-session behavior requires four independent partitions:
history inclusion, one-shot history suppression, fork divergence, and clear/reuse.
Concurrency is a separate public-router criterion because it must prove two simultaneous
requests preserve both session and routing isolation.

**Representation basis.** All lifecycle paths execute the actual Session/runtime
implementation. No external dependency representation is needed for the contract.

### Verification criteria

| Criterion                         | Contract                               | Test level            | Boundary | Required paths | Success criterion                                                                                   |
| --------------------------------- | -------------------------------------- | --------------------- | -------- | -------------: | --------------------------------------------------------------------------------------------------- |
| `VC_SESSION_HISTORY_INCLUDED`     | {need}`[[id]] <REQ_SESSION_LIFECYCLE>` | Component Integration | Local    |              1 | Remembered user/assistant turns precede the new message in the expected order.                      |
| `VC_SESSION_HISTORY_SUPPRESSED`   | {need}`[[id]] <REQ_SESSION_LIFECYCLE>` | Component Integration | Local    |              1 | One request can exclude prior history while retaining the system instruction and current user turn. |
| `VC_SESSION_FORK_ISOLATION`       | {need}`[[id]] <REQ_SESSION_LIFECYCLE>` | Component Integration | Local    |              1 | Extending a fork changes only the fork; the source session remains unchanged.                       |
| `VC_SESSION_CLEAR_REUSE`          | {need}`[[id]] <REQ_SESSION_LIFECYCLE>` | Component Integration | Local    |              1 | Clearing removes history and the same session can immediately accept a new turn.                    |
| `VC_SESSION_CONCURRENT_ISOLATION` | {need}`[[id]] <REQ_SESSION_LIFECYCLE>` | System                | Local    |              1 | Two concurrent requests retain distinct histories and independent successful routing traces.        |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                               | OPTIONAL        | N/A                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------ | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.boundary` | `impl.comparison` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Lifecycle branch/control flow selects whether and where history is copied or cleared; numeric comparison is not central. |
| Runtime / dependency  | The contract is local state semantics rather than dependency availability.                                               |
| Interface / protocol  | No external protocol is part of session lifecycle behavior.                                                              |
| Architecture          | The public state semantics do not prescribe an internal module graph.                                                    |
| Specification / model | Wrong history, a missing lifecycle partition, or wrong before/after ordering directly violates the Requirement.          |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-session-persistence)=

## Profile · REQ_SESSION_PERSISTENCE

**Verification intent.** Prove the public save/load path plus generated text/metadata,
supported embedded media, and explicit incompatible-version rejection.

**Models:** {ref}`Session persistence <test-plan-session-persistence-model>`

### Required coverage

| Test level            | Boundary | Representation | M&S target |          Target |
| --------------------- | -------- | -------------- | ---------- | --------------: |
| Component             | Local    | Actual         | —          |  **3 criteria** |
| Component Integration | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** The parent Requirement needs one public Session round-trip and one
generated-state property. The derived serialization contract adds four explicit media
partitions — file bytes, image bytes, local-video bytes/descriptor metadata, and
remote-video descriptor metadata — plus incompatible-version rejection.

**Representation basis.** Persistence is a local serialized-state boundary. All paths
execute the actual SessionStore/Session serializer; no external surrogate is involved.

### Verification criteria

| Criterion                                    | Contract                                    | Test level            | Boundary | Required paths | Required path IDs                                 | Success criterion                                                                                                            |
| -------------------------------------------- | ------------------------------------------- | --------------------- | -------- | -------------: | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `VC_SESSION_PERSISTENCE_GENERATED_STATE`     | {need}`[[id]] <REQ_SESSION_PERSISTENCE>`    | Component             | Local    |              1 | —                                                 | Generated turn sequences round-trip system prompt, user/assistant text, order, and metadata exactly.                         |
| `VC_SESSION_SERIALIZATION_MEDIA`             | {need}`[[id]] <TREQ_SESSION_SERIALIZATION>` | Component             | Local    |              4 | `file` · `image` · `local-video` · `remote-video` | File bytes, image bytes, local-video bytes/descriptor metadata, and remote-video descriptor metadata each survive save/load. |
| `VC_SESSION_SERIALIZATION_VERSION_REJECTION` | {need}`[[id]] <TREQ_SESSION_SERIALIZATION>` | Component             | Local    |              1 | —                                                 | Unsupported serialization versions raise SessionSerializationError instead of loading state.                                 |
| `VC_SESSION_PUBLIC_PERSISTENCE`              | {need}`[[id]] <REQ_SESSION_PERSISTENCE>`    | Component Integration | Local    |              1 | —                                                 | Public Session.save/load preserves the observable system instruction and conversation history.                               |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                                              | OPTIONAL          | N/A                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `impl.boundary` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.comparison` | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Serialization control flow and version boundary decide compatible state; ordinary comparisons are secondary.       |
| Runtime / dependency  | Persistence uses local state/files rather than a live dependency.                                                  |
| Interface / protocol  | The serialized payload shape is a compatibility boundary; HTTP-style interaction/status faults are not applicable. |
| Architecture          | The contract constrains restored semantics, not serializer module placement.                                       |
| Specification / model | Wrong values, omitted state/media partitions, or reordered history violate round-trip semantics.                   |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
