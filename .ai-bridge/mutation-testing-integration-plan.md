# Mutation testing integration roadmap — llm-router local pilot

Status: planned after DEPTH-P18\
Date: 2026-09-14\
Scope guard: implement and validate only inside `llm-router` while the pilot moves quickly. Do not roll this work to other consumers yet. Preserve every generic contract, temporary workaround, migration candidate, and cleanup trigger here so later Ternforge platform extraction does not lose prototype knowledge.

## Authoritative pilot operating rule

Until the user explicitly closes the llm-router pilot, this plan is executed **only inside llm-router**. Platform repositories named below are future ownership notes, not current work items. A platform repository may be touched during the pilot only when a concrete llm-router experiment is blocked and no local workaround can test the hypothesis; the intervention must be minimal and recorded in `.ai-bridge`.

A premature E1/E2/E3/E4 extraction attempt was cleaned up on 2026-09-14. All platform-side pilot branches/changes are discarded; only the technical findings are retained in `mutation-testing-platform-extraction-manifest.md`. Do not resume extraction until explicit post-pilot authorization.

## Why this exists

DEPTH-P18 proved the basic chain:

`Requirement/TREQ → Test Strength → Mutation Testing Report Schema 2.0 → Mutation Testing Elements → exact pytest/Allure → source`

The next goal is to turn that successful local spike into one integrated verification workflow without conflating different questions:

- **Verification Health Map** = does retained verification currently pass?
- **Verification Depth Map / Test Strength** = can the linked tests detect behavior-changing faults in the implementation they claim to verify?
- **Mutation Analysis** = which concrete mutants survived and what action is required?
- **Verification Assurance / Traceability** = why this evidence belongs to this contract, whether it is fresh, and where to drill down.

Mutation testing must strengthen the existing Sphinx-Needs graph; it must not create a second requirements graph and individual mutants must not become Needs.

## External practice lineage

### Google — changed-code mutation and signal filtering

Reference: Practical Mutation Testing at Scale: A view from Google\
<https://research.google/pubs/practical-mutation-testing-at-scale-a-view-from-google/>

Adopt:

- mutate changed code in review instead of blindly mutating the whole repository on every run;
- filter low-value mutation points;
- limit mutation density/work presented to developers;
- collect operator history and prefer historically useful operators.

Ternforge adaptation:

- use changed implementation lines + the existing Sphinx-Needs/IMPL graph to derive affected contracts;
- keep the full/audit campaign as a separate periodic mode;
- do not use operator-history filtering until we have enough local evidence.

### PIT / ArcMutate — coverage-first targeting, history, PR actionability

References:

- <https://pitest.org/quickstart/basic_concepts/>
- <https://pitest.org/quickstart/incremental_analysis/>
- <https://docs.arcmutate.com/docs/github/overview.html>

Adopt:

- baseline coverage before mutation;
- run only tests relevant to the mutated code;
- reuse logically valid prior results when source/tests have not changed;
- make surviving mutants the actionable review signal, close to the changed source line.

Ternforge adaptation:

- Coverage.py dynamic contexts already provide per-test execution facts;
- requirement-linked tests remain the semantic evidence set for that requirement;
- other tests that incidentally cover/kill a mutant may be retained as diagnostics but must not inflate the requirement's Test Strength;
- changed-line survivors become the fast local/PR work queue.

### Stryker / Mutation Testing Elements — portable artifact and standard investigation UI

References:

- <https://github.com/stryker-mutator/mutation-testing-elements/blob/master/packages/report-schema/src/mutation-testing-report-schema.json>
- <https://stryker-mutator.io/docs/stryker-js/configuration/>
- <https://stryker-mutator.io/docs/stryker-js/incremental/>
- <https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/>
- <https://stryker-mutator.io/docs/mutation-testing-elements/implementing-real-time-reporting/>

Adopt:

- standard Mutation Testing Report Schema as the detailed retained mutation artifact;
- `coveredBy`, `killedBy`, duration and explicit mutant states;
- Mutation Testing Elements as the detailed browser UI instead of a Ternforge-specific mutation frontend;
- per-test coverage as the execution optimisation model;
- versioned/incremental result semantics.

Ternforge adaptation:

- keep MTE standard and isolated;
- put Ternforge provenance/freshness/contract attribution in a sibling campaign manifest and compact derived projections rather than forking the standard report schema;
- use SSE/live reporting only if real runtime UX later proves useful; it is not required for the first local implementation.

### mutmut — Python execution engine

Reference:
<https://mutmut.readthedocs.io/en/latest/>

Adopt now:

- keep mutmut as the Python mutation executor;
- `mutate_only_covered_lines`;
- relevant-test selection;
- incremental/cache behaviour;
- parallel execution;
- forkserver where llm-router/macOS runtime setup is fork-unsafe.

Do not make mutmut's internal cache or CLI output the portal source of truth. Convert the completed campaign into retained standard artifacts.

### Cosmic Ray — future scaling reference only

Reference:
<https://cosmic-ray.readthedocs.io/en/latest/tutorials/distributed/>

Use only as a later reference if mutation execution becomes large enough to need distributed workers. Do not add this complexity during the llm-router prototype.

______________________________________________________________________

## Target data flow

```text
Sphinx-Needs graph
GOAL → Capability → REQ/TREQ → IMPL
                         ↘ TEST
                            │
normal pytest run            │
├─ JUnit                     │
├─ Allure results            │
└─ Coverage.py dynamic contexts
          │                  │
          └──────────┬───────┘
                     ↓
            mutation scope resolver
          ┌──────────┴──────────┐
          │                     │
     diff campaign          full audit
  git base → head       explicit wider scope
          │                     │
          └──────────┬──────────┘
                     ↓
                  mutmut
                     ↓
       Mutation Report Schema 2.0
        per contract/safe scope
                     │
          ┌──────────┴───────────┐
          ↓                      ↓
 Mutation Testing Elements   Ternforge derived facts
 exact mutant/source/tests   score/delta/freshness/triage
          │                      │
          ↓                      ├────────→ Depth Map / Test Strength
 exact pytest → Allure           ├────────→ Mutation work queue
                                 ├────────→ Verification Assurance
                                 └────────→ Specification/coverage health
```

## Truth and attribution rules

1. **Normal execution and mutation execution remain different evidence.** Do not put mutants into Allure as fake pytest cases.
2. **Requirement Test Strength is based only on the requirement-linked tests.** An unrelated test killing a mutant is useful diagnostic information but not proof for the requirement.
3. **No false attribution.** If an implementation scope is shared by multiple contracts and cannot be resolved safely, show N/A/shared-scope evidence rather than inventing a contract score.
4. **No stale green.** Mutation evidence is valid only for the implementation/test/config revision it measured. A source/test/config change invalidates or marks the result stale until rerun.
5. **No global vanity gate yet.** Low/Moderate/High are explanatory bands. The first actionable gate is changed-code/new-survivor based, not a project-wide score threshold.
6. **Mutants are artifacts, not Needs.** The Needs graph stores relationships to implementation/tests/evidence; thousands of individual mutants remain inside the standard mutation report.
7. **Suppressions are explicit evidence decisions.** Equivalent/noise/irrelevant mutants need a reason; suppression must not silently disappear from the report.

## Retained local artifact model

Prototype target under generated output:

```text
mutation-results/
  campaign.json                     # Ternforge campaign/provenance manifest
  summary.json                      # derived cross-contract projection
  contracts/
    TREQ_X/
      mutation-report.json          # standard schema 2.0
      index.html                    # standard MTE shell
    REQ_Y/
      mutation-report.json
      index.html
```

`campaign.json` should carry at minimum:

- campaign id and mode: `diff` or `full`;
- head SHA and, for diff mode, base SHA;
- mutated-source fingerprint/hash;
- requirement-linked test-set fingerprint/hash;
- mutmut version;
- adapter version;
- mutation config/operator-set hash;
- Coverage.py data/run identity;
- normal pytest/Allure run identity used for test links;
- started/finished timestamps and duration;
- contract/scope resolution status;
- stale/fresh determination inputs.

Keep the standard `mutation-report.json` conformant; do not add Ternforge-only required fields to it.

## Portal integration

### 1. Verification Depth Map — primary overview

Keep the existing three projections:

- Test Level;
- Representation Fidelity;
- Test Strength.

Improve Test Strength to expose:

- measured / unmeasured;
- fresh / stale;
- score band;
- killed / survived;
- **new survivors** versus baseline;
- score delta where a comparable baseline exists;
- campaign mode (`diff` or `full`).

Color continues to mean Test Strength only. Freshness/new-survivor state should use a small marker/badge, not overload the fill color.

Click behaviour:

- measured + fresh → exact contract MTE report;
- measured + stale → MTE still available, but visibly marked stale and not treated as current evidence;
- N/A/shared scope → no false mutation-detail target; tooltip explains why.

