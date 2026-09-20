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

**Verification intent.** Prove the public save/load contract across conversation state and
supported embedded media. Low-level media encoding and serialization-version compatibility
are owned by the derived {need}`TREQ_SESSION_SERIALIZATION`.

**Models:** {ref}`Session persistence <test-plan-session-persistence-model>`

### Required coverage

| Test level            | Boundary | Representation | M&S target |          Target |
| --------------------- | -------- | -------------- | ---------- | --------------: |
| Component             | Local    | Actual         | —          | **1 criterion** |
| Component Integration | Local    | Actual         | —          |  **2 criteria** |

**Coverage basis.** The public Requirement owns three observable persistence claims: generated
conversation state round-trips exactly, public Session save/load preserves the observable
system instruction and history, and the same public path preserves each supported embedded
media partition. The derived TREQ separately verifies serializer encoding and version
compatibility; those technical criteria are not counted as REQ evidence.

**Representation basis.** Both direct paths execute the actual Session/SessionStore
implementation against local serialized state. No external dependency or surrogate is part
of the public persistence claim.

### Verification criteria

| Criterion                                | Contract                                 | Test level            | Boundary | Required paths | Required path IDs                                 | Success criterion                                                                                                   |
| ---------------------------------------- | ---------------------------------------- | --------------------- | -------- | -------------: | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `VC_SESSION_PERSISTENCE_GENERATED_STATE` | {need}`[[id]] <REQ_SESSION_PERSISTENCE>` | Component             | Local    |              1 | —                                                 | Generated turn sequences round-trip system prompt, user/assistant text, order, and metadata exactly.                |
| `VC_SESSION_PUBLIC_PERSISTENCE`          | {need}`[[id]] <REQ_SESSION_PERSISTENCE>` | Component Integration | Local    |              1 | —                                                 | Public Session.save/load preserves the observable system instruction and conversation history exactly.              |
| `VC_SESSION_PUBLIC_MEDIA_PERSISTENCE`    | {need}`[[id]] <REQ_SESSION_PERSISTENCE>` | Component Integration | Local    |              4 | `file` · `image` · `local-video` · `remote-video` | Public Session.save/load preserves each supported embedded-media form through the complete public persistence path. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Required technical support

| Technical requirement                                                                | Target |
| ------------------------------------------------------------------------------------ | ------ |
| {need}`Session serialization rejects incompatible data <TREQ_SESSION_SERIALIZATION>` | PASS   |

### Fault applicability

| REQUIRED                                                              | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                      |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Public save/load control flow must restore the intended state; serializer encoding/version mechanics belong to the derived TREQ.                         |
| Runtime / dependency  | Persistence is local state behavior and does not depend on a live external dependency.                                                                   |
| Interface / protocol  | Serialized payload/schema compatibility is owned by the technical serialization contract, not by this public Requirement.                                |
| Architecture          | The Requirement constrains observable restored state rather than internal package-layer topology.                                                        |
| Specification / model | Wrong restored values or an omitted public state/media partition directly violate persistence semantics; serializer/version mechanics remain TREQ-owned. |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.

(verification-profile-treq-session-serialization)=

## Profile · TREQ_SESSION_SERIALIZATION

**Verification intent.** Prove the low-level serialized representation preserves each
supported embedded-media form and rejects incompatible serialization versions instead of
silently loading them.

**Models:** {ref}`Session persistence <test-plan-session-persistence-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **2 criteria** |

**Coverage basis.** The technical contract has two independent compatibility obligations:
all four supported embedded-media partitions survive save/load, and an unsupported
serialization version is rejected explicitly.

**Representation basis.** Tests execute the actual SessionStore serializer/deserializer with
real temporary files and in-memory media objects. No external model or dependency substitute
is involved.

### Verification criteria

| Criterion                                    | Contract                                    | Test level | Boundary | Required paths | Required path IDs                                 | Success criterion                                                                                                            |
| -------------------------------------------- | ------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `VC_SESSION_SERIALIZATION_MEDIA`             | {need}`[[id]] <TREQ_SESSION_SERIALIZATION>` | Component  | Local    |              4 | `file` · `image` · `local-video` · `remote-video` | File bytes, image bytes, local-video bytes/descriptor metadata, and remote-video descriptor metadata each survive save/load. |
| `VC_SESSION_SERIALIZATION_VERSION_REJECTION` | {need}`[[id]] <TREQ_SESSION_SERIALIZATION>` | Component  | Local    |              1 | —                                                 | Unsupported serialization versions raise SessionSerializationError instead of loading incompatible state.                    |

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

| REQUIRED                                                                                                                                 | OPTIONAL | N/A                                                                                                                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Version comparisons, type/shape branches, and encode/decode boundaries directly implement compatibility behavior.                |
| Runtime / dependency  | Serialization is a local compatibility boundary and has no live dependency failure mode.                                         |
| Interface / protocol  | The persisted JSON/media representation is the technical payload schema; incompatible shapes must not be silently accepted.      |
| Architecture          | No package-layer edge is normative for the serializer contract.                                                                  |
| Specification / model | Missing media partitions, corrupted round-trip values, or accepting an unsupported version directly violate the technical claim. |

No blocking mutation threshold is selected; deterministic technical fault obligations remain
blocking.
