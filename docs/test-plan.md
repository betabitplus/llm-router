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

| Fault class                        | Meaning                                                                                                                  | Challenged by                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison`                  | A comparison/operator change alters the implementation decision.                                                         | rule mutant: a comparison operator is swapped (`<` ↔ `<=`, `==` ↔ `!=`, …), or an identity or membership test is inverted (`is` ↔ `is not`, `in` ↔ `not in`, as Python mutation tools do)                                                                                                                                                                                                                                                                                                       |
| `impl.boundary`                    | A boundary value or threshold change alters accepted vs rejected behavior.                                               | rule mutant: a compared constant is shifted by ±1; a strict comparison made inclusive or back (`<` ↔ `<=`, `>` ↔ `>=`, PIT's conditionals boundary), which counts for `impl.comparison` as well; a slice bound removed (`items[:n]` → `items[:]`, MutPy's slice index removal)                                                                                                                                                                                                                  |
| `impl.arithmetic`                  | An arithmetic operator change alters a computed value.                                                                   | rule mutant: an arithmetic operator is swapped (`+` ↔ `-`, `*` ↔ `/`, `//` → `/`, `%` → `//`, `**` → `*`)                                                                                                                                                                                                                                                                                                                                                                                       |
| `impl.control-flow`                | A branch, return, or exception-flow change alters execution.                                                             | rule mutant: `and` ↔ `or`, a dropped `not`, `True` ↔ `False`; a returned value replaced by `None` or its negation; one operand of an `and`/`or` removed; a condition replaced by `True` or `False`, or a plain-value condition negated                                                                                                                                                                                                                                                          |
| `impl.effect`                      | A statement's, call's or value's effect is lost, or a value is read from the wrong attribute, while execution continues. | rule mutant: a statement with an effect is removed (a call, an attribute or item write, a write to a name the function declares `global` or `nonlocal`, an augmented assignment, `raise`, `del`); a function body is replaced by a default of its return type; an optional keyword argument, a built-in conversion, a method call used as a value or a container element is removed; another attribute the same code reads on the same object, with a name at least half alike, is read instead |
| `runtime.latency-timeout`          | Dependency latency or timeout behavior challenges the runtime path.                                                      | retained test with a runtime fault-injection observation                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `runtime.unavailable-disconnect`   | Dependency unavailability or disconnect challenges the runtime path.                                                     | retained test with a runtime fault-injection observation                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `runtime.malformed-response`       | Dependency returns malformed or unparsable data.                                                                         | retained test with a runtime fault-injection observation                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `interface.unexpected-interaction` | The system performs an external interaction that the contract says must not occur.                                       | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                                                                                                                                                                                                                                                                                                                        |
| `interface.error-status`           | The external interface returns an error status.                                                                          | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                                                                                                                                                                                                                                                                                                                        |
| `interface.payload-schema`         | The external payload violates the expected schema or shape.                                                              | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                                                                                                                                                                                                                                                                                                                        |
| `architecture.forbidden-edge`      | A forbidden dependency edge crosses an architectural boundary.                                                           | retained test with a runtime fault-injection observation · architecture mutant on an import-linter rule                                                                                                                                                                                                                                                                                                                                                                                         |
| `architecture.layer-bypass`        | Execution bypasses a required architectural layer or boundary.                                                           | retained test with a runtime fault-injection observation: a negative control that bypasses the layer the profile names and shows the requirement's own oracle flags it                                                                                                                                                                                                                                                                                                                          |
| `spec.wrong-outcome`               | The observable outcome differs from the Requirement.                                                                     | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one · scenario oracle mutant                                                                                                                                                                                                                                                                                                                                                               |
| `spec.missing-partition`           | A Requirement-relevant semantic partition is absent from verification.                                                   | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                                                                                                                                                                                                                                                                                                                        |
| `spec.wrong-ordering-boundary`     | Observable ordering or before/after boundary semantics are wrong.                                                        | retained test with a runtime fault-injection observation · semantic mutant where the profile selects one                                                                                                                                                                                                                                                                                                                                                                                        |

For retained pytest evidence, a fault class is challenged only when the test declares
the exact `contract_id + fault class` and the same execution retains a matching
runtime fault-injection observation. A marker without the runtime observation is not
fault evidence. A mutant challenges its class when it actually ran against the
contract's passing tests: the engine's retained report for a rule mutant, the isolated
run of the frozen patch for a semantic mutant.

(test-plan-mutation-policy)=

#### Mutation policy

Mutants are planted only on a contract's attributable `@impl` lines, every line one of
its `@impl` scopes claims. A line several contracts claim is challenged for each of them
with that contract's own passing tests (a parent's with its derived children's as well),
so a claim is tested where it is made and a survivor belongs to the contract whose tests
let it through; the other claimants are recorded beside it. An `@impl` names the code
that implements its contract and no more: a technical requirement that refines one check
of a broader function annotates that check, not the function. Each mutant runs the
contract's passing tests with the full pytest runner, one isolated run per mutant.