### 2. Mutation Analysis — operational work queue

Add one Sphinx/PyData-default page, not another bespoke dashboard.

Purpose: answer **“what mutation findings need attention now?”**

Show current campaign summary sorted by actionability:

- changed contracts with new survivors first;
- unresolved survivors;
- stale evidence;
- measured clean contracts;
- N/A/shared-scope diagnostics.

Per contract:

- current Test Strength and delta;
- new / resolved / existing survivors;
- campaign mode and freshness;
- links to Requirement/Assurance, MTE, exact source scope and relevant tests.

Use standard Sphinx table/cards/components. Detailed mutant browsing stays inside MTE.

### 3. Standard MTE report — forensic mutation detail

Keep the P18 standard UI:

- concrete mutant;
- source line/replacement;
- status;
- coveredBy/killedBy;
- Tests tab;
- exact pytest/Allure links.

Do not rebuild these controls in Sphinx.

### 4. Verification Assurance — contract evidence synthesis

Add a Mutation/Test Strength section to each relevant contract:

- latest current campaign;
- strength score and band;
- killed/survived;
- new survivor count;
- provenance/freshness;
- implementation scope attribution;
- link to MTE;
- link to mutation work queue filtered to the contract.

This is where Health, Depth and mutation evidence become understandable together without merging their semantics.

### 5. Specification / verification coverage health

Expose **mutation measurement coverage**, not a global mutation score:

- X / 44 contracts currently measured;
- fresh / stale / N/A counts;
- unresolved shared-scope attribution count.

This tells us whether the Test Strength map itself is sufficiently evidenced.

### 6. Allure integration

P18 already supports MTE → exact Allure.

Later in the local prototype, add the reverse direction without creating fake tests:

- enrich the retained normal Allure result/test evidence with a link or small attachment such as:
  - mutants covered;
  - mutants killed;
  - unresolved survivors covered;
  - “Open Mutation Analysis”.

This should be postprocessed into the original normal-test evidence after mutation analysis, not emitted as mutation test cases.

### 7. Navigation/read paths

Preserve the small number of human workflows already established:

**Operational failure path**
`Verification Health Map → exact Allure test → contract/assurance`

**Adequacy path**
`Verification Depth Map → Test Strength → MTE mutant → exact pytest/Allure → source`

**Review/action path**
`Mutation Analysis → new survivor → MTE/source → linked contract → linked tests`

No new isolated portal island.

______________________________________________________________________

## Implementation plan

### P19 — campaign provenance, freshness and baseline

Build first because every later delta/incremental decision depends on knowing exactly what was measured.

Implement locally:

- campaign manifest;
- stable local campaign id;
- source/test/config fingerprints;
- explicit `diff` vs `full` mode;
- baseline pointer;
- freshness calculation;
- standard summary projection;
- keep all three P18 reports schema-valid.

Acceptance:

- change a source/test fingerprint in a controlled probe and verify the old score becomes **stale**, never current green;
- restore revision and verify freshness returns;
- inspect campaign manifest and trace every score to report + test run + commit.

User-visible benefit:

- the site stops showing mutation numbers without revision context;
- every score answers “from exactly what code/tests/run did this come?”

### P20 — fast changed-contract execution

Implement Google's/PIT's fast path:

- explicit base/head range;
- changed source lines;
- resolve changed implementation scope through current IMPL/contract graph;
- intersect candidates with Coverage.py dynamic contexts;
- for each contract, run only its linked tests that actually cover the mutant;
- retain non-linked covering tests only as diagnostics;
- use `mutate_only_covered_lines`, mutmut cache/incremental behaviour and forkserver;
- retain a separate `full` campaign mode for audit.

Do not yet auto-filter operators using historical quality; only record the data.

Acceptance:

- run a controlled historical or temporary diff;
- prove unchanged contracts are not unnecessarily mutated;
- compare wall time and number of mutants/tests against a wider run;
- prove exact changed contract → mutant → linked test mapping;
- prove a test outside the contract cannot raise that contract's score.

User-visible benefit:

- mutation testing becomes fast enough for routine work instead of only periodic manual auditing.

### P21 — baseline delta, survivor triage and suppressions

Add actionable semantics:

- classify survivors as `new`, `existing`, `resolved`;
- triage state for unresolved findings;
- explicit suppression/ignore record with reason;
- optional owner and expiry fields for future multi-user/platform use;
- retain suppression reason into report/summary where standard fields permit;
- operator statistics: generated, killed, survived, suppressed/irrelevant, duration.

Initial policy:

- no project-wide score gate;
- local readiness signal = **new unresolved survivor in changed scope**;
- informational Test Strength bands remain.

Acceptance:

- create one known survivor, verify it appears as New;
- suppress it with a reason, verify it remains visible/auditable rather than disappearing;
- kill it with a test and verify it becomes Resolved;
- verify baseline/delta remains reproducible after rerun.

User-visible benefit:

- instead of “59.8%”, you get a concrete work queue: what got worse, what was fixed, and what was consciously accepted.

### P22 — integrated portal UX

Wire the derived facts into the portal:

- Depth Map markers/delta/freshness;
- new Mutation Analysis work-queue page;
- Verification Assurance mutation section;
- mutation measurement coverage in health/coverage view;
- MTE links;
- exact Allure links;
- reverse Allure → Mutation Analysis link if cleanly achievable without custom Allure UI.

UI constraint:

- use stock Sphinx/PyData/Sphinx-Needs components wherever possible;
- MTE remains the stock detailed mutation UI;
- no custom card system if a default component can express the information.

Acceptance:
physically walk all three user paths in browser:

1. Health → failing/passing test → Allure → contract.
2. Depth/Test Strength → measured contract → MTE → concrete mutant/source → exact Allure test.
3. Mutation Analysis → New survivor → MTE → source → contract/assurance → linked tests.

Also test:

- fresh vs stale;
- diff vs full;
- new/resolved/suppressed;
- N/A/shared scope;
- light/dark;
- reload;
- overflow;
- browser console/errors.

User-visible benefit:

- Health says **does it pass?**
- Depth says **how strong is the proof?**
- Mutation Analysis says **what exactly should I improve now?**
- Assurance says **why should I trust/attribute this evidence?**

### P23 — operator feedback and performance tuning

Only after several real campaigns:

- rank mutation operators by actionability and cost;
- identify noisy mutation points/categories;
- compare survivor usefulness rather than blindly maximizing mutant count;
- optionally cap/choose mutations for diff mode following Google's historical-performance approach;
- preserve wider/full mode so optimisation cannot silently erase audit capability.

Acceptance:

- operator table is based on retained campaigns, not opinion;
- filtering decision has before/after mutant count, runtime and survivor/actionability evidence;
- no operator is removed globally from a tiny sample.

### P24 — local mutation implementation checkpoint / post-pilot migration ledger

Before any cross-consumer rollout:

- re-run complete local acceptance;
- classify every file/contract as generic vs llm-router-specific vs disposable prototype glue;
- record exact target platform owner;
- record cleanup trigger for every local workaround;
- freeze a migration checklist before deleting local prototype logic.

No other consumer is updated until the llm-router pilot is accepted.

______________________________________________________________________

## Future Ternforge ownership map

This is a migration hypothesis to preserve during the pilot; confirm exact repo boundaries only after the local design is accepted.

| Capability proven in llm-router                                                | Likely platform owner later                                                                          | What remains consumer-specific               |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| pytest nodeid / execution identity / Coverage.py per-test facts                | `py-testkit`                                                                                         | test code and project-specific pytest config |
| mutation executor invocation + generic test-selection adapter                  | likely `py-testkit` or a small generic mutation component if separation proves necessary             | chosen Python engine/config overrides        |
| mutation report-schema adapter and derived contract facts                      | `ternforge-tooling-docops` for retained DocOps projection; execution part may stay with test tooling | consumer graph data                          |
| Sphinx pages, Depth integration, Assurance integration, Mutation Analysis page | `ternforge-tooling-docops`                                                                           | titles/project navigation and actual facts   |
| IMPL ownership / suppression structural validation                             | `py-policy`                                                                                          | concrete mappings/suppressions               |
| diff/full CI mode, baseline artifact retrieval, cache/orchestration            | `ternforge-infra-ci`                                                                                 | project CI opt-in/limits                     |
| reusable bootstrap/config                                                      | template-components → template-py-library only when pilot is stable                                  | llm-router-specific extras                   |
| thresholds/gating policy                                                       | platform default only after enough evidence                                                          | project overrides where justified            |

## Migration ledger fields

For every implementation step from P19 onward, append to this file:

- local file/artifact;
- why it exists;
- standard/reference it follows;
- generic or llm-router-specific;
- candidate platform owner;
- cleanup/replacement trigger;
- acceptance evidence;
- known limitation.

