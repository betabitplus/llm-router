(test-plan)=

# Test plan

## Project decisions

| Decision                       |                                  Value | Effect                                                                                                                                                                  |
| ------------------------------ | -------------------------------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Evidence freshness             |            **relevant inputs current** | retained evidence is valid only while its own code/test/profile/Gherkin/harness inputs still match; stale required evidence must be revalidated                         |
| Implementation fault detection |          **every valid mutant caught** | an Implementation class is caught only when each valid, unsuppressed mutant of that class in the contract's attributable code fails one of the contract's passing tests |
| Mutation signal                | **surviving mutant on a changed line** | a pull request reports surviving mutants on its changed lines as review findings; no mutation percentage gates a contract or the project                                |

(test-plan-test-models)=

## Reusable Test Models

(test-plan-configuration-validation-model)=

### Configuration validation

| Layer     | Required denominator                                                                  |
| --------- | ------------------------------------------------------------------------------------- |
| Component | every applicable configuration-validity contract selected by the verification profile |
| System    | verification-profile-selected representative public path(s)                           |

**Design:** equivalence partitioning · boundary value analysis

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-configuration-precedence-model)=

### Configuration precedence

| Layer              | Required denominator                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| Component          | generated omission-vs-explicit-value semantics selected by the verification profile                    |
| System integration | selected public override/clearing scenarios observed across the configured provider-interface boundary |

**Design:** precedence partitioning · omission vs explicit value · explicit clear/null semantics

**Completion:** required coverage = **100%**

(test-plan-credential-resolution-model)=

### Credential resolution

| Layer     | Required denominator                                                                                                                                                               |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Component | selected key-source partitions: configured fixed key, automatic rotation, required missing, plus every provider family explicitly permitted to run with an optional missing bearer |
| System    | selected public missing-credential error path                                                                                                                                      |

**Design:** equivalence partitioning · key-source precedence · provider-family optional-credential partitioning · deterministic rotation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-config-activation-model)=

### Configuration activation

| Layer              | Required denominator                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Component          | replacement snapshot round-trip, subsequent runtime snapshot capture, and selected cache invalidation                        |
| System integration | a public request created after installation exhibits a replacement-derived runtime effect at an observable provider boundary |

**Design:** state transition · replacement snapshot · stale-cache negative control · post-install behavioral observation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-tool-selection-model)=

### Tool selection

| Layer              | Required denominator                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Component          | every supported public named-choice input form plus each distinct provider named-choice serialization implementation selected by the profile |
| System integration | every provider-family partition selected by the verification profile, with each declared retained path present and passing                   |

**Design:** public input-form partitioning · provider-family capability partitioning · explicit named choice vs alternate registered tool · provider-boundary request inspection

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-tool-execution-model)=

### Tool execution

| Layer              | Required denominator                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Component          | verification-profile-selected registry semantics: duplicate rejection, callable schema/execution, supported call-shape parsing |
| System integration | selected multi-round and runtime-safety workflows, including every provider-family partition declared by the profile           |

**Design:** state-transition testing · provider-family capability partitioning · tool-result round trip · public error boundary · bounded round termination

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-routing-fallback-model)=

### Routing fallback

| Layer              | Required denominator                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Component          | route-order and route-attempt boundary criteria selected by the verification profile                                                          |
| System integration | public fallback, timeout, attempt-cap, and sticky-start workflows selected by the verification profile through a controlled provider boundary |

**Design:** failure partitioning · timeout with/without fallback · boundary-value analysis for route caps · route-order identity · sticky-start state transition

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-rate-limit-routing-model)=

### Rate-limit-aware routing

| Layer              | Required denominator                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Component          | provider/key isolation, both conservative-interval dominance directions, success reset, and cooldown-threshold state selected by the profile     |
| System integration | blocked-route skip, all-blocked fail/wait, earliest-availability selection, and auto-key availability/rotation workflows selected by the profile |

**Design:** state-transition testing · provider/key partitioning · timing-boundary analysis · availability ordering · negative interaction control

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-provider-retry-model)=

### Provider retry

| Layer              | Required denominator                                                                                                   |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Component          | explicit status/exception retry classification partitions selected by the verification profile                         |
| System integration | synchronous/asynchronous retryable, permanent, and exhausted same-route workflows selected by the verification profile |

**Design:** status/exception partitioning · sync/async equivalence · attempt-budget boundary analysis · same-route interaction counting

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-structured-recovery-model)=

