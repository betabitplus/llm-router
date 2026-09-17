from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
HTML = ROOT / "docs/_build/html"
RESULTS = HTML / "mutation-results"
BRIDGE = ROOT / ".ai-bridge"


def load(path: Path):
    return json.loads(path.read_text())


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def main() -> None:
    required = [
        RESULTS / "campaign.json",
        RESULTS / "summary.json",
        RESULTS / "triage.json",
        RESULTS / "operator-feedback.json",
        HTML / "verification-test-strength-facts.json",
        HTML / "mutation-analysis.html",
        HTML / "verification-depth-map.html",
        HTML / "verification-assurance.html",
        HTML / "requirement-monitor-facts.json",
        HTML / "evidence-run-provenance.json",
        HTML / "evidence-confidence-qualification.json",
        HTML / "assurance-fault-model-facts.json",
        HTML / "assurance-history/index.html",
        HTML / "assurance-history/assurance-history.csv",
        HTML / "assurance-history/REQ_INVALID_CONFIGURATION_ERRORS/index.html",
        HTML / "assurance-history/REQ_INVALID_CONFIGURATION_ERRORS/assurance-history.csv",
        HTML / "assurance-history/TREQ_RATE_LIMIT_STATE/index.html",
        HTML / "assurance-history/TREQ_RATE_LIMIT_STATE/assurance-history.csv",
        HTML / "assurance-targets.json",
        HTML / "assurance-snapshots.json",
        HTML / "favicon.ico",
        BRIDGE / "assurance-targets.json",
        BRIDGE / "assurance-snapshots.json",
        HTML / "specification-health.html",
        HTML / "verification-health-map.html",
        HTML / "_static/mutation-test-elements.js",
        BRIDGE / "mutation-testing-platform-extraction-manifest.md",
        BRIDGE / "system-level-ownership.md",
        BRIDGE / "monitor-readiness.md",
        ROOT / "docs/test-plan.md",
        HTML / "test-plan.html",
        ROOT / "docs/verification-profiles/invalid-configuration.md",
        HTML / "verification-profiles/invalid-configuration.html",
        ROOT / "test-results/evidence-run-inputs.json",
    ]
    for path in required:
        check(path.exists(), f"artifact exists: {path.relative_to(ROOT)}")

    campaign = load(RESULTS / "campaign.json")
    summary = load(RESULTS / "summary.json")
    triage = load(RESULTS / "triage.json")
    feedback = load(RESULTS / "operator-feedback.json")
    strength = load(HTML / "verification-test-strength-facts.json")
    depth_facts = load(HTML / "verification-depth-facts.json")
    monitor_facts = load(HTML / "requirement-monitor-facts.json")
    evidence_provenance = load(HTML / "evidence-run-provenance.json")
    evidence_qualification = load(HTML / "evidence-confidence-qualification.json")
    evidence_run_inputs = load(ROOT / "test-results/evidence-run-inputs.json")
    fault_model = load(HTML / "assurance-fault-model-facts.json")
    targets = load(BRIDGE / "assurance-targets.json")
    generated_targets = load(HTML / "assurance-targets.json")
    assurance_snapshots = load(BRIDGE / "assurance-snapshots.json")
    generated_assurance_snapshots = load(HTML / "assurance-snapshots.json")
    manifest = (BRIDGE / "mutation-testing-platform-extraction-manifest.md").read_text()
    ownership = (BRIDGE / "system-level-ownership.md").read_text()
    readiness = (BRIDGE / "monitor-readiness.md").read_text()
    test_plan_source = (ROOT / "docs/test-plan.md").read_text()
    test_plan_html = (HTML / "test-plan.html").read_text()
    configuration_source = (ROOT / "docs/requirements/configuration.md").read_text()
    verification_profile_source = (ROOT / "docs/verification-profiles/invalid-configuration.md").read_text()
    verification_profile_html = (HTML / "verification-profiles/invalid-configuration.html").read_text()
    pyproject_source = (ROOT / "pyproject.toml").read_text()
    unit_config_source = (ROOT / "tests/llm_router/unit/test_internal_config_validation.py").read_text()
    bdd_public_contract_source = (ROOT / "tests/llm_router/bdd/responses/test_public_contract.py").read_text()
    public_contract_feature = (ROOT / "features/responses/public_contract.feature").read_text()
    root_conftest_source = (ROOT / "tests/conftest.py").read_text()

    check(all(token in ownership for token in (
        "A · Ternforge platform",
        "B · Project / repository",
        "C · Contract-specific verification profile",
        "D · Actual evidence",
        "Requirement-monitor signal ledger",
        "Verification criterion set / denominator",
        "Aggregation quantifier vocabulary (`ALL` / `ANY`)",
        "Representation vocabulary",
        "Provenance states",
        "Producer qualification states",
        "Freshness states",
        "ternforge-tooling-docops",
        "py-testkit",
        "ternforge-infra-ci",
        "ternforge-tooling-py-policy",
    )), "system-level ownership invariant records all four levels, monitor signals and future platform owners")
    check(all(token in test_plan_source for token in (
        "(test-plan)=",
        "(test-plan-configuration-validation-model)=",
        "(test-plan-fault-model)=",
        "Mutation Reach floor",
        "Mutation Sensitivity floor",
        "Evidence freshness",
        "current retained run",
        "Retained mutmut Test Strength",
        "impl.comparison",
        "interface.unexpected-interaction",
        "spec.wrong-outcome",
        "required coverage = **100%**",
        "required deterministic fault detection = **100%**",
    )), "project Test Plan keeps only llm-router-specific decisions and reusable domain models")
    for generic_token in (
        "Scope\n**llm-router**",
        "PASS · FAIL · N/A · UNKNOWN",
        "Target flow",
        "Test levels",
        "Boundary mode",
        "### Representation",
        "### Evidence gates",
        "Requirement-local selection",
        "ISO/IEC/IEEE 29119",
    ):
        check(generic_token not in test_plan_source,
              f"project Test Plan omits generic/copied signal: {generic_token}")
    check(all(token in configuration_source for token in (
        ":id: REQ_INVALID_CONFIGURATION_ERRORS",
        ":revision: 2",
        "violates an applicable configuration constraint",
        "TREQ_CONFIG_PROVIDER_IDENTITY",
        "TREQ_CONFIG_MODEL_DECLARATION",
        "TREQ_CONFIG_REQUIRED_BASE_URL",
        "TREQ_CONFIG_ATTEMPT_TIMEOUT",
        "TREQ_CONFIG_RETRY_ATTEMPTS",
        "Verification profile →",
    )), "REQ_INVALID_CONFIGURATION_ERRORS contains normative behavior plus derived configuration constraints")
    for misplaced_token in (
        "## Verification target · REQ_INVALID_CONFIGURATION_ERRORS",
        "### Required coverage",
        "### Evidence aggregation",
        "### Fault applicability",
        "### Blocking mutation checks",
        "component:invalid-provider",
        "component:unknown-model",
        "system:unknown-model-public-error-before-provider",
    ):
        check(misplaced_token not in configuration_source,
              f"Requirement source excludes verification-design content: {misplaced_token}")
    check(all(token in verification_profile_source for token in (
        "## Profile · REQ_INVALID_CONFIGURATION_ERRORS",
        "### Required coverage",
        "### Verification criteria",
        "VC_CONFIG_PROVIDER_IDENTITY",
        "VC_CONFIG_MODEL_DECLARATION",
        "VC_CONFIG_REQUIRED_BASE_URL",
        "VC_CONFIG_ATTEMPT_TIMEOUT",
        "VC_CONFIG_RETRY_ATTEMPTS",
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
        "### Evidence aggregation",
        "### Fault applicability",
        "### Blocking mutation checks",
    )), "dedicated Verification Profile owns contract-specific verification design")
    check("coverage_item(id)" in pyproject_source,
          "coverage_item marker is registered under strict pytest markers")
    check(all(token in root_conftest_source for token in (
        '"coverage_item"',
        '"source_path"',
        '"source_sha256"',
        '"ternforge-retained-execution-inputs-1"',
        '"input_set_sha256"',
        '"docs/verification-profiles/**/*.md"',
    )), "criterion binding, exact test-source identity and run-start verification-profile snapshot are retained")
    declared_coverage = unit_config_source + "\n" + bdd_public_contract_source
    for coverage_item in (
        "VC_CONFIG_PROVIDER_IDENTITY",
        "VC_CONFIG_REQUIRED_BASE_URL",
        "VC_CONFIG_ATTEMPT_TIMEOUT",
        "VC_CONFIG_RETRY_ATTEMPTS",
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
    ):
        check(coverage_item in declared_coverage, f"declared runtime binding exists: {coverage_item}")
    check("VC_CONFIG_MODEL_DECLARATION" not in declared_coverage,
          "model-declaration criterion remains the intentional uncovered Component criterion")
    check(all(token in unit_config_source for token in (
        "TREQ_CONFIG_PROVIDER_IDENTITY[revision==1]",
        "TREQ_CONFIG_REQUIRED_BASE_URL[revision==1]",
        "TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]",
        "TREQ_CONFIG_RETRY_ATTEMPTS[revision==1]",
    )), "Component tests verify the derived Technical requirements rather than masquerading as parent-Requirement tests")
    check(
        "@REQ_INVALID_CONFIGURATION_ERRORS[revision==2]" in public_contract_feature and
        "And no provider request is sent" in public_contract_feature and
        "ProviderSentinelHTTPServer" in bdd_public_contract_source and
        'case["provider_requests"] == 0' in bdd_public_contract_source,
        "System criterion proves the parent public error and zero provider execution in the same BDD path",
    )

    qualification_producers = evidence_qualification.get("producers") or {}
    expected_confidence_producers = {
        "PRODUCER_PYTEST",
        "PRODUCER_ALLURE",
        "PRODUCER_PY_TESTKIT",
        "PRODUCER_PYTEST_BDD",
        "PRODUCER_SCRIPTED_HTTP_SERVER",
        "PRODUCER_LLM_ROUTER_TRACE_BRIDGE",
        "PRODUCER_ASSURANCE_ADAPTER",
        "PRODUCER_REQUIREMENT_MONITOR",
    }
    check(
        expected_confidence_producers <= set(qualification_producers) and
        all((qualification_producers[producer_id] or {}).get("status") == "QUALIFIED"
            for producer_id in expected_confidence_producers),
        "every evidence producer used by the Requirement monitor passed a retained intended-use false-green control",
    )
    check(
        evidence_run_inputs.get("schema") == "ternforge-retained-execution-inputs-1" and
        bool(evidence_run_inputs.get("input_set_sha256")) and
        bool(evidence_run_inputs.get("inputs")),
        "retained execution records an exact run-start verification-input snapshot",
    )
    check(
        evidence_provenance.get("schema") == "ternforge-evidence-run-provenance-1" and
        bool(evidence_provenance.get("run_id")) and
        all(bool(((evidence_provenance.get("subjects") or {}).get(name) or {}).get(key))
            for name, key in (
                ("junit", "sha256"),
                ("allure", "aggregate_sha256"),
                ("coverage", "sha256"),
                ("input_snapshot", "sha256"),
            )),
        "retained evidence run binds JUnit, Allure, coverage and input snapshot by digest",
    )
    monitor_contract = (monitor_facts.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    current_paths = list((monitor_contract.get("coverage_actual") or {}).values())
    check(len(current_paths) == 5, "Requirement monitor retains the expected five currently executed coverage paths")
    check(
        len({row.get("run_id") for row in current_paths}) == 1 and
        all(row.get("run_id") == evidence_provenance.get("run_id") for row in current_paths),
        "all current Requirement evidence paths belong to the same retained execution run",
    )
    check(
        all(row.get("provenance") == "COMPLETE" and row.get("provenance_scope") == "full_chain"
            for row in current_paths),
        "all current Requirement evidence paths have full-chain provenance",
    )
    check(
        all(row.get("producer_qualification") == "QUALIFIED" and
            row.get("producer_qualification_scope") == "full_chain"
            for row in current_paths),
        "all current Requirement evidence paths have a fully qualified producer chain",
    )
    check(
        all(row.get("freshness") == "CURRENT" for row in current_paths),
        "all current Requirement evidence paths belong to the current retained verification inputs",
    )
    check(
        all(row.get("source_sha256") and row.get("source_sha256") == row.get("current_source_sha256")
            for row in current_paths),
        "every current evidence path still matches the exact test-source bytes captured by its run",
    )
    system_path = (monitor_contract.get("coverage_actual") or {}).get(
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION"
    ) or {}
    check(
        system_path.get("level") == "system" and
        system_path.get("boundary") == "none" and
        "zero provider HTTP requests" in str(system_path.get("boundary_basis") or ""),
        "System coverage path derives System reach and Local boundary from current runtime evidence including the zero-request sentinel",
    )
    check(all(token in readiness for token in (
        "P34 MONITOR CUTOVER COMPLETE",
        "Component semantic coverage **4/5 · FAIL**",
        "System semantic coverage **1/1 · PASS**",
        "compatibility-only `.ai-bridge/assurance-targets.json`",
        "Test Coverage → Fault-based Testing → History",
    )), "monitor readiness ledger records the completed P34 target/actual cutover")
    check("Test plan" in test_plan_html and "Reusable Test Models" in test_plan_html,
          "generated Test Plan page renders the project-wide strategy")

    adapter = campaign.get("adapter") or {}
    check(adapter.get("version") == "p33-local-1", "retained mutation campaign keeps its original p33-local-1 adapter provenance")
    check(adapter.get("mutation_semantics_version") == "p21-local-2",
          "mutation semantics compatibility version remains explicit")
    check(campaign.get("mode") == "full", "retained pilot campaign is full audit")
    check(bool(campaign.get("run_id")), "retained pilot campaign has unique run_id")
    check(bool(campaign.get("baseline_run_id")), "retained pilot campaign has baseline_run_id")
    check(campaign.get("run_id") != campaign.get("baseline_run_id"), "run_id is not self-baseline")
    check(bool(campaign.get("finished_at")), "retained pilot campaign finished")
    check(float(campaign.get("duration_seconds") or 0) > 0, "retained pilot campaign has runtime")

    check(summary.get("total_contracts") == 44, "44 contracts remain in the verification-depth / mutation measurement universe")
    check(summary.get("measured_contracts") == 3, "exactly 3 objectively attributable measured contracts")
    check(summary.get("fresh_measured_contracts") == 3, "all measured contracts are fresh")
    check(summary.get("stale_measured_contracts") == 0, "no measured contract is stale")
    check(summary.get("new_unresolved_survivors") == 0, "no new unresolved survivor in current clean pilot state")
    check(summary.get("suppressed_survivors") == 0, "no acceptance suppression remains")
    check(summary.get("readiness") == "clear", "mutation readiness is clear")

    suppression_path = BRIDGE / "mutation-suppressions.json"
    if suppression_path.exists():
        suppressions = load(suppression_path).get("suppressions") or []
        check(not suppressions, "suppression ledger contains no acceptance-only suppression")
    else:
        check(True, "no suppression ledger remains in current clean pilot state")

    measured = campaign.get("contracts") or {}
    check(set(measured) == {
        "REQ_INVALID_CONFIGURATION_ERRORS",
        "TREQ_RATE_LIMIT_STATE",
        "TREQ_TOOL_REGISTRY",
    }, "current full audit measured the expected 3 pilot contracts")

    for contract_id, contract in measured.items():
        result = contract.get("result") or {}
        report_path = HTML / str(result.get("report_path"))
        wrapper_path = RESULTS / contract_id / "index.html"
        check(report_path.exists(), f"{contract_id}: standard mutation report retained")
        check(wrapper_path.exists(), f"{contract_id}: MTE wrapper retained")
        report = load(report_path)
        check(report.get("schemaVersion") == "2.0", f"{contract_id}: Mutation Testing Report Schema 2.0")
        killed = int(result.get("killed") or 0)
        survived = int(result.get("survived") or 0)
        valid = int(result.get("valid_mutants") or 0)
        check(valid == killed + survived, f"{contract_id}: valid mutant denominator is killed + survived")
        expected = round(100 * killed / valid, 1) if valid else None
        check(result.get("score") == expected, f"{contract_id}: Test Strength formula matches retained counts")

        declared = set(contract.get("linked_tests") or [])
        report_tests = {
            test.get("id")
            for row in (report.get("testFiles") or {}).values()
            for test in row.get("tests") or []
        }
        covered_by = {
            test_id
            for row in (report.get("files") or {}).values()
            for mutant in row.get("mutants") or []
            for test_id in mutant.get("coveredBy") or []
        }
        check(report_tests <= declared, f"{contract_id}: report tests are declared linked tests only")
        check(covered_by <= declared, f"{contract_id}: coveredBy cannot be inflated by unrelated tests")
        check(result.get("duration_seconds") is not None, f"{contract_id}: direct per-contract runtime retained")

        contract_triage = result.get("triage") or {}
        check(contract_triage.get("baseline_available") is True, f"{contract_id}: baseline evidence available")
        check(contract_triage.get("baseline_comparable") is True, f"{contract_id}: baseline comparable")
        check(contract_triage.get("new_unresolved_survivors") == 0, f"{contract_id}: no new unresolved survivor")
        check(contract_triage.get("score_delta") == 0.0, f"{contract_id}: current clean score delta is 0.0 pp")

    unattributed = strength.get("unattributed") or []
    check(len(unattributed) == 2, "two shared-scope diagnostics remain explicitly unattributed")

    filtering = feedback.get("filtering_decision") or {}
    check(filtering.get("decision") == "none", "P23 makes no operator filtering decision")
    check(filtering.get("full_audit_preserved") is True, "full audit mode preserved")
    check(filtering.get("diff_mode_filtering_enabled") is False, "diff operator filtering remains disabled")
    check((feedback.get("sample") or {}).get("directly_timed_contract_runs", 0) >= 3,
          "operator feedback includes directly timed contract runs")
    check(len(feedback.get("families") or []) >= 1, "operator feedback has retained diagnostic families")

    mutation_page = (HTML / "mutation-analysis.html").read_text()
    assurance_page = (HTML / "verification-assurance.html").read_text()
    spec_page = (HTML / "specification-health.html").read_text()
    health_page = (HTML / "verification-health-map.html").read_text()
    depth_page = (HTML / "verification-depth-map.html").read_text()
    trace_reader_page = (HTML / "traceability-reader.html").read_text()
    verification_page = (HTML / "verification.html").read_text()

    check(mutation_page.count('id="mutation-') >= 3, "Mutation Analysis exposes contract work queue anchors")
    check("Current signal" in mutation_page and "New 0" in mutation_page and "Debt 93" in mutation_page,
          "Mutation Analysis keeps the current mutation signal compact")
    check("How this helps during development" not in mutation_page,
          "Mutation Analysis no longer duplicates long usage guidance")
    check('id="mutation-history"' in mutation_page and "Recent changes" in mutation_page,
          "Mutation Analysis exposes compact retained change history")
    retained_history = [load(path) for path in sorted((RESULTS / "campaign-history").glob("*.json"))]
    history_triage = []
    for retained_run in retained_history:
        triage_totals = {"new": 0, "resolved": 0}
        for contract in (retained_run.get("contracts") or {}).values():
            retained_triage = ((contract.get("result") or {}).get("triage") or {})
            triage_totals["new"] += int(retained_triage.get("new_unresolved_survivors") or 0)
            triage_totals["resolved"] += int(retained_triage.get("resolved_survivors") or 0)
        history_triage.append(triage_totals)
    check(
        any(row["new"] == 3 for row in history_triage)
        and any(row["resolved"] == 3 for row in history_triage),
        "retained campaign history proves the New 3 → Resolved 3 acceptance cycle",
    )
    check("Fresh</strong> · New 0 · Debt 49" in mutation_page,
          "Mutation Analysis labels current survivor debt compactly")
    check("Why some contracts are N/A" in mutation_page,
          "Mutation Analysis keeps shared-scope diagnostics behind a compact disclosure")
    check('id="mutation-operator-feedback"' in mutation_page and "Run cost / mutation diagnostics" in mutation_page,
          "Mutation Analysis keeps operator diagnostics behind a compact disclosure")
    check(mutation_page.count("Shared @impl scope") >= 1, "portal retains shared-scope attribution warning")
    check('id="tf-strength-monitor"' not in depth_page and "Test Strength watch" not in depth_page,
          "Depth Map has no duplicate Test Strength watch")
    check("Missed example" in depth_page,
          "Depth Map keeps concise survivor detail in Test Strength hover")
    check("mutation-analysis.html#mutation-" in depth_page,
          "Depth Test Strength drill-down routes to Mutation Analysis")
    check("traceability-reader.html#review-" in depth_page,
          "non-mutation Depth drill-down routes to the contract in Traceability Reader")
    check("verification-assurance.html" not in depth_page,
          "Depth Map has no direct Contract Evidence link")
    check("DEPTH-P30-BOUNDARY-MODEL" in depth_page and
          'data-depth-mode="boundary"' in depth_page and
          "Boundary Reality" in depth_page,
          "Depth Map installs Boundary Reality as the second operational projection")
    check('data-depth-mode="representation"' not in depth_page and
          'mode==="representation"' not in depth_page and
          "tf-representation-headline" not in depth_page,
          "Representation Fidelity is no longer an equal/selectable Depth projection")
    check("Representation Fidelity</strong> now qualifies each concrete evidence path" in depth_page and
          "Same-path representation qualifiers" in depth_page and
          "exposure mode, not a universal weak→strong score" in depth_page,
          "Depth preserves Representation as a same-path qualifier and does not rank Boundary Reality as assurance strength")
    check('BOUNDARY_ORDER=["no_evidence","none","substitute","replay","direct"]' in depth_page and
          'label:"Direct live"' in depth_page,
          "Depth Boundary Reality retains Local → Substitute → Replay → Direct-live vocabulary")
    check("Assurance Target / Verification Profile" not in mutation_page and
          "Guarantee Frontier" not in mutation_page,
          "Mutation Analysis may link outward but does not duplicate Contract Evidence semantics")
    for contract_id in measured:
        wrapper=(RESULTS / contract_id / "index.html").read_text()
        check("verification-assurance.html" not in wrapper,
              f"{contract_id}: raw MTE wrapper has no Contract Evidence link")

    check("Contract Evidence" in assurance_page,
          "assurance page is named Contract Evidence")
    check("TERNFORGE-P34-REQUIREMENT-MONITOR-START" in assurance_page and
          assurance_page.count("TERNFORGE-P34-REQUIREMENT-MONITOR-START") == 1,
          "P34 Requirement monitor projection is installed once")
    check('"schema":"ternforge-requirement-monitor-p34-1"' in assurance_page,
          "embedded Requirement monitor model carries the P34 schema")
    for heading in ("1. Test Coverage", "2. Fault-based Testing", "3. History"):
        check(heading in assurance_page, f"P34 monitor contains agreed section: {heading}")
    for removed_heading in (
        "Evidence Frontier", "Fault Detection", "Evidence Trust", "Assurance Gap",
        "Evidence Paths", "Investigate", "Why / verification intent",
        "Possible ≠ Must ≠ Actual", "Target profile · ",
    ):
        check(removed_heading not in assurance_page,
              f"P34 monitor removes superseded section/concept: {removed_heading}")

    check("tf-p34-toc" in assurance_page and
          all(label in assurance_page for label in (">1 Test Coverage<", ">2 Fault-based Testing<", ">3 History<")),
          "P34 has only the three agreed monitor sections")
    for nav_label in ("Requirement ↗", "Verification profile ↗", "Test plan ↗", "Execution ↗"):
        check(nav_label in assurance_page, f"P34 outward navigation retains {nav_label}")
    check("anchor.closest('#verification-assurance-map > section[id^=\"assurance-\"]')" in assurance_page,
          "P34 same-page hashes keep the selected Requirement active")

    for status in ("PASS", "FAIL", "N/A", "UNKNOWN"):
        check(status in assurance_page, f"P34 visible status vocabulary contains {status}")
    check('const statusLabel=s=>' in assurance_page and '"MET":"PASS"' in assurance_page and '"NOT MET":"FAIL"' in assurance_page,
          "P34 keeps internal aggregation tokens hidden behind the public PASS / FAIL vocabulary")
    check("Weakest blocking signal" not in assurance_page and
          "tf-p34-summary" in assurance_page and
          "Test Coverage" in assurance_page and
          "Fault-based" in assurance_page and
          all(label in assurance_page for label in (
              "Component", "Component integration", "System", "System integration", "Acceptance",
              "Implementation", "Runtime / dependency", "Interface / protocol", "Architecture", "Specification / model",
          )),
          "P34 headline summarizes PASS / FAIL / N/A by coverage level and fault group")

    check("Test level" in assurance_page and
          all(label in assurance_page for label in ("Local", "Substitute", "Replay", "Direct live")) and
          all(label in assurance_page for label in ("Component", "Component integration", "System", "System integration", "Acceptance")),
          "P34 Test Coverage renders the agreed Test Level × Boundary matrix")
    check("data-cell=" in assurance_page and "tf-p34-cell-detail" in assurance_page and
          "Representation fidelity" in assurance_page and
          'actual:"Actual"' in assurance_page,
          "P34 matrix cells switch one compact parameter panel with explicit Representation value")
    check('disabled aria-disabled="true"' in assurance_page and
          "if(!target) return ''" in assurance_page,
          "P34 N/A coverage cells are disabled and cannot generate a detail panel")
    for signal in ("Semantic coverage", "Representation fidelity", "Provenance", "Producer qualification", "Freshness"):
        check(signal in assurance_page, f"P34 selected coverage cell exposes useful signal: {signal}")
    for removed_signal in (">Covered<", "M&S validation", "Evidence paths"):
        check(removed_signal not in assurance_page,
              f"P34 coverage detail removes redundant/non-applicable row: {removed_signal}")
    for criterion in (
        "VC_CONFIG_PROVIDER_IDENTITY", "VC_CONFIG_MODEL_DECLARATION",
        "VC_CONFIG_REQUIRED_BASE_URL", "VC_CONFIG_ATTEMPT_TIMEOUT",
        "VC_CONFIG_RETRY_ATTEMPTS", "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
    ):
        check(criterion in assurance_page, f"P34 embeds declared verification criterion: {criterion}")
    check("VC_CONFIG_MODEL_DECLARATION" in assurance_page and "UNKNOWN" in assurance_page,
          "P34 keeps the missing model-declaration criterion honest")
    check('metricSignalHtml("Semantic coverage",String(passed.length),String(target.declared_count),status)' in assurance_page,
          "P34 semantic coverage uses one Actual count and one Target count without duplicate percentages")
    check("data-summary-coverage" in assurance_page and "data-summary-fault" in assurance_page and
          "scrollMonitorTarget" in assurance_page and
          "syncMonitorChrome" in assurance_page and
          'const desiredTop=chrome.headerBottom+(isInternal?chrome.tocHeight+20:16)' in assurance_page and
          'target.startsWith("ce-coverage-")?selected' in assurance_page and
          ".bd-article-container{overflow:visible!important}" in assurance_page,
          "P34 coverage hash keeps the monitor verdict visible while other hashes remain fixed-header-aware")
    check("padding-bottom:34rem" in assurance_page,
          "P34 keeps enough bottom scroll room for History hash positioning")
    for link_label in ("Requirement ↗", "Verification profile ↗", "Test model ↗", "Raw facts ↗"):
        check(link_label in assurance_page, f"P34 coverage detail exposes deliberate drill-down link: {link_label}")
    check("Why this target?" not in assurance_page and
          "tf-p34-basis" not in assurance_page,
          "P34 monitor does not inline Requirement semantics or target rationale")
    check("tf-p34-state-lane" in assurance_page and
          all(option in assurance_page for option in (
              "Synthetic / abstract", "Surrogate / simulated", "Representative", "Actual",
              "COMPLETE", "INCOMPLETE", "QUALIFIED", "NOT QUALIFIED", "CURRENT", "STALE", "UNKNOWN",
          )) and
          "ACTUAL" in assurance_page and "TARGET" in assurance_page,
          "P34 categorical signals visibly show all options plus Actual and Target markers")
    check("tf-p34-help" in assurance_page and
          "Fails when a required behavior case in this cell has no passing evidence." in assurance_page and
          "Stops synthetic or surrogate evidence from being counted as proof that the required target actually ran." in assurance_page and
          "Checks that evidence-producing tools cannot silently turn bad verification into green evidence." in assurance_page and
          'button.setAttribute("aria-expanded"' in assurance_page,
          "P34 ? help states concrete failure modes in one sentence instead of embedded documentation")
    check("TERNFORGE-NO-CACHE" in assurance_page and
          'http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0"' in assurance_page,
          "P34 monitor HTML prevents stale local browser caching")
    check('id="ce-coverage-req_invalid_configuration_errors"' in assurance_page and
          'id="ce-faults-req_invalid_configuration_errors"' in assurance_page and
          'id="ce-history-req_invalid_configuration_errors"' in assurance_page and
          'id="tf-requirement-monitor"' in assurance_page and
          "EXPERIMENT" not in assurance_page,
          "accepted Requirement monitor is installed at canonical Contract Evidence anchors")
    check(not (HTML / "verification-assurance-experiment.html").exists(),
          "retired experiment page is not emitted after canonical cutover")
    check(all(label in assurance_page for label in (
              "Required evidence", "Retained path properties", "Evidence confidence",
              "passing required evidence", "4 pass", "1 missing", "scope-count", "model paths",
          )),
          "P34 canonical monitor makes required evidence the lead story and scopes properties to retained paths")
    check(all(label in assurance_page for label in ("N/A", "L0", "L1", "L2", "L3", "L4", "UNKNOWN", "NOT DECLARED", "INACTIVE")) and
          "dependent-wrap" in assurance_page and "M&amp;S validation" in assurance_page,
          "P34 canonical monitor nests M&S under Representation while retaining the complete inactive state space")
    check("ALL items" not in assurance_page and "ALL paths" not in assurance_page and
          "Conditional model check" not in assurance_page and "Depends on Representation" not in assurance_page,
          "P34 canonical monitor removes quantifier/meta prose that duplicated the visible denominators and hierarchy")
    check(".signal-card.na-signal{opacity:" not in assurance_page and
          "background:var(--pst-color-background)" in assurance_page and
          "PASS appears only when every required verification path" in assurance_page,
          "P34 canonical monitor keeps inactive tooltips opaque and uses the public PASS / FAIL vocabulary")
    check(all(label in assurance_page for label in (
              "Fault classes", "Required", "Challenged", "Detected",
              "Mutation checks", "Generated", "Reached", "Killed",
              "27/31", "11/27", "27/27",
          )) and
          "Detection effectiveness" not in assurance_page and
          "EXTRA" not in assurance_page,
          "P34 canonical monitor renders fault evidence as dependent denominator chains without non-blocking evidence badges")
    for criterion_text in (
        "A mismatched provider key and provider identity is rejected as invalid configuration.",
        "An undeclared requested model is rejected before provider execution.",
        "A provider that requires an explicit base URL is rejected when that URL is absent.",
        "A zero or negative effective attempt timeout is rejected.",
        "An effective retry maximum-attempt count below one is rejected.",
    ):
        check(criterion_text in assurance_page, f"P34 profile retains verification-criterion meaning outside the visible monitor: {criterion_text}")
    check("Evidence ↗" in assurance_page and "Criterion ↗" in assurance_page and
          "evidence_url" in assurance_page and
          "Gap: no passing evidence is retained for this required item in the selected cell." not in assurance_page,
          "P34 criteria stay monitor-only while routing passing evidence and missing criteria to drill-downs")

    check("data-fault-tab=" in assurance_page and
          all(label in assurance_page for label in (
              "Implementation", "Runtime / dependency", "Interface / protocol",
              "Architecture", "Specification / model",
          )),
          "P34 Fault-based Testing uses project Test Model groups as tabs")
    check("No required fault classes" in assurance_page and
          "EXTRA" not in assurance_page and
          "if(!stats.required.length) return ''" in assurance_page and
          'disabled aria-disabled="true"' in assurance_page,
          "P34 N/A fault groups are disabled without surfacing non-blocking optional evidence in the monitor")
    check("Rows = Test Levels; columns = boundary modes" in assurance_page and
          "Requirement-selected fault checks; N/A means this group has no required fault classes for this Requirement." in assurance_page,
          "P34 section-level ? help stays compact while explaining matrix axes and fault scope")
    check("metricRow('Required fault classes exercised',String(stats.exercised.length),String(stats.required.length)" in assurance_page and
          "metricRow('Exercised classes detected',String(detected),String(stats.exercised.length)" in assurance_page and
          "coverage=stats.exercised.length+' / '+stats.required.length" in assurance_page,
          "P34 fault detail uses one number per Actual/Target column and simple count ratios in tabs")
    for metric in (
        "Required fault classes exercised", "Exercised classes detected",
        "Component Mutation Reach", "System Mutation Reach",
        "Component Mutation Sensitivity", "System Mutation Sensitivity",
        "Retained mutmut Test Strength",
    ):
        check(metric in assurance_page, f"P34 Implementation detail exposes metric: {metric}")
    for fault_class in (
        "impl.comparison", "impl.boundary", "impl.control-flow",
        "interface.unexpected-interaction", "spec.wrong-outcome",
        "spec.missing-partition", "spec.wrong-ordering-boundary",
    ):
        check(fault_class in assurance_page, f"P34 embeds Requirement fault applicability: {fault_class}")
    for fault_semantic in (
        "A comparison/operator change alters the implementation decision.",
        "A boundary value or threshold change alters accepted vs rejected behavior.",
        "The system performs an external interaction that the contract says must not occur.",
        "A Requirement-relevant semantic partition is absent from verification.",
    ):
        check(fault_semantic in assurance_page, f"P34 fault class has semantic meaning: {fault_semantic}")
    check("Why this group?" not in assurance_page and
          "tf-p34-fault-class-main" not in assurance_page,
          "P34 fault monitor removes inline semantic rationale and long class descriptions")
    check("Profile ↗" in assurance_page and "Raw ↗" in assurance_page and
          "Verification profile ↗" in assurance_page and "Requirement ↗" in assurance_page,
          "P34 fault-class rows stay monitor-only and route missing vs exercised classes to the correct sources")
    check('"generated":31' in assurance_page and
          '"reached":27' in assurance_page and
          '"killed":11' in assurance_page and
          '"sensitivity":40.7' in assurance_page and
          '"sensitivity":100.0' in assurance_page and
          '"valid_mutants":102' in assurance_page and
          '"score":59.8' in assurance_page,
          "P34 embeds exact mutation Actuals with separate denominators")
    check("runtime.latency-timeout" in assurance_page and
          "architecture.forbidden-edge" in assurance_page and
          "optional" in assurance_page and "EXTRA" not in assurance_page,
          "P34 retains optional fault evidence in underlying facts without surfacing it as a monitor badge")

    check("Verification status" in assurance_page and
          "Component sensitivity" in assurance_page and
          "System sensitivity" in assurance_page and
          "Target revision" in assurance_page and
          "Full history ↗" in assurance_page,
          "P34 History stays compact and links to retained detail")
    check("Assurance is not pass/fail" not in assurance_page and
          "tf-gap-hero" not in assurance_page and
          "tf-path-group-grid" not in assurance_page and
          "tf-trust-item" not in assurance_page,
          "P34 default monitor contains no old prose/dashboard sections")

    check(targets == generated_targets,
          "generated Assurance Target registry is an exact projection of the local versioned source")
    check(targets.get("schema_version") == "ternforge-assurance-targets-p30-2",
          "Assurance Target registry keeps the agreed target schema")
    assignments = targets.get("assignments") or {}
    profiles = targets.get("profiles") or {}
    check(set(assignments) == {
          "REQ_INVALID_CONFIGURATION_ERRORS",
          "TREQ_RATE_LIMIT_STATE",
          "REQ_ASYNC_PROVIDER_EXECUTION",
    }, "P31 retains the three agreed Assurance Target counterexamples")
    check(all("overrides" in row and "issue_links" in row and "history" in row for row in assignments.values()),
          "every target assignment retains overrides, issue links and revision history explicitly")
    check(all((profile.get("cadence") or {}).get("mode") and (profile.get("freshness") or {}).get("policy")
              for profile in profiles.values()),
          "every target profile records cadence and freshness policy metadata")

    assignment = assignments["REQ_INVALID_CONFIGURATION_ERRORS"]
    profile = profiles.get(assignment.get("profile")) or {}
    obligations = profile.get("obligations") or []
    check(assignment.get("profile") == "public-preprovider-validation@1" and
          assignment.get("target_revision") == 1 and len(obligations) == 12,
          "Invalid Configuration has a versioned 12-obligation pilot Assurance Target")
    check(not any(
          o.get("kind") == "frontier_cell" and o.get("boundary") == "direct"
          for o in obligations
    ), "Invalid Configuration target intentionally contains no Direct-live obligation")
    check({
          (o.get("reach"), o.get("boundary"), o.get("representation_min"))
          for o in obligations if o.get("kind") == "frontier_cell"
    } == {("component", "none", "actual"), ("system", "none", "actual")},
          "Guarantee Frontier target is Component×Local and System×Local with Actual representation")
    check({
          (o.get("group"), o.get("kind"), o.get("min"))
          for o in obligations if o.get("kind") in {"mutation_reach", "mutation_sensitivity"}
    } == {
          ("component_local", "mutation_reach", 80.0),
          ("component_local", "mutation_sensitivity", 80.0),
          ("system_local", "mutation_reach", 80.0),
          ("system_local", "mutation_sensitivity", 80.0),
    }, "target keeps Mutation Reach and Sensitivity as separate obligations")
    check({
          o.get("layer") for o in obligations if o.get("kind") == "fault_layer"
    } == {"specification", "architecture", "interface", "runtime", "implementation"},
          "target covers the complete 5-layer Fault-model ladder")

    rate_assignment = assignments["TREQ_RATE_LIMIT_STATE"]
    rate_profile = profiles.get(rate_assignment.get("profile")) or {}
    rate_obligations = rate_profile.get("obligations") or []
    check(rate_assignment.get("profile") == "internal-state@1" and len(rate_obligations) == 3,
          "Rate-limit state uses the narrow internal-state Assurance Target")
    check(not any(o.get("kind") == "frontier_cell" and o.get("boundary") == "direct"
                  for o in rate_obligations),
          "Rate-limit state has no irrelevant Direct-live frontier obligation")
    check(any(o.get("kind") == "test_strength" and o.get("min") == 80.0
              for o in rate_obligations),
          "Rate-limit state targets the honestly available covered-mutant Test Strength instead of fabricating Mutation Reach")
    rate_strength = (strength.get("contracts") or {}).get("TREQ_RATE_LIMIT_STATE") or {}
    check(rate_strength.get("score") == 51.0,
          "Rate-limit state retained Test Strength is the real 51.0% signal")
    rate_tests = [row for row in depth_facts.get("tests") or []
                  if "TREQ_RATE_LIMIT_STATE" in (row.get("verifies") or [])]
    check(len(rate_tests) == 3 and all(
          row.get("system_reach") == "component" and
          row.get("boundary_mode") == "none" and
          row.get("representation_fidelity") == "actual"
          for row in rate_tests
    ), "Rate-limit state target is backed by three Component×Local×Actual paths")

    async_assignment = assignments["REQ_ASYNC_PROVIDER_EXECUTION"]
    async_profile = profiles.get(async_assignment.get("profile")) or {}
    async_obligations = async_profile.get("obligations") or []
    check(async_assignment.get("profile") == "external-provider-compatibility@1" and len(async_obligations) == 3,
          "Async provider execution uses the external-provider compatibility Assurance Target")
    async_frontier = {
          (o.get("reach"), o.get("boundary"), o.get("representation_min"), o.get("cadence"))
          for o in async_obligations if o.get("kind") == "frontier_cell"
    }
    check(async_frontier == {
          ("system_integration", "replay", "surrogate_simulated", "continuous_ci"),
          ("system_integration", "direct", "actual", "pre_release"),
    }, "provider-facing target requires repeatable Replay plus justified pre-release Direct-live evidence")
    async_tests = [row for row in depth_facts.get("tests") or []
                   if "REQ_ASYNC_PROVIDER_EXECUTION" in (row.get("verifies") or [])]
    check(len(async_tests) == 5 and all(
          row.get("system_reach") == "system_integration" and
          row.get("boundary_mode") == "replay" and
          row.get("representation_fidelity") == "surrogate_simulated"
          for row in async_tests
    ), "Async provider execution has five real System-integration×Replay×Surrogate paths")
    check(not any(row.get("boundary_mode") == "direct" for row in async_tests),
          "Async provider execution currently has no Direct-live path, creating the intended target-derived release gap")
    check(fault_model.get("schema_version") == "ternforge-fault-model-coverage-p31-1",
          "P31 retained fault-model facts use the expected schema")
    layers = {row.get("id"): row for row in fault_model.get("layers") or []}
    check(set(layers) == {"specification", "architecture", "interface", "runtime", "implementation"},
          "global pilot retains all 5 fault mechanisms")
    check(all(int(row.get("detected") or 0) > 0 for row in layers.values()),
          "every global fault mechanism has a real detected pilot challenge")
    check(layers["specification"].get("engine") == "Agentic Test Forge" and
          (layers["specification"].get("generated"), layers["specification"].get("detected")) == (6, 6),
          "Agentic Test Forge remains genuinely validated on Scenario Outline Examples mutation")
    check(layers["architecture"].get("engine") == "Import Linter" and
          layers["architecture"].get("baseline_kept") == 9 and
          layers["architecture"].get("detected") == 1,
          "global architecture mechanism proves a forbidden dependency negative control")
    check(layers["interface"].get("generic_mutator") is False and
          layers["interface"].get("detected") == 3,
          "global interface mechanism is honestly challenge-backed")
    check(layers["runtime"].get("engine") == "Toxiproxy" and
          layers["runtime"].get("detected") == 1,
          "global runtime mechanism is backed by real Toxiproxy fault injection")

    invalid_config_faults = (fault_model.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    groups = invalid_config_faults.get("groups") or {}
    component_faults = groups.get("component_local") or {}
    system_faults = groups.get("system_local") or {}
    check((component_faults.get("generated"), component_faults.get("reached"), component_faults.get("killed")) == (31, 27, 11) and
          component_faults.get("mutation_reach") == 87.1 and component_faults.get("sensitivity") == 40.7 and
          component_faults.get("system_reach") == "component" and component_faults.get("boundary_mode") == "none",
          "Component×Local fault cell retains exact generated/reached/killed, Reach and Sensitivity")
    check((system_faults.get("generated"), system_faults.get("reached"), system_faults.get("killed")) == (31, 27, 27) and
          system_faults.get("mutation_reach") == 87.1 and system_faults.get("sensitivity") == 100.0 and
          system_faults.get("system_reach") == "system" and system_faults.get("boundary_mode") == "none",
          "System×Local fault cell uses canonical Depth classification and proves stronger detection")
    check(set(component_faults.get("families") or {}) == {"boundary", "comparison"} and
          component_faults.get("engine_metadata") == "native pytest-gremlins operator metadata",
          "fault-family classifier uses engine-native pytest-gremlins metadata")
    check((component_faults["families"]["boundary"]["sensitivity"],
           component_faults["families"]["comparison"]["sensitivity"],
           system_faults["families"]["boundary"]["sensitivity"],
           system_faults["families"]["comparison"]["sensitivity"]) == (16.7, 60.0, 100.0, 100.0),
          "native boundary/comparison families retain exact cross-depth sensitivities")
    overlap = invalid_config_faults.get("detection_overlap") or {}
    check((overlap.get("mutant_universe"), overlap.get("detected_union"), overlap.get("corroborated"),
           overlap.get("component_only"), overlap.get("system_only"), overlap.get("undetected")) == (31, 27, 11, 0, 16, 4),
          "fault-model overlap uses exact engine-native mutant IDs for unique/corroborated/undetected detection")

    req_layers = invalid_config_faults.get("layers") or {}
    check(set(req_layers) == {"specification", "architecture", "interface", "runtime", "implementation"} and
          all(int(row.get("detected") or 0) > 0 for row in req_layers.values()),
          "profiled Requirement has real evidence on all 5 targeted fault layers")
    check(req_layers["specification"].get("engine") == "Cucumber Gherkin parser + pytest-bdd" and
          (req_layers["specification"].get("generated"), req_layers["specification"].get("detected")) == (1, 1) and
          req_layers["specification"].get("ast_validated") is True and
          "configuration error → Then it fails with a provider error" in req_layers["specification"].get("mutation", ""),
          "Requirement-specific specification outcome mutant is parse-valid and killed")
    check(req_layers["architecture"].get("engine") == "Import Linter" and
          (req_layers["architecture"].get("baseline_kept"), req_layers["architecture"].get("baseline_broken")) == (9, 0) and
          req_layers["architecture"].get("detected") == 1 and
          req_layers["architecture"].get("contract_id") == "private-core-layering",
          "Requirement-specific architecture mutant is killed by the real layering contract")
    check(req_layers["interface"].get("provider_requests") == 0 and
          req_layers["interface"].get("public_error") == "ConfigurationError" and
          req_layers["interface"].get("detected") == 1,
          "interface isolation probe proves invalid configuration touches no provider HTTP boundary")
    check(req_layers["runtime"].get("engine") == "Toxiproxy" and
          req_layers["runtime"].get("latency_ms") == 1500 and
          req_layers["runtime"].get("provider_requests") == 0 and
          req_layers["runtime"].get("public_error") == "ConfigurationError" and
          req_layers["runtime"].get("elapsed_seconds") is not None and
          float(req_layers["runtime"].get("elapsed_seconds")) < 1.0 and
          req_layers["runtime"].get("detected") == 1,
          "Toxiproxy proves provider degradation is irrelevant to the pre-provider claim")
    check((req_layers["implementation"].get("generated"), req_layers["implementation"].get("detected")) == (31, 27),
          "Requirement implementation fault layer is backed by the same 31-mutant universe with exact union detection")
    implementation = req_layers["implementation"]
    impl_reach = implementation.get("implementation_reach") or {}
    check((impl_reach.get("covered_statements"), impl_reach.get("executable_statements"), impl_reach.get("percent")) == (22, 24, 91.7) and
          impl_reach.get("missing_statements") == [22, 40] and
          impl_reach.get("metric") == "implementation_statement_reach" and
          "coverage.py executable statements" in impl_reach.get("basis", ""),
          "Implementation statement reach has an explicit honest 22/24 coverage.py denominator")
    check(implementation.get("overall_detection") == 87.1,
          "Overall Detection is retained as the secondary killed/generated metric")
    native_mutants = implementation.get("mutant_detail") or []
    check(len(native_mutants) == 31 and len({row.get("gremlin_id") for row in native_mutants}) == 31,
          "exact native mutant detail retains all 31 engine-native gremlin IDs without tuple-key collapse")
    check(sum(bool(row.get("component_killed")) for row in native_mutants) == 11 and
          sum(bool(row.get("system_killed")) for row in native_mutants) == 27 and
          sum(bool(row.get("system_reached")) for row in native_mutants) == 27,
          "exact native mutant table agrees with Component/System killed and reached counts")
    check(all("covering_tests" in row for group in (component_faults, system_faults) for row in group.get("mutants") or []),
          "per-mutant retained facts include covering tests without inventing killing tests")
    retained_mutmut = implementation.get("retained_mutmut") or {}
    check((retained_mutmut.get("killed"), retained_mutmut.get("survived"), retained_mutmut.get("valid_mutants")) == (61, 41, 102) and
          retained_mutmut.get("new_survivors") == 0 and
          retained_mutmut.get("existing_survivors") == 41 and
          retained_mutmut.get("resolved_survivors") == 0 and
          "mutate_only_covered_lines=true" in retained_mutmut.get("denominator_warning", ""),
          "retained mutmut Test Strength keeps its separate covered-lines denominator and survivor debt")
    for layer_id, required_fields in {
        "specification": ("claim_section", "mutation", "parser_validity", "execution_command", "detector", "source_url", "test_source_url"),
        "architecture": ("declared_rule", "baseline_summary", "injected_violation", "execution_command", "detector", "source_url"),
        "interface": ("dependency", "expected_interaction", "observed_interaction", "expected_public_error", "public_error", "detector", "source_url"),
        "runtime": ("dependency", "injected_fault", "expected_invariant", "observed_behavior", "detector", "source_url"),
    }.items():
        check(all(req_layers[layer_id].get(field) not in (None, "", []) for field in required_fields),
              f"{layer_id} fault detail retains all promised claim/challenge/detector/drill-down fields")

    # Evaluate the current target from retained facts: only Component Sensitivity should be open.
    current_actual = {
        "component-reach": component_faults.get("mutation_reach"),
        "component-sensitivity": component_faults.get("sensitivity"),
        "system-reach": system_faults.get("mutation_reach"),
        "system-sensitivity": system_faults.get("sensitivity"),
    }
    check(current_actual == {
        "component-reach": 87.1,
        "component-sensitivity": 40.7,
        "system-reach": 87.1,
        "system-sensitivity": 100.0,
    }, "current target actuals are stable")
    component_sensitivity = float(current_actual["component-sensitivity"] or 0.0)
    other_actuals = [
        float(value or 0.0)
        for key, value in current_actual.items()
        if key != "component-sensitivity"
    ]
    check(
        component_sensitivity < 80.0 and all(value >= 80.0 for value in other_actuals),
        "11/12 target result has exactly one blocking gap: Component mutation sensitivity",
    )

    check(assurance_snapshots == generated_assurance_snapshots,
          "generated assurance snapshot registry is an exact projection of the retained local source")
    check(assurance_snapshots.get("schema_version") == "ternforge-assurance-history-p31-1" and
          assurance_snapshots.get("history_starts_at_checkpoint") == "p31-local-1",
          "P31 assurance snapshot/event history starts explicitly without historical back-fill")
    snapshots = assurance_snapshots.get("snapshots") or []
    current_by_contract = {}
    for row in snapshots:
        current_by_contract[row.get("contract_id")] = row
    check(set(current_by_contract) == {
          "REQ_INVALID_CONFIGURATION_ERRORS",
          "TREQ_RATE_LIMIT_STATE",
          "REQ_ASYNC_PROVIDER_EXECUTION",
    }, "P31 snapshot history covers all three explicit Assurance Targets")
    invalid_snapshot = current_by_contract["REQ_INVALID_CONFIGURATION_ERRORS"]
    check((invalid_snapshot.get("obligations_met"), invalid_snapshot.get("obligations_total")) == (11, 12) and
          invalid_snapshot.get("blocking_gap_ids") == ["component-mutation-sensitivity"] and
          (invalid_snapshot.get("component_mutation_reach"), invalid_snapshot.get("component_mutation_sensitivity")) == (87.1, 40.7) and
          (invalid_snapshot.get("system_mutation_reach"), invalid_snapshot.get("system_mutation_sensitivity")) == (87.1, 100.0) and
          invalid_snapshot.get("test_strength") == 59.8 and
          (invalid_snapshot.get("fault_layers_detected"), invalid_snapshot.get("fault_layers_total")) == (5, 5),
          "primary Requirement snapshot retains obligations, gaps, Reach/Sensitivity, Test Strength and fault-layer state")
    rate_snapshot = current_by_contract["TREQ_RATE_LIMIT_STATE"]
    check((rate_snapshot.get("obligations_met"), rate_snapshot.get("obligations_total")) == (2, 3) and
          rate_snapshot.get("blocking_gap_ids") == ["covered-mutant-strength"] and
          rate_snapshot.get("test_strength") == 51.0,
          "internal-state snapshot retains only the honest covered-mutant Test Strength gap")
    async_snapshot = current_by_contract["REQ_ASYNC_PROVIDER_EXECUTION"]
    check((async_snapshot.get("obligations_met"), async_snapshot.get("obligations_total")) == (2, 3) and
          async_snapshot.get("blocking_gap_ids") == ["frontier-system-integration-live"],
          "provider-facing snapshot retains the justified pre-release Direct-live gap")
    check(all(any(
              row.get("contract_id") == contract_id and
              any(event.get("type") == "history_started" for event in row.get("events") or [])
              for row in snapshots)
              for contract_id in current_by_contract),
          "each target has an explicit P31 history-start event without requiring later snapshots to repeat it")
    check('"sensitivity":40.7' in assurance_page and
          '"boundary":"none"' in assurance_page and
          "VC_CONFIG_MODEL_DECLARATION" in assurance_page,
          "rendered P34 monitor keeps the real Component sensitivity and verification-criterion gap inputs")

    history = fault_model.get("history") or {}
    check(history.get("tool") == "DVC plots" and len(history.get("rows") or []) >= 11,
          "system Assurance History is rendered by DVC over retained mutation snapshots")
    history_page = (HTML / "assurance-history/index.html").read_text()
    check(("Assurance history · Test Strength" in history_page or
           "Assurance history \\u00b7 Test Strength" in history_page) and
          '"width": "container"' in history_page and
          ".vega-embed { width: 100%; max-width: 100%; }" in history_page and
          'rel="icon" href="data:,"' in history_page,
          "system DVC trend is standard, responsive, and clean")
    req_history = invalid_config_faults.get("history") or {}
    req_history_page = (HTML / "assurance-history/REQ_INVALID_CONFIGURATION_ERRORS/index.html").read_text()
    check(req_history.get("tool") == "DVC plots" and len(req_history.get("rows") or []) >= 1 and
          "REQ_INVALID_CONFIGURATION_ERRORS" in req_history_page and
          '"width": "container"' in req_history_page and
          'rel="icon" href="data:,"' in req_history_page,
          "Requirement-specific DVC trend is retained and responsive")
    rate_history = (fault_model.get("contract_histories") or {}).get("TREQ_RATE_LIMIT_STATE") or {}
    rate_history_page = (HTML / "assurance-history/TREQ_RATE_LIMIT_STATE/index.html").read_text()
    check(rate_history.get("tool") == "DVC plots" and len(rate_history.get("rows") or []) >= 1 and
          "TREQ_RATE_LIMIT_STATE" in rate_history_page and
          '"width": "container"' in rate_history_page and
          'rel="icon" href="data:,"' in rate_history_page,
          "internal-state retained DVC Test Strength history remains available outside the P34 Requirement monitor")

    check("TERNFORGE-P27-CONTRACT-EVIDENCE-START" not in assurance_page and
          "TERNFORGE-P29-ASSURANCE-EVIDENCE-START" not in assurance_page and
          "TERNFORGE-P31-ASSURANCE-EVIDENCE-START" not in assurance_page,
          "superseded Contract Evidence projections are absent")
    check("TERNFORGE-P22-MUTATION-START:" not in assurance_page and
          "Mutation / Test Strength" not in assurance_page,
          "Contract Evidence does not duplicate the Mutation Analysis journal")
    check("No evidence combines System/System integration reach with a Direct live external interaction." not in assurance_page and
          "No direct live external interaction is retained for this contract." not in assurance_page,
          "old generic gap inference is removed")
    check("TERNFORGE-P27-TRACE-EVIDENCE-START" in trace_reader_page and
          "verification-assurance.html#assurance-" in trace_reader_page,
          "Traceability Reader owns the per-contract Contract Evidence entry link")
    check("Assurance reading path" in verification_page and
          "where evidence is strong or missing across the system" in verification_page,
          "Verification overview documents system and per-contract assurance entry paths")

    direct_depth=[row for row in depth_facts.get("tests") or [] if row.get("boundary_mode")=="direct"]
    check(len(direct_depth)==0,
          "current retained evidence has zero Direct-live observations without treating them as a universal gap")
    living_pages=sorted((HTML / "specifications" / "_generated").glob("**/*.html"))
    check(bool(living_pages), "generated Living Specification pages exist")
    check(all("TERNFORGE-P28-LIVING-SEMANTICS-START" in path.read_text() for path in living_pages),
          "all Living Specification pages install the semantics-only projection")
    sample_living=(HTML / "specifications/_generated/responses/public-contract.html").read_text()
    check("Why trust this evidence? →" in sample_living and "Proof logic" in sample_living,
          "Living semantic projection links assurance and retains proof logic")
    check('if(text(title)!=="Verification boundary") return;' in sample_living and
          'if(label==="Evidence producers:"' in sample_living,
          "Living semantic projection removes boundary/producer details from the visible semantic narrative")

    check("TERNFORGE-P22-MEASUREMENT-START" in spec_page,
          "Specification Health has mutation measurement coverage")
    check("Open Test Strength on Verification Depth Map" in spec_page,
          "Specification Health routes mutation coverage to the overview map")
    for name, text in {
        "Health": health_page,
        "Depth": depth_page,
        "Specification Health": spec_page,
    }.items():
        check('href="mutation-analysis.html"' in text, f"{name}: portal navigation links Mutation Analysis")

    measurement_contract_ids = {row["contract_id"] for row in depth_facts.get("contracts") or []}
    check(len(measurement_contract_ids) == 44,
          "verification-depth / mutation measurement universe remains 44 contracts")
    requirements_text = "\n".join(
        path.read_text() for path in sorted((ROOT / "docs/requirements").glob("*.md"))
    )
    normative_contract_ids = set(re.findall(
        r"^:id:\s+((?:REQ|TREQ)_[A-Z0-9_]+)\s*$", requirements_text, flags=re.M
    ))
    check(len(normative_contract_ids) == 49,
          "normative Sphinx-Needs graph contains 49 Requirement/TREQ contracts")
    missing_contracts = sorted(
        contract_id for contract_id in normative_contract_ids if f"`{contract_id}`" not in manifest
    )
    check(not missing_contracts, f"extraction manifest classifies every normative contract: {missing_contracts}")
    for owner in ("py-testkit", "ternforge-infra-ci", "ternforge-tooling-docops", "py-policy"):
        check(owner in manifest, f"extraction manifest names future owner: {owner}")
    check("PILOT SCOPE GUARD — authoritative operating rule" in manifest,
          "manifest makes the llm-router-only pilot scope authoritative")
    check("llm-router P34" in manifest and
          "Current portal build: **P34**" in manifest and
          "1. Test Coverage → 2. Fault-based Testing → 3. History" in manifest and
          "Component semantic coverage **4/5 FAIL**" in manifest and
          "old custom Assurance Target/Profile registry is compatibility-only" in manifest,
          "manifest active checkpoint matches the current P34 Requirement monitor")
    check("all feature development happens inside" in manifest,
          "manifest forbids normal platform implementation during the active pilot")
    check("Post-pilot extraction backlog — DO NOT EXECUTE DURING ACTIVE PILOT" in manifest,
          "platform extraction is explicitly post-pilot backlog")
    check("COMPLETE FOR llm-router PILOT" not in manifest,
          "manifest contains no stale wording that marks premature extraction complete")
    for step in ("E1", "E2", "E3", "E4", "E5", "E6", "E7"):
        check(f"**{step} " in manifest, f"extraction manifest retains post-pilot migration step {step}")

    expected_bridge_files = {
        "assurance-targets.json",
        "assurance-snapshots.json",
        "build-mutation-report-prototype.py",
        "build-requirement-monitor.py",
        "qualify-evidence-confidence.py",
        "validate-mutation-pilot.py",
        "mutation-testing-integration-plan.md",
        "mutation-testing-platform-extraction-manifest.md",
        "system-level-ownership.md",
        "monitor-readiness.md",
        "verification-depth-map-local-prototype.md",
        "verification-depth-methodology-audit.md",
        "verification-health-map-local-prototype.md",
    }
    actual_bridge_files = {path.name for path in BRIDGE.iterdir() if path.is_file()}
    check(actual_bridge_files == expected_bridge_files,
          f"only substantive active-pilot .ai-bridge files remain: {sorted(actual_bridge_files)}")
    check(not (BRIDGE / "__pycache__").exists(), "no .ai-bridge __pycache__ debris remains")

    generated_paths = [
        str(path.relative_to(ROOT))
        for path in RESULTS.rglob("*")
        if path.is_file()
    ]
    generated_paths += [
        "docs/_build/html/mutation-analysis.html",
        "docs/_build/html/verification-test-strength-facts.json",
        "docs/_build/html/verification-depth-map.html",
        "docs/_build/html/verification-assurance.html",
        "docs/_build/html/assurance-fault-model-facts.json",
        "docs/_build/html/assurance-history/index.html",
        "docs/_build/html/assurance-history/assurance-history.csv",
        "docs/_build/html/assurance-history/REQ_INVALID_CONFIGURATION_ERRORS/index.html",
        "docs/_build/html/assurance-history/REQ_INVALID_CONFIGURATION_ERRORS/assurance-history.csv",
        "docs/_build/html/assurance-history/TREQ_RATE_LIMIT_STATE/index.html",
        "docs/_build/html/assurance-history/TREQ_RATE_LIMIT_STATE/assurance-history.csv",
        "docs/_build/html/assurance-targets.json",
        "docs/_build/html/assurance-snapshots.json",
        "docs/_build/html/favicon.ico",
        "docs/_build/html/specification-health.html",
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/test-plan.html",
        "docs/_build/html/_static/mutation-test-elements.js",
    ]
    missing_artifacts = sorted(path for path in generated_paths if f"`{path}`" not in manifest)
    check(not missing_artifacts, f"extraction manifest inventories all retained generated artifacts: {missing_artifacts}")

    check(not (ROOT / "mutants").exists(), "temporary mutmut workspace absent")
    setup = ROOT / "setup.cfg"
    check(not setup.exists() or "[mutmut]" not in setup.read_text(), "temporary mutmut setup config absent")

    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()
    approved_pilot_sources = {
        "docs/index.md",
        "docs/README.md",
        "docs/test-plan.md",
        "docs/experiments/index.md",
        "docs/requirements/configuration.md",
        "docs/verification-profiles/",
        "pyproject.toml",
        "src/llm_router/_internal/config/validation.py",
        "src/llm_router/_internal/runtime/routes.py",
        "tests/conftest.py",
        "features/responses/public_contract.feature",
        "tests/llm_router/bdd/responses/test_public_contract.py",
        "tests/llm_router/support/fault_server.py",
        "tests/llm_router/support/workers/error_boundary.py",
        "tests/llm_router/unit/test_internal_config_validation.py",
    }
    unexpected = []
    for line in status:
        if line.startswith("?? .ai-bridge"):
            continue
        path = line[3:]
        if path in approved_pilot_sources:
            continue
        unexpected.append(line)
    check(not unexpected, f"repository has no unrelated source changes outside approved pilot authoring files: {unexpected}")

    print("\nACTIVE LLM-ROUTER MUTATION PILOT STRUCTURAL GATE: PASS")


if __name__ == "__main__":
    main()
