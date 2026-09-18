(verification-profiles-tools)=

# Verification profiles · Tool orchestration

These profiles own verification design for the parent contracts in
{need}`GOAL_TOOL_ORCHESTRATION`. Product semantics remain in the normative
Requirements and Technical requirements; each profile declares the exact
verification cells, semantic criteria, and retained-path cardinality required for
the current assurance result.

(verification-profile-req-tool-choice)=

## Profile · REQ_TOOL_CHOICE

**Verification intent.** Prove explicit named-tool selection across every provider-adapter family
that declares tool support. Existing replay evidence covers OpenAI-compatible, QwenChat,
Gemini WebAPI, and AI Studio; Google GenAI is exercised through a deterministic local
provider boundary so its native named-tool configuration can be inspected directly.

**Models:** {ref}`Tool selection <test-plan-tool-selection-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          |  **2 criteria** |
| System Integration | Replay     | Surrogate      | L0         | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Component coverage requires both supported public named-choice input forms
(string name and mapping form) to normalize to the same selected tool, plus one retained named-string
serialization path for each distinct provider translation implementation: shared OpenAI-compatible/
AI Studio, QwenChat, Google GenAI, and Gemini WebAPI prompt translation. The Replay cell requires
four retained adapter-family raw-choice paths: OpenAI-compatible, QwenChat, Gemini WebAPI, and AI
Studio. The Substitute cell requires the Google GenAI raw-choice path. Together the provider-facing
paths still cover every adapter that currently declares `supports_tools=True` without duplicating
the shared AI Studio/OpenAI serializer branch.

**Representation basis.** Replay paths execute actual llm-router/provider-adapter code
against retained provider interactions. The Google GenAI path executes actual llm-router
and SDK code against a scripted local provider boundary. These are surrogate external
participants; L0 is sufficient because the claim is the request/tool selection emitted by
llm-router plus the observed tool trace, not fidelity of provider reasoning.

### Verification criteria

| Criterion                          | Contract                         | Test level         | Boundary   | Required paths | Success criterion                                                                                                      |
| ---------------------------------- | -------------------------------- | ------------------ | ---------- | -------------: | ---------------------------------------------------------------------------------------------------------------------- |
| `VC_TOOL_CHOICE_NAMED_INPUT_FORMS` | {need}`[[id]] <REQ_TOOL_CHOICE>` | Component          | Local      |              2 | Both supported public named-choice input forms normalize to the same selected registered tool.                         |
| `VC_TOOL_CHOICE_NAMED_SERIALIZERS` | {need}`[[id]] <REQ_TOOL_CHOICE>` | Component          | Local      |              4 | Each distinct provider translation implementation preserves the selected named tool in its native request/prompt form. |
| `VC_TOOL_CHOICE_REPLAY_FAMILIES`   | {need}`[[id]] <REQ_TOOL_CHOICE>` | System Integration | Replay     |              4 | All four replay-backed adapter families honor the explicit named tool and execute no alternate registered tool.        |
| `VC_TOOL_CHOICE_GOOGLE_GENAI`      | {need}`[[id]] <REQ_TOOL_CHOICE>` | System Integration | Substitute |              1 | Google GenAI emits native configuration restricted to the named tool and the runtime trace contains only that tool.    |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                               |
| ----------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow`                             | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `interface.payload-schema`                      | —        | `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass`       |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `spec.wrong-ordering-boundary`                                                                                                    |

#### Fault-group rationale

| Group                 | Why                                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Named-choice control flow must not fall through to auto/alternate selection.                                                      |
| Runtime / dependency  | Provider availability and latency do not determine whether llm-router emitted the caller-selected tool choice.                    |
| Interface / protocol  | Each provider-native request must encode the selected tool correctly; unrelated provider status/failure behavior is out of scope. |
| Architecture          | This Requirement does not prescribe an internal layering path for tool-choice normalization.                                      |
| Specification / model | Wrong selected tool and missing provider-family partitions directly invalidate the explicit-choice contract.                      |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-multi-round-tool-execution)=

## Profile · REQ_MULTI_ROUND_TOOL_EXECUTION

**Verification intent.** Prove the internal registry contracts required to execute tools,
then prove provider-facing multi-round workflows across every provider-adapter family that
currently declares tool support. The workflow must feed tool results back into subsequent
provider turns and terminate with the expected final structured response.

