# Verification Depth — methodology audit (DEPTH-P03)

## Decision

The map must not infer depth from verification_kind, Gherkin presence, source-directory names,
a configured fake, a vcr marker, or a successful network connection alone.

The two displayed axes are independent:

1. System Reach — observed architectural/test-object reach.
2. Environment — fidelity of the execution environment to the declared operational environment.

External-dependency mode (none / substitute / replay / direct) is a raw fact, not an Environment level.

## System Reach

Use ISTQB-aligned test-object boundaries:

Component → Component integration → System → System integration

Do not add Acceptance to this reach axis; Acceptance is validation/readiness, not deeper runtime reach.

Required raw evidence:

- JUnit + Sphinx-Needs: test identity and exact verifies relationship.
- Coverage.py dynamic test contexts: production code executed by that test and phase.
- A versioned architecture-boundary manifest: what belongs to a component, the system boundary,
  public entry points, and external interfaces.
- Actual interaction evidence:
  - HTTP substitute: received request in request journal.
  - VCR: cassette play_count > 0.
  - fake SDK: invocation observed at the fake method, not constructor.
  - direct HTTP/RPC: send-time client telemetry/span (OpenTelemetry is the preferred standard).
- For internal component/system transitions, co-coverage is supporting evidence but is not by itself
  a universal proof of interaction. Permanent tooling should retain an actual edge/checkpoint or span.

Coverage is evidence of execution, not a test-level classifier.

## Environment

Current run is Controlled for every contract.

Representative requires:

- a versioned operational/relevant-environment profile,
- declared critical dimensions that must match production/operations,
- machine-checked conformance/drift result attached to the run.

A label such as staging, a real container, VCR cassette, fake SDK, or direct live API call does not
by itself prove Representative.

Operational requires execution identity from the actual operational platform/environment.
A CI/local test calling a production API is still not an Operational execution.

OpenTelemetry deployment.environment.name is useful standardized identity metadata, but it is only
an environment tier label; it does not prove representativeness by itself.

## Local independent probe

Fresh main run, commit 1618432:

- 117/117 tests passed.
- 117 JUnit cases = 117 py-testkit runtime records = 117 Coverage.py test contexts = 117 Needs testcase nodes.
- 0 nodeid mismatches.
- 0 verifies mismatches.
- 0 BDD feature/scenario reference errors.
- 30 tests actually sent matched requests to ScriptedHTTPServer.
- 33 tests actually replayed VCR responses (play_count > 0).
- 8 tests actually called fake SDK methods.
- 71 tests total crossed an observed external interface.
- Prepared-substitute observations had 0 false positives in this run, but 1 false negative because
  setup-time evidence was lost across pytest phase boundaries.

The false negative was:
tests/llm_router/bdd/routing/test_rate_limits.py::test_a_blocked_route_is_skipped_when_another_route_is_available

It is now classified as System integration reach.

Current execution distribution:

- 50 System integration
- 3 System
- 26 Component integration
- 38 Component

Current contract distribution:

- 21 System integration
- 3 System
- 6 Component integration
- 14 Component

Environment: 44/44 Controlled.

Environment-source cross-check:

- 117/117 runtime records include the network-blocking fixture.
- 117/117 include record-mode and VCR fixture context.
- No deployment/environment profile or environment-conformance attestation exists.
- Therefore Controlled is evidence-backed; Representative and Operational are intentionally unreachable.

## Tooling risks to close before migration

1. ScriptedHTTPServer currently emits substitute evidence in **enter**; emit interaction evidence
   from actual request receipt instead.
2. Fake SDKs currently publish substitute evidence from constructors; publish at actual invoked method.
3. VCR replay must be retained from cassette state (play_count/requests), not inferred from marker.
4. pytest-cov 7 removed subprocess measurement support. If subprocess SUT paths return, configure
   Coverage.py patch = ["subprocess"] and combine subprocess data.
5. Replace repo-specific path-name heuristics with a versioned architecture-boundary manifest and
   observed boundary edges.
6. Add environment profile + conformance/attestation before allowing Representative or Operational.

## External references

- ISTQB CTFL v4.0.1:
  <https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf>
- Coverage.py measurement contexts:
  <https://coverage.readthedocs.io/en/7.12.0/contexts.html>
- Coverage.py subprocess measurement:
  <https://coverage.readthedocs.io/en/7.14.1/subprocess.html>
- pytest-cov contexts:
  <https://pytest-cov.readthedocs.io/en/latest/contexts.html>
- pytest-cov subprocess support:
  <https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html>
- VCR.py cassette API:
  <https://vcrpy.readthedocs.io/en/latest/advanced.html>
- OpenTelemetry HTTP spans:
  <https://opentelemetry.io/docs/specs/semconv/http/http-spans/>
- OpenTelemetry deployment environment:
  <https://opentelemetry.io/docs/specs/semconv/registry/entities/deployment/>