### Structured-output recovery

| Layer              | Required denominator                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| Component          | bounded repair-prompt property over dynamic schema metadata, invalid output, and validation detail        |
| System integration | successful repair plus minimum/intermediate total-attempt boundaries selected by the verification profile |

**Design:** state-transition testing · boundary-value analysis for total attempt budgets · invalid-payload partitioning · property-based prompt-size control

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-data-safety-observability-audit-model)=

### Data-safety observability audit

| Layer              | Required denominator                                                                                                                                |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | one representative public tool request observed by runtime logging and physically persisted through the actual VCR pre-serialization/write pipeline |

**Design:** end-to-end negative information-flow audit · protected prompt/credential/tool argument/tool-result markers · full structured-log scan · physical cassette scan

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-sensitive-runtime-diagnostics-model)=

### Sensitive runtime diagnostics

| Layer              | Required denominator                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Component          | centralized safe log-context field selection                                                                      |
| System integration | provider-error, local-tool-failure, and schema-validation failure partitions selected by the verification profile |

**Design:** negative information-flow assertions · hostile provider error payload · secret-bearing tool cause/arguments · secret-bearing schema-invalid value · full structured-log-record inspection

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-vcr-redaction-model)=

### Durable VCR redaction

| Layer              | Required denominator                                                                                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | authentication/account-data redaction, raw caller request/tool payload redaction, and caller-controlled provider-response echo redaction through the actual VCR pre-serialization and replay pipeline |

**Design:** temp-cassette physical serialization · post-write secret scan · deterministic request-body fingerprint · offline replay after the live server is gone

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-provider-adapter-model)=

### Provider adapter boundaries

| Layer                 | Required denominator                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Component integration | every supported provider family and each distinct transport/failure partition selected by the verification profile |
| System integration    | workflows whose semantics require public-runtime ordering or retry behavior across the adapter boundary            |

**Design:** provider-family partitioning · native transport selection · request/response translation · malformed/error/disconnect partitions · upload-before-chat ordering

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-async-provider-model)=

### Asynchronous provider execution

| Layer              | Required denominator                                                                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | every supported provider-family × declared async capability partition: text, structured output, image, document, local video, and remote video where that capability applies |

**Design:** provider-family × capability partitioning · async public entry point · async-only media branches · normalized/grounded response checks

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-response-normalization-model)=

### Provider response normalization

| Layer              | Required denominator                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| Component          | every supported usage-metadata shape selected by the profile                                                  |
| System integration | each non-baseline provider family independently compared with the OpenAI-compatible canonical public response |

**Design:** provider-shape partitioning · semantic equivalence · stable usage totals · provider-detail non-leakage

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-provider-error-boundary-model)=

### Public provider-error boundary

| Layer              | Required denominator                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| System integration | at least one HTTP-client failure partition and one SDK-originated failure partition through the public router |

**Design:** transport-family partitioning · hostile provider detail · stable public error type/metadata · provider interaction counting

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-session-lifecycle-model)=

### Session lifecycle

| Layer                 | Required denominator                                                             |
| --------------------- | -------------------------------------------------------------------------------- |
| Component integration | history inclusion, one-shot history suppression, fork isolation, and clear/reuse |
| System                | concurrent public requests preserving both session history and routing isolation |

**Design:** state-transition testing · copy-vs-share semantics · explicit history suppression · clear/reuse · concurrent isolation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-session-persistence-model)=

### Session persistence

| Layer                 | Required denominator                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Component             | generated text/metadata round-trip; file/image/local-video/remote-video serialization; incompatible-version rejection |
| Component integration | public Session save/load round-trip                                                                                   |

**Design:** property-based round-trip · binary media preservation · serialization-version boundary · public lifecycle round-trip

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-public-api-model)=

### Public package surface

| Layer     | Required denominator                                                        |
| --------- | --------------------------------------------------------------------------- |
| Component | the complete current package-declared public surface (`llm_router.__all__`) |

**Design:** authoritative export-set enumeration · package-root resolution

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-example-import-safety-model)=

### Executable example import safety

| Layer     | Required denominator                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| Component | every shipped Python example module under `examples/llm_router`, excluding `__init__.py` |

**Design:** fresh-module import · network sentinel · live-router call sentinel · one retained path per shipped module

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-structured-output-provider-matrix)=

### Structured output provider matrix

