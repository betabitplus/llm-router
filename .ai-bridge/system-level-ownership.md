# Pilot invariant — system-level ownership and placement

This file is a standing rule for the llm-router pilot. Every new entity, field, metric, page, option, test model, coverage denominator, status, or generated artifact must be classified **before implementation**. Do not let a convenient local prototype silently become a platform concept.

## The four levels

| Level                                          | Meaning                                                                                                                                                                                                              | Authoring owner in the pilot  | Rule                                                                                                                  |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **A · Ternforge platform**                     | Universal shape, semantics, status vocabulary, generic test dimensions/classifications, schemas/renderers and reusable tooling that should work for any consumer                                                     | Ternforge platform repos      | Consumer data must not redefine or copy these semantics.                                                              |
| **B · Project / repository**                   | Only repo-specific choices not supplied by the platform: project thresholds, reusable domain Test Models and explicit project overrides                                                                              | `llm-router`                  | Define once and reuse across Requirements/Technical requirements; do not restate universal vocabulary.                |
| **C · Contract-specific verification profile** | Verification-design decisions that cannot be known project-wide: required criteria, Test level / Boundary / Representation selections, fault-model applicability, contract-specific minimums or justified deviations | `docs/verification-profiles/` | Reference normative Requirements/Technical requirements and project Test Models; never define product semantics here. |
| **D · Actual evidence**                        | Measured execution facts: pass/fail, observed interactions, coverage, mutation reach/sensitivity, freshness, provenance and producer facts                                                                           | tools / retained artifacts    | Never hand-author an Actual value to make a monitor green.                                                            |

The normal data flow is:

```text
A · platform contract
        ↓
B · project Test Plan / reusable models
        ↓
C · contract-specific Verification Profile
        ↓
D · automatically retained Actual evidence
        ↓
Requirement monitor = Verification Profile vs Actual → PASS / FAIL / N/A / UNKNOWN
```

## Mandatory design ledger

For every pilot addition, record or be able to answer all of the following before extraction:

1. **System level:** A / B / C / D.
2. **Canonical authoring source:** exact repo + document/module that owns the value.
3. **Visible surface:** exact portal page/section that renders it.
4. **Target vs Actual:** whether a human authors the target or tooling measures the fact.
5. **Reuse scope:** all Ternforge consumers / this repository / this Requirement only.
6. **Future platform owner:** exact repo and subsystem if the entity is generic.
7. **Extraction status:** consumer-local pilot / candidate for extraction / platform-owned.
8. **Rationale for any project-specific vocabulary:** especially when no external standard supplies the taxonomy.

A list or denominator is never allowed to appear only in UI code. If the monitor says `4 / 4`, the four target items must be traceable to the Test Plan/Test Model or the Requirement-specific applicability record.

## Requirement-monitor signal ledger

| Signal / entity                                                                                         | Level                      | Target owner/source                                                                                                  | Actual owner/source                                                                                                                                                                                                                                     | Future owner                                                             |
| ------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Verification criterion set / denominator                                                                | C                          | contract-specific Verification Profile + referenced B-level Test Model                                               | retained JUnit `coverage_item` bindings to declared `VC_*` criteria                                                                                                                                                                                     | `ternforge-tooling-docops` renderer + `py-testkit` capture               |
| Aggregation quantifier vocabulary (`ALL` / `ANY`)                                                       | A vocabulary + C selection | platform defines quantifier semantics; each Verification Profile selects the rule per signal                         | derived over retained criterion evidence/producers                                                                                                                                                                                                      | `ternforge-tooling-docops`                                               |
| Representation vocabulary (`Synthetic / abstract`, `Surrogate / simulated`, `Representative`, `Actual`) | A                          | platform monitor semantics; selected target value is C in the Verification Profile                                   | observed per-test representation fact                                                                                                                                                                                                                   | `ternforge-tooling-docops`                                               |
| Provenance states (`COMPLETE / INCOMPLETE / UNKNOWN`)                                                   | A                          | platform monitor invariant: retained proof is fully traceable                                                        | revision-pinned Requirement/TREQ + declared verification criterion + exact test-source digest + same-run JUnit/Allure/coverage/observation/input-snapshot digests                                                                                       | `ternforge-tooling-docops` + `py-testkit`                                |
| Producer qualification states (`QUALIFIED / NOT QUALIFIED / UNKNOWN`)                                   | A                          | platform monitor invariant: every producer that can affect admitted evidence is qualified for its exact intended use | retained executable false-green controls, pinned to current producer/tool/projection fingerprints; upstream trust links alone never produce `QUALIFIED`                                                                                                 | `py-testkit` qualification facts + `ternforge-tooling-docops` projection |
| Freshness states (`CURRENT / STALE / UNKNOWN`)                                                          | A semantics + B policy     | project Test Plan defines what counts as current                                                                     | same retained execution window plus the per-evidence subset of run-start inputs (test source, executed product code, normative/profile/Gherkin/harness inputs and retained replay/data assets); a changed relevant input makes only that evidence stale | `ternforge-infra-ci` retention + `ternforge-tooling-docops` projection   |
| `PASS / FAIL / N/A / UNKNOWN`                                                                           | A                          | platform status vocabulary                                                                                           | derived from Target vs Actual                                                                                                                                                                                                                           | `ternforge-tooling-docops`                                               |