This is mandatory: no temporary prototype workaround may exist only in chat history.

## Implementation / extraction ledger

### P19 — campaign provenance + freshness

- **Local implementation:** `.ai-bridge/build-mutation-report-prototype.py`; generated `mutation-results/campaign.json`, `mutation-results/summary.json`, per-contract MTE wrappers, and `verification-test-strength-facts.json`.
- **Why it exists:** a Test Strength score must identify the exact implementation scope, linked tests, mutation config/engine and retained execution context that produced it; unchanged old scores remain forensic evidence but become stale rather than current.
- **Practice lineage:** PIT/Stryker incremental-analysis principle (reuse only when relevant code/tests/config are unchanged); Stryker separation of standard mutation report from runner/reporting metadata; content-addressed build/evidence provenance patterns.
- **Generic vs consumer-specific:** fingerprint/campaign/freshness model is generic; the three hard-coded llm-router contracts/scopes are prototype-only consumer data.
- **Candidate platform owner:** per-test/source execution identities in `py-testkit`; campaign and DocOps projection in `ternforge-tooling-docops`; baseline artifact retrieval/orchestration in `ternforge-infra-ci`; structural ownership rules in `py-policy`.
- **Cleanup/replacement trigger:** after llm-router UX and semantics are accepted and generic contracts exist in platform tooling, remove the hard-coded `CONTRACTS`, generated-HTML patching and temporary `setup.cfg` mutation configuration from the local adapter. Do not delete this local implementation before the platform acceptance reproduces P19 stale/fresh behavior.
- **Acceptance evidence:** full campaign `full-1618432f4429-0dd5b30724b2` completed in 61.706s, 3/3 measured contracts fresh; controlled implementation-scope change made exactly one contract stale without rerunning mutants, visibly propagated to Depth Map and MTE; restore returned 3/3 fresh; light/dark, overflow, clean reload, browser errors and HTTP artifact links checked physically.
- **Known limitations:** first retained campaign has no predecessor, therefore `baseline_campaign_id=null`; P20 adds changed-contract execution and P21 makes baseline delta/survivor state actionable. Current page patching is intentionally generated-only prototype glue.

### P20 — changed-contract / diff campaign

- **Local implementation:** same local adapter now resolves `base ref → changed implementation scope / changed linked test → selected contract`, records selected/skipped contracts and changed line/test details in campaign provenance, and runs mutmut only for selected contracts.
- **Why it exists:** routine mutation testing must follow Google/PIT's changed-code/test-impact model instead of repeatedly mutating every measurable contract.
- **Practice lineage:** Google changed-code mutation testing; PIT/ArcMutate incremental/change-focused execution; Stryker per-test coverage and incremental selection.
- **Generic vs consumer-specific:** diff/scope-selection algorithm is generic; current hard-coded `CONTRACTS` mapping is llm-router-only prototype data standing in for future Sphinx-Needs/IMPL graph resolution.
- **Candidate platform owner:** generic diff/base/cache orchestration → `ternforge-infra-ci`; per-test execution/coverage selection facts → `py-testkit`; graph-to-contract scope projection → `ternforge-tooling-docops`; ownership constraints → `py-policy`.
- **Cleanup/replacement trigger:** remove local resolver only after generic platform resolution reproduces clean-tree 0-selection, exact changed-contract selection, linked-test-only execution and mixed provenance for selected/skipped contracts.
- **Acceptance evidence:** clean `base=HEAD` = 0/3 selected after fixing pytest-bdd fallback; one controlled ToolRegistry change = exactly 1/3 selected at changed line 77. Real diff campaign ran 31 mutants in 27.834s vs full 233 mutants in 61.706s, skipped two contracts, retained their previous full provenance, and linked to the previous full campaign as baseline. Physical Depth hover showed Fresh/diff only on ToolRegistry and Fresh/full on skipped contracts; MTE provenance links matched. Every report test and every `coveredBy` was verified to be a declared linked test. Final restored full campaign = 3 fresh / 0 stale and end-to-end MTE→Allure still works.
- **Known limitations:** current local resolver has only three uniquely attributable pilot scopes; shared scopes stay N/A. One transient macOS/uv mutmut exit=1 occurred once during full rerun; no silent retry was added, immediate explicit reproduction succeeded, and the final full rerun passed. Distributed/cache reuse and operator filtering remain later work.

### P21 — baseline delta, triage and auditable suppressions

- **Local implementation:** stable mutant fingerprint records, per-contract `baseline_run_id`, unique `run_id` separated from content-addressed `campaign_id`, retained `triage.json`, and version-controlled local suppression ledger semantics.
- **Why it exists:** a raw percentage cannot tell whether a change introduced a new weakness. The operational signal is the delta in concrete surviving mutants for the exact changed contract, while raw Test Strength remains an explanatory adequacy metric.
- **Practice lineage:** Google/ArcMutate changed-code actionability; PIT/Stryker incremental history; standard mutation states remain in Mutation Testing Report Schema/MTE while Ternforge adds requirement attribution and review state beside the standard artifact.
- **Generic vs consumer-specific:** fingerprint, run/campaign provenance, delta/triage and suppression semantics are generic; the three llm-router scopes and acceptance probes are consumer-local.
- **Candidate platform owner:** execution/mutant identity → test tooling; retained campaign/triage/portal projection → `ternforge-tooling-docops`; baseline artifact retrieval/orchestration → `ternforge-infra-ci`; suppression validation → `py-policy`.
- **Cleanup/replacement trigger:** remove local triage/suppression/run-history code only after platform tooling reproduces content identity vs run identity, per-contract baselines across mixed full/diff history, new/existing/resolved classification, and reason-retaining suppressions.
- **Acceptance evidence:** ToolRegistry controlled weakening generated exactly 3 new survivors and -9.7 pp; one suppression remained visible/auditable and reduced only actionable count; restoring the assertion resolved exactly those 3 and returned +9.7 pp. Two identical final full runs share one campaign id but have distinct run ids; second run points to the first run as baseline and all three contracts report comparable Δ 0.0. Final site state = 3 fresh / 0 stale / 0 new, no suppression probe, tracked tree clean, physical MTE→Allure and light/dark/overflow/error QA passed.
- **Known limitations:** operator-quality learning is intentionally deferred to P23; P21 does not yet provide the dedicated cross-contract Mutation Analysis work-queue page — that is P22.

### P22 — integrated portal UX and action work queue

- **Local implementation:** generated `mutation-analysis.html` in the stock PyData/Sphinx shell, navigation links from the normal portal, per-contract mutation blocks in Verification Assurance, and mutation measurement coverage in Specification Health. MTE remains the standard mutant/source/test forensic UI.
- **Why it exists:** reviewers need one coherent path from current health to adequacy to concrete mutation action, not an isolated mutation dashboard or console-only artifact.
- **Practice lineage:** Stryker/MTE separation of summary vs detailed mutant exploration; ArcMutate/GitHub-style action queue for changed survivors; existing Ternforge Health/Depth/Assurance separation of independent evidence dimensions.
- **Generic vs consumer-specific:** page structure, ordering, provenance/freshness/delta presentation and portal links are generic; current hard-coded llm-router facts and HTML post-processing are pilot-only.
- **Candidate platform owner:** Sphinx/PyData page generation and Assurance/coverage projections → `ternforge-tooling-docops`; run/action facts → test tooling / `ternforge-infra-ci`; structural suppression rules → `py-policy`.
- **Cleanup/replacement trigger:** remove local shell cloning/HTML patching after DocOps natively renders the same three user paths and browser acceptance reproduces New/Suppressed/Resolved/Fresh/Stale/N/A states.
- **Acceptance evidence:** real ToolRegistry diff with weakened linked test produced 3 new survivors and moved ToolRegistry to first position with Attention; one explicit suppression reduced only actionable count and stayed auditable; restoring the assertion showed exactly 3 Resolved and +9.7 pp. Final clean full run = 3/44 measured, 3 fresh, 0 stale, 0 new. Physical paths verified Health→Mutation Analysis, Mutation→Assurance, Mutation→MTE→exact Allure Passed, Specification Health→measurement coverage, Depth measured→MTE and shared N/A no-navigation. Light/dark/no-overflow/errors and legacy producer cross-highlight regression passed; Show Source formatting defect found and fixed during QA.
- **Known limitations:** only three uniquely attributable contracts are measured in the pilot; reverse Allure→Mutation Analysis is optional and not implemented; current local generator patches built HTML rather than owning Sphinx directives/templates.

### P23 — retained operator feedback and performance evidence