| Layer              | Required denominator                               |
| ------------------ | -------------------------------------------------- |
| System integration | every adapter family declaring JSON-schema support |

**Design:** provider-family capability partitioning · one caller schema across routes · public structured-result equivalence · provider-format non-leakage

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-grounded-media-matrix)=

### Grounded multimodal provider matrix

| Layer              | Required denominator                                                                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | every adapter family declaring the relevant media capability together with JSON-schema support; video is partitioned into local-file and remote-URL modes |

**Design:** provider-family capability partitioning · retained known media · schema-valid structured result · deterministic grounding assertions · local-vs-remote video partitioning

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-schema-contract-model)=

### Provider-independent schema validation

| Layer     | Required denominator                                                                        |
| --------- | ------------------------------------------------------------------------------------------- |
| Component | Pydantic reconstruction, valid mapping-schema enforcement, invalid mapping-schema rejection |

**Design:** Draft 2020-12 object-schema validation · nested/common constraint enforcement · fail-closed schema normalization · requested-model reconstruction

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-content-normalization-model)=

### Multimodal content normalization

| Layer     | Required denominator                                                                                                   |
| --------- | ---------------------------------------------------------------------------------------------------------------------- |
| Component | ordered mixed parts/descriptor metadata, ChatMessage semantics, unsupported input/media, raw-image mode/min/max bounds |
| System    | representative invalid public requests proving zero provider-boundary interactions                                     |

**Design:** ordered-part equivalence · descriptor metadata preservation · mutable-meta copy semantics · boundary-value analysis · pre-provider negative interaction control

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-fault-model)=

### Fault-based testing

| Group                 | Fault classes                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------- |
| Implementation        | `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `impl.control-flow` · `impl.effect` |
| Runtime / dependency  | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`   |
| Interface / protocol  | `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema`    |
| Architecture          | `architecture.forbidden-edge` · `architecture.layer-bypass`                                   |
| Specification / model | `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`              |

#### Fault-class semantics

| Fault class                        | Meaning                                                                            | Challenged by                                                                                                                                                                                 |
| ---------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison`                  | A comparison/operator change alters the implementation decision.                   | rule mutant: a comparison operator is swapped (`<` ↔ `<=`, `==` ↔ `!=`, …)                                                                                                                    |
| `impl.boundary`                    | A boundary value or threshold change alters accepted vs rejected behavior.         | rule mutant: a compared constant is shifted by ±1                                                                                                                                             |
| `impl.arithmetic`                  | An arithmetic operator change alters a computed value.                             | rule mutant: an arithmetic operator is swapped (`+` ↔ `-`, `*` ↔ `/`, `//` → `/`, `%` → `//`, `**` → `*`)                                                                                     |
| `impl.control-flow`                | A branch, return, or exception-flow change alters execution.                       | rule mutant: `and` ↔ `or`, a dropped `not`, `True` ↔ `False`; a returned value replaced by `None` or its negation                                                                             |
| `impl.effect`                      | A statement's effect or a function's whole work is lost while execution continues. | rule mutant: a statement with an effect is removed (a call, an attribute or item write, an augmented assignment, `raise`, `del`); a function body is replaced by a default of its return type |
| `runtime.latency-timeout`          | Dependency latency or timeout behavior challenges the runtime path.                | retained test with a runtime fault-injection observation                                                                                                                                      |
| `runtime.unavailable-disconnect`   | Dependency unavailability or disconnect challenges the runtime path.               | retained test with a runtime fault-injection observation                                                                                                                                      |
| `runtime.malformed-response`       | Dependency returns malformed or unparsable data.                                   | retained test with a runtime fault-injection observation                                                                                                                                      |
| `interface.unexpected-interaction` | The system performs an external interaction that the contract says must not occur. | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |
| `interface.error-status`           | The external interface returns an error status.                                    | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |
| `interface.payload-schema`         | The external payload violates the expected schema or shape.                        | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |
| `architecture.forbidden-edge`      | A forbidden dependency edge crosses an architectural boundary.                     | retained test with a runtime fault-injection observation                                                                                                                                      |
| `architecture.layer-bypass`        | Execution bypasses a required architectural layer or boundary.                     | retained test with a runtime fault-injection observation                                                                                                                                      |
| `spec.wrong-outcome`               | The observable outcome differs from the Requirement.                               | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |
| `spec.missing-partition`           | A Requirement-relevant semantic partition is absent from verification.             | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |
| `spec.wrong-ordering-boundary`     | Observable ordering or before/after boundary semantics are wrong.                  | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                      |