- OpenTelemetry HTTPX instrumentation:
  <https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/httpx/httpx.html>
- NASA relevant/operational environment:
  <https://www.nasa.gov/reference/6-1-technical-planning/>
- Azure production-like environment / configuration drift:
  <https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/testing>
- WireMock request journal:
  <https://wiremock.org/docs/configuration/#request-journal>
- Testcontainers:
  <https://testcontainers.com/getting-started/>
- Pact:
  <https://docs.pact.io/>

## DEPTH-P04 — final three-axis candidate

### Axis 1 — Test Level (standard terminology)

Source: ISTQB CTFL.

Component → Component integration → System → System integration

Automation status: reliable after infrastructure hardening.

Machine facts required:

- exact test → requirement traceability;
- versioned architecture-boundary manifest;
- per-test executed production code;
- actual observed boundary edges/interactions.

Do not infer from unit/integration/bdd labels or file paths alone.

### Axis 2 — Representation Fidelity (project-defined universal ordinal scale)

No sufficiently universal standard ladder was found, so this axis is explicitly Ternforge-defined.
The terms themselves are ordinary engineering terms and the design is informed by NASA test-article
pedigree / simulated, prototype, qualification, flight article concepts.

Proposed scale:

Synthetic / Abstract → Surrogate / Simulated → Representative → Actual

Semantics:

- Synthetic / Abstract: constructed analytical/synthetic representation; no executable/physical stand-in with target pedigree.
- Surrogate / Simulated: executable/physical substitute intentionally stands in for the target.
- Representative: non-actual article/data/system with explicit pedigree and evidence that the relevant characteristics are representative for the intended use.
- Actual: the actual target article/system/dependency/data participates.

For an evidence chain with multiple required articles, the chain level is the weakest required article.
For a requirement with multiple evidence chains, the map may display the strongest complete chain,
but hover must preserve every chain.

Automation status: possible, but not trustworthy from inference alone.

Required structured facts:

- target/reality identity for every material verification article;
- article role and actual/surrogate/synthetic relation;
- for Representative, an explicit pedigree/attestation covering the relevant characteristics;
- for Actual, runtime identity proving the target itself participated.

Current llm-router facts can prove fake SDK / ScriptedHTTPServer as Surrogate and a future direct provider
call as Actual. VCR replay must not be auto-promoted to Representative merely because it came from a real
capture; current cassettes lack enough structured pedigree/freshness/intended-use attestation.

### Axis 3 — M&S Validation factor (NASA-STD-7009A)

L0 → L1 → L2 → L3 → L4, plus N/A when an evidence chain does not rely on M&S/surrogates.

NASA semantics are discrete and all conditions of a level must be met:

- L0: insufficient evidence.
- L1: conceptual validation / intended use and conceptual model adequately established.
- L2: favorable comparison to a sufficiently similar/representative referent (or suitable higher-fidelity M&S), within the RWS domain, for at least some important outputs.
- L3: favorable comparison to RWS in representative environment (or qualifying higher-fidelity M&S), validation points significantly span the operating domain, all important outputs compare favorably.
- L4: favorable comparison to RWS in operating environment (or qualifying higher-fidelity M&S), validation points completely span the operating domain, all outputs compare favorably.

Automation status: not reliable with current metadata.

Current producer.qualified_by nodes prove implementation/upstream contracts, not NASA empirical validation
against a referent. To automate the NASA level, qualification evidence must explicitly encode:

- intended use / RWS;
- referent identity and pedigree;
- validation points / covered domain;
- response quantities compared;
- comparison acceptance criterion and result;
- uncertainty where required;
- resulting factor level derived by deterministic gates.

Until those fields exist, the map must not manufacture L1-L4 from generic producer qualifications.

### Aggregation rule

Per evidence chain:

- Test Level = observed chain reach.
- Representation Fidelity = weakest required verification article on the chain.
- M&S Validation = weakest relevant M&S/surrogate validation factor on the chain; N/A if none.

Per requirement:

- each axis may show the strongest complete evidence chain for that axis;
- never combine maxima from different chains into a fictional single compound claim;
- hover/details must retain all contributing chains.

For Goal/Capability roll-up:

- show the weakest descendant requirement on the selected axis.

## DEPTH-P05 — implemented local projection

Three selectable map axes are now implemented locally:

- Test Level: Component → Component integration → System → System integration.
- Representation Fidelity: Synthetic/Abstract → Surrogate/Simulated → Representative → Actual.
- M&S Validation: N/A or L0 → L1 → L2 → L3 → L4.

Current strict model-validation gates:

- ScriptedHTTPServer: L0. Mechanics are qualified, but no structured conceptual/referent validation exists for each scripted provider behavior.
- VCR replay: L0. Replay tooling and historical capture exist, but there is no structured per-cassette intended-use/conceptual-validation record.
- Google GenAI fake SDK: L2 through linked passing live calibration EXP_0002.
- Gemini WebAPI fake SDK: L2 through linked passing live calibration EXP_0003.
- No producer is assigned L3 or L4.