- **Local implementation:** per-contract elapsed time on new mutation runs plus retained `mutation-results/operator-feedback.json`; Mutation Analysis exposes observed full/diff runtime and derived mutation-family volume/survivor/action-event/cost diagnostics.
- **Why it exists:** optimisation must be driven by historical actionability and cost, not by mutant count or an arbitrary operator preference.
- **Practice lineage:** Google's historical-performance/operator-selection principle, adapted conservatively to mutmut's available metadata; full audit remains the control mode.
- **Generic vs consumer-specific:** timing/history aggregation and actionability model are generic; current family classifier is provisional local glue because mutmut does not expose stable engine-native operator labels in the retained report.
- **Candidate platform owner:** timing/mutant facts → test tooling; retained historical performance and CI mode decisions → `ternforge-infra-ci`; DocOps projection → `ternforge-tooling-docops`.
- **Cleanup/replacement trigger:** replace derived family heuristics when stable engine operator metadata or a versioned Ternforge taxonomy exists; never port a hard-coded filter list from this pilot.
- **Acceptance evidence:** 11 retained runs / 9 with mutant records / 8 unique campaign contents; latest full 56.774s with three directly timed contracts (23.792s, 13.734s, 19.234s). Diff median 27.834s across 5 runs; full median 61.260s across 6. Mutation Analysis physically renders 8 families ordered by action evidence/cost, opens retained JSON, and clearly labels proportional cost estimation and acceptance-probe contamination. Light/dark/no-overflow/errors pass.
- **Decision:** **no mutation family filtered or capped**. `full_audit_preserved=true`, `diff_mode_filtering_enabled=false`. The sample is too narrow for safe tuning; P23 records evidence for later decisions rather than manufacturing one now.

### P24 — local mutation implementation checkpoint and migration ledger

- **Local closure artifacts:** `.ai-bridge/validate-mutation-pilot.py` and `.ai-bridge/mutation-testing-platform-extraction-manifest.md`. The manifest inventories every retained generated mutation artifact, every remaining local control/ledger file, and all 44 Requirement/TREQ contracts.
- **Frozen retained state:** full run `full-1618432f4429-2a6537110da3--1789401847015433000`; 56.774s; 3/44 measured; 3 fresh / 0 stale / 0 new unresolved / 0 suppressed; build `p24-local-1`; mutation-semantics compatibility `p21-local-2`.
- **Structural gate:** PASS. It enforces Schema 2.0, killed/(killed+survived), declared-linked-test-only report/test coverage, comparable non-self baselines, direct contract timing, two shared-scope N/A diagnostics, no P23 filtering, portal wiring, complete 44-contract extraction classification, complete generated-artifact inventory, no temporary mutmut/config/cache debris, and no tracked changes outside `.ai-bridge`.
- **Physical closure paths:** (1) Health → ToolRegistry Allure scope → exact test hash → Passed + `TREQ_TOOL_REGISTRY`; (2) Depth/Test Strength → ToolRegistry → MTE → exact Allure Passed; (3) Mutation Analysis → ToolRegistry → MTE source `tools.py` → physical survivor drawer at line 124 (`args=dict(call.args) → [removed]`, covered by one test) → ToolRegistry Assurance → scoped Allure → exact Passed test. Reload and physical light/dark remain overflow-free.
- **QA-tool caveat:** `agent-browser errors` retains an old MTE parser trace globally even on `about:blank` before a site is opened; fresh page script inspection confirms Mutation Analysis does not load MTE. This is recorded as browser-tool buffer contamination, not application evidence.
- **Cleanup performed:** removed acceptance-only `__pycache__`, write probe, screenshot and P19 pid/log/exit debris. Seven substantive `.ai-bridge` files remain and are individually classified in the extraction manifest.
- **Extraction ownership:** executor/report/fingerprint/timing → `py-testkit`; full/diff/cache/run/baseline history → `ternforge-infra-ci`; graph/portal/Assurance/coverage/MTE packaging → `ternforge-tooling-docops`; ownership and suppression validation → `py-policy`; durable methodology → `betabit-notes/ternforge/docs`. The contracts themselves remain llm-router Sphinx-Needs data.
- **Post-pilot ownership backlog, not active work:** E1 py-testkit → E2 infra-ci → E3 py-policy → E4 DocOps → E5 llm-router platform-parity migration → E6 local prototype cleanup → E7 explicit user-approved rollout decision. Do not execute this sequence while the pilot is active.
- **Scope guard:** P24 closed an implementation checkpoint only; it did **not** end the llm-router pilot and did not authorize cross-repository extraction.

### P25 — active-pilot cleanup and live operator usability

- **Scope correction:** a premature attempt to start E1–E4 platform extraction was discarded. The mutation branches/changes in py-testkit, infra-ci, py-policy and DocOps were deleted and all four owner repositories were verified back on clean `main`. The technical lessons remain only in `.ai-bridge/mutation-testing-platform-extraction-manifest.md` as post-pilot ownership notes.
- **Authoritative rule:** until the user explicitly ends the llm-router pilot, feature work stays in llm-router. A platform intervention is allowed only for a concrete experiment blocker that cannot be tested locally; it must be minimal, justified and recorded.
- **Prototype identity:** UI/build provenance is `p25-local-1`; mutation-semantics compatibility remains `p21-local-2`, so the accepted campaign/baseline identity is not reset by presentation changes.
- **Operator pain addressed:** a clean regression gate is no longer presented as “everything is fine.” The current page separates `Regression guard` from `Strength debt`, freshness and measurement coverage. Current retained state is 0 new unresolved, 93 known survivors, 3 fresh / 0 stale, 3/44 objectively measured; weakest measured contract is `TREQ_RATE_LIMIT_STATE` at 51.0%.
- **Consistent vocabulary:** existing baseline survivors are displayed as `Debt` in Mutation Analysis, Verification Assurance and the MTE bridge. `New` means regression, `Resolved` means previously surviving mutation now killed, `Suppressed` changes workflow actionability only, `Stale` means the evidence predates changed code/tests, and N/A is unmeasured/unattributable rather than zero/pass.
- **Live reading path:** Mutation Analysis now explains how Verification Health (observed failures), Verification Depth (level/representation/strength) and Mutation Analysis/MTE (specific wrong behavior missed by linked tests) fit together before the technical tables.
- **History/observability:** Recent campaign history surfaces retained New/Debt/Resolved signals and baseline IDs. The controlled ToolRegistry acceptance cycle is visible as `New 3` on run `1789400805519184000` followed by `Resolved 3` on `1789400951400402000`; both rows physically open the retained campaign JSON that contains the expected baseline/triage.
- **Physical browser acceptance:** work-queue Rate Limit → Assurance shows 51.0%, 51 killed / 49 survived, Fresh and Debt 49; Rate Limit → Allure opens the passing contract scope. ToolRegistry MTE shows Debt 3; exact pytest link opens hash `bd3b4e9acafbba5ecf530083b3cf17ae` with Passed + TREQ_TOOL_REGISTRY. Reload and physical light/dark switches have no horizontal overflow.
- **Browser-tool caveat retained:** Mutation Analysis does not load `mutation-test-elements.js` at all; the old MTE parser stack shown by `agent-browser errors` is a persistent tool-global buffer artifact already reproduced on blank pages, not an application error.
- **Structural gate:** the active-pilot gate now asserts the operator guidance, retained New→Resolved history, Debt terminology, linked-test-only mutation evidence, shared-scope N/A, provenance/freshness, cleanup residue and the post-pilot migration ledger.

### P26 — map-first Test Strength information hierarchy

- **Research check:** Stryker/PIT reporting reinforces a three-level split: summary/score for orientation, a compact changed/debt view for action, and detailed HTML/MTE source-mutant inspection only when investigating a concrete survivor. The pilot now follows that hierarchy instead of treating MTE as a routine user page.
- **Depth Map = normal monitor:** selecting Test Strength reveals a compact watch directly above the treemap. It shows the measured contracts ordered by actionability/weakness, score progress, killed/survived, Fresh/Stale, New/Debt/Δ and one retained missed-behavior example. Measured-contract click routes to Mutation Analysis rather than directly to MTE.
- **Mutation Analysis = when something needs attention/history:** current signal is one line; queue is Contract / Strength / Change / Open; recent history is six rows. Shared-scope N/A diagnostics and operator/run-cost diagnostics are collapsed by default.
- **MTE = raw forensic detail:** user-facing links now say `Raw mutants`; wrapper navigation starts with the Test Strength map and Changes/history. It remains the place for exact source mutation + covering/killing test inspection, not the normal monitoring surface.
- **Current watch:** Rate Limit = 51.0%, 51 killed / 49 survived, Debt 49, example `now-is-None branch disabled`; Invalid Config = 59.8%, Debt 41, boundary example; ToolRegistry = 90.3%, Debt 3, example `ToolStep.call_id → None`.
- **Physical acceptance:** Test Strength watch is visible only in Strength mode and renders 3 equal 432×153 cards at the 1512px QA viewport with no overflow; Test Level hides it. Map → Changes/history, Map → Assurance and Map → Raw mutants work. Raw ToolRegistry → exact Allure still reaches `bd3b4e9acafbba5ecf530083b3cf17ae` = Passed + TREQ_TOOL_REGISTRY. Both Depth Map and Mutation Analysis pass physical light/dark with no horizontal overflow; Mutation Analysis's two technical disclosures are closed by default.
- **Migration lesson:** later DocOps extraction must preserve this hierarchy: overview/current signal belongs with Depth; run change/history belongs in Mutation Analysis; source-level MTE stays secondary forensic detail. **P26 user-facing watch/Assurance links are superseded by P27.**