##### Mutant outcomes

| Outcome     | Meaning                                                                                                                                                                                                                                                                     | Counts as                                   |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Caught      | at least one of the contract's passing tests fails or times out on the mutant                                                                                                                                                                                               | caught                                      |
| Survived    | the tests run the mutated line and all of them pass                                                                                                                                                                                                                         | not caught                                  |
| Not reached | no test of the contract executes the mutated line; code that runs when its module is imported (a module or class body, a decorator, a default value) counts as reached once a test runs its module, and every selected test runs for it, as Stryker runs its static mutants | not caught                                  |
| Invalid     | the mutated code breaks import or test collection                                                                                                                                                                                                                           | neither; counted apart                      |
| Suppressed  | a suppression pragma covers the mutant                                                                                                                                                                                                                                      | neither; shown with its category and reason |

An Implementation class is **caught** for a contract when it has at least one valid,
unsuppressed mutant and every such mutant is caught. A REQUIRED class without such a
mutant is **not challenged**: the class does not fit the contract's code, or the code
scope is wrong.

##### Arid code

| Rule                 | Code it covers                                                                                                                                                                                  | Why it is not mutated                                                                   |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `arid.logging`       | a statement that only logs or warns: a logger method call, a `log_…` or `_log_…` helper call, `warnings.warn`; a call that only builds a logger or a logging callback (a `…_logger(…)` builder) | a log line is no contract outcome, and a test that pins log wording is brittle          |
| `arid.sleep`         | a statement that only waits: `sleep`, `time.sleep`, `asyncio.sleep`                                                                                                                             | waiting changes timing, not results                                                     |
| `arid.type-checking` | an `if TYPE_CHECKING:` block                                                                                                                                                                    | it never runs                                                                           |
| `arid.repr`          | a `__repr__` or `__rich_repr__` method                                                                                                                                                          | a debug representation is no contract outcome; `__str__` stays mutated, it is a message |

A mutant inside arid code is not planted; the campaign counts it by rule. A profile
turns a rule off for its contract in a **Mutation policy** table
(`| Rule | Decision | Why |`, decision `Mutate`) when that code is the contract's
subject, for example when waiting is the behavior under test.

##### Validity

Before anything runs, the engine drops mutants that cannot be valid or
that repeat another one. Nothing inside a type annotation is mutated, as Python mutation tools leave
annotations alone: an annotation changes no call. A body is replaced only by a default of its annotated return
type (`None`; `False` and `True`; `0` and `1`; `0.0`; `""`; `b""`; an empty collection), and
never in a generator, a stub (`pass`, `...`, `raise NotImplementedError`), an overload,
an abstract method or a dunder method other than `__call__`. Statement removal never
removes a plain local name binding, so it cannot unbind a name; a write to a name the
function declares `global` or `nonlocal` is removed, since it changes state that outlives the
call, as an attribute write does. A body mutant that repeats the statement or return mutant
of a one-statement function is not planted. A mutant that still breaks import or collection
is invalid.

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
on request, several contracts at once, each in its own copy of the working tree, made at once
and without the pilot's model records and the experiments, which no test reads. Its inputs
are the product files that hold its mutants, its tests with their Gherkin and cassettes, the
shared test support and the dependencies, as PIT and Stryker count them. Python files count by
what they do: a tool by its syntax tree, code under test by its tokens at their positions with
its `# mutation:` pragmas, so an edited comment or a reformatting reruns nothing.
`pyproject.toml` counts by the tables its run reads, as Bazel keys an action by its declared
inputs: its layout, its comments and the tables of tools the run does not start (linters, type
checkers, release tools) rerun nothing, while a test setting, a dependency or an unknown table
does; the semantic cascade also counts ty's table, since it type-checks each mutant, a draft's
judgement ruff's, since it formats the draft, and the architecture mutants import-linter's. A mutant's
time limit is 1.25 times its tests' time in the retained run plus 10 s, as in PIT, and a
mutant that outruns it counts as caught only when a second run with twice the limit runs out
of time too: a slow suite is no hang. Within a contract the engine runs mutants at once on the
machine's cores the contracts running beside it leave, and keeps its own incremental cache per
contract, as PIT's history and Stryker's incremental mode do: where only tests changed, as when a
cycle adds mutation pins, a mutant whose source file and covering test files are unchanged keeps
its result and one a new or changed test covers runs again; a change of the engine, of the tests'
shared inputs or of any source file empties the cache. No mutation percentage gates a contract or
the project.

##### Scenario oracle mutants