For retained pytest evidence, a fault class is challenged only when the test declares
the exact `contract_id + fault class` and the same execution retains a matching
runtime fault-injection observation. A marker without the runtime observation is not
fault evidence. A mutant challenges its class when it actually ran against the
contract's passing tests: the engine's retained report for a rule mutant, the isolated
run of the frozen patch for a semantic mutant.

(test-plan-mutation-policy)=

#### Mutation policy

Mutants are planted only on a contract's attributable `@impl` lines, the lines no
contract outside its derivation family also claims. Each mutant runs the contract's
passing tests with the full pytest runner, one isolated run per mutant.

##### Mutant outcomes

| Outcome     | Meaning                                                                       | Counts as                                   |
| ----------- | ----------------------------------------------------------------------------- | ------------------------------------------- |
| Caught      | at least one of the contract's passing tests fails or times out on the mutant | caught                                      |
| Survived    | the tests run the mutated line and all of them pass                           | not caught                                  |
| Not reached | no test of the contract executes the mutated line                             | not caught                                  |
| Invalid     | the mutated code breaks import or test collection                             | neither; counted apart                      |
| Suppressed  | a suppression pragma covers the mutant                                        | neither; shown with its category and reason |

An Implementation class is **caught** for a contract when it has at least one valid,
unsuppressed mutant and every such mutant is caught. A REQUIRED class without such a
mutant is **not challenged**: the class does not fit the contract's code, or the code
scope is wrong.

##### Arid code

| Rule                 | Code it covers                                                                                                | Why it is not mutated                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `arid.logging`       | a statement that only logs or warns: a logger method call, a `log_…` or `_log_…` helper call, `warnings.warn` | a log line is no contract outcome, and a test that pins log wording is brittle          |
| `arid.sleep`         | a statement that only waits: `sleep`, `time.sleep`, `asyncio.sleep`                                           | waiting changes timing, not results                                                     |
| `arid.type-checking` | an `if TYPE_CHECKING:` block                                                                                  | it never runs                                                                           |
| `arid.repr`          | a `__repr__` or `__rich_repr__` method                                                                        | a debug representation is no contract outcome; `__str__` stays mutated, it is a message |

A mutant inside arid code is not planted; the campaign counts it by rule. A profile
turns a rule off for its contract in a **Mutation policy** table
(`| Rule | Decision | Why |`, decision `Mutate`) when that code is the contract's
subject, for example when waiting is the behavior under test.

##### Validity

Before anything runs, the engine drops mutants that cannot be valid or
that repeat another one. A body is replaced only by a default of its annotated return
type (`None`; `False` and `True`; `0` and `1`; `0.0`; `""`; `b""`; an empty collection), and
never in a generator, a stub (`pass`, `...`, `raise NotImplementedError`), an overload,
an abstract method or a dunder method other than `__call__`. Statement removal never
removes a plain name binding, so it cannot unbind a name. A body mutant that repeats
the statement or return mutant of a one-statement function is not planted. A mutant
that still breaks import or collection is invalid.

##### Suppression

`# mutation: <category>[<operators>] <reason>` on the mutated line or
on the line above the statement it covers. `equivalent`: no input can observe the
change, and the reason says why. `unproductive`: a change no test should pin down.
`arid`: diagnostic or caching code that no rule covers. `[<operators>]` narrows the
pragma to those operators. A suppressed mutant does not run, stays visible with its
category and reason, and never counts as caught. A pragma that covers no mutant fails
the build; the engine's own pardon pragma is not used.

##### Cadence and signal

A pull request and every push of a branch mutate only the lines the branch changes against
its base that are attributable and covered by the contract's tests, and report at most one
surviving mutant per line as a review finding. The operator of a line's finding is the most
productive one: the recorded verdicts rank the operators by the share of their survivors a
pin was asked for, starting from Google's order (comparison, boolean, arithmetic, statement,
return, boundary, body) while few verdicts are recorded, as Google ranks its operators by how
useful their mutants were. A survivor whose recorded verdict is equivalent or irrelevant is
no finding: the summary lists it apart with the verdict and its reason. The retained
campaign reruns every contract whose inputs changed since its last run, and every contract
on request, several contracts at once, each in its own copy of the working tree. Its inputs
are the product files that hold its mutants, its tests with their Gherkin and cassettes, the
shared test support and the dependencies, as PIT and Stryker count them. Python files count by
what they do: a tool by its syntax tree, code under test by its tokens at their positions with
its `# mutation:` pragmas, so an edited comment or a reformatting reruns nothing. A mutant's
time limit is 1.25 times its tests' time in the retained run plus 10 s, as in PIT, and a
mutant that outruns it counts as caught only when a second run with twice the limit runs out
of time too: a slow suite is no hang. No mutation percentage gates a contract or the project.

