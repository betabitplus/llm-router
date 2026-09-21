# Requirement monitor readiness · llm-router pilot

Status: **P34 MONITOR CUTOVER COMPLETE**

| Input                                  | Level    | Canonical source                                      | Actual source                                                                                                                                               | State                                                                        |
| -------------------------------------- | -------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| UI/status contract                     | A        | `.ai-bridge/system-level-ownership.md`                | —                                                                                                                                                           | READY                                                                        |
| Project Test Plan                      | B        | `docs/test-plan.md`                                   | —                                                                                                                                                           | READY                                                                        |
| Contract-specific Verification Profile | C        | `docs/verification-profiles/invalid-configuration.md` | —                                                                                                                                                           | READY                                                                        |
| Verification criteria                  | C→D link | declared `VC_*` criteria in the Verification Profile  | `coverage_item(...)` declarations retained as standard JUnit properties + test result                                                                       | READY                                                                        |
| Test Level / Boundary mode             | D        | —                                                     | current coverage context + retained boundary observations/sentinels; depth facts only where current runtime evidence cannot establish the value             | READY                                                                        |
| Representation / M&S                   | D        | —                                                     | current coverage context for Actual target execution; retained model-validation facts only when a surrogate/model participates                              | READY                                                                        |
| Fault classes / mutation               | D        | —                                                     | `assurance-fault-model-facts.json` + fresh retained mutation campaign                                                                                       | READY                                                                        |
| Producer qualification                 | D        | —                                                     | `evidence-confidence-qualification.json`: executable intended-use false-green controls pinned to current tool/code fingerprints                             | READY                                                                        |
| Provenance                             | D        | —                                                     | `evidence-run-provenance.json` + exact JUnit/Allure/coverage/input-snapshot/test-source digests and same-run identity                                       | READY                                                                        |
| Freshness                              | D        | —                                                     | exact JUnit/Allure execution window + per-evidence comparison against the run-start input snapshot; only changed relevant inputs make a retained path stale | READY                                                                        |
| History                                | D        | —                                                     | legacy P31–P33 snapshots retained                                                                                                                           | READY · new Test Plan target history starts at monitor cutover; no back-fill |

## Actual → display mapping

| Actual fact                                                                               | Monitor value                                   |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------- |
| boundary `none` / `substitute` / `replay` / `direct`                                      | Local / Substitute / Replay / Direct live       |
| representation `synthetic_abstract` / `surrogate_simulated` / `representative` / `actual` | Synthetic / Surrogate / Representative / Actual |

Level A owns the display semantics. `docs/test-plan.md` contains only llm-router-specific Level-B choices; `verification-depth-facts.json` supplies Actual values only. Generic vocabulary must not be copied into the project page.

## Verification-criterion contract

The Invalid Configuration hierarchy declares fourteen stable criteria without collapsing Technical requirements into the parent:

- Parent `REQ_INVALID_CONFIGURATION_ERRORS`: 1 System criterion / 1 retained path for the public pre-provider rejection claim.
- Thirteen derived `TREQ_CONFIG_*` contracts: 13 Component criteria / 16 retained paths for the concrete configuration-validity constraints, each with its own Verification Profile, Fault Model, and Contract Evidence page.

Current execution satisfies the parent **1/1 System criterion · 1/1 path** and the child set **13/13 Component criteria · 16/16 paths**. This does **not** make the hierarchy green: the parent and child contracts keep independent blocking Fault Model targets, and missing child-specific challenges remain red instead of inheriting the parent mutation/fault campaign.

The profile parser now fails closed when a Required Coverage count disagrees with the criterion table, a criterion ID is duplicated, a Fault applicability table is absent, any project fault class is missing/duplicated/unknown, or a fault-group rationale is omitted. Missing fault authoring can therefore no longer silently become `N/A`.

Runtime binding is retained without inferring semantics from test names or directories:

`Verification Profile VC_* → pytest coverage_item marker → revision-pinned verifies contract → tests/conftest.py → JUnit property → nodeid result`

## P34 cutover

Contract Evidence now reads normative Requirements/Technical requirements + the Level-B Test Plan + the Level-C Verification Profile + retained Level-D Actual facts. The compatibility-only `.ai-bridge/assurance-targets.json` registry is not used for P34 monitor status.

Visible sections: `Test Coverage → Fault-based Testing → History`.

No Ternforge platform repository was changed.