A scenario checks the outcome it names only when its Then steps compare what happened with
what it expects. Each scenario oracle mutant changes that expectation in one step
definition, or in an assertion helper a Then step reaches, in a copy of the project and
nothing else: a constant the step compares with becomes another value of its type, the
expected error or type an assertion helper is given becomes another one the module names,
and an assertion with neither is negated. The scenarios that use the step run as the
retained run runs them, and one must fail. A mutant they all pass survives: the step would
pass as well when the product gave another outcome. A Then step whose code checks nothing
at all counts as a survivor. A run that cannot collect or build the scenario is invalid.
The mutant counts for `spec.wrong-outcome` of every contract its scenario names by tag, and
otherwise of every contract the scenario's test verifies, where the profile does not rule
the class out; the class is caught only when every one that ran is caught, and the
survivors are listed with the step and the expectation that did not matter. No model is
asked. The results are retained with the digest of the features, the test code, the
cassettes and the product code, and count only while those are unchanged and the producer
is qualified on a calibration project whose steps check strongly, through a helper, weakly
and not at all.

##### Architecture mutants

Every import-linter rule gets one architecture mutant: an import of a module the rule
forbids, added at the end of a module the rule governs, in a copy of the project. The rule
must then be reported broken; one that stays kept would let that edge in, as a rule made
hollow by an exception does. The result challenges `architecture.forbidden-edge` at the
level of the rules themselves and is retained with the digest of the code and the rules.

##### Semantic mutants