None of these Level-A vocabularies should be copied into each consumer Test Plan. During the pilot their renderer/validation stays local to `llm-router`; extraction remains post-pilot.

## Future Ternforge ownership map

No platform repository is changed during this pilot. These are the preferred eventual owners **after explicit pilot acceptance**, not authorization to extract now.

| Capability                                                                                                                                                                        | Level       | Preferred Ternforge owner                 | Precise subsystem responsibility                                                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Requirement-monitor structure, status vocabulary, generic Test Level / Boundary / Representation semantics, Test Plan/Test Model projections, links from Sphinx-Needs             | A           | `ternforge-tooling-docops`                | Sphinx extension schemas/adapters + portal renderers; consumer supplies selections/data, not copied universal semantics.                                                              |
| Runtime evidence capture, test identity, observed boundary facts, per-test coverage contexts, semantic `coverage_item` declarations, generic mutation execution/report conversion | A/D tooling | `py-testkit`                              | Runtime/test instrumentation and standard retained evidence producers; consumer Test Models own the item IDs/meaning.                                                                 |
| Evidence retention, freshness windows, campaign history and CI orchestration                                                                                                      | A/D tooling | `ternforge-infra-ci`                      | CI retention/orchestration/history; not requirement semantics.                                                                                                                        |
| Structural linting of required project policy files / allowed locations                                                                                                           | A           | `ternforge-tooling-py-policy`             | Repository policy and file-placement rules only; it must not invent project verification targets.                                                                                     |
| Project Test Plan contents: repo-specific thresholds, reusable domain Test Models and explicit overrides                                                                          | B           | consumer repo (`llm-router` during pilot) | `docs/test-plan.md`; universal monitor/test vocabulary stays Level A and is not copied into the project page.                                                                         |
| Contract-specific verification applicability, criteria and justified deviations                                                                                                   | C           | consumer repo                             | dedicated `docs/verification-profiles/` pages that reference authoritative Requirements/Technical requirements; later represented by a typed DocOps schema when the pilot stabilizes. |
| Concrete JUnit/Allure/coverage/mutation/provenance facts                                                                                                                          | D           | generated/retained evidence               | Never authoritative authoring input; consumed by DocOps monitors.                                                                                                                     |

## llm-router pilot sources after this checkpoint

- **Normative contracts:** authoritative Requirements/Technical requirements under `docs/requirements/`; they define required behavior and engineering constraints, not test design.
- **Project policy / Test Plan:** `docs/test-plan.md`.
- **Contract-specific verification criteria:** dedicated profiles under `docs/verification-profiles/`; the first fully worked example is `invalid-configuration.md` for `REQ_INVALID_CONFIGURATION_ERRORS`.
- **Requirement monitor:** generated `verification-assurance.html`; P34 reads normative contracts + Level-B Test Plan + Level-C Verification Profile + Level-D retained evidence.
- **Actual execution inventory:** generated `verification.html`, Allure/JUnit and retained runtime artifacts.
- **Evidence-producer / proof-of-proof registry:** generated `evidence-trust.html`.
- **Mutation actual/history:** generated `mutation-analysis.html` + standard mutation artifacts.
- **Compatibility-only legacy source:** `.ai-bridge/assurance-targets.json` is frozen P33 input and is not used for P34 monitor status. It must not be treated as the long-term policy model.

## Working rule for the rest of the pilot

When discussing or implementing anything new, first state its level and owner. Prefer an existing standard/platform term or schema. If a concept would be copied unchanged between consumers, treat it as Level A even while the pilot implementation remains local. Level B contains only genuine repo-specific decisions. Contract-specific verification invention belongs in a Verification Profile, is the last resort, and must carry a rationale/deviation record.