### P27 — separated mutation monitoring from contract evidence

- **User-flow correction:** the P26 Test Strength watch was removed because it duplicated the treemap. Depth is again one monitor: summary bands stay on the dimension control; measured-contract hover shows score, killed/survived, Fresh/New/Debt/Δ and one missed-behavior example; click goes to Mutation Analysis.
- **Mutation flow:** `Verification Depth → Mutation Analysis → Raw mutants / Allure`. Mutation Analysis no longer links to Contract Evidence; all three MTE wrappers no longer link to it either. Contract IDs in the journal link back to the Traceability Reader for requirement meaning, not to an assurance dump.
- **Contract audit flow:** old `Verification assurance map` is presented as `Contract Evidence` and is entered from a specific Requirement/TREQ in Traceability Reader. It answers one question: `what proves this contract now?`
- **Contract Evidence projection:** only the selected contract is visible. Main view = current proof status + revision/acceptance metadata + implementation + required evidence + one known limit. Mutation/Test Strength injection, verification-scope matrix, runtime-assurance repetition and producer-trust list are not shown in the main contract view.
- **Entry/return navigation:** Traceability Reader adds `Contract evidence →` to all 44 Requirement/TREQ cards and stable `review-REQ/TREQ` anchors; Contract Evidence returns to the exact originating card. Opening Contract Evidence without a hash tells the user to start from Traceability Reader.
- **Specification Health:** mutation measurement coverage now routes to Verification Depth, not a removed Mutation Analysis coverage anchor.
- **Physical acceptance:** TREQ_RATE_LIMIT_STATE round-trip Traceability→Contract Evidence→same TREQ works; selected evidence view is one visible section with Complete + 1 implementation + 3/3 unit checks + known live-reality limit; no mutation text. Depth has no duplicate watch/Contract Evidence links; Mutation Analysis has no Contract Evidence links; ToolRegistry Raw mutants still opens exact Allure hash `bd3b4e9acafbba5ecf530083b3cf17ae` with Passed + TREQ_TOOL_REGISTRY. Contract Evidence/Depth/Mutation Analysis pass light/dark with no horizontal overflow.
- **Migration boundary:** future DocOps mutation extraction owns Depth/Test Strength, Mutation Analysis, measurement coverage and MTE packaging. Contract Evidence belongs to the wider traceability/audit UX and **must not receive mutation score/delta blocks**.

### P28 — role boundaries + assurance case / evidence envelope

- **Role cleanup:** Living Specifications are semantics pages. They keep scenario intent, `Verifies`, contract provenance, proof logic, Given/When/Then bindings, executable usage and binding identifiers. Current `Verified/passed`, runtime timestamp/duration, Verification boundary/envelope mechanics, evidence-producer lists and assurance gaps are removed from the visible semantic narrative. Raw execution and `Why trust this evidence?` remain links.
- **Assurance model:** Contract Evidence is no longer a proof-status page. It follows an assurance-case structure (`claim → argument → evidence`) and answers: how convincing is the retained evidence, from which angles, and what is still missing?
- **No scalar confidence:** do not invent one confidence percentage. Evidence strength is multi-dimensional; maxima from different tests must never be merged into a fictional stronger path.
- **Evidence envelope:** every contract has two coupled matrices built from retained test facts: `System Reach × External Reality` and `System Reach × Representation Fidelity`. A cell is filled only when one actual evidence path has that exact combination.
- **Independent confidence qualifiers:** method corroboration, mutation Test Strength, evidence-producer trust basis and surrogate/model validation stay separate. M&S L0/L2 is shown for material substitute producers; mutation sensitivity links to Mutation Analysis only when objectively measured.
- **Assurance gaps:** explicitly derive missing combined evidence, especially `System/System integration × Direct live`, `System/System integration × Representative/Actual`, absent direct-live evidence, L0 surrogate calibration gaps, single-method claims and missing mutation sensitivity.
- **Subclaims:** derived REQ/TREQ children are displayed as supporting claims with their own evidence; their evidence strengthens the parent argument but is not silently counted as direct parent evidence.
- **System aggregation:** no-hash Contract Evidence is the assurance coverage overview. It aggregates descendant Requirement/TREQ evidence over Goals/Capabilities and shows both evidence matrices. Current retained facts expose the key gap: 43/44 contracts have direct evidence, 24/44 have System/System-integration evidence, but 0/44 have Direct-live external evidence and therefore 0/44 have System × Direct-live evidence.
- **Current cross-dimensional example:** `REQ_REQUEST_OVERRIDE_PRECEDENCE` has two Behavior paths at `System integration × Substitute` and one Property path at `Component × Actual`; the matrix correctly shows no `System integration × Actual/Representative` and no `System × Direct live`. Separate maxima are never presented as if one evidence path achieved both.
- **Navigation:** semantic scenario → `Why trust this evidence?` → contract assurance case; Traceability Reader → Contract Evidence; Contract Evidence → semantic contract / raw execution / producer trust / child subclaims. Health/Depth/Mutation keep their P27 roles and do not receive Contract Evidence links.
- **Research lineage:** NASA-style requirement verification matrices motivate explicit requirement-to-evidence coverage; NIST/GSN/CAE assurance-case practice motivates claim/argument/evidence structure; SEI confidence work motivates surfacing reasons for doubt rather than hiding them behind one score.
- **Future owner:** the generic semantics/assurance projection belongs to broader `ternforge-tooling-docops` traceability/assurance after pilot acceptance. This is not part of mutation extraction and must remain local during the active llm-router pilot.

### P29 — Fault-model Coverage + native fault families + Assurance History

- **Five different fault obligations, five honest mechanisms:** Specification/model faults use Agentic Test Forge Gherkin mutation; Architecture faults use an Import Linter negative-control injection; Interface/protocol faults use deterministic adapter-boundary fault challenges; Runtime/dependency faults use Toxiproxy; Implementation faults use pytest-gremlins native operator metadata alongside the retained mutmut contract campaign. These are separate evidence obligations and are never averaged into one “assurance score”.
- **Why pytest-gremlins was added:** mutmut remains the retained requirement Test Strength engine and MTE report source, but its retained artifacts do not expose a reliable stable fault-family taxonomy. P29 had the concrete requirement to classify fault families with engine metadata and compare detection at different evidence depths. pytest-gremlins satisfies that gap with native `boundary`, `comparison`, `boolean`, `arithmetic`, `return` operator labels plus source location and selected tests.
- **Two independent mutation metrics:** `Mutation Reach = reached/generated` answers whether the linked evidence path executes the mutation sites; `Sensitivity = killed/reached` answers whether the tests detect faults they actually reach. Do not hide unreached mutants inside sensitivity and do not call simple killed/generated “Test Strength” when comparing evidence depths.
- **Same-universe cross-depth comparison:** `REQ_INVALID_CONFIGURATION_ERRORS` uses one stable 31-mutant `validate_config` universe. Component/local unit evidence reaches 27/31 (87.1%) and kills 11/27 (40.7%). System-integration/substitute BDD evidence reaches the same 27/31 (87.1%) and kills 27/27 (100.0%). This demonstrates that architectural test depth can contribute detection strength independently of code reach.
- **Native fault-family matrix:** for that contract, boundary faults are 12/14 reached; Component kills 2/12 = 16.7%, System integration kills 12/12 = 100%. Comparison faults are 15/17 reached; Component kills 9/15 = 60.0%, System integration kills 15/15 = 100%. The UI must label these as engine-native pytest-gremlins families, not Ternforge classifier guesses.
- **Unique vs corroborated detections:** of 31 generated mutants, 21 are detected by at least one tested path; 11 are killed by both paths, none only by Component, and 10 only by System integration. This is more useful than displaying only a stronger-path score because it shows what the deeper evidence uniquely contributes.
- **Interface limitation stays explicit:** the three current provider-boundary challenges (retryable HTTP status, malformed success payload, transport disconnect) are real and pass, but llm-router has no machine-readable provider-interface schema that a generic schema/interface mutator can safely consume. P29 records this layer as challenge-backed, not generator-backed. A future schema source may justify a standard interface mutation engine; until then do not fabricate generic coverage.
- **Assurance History uses a standard renderer:** DVC plots renders a portable Vega-Lite trend from retained campaign CSV instead of a custom Ternforge chart. Eleven real historical mutation snapshots are retained. The current history is explicitly a retained mutation-signal history; wider assurance-envelope/fault-model snapshots are not fabricated for old runs and should appear only after future runs actually retain those dimensions. The DVC `simple` renderer is kept intact apart from a responsive-width adaptation and readable axis labels.
- **Contract Evidence owns the assurance projection:** system view gets the five-layer Fault-model Coverage table and Assurance History; contract view gets the family × evidence-depth matrix only where objective same-universe facts exist. Health, Depth, Mutation Analysis, Living Specs, MTE and Allure keep their existing roles.
- **Physical acceptance:** the responsive DVC plot was checked inside Contract Evidence at 1512 px and 1024 px in both light and dark outer modes. The canvas uses 840/894 px and 872/926 px respectively, with no inner/outer horizontal overflow, failed HTTP responses, page errors or console errors; the standalone DVC report also opens cleanly with no favicon request noise. The exact Living Specification scenario `Invalid model configuration surfaces as a configuration error` physically links to `assurance-req_invalid_configuration_errors`, and the exact Traceability Reader card lands on the same single active contract section. Depth and Mutation Analysis both retain zero Contract Evidence links. The Invalid Configuration contract physically showed the then-prototype overlap as 31-mutant universe, 21 detected union, 11 corroborated and 10 System-integration-only. **P31 later proved that this overlap join was under-counting native mutants sharing line/operator/description; the authoritative native-ID overlap is now 27 union / 11 corroborated / 0 Component-only / 16 System-only / 4 undetected.** P29 structural gate was PASS for the P29 implementation, but its overlap figure is superseded by P31.
- **Pilot boundary:** all P29 implementation remains local in llm-router. Future generic owners are migration notes only until the user explicitly ends the pilot.

