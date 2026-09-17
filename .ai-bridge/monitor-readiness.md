# Requirement monitor readiness · llm-router pilot

Status: **P34 MONITOR CUTOVER COMPLETE**

| Input                                  | Level    | Canonical source                                      | Actual source                                                                                                                                   | State                                                                        |
| -------------------------------------- | -------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| UI/status contract                     | A        | `.ai-bridge/system-level-ownership.md`                | —                                                                                                                                               | READY                                                                        |
| Project Test Plan                      | B        | `docs/test-plan.md`                                   | —                                                                                                                                               | READY                                                                        |
| Contract-specific Verification Profile | C        | `docs/verification-profiles/invalid-configuration.md` | —                                                                                                                                               | READY                                                                        |
| Verification criteria                  | C→D link | declared `VC_*` criteria in the Verification Profile  | `coverage_item(...)` declarations retained as standard JUnit properties + test result                                                           | READY                                                                        |
| Test Level / Boundary mode             | D        | —                                                     | current coverage context + retained boundary observations/sentinels; depth facts only where current runtime evidence cannot establish the value | READY                                                                        |
| Representation / M&S                   | D        | —                                                     | current coverage context for Actual target execution; retained model-validation facts only when a surrogate/model participates                  | READY                                                                        |
| Fault classes / mutation               | D        | —                                                     | `assurance-fault-model-facts.json` + fresh retained mutation campaign                                                                           | READY                                                                        |
| Producer qualification                 | D        | —                                                     | `evidence-confidence-qualification.json`: executable intended-use false-green controls pinned to current tool/code fingerprints                 | READY                                                                        |
| Provenance                             | D        | —                                                     | `evidence-run-provenance.json` + exact JUnit/Allure/coverage/input-snapshot/test-source digests and same-run identity                           | READY                                                                        |
| Freshness                              | D        | —                                                     | exact JUnit/Allure execution window + byte-for-byte run-start verification-input snapshot                                                       | READY                                                                        |
| History                                | D        | —                                                     | legacy P31–P33 snapshots retained                                                                                                               | READY · new Test Plan target history starts at monitor cutover; no back-fill |

## Actual → display mapping

| Actual fact                                                                               | Monitor value                                   |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------- |
| boundary `none` / `substitute` / `replay` / `direct`                                      | Local / Substitute / Replay / Direct live       |
| representation `synthetic_abstract` / `surrogate_simulated` / `representative` / `actual` | Synthetic / Surrogate / Representative / Actual |

Level A owns the display semantics. `docs/test-plan.md` contains only llm-router-specific Level-B choices; `verification-depth-facts.json` supplies Actual values only. Generic vocabulary must not be copied into the project page.

## Verification-criterion contract

The Verification Profile declares six stable criteria for `REQ_INVALID_CONFIGURATION_ERRORS`:

- Component: 5 criteria derived from the five configuration-validity Technical requirements
- System: 1 criterion for the parent public rejection Requirement

Current executable bindings:

- `VC_CONFIG_PROVIDER_IDENTITY` → unit test verifying `TREQ_CONFIG_PROVIDER_IDENTITY`
- `VC_CONFIG_REQUIRED_BASE_URL` → unit test verifying `TREQ_CONFIG_REQUIRED_BASE_URL`
- `VC_CONFIG_ATTEMPT_TIMEOUT` → unit test verifying `TREQ_CONFIG_ATTEMPT_TIMEOUT`
- `VC_CONFIG_RETRY_ATTEMPTS` → unit test verifying `TREQ_CONFIG_RETRY_ATTEMPTS`
- `VC_CONFIG_MODEL_DECLARATION` → **no Component binding**
- `VC_INVALID_CONFIGURATION_PUBLIC_REJECTION` → BDD public-path test verifying `REQ_INVALID_CONFIGURATION_ERRORS`

Current intended monitor result remains Component semantic coverage **4/5 · FAIL**; System semantic coverage **1/1 · PASS**.

Runtime binding is retained without inferring semantics from test names or directories:

`Verification Profile VC_* → pytest coverage_item marker → revision-pinned verifies contract → tests/conftest.py → JUnit property → nodeid result`

## P34 cutover

Contract Evidence now reads normative Requirements/Technical requirements + the Level-B Test Plan + the Level-C Verification Profile + retained Level-D Actual facts. The compatibility-only `.ai-bridge/assurance-targets.json` registry is not used for P34 monitor status.

Visible sections: `Test Coverage → Fault-based Testing → History`.

No Ternforge platform repository was changed.