Current contract distribution:

- Test Level: 21 System integration / 3 System / 6 Component integration / 14 Component.
- Representation Fidelity: 20 Actual / 24 Surrogate-Simulated.
- M&S Validation: 2 L2 / 24 L0 / 18 N/A.

Important: L2 does not auto-promote Representation Fidelity to Representative. The axes remain independent;
Representative still needs explicit intended-use pedigree/attestation.

## DEPTH-P14 — producer credibility integration

M&S Validation remains a producer/model property, not a third requirement-treemap axis.

Traceability integration:

- Representation Fidelity hover lists contributing evidence producers and their achieved validation level.
- Persistent amber outline is shown only when the contract's strongest Representation evidence is non-Actual
  and at least one contributing producer remains L0.
- Producer selection highlights all direct verified contracts plus conservative Req/TREQ roll-up parents.
- Producer impact counts use the same roll-up closure as the treemap highlight.

Current roll-up-aware impact:

- Scripted HTTP: L0, 30 tests, 16 contracts.
- VCR replay: L0, 33 tests, 9 contracts.
- Gemini WebAPI fake SDK: L2, 5 tests, 2 contracts.
- Google GenAI fake SDK: L2, 3 tests, 2 contracts.
- L0 union: 63 tests, 24 affected contracts.
- Persistent amber warning: 22 contracts because two L0-using contracts also have stronger Actual representation evidence.

Interaction semantics:

- click producer -> Representation Fidelity + highlighted affected contracts;
- click same producer -> clear selection;
- switch to Test Level -> clear producer selection and restore baseline outlines.

## P28 — assurance case and evidence-envelope methodology

The llm-router pilot now separates **verification state/depth** from **assurance confidence**.

Reference lineage used for the local design:

- NASA systems-engineering verification/validation practice: requirement verification matrices keep each requirement tied to explicit verification evidence/methods rather than relying on a global pass flag.
- NIST assurance-case terminology: assurance is an auditable argument supported by a body of evidence for explicit claims.
- GSN / CAE practice: structure the reasoning as claim → argument/context → evidence, and decompose parent claims into supporting subclaims.
- SEI assurance-confidence work: make reasons for doubt/defeaters visible and collect evidence that addresses them instead of hiding uncertainty behind one opaque confidence number.

### Local P28 rule

Do **not** assign one total confidence score and do **not** infer a compound strength from independent maxima.

For every direct Requirement/TREQ evidence path retain these orthogonal facts:

- System Reach: Component → Component integration → System → System integration.
- External Reality / boundary interaction: Local only → Substitute → Replay → Direct live.
- Representation Fidelity: Synthetic/Abstract → Surrogate/Simulated → Representative → Actual.
- M&S/surrogate validation factor where material: N/A or L0 → L4.
- Verification method: behavior/BDD, unit, integration, property, etc.
- Test sensitivity when objectively measured: mutation Test Strength.
- Evidence-producer trust basis / calibration links.

The primary evidence envelope therefore uses **two coupled matrices**:

1. `System Reach × External Reality`;
2. `System Reach × Representation Fidelity`.

A matrix cell is filled only if one retained evidence path has that exact pair. Example: `System integration × Substitute` from one BDD test plus `Component × Actual` from one property test does **not** imply `System integration × Actual`.

### Confidence profile and gaps

Contract Evidence reports, without collapsing them into one score:

- method corroboration / diversity;
- mutation Test Strength when available;
- producer trust-basis coverage;
- surrogate/model validation level;
- supporting child REQ/TREQ claims;
- explicit missing combinations / reasons for doubt.

Current system-level finding from retained P28 facts:

- 43/44 Requirement/TREQ contracts have direct verification evidence;
- 24/44 have System or System-integration evidence;
- 0/44 have Direct-live external evidence;
- 0/44 therefore have System/System-integration × Direct-live evidence.

This is assurance coverage, **not execution health**. A currently green test run does not fill a missing assurance cell, and a missing assurance cell does not mean the current implementation failed.

### Documentation role boundary

- Living Specifications: semantics, rationale/proof logic, executable/code binding; links outward to raw execution and assurance.
- Verification Health: current observed pass/fail.
- Verification Depth: how deep/realistic/strong verification reaches along one selected dimension.
- Mutation Analysis: Test Strength change/debt journal.
- Contract Evidence: system and per-contract assurance case, evidence envelope, corroboration, producer/model trust links and open gaps.
- Allure / MTE / raw evidence records: forensic execution details.

Future generic ownership: broader `ternforge-tooling-docops` traceability/assurance projection after the llm-router pilot is explicitly accepted. Do not extract during the active pilot.