### P30 — Full Contract Evidence: Assurance Target → Actual Evidence → Target-derived gaps

P30 closes the design gap that remained after P29. P29 proved that the fault-model signals and DVC history could be collected, but it still rendered the old assurance-envelope semantics and inferred generic gaps. P30 makes the Requirement-level Contract Evidence model match the agreed design end to end.

- **Versioned Assurance Target source:** `.ai-bridge/assurance-targets.json` is the local pilot source of truth. It is deliberately outside generated HTML and carries profile id/revision/status/source/rationale, Requirement assignment, target revision/history and explicit obligations. The generated `assurance-targets.json` is read-only projection. This is a pilot registry beside the Sphinx-Needs graph, not a second requirements graph; a future native implementation must attach equivalent policy metadata to/version it with the engineering graph.
- **Fully profiled Requirement:** `REQ_INVALID_CONFIGURATION_ERRORS` uses `public-preprovider-validation@1`, revision 1. The authored Statement says invalid configuration must fail deterministically **before provider execution**, and the authored Verification intent calls for both a public behavioral scenario and direct lower-level validation rules. Therefore the target requires Component×Local and System×Local evidence with Actual implementation representation; it intentionally does **not** require Direct-live provider evidence.
- **Target obligations:** 12 blocking obligations: 2 frontier cells, ≥2 verification methods, separate Component/System Mutation Reach and Mutation Sensitivity floors, and all five fault layers. Current result is **11/12 met**. The only current blocking gap is **Component mutation Sensitivity 40.7% < 80%**. Component Reach 87.1%, System Reach 87.1%, System Sensitivity 100%, both frontier cells, method corroboration and all five fault layers are satisfied. Completion is an obligation count, never “91.7% confidence”.
- **One Guarantee Frontier:** the primary topology is `System Reach × Boundary Reality`. Representation Fidelity is shown only as a qualifier on the exact evidence path/cell. The old second `Reach × Representation` matrix is removed, preventing fictional combinations of maxima from different tests.
- **Canonical path classification:** the public BDD evidence for this Requirement is `System × Local × Actual`; the direct validation suite is `Component × Local × Actual`. P30 corrects P29’s provisional `System integration × Substitute` label for the mutation comparison and aligns the mutation groups with authoritative Verification Depth facts.
- **Requirement-specific specification challenge:** Agentic Test Forge remains genuinely validated on a Scenario Outline (6/6 Examples mutants), but it only mutates Examples table cells. This Requirement is a simple Scenario, so P30 does not fake ATF coverage. It creates one plausible wrong-outcome mutant (`ConfigurationError → ProviderError`), validates both original and mutant with the official Cucumber Gherkin parser, and executes the exact pytest-bdd scenario; **1/1 is killed**.
- **Requirement-specific architecture challenge:** inject `config.validation → providers.registry` in a temporary copy. Real Import Linter baseline is 9/9 contracts kept; the intentional lower-to-upper dependency breaks `Private implementation must stay layered`; **1/1 is detected**.
- **Requirement-specific interface challenge:** install a local ScriptedHTTPServer sentinel as the provider endpoint, run the public invalid-model path, and require `ConfigurationError` with **0 provider HTTP requests**. For a pre-provider claim this is the relevant interface fault (unexpected provider interaction), more meaningful than mutating an unrelated external API schema.
- **Requirement-specific runtime/dependency challenge:** put **Toxiproxy 2.12.0** with 1500 ms provider latency in front of the sentinel. The same public request still returns `ConfigurationError` immediately with **0 provider requests**; **1/1 challenge detected**. This proves dependency degradation is irrelevant to the pre-provider guarantee.
- **Implementation fault detail:** one stable 31-mutant `validate_config` universe. Component×Local: 27 reached / 11 killed = **87.1% Reach / 40.7% Sensitivity**. System×Local: 27 reached / 27 killed = **87.1% / 100%**. Native engine families remain: boundary 16.7% vs 100%; comparison 60.0% vs 100%.
- **Contribution, not just score — historical P30 display:** P30 rendered 31-mutant universe; 21 detected by either path; 11 corroborated by both; 0 Component-only; 10 System-only. **P31 corrected this join to native `gremlin_id`: 27 detected union / 11 corroborated / 0 Component-only / 16 System-only / 4 undetected.** The conclusion remains: the public path adds detection/oracle strength rather than additional code reach, but only the P31 native-ID counts are authoritative.
- **Evidence trust:** method corroboration, producer qualification, M&S/surrogate applicability and freshness remain separate; no scalar confidence score is produced. This selected contract uses Actual implementation paths and no material surrogate, so M&S validation is N/A rather than an invented level.
- **Target-derived gaps only:** empty theoretical cells remain neutral unless the profile requires them. Direct-live is explicitly called out as **not a gap** for this Requirement.
- **Evidence Paths:** each retained path card keeps Method, System Reach, Boundary Reality, Representation, M&S status, producer-trust summary and mutation signal from the same path, with navigation to retained narrative/raw evidence.
- **Assurance History:** P30 starts explicit target revision history at v1 and renders a Requirement-specific DVC/Vega-Lite Test Strength trend from real retained campaigns. Older campaigns are not back-filled with Assurance Target/fault-layer dimensions that were never retained.
- **System overview:** one aggregate Reach×Boundary topology; target coverage is separate from evidence coverage. P30 deliberately profiles three contrasting contracts: pre-provider validation (`REQ_INVALID_CONFIGURATION_ERRORS`), an internal-state invariant (`TREQ_RATE_LIMIT_STATE`), and mutable external-provider compatibility (`REQ_ASYNC_PROVIDER_EXECUTION`). The remaining 41/44 contracts show actual evidence plus “target not declared”; they do not inherit generic red gaps.
- **Final P30 physical browser acceptance:** Chrome/Playwright was exercised at 1512×1200 and 1024×1000 in both light and dark modes. The selected Requirement renders exactly 2 satisfied target frontier cells, 0 missing/partial target cells, exactly 1 blocking gap (Component Sensitivity 40.7% < 80%), 5/5 required fault-layer rows, 5 retained Evidence Path cards, native boundary/comparison family values, the then-P30 overlap display of 21 detected union / 11 corroborated / 10 System-only detections (superseded by P31 native-ID counts 27 / 11 / 16 with 4 undetected), and one responsive Requirement-specific DVC canvas with zero inner/outer horizontal overflow. Deep reload preserves the exact hash-selected contract. The no-hash overview renders exactly one Reach×Boundary frontier and target coverage 3/44. `TREQ_RATE_LIMIT_STATE` now proves the internal-state counterexample: Component×Local×Actual is satisfied, Direct-live is not targeted, and its only blocking gap is the honestly available covered-mutant Test Strength 51.0% < 80%. `REQ_ASYNC_PROVIDER_EXECUTION` proves the opposite provider-facing case: System-integration×Replay×Surrogate is satisfied continuously, while System-integration×Direct-live×Actual is a justified pre-release gap because current retained evidence contains zero Direct-live paths. Physical click paths were exercised from the exact Living Specification scenario and the exact Traceability Reader card into the Requirement, plus outward drill-downs to raw target JSON, scoped Allure execution, producer trust, Mutation Analysis, Requirement DVC history and narrative/raw evidence; all returned HTTP 200 with no page errors or failed requests. Depth, Health and Mutation Analysis retain zero Contract Evidence links. The final residual console 404 was isolated to Chrome automatically requesting `/favicon.ico` when opening raw JSON directly; P30 now emits a valid root favicon, and the complete repeated navigation/regression run is clean: zero console errors, zero HTTP >=400 responses, zero failed requests, zero page errors. P30 structural gate is PASS.
- **Final Depth/target counterexample regression:** the same 1512/1024 × light/dark browser matrix was repeated after replacing the peer Representation projection with **Boundary Reality**. All three switches (`Test Level`, `Boundary Reality`, `Test Strength`) operate without overflow or JS/HTTP errors; Boundary Reality shows the retained contract distribution `18 Local only · 17 Substitute · 9 Replay · 0 Direct live`, while Representation remains visible only in same-path hover qualifiers. The exact OpenAI adapter hover reports `Substitute · Surrogate / Simulated · L0` on one path; selecting the Scripted HTTP producer keeps Boundary mode active and highlights 16 affected contracts; clicking that contract opens Traceability Reader. The exact measured `TREQ_RATE_LIMIT_STATE` Test Strength hover reports `51.0% · 51 killed · 49 survived`, and its physical click opens Mutation Analysis. Its DVC trend renders from 6 retained snapshots with zero iframe overflow. The three Target contracts and an unprofiled control were deep-reloaded in every browser mode/width: `REQ_INVALID_CONFIGURATION_ERRORS` = 11/12 with only Component Sensitivity open; `TREQ_RATE_LIMIT_STATE` = 2/3 with only covered-mutant Test Strength open and no Direct-live target; `REQ_ASYNC_PROVIDER_EXECUTION` = 2/3 with only the pre-release Direct-live compatibility obligation open; the unprofiled OpenAI adapter has zero fabricated gaps. Raw JSON pages and all tested drill-downs remain HTTP 200 with zero console/page/request failures.