**Models:** {ref}`Tool execution <test-plan-tool-execution-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          |  **3 criteria** |
| System Integration | Replay     | Surrogate      | L0         | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Component coverage owns the derived ToolRegistry semantics.
Replay coverage requires QwenChat, AI Studio, Gemini WebAPI, and Google GenAI retained
workflows. The Substitute cell requires an OpenAI-compatible local-boundary workflow and
also proves that the first tool result is returned to the second provider turn and both
tool results are returned before the final turn.

**Representation basis.** Component paths execute the actual ToolRegistry. Replay and
Substitute paths execute actual llm-router/provider-adapter code but use retained or
scripted external participants; they therefore remain Surrogate at L0.

### Verification criteria

| Criterion                              | Contract                                        | Test level         | Boundary   | Required paths | Success criterion                                                                                                    |
| -------------------------------------- | ----------------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------- |
| `VC_TOOL_REGISTRY_SCHEMA_EXECUTION`    | {need}`[[id]] <TREQ_TOOL_REGISTRY>`             | Component          | Local      |              1 | Callable schema derivation matches the Python signature and execution preserves arguments/results.                   |
| `VC_TOOL_REGISTRY_DUPLICATE_REJECTION` | {need}`[[id]] <TREQ_TOOL_REGISTRY>`             | Component          | Local      |              1 | Duplicate tool names are rejected deterministically.                                                                 |
| `VC_TOOL_REGISTRY_CALL_SHAPES`         | {need}`[[id]] <TREQ_TOOL_REGISTRY>`             | Component          | Local      |              2 | Both retained supported provider tool-call shapes normalize into the same callable contract.                         |
| `VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES`  | {need}`[[id]] <REQ_MULTI_ROUND_TOOL_EXECUTION>` | System Integration | Replay     |              4 | QwenChat, AI Studio, Gemini WebAPI, and Google GenAI complete their retained multi-round workflows with tool traces. |
| `VC_TOOL_MULTI_ROUND_OPENAI_LOCAL`     | {need}`[[id]] <REQ_MULTI_ROUND_TOOL_EXECUTION>` | System Integration | Substitute |              1 | OpenAI-compatible executes add then multiply, round-trips each tool result, and terminates with final result 84.     |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                       | OPTIONAL | N/A                                                                                                                               |
| -------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `interface.unexpected-interaction`                          | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.error-status` · `architecture.forbidden-edge`                                                                          |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Multi-round execution is a state machine; skipping or terminating a branch can lose a required tool round or final response.                           |
| Runtime / dependency  | Availability/timeout recovery belongs to provider retry/routing contracts rather than the semantic tool-result round trip.                             |
| Interface / protocol  | Tool results must be returned in the next provider turn with the expected shape and without an extra/unaccounted turn in the required workflow.        |
| Architecture          | Provider tool calls must pass through the required ToolRegistry normalization/execution boundary before results are returned to the provider.          |
| Specification / model | Required provider-family partitions, add→multiply ordering, intermediate-result propagation, and final outcome are all part of the normative behavior. |

No blocking mutation threshold is selected here. The retained mutmut Test Strength for {need}`TREQ_TOOL_REGISTRY`
remains diagnostic under the project Test Plan; required deterministic fault classes above are blocking.

(verification-profile-req-tool-runtime-safety)=

## Profile · REQ_TOOL_RUNTIME_SAFETY

**Verification intent.** Exercise the public orchestration boundary against a failing local
tool and an overlong tool-request loop. Prove stable public error translation, absence of
additional provider execution after the failure, and termination at the configured round
limit while preserving the outstanding tool call.

**Models:** {ref}`Tool execution <test-plan-tool-execution-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** One criterion owns public local-tool failure behavior and one owns the
configured round-limit boundary.

**Representation basis.** Both paths execute actual llm-router orchestration while a
scripted provider participant drives deterministic tool requests, so the external
participant remains Surrogate at L0.

### Verification criteria

| Criterion                      | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                          |
| ------------------------------ | ---------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_TOOL_RUNTIME_PUBLIC_ERROR` | {need}`[[id]] <REQ_TOOL_RUNTIME_SAFETY>` | System Integration | Substitute |              1 | A local tool failure surfaces through the public tool-execution error without a further provider turn or sensitive values. |
| `VC_TOOL_RUNTIME_ROUND_LIMIT`  | {need}`[[id]] <REQ_TOOL_RUNTIME_SAFETY>` | System Integration | Substitute |              1 | Tool execution stops at the configured round limit and preserves the outstanding tool call in the public response.         |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                              | OPTIONAL | N/A                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                                                             | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                         |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The round-limit comparison/boundary and failure control flow are the implementation mechanisms that enforce bounded execution.     |
| Runtime / dependency  | Provider timeout/unavailability/malformed-reply recovery is owned by resilience/provider contracts, not local tool failure safety. |
| Interface / protocol  | A further provider turn after local failure or limit exhaustion is explicitly forbidden; provider response schema/status is not.   |
| Architecture          | This contract constrains observable safety behavior rather than a particular internal layering topology.                           |
| Specification / model | Failure vs limit partitions, termination ordering, preserved outstanding call, and public error outcome are normative semantics.   |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.