##### Semantic mutants

A profile may select semantic mutants for `spec.*` and
`interface.*` classes that rule operators cannot express, in a **Semantic mutants**
table (`| Fault class | Target | Budget | Risk |`). A generator given the Requirement,
the profile's criteria, the target's code and similar fixes from the repository history
proposes at most the budget per target (see Model generation). Each proposal is frozen
as a patch and is not regenerated while its inputs are unchanged. It counts only after a
deterministic cascade:

1. the patch applies, uses only the names and capabilities its module already has (no
   new import, no dynamic code, no process or file-system access the original lacks),
   and the module imports;
2. it still differs from the original after comments and docstrings are removed and the
   syntax tree is normalized;
3. it repeats no other mutant, rule or semantic;
4. it runs against the contract's passing tests in an isolated copy, and a failing test
   makes it caught;
5. a survivor goes to a differential property run that searches for an input on which
   the original and the mutant differ, and then to the survivor judgement below.

With such an input the class is challenged and not caught, and the input is the test
goal; without one the mutant is UNKNOWN (equivalence not proven) and never PASS. The
cascade is an evidence producer qualified on a calibration set of known identical,
duplicate, invalid, confined, equivalent and distinguishable mutants. A selected target
without a current proposal keeps its class UNKNOWN: it was never generated, its
generation was deferred or failed, or its proposals went stale. A draft test for a
survivor is judged in the project's style: it is formatted and given ruff's safe fixes by
the project's own rules first, and a rule it still breaks rejects it. It is kept only when it
passes on the original five times in a row (TestGen-LLM's reliability filter), fails on the
frozen patch, imports nothing beyond the public API, the modules the contract's own tests
already import and, for a Technical requirement, the module of the code it tests and the
project modules that module imports itself, and uses no process, file-system or
dynamic-code primitive. Its author sees the shortest of the
contract's tests as an example, or the step definitions of the scenarios pytest-bdd
generates, and a rejected draft is asked for again with the reason, the errors pytest
reported on the original and the lint rules it broke, from the role's next model.

##### Model generation

| Role                      | Order | Backend           | Model                     |
| ------------------------- | ----: | ----------------- | ------------------------- |
| Semantic mutant generator |     1 | `antigravity-cli` | `gemini-3.1-pro-high`     |
| Semantic mutant generator |     2 | `antigravity-cli` | `gemini-3.8-flash-high`   |
| Draft test author         |     1 | `antigravity-cli` | `gemini-3.8-flash-medium` |
| Draft test author         |     2 | `antigravity-cli` | `claude-sonnet-4-6`       |
| Survivor verdict          |     1 | `claude-cli`      | `claude-opus-5-5`         |
| Survivor verdict review   |     1 | `antigravity-cli` | `gemini-3.1-pro-high`     |
| Survivor verdict review   |     2 | `antigravity-cli` | `gemini-3.8-flash-high`   |

Semantic mutants, their draft tests and the verdicts on survivors come from a model called
through one adapter (ADR_0004). Antigravity serves Gemini and Claude models from two quotas,
a large one for the Gemini family and a smaller one for every other model, so Gemini carries
the volume and a role falls back into the other pool; the Claude subscription serves only the
verdict model. Each role tries its backends in order. A backend that is unavailable (not
signed in, account not eligible) or whose budget defers the call is skipped for the next.
A `claude-cli` call runs without tools, plugins, MCP servers or memory, with a replaced
system prompt and a JSON schema. `agy` cannot be started without its tools, its own system
prompt or its conversation history: the adapter tells it to answer from the text alone,
puts the system text before the prompt, and refuses a call that reaches for a tool. Every
answer is validated again on receipt. Which Claude subscription a call uses is the machine's
choice, a named profile of the CLI with its own sign-in (`model_generation.py profile`), and
every ledger row names the profile; the windows the budget reads are that subscription's.

###### Generation budget

| Budget                    | Limit |
| ------------------------- | ----: |
| 5-hour window             |   80% |
| Weekly window             |   70% |
| Calls per run             |    40 |
| List price per call       | $0.50 |
| Draft attempts per mutant |     2 |

Every call appends one row to the consumption ledger. The row records the role,
backend, model, outcome, tokens, the list-price equivalent where the backend reports
one, the duration and the plan windows. A window at or above its limit, or a run that
reached its call limit, defers the call; a backend that reports no windows is bounded by
the call limit alone. A deferred, rejected or invalid generation is never a pass. The
target keeps no current proposal, and its class stays UNKNOWN. Generation runs only on
request and only for targets whose proposals are missing or stale; the gate, the cascade
and the portal build never call a model. A proposal or draft names the call that
produced it, and the gate recomputes it from the stored response.

##### Survivor judgement

| Assessor | Backend           | Model                      |
| -------: | ----------------- | -------------------------- |
|        1 | `antigravity-cli` | `claude-opus-4-6-thinking` |
|        2 | `antigravity-cli` | `gemini-3.1-pro-high`      |
|        3 | `antigravity-cli` | `gemini-3.8-flash-high`    |

A survivor is a mutant that every passing test of its contract lets through, rule or
semantic (ADR_0005). A symbolic search (CrossHair) over a typed harness of the original and
the mutant looks for an input that tells them apart, then every assessor of the table
answers distinct (with an input), equivalent or unsure, with its confidence. The assessors
see the parameters as the code declares them and how the project's types the target takes
or names are built; an input may use any of the project's dataclasses, exceptions and enum
members. None of this
can make a survivor caught. An input counts only when execution confirms it: called with
it twice, each version repeats itself, and the original and the mutant return different
values, leave their object in different states or raise different exception types. A clock
reading or a memory address is not a difference. A semantic survivor with a confirmed input is
distinguished. A rule survivor keeps its outcome and gains the input as its test goal. An
assessors' equivalent is never a proof. When every assessor judges a survivor equivalent
with a confidence above the calibrated threshold, it is labelled likely equivalent and stays
UNKNOWN, or survived for a rule mutant, until its verdict is recorded (below).
Otherwise it is labelled unsure. A survivor that cannot be called from typed arguments, such
as an asynchronous method or a method of an object that needs a running router, is not
judged, and its row says why. The assessors come from two model families, Claude and
Gemini, and a label needs all of them, so one family's shared blind spot does not label a
survivor alone.

###### Judgement settings

| Setting                        |     Value |
| ------------------------------ | --------: |
| Symbolic paths per mutant      | 300 paths |
| Symbolic time limit per mutant |      60 s |
| False-equivalent rate          |       10% |
| Assessed equivalence           |  advisory |

The symbolic search explores its paths in a seeded order, so a bound on paths gives the same
answer on any machine; the time limit only stops a search that runs away. The threshold is
split conformal over the distinct pairs: labelled calibration pairs, half equivalent and half
distinct, every distinct one with an input that execution confirms, and observed pairs, real
survivors the symbolic search left unsure and a mutation pin proves distinct, once every
assessor answered the triage's own question about them. Only those are asked the triage's
question, so only they stand for the survivors it asks about. The hand-made pairs are easier than real survivors (on the survivors
the pins proved distinct, single assessors called some equivalent that none of the labelled
pairs had them call), so the observed pairs carry the rate. A survivor is labelled likely
equivalent only when its lowest assessor confidence is above the threshold, which at most the
false-equivalent rate of the distinct pairs exceed. The assessors' answers on the pairs are
frozen and replayed by the qualification. A change of assessor, model, prompt or labelled pairs
leaves the ensemble uncalibrated, and its labels do not count until it is calibrated again.
Rule survivors are judged on request, apart from the campaign.

##### Survivor verdicts

Every judged survivor, and every mutant no test of its contract reaches, gets a verdict from
the Survivor verdict role (ADR_0006). The verdict model sees the requirement and its criteria,
the Feature and Goal it serves, both versions of the code, the survivor judgement and any
input execution confirmed; for an unreached mutant, that no test runs its line. A verdict
that would take a mutant out of its class, equivalent or irrelevant, counts only when the
Survivor verdict review, a model of another family asked the same question, agrees: a panel
of models from different families is less biased toward its own (PoLL). When the review does
not agree, the mutant is pinned.

| Verdict      | Meaning                                                                                        | Effect                                                                                                                                                           |
| ------------ | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pin`        | The mutant changes something the requirement asks for.                                         | A test that pins it is drafted, kept only when it breaks no lint rule, passes on the original five times and fails on the mutant, and adopted as a mutation pin. |
| `equivalent` | No input tells the versions apart as the contract observes them; never with a confirmed input. | The mutant leaves its class as suppressed, with the verdict's reason.                                                                                            |
| `irrelevant` | The versions differ, but in nothing a requirement asks for.                                    | The mutant leaves its class as suppressed, with the verdict's reason.                                                                                            |
| `escalate`   | Deciding changes what a Feature or Goal promises, and no requirement settles it.               | The mutant stays in its class, and the decision waits for the person.                                                                                            |

The person decides only escalations: a comparison, a type, a default or a message inside a
requirement's scope is the verdict model's to decide, never a reason to escalate. A person's
verdict, when recorded, wins over the model's. A verdict counts while the code, the tests and
the question it answered are unchanged. A mutation pin is a test module under
`tests/llm_router/mutation_pins/` that verifies its contract and names, in its first line, the
mutant it pins; it proves no coverage case and no depth, so it never changes a criterion's
count or a contract's level, boundary or representation, but the next campaign counts it
among the contract's tests. A pin is kept as the cascade judged it, in the project's style, and
it names the answer or kept draft it was made from; when the rules change, every pin is judged
again, and a pin that no draft brings within them is removed.

###### Model canaries

A model's answers count for a role only after it passed that role's canaries, a few cases
with a known outcome. The generator must propose a well-formed, confined defect for a canary
target; the draft author must write a test the cascade keeps for a known distinguishable
mutant; the verdict model and the verdict review must pin a known gap, judge a known
equivalent equivalent and escalate a known product decision. An assessor must meet the
calibration floors: an input confirmed for at least 80% of the labelled distinct pairs, and
at most the false-equivalent rate of all distinct pairs, labelled or observed, judged
equivalent. A
change of model, question or canary set asks for the canaries again; until they pass, the
role skips that model. A canary the backend did not answer (its quota, its capacity, the time
limit) leaves the model's record for the same questions as it was.

**Completion:** required fault-class coverage = **100%** · required deterministic fault detection = **100%**

(test-plan-upper-level-assurance)=

## Upper-level assurance and validation

Requirement/TREQ Verification Profiles prove individual normative contracts. Feature, Goal, and whole-product monitors add only evidence that cannot be reduced to one child contract in isolation.

| Owner level      | Child-support gate      | Direct upper-level evidence                       | Purpose                                                               |
| ---------------- | ----------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| Feature          | all direct Requirements | Capability integration · Capability validation    | prove cross-Requirement interaction and the capability's intended use |
| Goal             | all direct Features     | Cross-capability integration · Outcome validation | prove cross-Feature behavior and the Goal-level outcome               |
| Product / System | all current Goals       | Cross-goal integration · Operational validation   | prove whole-product interactions and intended operation               |

**Ownership rule.** Cross evidence belongs to the lowest common assurance owner of the claims it connects: TREQ × TREQ → REQ, REQ × REQ → Feature, Feature × Feature → Goal, Goal × Goal → Product / System. The same upper-level criterion is never copied into its descendants.

**Target source.** This Test Plan defines the allowed assurance kinds and completion rules. A branch-specific Assurance Profile declares the concrete integration/validation criteria before execution. Existing tests never create or weaken a Target merely by existing.

**Methods.** A declared validation criterion may be satisfied by an appropriate retained test, analysis, inspection, demonstration, manual test, or engineering/operational experiment. The method and environment are part of the criterion Target; stronger evidence may replace a weaker method only when the profile explicitly permits it.

**Status semantics.** A declared criterion is `PASS` only when every required retained execution/evaluation passes. A declared but missing or failing criterion is `FAIL`. A section with no declared Target is `N/A`. An applicable child Goal/Feature/Requirement that has not yet been onboarded into the assurance pipeline is `UNKNOWN`, not `N/A` and never implicit `PASS`.

**Completion.** child support = **100% of required direct children PASS** · declared upper-level criteria = **100% PASS**. `N/A` sections do not block; `UNKNOWN` required child support does block whole-product assurance.