### P31 — Contract Evidence 1:1 completion against the agreed Requirement-level schema

P31 exists because the P30 page was a correct target-relative shell but still did **not** match the promised Contract Evidence design 1:1. In particular, four fault layers were still summarized rather than explained, Evidence Paths lacked several same-path qualifiers/drill-downs, assurance history was mutation-centric, the assurance argument/incident lifecycle was implicit, and the implementation overlap calculation collapsed distinct native mutants that shared line/operator/description.

- **Full five-layer detail, not a status bar:** `REQ_INVALID_CONFIGURATION_ERRORS` now has explicit 3.1–3.5 drill-downs. Specification retains the exact `ConfigurationError → ProviderError` Gherkin negative control, parser validity, execution command, pytest-bdd detector/output and repo links. Architecture retains the 9/9 clean Import Linter baseline, exact `config.validation → providers.registry` injected violation, broken contract and detector output. Interface retains expected/observed provider interaction (`0` requests), public result and sentinel detector. Runtime retains the exact Toxiproxy `latency/downstream/1500 ms` toxic, expected invariant, observed `ConfigurationError`, `0` provider requests and elapsed time. Implementation retains its own mutation/coverage denominators.
- **Honest Implementation Reach:** coverage.py executable statements in the declared `validate_config` scope are the explicit denominator: **22/24 = 91.7% statement reach**, with missing statement lines `[22, 40]`. This is labelled `Implementation statement reach`; it is not confused with Mutation Reach.
- **Correct native mutant identity:** pytest-gremlins' stable `gremlin_id` is now the join key. The full universe contains **31 distinct native mutants**. Component×Local = 31 generated / 27 reached / 11 killed / 16 reached-survived / 4 unreached = **87.1% Mutation Reach / 40.7% Sensitivity / 35.5% Overall Detection**. System×Local = 31 / 27 / 27 / 0 / 4 = **87.1% / 100% / 87.1%**.
- **P29/P30 overlap correction:** the old prototype joined mutants by `(line, operator, description)`, which collapsed repeated boundary/comparison mutants on the same line. That produced the incorrect `21 union / 11 corroborated / 10 System-only` display. P31 corrects it using native IDs: **27 detected union / 11 corroborated / 0 Component-only / 16 System-only / 4 undetected**. The earlier numbers are superseded and must not be used for extraction.
- **Separate engine denominators remain explicit:** the retained mutmut campaign is still `61 killed / 41 survived / 102 valid = 59.8% covered-mutant Test Strength`; it records New 0 / Debt 41 / Resolved 0 and explicitly warns that `mutate_only_covered_lines=true` makes this unsuitable as a full-scope Mutation Reach denominator.
- **Native fault-family × evidence depth:** engine-native boundary/comparison metadata remains authoritative; each cell now carries generated/reached/killed/survived/unreached plus Reach, Sensitivity and secondary Overall Detection. The exact 31-mutant table shows native ID, source line/change, per-depth reached/killed state, covering tests and engine-reported killing test (including an honest `unknown` when that is what the engine reports).
- **Evidence Qualifiers completed:** Representation remains a same-path qualifier; explicit Scenario/Data Representativeness, M&S credibility, Method Corroboration and Freshness panels are now present. No scenario/data classification or per-path timestamp is fabricated: current retained paths show `Not classified` / `not timestamped` with the reason, while mutation-campaign freshness is reported separately when available.
- **Evidence Path cards completed:** every retained path carries Method, System Reach, Boundary Reality, Representation, Scenario/Data, Environment, concrete producer identities, M&S credibility, Mutation Reach/Sensitivity/Overall Detection where the same path has an objective decomposition, and freshness provenance. Independent drill-downs are emitted for Narrative evidence, contract-scoped Allure, revision-pinned source, raw evidence and mutants where available.
- **Actionable gaps:** the one primary blocking gap, Component mutation Sensitivity 40.7% < 80%, links directly to depth/family diagnostics, exact mutants, Mutation Analysis and MTE survivors, with a grounded next question. The provider-facing Direct-live gap links to its exact frontier/evidence/target sources without pretending a live result exists. Optional improvements remain separate from Target gaps.
- **Explicit assurance argument:** Contract Evidence now renders `claim → obligations → evidence`, with satisfied/gap state and support links per obligation. Supporting REQ/TREQ subclaims are rendered separately and never counted as parent direct evidence.
- **Assurance History completed prospectively:** `.ai-bridge/assurance-snapshots.json` starts at `p31-local-1`; the generated projection is `docs/_build/html/assurance-snapshots.json`. Each explicit Target now retains target/profile revision, obligations met/total, blocking gaps, Reach/Sensitivity, Test Strength where available, survivor change, fault-layer status and assurance events. Initial snapshots are `REQ_INVALID_CONFIGURATION_ERRORS 11/12`, `TREQ_RATE_LIMIT_STATE 2/3`, and `REQ_ASYNC_PROVIDER_EXECUTION 2/3`. Pre-P31 Target/fault-model values are **not back-filled**. Older real mutation history remains separately rendered with DVC/Vega-Lite.
- **Incident / Target Revision Loop made visible:** escaped bug → classify existing target vs weak evidence → strengthen evidence or revise target → gap opens/remains → fix/new evidence → target met or residual risk explicitly accepted → close issue. Current target revision, rationale, issue links and overrides are shown without inventing an incident.
- **Coherent top navigation:** Semantics, Traceability, Health, Depth, Mutation Analysis, scoped Allure/raw execution, raw target/profile, Evidence Producer Credibility and Assurance History are available directly from the Requirement view.
- **Role boundaries preserved:** one Guarantee Frontier remains `System Reach × Boundary Reality`; Representation is not reintroduced as a peer matrix; Verification Depth remains `Test Level / Boundary Reality / Test Strength`; no generic Direct-live gap returns; Living Specifications remain semantic, Health current-state, Mutation Analysis change/debt, and raw evidence forensic.
- **Three target counterexamples remain deliberate:** pre-provider validation has no Direct-live obligation; internal `TREQ_RATE_LIMIT_STATE` has no Direct-live obligation and exposes only its honest covered-mutant Test Strength gap; external `REQ_ASYNC_PROVIDER_EXECUTION` has a justified pre-release Direct-live obligation that is currently missing.