A profile may select semantic mutants for `spec.*` and
`interface.*` classes that rule operators cannot express, in a **Semantic mutants**
table (`| Fault class | Target | Budget | Risk |`). Every profile whose contract requires such
a class and has functions in its `@impl` scope selects them (050): by default each required
`spec.*` and `interface.*` class at each of those functions, with a budget of 2 and the class's
risk in words, and a profile may narrow the table or say its risk more exactly. A generator given the Requirement,
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
   makes it caught, as does a run that does not finish within the campaign's time limits
   (1.25 times those tests' time in the retained run and 10 s, confirmed at twice that);
5. a survivor goes to a differential property run that searches for an input on which
   the original and the mutant differ, and then to the survivor judgement below.

With such an input the class is challenged and not caught, and the input is the test
goal; without one the mutant is UNKNOWN (equivalence not proven) and never PASS. The
cascade is an evidence producer qualified on a calibration set of known identical,
duplicate, invalid, confined, equivalent and distinguishable mutants. It judges a contract's
proposals in chunks of three, as many chunks of any contracts at once as the campaign runs
contracts, the largest contracts first, so no single contract sets the length of a run.
Proposals whose mutated function reads the same stay in one chunk, so a repeated mutant is
still named a duplicate of the first; judged in chunks, the calibration set must get the same
outcome for every proposal. A contract whose retained result was made from exactly its
current inputs is not run again, and where only the assessors' answers or the drafts changed
its mutants' test runs stand. The cascade runs only while the evidence producers are qualified
for the current code: a run before the qualification catches up would judge every contract
without the assessors' labels and put those results in place of calibrated ones. A mutant's tests are the contract's tests that run its target in
the retained run's per-test coverage, stopped at the first failure as PIT and Stryker stop; the
test run imports the module anyway, so whether it imports is asked only when a type check or the
run fails. Draft tests are judged in as many isolated copies at once, and scenario oracle
mutants run in as many copies. A selected target
without a current proposal keeps its class UNKNOWN: it was never generated, its
generation was deferred or failed, or its proposals went stale. A draft test for a
survivor is judged in the project's style: it is formatted and given ruff's safe fixes by
the project's own rules first, and a rule it still breaks rejects it. It is kept only when it
passes on the original five times in a row (TestGen-LLM's reliability filter), fails on the
frozen patch, imports nothing beyond the public API, the modules the contract's own tests
already import and, for a Technical requirement, the module of the code it tests and the
project modules that module imports itself (a Requirement's pin imports no private module of the
project, such as `llm_router._internal`, and reaches none by attribute or by a dotted name either:
it observes through the package's public API), uses no process, file-system or dynamic-code
primitive, imported or reached as an attribute of a module from outside the project (a project
module's own client stays reachable, where an adapter's test replaces its transport), and reads,
replaces, imports or passes no private name of the project (one that starts with `_`: ruff's
flake8-self rule, with the `getattr`, `setattr`, `monkeypatch.setattr` and `patch` targets, the
imports it does not see, a private keyword and a private option the project spells as a string,
such as `_executor`): a pin observes what
its requirement names through what the code offers its callers, since a private step changes with
a refactoring that breaks nothing (on 2026-09-30 a third of the REQ pins read or replaced one,
against one module in fifty of the project's own tests). A parametrized value with a bracket
needs `ids=`: a test's id becomes a need's title in the documentation, where `[[` starts a
sphinx-needs function call and stops the build. Every test run blocks the network but for the
machine itself (pytest-recording's `--block-network`): the retained run, CI and the pre-push
hook alike, so a test whose call the block stops behaves the same in each. On 2026-10-01 the
pre-push run, without the block, let a pin's call reach a real provider, and the pin was taken
back. The author has no tools, so the question carries what a person would
look up. Its example is a test that runs the mutant's line, else one that runs its function,
the contract's own first (the shortest of the contract's tests when none does; for a
scenario pytest-bdd generates, its step definitions), with the helpers, fixtures and
constants of its module, as ACH hands its author the whole test class. When no test runs
the line, a second test shows how the project reaches such a line: the one that runs most of
the function's rarer lines, each weighed by how few tests run it. A function outside a class
comes with the functions of its module that call it, which show what reaches it, and those
it calls or hands on, which show what it relies on. An API card says where
every name the examples import, and the verdict's focus and the defect mention, lives and
how it is built, with every member of an enum and what each method returns, two steps deep;
and how the project's types the function takes are built unless the pin may not import it;
then the question says to reach the function through the public API. The answer cites under
`sources` every project name it uses, each from the examples or the card. Before anything
runs, a grounding check looks each name up in the source tree, as De-Hallucinator grounds a
model's code in the project's own APIs: a name its module does not bind, a member its enum
lacks, an argument its constructor does not take or one it cannot be built without, also
through a subclass the draft declares and its `super().__init__`, rejects the draft, and the reason names what exists
instead. What the tree alone cannot settle (a name from an outside package, a
lazy module, an inherited or aliased constructor) is never a problem. The check is qualified
on a small project with known answers, and the gate runs it over the project's own tests
and pins, where it must find nothing. A rejected draft is asked for again with the reason,
the errors pytest reported on the original, the lint rules it broke and the API card of
every project name those errors mention, from the role's next model. A failure that prints
no error lines is reported with the reason pytest's summary gives, and a run that does not
finish is reported as such. The rules say that an async test needs its pytest-asyncio marker
while the project runs it in strict mode.

Every judged draft is recorded beside its contract's verdicts (`drafts.json`) with its
cause: kept, invented project API, misused project API, wrong behaviour on the original,
does not catch the mutant, outside the pin rules, or lint. The record also keeps the names
the draft used that appear nowhere in its question, and its sources. The
{doc}`Model roles <model-roles>` page shows each role's calls and each model's drafts by
cause. It marks the draft author failing when fewer than one in five of its last twenty
recorded drafts is kept, judged from ten on: TestGen-LLM's filters (builds, passes
reliably, adds coverage) keep about a quarter of its tests.

For a line of a function, the question also says what must hold for that line to run: the
conditions of the branches, loops, handlers and cases around it and the early exits before it,
read from the code (SymPrompt's path constraints, approximated without running anything). A
draft that passes on the original and on the mutant alike is run once more on the mutant under
coverage, and its reason says whether it never reached the changed lines, reached only some of
them, or ran them all without checking what they do (CoverUp's coverage feedback). The project's
type checkers are not a filter: on the project's own tests pyright flags 4% of the modules and
ty 2%, and with attribute checks on 10%, while the grounding check flags none, and neither sees an
invented enum member under the project's settings (2026-09-28, 279 stored drafts). griffe, the
API reader behind mkdocstrings, was measured as the grounding check's resolver and flagged 45 of
the 125 test modules out of the box, so it is not used.

A mutant every draft without tools missed climbs a ladder. First the Draft test author with
tools writes one draft at each level of its Effort, then the Draft test author, last resort, the
verdict's own model, one at each of its levels, the next level only after the cascade rejected
the draft below. Each mutant climbs on its own, beside the others: it takes its next step as soon
as the cascade rejected its own draft and never waits for another mutant's, and at most as many
drafts are judged at once as the cascade runs processes. This is a pipeline first and an agent
only for what it cannot settle, as Agentless and
CoverUp's lookup tool suggest. Each works in a copy of the project (its code, tests and settings, no
history and nothing under the person's home) where it may read and search the copy, write the one
file its pin will be and run one command, the cascade's own check of that file: the project's
rules, five runs on the original, one on the mutant, what the test reached, and pyright's findings
as advice. Only the claude CLI serves these roles, since its permissions hold the tools to the
copy without asking anyone; agy cannot switch its own tools off. Whatever the model reports, the
cascade judges its final answer again. A pin the last resort wrote says so in its first lines and
on the Model roles page, so a later verdict model can look at it again.

A mutant every rung missed has its verdict asked once more, with what a person would look up
next: every call of the function across the project's source, each with the function around it,
and how the names those callers use are built. A branch no caller can take cannot be observed
where the requirement is observed (a contextual equivalent, in GEM-LLM's terms), so the verdict
then answers irrelevant and cites the caller lines that show it, and its review must agree, as
for any suppression; a caller that reaches the change keeps the pin, and the verdict names that
caller for the next climb. A mutant still pinned after that waits for the person. The Model
roles page lists every pin verdict still waiting for its pin, with where its ladder stands.

##### Model generation

| Role                           | Order | Backend           | Model                     | Effort         |
| ------------------------------ | ----: | ----------------- | ------------------------- | -------------- |
| Semantic mutant generator      |     1 | `antigravity-cli` | `gemini-3.1-pro-high`     | —              |
| Semantic mutant generator      |     2 | `antigravity-cli` | `gemini-3.8-flash-high`   | —              |
| Semantic mutant generator      |     3 | `claude-cli`      | `claude-sonnet-5-5`       | `high`         |
| Draft test author              |     1 | `antigravity-cli` | `gemini-3.8-flash-medium` | —              |
| Draft test author              |     2 | `antigravity-cli` | `gemini-3.1-pro-high`     | —              |
| Draft test author              |     3 | `claude-cli`      | `claude-sonnet-5-5`       | `low` → `high` |
| Draft test author with tools   |     1 | `claude-cli`      | `claude-sonnet-5-5`       | `medium`       |
| Draft test author, last resort |     1 | `claude-cli`      | `claude-opus-5-5`         | `xhigh`        |
| Survivor verdict               |     1 | `claude-cli`      | `claude-opus-5-5`         | `xhigh`        |
| Survivor verdict review        |     1 | `antigravity-cli` | `gemini-3.1-pro-high`     | —              |
| Survivor verdict review        |     2 | `antigravity-cli` | `gemini-3.8-flash-high`   | —              |

Semantic mutants, their draft tests and the verdicts on survivors come from a model called
through one adapter (ADR_0004). Antigravity serves Gemini and Claude models from two quotas,
a large one for the Gemini family and a smaller one for every other model. On Google AI Pro
a week of the smaller one took about 64 of the pilot's calls and a week of the Gemini one
about 920 (2026-09-28). Since 2026-10-01 Antigravity's Gemini models come first wherever they do
the work as well, the person's balancing of the quotas: several Antigravity accounts now carry
the volume, and a run moves to the next account when one runs out. The Claude subscription
serves what only it can (the draft author's rungs with tools, the assessor of another family
than Gemini) and the most critical roles (the verdict and the last resort), and answers where a
Gemini call is deferred. At the draft author's first rung Gemini 3.8 Flash kept about as many
drafts as Sonnet 5.5 (33 of 106 against 147 of 464, the drafts to 2026-09-30). A draft's retry is
asked one level up the same model's ladder where it has one, else of the next model. No role uses
Antigravity's smaller pool: its one assessor model never answered. Which model a role asks
first changes no stored answer: a proposal counts while its inputs are unchanged, a draft is
judged by running it, and a verdict is bound to its question. Each role tries its backends in order. A backend that is unavailable (not
signed in, account not eligible) or whose budget defers the call is skipped for the next.
Two channels work at once: while the model a call would ask first runs as many calls as its
pool takes, a later model of the role on another pool that has room answers it, so the Claude
subscription and Antigravity answer side by side; the order decides who answers first while
both have room, and each channel's budget below keeps its reserve (to spare a channel, raise
what it keeps free). A `claude-cli` call runs without tools, plugins, MCP servers or memory, with a replaced
system prompt and a JSON schema; only a call of the draft author's rungs with tools works in its
copy of the project with the tools that copy allows. `agy` cannot be started without its tools, its own system
prompt or its conversation history: the adapter tells it to answer from the text alone,
puts the system text before the prompt, and refuses a call that reaches for a tool. Every
answer is validated again on receipt. Which Claude subscription a call uses is the machine's
choice, a named profile of the CLI with its own sign-in (`model_generation.py profile`), and
every ledger row names it by a label that carries no profile name; the windows the budget
reads are that subscription's. When the sign-in in use has no room left in its windows, the run
probes the machine's other signed-in profiles, once each, and moves to one that has room; the
chosen profile comes first.

The Effort column sets a Claude model's reasoning effort by flag, and every ledger row records
the level its call asked for. An Antigravity model names its level in its id; an empty cell
leaves the backend's default: Antigravity's for Opus 4.6, whose id names none, and Claude
Code's for Sonnet 5, `high` (Claude Code's model configuration), the level of the answers it
stays listed for. No call reads the person's settings, since `--safe-mode` keeps a level saved
there for a model: from 2026-09-26 to 09-28 one saved in the CLI's own sign-in ran the first
135 verdicts at `xhigh`, the level the verdict now asks for by flag, and the 331 after them,
through the pilot's profile, ran at Claude Code's default for Opus 5.5, `medium`. Both levels
passed the verdict canaries, and every verdict stands; the Model roles page shows the level of
each call. A judge (the verdict, its review, an assessor) and the generator answer at one
level: a judge's level is part of what its canaries and calibration measured, and execution
checks a generated defect's form, not whether it matters. The draft author's rungs, whose every
answer execution checks in full, may climb a ladder of levels: a draft's retry is asked one
level up a model's ladder, and each rung with tools asks one draft at each of its levels before
the mutant climbs a rung. So Anthropic advises for work with a checker: run low and rerun the
failures higher, in its coding runs the same pass rate for half the cost. A ladder keeps only
levels far enough apart to differ, since every level is one more round for a mutant it fails
(the person's rule, 2026-09-29): the retry goes from `low` straight to `high`; the rung with tools
answers at `medium`, where it kept 24 of its 32 drafts; the last resort answers at `xhigh`, since
at `high` it kept none of 3 (the drafts of 2026-09-27 to 09-29). A ladder answers its
role's canaries from its lowest level up until a level passes, so a question starts at the
lowest level that passed, the levels above it answer without canaries (a level passing shows the
model can do the task, and execution still checks every answer above it), and a new model finds
its own lowest level.

###### Generation budget

| Budget                         | Limit |
| ------------------------------ | ----: |
| 5-hour window                  |  100% |
| Weekly window                  |  100% |
| Calls per run                  |   200 |
| List price per call            | $0.50 |
| List price per call with tools | $5.00 |
| Draft attempts per mutant      |     2 |
| Parallel calls to start with   |     8 |
| Parallel calls at most         |    16 |
| Smaller-pool calls per week    |    30 |
| Antigravity quota kept free    |    0% |

Every call appends one row to the consumption ledger. The row records the role,
backend, model, outcome, tokens, the list-price equivalent where the backend reports
one, the duration and the plan windows. A window at or above its limit, or a run that
reached its call limit, defers the call; a backend that reports no windows is bounded by
the call limit alone. A call whose backend reports its list price stops at its price cap, a
fuse against a call that runs away rather than a price list: the Test Plan's cap for a call with
or without tools, or three times the most expensive answered call of its role, whichever is
larger, so the cap follows the models' prices when they change. A call that reaches its cap is
asked once more at twice the cap; one that reaches that too is asked of the role's next model,
and a rung of the draft author's ladder climbs as after a rejected draft. The Model roles page
gives each role's cap in force beside its most expensive answered call, and every call a cap
stopped. Since 2026-09-28 both window limits stand at 100%, the person's
decision to be reviewed later: a call is deferred only when its window is full, so the
pipeline no longer leaves room for the person's own work on the same subscription. Where
agm keeps several Antigravity accounts (its multi-account switcher), each run reads what every
account has left of each quota, Gemini Pro, Gemini Flash and the one Claude and GPT share, and
moves agy alone, never the person's IDE, to the account with the most left once the one in use
is down to the share the Test Plan keeps free; a call its quota rejects is asked again on
another account, and when the run ends agy is back on the account it used before. Which account
agy uses is what its own credential store holds, as `agm sync` reads it, not agm's list, which
on 2026-09-29 named the second account while the store still held the first: a switch counts once
the store holds the new account, and a refusal counts against the account the store confirms. An
account agm reports switched while the store keeps the account it had (two of five on 2026-10-01) is
passed over for the next one with quota left, for the rest of the run.
agm reads an account's short window, not its week: a confirmed refusal that says when its quota
resets keeps that quota spent on its account until then, in the next runs too. Every account has
a weekly quota of its own. The accounts are alike: a run works on the one agy was left on and
moves only when that one cannot answer. An account Antigravity does not let in, such as one its
owner has yet to verify, takes no call of the run, not even the probe that starts it: every quota
of it counts as spent, the call goes to another account, and the next runs skip it without a call
for six hours. A canary no answer judged (an account or backend that could not be used) has not
failed: the model waits for its canaries to be asked again. A ledger row
names the account by a digest, and the probe's row records what each account had left. Without
agm the CLI reports neither quota, so the smaller pool is bounded by its calls in the last seven
days, counted from the ledger's calls actually made: 30 is about half of that pool's week and
leaves the rest to the person's own work on it. Independent questions (the assessors of
survivors, the calibration's pairs, the verdicts of a chunk of survivors, the drafts of one
round) are asked at once. Asking at once spends no more quota, only sooner, and no
subscription publishes how many calls it takes at a time, so each quota pool (the Claude
account, Antigravity's Gemini pool and its smaller one) finds it the way TCP finds its window:
it starts at its parallel calls to start with and doubles while every call at the limit is
answered; an overload answer (a 503 without capacity, a 429, a rate limit) halves it once per
burst, and from then on it grows by one at a time. It never passes the parallel calls at
most, which also keeps the machine's CLI processes in bounds. Every ledger row records how
many calls its pool ran at once and under which limit. A deferred, rejected or invalid generation is never a pass. The
target keeps no current proposal, and its class stays UNKNOWN. Generation runs only on
request and only for targets whose proposals are missing or stale; the gate, the cascade
and the portal build never call a model. A proposal or draft names the call that
produced it, and the gate recomputes it from the stored response.

##### Survivor judgement

| Assessor | Order | Backend           | Model                   | Effort                    |
| -------: | ----: | ----------------- | ----------------------- | ------------------------- |
|        1 |     1 | `claude-cli`      | `claude-sonnet-5-5`     | `low` → `medium` → `high` |
|        2 |     1 | `antigravity-cli` | `gemini-3.1-pro-high`   | —                         |
|        3 |     1 | `antigravity-cli` | `gemini-3.8-flash-high` | —                         |

A survivor is a mutant that every passing test of its contract lets through, rule or
semantic (ADR_0005). A symbolic search (CrossHair) over a typed harness of the original and
the mutant looks for an input that tells them apart, then every assessor of the table
answers distinct (with an input), equivalent or unsure, with its confidence. The triage of a
contract whose survivors, answers and judgement settings are those of its retained triage is
read back; the others are judged at once, as many as the cascade runs, and the questions of every
contract go to the assessors at once. An assessor
answers through its first model that can, as a role does: a later one only when the ones
before it are deferred, unavailable or not calibrated yet. A model whose Effort is a ladder of
levels is the search for its lowest level that meets the calibration floors: each level answers
as a model of its own, a level that misses the floors does not answer, and the calibration asks
the next level only then, in the same run. Sonnet 5 and Opus 4.6 left the first assessor on
2026-10-01: no current answer of the triage rested on them. The assessors
see the parameters as the code declares them and how the project's types the target takes
or names are built; an input may use any of the project's dataclasses, exceptions and enum
members. The question shows both versions as code, not the requirement: whether two versions
behave the same does not depend on it. Behaviour is what CrossHair's diffbehavior compares: what
the target returns, what it leaves in its arguments and the exception it raises. The question
names an argument only when its type lets a call change it (not a number, a text, a tuple, an
enum member or one of the project's frozen dataclasses), so a question about any other target
reads as before. Until 2026-10-01 it asked only for the return value and the exception, and an
assessor that followed it called a pin-proven mutant that changes its argument equivalent. Every answer cites, copied word for word from the code
it was shown, the lines it rests on, one of them a line the change touches; an answer whose
sources are not in its question does not count and its assessor is asked again. None of this
can make a survivor caught. An input counts only when execution confirms it: called with
it twice, each version repeats itself, and the original and the mutant return different
values, leave their object or an argument that can change in different states or raise
different exception types. A clock
reading or a memory address is not a difference. A semantic survivor with a confirmed input is
distinguished. A rule survivor keeps its outcome and gains the input as its test goal. An
assessors' equivalent is never a proof. When every assessor judges a survivor equivalent
with a confidence above the calibrated threshold, it is labelled likely equivalent and stays
UNKNOWN, or survived for a rule mutant, until its verdict is recorded (below).
Otherwise it is labelled unsure. A survivor that cannot be called from typed arguments, such
as an asynchronous method or a method of an object that needs a running router, is not
judged, and its row says why. Nor is a target that reads the environment (environment
variables, files, the locale, the clock, randomness, the network), in its own code or through a
function of its module or a method of its class it calls: the harness cannot vary what it
reads, so its survivors go to the verdict with the whole context. The assessors come from two model families, Claude and
Gemini, and a label needs all of them that take part, so one family's shared blind spot does not
label a survivor alone. An assessor none of whose models meets the calibration floors takes no
part until one does, though what it answered before stays in the judgements it is in; a label
then needs at least two assessors from at least two families, and a verdict does not wait for
it. Since 2026-09-29 Gemini 3.8 Flash misses them: of the real survivors a pin proves distinct it
called 16 of 104 equivalent, and the Claude assessor and Gemini 3.1 Pro judge.

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
assessor's first calibrated model answered the triage's own question about them. Only those are asked the triage's
question, so only they stand for the survivors it asks about. The hand-made pairs are easier than real survivors (on the survivors
the pins proved distinct, single assessors called some equivalent that none of the labelled
pairs had them call), so the observed pairs carry the rate. A survivor is labelled likely
equivalent only when its lowest assessor confidence is above the threshold, which at most the
false-equivalent rate of the distinct pairs exceed. A model counts for its assessor once it
answered every labelled pair and every observed pair the first such models answered, and a
level of a ladder once it also meets the calibration floors, so a new or replaced model costs
one pass over the pairs for each level it climbs, and the calibration asks only what is
missing. Each combination of usable models, one per assessor, gets its own threshold
(Mondrian conformal), and the highest labels, so a label keeps the rate whichever models
answered. The assessors' answers on the pairs are frozen and replayed by the qualification.
A change of assessor, model, level, prompt or labelled pairs leaves the ensemble uncalibrated
until the calibration runs again. An answer counts only for the question it answered, a labelled
pair's as the record names it and an observed pair's as the triage stored it: when a question
changes, every model answers the new one, and a model that missed the floors on the old questions
is measured anew.
Rule survivors are judged on request, apart from the campaign.

##### Survivor verdicts

Every judged survivor, and every mutant no test of its contract reaches, gets a verdict from
the Survivor verdict role (ADR_0006), once its judgement is complete: a survivor still waiting
for an assessor's answer gets none yet, since its question would grow by that answer and the
verdict and its review would be asked twice. The verdict model sees the requirement and its criteria,
the Feature and Goal it serves, both versions of the code, the survivor judgement and any
input execution confirmed; for an unreached mutant, that no test runs its line. A verdict
that would take a mutant out of its class, equivalent or irrelevant, counts only when the
Survivor verdict review, a model of another family asked the same question, agrees: a panel
of models from different families is less biased toward its own (PoLL). When the review does
not agree, the mutant is pinned. The verdict and the review each cite what they rest on,
copied word for word from the question: the words of the requirement, Feature, Goal or criterion
the verdict turns on and at least one line the change touches. A check finds every source in the
question; an answer that breaks it, or another rule the schema cannot state, does not count and
is asked once more, saying what broke. Every stored question and answer a record names is
published beside the {doc}`Model roles <model-roles>` page, which also counts the answers
whose sources do not hold up, and the explorer links each survivor's.

A suppression outlives the model that decided it. When the model or level the verdict or its
review asks first is not the one that answered a suppression that counts, one in ten of that
answerer's suppressions, those whose key hashes lowest with the current model, is asked again
of the role as it now stands, on the next `--decide-survivors`: a changed judge shows on a sample
of what the old one took out of its class, not only on the canaries. A re-check that does not
uphold its suppression pins the mutant; the Model roles page shows each sample and its answers.
When a sample disagrees, the person decides whether the rest of that answerer's suppressions are
asked again, since that spends the verdict's budget.

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

A pin often kills its neighbours too. `--subsume-pins` runs every pin of a contract against every
mutant the contract's pins pin, in a copy of the project, and keeps a greedy set cover of that
kill matrix: each step the pin that kills the most mutants still uncovered (Chvátal's heuristic,
as PRIMG and the LLM-assisted minimization of FoadG reduce generated tests by the mutants they
kill). A pin whose mutant the kept pins kill is removed: its record keeps the pin and names the
pins that kill its mutant, and its file waits beside the record. The matrix cannot see a mutant
that only a removed pin killed without pinning it, so the campaign after the removal is the
check: the next `--subsume-pins` brings back, as they were, the fewest removed pins that kill
every mutant the campaign caught before the removal and misses now, and a pin brought back
stays. A removed pin whose mutant survives again comes back first when its verdict is decided,
judged again from its stored draft without asking a model. `--subsume-pins --verify` only
brings back what earlier removals cost and removes nothing: the last pass before a gate, since
another removal would need another campaign to check it. A pin the cascade keeps alone can still
fail in the project's full test run, where the tests before it run too: `--reject-pin` takes it
back with its reason, and its stored answer is never judged again. Subsumption runs once a milestone,
not in every cycle.

###### Model canaries

A model's answers count for a role only after it passed that role's canaries, a few cases
with a known outcome. The generator must propose a well-formed, confined defect for a canary
target; the draft author, and each of its rungs with tools in a copy of the canary's project,
must write a test the cascade keeps for a known distinguishable mutant; the verdict model and the verdict review must pin a known gap, judge a known
equivalent equivalent and escalate a known product decision, and judge three real survivors
as their records settled them: one a kept pin proves distinct, one both families judged
irrelevant and one both judged equivalent; asked again with the callers in view, they must
judge a change no caller reaches irrelevant and pin one a caller reaches. An assessor must meet the
calibration floors: an input confirmed for at least 80% of the labelled distinct pairs, and
at most the false-equivalent rate of all distinct pairs, labelled or observed, judged
equivalent; an assessor model that misses them does not answer, and at a level of a ladder
the calibration asks the next level. A ladder of levels answers its role's canaries from its
lowest level up until one passes; the next level is asked only after the one below answered
every case and failed. The canary questions of a round are asked at once, as the assessors'
are; each backend still takes its parallel calls at a time. A change of model, level, question or canary set asks for the canaries
again: a question the model already answered at that level is judged again from its stored
answer, as a stored pin draft is, and only new and changed questions are asked; until they pass, the role skips that model at that level and the levels above it. A canary the backend did not answer (its quota, its capacity, the time
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