**Final P31 physical/browser acceptance is closed.** Chrome/Playwright exercised the selected `REQ_INVALID_CONFIGURATION_ERRORS` contract at **1512×1200 and 1024×1000 in both light and dark mode**; the page actually resolves `data-theme=light` on white (`rgb(255,255,255)`) and `data-theme=dark` on dark (`rgb(20,24,30)`) rather than merely spoofing labels. The primary matrix ran **72 structural/browser checks with 0 failures**: exact single active contract, 11/12 Target Satisfaction, exactly one Component Sensitivity gap, five detailed fault layers, 31 exact native-mutant rows, five Evidence Path cards, 22/24 = 91.7% Implementation statement reach, corrected 27/11/0/16/4 overlap after opening Implementation detail, Scenario/Data not-classified disclosure, assurance argument, P31 snapshot/event history, incident revision loop, coherent navigation, responsive DVC frame and zero horizontal overflow even with all five fault details expanded. No page errors, console errors or HTTP >=400 responses were observed in any matrix cell.

The three target counterexamples were physically re-opened: `REQ_INVALID_CONFIGURATION_ERRORS = 11/12` with only Component Sensitivity open and no Direct-live obligation; `TREQ_RATE_LIMIT_STATE = 2/3` with only covered-mutant Test Strength 51.0% open and no Direct-live blocking gap; `REQ_ASYNC_PROVIDER_EXECUTION = 2/3` with the justified pre-release Direct-live compatibility gap; unprofiled `TREQ_TOOL_REGISTRY` remains `TARGET NOT DECLARED` with zero fabricated blocking gaps. The no-hash overview physically renders target coverage **3/44**, exactly one aggregate Reach×Boundary frontier, and 5/5 pilot fault mechanisms with explicit wording that this is mechanism capability rather than Requirement coverage.

Navigation/drill-down acceptance is also physical. The exact Living Specification scenario `Invalid model configuration surfaces as a configuration error` clicks `Why trust this evidence? →` and lands on the exact active `assurance-req_invalid_configuration_errors` section; the exact Traceability Reader card does the same via `Contract evidence →`. Primary Contract Evidence links to Semantics, Traceability, Health, Depth, Mutation Analysis, scoped Allure execution, raw Target/profile, Evidence Producer Credibility, Narrative evidence, Raw evidence, MTE mutants and survivors all returned HTTP 200 with clean browser diagnostics. The three same-page drill-downs — Assurance History, depth/family diagnostics, exact mutants — were re-tested independently after the combined sequence exposed a hash-rerender test artifact; each physical click lands on its exact anchor.

Verification Depth was re-run at **1512/1024 × light/dark** with **48/48 checks passing**: exactly three controls (`reach`, `boundary`, `strength`), each physically becomes active when clicked, Boundary Reality retains `Local only → Substitute → Replay → Direct live`, Representation Fidelity stays a same-path qualifier, Test Strength remains 3/44 measured, and there is zero overflow or browser error. Standalone DVC system, Invalid Configuration and Rate-limit reports each return HTTP 200, render exactly one Vega canvas, have zero horizontal overflow and no page/console/HTTP errors. The updated `.ai-bridge/validate-mutation-pilot.py` structural gate passes with the P31 schemas, native-ID overlap, snapshot/event history and extraction guardrails. **P31 is complete for the local llm-router pilot surface; the overall llm-router pilot remains active and E1–E7 extraction stays blocked until explicit user approval.**

### P32 — retained intermediate UI snapshot only

P32 is present in `assurance-snapshots.json` because the assurance surface was rebuilt once between P31 and the final progressive-disclosure pass. It has **no independent assurance semantics**. After excluding `checkpoint`, `captured_at` and the derived `fingerprint`, all three profiled P32 snapshots are field-for-field equal to their P33 counterparts. No Target, Actual evidence, gap, fault-model result, mutation denominator or policy changed. Because no separate durable P32 design record survived, the pilot explicitly does **not** reconstruct one after the fact; P32 is retained as history and superseded by P33 presentation.

### P33 — progressive-disclosure Contract Evidence

P33 keeps the P30/P31 data model and changes the reading experience so the user can scan the assurance case before opening forensic detail.

- **Numbered reading order:** `Overview → 1 Evidence Frontier → 2 Fault Detection → 3 Evidence Trust → 4 Assurance Gap → 5 Evidence Paths → 6 History → 7 Investigate`, backed by a sticky in-page TOC that preserves the selected contract while navigating internal anchors.
- **At-a-glance contract state:** `Possible / Must / Actual / Gap` explicitly separates theoretical topology from Target obligations, retained evidence and the real `Must − Actual` gap. Target/profile rationale and the full obligation table remain available behind disclosure rather than competing with the primary scan.
- **One Frontier only:** the main 4×4 view remains `System Reach × Boundary Reality`. Same-path mutation Reach/Sensitivity may annotate a cell. Representation, model/surrogate credibility, method corroboration and freshness remain qualifiers; the rejected second `Reach × Representation` matrix does not return.
- **Fault Detection as a ladder, not a wall:** Requirement/model, Architecture/interface, Runtime/dependency and Implementation are shown as four visual blocks. The expensive implementation detail — four-depth mutation comparison, native fault families, unique/corroborated detection, retained mutmut Test Strength and all 31 exact mutants — is preserved behind disclosures.
- **Trust and gaps are orthogonal:** Evidence Trust is a compact scan strip for methods, producer chain, surrogate/model basis, freshness and weakest sensitivity; no scalar confidence is introduced. Assurance Gap is one visual Target-vs-Actual diagnostic with optional improvements kept distinct from blocking Target gaps.
- **Paths/history/investigation use progressive disclosure:** repeated paths are grouped for scanning; exact Narrative/Allure/Raw/Mutants links are shown only when requested. History defaults to compact trends, with exact snapshots and DVC drill-down behind details. The escaped-defect → strengthen evidence or revise Target loop remains available under `Investigate` rather than occupying the default page.

**P33 acceptance is closed for this local checkpoint.** The structural gate reaches `ACTIVE LLM-ROUTER MUTATION PILOT STRUCTURAL GATE: PASS` after removing temporary review screenshots and `.ai-bridge/__pycache__`. Physical browser QA re-opened `REQ_INVALID_CONFIGURATION_ERRORS` at 1512×1200 and 1024×1000 in actual Light/Dark mode: Light is `rgb(255, 255, 255)`, Dark is `rgb(20, 24, 30)`, default deep disclosures remain closed and there is no horizontal overflow. A worst-case 1024-dark expansion with all 12 P33 disclosures open still remains exactly 1024px wide. The exact Traceability Reader card reaches the exact P33 contract. The exact Living Specification scenario reaches the same contract via `Why trust this evidence? →`, while its visible semantic narrative contains no `Verified`, `Verification boundary` or `Evidence producers` blocks. No platform repository or other consumer was touched.

P33 is therefore the **current local user-review surface**, not the end of the llm-router pilot. Next work is live user review and only surgical UX corrections that make the accepted model easier to read. E1–E7 extraction stays blocked until the user explicitly ends the pilot.

## Explicit non-goals for the fast local phase

- no rollout to other consumers;
- no additional mutation engine beyond mutmut + pytest-gremlins unless another concrete evidence gap is demonstrated; pytest-gremlins is the explicit P29 exception because mutmut does not provide reliable engine-native fault-family metadata for the required cross-depth analysis;
- no distributed mutation workers;
- no custom replacement for Mutation Testing Elements;
- no thousands of mutant Needs;
- no global mutation-score quality gate;
- no automatic operator suppression from insufficient history;
- no conflation of Test Strength with Verification Health, Representation Fidelity or Evidence Producer Credibility.

## Definition of success for user review

When this roadmap is locally complete, one browser session should let a reviewer answer seven questions without reading implementation scripts:

1. **What currently passes or fails?** → Verification Health Map.
2. **How deeply/realistically/strongly is this contract tested?** → Verification Depth Map.
3. **Did this change introduce a new testing weakness, or is it known strength debt?** → Mutation Analysis current signal + work queue.
4. **What changed across mutation baselines and was a weakness later resolved?** → Mutation Analysis recent changes.
5. **What exact mutation survived, which source line changed, and which linked tests covered/killed it?** → Raw mutants → exact Allure/source.
6. **What must be demonstrated for this Requirement/TREQ, what is actually demonstrated now, and which Target obligations are still unsatisfied?** → Traceability Reader → Contract Evidence → Assurance Target / Guarantee Frontier / Target Satisfaction / Gaps.
7. **Which fault-model layers and native fault families have actually been challenged, what does deeper evidence uniquely detect, why should the evidence be trusted, and how has the retained signal changed over time?** → Contract Evidence → Fault-model Coverage / Evidence Paths / Evidence Producer Credibility / Assurance History.

Living Specifications answer semantics/proof intent; Health/Depth answer monitoring; Mutation Analysis answers mutation change history; Contract Evidence answers assurance sufficiency against an explicit Target; raw Allure/MTE/evidence records answer forensic execution detail. Platform extraction starts only after the user explicitly accepts this workflow and ends the pilot.
