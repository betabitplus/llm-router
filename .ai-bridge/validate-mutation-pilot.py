from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

ROOT = Path.cwd()
HTML = ROOT / "docs/_build/html"
RESULTS = HTML / "mutation-results"
BRIDGE = ROOT / ".ai-bridge"


def load(path: Path):
    return json.loads(path.read_text())


def only_campaign_extras(contract: dict, challenged: set, expected: set) -> bool:
    """Classes challenged beyond the declared retained challenges may only come from
    the current Implementation fault campaign."""
    classes = (contract.get("fault_actual") or {}).get("classes") or {}
    return set(expected) <= set(challenged) and all(
        class_id.startswith("impl.") and classes.get(class_id, {}).get("campaign_state") == "current"
        for class_id in set(challenged) - set(expected)
    )


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def declared_provider_capabilities() -> dict[str, dict[str, bool]]:
    """Read the five adapter-family capability declarations from source AST."""
    families = {
        "openai": ROOT / "src/llm_router/_internal/providers/openai_compatible.py",
        "qwenchat": ROOT / "src/llm_router/_internal/providers/qwenchat.py",
        "aistudio": ROOT / "src/llm_router/_internal/providers/aistudio.py",
        "gemini_webapi": ROOT / "src/llm_router/_internal/providers/gemini_webapi.py",
        "google_genai": ROOT / "src/llm_router/_internal/providers/google_genai.py",
    }
    keys = {
        "supports_images",
        "supports_files",
        "supports_video_file",
        "supports_video_url",
        "supports_json_schema",
        "supports_tools",
    }
    result: dict[str, dict[str, bool]] = {}
    for family, path in families.items():
        tree = ast.parse(path.read_text(), filename=str(path))
        calls = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "capabilities"
                for target in node.targets
            )
            and isinstance(node.value, ast.Call)
            and (
                (
                    isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "ProviderCapabilities"
                )
                or (
                    isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr == "ProviderCapabilities"
                )
            )
        ]
        if len(calls) != 1:
            raise AssertionError(
                f"{family}: expected exactly one ProviderCapabilities declaration"
            )
        values = dict.fromkeys(keys, False)
        for keyword in calls[0].keywords:
            if keyword.arg not in keys:
                continue
            if not isinstance(keyword.value, ast.Constant) or not isinstance(
                keyword.value.value, bool
            ):
                raise AssertionError(
                    f"{family}: capability {keyword.arg} must be a literal boolean"
                )
            values[keyword.arg] = keyword.value.value
        result[family] = values
    return result


def main() -> None:
    required = [
        RESULTS / "campaign.json",
        RESULTS / "summary.json",
        RESULTS / "triage.json",
        RESULTS / "operator-feedback.json",
        HTML / "verification-test-strength-facts.json",
        HTML / "mutation-analysis.html",
        HTML / "verification-health-map.html",
        HTML / "verification-assurance.html",
        HTML / "contract-evidence-request-override-precedence.html",
        HTML / "contract-evidence-credential-resolution.html",
        HTML / "contract-evidence-config-installation-coherence.html",
        HTML / "contract-evidence-config-cache-invalidation.html",
        HTML / "contract-evidence-config-provider-identity.html",
        HTML / "contract-evidence-config-model-declaration.html",
        HTML / "contract-evidence-config-required-base-url.html",
        HTML / "contract-evidence-config-attempt-timeout.html",
        HTML / "contract-evidence-config-retry-attempts.html",
        HTML / "contract-evidence-config-retry-wait-bounds.html",
        HTML / "contract-evidence-config-route-attempt-limit.html",
        HTML / "contract-evidence-config-fallback-shuffle-min-routes.html",
        HTML / "contract-evidence-config-tool-round-limit.html",
        HTML / "contract-evidence-config-structured-output-attempts.html",
        HTML / "contract-evidence-config-default-provider-declaration.html",
        HTML / "contract-evidence-config-default-model-mapping.html",
        HTML / "contract-evidence-config-model-provider-references.html",
        HTML / "assurance-feat-configuration-precedence.html",
        HTML / "assurance-goal-configuration-predictability.html",
        ROOT / "docs/assurance-profiles/configuration.md",
        HTML / "assurance-profiles/configuration.html",
        HTML / "specifications/_generated/configuration/assurance.html",
        HTML / "assurance-feat-structured-output.html",
        HTML / "assurance-goal-rich-input-output.html",
        ROOT / "docs/assurance-profiles/structured-output.md",
        HTML / "assurance-profiles/structured-output.html",
        HTML / "specifications/_generated/structured-output/assurance.html",
        HTML / "contract-evidence-tool-choice.html",
        HTML / "contract-evidence-multi-round-tool-execution.html",
        HTML / "contract-evidence-tool-runtime-safety.html",
        HTML / "contract-evidence-tool-registry.html",
        HTML / "assurance-feat-tool-selection.html",
        HTML / "assurance-feat-tool-execution.html",
        HTML / "assurance-goal-tool-orchestration.html",
        ROOT / "docs/assurance-profiles/tools.md",
        HTML / "assurance-profiles/tools.html",
        HTML / "specifications/_generated/tools/assurance.html",
        HTML / "contract-evidence-sync-route-fallback.html",
        HTML / "contract-evidence-route-timeout-fallback.html",
        HTML / "contract-evidence-route-attempt-limit.html",
        HTML / "contract-evidence-route-sticky-start.html",
        HTML / "contract-evidence-rate-limit-routing.html",
        HTML / "contract-evidence-provider-retry.html",
        HTML / "contract-evidence-provider-retry-classification.html",
        HTML / "contract-evidence-provider-retry-bounds.html",
        HTML / "contract-evidence-structured-output-repair.html",
        HTML / "contract-evidence-structured-output-attempt-bounds.html",
        HTML / "contract-evidence-repair-prompt-bounds.html",
        HTML / "assurance-feat-provider-retry.html",
        HTML / "assurance-feat-structured-recovery.html",
        HTML / "assurance-goal-resilient-execution.html",
        ROOT / "docs/assurance-profiles/resilience.md",
        HTML / "assurance-profiles/resilience.html",
        HTML / "specifications/_generated/resilience/assurance.html",
        HTML / "contract-evidence-sensitive-data-protection.html",
        HTML / "contract-evidence-runtime-log-safety.html",
        HTML / "contract-evidence-vcr-auth-redaction.html",
        HTML / "contract-evidence-vcr-request-content-redaction.html",
        HTML / "contract-evidence-vcr-response-content-redaction.html",
        HTML / "assurance-feat-sensitive-data-protection.html",
        HTML / "assurance-goal-data-safety.html",
        ROOT / "docs/assurance-profiles/security.md",
        HTML / "assurance-profiles/security.html",
        HTML / "contract-evidence-provider-adapter-interoperability.html",
        HTML / "contract-evidence-openai-adapter-boundary.html",
        HTML / "contract-evidence-qwenchat-adapter-boundary.html",
        HTML / "contract-evidence-aistudio-adapter-boundary.html",
        HTML / "contract-evidence-gemini-webapi-adapter-boundary.html",
        HTML / "contract-evidence-google-genai-adapter-boundary.html",
        HTML / "contract-evidence-async-provider-execution.html",
        HTML / "contract-evidence-response-normalization.html",
        HTML / "contract-evidence-usage-normalization.html",
        HTML / "contract-evidence-provider-error-boundary.html",
        HTML / "assurance-feat-provider-interoperability.html",
        HTML / "assurance-feat-async-execution.html",
        HTML / "assurance-feat-public-response-contract.html",
        HTML / "assurance-goal-provider-portability.html",
        ROOT / "docs/assurance-profiles/providers.md",
        HTML / "assurance-profiles/providers.html",
        HTML / "specifications/_generated/providers/assurance.html",
        HTML / "contract-evidence-session-lifecycle.html",
        HTML / "contract-evidence-session-persistence.html",
        HTML / "contract-evidence-session-serialization.html",
        HTML / "assurance-feat-session-lifecycle.html",
        HTML / "assurance-goal-session-continuity.html",
        HTML / "upper-assurance-facts.json",
        ROOT / "docs/assurance-profiles/sessions.md",
        HTML / "assurance-profiles/sessions.html",
        HTML / "specifications/_generated/sessions/assurance.html",
        HTML / "contract-evidence-public-api-surface.html",
        HTML / "contract-evidence-example-import-safety.html",
        HTML / "contract-evidence-structured-text-output.html",
        HTML / "contract-evidence-document-input.html",
        HTML / "contract-evidence-image-input.html",
        HTML / "contract-evidence-video-input.html",
        HTML / "contract-evidence-structured-schema-contract.html",
        HTML / "contract-evidence-multimodal-content-normalization.html",
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
        HTML / "verification-health-map.html",
        HTML / "_static/mutation-test-elements.js",
        BRIDGE / "mutation-testing-platform-extraction-manifest.md",
        BRIDGE / "system-level-ownership.md",
        BRIDGE / "monitor-readiness.md",
        ROOT / "docs/test-plan.md",
        HTML / "test-plan.html",
        ROOT / "docs/verification-profiles/invalid-configuration.md",
        HTML / "verification-profiles/invalid-configuration.html",
        ROOT / "docs/verification-profiles/tools.md",
        HTML / "verification-profiles/tools.html",
        ROOT / "docs/verification-profiles/routing.md",
        HTML / "verification-profiles/routing.html",
        ROOT / "docs/verification-profiles/resilience.md",
        HTML / "verification-profiles/resilience.html",
        ROOT / "docs/verification-profiles/security.md",
        HTML / "verification-profiles/security.html",
        ROOT / "docs/verification-profiles/providers.md",
        HTML / "verification-profiles/providers.html",
        ROOT / "docs/verification-profiles/sessions.md",
        HTML / "verification-profiles/sessions.html",
        ROOT / "docs/verification-profiles/developer.md",
        HTML / "verification-profiles/developer.html",
        ROOT / "docs/verification-profiles/structured-output.md",
        HTML / "verification-profiles/structured-output.html",
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
    upper_facts = load(HTML / "upper-assurance-facts.json")
    evidence_provenance = load(HTML / "evidence-run-provenance.json")
    evidence_qualification = load(HTML / "evidence-confidence-qualification.json")
    evidence_run_inputs = load(ROOT / "test-results/evidence-run-inputs.json")
    fault_model = load(HTML / "assurance-fault-model-facts.json")
    targets = load(BRIDGE / "assurance-targets.json")
    generated_targets = load(HTML / "assurance-targets.json")
    assurance_snapshots = load(BRIDGE / "assurance-snapshots.json")
    generated_assurance_snapshots = load(HTML / "assurance-snapshots.json")

    stale_required = []
    for contract_id, contract in (monitor_facts.get("contracts") or {}).items():
        target = contract.get("target") or {}
        required_items = {
            item_id
            for cell in target.get("coverage") or []
            for item_id in cell.get("items") or []
        }
        for item_id in required_items:
            for row in (contract.get("coverage_actual") or {}).get(item_id, []):
                if row.get("freshness") != "CURRENT":
                    stale_required.append(
                        f"{contract_id}:{item_id}:{row.get('nodeid') or 'unknown'}"
                    )
        if target.get("mutation"):
            mutation_fact = (strength.get("contracts") or {}).get(contract_id) or {}
            if mutation_fact.get("fresh") is False:
                stale_required.append(f"{contract_id}:mutation")

    for collection_name in ("features", "goals"):
        for entity_id, entity in (upper_facts.get(collection_name) or {}).items():
            for section in entity.values():
                if not isinstance(section, dict):
                    continue
                for criterion in section.get("criteria") or []:
                    if criterion.get("rows") and (criterion.get("freshness") or {}).get(
                        "status"
                    ) != "MET":
                        stale_required.append(f"{entity_id}:{criterion.get('id')}")
    product = upper_facts.get("product_system") or {}
    for section in product.values():
        if not isinstance(section, dict):
            continue
        for criterion in section.get("criteria") or []:
            if criterion.get("rows") and (criterion.get("freshness") or {}).get(
                "status"
            ) != "MET":
                stale_required.append(f"PRODUCT_SYSTEM:{criterion.get('id')}")

    check(
        not stale_required,
        "required retained evidence is fresh"
        + (f"; stale={', '.join(stale_required[:8])}" if stale_required else ""),
    )

    manifest = (BRIDGE / "mutation-testing-platform-extraction-manifest.md").read_text()
    ownership = (BRIDGE / "system-level-ownership.md").read_text()
    readiness = (BRIDGE / "monitor-readiness.md").read_text()
    test_plan_source = (ROOT / "docs/test-plan.md").read_text()
    test_plan_html = (HTML / "test-plan.html").read_text()
    configuration_source = (ROOT / "docs/requirements/configuration.md").read_text()
    verification_profile_source = (ROOT / "docs/verification-profiles/invalid-configuration.md").read_text()
    verification_profile_html = (HTML / "verification-profiles/invalid-configuration.html").read_text()
    configuration_profile_source = (ROOT / "docs/verification-profiles/configuration.md").read_text()
    configuration_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/configuration.md"
    ).read_text()
    routing_requirements_source = (ROOT / "docs/requirements/routing.md").read_text()
    routing_profile_source = (ROOT / "docs/verification-profiles/routing.md").read_text()
    resilience_requirements_source = (ROOT / "docs/requirements/resilience.md").read_text()
    resilience_profile_source = (ROOT / "docs/verification-profiles/resilience.md").read_text()
    resilience_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/resilience.md"
    ).read_text()
    security_requirements_source = (ROOT / "docs/requirements/security.md").read_text()
    security_profile_source = (ROOT / "docs/verification-profiles/security.md").read_text()
    security_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/security.md"
    ).read_text()
    provider_requirements_source = (ROOT / "docs/requirements/providers.md").read_text()
    provider_profile_source = (ROOT / "docs/verification-profiles/providers.md").read_text()
    provider_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/providers.md"
    ).read_text()
    session_requirements_source = (ROOT / "docs/requirements/sessions.md").read_text()
    session_profile_source = (ROOT / "docs/verification-profiles/sessions.md").read_text()
    session_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/sessions.md"
    ).read_text()
    developer_requirements_source = (ROOT / "docs/requirements/developer.md").read_text()
    developer_profile_source = (ROOT / "docs/verification-profiles/developer.md").read_text()
    developer_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/developer.md"
    ).read_text()
    product_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/product-system.md"
    ).read_text()
    structured_requirements_source = (ROOT / "docs/requirements/structured_output.md").read_text()
    structured_profile_source = (ROOT / "docs/verification-profiles/structured-output.md").read_text()
    structured_assurance_profile_source = (
        ROOT / "docs/assurance-profiles/structured-output.md"
    ).read_text()
    all_requirements_source = "\n".join(
        path.read_text()
        for path in sorted((ROOT / "docs/requirements").glob("*.md"))
    )
    pyproject_source = (ROOT / "pyproject.toml").read_text()
    unit_config_source = (ROOT / "tests/llm_router/unit/test_internal_config_validation.py").read_text()
    bdd_public_contract_source = (ROOT / "tests/llm_router/bdd/responses/test_public_contract.py").read_text()
    public_contract_feature = (ROOT / "features/responses/public_contract.feature").read_text()
    root_conftest_source = (ROOT / "tests/conftest.py").read_text()

    check(
        "**Verification intent.**" not in all_requirements_source,
        "all normative Requirement/TREQ cards are HOW-free; Verification Profiles own verification design",
    )
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
        "(test-plan-provider-retry-model)=",
        "(test-plan-structured-recovery-model)=",
        "(test-plan-data-safety-observability-audit-model)=",
        "(test-plan-sensitive-runtime-diagnostics-model)=",
        "(test-plan-vcr-redaction-model)=",
        "(test-plan-session-lifecycle-model)=",
        "(test-plan-session-persistence-model)=",
        "(test-plan-public-api-model)=",
        "(test-plan-example-import-safety-model)=",
        "(test-plan-structured-output-provider-matrix)=",
        "(test-plan-grounded-media-matrix)=",
        "(test-plan-schema-contract-model)=",
        "(test-plan-content-normalization-model)=",
        "(test-plan-fault-model)=",
        "Mutation Reach floor",
        "Mutation Sensitivity floor",
        "Evidence freshness",
        "relevant inputs current",
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
    check(all(token in routing_requirements_source for token in (
        ":id: GOAL_ROUTING_RELIABILITY",
        ":id: REQ_SYNC_ROUTE_FALLBACK",
        ":id: REQ_ROUTE_TIMEOUT_FALLBACK",
        ":id: REQ_ROUTE_ATTEMPT_LIMIT",
        ":id: REQ_ROUTE_STICKY_START",
        ":id: REQ_RATE_LIMIT_ROUTING",
        ":id: TREQ_ROUTE_ORDER",
        ":id: TREQ_RATE_LIMIT_STATE",
        ":id: TREQ_RATE_LIMIT_COOLDOWN_POLICY",
        ":id: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION",
    )), "routing Goal keeps both features and the full normative routing contract set")
    check(
        "**Verification intent.**" not in routing_requirements_source,
        "Routing normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in routing_profile_source for token in (
        "## Profile · REQ_SYNC_ROUTE_FALLBACK",
        "## Profile · REQ_ROUTE_TIMEOUT_FALLBACK",
        "## Profile · REQ_ROUTE_ATTEMPT_LIMIT",
        "## Profile · REQ_ROUTE_STICKY_START",
        "## Profile · TREQ_ROUTE_ORDER",
        "## Profile · REQ_RATE_LIMIT_ROUTING",
        "## Profile · TREQ_RATE_LIMIT_STATE",
        "## Profile · TREQ_RATE_LIMIT_COOLDOWN_POLICY",
        "## Profile · TREQ_RATE_LIMIT_AVAILABILITY_SELECTION",
        "VC_ROUTE_TIMEOUT_FALLBACK",
        "VC_ROUTE_STICKY_PUBLIC_NEXT_START",
        "VC_ROUTE_ORDER_STICKY_START_IDENTITY",
        "VC_RATE_LIMIT_SKIP_BLOCKED_ROUTE",
        "VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION",
        "VC_RATE_LIMIT_COOLDOWN_THRESHOLD",
        "VC_RATE_LIMIT_AVAILABLE_KEY_BEFORE_WAIT",
        "VC_RATE_LIMIT_ALL_BLOCKED_WAIT_EARLIEST",
        "### Required technical support",
        "### Fault applicability",
    )), "Routing Verification Profiles keep REQ/TREQ ownership split, explicit dependencies, and Fault Models")
    check(all(token in resilience_requirements_source for token in (
        ":id: GOAL_RESILIENT_EXECUTION",
        ":id: REQ_PROVIDER_RETRY",
        ":id: TREQ_PROVIDER_RETRY_CLASSIFICATION",
        ":id: TREQ_PROVIDER_RETRY_BOUNDS",
        ":id: REQ_STRUCTURED_OUTPUT_REPAIR",
        ":id: TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS",
        ":id: TREQ_REPAIR_PROMPT_BOUNDS",
    )), "Resilience Goal keeps both features and the full normative recovery contract set")
    check(
        "**Verification intent.**" not in resilience_requirements_source,
        "Resilience normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in resilience_profile_source for token in (
        "## Profile · REQ_PROVIDER_RETRY",
        "## Profile · TREQ_PROVIDER_RETRY_CLASSIFICATION",
        "## Profile · TREQ_PROVIDER_RETRY_BOUNDS",
        "## Profile · REQ_STRUCTURED_OUTPUT_REPAIR",
        "## Profile · TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS",
        "## Profile · TREQ_REPAIR_PROMPT_BOUNDS",
        "VC_PROVIDER_RETRY_STATUS_CLASSIFICATION",
        "VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION",
        "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY",
        "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY",
        "VC_PROVIDER_RETRY_ATTEMPT_BOUND",
        "VC_REPAIR_PROMPT_BOUNDS",
        "VC_STRUCTURED_REPAIR_RECOVERY",
        "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND",
        "### Required technical support",
        "### Fault applicability",
    )), "Resilience Verification Profiles split parent outcomes from first-class Technical support and explicit Fault Models")
    check(all(token in resilience_assurance_profile_source for token in (
        "## Feature · FEAT_PROVIDER_RETRY",
        "## Feature · FEAT_STRUCTURED_RECOVERY",
        "## Goal · GOAL_RESILIENT_EXECUTION",
        "AGI_RESILIENCE_RETRY_DURING_REPAIR",
        "AOV_RESILIENCE_COMBINED_BUDGET_CEILING",
    )), "Resilience Assurance Profile owns cross-capability recovery composition and combined bounded-work outcome")
    check(all(token in security_requirements_source for token in (
        ":id: GOAL_DATA_SAFETY",
        ":id: REQ_SENSITIVE_DATA_PROTECTION",
        ":id: TREQ_RUNTIME_LOG_SAFETY",
        ":revision: 2",
        ":id: TREQ_VCR_AUTH_REDACTION",
        ":id: TREQ_VCR_REQUEST_CONTENT_REDACTION",
        ":id: TREQ_VCR_RESPONSE_CONTENT_REDACTION",
    )), "Data Safety Goal keeps the complete normative diagnostic and durable-evidence contract set")
    check(
        "**Verification intent.**" not in security_requirements_source,
        "Data Safety normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in security_profile_source for token in (
        "## Profile · REQ_SENSITIVE_DATA_PROTECTION",
        "## Profile · TREQ_RUNTIME_LOG_SAFETY",
        "## Profile · TREQ_VCR_AUTH_REDACTION",
        "## Profile · TREQ_VCR_REQUEST_CONTENT_REDACTION",
        "## Profile · TREQ_VCR_RESPONSE_CONTENT_REDACTION",
        "VC_DATA_SAFETY_OBSERVABILITY_AUDIT",
        "VC_SECURITY_LOG_CONTEXT_FIELDS",
        "VC_VCR_AUTH_DURABLE_REDACTION",
        "VC_VCR_REQUEST_BODY_DURABLE_REDACTION",
        "VC_VCR_RESPONSE_ECHO_DURABLE_REDACTION",
        "VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS",
        "VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS",
        "VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS",
        "### Required technical support",
        "### Fault applicability",
    )), "Data Safety Verification Profiles split parent outcome from first-class technical support and explicit Fault Models")
    check(
        all(
            token in security_assurance_profile_source
            for token in (
                "## Feature · FEAT_SENSITIVE_DATA_PROTECTION",
                "### Capability integration",
                "### Capability validation",
                "## Goal · GOAL_DATA_SAFETY",
                "### Cross-capability integration",
                "### Outcome validation",
                "**Target:** N/A",
            )
        ),
        "Data Safety Assurance Profile keeps the one-Requirement/one-Feature upper topology explicitly N/A",
    )
    check(all(token in provider_requirements_source for token in (
        ":id: GOAL_PROVIDER_PORTABILITY",
        ":id: REQ_PROVIDER_ADAPTER_INTEROPERABILITY",
        ":id: TREQ_OPENAI_ADAPTER_BOUNDARY",
        ":id: TREQ_QWENCHAT_ADAPTER_BOUNDARY",
        ":id: TREQ_AISTUDIO_ADAPTER_BOUNDARY",
        ":id: TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY",
        ":id: TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY",
        ":id: REQ_ASYNC_PROVIDER_EXECUTION",
        ":id: REQ_RESPONSE_NORMALIZATION",
        ":id: TREQ_USAGE_NORMALIZATION",
        ":id: REQ_PROVIDER_ERROR_BOUNDARY",
    )), "Provider portability Goal keeps the complete normative adapter/public-contract set")
    check(
        "**Verification intent.**" not in provider_requirements_source,
        "Provider normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in provider_profile_source for token in (
        "## Profile · REQ_PROVIDER_ADAPTER_INTEROPERABILITY",
        "## Profile · TREQ_OPENAI_ADAPTER_BOUNDARY",
        "## Profile · TREQ_QWENCHAT_ADAPTER_BOUNDARY",
        "## Profile · TREQ_AISTUDIO_ADAPTER_BOUNDARY",
        "## Profile · TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY",
        "## Profile · TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY",
        "## Profile · REQ_ASYNC_PROVIDER_EXECUTION",
        "## Profile · REQ_RESPONSE_NORMALIZATION",
        "## Profile · TREQ_USAGE_NORMALIZATION",
        "## Profile · REQ_PROVIDER_ERROR_BOUNDARY",
        "VC_PROVIDER_ADAPTER_INTEROPERABILITY_MATRIX",
        "VC_PROVIDER_OPENAI_ADAPTER_BOUNDARY",
        "VC_PROVIDER_QWENCHAT_ADAPTER_BOUNDARY",
        "VC_PROVIDER_AISTUDIO_ADAPTER_BOUNDARY",
        "VC_PROVIDER_GEMINI_WEBAPI_ADAPTER_BOUNDARY",
        "VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY",
        "VC_ASYNC_TEXT_PROVIDER_MATRIX",
        "VC_ASYNC_STRUCTURED_PROVIDER_MATRIX",
        "VC_ASYNC_IMAGE_PROVIDER_MATRIX",
        "VC_ASYNC_DOCUMENT_PROVIDER_MATRIX",
        "VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX",
        "VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX",
        "VC_PROVIDER_USAGE_NORMALIZATION",
        "VC_PROVIDER_RESPONSE_EQUIVALENCE",
        "VC_PROVIDER_ERROR_HTTP",
        "VC_PROVIDER_ERROR_SDK",
        "### Required technical support",
        "### Fault applicability",
    )), "Provider Verification Profiles split parent product claims from first-class adapter/usage Technical support")
    check(all(token in provider_assurance_profile_source for token in (
        "## Feature · FEAT_PROVIDER_INTEROPERABILITY",
        "## Feature · FEAT_ASYNC_EXECUTION",
        "## Feature · FEAT_PUBLIC_RESPONSE_CONTRACT",
        "## Goal · GOAL_PROVIDER_PORTABILITY",
        "AC_PROVIDER_PUBLIC_SUCCESS_ERROR_STABILITY",
        "AGI_PROVIDER_SYNC_ASYNC_SWAP_EQUIVALENCE",
        "AOV_PROVIDER_SWAP_PRESERVES_SUCCESS_FAILURE_CONTRACT",
    )), "Provider Assurance Profile owns public success/error integration, provider swap integration, and Goal outcome validation")
    check(all(token in session_requirements_source for token in (
        ":id: GOAL_SESSION_CONTINUITY",
        ":id: REQ_SESSION_LIFECYCLE",
        ":id: REQ_SESSION_PERSISTENCE",
        ":id: TREQ_SESSION_SERIALIZATION",
    )), "Session continuity Goal keeps the complete normative lifecycle/persistence contract set")
    check(
        "**Verification intent.**" not in session_requirements_source,
        "Session normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in session_profile_source for token in (
        "## Profile · REQ_SESSION_LIFECYCLE",
        "## Profile · REQ_SESSION_PERSISTENCE",
        "## Profile · TREQ_SESSION_SERIALIZATION",
        "VC_SESSION_HISTORY_INCLUDED",
        "VC_SESSION_HISTORY_SUPPRESSED",
        "VC_SESSION_FORK_ISOLATION",
        "VC_SESSION_CLEAR_REUSE",
        "VC_SESSION_CONCURRENT_ISOLATION",
        "VC_SESSION_PERSISTENCE_GENERATED_STATE",
        "VC_SESSION_PUBLIC_MEDIA_PERSISTENCE",
        "VC_SESSION_SERIALIZATION_MEDIA",
        "VC_SESSION_SERIALIZATION_VERSION_REJECTION",
        "VC_SESSION_PUBLIC_PERSISTENCE",
        "### Required technical support",
        "Session serialization rejects incompatible data <TREQ_SESSION_SERIALIZATION>",
        "### Fault applicability",
    )), "Session Verification Profiles split public persistence from first-class serialization technical support")
    check(
        all(
            token in session_assurance_profile_source
            for token in (
                "## Feature · FEAT_SESSION_LIFECYCLE",
                "AC_SESSION_FORK_PERSISTENCE_ISOLATION",
                "### Capability validation",
                "**Target:** N/A",
                "## Goal · GOAL_SESSION_CONTINUITY",
                "### Cross-capability integration",
                "AOV_SESSION_RESTORED_CONTINUITY",
            )
        ),
        "Session Assurance Profile owns one cross-Requirement integration target and one distinct Goal outcome target",
    )
    check(all(token in developer_requirements_source for token in (
        ":id: GOAL_DEVELOPER_USABILITY",
        ":id: REQ_PUBLIC_API_SURFACE",
        ":id: REQ_EXAMPLE_IMPORT_SAFETY",
    )), "Developer usability Goal keeps the complete normative public-surface/example contract set")
    check(
        "**Verification intent.**" not in developer_requirements_source,
        "Developer normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in developer_profile_source for token in (
        "## Profile · REQ_PUBLIC_API_SURFACE",
        "## Profile · REQ_EXAMPLE_IMPORT_SAFETY",
        "VC_PUBLIC_API_ROOT_EXPORTS",
        "VC_EXAMPLE_IMPORT_SAFETY",
        "### Fault applicability",
    )), "Developer Verification Profiles own independent coverage targets and explicit Fault Models")
    check(
        all(
            token in developer_assurance_profile_source
            for token in (
                "## Feature · FEAT_PUBLIC_API",
                "## Feature · FEAT_EXECUTABLE_EXAMPLES",
                "## Goal · GOAL_DEVELOPER_USABILITY",
                "### Capability integration",
                "### Capability validation",
                "### Cross-capability integration",
                "### Outcome validation",
                "**Target:** N/A",
            )
        ),
        "Developer Assurance Profile explicitly owns upper-level N/A topology without duplicating Requirement proof",
    )
    check(
        "## Product / System" in product_assurance_profile_source
        and "### Cross-goal integration" in product_assurance_profile_source
        and "### Operational validation" in product_assurance_profile_source,
        "Product/System upper Targets live in one project-wide Assurance Profile",
    )
    check(all(token in structured_requirements_source for token in (
        ":id: GOAL_RICH_INPUT_OUTPUT",
        ":id: FEAT_STRUCTURED_OUTPUT",
        ":id: REQ_STRUCTURED_TEXT_OUTPUT",
        ":id: REQ_DOCUMENT_INPUT",
        ":id: REQ_IMAGE_INPUT",
        ":id: REQ_VIDEO_INPUT",
        ":id: REQ_STRUCTURED_SCHEMA_CONTRACT",
        ":id: REQ_MULTIMODAL_CONTENT_NORMALIZATION",
        ":revision: 2",
        "Draft 2020-12",
    )), "Rich input/output Goal keeps the complete normative structured/media contract set")
    check(
        "**Verification intent.**" not in structured_requirements_source,
        "Rich input/output normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in structured_profile_source for token in (
        "## Profile · REQ_STRUCTURED_TEXT_OUTPUT",
        "## Profile · REQ_DOCUMENT_INPUT",
        "## Profile · REQ_IMAGE_INPUT",
        "## Profile · REQ_VIDEO_INPUT",
        "## Profile · REQ_STRUCTURED_SCHEMA_CONTRACT",
        "## Profile · REQ_MULTIMODAL_CONTENT_NORMALIZATION",
        "VC_STRUCTURED_TEXT_PROVIDER_MATRIX",
        "VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX",
        "VC_IMAGE_GROUNDED_PROVIDER_MATRIX",
        "VC_VIDEO_LOCAL_GROUNDED_MATRIX",
        "VC_VIDEO_REMOTE_GROUNDED_MATRIX",
        "VC_SCHEMA_PYDANTIC_RECONSTRUCTION",
        "VC_SCHEMA_MAPPING_ENFORCEMENT",
        "VC_SCHEMA_INVALID_MAPPING_REJECTION",
        "VC_CONTENT_ORDER_DESCRIPTOR_METADATA",
        "VC_CONTENT_CHAT_MESSAGE_SEMANTICS",
        "VC_CONTENT_INVALID_INPUT_REJECTION",
        "VC_CONTENT_PRE_PROVIDER_REJECTION",
        "### Fault applicability",
    )), "Rich input/output Verification Profiles own independent coverage targets and explicit Fault Models")
    check(all(token in structured_assurance_profile_source for token in (
        "## Feature · FEAT_STRUCTURED_OUTPUT",
        "## Goal · GOAL_RICH_INPUT_OUTPUT",
        "AC_RICH_SCHEMA_MEDIA_COMPOSITION",
        "ACV_RICH_INVALID_SCHEMA_PRE_PROVIDER",
        "AOV_RICH_PROVIDER_SWAP_EQUIVALENCE",
    )), "Rich input/output Assurance Profile owns composition, pre-provider validation, and provider-swap outcome Targets")

    check(all(token in verification_profile_source for token in (
        "## Profile · REQ_INVALID_CONFIGURATION_ERRORS",
        "## Profile · TREQ_CONFIG_PROVIDER_IDENTITY",
        "## Profile · TREQ_CONFIG_MODEL_DECLARATION",
        "## Profile · TREQ_CONFIG_REQUIRED_BASE_URL",
        "## Profile · TREQ_CONFIG_ATTEMPT_TIMEOUT",
        "## Profile · TREQ_CONFIG_RETRY_ATTEMPTS",
        "## Profile · TREQ_CONFIG_RETRY_WAIT_BOUNDS",
        "## Profile · TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT",
        "## Profile · TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES",
        "## Profile · TREQ_CONFIG_TOOL_ROUND_LIMIT",
        "## Profile · TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS",
        "## Profile · TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION",
        "## Profile · TREQ_CONFIG_DEFAULT_MODEL_MAPPING",
        "## Profile · TREQ_CONFIG_MODEL_PROVIDER_REFERENCES",
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
        "### Required technical support",
        "### Fault applicability",
        "### Blocking mutation checks",
    )), "Invalid Configuration profile splits the parent public rejection claim from all thirteen first-class Technical requirements")
    check(
        "## Profile · REQ_CONFIG_INSTALLATION_COHERENCE" in configuration_profile_source
        and "## Profile · TREQ_CONFIG_CACHE_INVALIDATION" in configuration_profile_source
        and "### Required technical support" in configuration_profile_source,
        "Configuration activation profile splits cache invalidation into first-class Technical support",
    )
    check(all(token in configuration_assurance_profile_source for token in (
        "## Feature · FEAT_CONFIGURATION_PRECEDENCE",
        "## Goal · GOAL_CONFIGURATION_PREDICTABILITY",
        "AC_CONFIGURATION_EFFECTIVE_VIEW_COMPOSITION",
        "ACV_CONFIGURATION_POST_INSTALL_REJECTION",
    )), "Configuration Assurance Profile owns the distinct cross-Requirement composition and post-install validation Targets")
    check(
        "coverage_item(id)" in pyproject_source
        and "coverage_path(id_or_selector)" in pyproject_source
        and "fault_item(contract_id, id)" in pyproject_source,
        "semantic coverage, exact path identity and contract-specific fault markers are registered under strict pytest markers",
    )
    check(all(token in root_conftest_source for token in (
        '"coverage_item"',
        '"coverage_path"',
        '"fault_item"',
        '"fault_items"',
        '"source_path"',
        '"source_sha256"',
        '"ternforge-retained-execution-inputs-1"',
        '"input_set_sha256"',
        '"docs/verification-profiles/**/*.md"',
    )), "criterion binding, exact test-source identity and run-start verification-profile snapshot are retained")
    declared_coverage = unit_config_source + "\n" + bdd_public_contract_source
    for coverage_item in (
        "VC_CONFIG_PROVIDER_IDENTITY",
        "VC_CONFIG_MODEL_DECLARATION",
        "VC_CONFIG_REQUIRED_BASE_URL",
        "VC_CONFIG_ATTEMPT_TIMEOUT",
        "VC_CONFIG_RETRY_ATTEMPTS",
        "VC_CONFIG_RETRY_WAIT_BOUNDS",
        "VC_CONFIG_ROUTE_ATTEMPT_LIMIT",
        "VC_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES",
        "VC_CONFIG_TOOL_ROUND_LIMIT",
        "VC_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS",
        "VC_CONFIG_DEFAULT_PROVIDER_DECLARATION",
        "VC_CONFIG_DEFAULT_MODEL_MAPPING",
        "VC_CONFIG_MODEL_PROVIDER_REFERENCES",
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
    ):
        check(coverage_item in declared_coverage, f"declared runtime binding exists: {coverage_item}")
    check(all(token in unit_config_source for token in (
        "TREQ_CONFIG_PROVIDER_IDENTITY[revision==1]",
        "TREQ_CONFIG_MODEL_DECLARATION[revision==1]",
        "TREQ_CONFIG_REQUIRED_BASE_URL[revision==1]",
        "TREQ_CONFIG_ATTEMPT_TIMEOUT[revision==1]",
        "TREQ_CONFIG_RETRY_ATTEMPTS[revision==1]",
        "TREQ_CONFIG_RETRY_WAIT_BOUNDS[revision==1]",
        "TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT[revision==1]",
        "TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES[revision==1]",
        "TREQ_CONFIG_TOOL_ROUND_LIMIT[revision==1]",
        "TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS[revision==1]",
        "TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION[revision==1]",
        "TREQ_CONFIG_DEFAULT_MODEL_MAPPING[revision==1]",
        "TREQ_CONFIG_MODEL_PROVIDER_REFERENCES[revision==1]",
    )), "Component tests verify the full derived Technical-requirement set rather than masquerading as parent-Requirement tests")
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
        "PRODUCER_HYPOTHESIS",
        "PRODUCER_SCRIPTED_HTTP_SERVER",
        "PRODUCER_VCR",
        "PRODUCER_LLM_ROUTER_TRACE_BRIDGE",
        "PRODUCER_ASSURANCE_ADAPTER",
        "PRODUCER_REQUIREMENT_MONITOR",
        "PRODUCER_GOOGLE_GENAI_FAKE_SDK",
        "PRODUCER_GEMINI_WEBAPI_FAKE_SDK",
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
        {"tests/**/cassettes/**/*", "tests/llm_router/data/**/*"}
        <= set(evidence_run_inputs.get("input_scope") or []),
        "retained input snapshot includes replay cassettes and test data used by evidence",
    )
    retained_rows = [
        row
        for contract in (monitor_facts.get("contracts") or {}).values()
        for bindings in (contract.get("coverage_actual") or {}).values()
        for row in bindings
    ]
    check(
        all(
            isinstance(row.get("freshness_input_count"), int)
            and isinstance(row.get("freshness_changed_inputs"), list)
            and bool(row.get("freshness_input_sha256"))
            for row in retained_rows
        ),
        "each retained Requirement/TREQ evidence path records per-evidence freshness inputs",
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
    invalid_child_ids = (
        "TREQ_CONFIG_PROVIDER_IDENTITY",
        "TREQ_CONFIG_MODEL_DECLARATION",
        "TREQ_CONFIG_REQUIRED_BASE_URL",
        "TREQ_CONFIG_ATTEMPT_TIMEOUT",
        "TREQ_CONFIG_RETRY_ATTEMPTS",
        "TREQ_CONFIG_RETRY_WAIT_BOUNDS",
        "TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT",
        "TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES",
        "TREQ_CONFIG_TOOL_ROUND_LIMIT",
        "TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS",
        "TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION",
        "TREQ_CONFIG_DEFAULT_MODEL_MAPPING",
        "TREQ_CONFIG_MODEL_PROVIDER_REFERENCES",
    )
    parent_paths = [
        row
        for rows in (monitor_contract.get("coverage_actual") or {}).values()
        for row in rows
    ]
    child_paths = [
        row
        for contract_id in invalid_child_ids
        for rows in (
            (monitor_facts.get("contracts") or {}).get(contract_id, {}).get(
                "coverage_actual", {}
            )
        ).values()
        for row in rows
    ]
    current_paths = parent_paths + child_paths
    check(
        len(parent_paths) == 1
        and len(child_paths) == 16
        and len(current_paths) == 17,
        "Invalid Configuration evidence keeps one parent public path plus sixteen child-TREQ validation paths",
    )
    check(
        len({row.get("run_id") for row in current_paths}) == 1 and
        all(row.get("run_id") == evidence_provenance.get("run_id") for row in current_paths),
        "all current parent/TREQ Invalid Configuration evidence paths belong to the same retained execution run",
    )
    check(
        all(row.get("provenance") == "COMPLETE" and row.get("provenance_scope") == "full_chain"
            for row in current_paths),
        "all current parent/TREQ Invalid Configuration evidence paths have full-chain provenance",
    )
    check(
        all(row.get("producer_qualification") == "QUALIFIED" and
            row.get("producer_qualification_scope") == "full_chain"
            for row in current_paths),
        "all current parent/TREQ Invalid Configuration evidence paths have a fully qualified producer chain",
    )
    check(
        all(row.get("freshness") == "CURRENT" for row in current_paths),
        "all current parent/TREQ Invalid Configuration evidence paths belong to the current retained verification inputs",
    )
    check(
        all(row.get("source_sha256") and row.get("source_sha256") == row.get("current_source_sha256")
            for row in current_paths),
        "every current evidence path still matches the exact test-source bytes captured by its run",
    )
    system_paths = (monitor_contract.get("coverage_actual") or {}).get(
        "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION"
    ) or []
    system_path = system_paths[0] if len(system_paths) == 1 else {}
    system_boundary_basis = str(system_path.get("boundary_basis") or "")
    check(
        system_path.get("level") == "system"
        and system_path.get("boundary") == "none"
        and "provider-boundary observation" in system_boundary_basis
        and "zero HTTP requests" in system_boundary_basis,
        "System coverage path proves System reach and Local boundary from the current zero-request provider-boundary observation",
    )

    depth_source = depth_facts.get("source_run") or {}
    depth_audit = depth_facts.get("audit") or {}
    depth_inputs = depth_source.get("inputs") or {}
    provenance_subjects = evidence_provenance.get("subjects") or {}
    retained_test_count = int(depth_source.get("tests") or 0)
    check(
        depth_facts.get("schema_version") == 4
        and retained_test_count >= 189
        and depth_source.get("passed") == retained_test_count
        and depth_audit.get("contracts") == 63
        and depth_audit.get("runtime_evidence") == retained_test_count
        and depth_audit.get("nodeid_mismatches") == 0
        and depth_audit.get("verifies_mismatches") == 0
        and depth_audit.get("bdd_feature_scenario_errors") == 0,
        "Depth facts are reproducibly regenerated from the current retained test run",
    )
    check(
        ((depth_inputs.get("junit") or {}).get("sha256")
         == (provenance_subjects.get("junit") or {}).get("sha256"))
        and ((depth_inputs.get("allure") or {}).get("aggregate_sha256")
             == (provenance_subjects.get("allure") or {}).get("aggregate_sha256"))
        and ((depth_inputs.get("coverage") or {}).get("sha256")
             == (provenance_subjects.get("coverage") or {}).get("sha256"))
        and ((depth_inputs.get("coverage_db") or {}).get("sha256")
             == (provenance_subjects.get("coverage_db") or {}).get("sha256")),
        "Depth classification is digest-bound to the exact JUnit, Allure, coverage JSON and dynamic-context DB used by the monitor",
    )
    depth_by_nodeid = {
        row.get("nodeid"): row for row in depth_facts.get("tests") or []
    }
    all_monitor_paths = [
        row
        for contract in (monitor_facts.get("contracts") or {}).values()
        for rows in (contract.get("coverage_actual") or {}).values()
        for row in rows
    ]
    check(
        all(
            row.get("nodeid") in depth_by_nodeid
            and row.get("level") == depth_by_nodeid[row["nodeid"]].get("system_reach")
            and row.get("boundary") == depth_by_nodeid[row["nodeid"]].get("boundary_mode")
            and row.get("representation") == depth_by_nodeid[row["nodeid"]].get("representation_fidelity")
            and row.get("ms_validation") == depth_by_nodeid[row["nodeid"]].get("ms_validation")
            for row in all_monitor_paths
        ),
        "Requirement Monitor Actual is projected only from matching current Depth rows, never reconstructed from Target",
    )
    check(
        all(
            row.get("provenance") == "COMPLETE"
            and row.get("producer_qualification") == "QUALIFIED"
            and row.get("freshness") == "CURRENT"
            for row in all_monitor_paths
        ),
        "all retained Contract Evidence paths are full-chain complete, qualified and current",
    )

    tool_choice = (monitor_facts.get("contracts") or {}).get("REQ_TOOL_CHOICE") or {}
    tool_choice_targets = {
        (row.get("level"), row.get("boundary")): row
        for row in (tool_choice.get("target") or {}).get("coverage") or []
    }
    tool_choice_actual = tool_choice.get("coverage_actual") or {}
    named_forms = tool_choice_actual.get("VC_TOOL_CHOICE_NAMED_INPUT_FORMS") or []
    named_serializers = tool_choice_actual.get("VC_TOOL_CHOICE_NAMED_SERIALIZERS") or []
    replay_choice = tool_choice_actual.get("VC_TOOL_CHOICE_REPLAY_FAMILIES") or []
    local_choice = tool_choice_actual.get("VC_TOOL_CHOICE_GOOGLE_GENAI") or []
    check(
        tool_choice_targets.get(("component", "none"), {}).get("item_path_counts")
            == {
                "VC_TOOL_CHOICE_NAMED_INPUT_FORMS": 2,
                "VC_TOOL_CHOICE_NAMED_SERIALIZERS": 4,
            }
        and tool_choice_targets.get(("system_integration", "replay"), {}).get("item_path_counts")
            == {"VC_TOOL_CHOICE_REPLAY_FAMILIES": 4}
        and tool_choice_targets.get(("system_integration", "substitute"), {}).get("item_path_counts")
            == {"VC_TOOL_CHOICE_GOOGLE_GENAI": 1}
        and len(named_forms) == 2
        and len(named_serializers) == 4
        and len(replay_choice) == 4
        and len(local_choice) == 1,
        "Tool Choice preserves independent public-input, provider-serializer and provider-family denominators without last-test-wins collapse",
    )
    check(
        all(
            row.get("result") == "passed"
            and row.get("level") == "component"
            and row.get("boundary") == "none"
            and row.get("representation") == "actual"
            for row in [*named_forms, *named_serializers]
        )
        and all(
            row.get("result") == "passed"
            and row.get("level") == "system_integration"
            and row.get("boundary") == "replay"
            and row.get("representation") == "surrogate_simulated"
            and str(row.get("ms_validation")).lower() == "l0"
            and "PRODUCER_VCR" in (row.get("producer_ids") or [])
            for row in replay_choice
        )
        and all(
            row.get("result") == "passed"
            and row.get("level") == "system_integration"
            and row.get("boundary") == "substitute"
            and row.get("representation") == "surrogate_simulated"
            and str(row.get("ms_validation")).lower() == "l0"
            and "PRODUCER_SCRIPTED_HTTP_SERVER" in (row.get("producer_ids") or [])
            for row in local_choice
        ),
        "Tool Choice Actual distinguishes Replay/VCR from Substitute/ScriptedHTTP without representation inflation",
    )

    tool_multi = (monitor_facts.get("contracts") or {}).get("REQ_MULTI_ROUND_TOOL_EXECUTION") or {}
    tool_multi_targets = {
        (row.get("level"), row.get("boundary")): row
        for row in (tool_multi.get("target") or {}).get("coverage") or []
    }
    tool_multi_actual = tool_multi.get("coverage_actual") or {}
    replay_multi = tool_multi_actual.get("VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES") or []
    local_multi = tool_multi_actual.get("VC_TOOL_MULTI_ROUND_OPENAI_LOCAL") or []
    check(
        set(tool_multi_targets) == {
            ("system_integration", "replay"),
            ("system_integration", "substitute"),
        }
        and tool_multi_targets[("system_integration", "replay")].get("item_path_counts")
            == {"VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES": 4}
        and tool_multi_targets[("system_integration", "substitute")].get("item_path_counts")
            == {"VC_TOOL_MULTI_ROUND_OPENAI_LOCAL": 1}
        and (tool_multi.get("target") or {}).get("required_treqs")
            == ["TREQ_TOOL_REGISTRY"]
        and set(tool_multi_actual)
            == {"VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES", "VC_TOOL_MULTI_ROUND_OPENAI_LOCAL"}
        and len(replay_multi) == 4
        and len(local_multi) == 1,
        "Multi-round parent owns only provider-facing workflow criteria and delegates registry proof to TREQ_TOOL_REGISTRY",
    )
    check(
        all(
            row.get("boundary") == "replay"
            and row.get("representation") == "surrogate_simulated"
            and str(row.get("ms_validation")).lower() == "l0"
            and "PRODUCER_VCR" in (row.get("producer_ids") or [])
            for row in replay_multi
        )
        and all(
            row.get("boundary") == "substitute"
            and row.get("representation") == "surrogate_simulated"
            and str(row.get("ms_validation")).lower() == "l0"
            and "PRODUCER_SCRIPTED_HTTP_SERVER" in (row.get("producer_ids") or [])
            for row in local_multi
        ),
        "Multi-round Actual keeps Replay and Substitute evidence as distinct same-path classifications",
    )

    tool_registry = (monitor_facts.get("contracts") or {}).get("TREQ_TOOL_REGISTRY") or {}
    registry_targets = {
        (row.get("level"), row.get("boundary")): row
        for row in (tool_registry.get("target") or {}).get("coverage") or []
    }
    registry_actual = tool_registry.get("coverage_actual") or {}
    check(
        registry_targets.get(("component", "none"), {}).get("item_path_counts")
            == {
                "VC_TOOL_REGISTRY_CALL_SHAPES": 2,
                "VC_TOOL_REGISTRY_DUPLICATE_REJECTION": 1,
                "VC_TOOL_REGISTRY_SCHEMA_EXECUTION": 1,
            }
        and set(registry_actual)
            == {
                "VC_TOOL_REGISTRY_CALL_SHAPES",
                "VC_TOOL_REGISTRY_DUPLICATE_REJECTION",
                "VC_TOOL_REGISTRY_SCHEMA_EXECUTION",
            }
        and len(registry_actual["VC_TOOL_REGISTRY_CALL_SHAPES"]) == 2
        and len(registry_actual["VC_TOOL_REGISTRY_DUPLICATE_REJECTION"]) == 1
        and len(registry_actual["VC_TOOL_REGISTRY_SCHEMA_EXECUTION"]) == 1
        and all(
            row.get("level") == "component"
            and row.get("boundary") == "none"
            and row.get("representation") == "actual"
            for rows in registry_actual.values()
            for row in rows
        ),
        "TREQ_TOOL_REGISTRY owns the exact 1/1/2 local registry denominator as first-class Contract Evidence",
    )

    tool_runtime = (monitor_facts.get("contracts") or {}).get("REQ_TOOL_RUNTIME_SAFETY") or {}
    runtime_actual = tool_runtime.get("coverage_actual") or {}
    runtime_paths = [
        row for rows in runtime_actual.values() for row in rows
    ]
    check(
        set(runtime_actual) == {
            "VC_TOOL_RUNTIME_PUBLIC_ERROR",
            "VC_TOOL_RUNTIME_ROUND_LIMIT",
        }
        and len(runtime_paths) == 2
        and all(
            row.get("level") == "system_integration"
            and row.get("boundary") == "substitute"
            and row.get("representation") == "surrogate_simulated"
            and str(row.get("ms_validation")).lower() == "l0"
            and "PRODUCER_SCRIPTED_HTTP_SERVER" in (row.get("producer_ids") or [])
            for row in runtime_paths
        ),
        "Tool Runtime Safety retains both required System-integration Substitute/Surrogate/L0 paths",
    )

    check(all(token in readiness for token in (
        "P34 MONITOR CUTOVER COMPLETE",
        "Parent `REQ_INVALID_CONFIGURATION_ERRORS`: 1 System criterion / 1 retained path",
        "13/13 Component criteria · 16/16 paths",
        "missing child-specific challenges remain red instead of inheriting the parent mutation/fault campaign",
        "compatibility-only `.ai-bridge/assurance-targets.json`",
        "Test Coverage → Fault-based Testing → History",
    )), "monitor readiness ledger records the completed P34 target/actual cutover and first-class Configuration ownership")
    check("Test plan" in test_plan_html and "Reusable Test Models" in test_plan_html,
          "generated Test Plan page renders the project-wide strategy")

    adapter = campaign.get("adapter") or {}
    check(
        adapter.get("version") == "p34-local-2",
        "retained mutation campaign uses the current p34-local-2 adapter provenance",
    )
    check(adapter.get("mutation_semantics_version") == "p21-local-2",
          "mutation semantics compatibility version remains explicit")
    check(
        campaign.get("mode") in {"full", "diff"},
        "retained pilot campaign uses a supported full/diff mode",
    )
    check(bool(campaign.get("run_id")), "retained pilot campaign has unique run_id")
    check(bool(campaign.get("baseline_run_id")), "retained pilot campaign has baseline_run_id")
    check(campaign.get("run_id") != campaign.get("baseline_run_id"), "run_id is not self-baseline")
    check(bool(campaign.get("finished_at")), "retained pilot campaign finished")
    check(float(campaign.get("duration_seconds") or 0) > 0, "retained pilot campaign has runtime")

    history_runs = [
        load(path)
        for path in sorted((RESULTS / "campaign-history").glob("*.json"))
    ]
    retained_runs = [*history_runs, campaign]
    retained_runs_by_id = {
        row.get("run_id"): row for row in retained_runs if row.get("run_id")
    }
    measured_ids = {"REQ_INVALID_CONFIGURATION_ERRORS", "TREQ_TOOL_REGISTRY"}
    check(
        any(
            row.get("mode") == "full"
            and set(row.get("selected_contracts") or []) == measured_ids
            and bool(row.get("finished_at"))
            for row in retained_runs
        ),
        "retained mutation history contains a completed full baseline for every uniquely attributable contract",
    )
    if campaign.get("mode") == "diff":
        selected = set(campaign.get("selected_contracts") or [])
        skipped = set(campaign.get("skipped_contracts") or [])
        scope_resolution = campaign.get("scope_resolution") or {}
        check(
            bool(selected)
            and selected <= measured_ids
            and skipped == measured_ids - selected,
            "latest diff campaign selects only changed uniquely attributable contracts and skips the rest",
        )
        check(
            bool(campaign.get("base_sha"))
            and all(
                (scope_resolution.get(contract_id) or {}).get("selected") is True
                and bool((scope_resolution.get(contract_id) or {}).get("reasons"))
                for contract_id in selected
            ),
            "latest diff campaign retains its base SHA and objective change-selection reasons",
        )

    check(
        summary.get("total_contracts") == 63,
        "63 contracts are present in the verification-depth / mutation measurement universe",
    )
    check(
        summary.get("measured_contracts") == 2,
        "exactly 2 uniquely attributable contracts are measured",
    )
    check(summary.get("fresh_measured_contracts") == 2, "all measured contracts are fresh")
    check(summary.get("stale_measured_contracts") == 0, "no measured contract is stale")
    check(summary.get("new_unresolved_survivors") == 0, "current campaign introduces no new unresolved survivors")
    check(summary.get("resolved_survivors") == 0, "current comparable content reports no fabricated survivor resolution")
    check(summary.get("unresolved_survivors") == 29, "current measured mutation debt remains explicit")
    check(summary.get("suppressed_survivors") == 0, "no acceptance suppression remains")
    check(summary.get("readiness") == "clear", "mutation readiness is clear when no new unresolved survivor exists")

    suppression_path = BRIDGE / "mutation-suppressions.json"
    if suppression_path.exists():
        suppressions = load(suppression_path).get("suppressions") or []
        check(not suppressions, "suppression ledger contains no acceptance-only suppression")
    else:
        check(True, "no suppression ledger remains in current clean pilot state")

    strength_contracts = strength.get("contracts") or {}
    check(
        set(strength_contracts) == measured_ids,
        "retained Test Strength facts contain only the two uniquely attributable pilot contracts",
    )
    measured = {}
    for contract_id, strength_row in strength_contracts.items():
        owner_run = retained_runs_by_id.get(strength_row.get("run_id"))
        check(
            owner_run is not None,
            f"{contract_id}: retained Test Strength run_id resolves to a retained campaign",
        )
        owner_contract = (owner_run.get("contracts") or {}).get(contract_id)
        check(
            owner_contract is not None,
            f"{contract_id}: retained owner campaign contains the measured contract",
        )
        measured[contract_id] = owner_contract

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
        check(
            contract_triage.get("baseline_comparable") is True,
            f"{contract_id}: current campaign remains comparable with the immediately previous compatible baseline",
        )
        check(
            contract_triage.get("score_delta") == 0.0,
            f"{contract_id}: comparable campaign retains the unchanged mutation score without fabricated movement",
        )
        check(
            contract_triage.get("new_unresolved_survivors") == 0
            and contract_triage.get("resolved_survivors") == 0
            and contract_triage.get("existing_survivors") == survived,
            f"{contract_id}: survivor identities are retained without fabricated new/resolved changes",
        )

    unattributed = strength.get("unattributed") or []
    check(
        {row.get("contract_id") for row in unattributed}
        == {"REQ_ROUTE_ATTEMPT_LIMIT", "REQ_CONFIG_INSTALLATION_COHERENCE"},
        "shared implementation scopes remain diagnostic-only and explicitly unattributed",
    )
    shared_reasons = {
        row.get("contract_id"): str(row.get("reason") or "")
        for row in unattributed
    }
    check(
        "TREQ_ROUTE_ORDER" in shared_reasons["REQ_ROUTE_ATTEMPT_LIMIT"]
        and "TREQ_CONFIG_CACHE_INVALIDATION"
        in shared_reasons["REQ_CONFIG_INSTALLATION_COHERENCE"],
        "shared-scope diagnostics name the contracts that prevent unique attribution",
    )
    check(
        not (
            {"REQ_ROUTE_ATTEMPT_LIMIT", "REQ_CONFIG_INSTALLATION_COHERENCE", "TREQ_RATE_LIMIT_STATE"}
            & set(strength.get("contracts") or {})
        ),
        "shared-scope and retired limiter diagnostics do not leak into measured Requirement/TREQ strength facts",
    )

    filtering = feedback.get("filtering_decision") or {}
    check(filtering.get("decision") == "none", "P23 makes no operator filtering decision")
    check(filtering.get("full_audit_preserved") is True, "full audit mode preserved")
    check(filtering.get("diff_mode_filtering_enabled") is False, "diff operator filtering remains disabled")
    check((feedback.get("sample") or {}).get("directly_timed_contract_runs", 0) >= 3,
          "operator feedback includes directly timed contract runs")
    check(len(feedback.get("families") or []) >= 1, "operator feedback has retained diagnostic families")

    mutation_page = (HTML / "mutation-analysis.html").read_text()
    evidence_trust_page = (HTML / "evidence-trust.html").read_text()
    assurance_page = (HTML / "verification-assurance.html").read_text()
    override_page = (HTML / "contract-evidence-request-override-precedence.html").read_text()
    credential_page = (HTML / "contract-evidence-credential-resolution.html").read_text()
    install_page = (HTML / "contract-evidence-config-installation-coherence.html").read_text()
    config_treq_pages = {
        "TREQ_CONFIG_CACHE_INVALIDATION": (HTML / "contract-evidence-config-cache-invalidation.html").read_text(),
        "TREQ_CONFIG_PROVIDER_IDENTITY": (HTML / "contract-evidence-config-provider-identity.html").read_text(),
        "TREQ_CONFIG_MODEL_DECLARATION": (HTML / "contract-evidence-config-model-declaration.html").read_text(),
        "TREQ_CONFIG_REQUIRED_BASE_URL": (HTML / "contract-evidence-config-required-base-url.html").read_text(),
        "TREQ_CONFIG_ATTEMPT_TIMEOUT": (HTML / "contract-evidence-config-attempt-timeout.html").read_text(),
        "TREQ_CONFIG_RETRY_ATTEMPTS": (HTML / "contract-evidence-config-retry-attempts.html").read_text(),
        "TREQ_CONFIG_RETRY_WAIT_BOUNDS": (HTML / "contract-evidence-config-retry-wait-bounds.html").read_text(),
        "TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT": (HTML / "contract-evidence-config-route-attempt-limit.html").read_text(),
        "TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES": (HTML / "contract-evidence-config-fallback-shuffle-min-routes.html").read_text(),
        "TREQ_CONFIG_TOOL_ROUND_LIMIT": (HTML / "contract-evidence-config-tool-round-limit.html").read_text(),
        "TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS": (HTML / "contract-evidence-config-structured-output-attempts.html").read_text(),
        "TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION": (HTML / "contract-evidence-config-default-provider-declaration.html").read_text(),
        "TREQ_CONFIG_DEFAULT_MODEL_MAPPING": (HTML / "contract-evidence-config-default-model-mapping.html").read_text(),
        "TREQ_CONFIG_MODEL_PROVIDER_REFERENCES": (HTML / "contract-evidence-config-model-provider-references.html").read_text(),
    }
    tool_choice_page = (HTML / "contract-evidence-tool-choice.html").read_text()
    tool_multi_page = (HTML / "contract-evidence-multi-round-tool-execution.html").read_text()
    tool_runtime_page = (HTML / "contract-evidence-tool-runtime-safety.html").read_text()
    tool_registry_page = (HTML / "contract-evidence-tool-registry.html").read_text()
    sync_route_page = (HTML / "contract-evidence-sync-route-fallback.html").read_text()
    timeout_route_page = (HTML / "contract-evidence-route-timeout-fallback.html").read_text()
    attempt_limit_page = (HTML / "contract-evidence-route-attempt-limit.html").read_text()
    sticky_route_page = (HTML / "contract-evidence-route-sticky-start.html").read_text()
    route_order_page = (HTML / "contract-evidence-route-order.html").read_text()
    rate_limit_page = (HTML / "contract-evidence-rate-limit-routing.html").read_text()
    provider_retry_page = (HTML / "contract-evidence-provider-retry.html").read_text()
    provider_retry_classification_page = (
        HTML / "contract-evidence-provider-retry-classification.html"
    ).read_text()
    provider_retry_bounds_page = (
        HTML / "contract-evidence-provider-retry-bounds.html"
    ).read_text()
    structured_repair_page = (HTML / "contract-evidence-structured-output-repair.html").read_text()
    structured_attempt_bounds_page = (
        HTML / "contract-evidence-structured-output-attempt-bounds.html"
    ).read_text()
    repair_prompt_bounds_page = (
        HTML / "contract-evidence-repair-prompt-bounds.html"
    ).read_text()
    security_page = (HTML / "contract-evidence-sensitive-data-protection.html").read_text()
    runtime_log_safety_page = (HTML / "contract-evidence-runtime-log-safety.html").read_text()
    vcr_auth_redaction_page = (HTML / "contract-evidence-vcr-auth-redaction.html").read_text()
    vcr_request_redaction_page = (HTML / "contract-evidence-vcr-request-content-redaction.html").read_text()
    vcr_response_redaction_page = (HTML / "contract-evidence-vcr-response-content-redaction.html").read_text()
    provider_adapter_page = (HTML / "contract-evidence-provider-adapter-interoperability.html").read_text()
    openai_adapter_page = (HTML / "contract-evidence-openai-adapter-boundary.html").read_text()
    qwenchat_adapter_page = (HTML / "contract-evidence-qwenchat-adapter-boundary.html").read_text()
    aistudio_adapter_page = (HTML / "contract-evidence-aistudio-adapter-boundary.html").read_text()
    gemini_webapi_adapter_page = (HTML / "contract-evidence-gemini-webapi-adapter-boundary.html").read_text()
    google_genai_adapter_page = (HTML / "contract-evidence-google-genai-adapter-boundary.html").read_text()
    async_provider_page = (HTML / "contract-evidence-async-provider-execution.html").read_text()
    response_normalization_page = (HTML / "contract-evidence-response-normalization.html").read_text()
    usage_normalization_page = (HTML / "contract-evidence-usage-normalization.html").read_text()
    provider_error_page = (HTML / "contract-evidence-provider-error-boundary.html").read_text()
    session_lifecycle_page = (HTML / "contract-evidence-session-lifecycle.html").read_text()
    session_persistence_page = (HTML / "contract-evidence-session-persistence.html").read_text()
    session_serialization_page = (HTML / "contract-evidence-session-serialization.html").read_text()
    public_api_page = (HTML / "contract-evidence-public-api-surface.html").read_text()
    example_import_page = (HTML / "contract-evidence-example-import-safety.html").read_text()
    structured_text_page = (HTML / "contract-evidence-structured-text-output.html").read_text()
    document_input_page = (HTML / "contract-evidence-document-input.html").read_text()
    image_input_page = (HTML / "contract-evidence-image-input.html").read_text()
    video_input_page = (HTML / "contract-evidence-video-input.html").read_text()
    structured_schema_page = (HTML / "contract-evidence-structured-schema-contract.html").read_text()
    content_normalization_page = (HTML / "contract-evidence-multimodal-content-normalization.html").read_text()
    upper_assurance_pages = {
        "Feature fallback": (HTML / "assurance-feat-route-fallback.html").read_text(),
        "Feature rate limit": (HTML / "assurance-feat-rate-limit-routing.html").read_text(),
        "Goal routing": (HTML / "assurance-goal-routing-reliability.html").read_text(),
        "Feature public API": (HTML / "assurance-feat-public-api.html").read_text(),
        "Feature examples": (HTML / "assurance-feat-executable-examples.html").read_text(),
        "Goal developer": (HTML / "assurance-goal-developer-usability.html").read_text(),
        "Feature sessions": (HTML / "assurance-feat-session-lifecycle.html").read_text(),
        "Goal sessions": (HTML / "assurance-goal-session-continuity.html").read_text(),
        "Feature data safety": (HTML / "assurance-feat-sensitive-data-protection.html").read_text(),
        "Goal data safety": (HTML / "assurance-goal-data-safety.html").read_text(),
        "Feature tool selection": (HTML / "assurance-feat-tool-selection.html").read_text(),
        "Feature tool execution": (HTML / "assurance-feat-tool-execution.html").read_text(),
        "Goal tools": (HTML / "assurance-goal-tool-orchestration.html").read_text(),
        "Feature provider retry": (HTML / "assurance-feat-provider-retry.html").read_text(),
        "Feature structured recovery": (HTML / "assurance-feat-structured-recovery.html").read_text(),
        "Goal resilience": (HTML / "assurance-goal-resilient-execution.html").read_text(),
        "Feature provider interoperability": (HTML / "assurance-feat-provider-interoperability.html").read_text(),
        "Feature async execution": (HTML / "assurance-feat-async-execution.html").read_text(),
        "Feature public response": (HTML / "assurance-feat-public-response-contract.html").read_text(),
        "Goal provider portability": (HTML / "assurance-goal-provider-portability.html").read_text(),
        "Feature configuration": (HTML / "assurance-feat-configuration-precedence.html").read_text(),
        "Goal configuration": (HTML / "assurance-goal-configuration-predictability.html").read_text(),
        "Feature rich output": (HTML / "assurance-feat-structured-output.html").read_text(),
        "Goal rich output": (HTML / "assurance-goal-rich-input-output.html").read_text(),
        "Product / System": (HTML / "assurance-product-system.html").read_text(),
    }
    health_page = (HTML / "verification-health-map.html").read_text()
    # The map itself: health and, beside it, the measures of the retired Verification Depth Map (MAP-P41).
    health_section = health_page.split('<section id="verification-health-map">', 1)[-1].split("</section>", 1)[0]
    trace_reader_page = (HTML / "traceability-reader.html").read_text()
    verification_page = (HTML / "verification.html").read_text()

    canonical_monitor_style = re.search(
        r'<style id="tf-requirement-monitor-style">(.*?)</style>',
        sticky_route_page,
        flags=re.DOTALL,
    )
    check(
        canonical_monitor_style is not None,
        "canonical REQ Contract Evidence page exposes the shared monitor style",
    )
    canonical_style_text = canonical_monitor_style.group(1) if canonical_monitor_style else ""
    domain_source = (BRIDGE / "assurance_monitor_domain.py").read_text()
    registry_source = (BRIDGE / "assurance_monitor_registry.py").read_text()
    ui_source = (BRIDGE / "assurance_monitor_ui.py").read_text()
    requirement_renderer_source = (BRIDGE / "build-requirement-monitor.py").read_text()
    upper_renderer_source = (BRIDGE / "build-upper-assurance-pilot.py").read_text()
    assurance_adapter_source = (BRIDGE / "build-mutation-report-prototype.py").read_text()
    check(
        all(
            token in domain_source
            for token in (
                "def combine(",
                "def cell_state(",
                "def fault_state(",
                "def contract_domain_state(",
                "PRODUCER =",
                "FRESHNESS =",
                "REPRESENTATION =",
                "PROVENANCE =",
                "MS_LEVELS =",
            )
        ),
        "shared assurance domain owns status algebra, vocabularies, and contract-state projection",
    )
    check(
        all(
            token in registry_source
            for token in (
                "PAGE_SPECS = (",
                "def contract_slug(",
                "def monitor_urls(",
                "def normalize_needs_graph(",
                "def navigation_spec(",
                "Product / System",
            )
        ),
        "shared assurance registry owns monitor page declarations, URLs, and hierarchy projection",
    )
    check(
        "PRODUCER =" not in ui_source
        and "FRESHNESS =" not in ui_source
        and "REPRESENTATION =" not in ui_source
        and "PROVENANCE =" not in ui_source
        and "MS_LEVELS =" not in ui_source,
        "shared monitor UI is presentation-only and does not own assurance semantics",
    )
    check(
        "MONITOR_STYLE =" in ui_source
        and "function syncSticky" in ui_source
        and "function flashTarget" in ui_source
        and "def coverage_card(" in ui_source
        and "def lane(" in ui_source
        and "def technical_support_card(" in ui_source
        and "def domain_card(" in ui_source
        and "def history_section(" in ui_source
        and "def inspector_head(" in ui_source
        and "def signal_group(" in ui_source
        and "def confidence_subgroup(" in ui_source
        and "def drilldowns(" in ui_source
        and "def section_head(" in ui_source
        and "def verdict_header(" in ui_source
        and "def support_panel(" in ui_source
        and "def metric_tile(" in ui_source
        and "def assurance_navigation(" in ui_source
        and "ASSURANCE_NAV_STYLE =" in ui_source
        and "def render_monitor_shell(" in ui_source,
        "shared assurance monitor UI owns canonical CSS, behavior, and reusable components",
    )
    check(
        all(
            token not in source
            for source in (requirement_renderer_source, upper_renderer_source)
            for token in (
                "#tf-requirement-monitor",
                "function syncSticky",
                "function flashTarget",
                "def coverage_card(",
                "def lane(",
                'class="inspector-head"',
                'class="signal-group ',
                'class="drilldowns"',
                'class="section-head"',
                'class="verdict"',
                "technical-support-panel",
                "pst-secondary-sidebar",
                "breadcrumb-item active",
                '<article class="bd-article">',
                "tf-requirement-monitor-style",
            )
        )
        and "ui.render_monitor_shell(" in requirement_renderer_source
        and "ui.render_monitor_shell(" in upper_renderer_source
        and "ui.monitor_script(" in requirement_renderer_source
        and "ui.monitor_script(" in upper_renderer_source
        and "ui.inspector_head(" in requirement_renderer_source
        and "ui.inspector_head(" in upper_renderer_source
        and "ui.section_head(" in requirement_renderer_source
        and "ui.section_head(" in upper_renderer_source
        and "ui.verdict_header(" in requirement_renderer_source
        and "ui.verdict_header(" in upper_renderer_source
        and "ui.metric_tile(" in requirement_renderer_source
        and "ui.metric_tile(" in upper_renderer_source
        and "ui.na_fault_tile(" in requirement_renderer_source
        and "ui.na_fault_tile(" in upper_renderer_source
        and 'SHELL = OUT_DIR / "verification-assurance.html"' in upper_renderer_source
        and "contract-evidence-route-sticky-start.html" not in upper_renderer_source,
        "REQ/TREQ and upper renderers consume one shared monitor design system and canonical shell",
    )
    check(
        all(
            token not in source
            for source in (requirement_renderer_source, upper_renderer_source)
            for token in (
                "def combine(",
                "def cell_state(",
                "def fault_state(",
                "def contract_domain_state(",
                "def contract_slug(",
                "def navigation_spec(",
                "def assurance_navigation(",
            )
        )
        and "assurance_monitor_domain.py" in requirement_renderer_source
        and "assurance_monitor_domain.py" in upper_renderer_source
        and "domain.contract_domain_state(" in upper_renderer_source
        and "assurance_monitor_registry.py" in requirement_renderer_source
        and "assurance_monitor_registry.py" in upper_renderer_source
        and "registry.navigation_spec(" in requirement_renderer_source
        and "registry.navigation_spec(" in upper_renderer_source
        and "ui.assurance_navigation(" in requirement_renderer_source
        and "ui.assurance_navigation(" in upper_renderer_source
        and "build-requirement-monitor.py" not in upper_renderer_source
        and "reqmon." not in upper_renderer_source,
        "REQ/TREQ and upper renderers share domain semantics without importing one another",
    )
    check(
        "tf-p34-" not in assurance_adapter_source
        and "tf-contract-shell" not in assurance_adapter_source
        and "TERNFORGE-P33-ASSURANCE-EVIDENCE-START" not in assurance_adapter_source
        and "requirement_monitor_block(" not in assurance_adapter_source,
        "superseded parallel Contract Evidence renderers are absent from the active evidence builder",
    )
    check(
        "def metric(" not in requirement_renderer_source
        and "metric-card" not in requirement_renderer_source
        and "STATUS_ORDER" not in upper_renderer_source,
        "dead presentation helpers are removed from active monitor renderers",
    )
    check(
        "PAGE_SPECS = (" in registry_source
        and "FEATURE_SECTION_LABELS = (" in registry_source
        and "profile_source: str" in registry_source
        and "profile_url: str" in registry_source
        and "docs/assurance-profiles/developer.md" in registry_source
        and "docs/assurance-profiles/product-system.md" in registry_source
        and "PAGE_SPECS = registry.PAGE_SPECS" in upper_renderer_source
        and "def parse_profiles(" in upper_renderer_source
        and "for spec in PAGE_SPECS:" in upper_renderer_source
        and upper_renderer_source.count("render_page(") == 2
        and 'PROFILE = ROOT / "docs/assurance-profiles/routing.md"' not in upper_renderer_source
        and 'for feature_id in ("FEAT_' not in upper_renderer_source
        and 'goal_id = "GOAL_' not in upper_renderer_source
        and '"schema": "ternforge-upper-assurance-pilot-2"' in upper_renderer_source
        and '"profiles": profile_capture_facts(run_inputs)' in upper_renderer_source
        and '"goals": goals' in upper_renderer_source,
        "upper assurance onboarding, profiles, navigation, and pages are driven by one declarative registry",
    )
    check(
        "<title>Technical Assurance &#8212; llm-router" in route_order_page
        and '<span class="ellipsis">Technical Assurance</span>' in route_order_page,
        "TREQ monitor shell exposes Technical Assurance consistently in title and breadcrumb",
    )
    hierarchy_nav_pages = {
        "Product / System": upper_assurance_pages["Product / System"],
        "Goal routing": upper_assurance_pages["Goal routing"],
        "Goal developer": upper_assurance_pages["Goal developer"],
        "Goal sessions": upper_assurance_pages["Goal sessions"],
        "Goal data safety": upper_assurance_pages["Goal data safety"],
        "Goal tools": upper_assurance_pages["Goal tools"],
        "Goal resilience": upper_assurance_pages["Goal resilience"],
        "Goal provider portability": upper_assurance_pages["Goal provider portability"],
        "Goal configuration": upper_assurance_pages["Goal configuration"],
        "Feature configuration": upper_assurance_pages["Feature configuration"],
        "Goal rich output": upper_assurance_pages["Goal rich output"],
        "Feature rich output": upper_assurance_pages["Feature rich output"],
        "Feature sessions": upper_assurance_pages["Feature sessions"],
        "Feature data safety": upper_assurance_pages["Feature data safety"],
        "Feature tool selection": upper_assurance_pages["Feature tool selection"],
        "Feature tool execution": upper_assurance_pages["Feature tool execution"],
        "Feature provider retry": upper_assurance_pages["Feature provider retry"],
        "Feature structured recovery": upper_assurance_pages["Feature structured recovery"],
        "Feature provider interoperability": upper_assurance_pages["Feature provider interoperability"],
        "Feature async execution": upper_assurance_pages["Feature async execution"],
        "Feature public response": upper_assurance_pages["Feature public response"],
        "Feature fallback": upper_assurance_pages["Feature fallback"],
        "Feature public API": upper_assurance_pages["Feature public API"],
        "REQ sticky route": sticky_route_page,
        "TREQ route order": route_order_page,
        "REQ rate limit": rate_limit_page,
        "REQ provider retry": provider_retry_page,
        "TREQ provider retry classification": provider_retry_classification_page,
        "TREQ provider retry bounds": provider_retry_bounds_page,
        "REQ structured repair": structured_repair_page,
        "TREQ structured attempt bounds": structured_attempt_bounds_page,
        "TREQ repair prompt bounds": repair_prompt_bounds_page,
        "REQ provider interoperability": provider_adapter_page,
        "TREQ OpenAI adapter": openai_adapter_page,
        "TREQ QwenChat adapter": qwenchat_adapter_page,
        "TREQ AI Studio adapter": aistudio_adapter_page,
        "TREQ Gemini WebAPI adapter": gemini_webapi_adapter_page,
        "TREQ Google GenAI adapter": google_genai_adapter_page,
        "REQ async provider": async_provider_page,
        "REQ response normalization": response_normalization_page,
        "TREQ usage normalization": usage_normalization_page,
        "REQ provider error": provider_error_page,
        "REQ config override": override_page,
        "REQ config invalid": assurance_page,
        "REQ config credential": credential_page,
        "REQ config installation": install_page,
        **{f"Config {contract_id}": page for contract_id, page in config_treq_pages.items()},
        "REQ session persistence": session_persistence_page,
        "TREQ session serialization": session_serialization_page,
        "REQ data safety": security_page,
        "TREQ runtime log safety": runtime_log_safety_page,
        "TREQ VCR auth": vcr_auth_redaction_page,
        "TREQ VCR request": vcr_request_redaction_page,
        "TREQ VCR response": vcr_response_redaction_page,
        "REQ tool choice": tool_choice_page,
        "REQ tool multi-round": tool_multi_page,
        "TREQ tool registry": tool_registry_page,
        "REQ tool runtime": tool_runtime_page,
    }
    for name, page in hierarchy_nav_pages.items():
        nav = re.search(
            r'<nav class="tf-assurance-nav".*?</nav>',
            page,
            flags=re.DOTALL,
        )
        nav_text = nav.group(0) if nav else ""
        check(
            nav is not None
            and page.count('class="tf-assurance-nav"') == 1
            and nav.start() < page.index('<div id="tf-requirement-monitor">')
            and nav_text.count('aria-current="page"') == 1,
            f"{name}: hierarchy navigation is a single surface separate from the monitor",
        )
        check(
            all(token not in nav_text for token in ("PASS", "FAIL", "UNKNOWN", "N/A")),
            f"{name}: hierarchy navigation contains navigation only, without assurance status",
        )
    check(
        "<span>Goals</span><b>9</b>" in upper_assurance_pages["Product / System"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-routing-reliability.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-developer-usability.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-session-continuity.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-data-safety.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-tool-orchestration.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-resilient-execution.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-provider-portability.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-configuration-predictability.html"' in upper_assurance_pages["Product / System"]
        and 'href="assurance-goal-rich-input-output.html"' in upper_assurance_pages["Product / System"],
        "Product / System navigation exposes all nine onboarded Goals through one compact dropdown",
    )
    check(
        "<span>Capabilities</span><b>2</b>" in upper_assurance_pages["Goal routing"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Goal routing"]
        and 'href="assurance-feat-route-fallback.html"' in upper_assurance_pages["Goal routing"]
        and 'href="assurance-feat-rate-limit-routing.html"' in upper_assurance_pages["Goal routing"],
        "Goal navigation exposes both monitored capabilities through one compact dropdown",
    )
    check(
        "<span>Capabilities</span><b>2</b>" in upper_assurance_pages["Goal developer"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Goal developer"]
        and 'href="assurance-feat-public-api.html"' in upper_assurance_pages["Goal developer"]
        and 'href="assurance-feat-executable-examples.html"' in upper_assurance_pages["Goal developer"],
        "Developer Goal navigation exposes both monitored capabilities through the shared dropdown",
    )
    check(
        "<span>Capabilities</span><b>1</b>" in upper_assurance_pages["Goal sessions"]
        and 'href="assurance-feat-session-lifecycle.html"' in upper_assurance_pages["Goal sessions"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Goal sessions"],
        "Session Goal navigation uses one direct next-level link for its single capability",
    )
    check(
        "<span>Capabilities</span><b>1</b>" in upper_assurance_pages["Goal data safety"]
        and 'href="assurance-feat-sensitive-data-protection.html"' in upper_assurance_pages["Goal data safety"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Goal data safety"],
        "Data Safety Goal navigation uses one direct next-level link for its single capability",
    )
    check(
        "<span>Capabilities</span><b>2</b>" in upper_assurance_pages["Goal tools"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Goal tools"]
        and 'href="assurance-feat-tool-selection.html"' in upper_assurance_pages["Goal tools"]
        and 'href="assurance-feat-tool-execution.html"' in upper_assurance_pages["Goal tools"],
        "Tool Orchestration Goal navigation exposes both capabilities through the shared dropdown",
    )
    check(
        "<span>Capabilities</span><b>2</b>" in upper_assurance_pages["Goal resilience"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Goal resilience"]
        and 'href="assurance-feat-provider-retry.html"' in upper_assurance_pages["Goal resilience"]
        and 'href="assurance-feat-structured-recovery.html"' in upper_assurance_pages["Goal resilience"],
        "Resilient Execution Goal navigation exposes both capabilities through the shared dropdown",
    )
    check(
        "<span>Capabilities</span><b>3</b>" in upper_assurance_pages["Goal provider portability"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Goal provider portability"]
        and 'href="assurance-feat-provider-interoperability.html"' in upper_assurance_pages["Goal provider portability"]
        and 'href="assurance-feat-async-execution.html"' in upper_assurance_pages["Goal provider portability"]
        and 'href="assurance-feat-public-response-contract.html"' in upper_assurance_pages["Goal provider portability"],
        "Provider Portability Goal navigation exposes all three capabilities through the shared dropdown",
    )
    check(
        "<span>Capabilities</span><b>1</b>" in upper_assurance_pages["Goal configuration"]
        and 'href="assurance-feat-configuration-precedence.html"' in upper_assurance_pages["Goal configuration"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Goal configuration"],
        "Configuration Goal navigation uses one direct next-level link for its single capability",
    )
    check(
        "<span>Capabilities</span><b>1</b>" in upper_assurance_pages["Goal rich output"]
        and 'href="assurance-feat-structured-output.html"' in upper_assurance_pages["Goal rich output"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Goal rich output"],
        "Rich input/output Goal navigation uses one direct next-level link for its single capability",
    )
    check(
        "<span>Requirements</span><b>6</b>" in upper_assurance_pages["Feature rich output"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-structured-text-output.html"' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-document-input.html"' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-image-input.html"' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-video-input.html"' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-structured-schema-contract.html"' in upper_assurance_pages["Feature rich output"]
        and 'href="contract-evidence-multimodal-content-normalization.html"' in upper_assurance_pages["Feature rich output"],
        "Rich input/output Feature navigation exposes all six direct Requirements",
    )
    check(
        "<span>Requirements</span><b>4</b>" in upper_assurance_pages["Feature configuration"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Feature configuration"]
        and 'href="contract-evidence-request-override-precedence.html"' in upper_assurance_pages["Feature configuration"]
        and 'href="verification-assurance.html"' in upper_assurance_pages["Feature configuration"]
        and 'href="contract-evidence-credential-resolution.html"' in upper_assurance_pages["Feature configuration"]
        and 'href="contract-evidence-config-installation-coherence.html"' in upper_assurance_pages["Feature configuration"],
        "Configuration Feature navigation exposes all four direct Requirements",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature provider interoperability"]
        and 'href="contract-evidence-provider-adapter-interoperability.html"' in upper_assurance_pages["Feature provider interoperability"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature provider interoperability"],
        "Provider Interoperability Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature async execution"]
        and 'href="contract-evidence-async-provider-execution.html"' in upper_assurance_pages["Feature async execution"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature async execution"],
        "Async Execution Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>2</b>" in upper_assurance_pages["Feature public response"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Feature public response"]
        and 'href="contract-evidence-response-normalization.html"' in upper_assurance_pages["Feature public response"]
        and 'href="contract-evidence-provider-error-boundary.html"' in upper_assurance_pages["Feature public response"],
        "Public Response Feature navigation exposes both direct Requirements",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature provider retry"]
        and 'href="contract-evidence-provider-retry.html"' in upper_assurance_pages["Feature provider retry"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature provider retry"],
        "Provider Retry Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature structured recovery"]
        and 'href="contract-evidence-structured-output-repair.html"' in upper_assurance_pages["Feature structured recovery"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature structured recovery"],
        "Structured Recovery Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature tool selection"]
        and 'href="contract-evidence-tool-choice.html"' in upper_assurance_pages["Feature tool selection"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature tool selection"],
        "Tool Selection Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>2</b>" in upper_assurance_pages["Feature tool execution"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Feature tool execution"]
        and 'href="contract-evidence-multi-round-tool-execution.html"' in upper_assurance_pages["Feature tool execution"]
        and 'href="contract-evidence-tool-runtime-safety.html"' in upper_assurance_pages["Feature tool execution"],
        "Tool Execution Feature navigation exposes both direct Requirements",
    )
    check(
        "<span>Requirements</span><b>1</b>" in upper_assurance_pages["Feature data safety"]
        and 'href="contract-evidence-sensitive-data-protection.html"' in upper_assurance_pages["Feature data safety"]
        and '<details class="tf-assurance-next">' not in upper_assurance_pages["Feature data safety"],
        "Data Safety Feature navigation uses one direct Requirement link",
    )
    check(
        "<span>Requirements</span><b>2</b>" in upper_assurance_pages["Feature sessions"]
        and '<details class="tf-assurance-next">' in upper_assurance_pages["Feature sessions"]
        and 'href="contract-evidence-session-lifecycle.html"' in upper_assurance_pages["Feature sessions"]
        and 'href="contract-evidence-session-persistence.html"' in upper_assurance_pages["Feature sessions"],
        "Session Feature navigation exposes both monitored Requirements through one compact dropdown",
    )
    check(
        ">Public API</a>" in upper_assurance_pages["Goal developer"]
        and ">Public API</span>" in upper_assurance_pages["Feature public API"]
        and ">Public API surface</span>" in public_api_page,
        "shared hierarchy labels preserve common acronyms without per-page overrides",
    )
    check(
        "<span>Requirements</span><b>4</b>" in upper_assurance_pages["Feature fallback"]
        and 'href="contract-evidence-route-sticky-start.html"' in upper_assurance_pages["Feature fallback"],
        "Feature navigation exposes monitored Requirements through the shared next-level dropdown",
    )
    check(
        "Product / System" in sticky_route_page
        and "Routing reliability" in sticky_route_page
        and "Route fallback" in sticky_route_page
        and "Route sticky start" in sticky_route_page
        and "<span>Technical support</span><b>1</b>" in sticky_route_page
        and 'href="contract-evidence-route-order.html"' in sticky_route_page,
        "Requirement navigation shows full ancestry and one direct Technical support child",
    )
    check(
        "<span>Technical support</span><b>1</b>" in install_page
        and 'href="contract-evidence-config-cache-invalidation.html"' in install_page,
        "Configuration installation navigation exposes first-class cache invalidation Technical support",
    )
    check(
        "<span>Technical support</span><b>13</b>" in assurance_page
        and '<details class="tf-assurance-next">' in assurance_page
        and 'href="contract-evidence-config-provider-identity.html"' in assurance_page
        and 'href="contract-evidence-config-model-provider-references.html"' in assurance_page,
        "Invalid Configuration navigation exposes all thirteen first-class validation Technical requirements",
    )
    check(
        "<span>Technical support</span><b>5</b>" in provider_adapter_page
        and '<details class="tf-assurance-next">' in provider_adapter_page
        and 'href="contract-evidence-openai-adapter-boundary.html"' in provider_adapter_page
        and 'href="contract-evidence-qwenchat-adapter-boundary.html"' in provider_adapter_page
        and 'href="contract-evidence-aistudio-adapter-boundary.html"' in provider_adapter_page
        and 'href="contract-evidence-gemini-webapi-adapter-boundary.html"' in provider_adapter_page
        and 'href="contract-evidence-google-genai-adapter-boundary.html"' in provider_adapter_page,
        "Provider Interoperability Requirement navigation exposes all five first-class adapter Technical requirements",
    )
    check(
        "<span>Technical support</span><b>1</b>" in response_normalization_page
        and 'href="contract-evidence-usage-normalization.html"' in response_normalization_page,
        "Response Normalization navigation exposes first-class usage-normalization Technical support",
    )
    check(
        "Session continuity" in session_persistence_page
        and "Session lifecycle" in session_persistence_page
        and "<span>Technical support</span><b>1</b>" in session_persistence_page
        and 'href="contract-evidence-session-serialization.html"' in session_persistence_page,
        "Session persistence navigation exposes its first-class serialization Technical requirement",
    )
    check(
        "Data safety" in security_page
        and "Sensitive data protection" in security_page
        and "<span>Technical support</span><b>4</b>" in security_page
        and '<details class="tf-assurance-next">' in security_page
        and 'href="contract-evidence-runtime-log-safety.html"' in security_page
        and 'href="contract-evidence-vcr-auth-redaction.html"' in security_page
        and 'href="contract-evidence-vcr-request-content-redaction.html"' in security_page
        and 'href="contract-evidence-vcr-response-content-redaction.html"' in security_page,
        "Data Safety Requirement navigation exposes all four first-class Technical requirements",
    )
    check(
        "Tool orchestration" in tool_multi_page
        and "Tool execution" in tool_multi_page
        and "<span>Technical support</span><b>1</b>" in tool_multi_page
        and 'href="contract-evidence-tool-registry.html"' in tool_multi_page,
        "Multi-round Tool Requirement navigation exposes first-class Tool Registry technical support",
    )
    session_serialization_nav = re.search(
        r'<nav class="tf-assurance-nav".*?</nav>',
        session_serialization_page,
        flags=re.DOTALL,
    )
    check(
        session_serialization_nav is not None
        and "Session serialization" in session_serialization_nav.group(0)
        and "tf-assurance-next" not in session_serialization_nav.group(0),
        "Session serialization TREQ is a leaf while preserving full ancestry",
    )
    route_order_nav = re.search(
        r'<nav class="tf-assurance-nav".*?</nav>',
        route_order_page,
        flags=re.DOTALL,
    )
    check(
        route_order_nav is not None
        and "Route order" in route_order_nav.group(0)
        and "tf-assurance-next" not in route_order_nav.group(0),
        "leaf TREQ navigation keeps ancestry without inventing a next-level control",
    )
    check(
        "<span>Technical support</span><b>3</b>" in rate_limit_page
        and '<details class="tf-assurance-next">' in rate_limit_page,
        "Requirement navigation uses a compact dropdown when several Technical requirements exist",
    )
    check(
        'href="assurance-goal-resilient-execution.html"' in provider_retry_page
        and 'href="assurance-feat-provider-retry.html"' in provider_retry_page
        and "<span>Technical support</span><b>2</b>" in provider_retry_page
        and 'href="contract-evidence-provider-retry-classification.html"' in provider_retry_page
        and 'href="contract-evidence-provider-retry-bounds.html"' in provider_retry_page,
        "Provider Retry navigation uses onboarded upper ancestors and exposes both first-class Technical requirements",
    )
    check(
        'href="assurance-goal-resilient-execution.html"' in structured_repair_page
        and 'href="assurance-feat-structured-recovery.html"' in structured_repair_page
        and "<span>Technical support</span><b>2</b>" in structured_repair_page
        and 'href="contract-evidence-structured-output-attempt-bounds.html"' in structured_repair_page
        and 'href="contract-evidence-repair-prompt-bounds.html"' in structured_repair_page,
        "Structured Repair navigation uses onboarded upper ancestors and exposes both first-class Technical requirements",
    )

    expected_upper_titles = {
        "Feature fallback": "Capability Assurance",
        "Feature rate limit": "Capability Assurance",
        "Goal routing": "Outcome Assurance",
        "Feature public API": "Capability Assurance",
        "Feature examples": "Capability Assurance",
        "Goal developer": "Outcome Assurance",
        "Feature sessions": "Capability Assurance",
        "Goal sessions": "Outcome Assurance",
        "Feature data safety": "Capability Assurance",
        "Goal data safety": "Outcome Assurance",
        "Feature tool selection": "Capability Assurance",
        "Feature tool execution": "Capability Assurance",
        "Goal tools": "Outcome Assurance",
        "Feature provider retry": "Capability Assurance",
        "Feature structured recovery": "Capability Assurance",
        "Goal resilience": "Outcome Assurance",
        "Feature provider interoperability": "Capability Assurance",
        "Feature async execution": "Capability Assurance",
        "Feature public response": "Capability Assurance",
        "Goal provider portability": "Outcome Assurance",
        "Feature configuration": "Capability Assurance",
        "Goal configuration": "Outcome Assurance",
        "Feature rich output": "Capability Assurance",
        "Goal rich output": "Outcome Assurance",
        "Product / System": "Product / System Assurance",
    }
    for name, page in upper_assurance_pages.items():
        expected_title = expected_upper_titles[name]
        check(
            f"<title>{expected_title} &#8212; llm-router" in page
            and f'<span class="ellipsis">{expected_title}</span>' in page,
            f"{name}: document title and breadcrumb match the rendered assurance surface",
        )
        style = re.search(
            r'<style id="tf-requirement-monitor-style">(.*?)</style>',
            page,
            flags=re.DOTALL,
        )
        script = re.search(
            r'<script id="tf-requirement-monitor-script">(.*?)</script>',
            page,
            flags=re.DOTALL,
        )
        check(
            style is not None and style.group(1) == canonical_style_text,
            f"{name}: upper assurance uses the exact canonical REQ monitor CSS",
        )
        check(
            page.count('id="tf-requirement-monitor-style"') == 1
            and page.count('id="tf-requirement-monitor-script"') == 1,
            f"{name}: upper assurance keeps one canonical monitor style/script pair",
        )
        check(
            script is not None
            and "syncSticky" in script.group(1)
            and "syncAssurancePath" in script.group(1)
            and "nav-flash" in script.group(1)
            and "document.querySelectorAll" in script.group(1),
            f"{name}: sticky layout and navigation flash follow the canonical REQ interaction pattern",
        )
        check(
            "upper-gate-grid" not in page,
            f"{name}: retired narrative upper-gate layout is absent",
        )
        check(
            'class="verdict"' in page
            and 'class="domain-strip with-support"' in page
            and 'class="section-head"' in page
            and 'class="panel history"' in page,
            f"{name}: verdict, domain strip, sections, and History use canonical Contract Evidence structure",
        )
    for name in (
        "Feature fallback",
        "Goal routing",
        "Feature sessions",
        "Goal sessions",
        "Feature tool execution",
        "Goal tools",
        "Goal resilience",
        "Feature public response",
        "Goal provider portability",
        "Feature configuration",
        "Feature rich output",
        "Goal rich output",
    ):
        page = upper_assurance_pages[name]
        check(
            'class="fault-layout"' in page
            and "data-upper=" in page
            and 'class="inspector"' in page
            and "classList.toggle('selected'" in page,
            f"{name}: active upper criteria use canonical tile → selected inspector interaction",
        )
    for name in (
        "Feature rate limit",
        "Feature public API",
        "Feature examples",
        "Goal developer",
        "Feature sessions",
        "Goal sessions",
        "Feature data safety",
        "Goal data safety",
        "Feature tool selection",
        "Feature tool execution",
        "Feature provider retry",
        "Feature structured recovery",
        "Feature provider interoperability",
        "Feature async execution",
        "Feature public response",
        "Goal configuration",
        "Goal rich output",
        "Product / System",
    ):
        check(
            'class="fault-tile na"' in upper_assurance_pages[name],
            f"{name}: undeclared upper Targets use canonical disabled N/A tiles",
        )

    monitor_copy_pages = {
        path.name: path.read_text()
        for path in sorted(HTML.glob("contract-evidence-*.html"))
    }
    monitor_copy_pages.update(upper_assurance_pages)
    monitor_local_link_issues: list[tuple[str, str]] = []
    for monitor_name, monitor_page in monitor_copy_pages.items():
        for href in re.findall(r'href="([^"]+)"', monitor_page):
            target = href.split("#", 1)[0].split("?", 1)[0]
            if (
                not target
                or target.startswith(("http://", "https://", "mailto:", "javascript:"))
            ):
                continue
            if not (HTML / target).exists():
                monitor_local_link_issues.append((monitor_name, href))
    check(
        not monitor_local_link_issues,
        f"all Contract/upper monitor local link targets exist: {monitor_local_link_issues}",
    )
    banned_tooltip_phrases = (
        "Fails when",
        "Fails if",
        "PASS appears only",
        "never challenged",
        "escapes the expected oracle",
        "verification article",
        "intended-use pedigree",
        "Checks this Test level",
        "Checks how many required failure modes",
        "Checks that this fault group",
        "Shows where proof is required across Test level",
        "Combines verification",
        "Combines child support",
    )
    check(
        all(
            phrase not in page
            for page in monitor_copy_pages.values()
            for phrase in banned_tooltip_phrases
        ),
        "Contract Evidence tooltips avoid failure-condition jargon and stale technical prose",
    )
    check(
        "Checks that every evidence producer used by this proof is qualified for its role."
        in sticky_route_page
        and "Checks that every evidence producer used by this proof is qualified for its role."
        in upper_assurance_pages["Feature fallback"],
        "REQ and upper assurance use the same plain-language evidence-producer explanation",
    )
    upper_help_expectations = {
        "Feature fallback": (
            "Checks that every Requirement needed by this capability is independently proven.",
            "Checks that the Requirements inside this capability work correctly together.",
            "Checks that this capability actually delivers the behavior it exists to provide.",
        ),
        "Feature rate limit": (
            "Checks that every Requirement needed by this capability is independently proven.",
            "Checks that the Requirements inside this capability work correctly together.",
            "Checks that this capability actually delivers the behavior it exists to provide.",
        ),
        "Goal routing": (
            "Checks that every capability needed by this Goal is independently proven.",
            "Checks that the capabilities inside this Goal work correctly together.",
            "Checks that the Goal&#x27;s intended product outcome is achieved in a realistic scenario.",
        ),
        "Feature public API": (
            "Checks that every Requirement needed by this capability is independently proven.",
            "Checks that the Requirements inside this capability work correctly together.",
            "Checks that this capability actually delivers the behavior it exists to provide.",
        ),
        "Feature examples": (
            "Checks that every Requirement needed by this capability is independently proven.",
            "Checks that the Requirements inside this capability work correctly together.",
            "Checks that this capability actually delivers the behavior it exists to provide.",
        ),
        "Goal developer": (
            "Checks that every capability needed by this Goal is independently proven.",
            "Checks that the capabilities inside this Goal work correctly together.",
            "Checks that the Goal&#x27;s intended product outcome is achieved in a realistic scenario.",
        ),
        "Feature sessions": (
            "Checks that every Requirement needed by this capability is independently proven.",
            "Checks that the Requirements inside this capability work correctly together.",
            "Checks that this capability actually delivers the behavior it exists to provide.",
        ),
        "Goal sessions": (
            "Checks that every capability needed by this Goal is independently proven.",
            "Checks that the capabilities inside this Goal work correctly together.",
            "Checks that the Goal&#x27;s intended product outcome is achieved in a realistic scenario.",
        ),
        "Product / System": (
            "Checks that every Goal required for whole-product assurance is independently proven.",
            "Checks that product Goals do not break each other when they interact.",
            "Checks that the whole product works in the intended end-to-end operating scenario.",
        ),
    }
    check(
        all(
            all(tip in upper_assurance_pages[name] for tip in tips)
            for name, tips in upper_help_expectations.items()
        ),
        "upper assurance keeps one semantic tooltip for every upper-level domain",
    )
    check(
        all(
            not re.search(r'class="section-head"><h3>[^<]*<span class="help"', page)
            for page in upper_assurance_pages.values()
        ),
        "upper assurance does not duplicate domain tooltips in section headings",
    )
    check(
        all(
            'class="signal-card ' in page
            and "technical-support-card" in page
            for page in upper_assurance_pages.values()
        ),
        "upper child-support sections reuse canonical REQ technical-support cards",
    )
    check(
        "Producer qualification · 8 producers" in sticky_route_page
        and "<b>1/1</b><small>evidence path</small>" in sticky_route_page,
        "REQ Producer qualification distinguishes producer entities from the evidence-path gate",
    )
    session_persistence_contract = monitor_facts["contracts"]["REQ_SESSION_PERSISTENCE"]
    check(
        (session_persistence_contract.get("target") or {}).get("required_treqs")
        == ["TREQ_SESSION_SERIALIZATION"]
        and re.search(
            r'<strong>Technical support.*?<span class="status not-met">FAIL</span>',
            session_persistence_page,
            re.DOTALL,
        ),
        "Session persistence remains blocked by its first-class serialization Technical requirement",
    )
    session_feature_facts = upper_facts["features"]["FEAT_SESSION_LIFECYCLE"]
    session_goal_facts = upper_facts["goals"]["GOAL_SESSION_CONTINUITY"]
    session_integration = session_feature_facts["capability_integration"]["criteria"][0]
    session_outcome = session_goal_facts["outcome_validation"]["criteria"][0]
    check(
        session_feature_facts["requirement_support"]["status"] == "NOT MET"
        and session_feature_facts["capability_integration"]["status"] == "MET"
        and session_feature_facts["capability_validation"]["status"] == "N/A"
        and session_feature_facts["status"] == "NOT MET"
        and session_integration["id"] == "AC_SESSION_FORK_PERSISTENCE_ISOLATION"
        and session_integration["status"] == "MET"
        and session_integration["passed_executions"] == 1
        and session_integration["required_executions"] == 1
        and session_integration["producer_qualification"]["status"] == "MET"
        and session_integration["freshness"]["status"] == "MET",
        "Session Feature keeps proven integration green while red Requirement support blocks overall PASS",
    )
    check(
        session_goal_facts["capability_support"]["status"] == "NOT MET"
        and session_goal_facts["cross_capability_integration"]["status"] == "N/A"
        and session_goal_facts["outcome_validation"]["status"] == "MET"
        and session_goal_facts["status"] == "NOT MET"
        and session_outcome["id"] == "AOV_SESSION_RESTORED_CONTINUITY"
        and session_outcome["status"] == "MET"
        and session_outcome["passed_executions"] == 1
        and session_outcome["required_executions"] == 1
        and session_outcome["producer_qualification"]["status"] == "MET"
        and session_outcome["freshness"]["status"] == "MET",
        "Session Goal keeps proven restored continuity green while red capability support blocks overall PASS",
    )
    config_feature_facts = upper_facts["features"]["FEAT_CONFIGURATION_PRECEDENCE"]
    config_goal_facts = upper_facts["goals"]["GOAL_CONFIGURATION_PREDICTABILITY"]
    config_integration = config_feature_facts["capability_integration"]["criteria"][0]
    config_validation = config_feature_facts["capability_validation"]["criteria"][0]
    check(
        config_feature_facts["requirement_support"]["status"] == "NOT MET"
        and config_feature_facts["capability_integration"]["status"] == "MET"
        and config_feature_facts["capability_validation"]["status"] == "MET"
        and config_feature_facts["status"] == "NOT MET"
        and config_integration["id"] == "AC_CONFIGURATION_EFFECTIVE_VIEW_COMPOSITION"
        and config_integration["passed_executions"] == 1
        and config_integration["required_executions"] == 1
        and config_validation["id"] == "ACV_CONFIGURATION_POST_INSTALL_REJECTION"
        and config_validation["passed_executions"] == 1
        and config_validation["required_executions"] == 1,
        "Configuration Feature keeps both cross-Requirement proofs green while red child support blocks overall PASS",
    )
    check(
        config_goal_facts["capability_support"]["status"] == "NOT MET"
        and config_goal_facts["cross_capability_integration"]["status"] == "N/A"
        and config_goal_facts["outcome_validation"]["status"] == "N/A"
        and config_goal_facts["status"] == "NOT MET",
        "Configuration Goal stays blocked by capability support without inventing duplicate Goal-level evidence",
    )
    rich_feature_facts = upper_facts["features"]["FEAT_STRUCTURED_OUTPUT"]
    rich_goal_facts = upper_facts["goals"]["GOAL_RICH_INPUT_OUTPUT"]
    rich_integration = rich_feature_facts["capability_integration"]["criteria"][0]
    rich_validation = rich_feature_facts["capability_validation"]["criteria"][0]
    rich_outcome = rich_goal_facts["outcome_validation"]["criteria"][0]
    check(
        rich_feature_facts["requirement_support"]["status"] == "NOT MET"
        and rich_feature_facts["capability_integration"]["status"] == "MET"
        and rich_feature_facts["capability_validation"]["status"] == "MET"
        and rich_feature_facts["status"] == "NOT MET"
        and rich_integration["id"] == "AC_RICH_SCHEMA_MEDIA_COMPOSITION"
        and rich_integration["passed_executions"] == 1
        and rich_integration["required_executions"] == 1
        and rich_validation["id"] == "ACV_RICH_INVALID_SCHEMA_PRE_PROVIDER"
        and rich_validation["passed_executions"] == 1
        and rich_validation["required_executions"] == 1,
        "Rich input/output Feature keeps composition and pre-provider validation green while red Requirement support blocks overall PASS",
    )
    check(
        rich_goal_facts["capability_support"]["status"] == "NOT MET"
        and rich_goal_facts["cross_capability_integration"]["status"] == "N/A"
        and rich_goal_facts["outcome_validation"]["status"] == "MET"
        and rich_goal_facts["status"] == "NOT MET"
        and rich_outcome["id"] == "AOV_RICH_PROVIDER_SWAP_EQUIVALENCE"
        and rich_outcome["passed_executions"] == 1
        and rich_outcome["required_executions"] == 1
        and rich_outcome["producer_qualification"]["status"] == "MET"
        and rich_outcome["freshness"]["status"] == "MET",
        "Rich input/output Goal keeps provider-swap outcome green while red capability support blocks overall PASS",
    )

    goal_page = upper_assurance_pages["Goal routing"]
    routing_goal = upper_facts["goals"]["GOAL_ROUTING_RELIABILITY"]
    routing_integration = routing_goal["cross_capability_integration"]["criteria"][0]
    observed_chain = [
        row.get("id") for row in routing_integration["producer_qualification"]["producers"]
    ]
    check(
        observed_chain[:5]
        == ["PRODUCER_PYTEST", "PRODUCER_PY_TESTKIT", "PRODUCER_ALLURE", "PRODUCER_PYTEST_BDD", "PRODUCER_SCRIPTED_HTTP_SERVER"]
        and observed_chain[-3:]
        == ["PRODUCER_LLM_ROUTER_TRACE_BRIDGE", "PRODUCER_ASSURANCE_ADAPTER", "PRODUCER_UPPER_ASSURANCE_MONITOR"]
        and routing_integration["classification"]["status"] == "MET",
        "upper assurance judges the producers that actually took part in the retained evidence and its test level/boundary/realism",
    )
    check(
        "0 / 2 capabilities pass" in goal_page
        and "1 / 1 scenarios pass" in goal_page
        and "Selected assurance scenario" in goal_page
        and "Scenario coverage" in goal_page
        and '<div class="signal-card coverage-card met-signal">' in goal_page
        and f"<b>{len(observed_chain)}/{len(observed_chain)}</b><small>producers</small>" in goal_page
        and "Test level × boundary × realism" in goal_page
        and goal_page.count('class="state-lane"') >= 2
        and 'class="marker both">ACTUAL = TARGET' in goal_page
        and "Retained path properties" in goal_page
        and "Evidence confidence" in goal_page
        and "Freshness" not in goal_page
        and ">Execution<" not in goal_page
        and ">Confidence<" not in goal_page,
        "upper assurance reuses the canonical REQ coverage-card and state-lane inspector pattern",
    )

    assurance_title_suffix=re.search(
        r"<title>.*?( &#8212; llm-router [^<]+)</title>",
        assurance_page,
        flags=re.DOTALL,
    )
    mutation_title_suffix=re.search(
        r"<title>Mutation Analysis( &#8212; llm-router [^<]+)</title>",
        mutation_page,
        flags=re.DOTALL,
    )
    check(
        assurance_title_suffix is not None
        and mutation_title_suffix is not None
        and mutation_title_suffix.group(1) == assurance_title_suffix.group(1),
        "Mutation Analysis title inherits the current portal documentation version",
    )
    check(
        mutation_page.count('id="mutation-') >= 2,
        "Mutation Analysis exposes the measured contract work queue anchors",
    )
    check(
        "Current signal" in mutation_page
        and "New 0" in mutation_page
        and "Debt 29" in mutation_page
        and "Measured 2/63" in mutation_page,
        "Mutation Analysis keeps the current measured mutation signal compact and denominator-explicit",
    )
    check("How this helps during development" not in mutation_page,
          "Mutation Analysis no longer duplicates long usage guidance")
    check('id="mutation-history"' in mutation_page and "Recent changes" in mutation_page,
          "Mutation Analysis exposes compact retained change history")
    retained_feedback_runs = list(feedback.get("runs") or [])
    check(
        len(retained_feedback_runs) >= 2
        and all(int(row.get("new_unresolved_survivors") or 0) == 0 for row in retained_feedback_runs[-2:])
        and all(int(row.get("resolved_survivors") or 0) == 0 for row in retained_feedback_runs[-2:])
        and all(int(row.get("mutants") or 0) > 0 for row in retained_feedback_runs[-2:]),
        "retained campaign summaries preserve current full-audit mutation evidence without fabricating New/Resolved history",
    )
    mutation_history_match = re.search(
        r'<section id="mutation-history">.*?</section>',
        mutation_page,
        flags=re.DOTALL,
    )
    mutation_history_html = mutation_history_match.group(0) if mutation_history_match else ""
    check(
        bool(mutation_history_html)
        and 'href="#"' not in mutation_history_html
        and (
            "mutation-results/campaign-history/" in mutation_history_html
            or "mutation-results/operator-feedback.json" in mutation_history_html
        ),
        "Mutation Analysis history has no broken provenance links and uses retained raw history or summary fallback",
    )
    check(
        mutation_page.count("Fresh</strong> · New 0 · Debt ") >= 2,
        "Mutation Analysis labels each measured contract fresh and keeps survivor debt compact",
    )
    check("Why some contracts are N/A" in mutation_page,
          "Mutation Analysis keeps shared-scope diagnostics behind a compact disclosure")
    check('id="mutation-operator-feedback"' in mutation_page and "Run cost / mutation diagnostics" in mutation_page,
          "Mutation Analysis keeps operator diagnostics behind a compact disclosure")
    mutation_toc_match=re.search(
        r'<nav class="bd-toc-nav page-toc">.*?</nav>',
        mutation_page,
        flags=re.DOTALL,
    )
    mutation_toc=mutation_toc_match.group(0) if mutation_toc_match else ""
    check(
        (
            not mutation_toc
            or all(
                f'href="#{anchor}"' in mutation_toc
                for anchor in (
                    "mutation-work-queue",
                    "mutation-history",
                    "mutation-unattributed",
                    "mutation-operator-feedback",
                )
            )
        )
        and 'href="#ce-' not in mutation_page
        and 'id="tf-requirement-monitor-style"' not in mutation_page
        and 'id="tf-requirement-monitor-script"' not in mutation_page,
        "Mutation Analysis has no leaked Contract Evidence TOC/runtime assets and any local TOC is mutation-specific",
    )
    check(
        'id="mutation-unattributed"' in mutation_page
        and "2 shared-scope diagnostics" in mutation_page
        and "REQ_ROUTE_ATTEMPT_LIMIT" in mutation_page
        and "REQ_CONFIG_INSTALLATION_COHERENCE" in mutation_page
        and "cannot be uniquely attributed" in mutation_page
        and "diagnostic only" in mutation_page,
        "portal retains concrete shared-scope attribution diagnostics without assigning shared implementation strength to a contract",
    )
    check("Assurance Target / Verification Profile" not in mutation_page and
          "Guarantee Frontier" not in mutation_page,
          "Mutation Analysis may link outward but does not duplicate Contract Evidence semantics")
    trust_need_ids=set(
        re.findall(r'href="#((?:PRODUCER|QUAL)_[A-Z0-9_]+)"', evidence_trust_page)
    )
    check(
        trust_need_ids
        and all(f'id="{need_id}"' in evidence_trust_page for need_id in trust_need_ids),
        "Evidence Trust materializes stable anchors for every producer/qualification deep-link",
    )
    hidden_registry_links=[]
    hidden_registry_pattern=re.compile(
        r'href="[^"]*evidence-producers\.html#(?:PRODUCER|QUAL)_[A-Z0-9_]+"'
    )
    for generated_page in HTML.rglob("*.html"):
        if hidden_registry_pattern.search(generated_page.read_text()):
            hidden_registry_links.append(str(generated_page.relative_to(HTML)))
    check(
        not hidden_registry_links,
        f"generated portal routes hidden producer registry deep-links through visible Evidence Trust: {hidden_registry_links}",
    )
    for contract_id in measured:
        wrapper=(RESULTS / contract_id / "index.html").read_text()
        check("verification-assurance.html" not in wrapper,
              f"{contract_id}: raw MTE wrapper has no Contract Evidence link")

    check("Contract Evidence" in assurance_page,
          "assurance page is named Contract Evidence")
    check(monitor_facts.get("schema") == "ternforge-requirement-monitor-p34-2",
          "Requirement monitor facts carry the current P34 multi-binding schema")
    profiled_contracts = {
        contract_id
        for path in (ROOT / "docs/verification-profiles").glob("*.md")
        for contract_id in re.findall(
            r"^## Profile · ((?:REQ|TREQ)_[A-Z0-9_]+)\s*$",
            path.read_text(),
            flags=re.MULTILINE,
        )
    }
    check(
        set(monitor_facts.get("contracts") or {}) == profiled_contracts,
        "Contract Evidence facts exactly match all first-class REQ/TREQ Verification Profiles",
    )
    required_gate_signals = {
        "semantic_coverage",
        "representation",
        "provenance",
        "producer_qualification",
        "freshness",
        "ms_validation",
    }
    for contract_id, contract in (monitor_facts.get("contracts") or {}).items():
        target = contract.get("target") or {}
        check(
            bool(target.get("coverage_basis"))
            and bool(target.get("representation_basis")),
            f"{contract_id}: Target retains explicit Coverage and Representation basis",
        )
        check(
            set(target.get("gate_aggregation") or {}) == required_gate_signals
            and all(
                (row or {}).get("rule") == "ALL"
                for row in (target.get("gate_aggregation") or {}).values()
            ),
            f"{contract_id}: Target declares the complete fail-closed evidence aggregation surface",
        )
        actual_rows = [
            row
            for rows in (contract.get("coverage_actual") or {}).values()
            for row in rows
        ]
        check(
            all(row.get("verifies_revision_current") is True for row in actual_rows),
            f"{contract_id}: every retained coverage binding pins the current normative revision",
        )
        fault_rows = [
            row
            for retained in ((contract.get("fault_actual") or {}).get("retained_challenges") or {}).values()
            for row in (retained.get("rows") or [])
        ]
        check(
            all(row.get("verifies_revision_current") is True for row in fault_rows),
            f"{contract_id}: every credited fault challenge pins the current normative revision",
        )

    capabilities = declared_provider_capabilities()
    capability_counts = {
        "structured": sum(
            row["supports_json_schema"] for row in capabilities.values()
        ),
        "image": sum(row["supports_images"] for row in capabilities.values()),
        "document": sum(row["supports_files"] for row in capabilities.values()),
        "video_local": sum(
            row["supports_video_file"] for row in capabilities.values()
        ),
        "video_remote": sum(
            row["supports_video_url"] for row in capabilities.values()
        ),
        "tools": sum(row["supports_tools"] for row in capabilities.values()),
    }
    provider_labels = {
        "openai": "OpenAI-compatible",
        "qwenchat": "QwenChat",
        "aistudio": "AI Studio",
        "gemini_webapi": "Gemini WebAPI",
        "google_genai": "Google GenAI",
    }
    capability_path_ids = {
        "structured": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_json_schema"]
        },
        "image": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_images"]
        },
        "document": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_files"]
        },
        "video_local": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_video_file"]
        },
        "video_remote": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_video_url"]
        },
        "tools": {
            provider_labels[family]
            for family, row in capabilities.items()
            if row["supports_tools"]
        },
    }
    all_provider_ids = set(provider_labels.values())

    def target_paths(contract_id: str, criterion_id: str) -> int:
        for cell in (
            (monitor_facts["contracts"][contract_id].get("target") or {}).get(
                "coverage"
            )
            or []
        ):
            counts = cell.get("item_path_counts") or {}
            if criterion_id in counts:
                return int(counts[criterion_id])
        raise AssertionError(
            f"{contract_id}: missing criterion {criterion_id} in Target"
        )

    def target_path_ids(contract_id: str, criterion_id: str) -> set[str]:
        for cell in (
            (monitor_facts["contracts"][contract_id].get("target") or {}).get(
                "coverage"
            )
            or []
        ):
            path_ids = cell.get("item_path_ids") or {}
            if criterion_id in path_ids:
                return set(path_ids[criterion_id])
        return set()

    def actual_path_ids(contract_id: str, criterion_id: str) -> list[str]:
        return [
            str(row.get("coverage_path") or "")
            for row in (
                monitor_facts["contracts"][contract_id]
                .get("coverage_actual", {})
                .get(criterion_id, [])
            )
            if row.get("coverage_path")
        ]

    check(
        capability_counts
        == {
            "structured": 5,
            "image": 5,
            "document": 4,
            "video_local": 4,
            "video_remote": 3,
            "tools": 5,
        },
        "current adapter capability declarations have the audited 5/5/4/4/3/5 provider-family denominators",
    )
    check(
        target_paths(
            "REQ_STRUCTURED_TEXT_OUTPUT",
            "VC_STRUCTURED_TEXT_PROVIDER_MATRIX",
        )
        == capability_counts["structured"]
        and target_paths(
            "REQ_IMAGE_INPUT",
            "VC_IMAGE_GROUNDED_PROVIDER_MATRIX",
        )
        == capability_counts["image"]
        and target_paths(
            "REQ_DOCUMENT_INPUT",
            "VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX",
        )
        == capability_counts["document"]
        and target_paths(
            "REQ_VIDEO_INPUT",
            "VC_VIDEO_LOCAL_GROUNDED_MATRIX",
        )
        == capability_counts["video_local"]
        and target_paths(
            "REQ_VIDEO_INPUT",
            "VC_VIDEO_REMOTE_GROUNDED_MATRIX",
        )
        == capability_counts["video_remote"],
        "Rich input/output provider denominators track current adapter capability declarations",
    )
    check(
        target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_TEXT_PROVIDER_MATRIX",
        )
        == len(capabilities)
        and target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_STRUCTURED_PROVIDER_MATRIX",
        )
        == capability_counts["structured"]
        and target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_IMAGE_PROVIDER_MATRIX",
        )
        == capability_counts["image"]
        and target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_DOCUMENT_PROVIDER_MATRIX",
        )
        == capability_counts["document"]
        and target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX",
        )
        == capability_counts["video_local"]
        and target_paths(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX",
        )
        == capability_counts["video_remote"],
        "Async provider × capability denominators track current adapter declarations",
    )
    check(
        target_paths(
            "REQ_TOOL_CHOICE",
            "VC_TOOL_CHOICE_REPLAY_FAMILIES",
        )
        + target_paths(
            "REQ_TOOL_CHOICE",
            "VC_TOOL_CHOICE_GOOGLE_GENAI",
        )
        == capability_counts["tools"],
        "Tool-choice provider-family denominator tracks all adapters declaring tool support",
    )
    check(
        target_paths(
            "REQ_RESPONSE_NORMALIZATION",
            "VC_PROVIDER_RESPONSE_EQUIVALENCE",
        )
        == len(capabilities) - 1,
        "Response-normalization denominator compares every non-baseline provider family",
    )
    check(
        target_path_ids(
            "REQ_STRUCTURED_TEXT_OUTPUT",
            "VC_STRUCTURED_TEXT_PROVIDER_MATRIX",
        )
        == capability_path_ids["structured"]
        and target_path_ids(
            "REQ_IMAGE_INPUT",
            "VC_IMAGE_GROUNDED_PROVIDER_MATRIX",
        )
        == capability_path_ids["image"]
        and target_path_ids(
            "REQ_DOCUMENT_INPUT",
            "VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX",
        )
        == capability_path_ids["document"]
        and target_path_ids(
            "REQ_VIDEO_INPUT",
            "VC_VIDEO_LOCAL_GROUNDED_MATRIX",
        )
        == capability_path_ids["video_local"]
        and target_path_ids(
            "REQ_VIDEO_INPUT",
            "VC_VIDEO_REMOTE_GROUNDED_MATRIX",
        )
        == capability_path_ids["video_remote"],
        "Rich input/output Targets retain the exact provider-family identities implied by adapter capabilities",
    )
    check(
        target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_TEXT_PROVIDER_MATRIX",
        )
        == all_provider_ids
        and target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_STRUCTURED_PROVIDER_MATRIX",
        )
        == capability_path_ids["structured"]
        and target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_IMAGE_PROVIDER_MATRIX",
        )
        == capability_path_ids["image"]
        and target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_DOCUMENT_PROVIDER_MATRIX",
        )
        == capability_path_ids["document"]
        and target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX",
        )
        == capability_path_ids["video_local"]
        and target_path_ids(
            "REQ_ASYNC_PROVIDER_EXECUTION",
            "VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX",
        )
        == capability_path_ids["video_remote"],
        "Async Targets retain exact provider identities for every capability partition",
    )
    check(
        target_path_ids(
            "REQ_TOOL_CHOICE",
            "VC_TOOL_CHOICE_REPLAY_FAMILIES",
        )
        == capability_path_ids["tools"] - {"Google GenAI"}
        and target_path_ids(
            "REQ_TOOL_CHOICE",
            "VC_TOOL_CHOICE_GOOGLE_GENAI",
        )
        == {"Google GenAI"}
        and target_path_ids(
            "REQ_MULTI_ROUND_TOOL_EXECUTION",
            "VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES",
        )
        == capability_path_ids["tools"] - {"OpenAI-compatible"}
        and target_path_ids(
            "REQ_MULTI_ROUND_TOOL_EXECUTION",
            "VC_TOOL_MULTI_ROUND_OPENAI_LOCAL",
        )
        == {"OpenAI-compatible"},
        "Tool provider matrices retain the exact Replay/Substitute family split",
    )
    check(
        target_path_ids(
            "REQ_RESPONSE_NORMALIZATION",
            "VC_PROVIDER_RESPONSE_EQUIVALENCE",
        )
        == all_provider_ids - {"OpenAI-compatible"},
        "Response-normalization Target retains every non-baseline provider identity",
    )
    for contract_id, contract in monitor_facts["contracts"].items():
        for cell in (contract.get("target") or {}).get("coverage") or []:
            counts = cell.get("item_path_counts") or {}
            path_ids = cell.get("item_path_ids") or {}
            for criterion_id, expected_count in counts.items():
                if int(expected_count) > 1:
                    check(
                        criterion_id in path_ids
                        and len(path_ids[criterion_id]) == int(expected_count)
                        and len(set(path_ids[criterion_id])) == int(expected_count),
                        f"{contract_id}/{criterion_id}: every multi-path Target has exact unique path identities",
                    )
            for criterion_id, expected_ids in path_ids.items():
                actual_ids = actual_path_ids(contract_id, criterion_id)
                check(
                    len(actual_ids) == len(set(actual_ids)),
                    f"{contract_id}/{criterion_id}: retained coverage path identities are unique",
                )
                check(
                    set(actual_ids) <= set(expected_ids),
                    f"{contract_id}/{criterion_id}: retained coverage path identities are a subset of Target",
                )
    shipped_examples = [
        path
        for path in (ROOT / "examples/llm_router").glob("*.py")
        if path.name != "__init__.py"
    ]
    check(
        target_paths(
            "REQ_EXAMPLE_IMPORT_SAFETY",
            "VC_EXAMPLE_IMPORT_SAFETY",
        )
        == len(shipped_examples),
        "Example-import-safety denominator tracks every shipped example module",
    )
    contract_pages = {
        "REQ_REQUEST_OVERRIDE_PRECEDENCE": override_page,
        "REQ_INVALID_CONFIGURATION_ERRORS": assurance_page,
        "REQ_CREDENTIAL_RESOLUTION": credential_page,
        "REQ_CONFIG_INSTALLATION_COHERENCE": install_page,
        **config_treq_pages,
        "REQ_TOOL_CHOICE": tool_choice_page,
        "REQ_MULTI_ROUND_TOOL_EXECUTION": tool_multi_page,
        "REQ_TOOL_RUNTIME_SAFETY": tool_runtime_page,
        "REQ_SYNC_ROUTE_FALLBACK": sync_route_page,
        "REQ_ROUTE_TIMEOUT_FALLBACK": timeout_route_page,
        "REQ_ROUTE_ATTEMPT_LIMIT": attempt_limit_page,
        "REQ_ROUTE_STICKY_START": sticky_route_page,
        "REQ_RATE_LIMIT_ROUTING": rate_limit_page,
        "REQ_PROVIDER_RETRY": provider_retry_page,
        "TREQ_PROVIDER_RETRY_CLASSIFICATION": provider_retry_classification_page,
        "TREQ_PROVIDER_RETRY_BOUNDS": provider_retry_bounds_page,
        "REQ_STRUCTURED_OUTPUT_REPAIR": structured_repair_page,
        "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS": structured_attempt_bounds_page,
        "TREQ_REPAIR_PROMPT_BOUNDS": repair_prompt_bounds_page,
        "REQ_SENSITIVE_DATA_PROTECTION": security_page,
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": provider_adapter_page,
        "TREQ_OPENAI_ADAPTER_BOUNDARY": openai_adapter_page,
        "TREQ_QWENCHAT_ADAPTER_BOUNDARY": qwenchat_adapter_page,
        "TREQ_AISTUDIO_ADAPTER_BOUNDARY": aistudio_adapter_page,
        "TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY": gemini_webapi_adapter_page,
        "TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY": google_genai_adapter_page,
        "REQ_ASYNC_PROVIDER_EXECUTION": async_provider_page,
        "REQ_RESPONSE_NORMALIZATION": response_normalization_page,
        "TREQ_USAGE_NORMALIZATION": usage_normalization_page,
        "REQ_PROVIDER_ERROR_BOUNDARY": provider_error_page,
        "REQ_SESSION_LIFECYCLE": session_lifecycle_page,
        "REQ_SESSION_PERSISTENCE": session_persistence_page,
        "TREQ_SESSION_SERIALIZATION": session_serialization_page,
        "REQ_PUBLIC_API_SURFACE": public_api_page,
        "REQ_EXAMPLE_IMPORT_SAFETY": example_import_page,
        "REQ_STRUCTURED_TEXT_OUTPUT": structured_text_page,
        "REQ_DOCUMENT_INPUT": document_input_page,
        "REQ_IMAGE_INPUT": image_input_page,
        "REQ_VIDEO_INPUT": video_input_page,
        "REQ_STRUCTURED_SCHEMA_CONTRACT": structured_schema_page,
        "REQ_MULTIMODAL_CONTENT_NORMALIZATION": content_normalization_page,
    }
    for contract_id, page in contract_pages.items():
        check(
            page.count('id="tf-requirement-monitor"') == 1
            and page.count('<section id="assurance-') == 1
            and f'<section id="assurance-{contract_id.lower()}">' in page
            and 'id="verification-assurance-map"' not in page,
            f"{contract_id}: Contract Evidence is one isolated accepted monitor",
        )
        check(
            f'id="ce-coverage-{contract_id.lower()}"' in page
            and f'id="ce-faults-{contract_id.lower()}"' in page
            and f'id="ce-history-{contract_id.lower()}"' in page,
            f"{contract_id}: canonical coverage/fault/history anchors exist",
        )
        check(
            "EXPERIMENT" not in page and "EXTRA" not in page,
            f"{contract_id}: no retired experiment/optional-evidence badges leak into monitor UI",
        )
        check(
            "path-identity-gaps" not in page
            and "Missing:" not in page
            and "Unexpected:" not in page
            and "Duplicate:" not in page,
            f"{contract_id}: exact path identities stay out of the compact monitor UI",
        )

    routing_fault_expectations = {
        "REQ_SYNC_ROUTE_FALLBACK": {
            "interface.error-status": (1, 1),
        },
        "REQ_ROUTE_TIMEOUT_FALLBACK": {
            "runtime.latency-timeout": (4, 4),
        },
        "REQ_ROUTE_ATTEMPT_LIMIT": {},
        "REQ_ROUTE_STICKY_START": {},
        "REQ_RATE_LIMIT_ROUTING": {
            "interface.error-status": (1, 1),
        },
    }
    for contract_id, expected_challenges in routing_fault_expectations.items():
        routing_contract = monitor_facts["contracts"][contract_id]
        actual_by_item = routing_contract.get("coverage_actual") or {}
        for target_cell in (routing_contract.get("target") or {}).get("coverage") or []:
            for criterion_id in target_cell.get("items") or []:
                expected_paths = int(
                    (target_cell.get("item_path_counts") or {}).get(criterion_id, 1)
                )
                actual_paths = [
                    row
                    for row in actual_by_item.get(criterion_id) or []
                    if row.get("level") == target_cell.get("level")
                    and row.get("boundary") == target_cell.get("boundary")
                ]
                check(
                    len(actual_paths) == expected_paths
                    and all(
                        row.get("result") == "passed"
                        and row.get("provenance") == "COMPLETE"
                        and row.get("producer_qualification") == "QUALIFIED"
                        and row.get("freshness") == "CURRENT"
                        for row in actual_paths
                    ),
                    f"{contract_id}: {criterion_id} retains every declared current/qualified coverage path",
                )

        retained = (
            (routing_contract.get("fault_actual") or {}).get("retained_challenges")
            or {}
        )
        check(
            set(retained) == set(expected_challenges),
            f"{contract_id}: retained fault challenges contain only explicitly declared runtime-observed classes",
        )
        for fault_class, (expected_exercised, expected_detected) in expected_challenges.items():
            row = retained[fault_class]
            check(
                row.get("exercised_paths") == expected_exercised
                and row.get("detected_paths") == expected_detected
                and row.get("exercised") is True
                and row.get("detected") is True
                and all(
                    item.get("freshness") == "CURRENT"
                    and item.get("producer_qualification") == "QUALIFIED"
                    and item.get("observation_sha256")
                    for item in row.get("rows") or []
                ),
                f"{contract_id}: {fault_class} challenge is current, qualified, and detected on every declared path",
            )

        required_faults = {
            item["id"]
            for group in (routing_contract.get("target") or {}).get("fault_groups") or []
            for item in group.get("items") or []
            if item.get("state") == "required"
        }
        challenged_faults = {
            class_id
            for class_id in required_faults
            if ((routing_contract.get("fault_actual") or {}).get("classes") or {})
            .get(class_id, {})
            .get("exercised")
        }
        routing_classes = (routing_contract.get("fault_actual") or {}).get("classes") or {}
        campaign_challenged = challenged_faults - set(expected_challenges)
        check(
            set(expected_challenges) <= challenged_faults
            and all(
                class_id.startswith("impl.")
                and routing_classes[class_id].get("campaign_state") == "current"
                for class_id in campaign_challenged
            )
            and challenged_faults < required_faults,
            f"{contract_id}: partial Fault Model remains explicit instead of becoming false-green",
        )
        check(
            '<div class="overall not-met">FAIL</div>' in contract_pages[contract_id],
            f"{contract_id}: rendered Overall remains FAIL while required fault classes are still unchallenged",
        )

    resilience_expectations = {
        "REQ_PROVIDER_RETRY": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY": 4,
                    "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY": 2,
                },
            },
            "treqs": [
                "TREQ_PROVIDER_RETRY_CLASSIFICATION",
                "TREQ_PROVIDER_RETRY_BOUNDS",
            ],
            "faults": {
                "interface.error-status": (4, 4),
                "runtime.unavailable-disconnect": (2, 2),
            },
        },
        "TREQ_PROVIDER_RETRY_CLASSIFICATION": {
            "cells": {
                ("component", "none"): {
                    "VC_PROVIDER_RETRY_STATUS_CLASSIFICATION": 2,
                    "VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION": 2,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "TREQ_PROVIDER_RETRY_BOUNDS": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_RETRY_ATTEMPT_BOUND": 2,
                },
            },
            "treqs": [],
            "faults": {"interface.unexpected-interaction": (2, 2)},
        },
        "REQ_STRUCTURED_OUTPUT_REPAIR": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_STRUCTURED_REPAIR_RECOVERY": 1,
                },
            },
            "treqs": [
                "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS",
                "TREQ_REPAIR_PROMPT_BOUNDS",
            ],
            "faults": {"interface.payload-schema": (1, 1)},
        },
        "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND": 2,
                },
            },
            "treqs": [],
            "faults": {"interface.unexpected-interaction": (2, 2)},
        },
        "TREQ_REPAIR_PROMPT_BOUNDS": {
            "cells": {
                ("component", "none"): {"VC_REPAIR_PROMPT_BOUNDS": 1},
            },
            "treqs": [],
            "faults": {},
        },
    }
    for contract_id, expected in resilience_expectations.items():
        contract = monitor_facts["contracts"][contract_id]
        target_cells = {
            (row.get("level"), row.get("boundary")): row
            for row in (contract.get("target") or {}).get("coverage") or []
        }
        check(
            set(target_cells) == set(expected["cells"])
            and all(
                target_cells[key].get("item_path_counts") == counts
                for key, counts in expected["cells"].items()
            ),
            f"{contract_id}: Resilience coverage target keeps the independently authored Test level/Boundary denominators",
        )
        check(
            (contract.get("target") or {}).get("required_treqs") == expected["treqs"],
            f"{contract_id}: Technical Support ownership stays explicit and does not duplicate child evidence",
        )
        actual_by_item = contract.get("coverage_actual") or {}
        for (level, boundary), criteria in expected["cells"].items():
            for criterion_id, expected_paths in criteria.items():
                rows = [
                    row for row in actual_by_item.get(criterion_id) or []
                    if row.get("level") == level and row.get("boundary") == boundary
                ]
                check(
                    len(rows) == expected_paths
                    and all(
                        row.get("result") == "passed"
                        and row.get("provenance") == "COMPLETE"
                        and row.get("producer_qualification") == "QUALIFIED"
                        and row.get("freshness") == "CURRENT"
                        for row in rows
                    ),
                    f"{contract_id}: {criterion_id} retains every declared current/qualified evidence path",
                )
        retained = (contract.get("fault_actual") or {}).get("retained_challenges") or {}
        check(
            set(retained) == set(expected["faults"]),
            f"{contract_id}: retained fault challenges contain only explicitly declared runtime-observed classes",
        )
        for fault_class, (exercised, detected) in expected["faults"].items():
            row = retained[fault_class]
            check(
                row.get("exercised_paths") == exercised
                and row.get("detected_paths") == detected
                and row.get("exercised") is True
                and row.get("detected") is True
                and all(
                    item.get("freshness") == "CURRENT"
                    and item.get("producer_qualification") == "QUALIFIED"
                    and item.get("observation_sha256")
                    for item in row.get("rows") or []
                ),
                f"{contract_id}: {fault_class} challenge is current, qualified, and detected on every declared path",
            )
        required_faults = {
            item["id"]
            for group in (contract.get("target") or {}).get("fault_groups") or []
            for item in group.get("items") or []
            if item.get("state") == "required"
        }
        challenged_faults = {
            class_id
            for class_id in required_faults
            if ((contract.get("fault_actual") or {}).get("classes") or {})
            .get(class_id, {})
            .get("exercised")
        }
        check(
            only_campaign_extras(contract, challenged_faults, set(expected["faults"]))
            and challenged_faults < required_faults,
            f"{contract_id}: partial Resilience Fault Model remains explicit instead of becoming false-green",
        )
        page = contract_pages[contract_id]
        check(
            '<div class="overall not-met">FAIL</div>' in page
            and re.search(r'<strong>Verification coverage.*?<span class="status met">PASS</span>', page, re.DOTALL)
            and re.search(r'<strong>Fault model.*?<span class="status not-met">FAIL</span>', page, re.DOTALL),
            f"{contract_id}: rendered monitor keeps Coverage PASS, Fault Model FAIL, and Overall FAIL",
        )

    security_contracts = monitor_facts["contracts"]
    security_parent = security_contracts["REQ_SENSITIVE_DATA_PROTECTION"]
    parent_target = (security_parent.get("target") or {}).get("coverage") or []
    check(
        len(parent_target) == 1
        and parent_target[0].get("level") == "system_integration"
        and parent_target[0].get("boundary") == "substitute"
        and parent_target[0].get("representation") == "surrogate_simulated"
        and parent_target[0].get("ms_validation_target") == "L0"
        and parent_target[0].get("item_path_counts")
        == {"VC_DATA_SAFETY_OBSERVABILITY_AUDIT": 1}
        and not (security_parent.get("coverage_actual") or {}),
        "REQ_SENSITIVE_DATA_PROTECTION: product-level observability target remains explicit and red while the full cross-artifact proof is missing",
    )
    check(
        (security_parent.get("target") or {}).get("required_treqs")
        == [
            "TREQ_RUNTIME_LOG_SAFETY",
            "TREQ_VCR_AUTH_REDACTION",
            "TREQ_VCR_REQUEST_CONTENT_REDACTION",
            "TREQ_VCR_RESPONSE_CONTENT_REDACTION",
        ],
        "REQ_SENSITIVE_DATA_PROTECTION: Technical Support contains exactly the four narrow technical confidentiality contracts",
    )
    check(
        not (
            (security_parent.get("fault_actual") or {}).get("retained_challenges")
            or {}
        ),
        "REQ_SENSITIVE_DATA_PROTECTION: child technical fault challenges are not duplicated onto the parent Requirement",
    )
    check(
        '<div class="overall not-met">FAIL</div>' in security_page
        and re.search(
            r'<strong>Verification coverage.*?<span class="status not-met">FAIL</span>',
            security_page,
            re.DOTALL,
        )
        and re.search(
            r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
            security_page,
            re.DOTALL,
        )
        and re.search(
            r'<strong>Technical support.*?<span class="status not-met">FAIL</span>',
            security_page,
            re.DOTALL,
        )
        and "0 / 4 pass" in security_page,
        "REQ_SENSITIVE_DATA_PROTECTION: rendered monitor keeps missing product proof and failing Technical Support visible",
    )

    runtime_contract = security_contracts["TREQ_RUNTIME_LOG_SAFETY"]
    runtime_expected_cells = {
        ("component", "none"): {"VC_SECURITY_LOG_CONTEXT_FIELDS": 1},
        ("system_integration", "substitute"): {
            "VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS": 1,
            "VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS": 1,
            "VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS": 1,
        },
    }
    runtime_target_cells = {
        (row.get("level"), row.get("boundary")): row
        for row in (runtime_contract.get("target") or {}).get("coverage") or []
    }
    check(
        set(runtime_target_cells) == set(runtime_expected_cells)
        and all(
            runtime_target_cells[key].get("item_path_counts") == counts
            for key, counts in runtime_expected_cells.items()
        ),
        "TREQ_RUNTIME_LOG_SAFETY: coverage target owns only runtime-diagnostic partitions",
    )
    runtime_actual = runtime_contract.get("coverage_actual") or {}
    for (level, boundary), criteria in runtime_expected_cells.items():
        for criterion_id, expected_paths in criteria.items():
            rows = [
                row
                for row in runtime_actual.get(criterion_id) or []
                if row.get("level") == level and row.get("boundary") == boundary
            ]
            check(
                len(rows) == expected_paths
                and all(
                    row.get("result") == "passed"
                    and row.get("provenance") == "COMPLETE"
                    and row.get("producer_qualification") == "QUALIFIED"
                    and row.get("freshness") == "CURRENT"
                    for row in rows
                ),
                f"TREQ_RUNTIME_LOG_SAFETY: {criterion_id} retains every declared current/qualified path",
            )
    runtime_faults = (
        (runtime_contract.get("fault_actual") or {}).get("retained_challenges") or {}
    )
    expected_runtime_faults = {
        "interface.error-status": (1, 1),
        "interface.payload-schema": (1, 1),
    }
    check(
        set(runtime_faults) == set(expected_runtime_faults),
        "TREQ_RUNTIME_LOG_SAFETY: provider/schema fault challenges moved to the narrow technical owner",
    )
    for fault_class, (exercised, detected) in expected_runtime_faults.items():
        row = runtime_faults[fault_class]
        check(
            row.get("exercised_paths") == exercised
            and row.get("detected_paths") == detected
            and row.get("exercised") is True
            and row.get("detected") is True,
            f"TREQ_RUNTIME_LOG_SAFETY: {fault_class} remains detected by retained evidence",
        )
    check(
        '<div class="overall not-met">FAIL</div>' in runtime_log_safety_page
        and re.search(
            r'<strong>Verification coverage.*?<span class="status met">PASS</span>',
            runtime_log_safety_page,
            re.DOTALL,
        )
        and re.search(
            r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
            runtime_log_safety_page,
            re.DOTALL,
        ),
        "TREQ_RUNTIME_LOG_SAFETY: Coverage passes while incomplete Fault Model keeps the contract red",
    )

    for contract_id, criterion_id, page in (
        (
            "TREQ_VCR_AUTH_REDACTION",
            "VC_VCR_AUTH_DURABLE_REDACTION",
            vcr_auth_redaction_page,
        ),
        (
            "TREQ_VCR_REQUEST_CONTENT_REDACTION",
            "VC_VCR_REQUEST_BODY_DURABLE_REDACTION",
            vcr_request_redaction_page,
        ),
    ):
        contract = security_contracts[contract_id]
        target_rows = (contract.get("target") or {}).get("coverage") or []
        actual_rows = (contract.get("coverage_actual") or {}).get(criterion_id) or []
        check(
            len(target_rows) == 1
            and target_rows[0].get("level") == "system_integration"
            and target_rows[0].get("boundary") == "substitute"
            and target_rows[0].get("item_path_counts") == {criterion_id: 1}
            and len(actual_rows) == 1
            and actual_rows[0].get("result") == "passed"
            and actual_rows[0].get("provenance") == "COMPLETE"
            and actual_rows[0].get("producer_qualification") == "QUALIFIED"
            and actual_rows[0].get("freshness") == "CURRENT",
            f"{contract_id}: durable VCR coverage is one current qualified physical-persistence path",
        )
        check(
            '<div class="overall not-met">FAIL</div>' in page
            and re.search(
                r'<strong>Verification coverage.*?<span class="status met">PASS</span>',
                page,
                re.DOTALL,
            )
            and re.search(
                r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
                page,
                re.DOTALL,
            ),
            f"{contract_id}: passing coverage does not false-green the incomplete Fault Model",
        )

    response_contract = security_contracts["TREQ_VCR_RESPONSE_CONTENT_REDACTION"]
    response_target = (response_contract.get("target") or {}).get("coverage") or []
    check(
        len(response_target) == 1
        and response_target[0].get("level") == "system_integration"
        and response_target[0].get("boundary") == "substitute"
        and response_target[0].get("item_path_counts")
        == {"VC_VCR_RESPONSE_ECHO_DURABLE_REDACTION": 1}
        and not (response_contract.get("coverage_actual") or {}),
        "TREQ_VCR_RESPONSE_CONTENT_REDACTION: generic caller-echo target stays red despite narrower credential-redaction evidence",
    )
    check(
        '<div class="overall not-met">FAIL</div>' in vcr_response_redaction_page
        and re.search(
            r'<strong>Verification coverage.*?<span class="status not-met">FAIL</span>',
            vcr_response_redaction_page,
            re.DOTALL,
        )
        and re.search(
            r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
            vcr_response_redaction_page,
            re.DOTALL,
        ),
        "TREQ_VCR_RESPONSE_CONTENT_REDACTION: known response-echo gap remains visibly unproven",
    )

    provider_expectations = {
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_ADAPTER_INTEROPERABILITY_MATRIX": 5,
                },
            },
            "treqs": [
                "TREQ_OPENAI_ADAPTER_BOUNDARY",
                "TREQ_QWENCHAT_ADAPTER_BOUNDARY",
                "TREQ_AISTUDIO_ADAPTER_BOUNDARY",
                "TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY",
                "TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY",
            ],
            "faults": {},
        },
        "TREQ_OPENAI_ADAPTER_BOUNDARY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_OPENAI_ADAPTER_BOUNDARY": 6,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "TREQ_QWENCHAT_ADAPTER_BOUNDARY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_QWENCHAT_ADAPTER_BOUNDARY": 4,
                },
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_QWENCHAT_UPLOAD_RETRY": 1,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "TREQ_AISTUDIO_ADAPTER_BOUNDARY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_AISTUDIO_ADAPTER_BOUNDARY": 3,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_GEMINI_WEBAPI_ADAPTER_BOUNDARY": 5,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY": 3,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "REQ_ASYNC_PROVIDER_EXECUTION": {
            "cells": {
                ("system_integration", "replay"): {
                    "VC_ASYNC_TEXT_PROVIDER_MATRIX": 5,
                    "VC_ASYNC_STRUCTURED_PROVIDER_MATRIX": 5,
                    "VC_ASYNC_IMAGE_PROVIDER_MATRIX": 5,
                    "VC_ASYNC_DOCUMENT_PROVIDER_MATRIX": 4,
                    "VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX": 4,
                    "VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX": 3,
                },
            },
            "treqs": [],
            "actual": {
                "VC_ASYNC_TEXT_PROVIDER_MATRIX": 2,
                "VC_ASYNC_STRUCTURED_PROVIDER_MATRIX": 2,
                "VC_ASYNC_IMAGE_PROVIDER_MATRIX": 1,
                "VC_ASYNC_DOCUMENT_PROVIDER_MATRIX": 0,
                "VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX": 0,
                "VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX": 0,
            },
            "coverage_pass": False,
            "faults": {},
        },
        "REQ_RESPONSE_NORMALIZATION": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_RESPONSE_EQUIVALENCE": 4,
                },
            },
            "treqs": ["TREQ_USAGE_NORMALIZATION"],
            "actual": {"VC_PROVIDER_RESPONSE_EQUIVALENCE": 1},
            "coverage_pass": False,
            "faults": {},
        },
        "TREQ_USAGE_NORMALIZATION": {
            "cells": {
                ("component", "none"): {
                    "VC_PROVIDER_USAGE_NORMALIZATION": 3,
                },
            },
            "treqs": [],
            "faults": {},
        },
        "REQ_PROVIDER_ERROR_BOUNDARY": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_ERROR_HTTP": 1,
                    "VC_PROVIDER_ERROR_SDK": 1,
                },
            },
            "treqs": [],
            "faults": {"interface.error-status": (2, 2)},
        },
    }
    for contract_id, expected in provider_expectations.items():
        contract = monitor_facts["contracts"][contract_id]
        cells = cast(
            "dict[tuple[str, str], dict[str, int]]",
            cast("dict[str, Any]", expected)["cells"],
        )
        target_cells = {
            (row.get("level"), row.get("boundary")): row
            for row in (contract.get("target") or {}).get("coverage") or []
        }
        check(
            set(target_cells) == set(cells)
            and all(
                target_cells[key].get("item_path_counts") == counts
                for key, counts in cells.items()
            ),
            f"{contract_id}: Provider coverage target keeps the independently authored Test level/Boundary denominators",
        )
        check(
            (contract.get("target") or {}).get("required_treqs")
            == cast("dict[str, Any]", expected)["treqs"],
            f"{contract_id}: Provider Technical Support ownership stays explicit instead of duplicating child evidence",
        )
        actual_by_item = contract.get("coverage_actual") or {}
        expected_actual = {
            criterion_id: expected_paths
            for criteria in cells.values()
            for criterion_id, expected_paths in criteria.items()
        }
        expected_actual.update(
            cast("dict[str, int]", cast("dict[str, Any]", expected).get("actual") or {})
        )
        for (level, boundary), criteria in cells.items():
            for criterion_id in criteria:
                expected_paths = expected_actual.get(criterion_id, 0)
                rows = [
                    row
                    for row in actual_by_item.get(criterion_id) or []
                    if row.get("level") == level and row.get("boundary") == boundary
                ]
                check(
                    len(rows) == expected_paths
                    and all(
                        row.get("result") == "passed"
                        and row.get("provenance") == "COMPLETE"
                        and row.get("producer_qualification") == "QUALIFIED"
                        and row.get("freshness") == "CURRENT"
                        and row.get("verifies_revision_current") is True
                        for row in rows
                    ),
                    f"{contract_id}: {criterion_id} retains exactly the current/qualified Actual paths without filling Target gaps",
                )
        retained = (
            (contract.get("fault_actual") or {}).get("retained_challenges") or {}
        )
        expected_faults = cast(
            "dict[str, tuple[int, int]]",
            cast("dict[str, Any]", expected)["faults"],
        )
        check(
            set(retained) == set(expected_faults),
            f"{contract_id}: retained fault challenges contain only explicitly declared runtime-observed classes",
        )
        for fault_class, (exercised, detected) in expected_faults.items():
            row = retained[fault_class]
            check(
                row.get("exercised_paths") == exercised
                and row.get("detected_paths") == detected
                and row.get("exercised") is True
                and row.get("detected") is True
                and all(
                    item.get("freshness") == "CURRENT"
                    and item.get("producer_qualification") == "QUALIFIED"
                    and item.get("observation_sha256")
                    for item in row.get("rows") or []
                ),
                f"{contract_id}: {fault_class} challenge is current, qualified, and detected on every declared path",
            )
        required_faults = {
            item["id"]
            for group in (contract.get("target") or {}).get("fault_groups") or []
            for item in group.get("items") or []
            if item.get("state") == "required"
        }
        challenged_faults = {
            class_id
            for class_id in required_faults
            if ((contract.get("fault_actual") or {}).get("classes") or {})
            .get(class_id, {})
            .get("exercised")
        }
        check(
            only_campaign_extras(contract, challenged_faults, set(expected_faults))
            and challenged_faults < required_faults,
            f"{contract_id}: partial Provider Fault Model remains explicit instead of becoming false-green",
        )
        page = contract_pages[contract_id]
        coverage_pass = bool(cast("dict[str, Any]", expected).get("coverage_pass", True))
        coverage_class = "met" if coverage_pass else "not-met"
        coverage_label = "PASS" if coverage_pass else "FAIL"
        check(
            '<div class="overall not-met">FAIL</div>' in page
            and re.search(
                rf'<strong>Verification coverage.*?<span class="status {coverage_class}">{coverage_label}</span>',
                page,
                re.DOTALL,
            )
            and re.search(
                r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
                page,
                re.DOTALL,
            ),
            f"{contract_id}: rendered monitor keeps honest Coverage, Fault Model FAIL, and Overall FAIL",
        )

    small_feature_expectations = {
        "REQ_SESSION_LIFECYCLE": {
            ("component_integration", "none"): {
                "VC_SESSION_HISTORY_INCLUDED": 1,
                "VC_SESSION_HISTORY_SUPPRESSED": 1,
                "VC_SESSION_FORK_ISOLATION": 1,
                "VC_SESSION_CLEAR_REUSE": 1,
            },
            ("system", "none"): {"VC_SESSION_CONCURRENT_ISOLATION": 1},
        },
        "REQ_SESSION_PERSISTENCE": {
            ("component", "none"): {
                "VC_SESSION_PERSISTENCE_GENERATED_STATE": 1,
            },
            ("component_integration", "none"): {
                "VC_SESSION_PUBLIC_PERSISTENCE": 1,
                "VC_SESSION_PUBLIC_MEDIA_PERSISTENCE": 4,
            },
        },
        "TREQ_SESSION_SERIALIZATION": {
            ("component", "none"): {
                "VC_SESSION_SERIALIZATION_MEDIA": 4,
                "VC_SESSION_SERIALIZATION_VERSION_REJECTION": 1,
            },
        },
        "REQ_PUBLIC_API_SURFACE": {
            ("component", "none"): {"VC_PUBLIC_API_ROOT_EXPORTS": 1},
        },
        "REQ_EXAMPLE_IMPORT_SAFETY": {
            ("component", "none"): {"VC_EXAMPLE_IMPORT_SAFETY": 6},
        },
    }
    session_fault_expectations = {
        "REQ_SESSION_LIFECYCLE": {
            "impl.control-flow",
            "spec.wrong-outcome",
            "spec.missing-partition",
            "spec.wrong-ordering-boundary",
        },
        "REQ_SESSION_PERSISTENCE": {
            "impl.control-flow",
            "spec.wrong-outcome",
            "spec.missing-partition",
        },
        "TREQ_SESSION_SERIALIZATION": {
            "impl.comparison",
            "impl.boundary",
            "impl.control-flow",
            "interface.payload-schema",
            "spec.wrong-outcome",
            "spec.missing-partition",
        },
    }
    developer_fault_expectations = {
        "REQ_PUBLIC_API_SURFACE": {
            "architecture.layer-bypass",
            "spec.wrong-outcome",
            "spec.missing-partition",
        },
        "REQ_EXAMPLE_IMPORT_SAFETY": {
            "impl.control-flow",
            "interface.unexpected-interaction",
            "spec.wrong-outcome",
            "spec.missing-partition",
        },
    }
    for contract_id, expected_cells in small_feature_expectations.items():
        contract = monitor_facts["contracts"][contract_id]
        target_cells = {
            (row.get("level"), row.get("boundary")): row
            for row in (contract.get("target") or {}).get("coverage") or []
        }
        check(
            set(target_cells) == set(expected_cells)
            and all(
                target_cells[key].get("item_path_counts") == counts
                for key, counts in expected_cells.items()
            ),
            f"{contract_id}: coverage target keeps the independently authored Test level/Boundary denominators",
        )
        actual_by_item = contract.get("coverage_actual") or {}
        for (level, boundary), criteria in expected_cells.items():
            for criterion_id, expected_paths in criteria.items():
                rows = [
                    row
                    for row in actual_by_item.get(criterion_id) or []
                    if row.get("level") == level and row.get("boundary") == boundary
                ]
                check(
                    len(rows) == expected_paths
                    and all(
                        row.get("result") == "passed"
                        and row.get("provenance") == "COMPLETE"
                        and row.get("producer_qualification") == "QUALIFIED"
                        and row.get("freshness") == "CURRENT"
                        for row in rows
                    ),
                    f"{contract_id}: {criterion_id} retains every declared current/qualified evidence path",
                )
        retained = (
            (contract.get("fault_actual") or {}).get("retained_challenges") or {}
        )
        required_faults = {
            item["id"]
            for group in (contract.get("target") or {}).get("fault_groups") or []
            for item in group.get("items") or []
            if item.get("state") == "required"
        }
        challenged_faults = {
            class_id
            for class_id in required_faults
            if ((contract.get("fault_actual") or {}).get("classes") or {})
            .get(class_id, {})
            .get("exercised")
        }
        expected_session_faults = session_fault_expectations.get(contract_id)
        if expected_session_faults is not None:
            check(
                required_faults == expected_session_faults,
                f"{contract_id}: Session Fault Model keeps the independently authored required classes",
            )
        expected_developer_faults = developer_fault_expectations.get(contract_id)
        page = contract_pages[contract_id]
        if expected_developer_faults is not None:
            check(
                set(retained) == expected_developer_faults
                and required_faults == expected_developer_faults
                and challenged_faults == expected_developer_faults,
                f"{contract_id}: retained Developer fault challenges exactly cover the declared required Fault Model",
            )
            for fault_class in sorted(expected_developer_faults):
                row = retained[fault_class]
                check(
                    row.get("exercised_paths") == 1
                    and row.get("detected_paths") == 1
                    and row.get("exercised") is True
                    and row.get("detected") is True
                    and all(
                        item.get("freshness") == "CURRENT"
                        and item.get("producer_qualification") == "QUALIFIED"
                        and item.get("verifies_revision_current") is True
                        and item.get("observation_sha256")
                        for item in row.get("rows") or []
                    ),
                    f"{contract_id}: {fault_class} challenge is current, qualified, revision-bound, and detected",
                )
            check(
                '<div class="overall met">PASS</div>' in page
                and re.search(
                    r'<strong>Verification coverage.*?<span class="status met">PASS</span>',
                    page,
                    re.DOTALL,
                )
                and re.search(
                    r'<strong>Fault model.*?<span class="status met">PASS</span>',
                    page,
                    re.DOTALL,
                ),
                f"{contract_id}: rendered monitor keeps Coverage PASS, Fault Model PASS, and Overall PASS",
            )
        else:
            check(
                retained == {},
                f"{contract_id}: no fault class is credited without an explicit retained challenge",
            )
            check(
                bool(required_faults)
                and only_campaign_extras(contract, challenged_faults, set())
                and challenged_faults < required_faults,
                f"{contract_id}: incomplete required Fault Model remains explicit instead of becoming false-green",
            )
            check(
                '<div class="overall not-met">FAIL</div>' in page
                and re.search(
                    r'<strong>Verification coverage.*?<span class="status met">PASS</span>',
                    page,
                    re.DOTALL,
                )
                and re.search(
                    r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
                    page,
                    re.DOTALL,
                ),
                f"{contract_id}: rendered monitor keeps Coverage PASS, Fault Model FAIL, and Overall FAIL",
            )

    structured_expectations = {
        "REQ_STRUCTURED_TEXT_OUTPUT": {
            "cells": {
                ("system_integration", "replay", "surrogate_simulated", "L0"): {
                    "VC_STRUCTURED_TEXT_PROVIDER_MATRIX": 5,
                },
            },
            "actual": {"VC_STRUCTURED_TEXT_PROVIDER_MATRIX": 1},
            "coverage_pass": False,
        },
        "REQ_DOCUMENT_INPUT": {
            "cells": {
                ("system_integration", "replay", "surrogate_simulated", "L0"): {
                    "VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX": 4,
                },
            },
            "actual": {"VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX": 4},
            "coverage_pass": True,
        },
        "REQ_IMAGE_INPUT": {
            "cells": {
                ("system_integration", "replay", "surrogate_simulated", "L0"): {
                    "VC_IMAGE_GROUNDED_PROVIDER_MATRIX": 5,
                },
            },
            "actual": {"VC_IMAGE_GROUNDED_PROVIDER_MATRIX": 4},
            "coverage_pass": False,
        },
        "REQ_VIDEO_INPUT": {
            "cells": {
                ("system_integration", "replay", "surrogate_simulated", "L0"): {
                    "VC_VIDEO_LOCAL_GROUNDED_MATRIX": 4,
                    "VC_VIDEO_REMOTE_GROUNDED_MATRIX": 3,
                },
            },
            "actual": {
                "VC_VIDEO_LOCAL_GROUNDED_MATRIX": 4,
                "VC_VIDEO_REMOTE_GROUNDED_MATRIX": 3,
            },
            "coverage_pass": True,
        },
        "REQ_STRUCTURED_SCHEMA_CONTRACT": {
            "cells": {
                ("component", "none", "actual", None): {
                    "VC_SCHEMA_PYDANTIC_RECONSTRUCTION": 1,
                    "VC_SCHEMA_MAPPING_ENFORCEMENT": 1,
                    "VC_SCHEMA_INVALID_MAPPING_REJECTION": 1,
                },
            },
            "actual": {
                "VC_SCHEMA_PYDANTIC_RECONSTRUCTION": 1,
                "VC_SCHEMA_MAPPING_ENFORCEMENT": 1,
                "VC_SCHEMA_INVALID_MAPPING_REJECTION": 1,
            },
            "coverage_pass": True,
        },
        "REQ_MULTIMODAL_CONTENT_NORMALIZATION": {
            "cells": {
                ("component", "none", "actual", None): {
                    "VC_CONTENT_ORDER_DESCRIPTOR_METADATA": 1,
                    "VC_CONTENT_CHAT_MESSAGE_SEMANTICS": 1,
                    "VC_CONTENT_INVALID_INPUT_REJECTION": 5,
                },
                ("system", "none", "actual", None): {
                    "VC_CONTENT_PRE_PROVIDER_REJECTION": 2,
                },
            },
            "actual": {
                "VC_CONTENT_ORDER_DESCRIPTOR_METADATA": 1,
                "VC_CONTENT_CHAT_MESSAGE_SEMANTICS": 1,
                "VC_CONTENT_INVALID_INPUT_REJECTION": 5,
                "VC_CONTENT_PRE_PROVIDER_REJECTION": 2,
            },
            "coverage_pass": True,
        },
    }
    for contract_id, expected in structured_expectations.items():
        contract = monitor_facts["contracts"][contract_id]
        target_cells = {
            (
                row.get("level"),
                row.get("boundary"),
                row.get("representation"),
                row.get("ms_validation_target"),
            ): row
            for row in (contract.get("target") or {}).get("coverage") or []
        }
        check(
            set(target_cells) == set(expected["cells"])
            and all(
                target_cells[key].get("item_path_counts") == counts
                for key, counts in expected["cells"].items()
            ),
            f"{contract_id}: rich-input/output Target preserves independently authored level/boundary/representation denominators",
        )

        actual_by_item = contract.get("coverage_actual") or {}
        for criterion_id, expected_paths in expected["actual"].items():
            rows = actual_by_item.get(criterion_id) or []
            check(
                len(rows) == expected_paths
                and all(
                    row.get("result") == "passed"
                    and row.get("provenance") == "COMPLETE"
                    and row.get("producer_qualification") == "QUALIFIED"
                    and row.get("freshness") == "CURRENT"
                    for row in rows
                ),
                f"{contract_id}: {criterion_id} reports the exact current retained Actual denominator without filling missing paths",
            )

        retained = (
            (contract.get("fault_actual") or {}).get("retained_challenges") or {}
        )
        required_faults = {
            item["id"]
            for group in (contract.get("target") or {}).get("fault_groups") or []
            for item in group.get("items") or []
            if item.get("state") == "required"
        }
        challenged_faults = {
            class_id
            for class_id in required_faults
            if ((contract.get("fault_actual") or {}).get("classes") or {})
            .get(class_id, {})
            .get("exercised")
        }
        check(
            retained == {}
            and bool(required_faults)
            and challenged_faults == set()
            and challenged_faults < required_faults,
            f"{contract_id}: absent retained fault challenges stay explicitly red instead of becoming false-green",
        )

        page = contract_pages[contract_id]
        coverage_class = "met" if expected["coverage_pass"] else "not-met"
        coverage_label = "PASS" if expected["coverage_pass"] else "FAIL"
        check(
            '<div class="overall not-met">FAIL</div>' in page
            and re.search(
                rf'<strong>Verification coverage.*?<span class="status {coverage_class}">{coverage_label}</span>',
                page,
                re.DOTALL,
            )
            and re.search(
                r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
                page,
                re.DOTALL,
            ),
            f"{contract_id}: rendered monitor preserves honest Coverage status, Fault Model FAIL, and Overall FAIL",
        )

    check(assurance_page.count('id="tf-requirement-monitor"') == 1,
          "accepted Requirement monitor is installed exactly once")
    check(
        '<article class="bd-article"><section id="assurance-req_invalid_configuration_errors">' in assurance_page
        and assurance_page.count('<section id="assurance-') == 1
        and 'id="verification-assurance-map"' not in assurance_page,
        "canonical Contract Evidence is an isolated Requirement page, not a monitor nested inside the old assurance map",
    )
    check(
        'id="ce-coverage-req_invalid_configuration_errors"' in assurance_page
        and 'id="ce-faults-req_invalid_configuration_errors"' in assurance_page
        and 'id="ce-history-req_invalid_configuration_errors"' in assurance_page,
        "accepted Requirement monitor preserves canonical Contract Evidence anchors",
    )
    check(not (HTML / "verification-assurance-experiment.html").exists(),
          "retired experiment page is not emitted after canonical cutover")
    check("EXPERIMENT" not in assurance_page,
          "canonical Contract Evidence carries no experiment labeling")

    for heading in ("Verification matrix", "Fault model", "History"):
        check(heading in assurance_page, f"canonical monitor contains accepted section: {heading}")
    for removed_heading in (
        "Evidence Frontier", "Fault Detection", "Evidence Trust", "Assurance Gap",
        "Evidence Paths", "Investigate", "Why / verification intent",
        "Possible ≠ Must ≠ Actual", "Target profile · ",
    ):
        check(removed_heading not in assurance_page,
              f"canonical monitor removes superseded section/concept: {removed_heading}")

    for status in ("PASS", "FAIL", "N/A", "UNKNOWN"):
        check(status in assurance_page, f"canonical visible status vocabulary contains {status}")
    check("MET" not in assurance_page and "NOT MET" not in assurance_page,
          "internal aggregation tokens are not visible in canonical monitor")

    check(
        "Test level" in assurance_page
        and all(label in assurance_page for label in ("Local", "Substitute", "Replay", "Direct live"))
        and all(label in assurance_page for label in (
            "Component", "Component integration", "System", "System integration", "Acceptance",
        )),
        "canonical monitor renders the accepted Test Level × Boundary matrix",
    )
    check("data-cell=" in assurance_page and 'id="cell-inspector"' in assurance_page,
          "canonical matrix cells switch the accepted cell inspector")
    check(
        all(
            label in assurance_page
            for label in (
                "Required evidence",
                "Semantic coverage",
                "1<span>/</span>1",
                "criterion passing",
                "1 criterion pass",
                "0 criteria fail",
                "0 criteria missing",
                "Retained path properties",
                "1/1 path retained",
                "Evidence confidence",
            )
        ),
        "canonical Invalid Configuration parent inspector renders exactly its one System×Local public rejection path",
    )
    check(
        "Representation" in assurance_page
        and "dependent-wrap" in assurance_page
        and "M&amp;S validation" in assurance_page
        and all(label in assurance_page for label in (
            "N/A", "L0", "L1", "L2", "L3", "L4", "NOT DECLARED", "INACTIVE",
        )),
        "canonical monitor nests M&S under Representation with the complete state space",
    )
    check(
        all(label in assurance_page for label in (
            "Provenance", "Producer qualification", "COMPLETE", "QUALIFIED",
        ))
        and "Freshness" not in assurance_page
        and "CURRENT" not in assurance_page,
        "canonical confidence signals stay visible while healthy Freshness stays hidden",
    )
    check(
        "Checks that the evidence uses the required kind of target: synthetic, surrogate, representative, or actual."
        in assurance_page
        and "Checks that every evidence producer used by this proof is qualified for its role."
        in assurance_page
        and "Checks that any surrogate or model used as evidence is validated strongly enough for this target."
        in assurance_page,
        "canonical help text explains what each assurance signal checks in plain language",
    )
    check(
        all(label in assurance_page for label in (
            "Requirement ↗", "Verification profile ↗", "Test model ↗", "Raw facts ↗",
        )),
        "canonical cell inspector retains deliberate drill-downs",
    )
    check(
        "ALL items" not in assurance_page
        and "ALL paths" not in assurance_page
        and "Conditional model check" not in assurance_page
        and "Depends on Representation" not in assurance_page,
        "canonical monitor omits redundant aggregation/meta prose",
    )
    check(
        ".signal-card.na-signal{opacity:" not in assurance_page
        and "background:var(--pst-color-background)" in assurance_page,
        "canonical inactive tooltips remain opaque",
    )
    check(
        "TERNFORGE-NO-CACHE" in assurance_page
        and 'http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0"' in assurance_page,
        "canonical monitor HTML prevents stale local browser caching",
    )

    contract_monitor = monitor_facts["contracts"]["REQ_INVALID_CONFIGURATION_ERRORS"]
    invalid_fault_actual = contract_monitor.get("fault_actual") or {}
    invalid_fault_binding = invalid_fault_actual.get("specialized_probe_binding") or {}
    check(
        invalid_fault_actual.get("specialized_probe_current") is True
        and invalid_fault_binding.get("contract_id") == "REQ_INVALID_CONFIGURATION_ERRORS"
        and int(invalid_fault_binding.get("revision") or -1)
        == int(contract_monitor.get("revision") or -2)
        and bool(invalid_fault_binding.get("source_sha256"))
        and bool(invalid_fault_binding.get("probe_input_set_sha256"))
        and bool(invalid_fault_binding.get("probe_inputs")),
        "Invalid Configuration specialized fault credits are byte-bound to the current Requirement revision and probe inputs",
    )
    check(
        all(
            not ((contract.get("fault_actual") or {}).get("specialized_probe_binding"))
            and (contract.get("fault_actual") or {}).get("specialized_probe_current")
            is False
            for contract_id, contract in monitor_facts["contracts"].items()
            if contract_id != "REQ_INVALID_CONFIGURATION_ERRORS"
        ),
        "no other Requirement receives undeclared specialized fault credit",
    )
    declared_criteria = {
        item
        for row in contract_monitor["target"]["coverage"]
        for item in row.get("items") or []
    }
    check(
        declared_criteria == {"VC_INVALID_CONFIGURATION_PUBLIC_REJECTION"},
        "Invalid Configuration parent monitor owns only its public rejection criterion",
    )
    check(
        (contract_monitor.get("target") or {}).get("required_treqs")
        == list(invalid_child_ids),
        "Invalid Configuration parent requires all thirteen validation Technical requirements",
    )
    invalid_targets = {
        (row["level"], row["boundary"]): row
        for row in contract_monitor["target"]["coverage"]
    }
    check(
        set(invalid_targets) == {("system", "none")}
        and invalid_targets[("system", "none")]["declared_count"] == 1
        and sum(invalid_targets[("system", "none")]["item_path_counts"].values()) == 1,
        "Invalid Configuration parent denominator is exactly one System×Local public rejection path",
    )
    invalid_child_expected = {
        "TREQ_CONFIG_PROVIDER_IDENTITY": ("VC_CONFIG_PROVIDER_IDENTITY", 1),
        "TREQ_CONFIG_MODEL_DECLARATION": ("VC_CONFIG_MODEL_DECLARATION", 1),
        "TREQ_CONFIG_REQUIRED_BASE_URL": ("VC_CONFIG_REQUIRED_BASE_URL", 1),
        "TREQ_CONFIG_ATTEMPT_TIMEOUT": ("VC_CONFIG_ATTEMPT_TIMEOUT", 1),
        "TREQ_CONFIG_RETRY_ATTEMPTS": ("VC_CONFIG_RETRY_ATTEMPTS", 1),
        "TREQ_CONFIG_RETRY_WAIT_BOUNDS": ("VC_CONFIG_RETRY_WAIT_BOUNDS", 2),
        "TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT": ("VC_CONFIG_ROUTE_ATTEMPT_LIMIT", 1),
        "TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES": (
            "VC_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES", 1
        ),
        "TREQ_CONFIG_TOOL_ROUND_LIMIT": ("VC_CONFIG_TOOL_ROUND_LIMIT", 1),
        "TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS": (
            "VC_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS", 1
        ),
        "TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION": (
            "VC_CONFIG_DEFAULT_PROVIDER_DECLARATION", 1
        ),
        "TREQ_CONFIG_DEFAULT_MODEL_MAPPING": ("VC_CONFIG_DEFAULT_MODEL_MAPPING", 2),
        "TREQ_CONFIG_MODEL_PROVIDER_REFERENCES": (
            "VC_CONFIG_MODEL_PROVIDER_REFERENCES", 2
        ),
    }
    for contract_id, (criterion_id, path_count) in invalid_child_expected.items():
        child = monitor_facts["contracts"][contract_id]
        child_cells = (child.get("target") or {}).get("coverage") or []
        check(
            len(child_cells) == 1
            and child_cells[0].get("level") == "component"
            and child_cells[0].get("boundary") == "none"
            and child_cells[0].get("item_path_counts") == {criterion_id: path_count}
            and (child.get("target") or {}).get("required_treqs") == [],
            f"{contract_id}: first-class Component×Local target preserves its independently authored denominator",
        )
        rows = (child.get("coverage_actual") or {}).get(criterion_id) or []
        check(
            len(rows) == path_count
            and all(
                row.get("result") == "passed"
                and row.get("provenance") == "COMPLETE"
                and row.get("producer_qualification") == "QUALIFIED"
                and row.get("freshness") == "CURRENT"
                for row in rows
            ),
            f"{contract_id}: Actual retains exactly the current qualified TREQ paths",
        )
        check(
            not ((child.get("fault_actual") or {}).get("retained_challenges") or {}),
            f"{contract_id}: missing contract-specific fault challenges remain explicit instead of inheriting parent credit",
        )

    override_monitor = monitor_facts["contracts"]["REQ_REQUEST_OVERRIDE_PRECEDENCE"]
    credential_monitor = monitor_facts["contracts"]["REQ_CREDENTIAL_RESOLUTION"]
    install_monitor = monitor_facts["contracts"]["REQ_CONFIG_INSTALLATION_COHERENCE"]
    override_targets = {
        (row["level"], row["boundary"]): row
        for row in override_monitor["target"]["coverage"]
    }
    check(
        override_targets[("component", "none")]["declared_count"] == 1
        and override_targets[("component", "none")]["representation"] == "actual"
        and override_targets[("system_integration", "substitute")]["declared_count"] == 2
        and override_targets[("system_integration", "substitute")]["representation"] == "surrogate_simulated"
        and override_targets[("system_integration", "substitute")]["ms_validation_target"] == "L0",
        "override profile preserves Component Actual plus System-integration Substitute/Surrogate/L0 targets",
    )
    credential_targets = {
        (row["level"], row["boundary"]): row
        for row in credential_monitor["target"]["coverage"]
    }
    check(
        credential_targets[("component", "none")]["declared_count"] == 4
        and sum(credential_targets[("component", "none")]["item_path_counts"].values()) == 6
        and credential_targets[("system", "none")]["declared_count"] == 1
        and sum(credential_targets[("system", "none")]["item_path_counts"].values()) == 1,
        "credential profile retains Component 4 criteria / 6 paths plus System 1 / 1",
    )
    install_targets = {
        (row["level"], row["boundary"]): row
        for row in install_monitor["target"]["coverage"]
    }
    check(
        install_targets[("component", "none")]["declared_count"] == 2
        and install_targets[("system_integration", "substitute")]["declared_count"] == 1
        and install_targets[("system_integration", "substitute")]["representation"] == "surrogate_simulated"
        and install_targets[("system_integration", "substitute")]["ms_validation_target"] == "L0",
        "configuration-installation parent owns two state criteria plus the System-integration runtime-effect path",
    )
    expected_actual = {
        "REQ_REQUEST_OVERRIDE_PRECEDENCE": {
            "VC_REQUEST_OMISSION_PROPERTY",
            "VC_REQUEST_OVERRIDE_PRECEDENCE",
            "VC_REQUEST_EXPLICIT_CLEAR",
        },
        "REQ_CREDENTIAL_RESOLUTION": {
            "VC_CREDENTIAL_CUSTOM_ENV_NAME",
            "VC_CREDENTIAL_AUTO_ROTATION",
            "VC_CREDENTIAL_REQUIRED_MISSING",
            "VC_CREDENTIAL_OPTIONAL_MISSING",
            "VC_CREDENTIAL_PUBLIC_MISSING_ERROR",
        },
        "REQ_CONFIG_INSTALLATION_COHERENCE": {
            "VC_CONFIG_INSTALLATION_ROUND_TRIP",
            "VC_CONFIG_INSTALLATION_RUNTIME_CAPTURE",
            "VC_CONFIG_INSTALLATION_RUNTIME_EFFECT",
        },
        "TREQ_CONFIG_CACHE_INVALIDATION": {"VC_CONFIG_CACHE_INVALIDATION"},
    }
    check(
        (install_monitor.get("target") or {}).get("required_treqs")
        == ["TREQ_CONFIG_CACHE_INVALIDATION"],
        "Configuration installation parent exposes cache invalidation only as Technical Support",
    )
    for contract_id, criteria in expected_actual.items():
        rows = monitor_facts["contracts"][contract_id]["coverage_actual"]
        check(set(rows) == criteria, f"{contract_id}: every declared criterion has retained evidence")
        flat_rows = [row for bindings in rows.values() for row in bindings]
        check(
            all(row.get("result") == "passed" for row in flat_rows)
            and all(row.get("provenance") == "COMPLETE" for row in flat_rows)
            and all(row.get("producer_qualification") == "QUALIFIED" for row in flat_rows)
            and all(row.get("freshness") == "CURRENT" for row in flat_rows),
            f"{contract_id}: retained criterion evidence is passed, complete, qualified and current",
        )
    override_actual = override_monitor["coverage_actual"]
    override_expected_counts = {
        "VC_REQUEST_OVERRIDE_PRECEDENCE": 1,
        "VC_REQUEST_EXPLICIT_CLEAR": 2,
    }
    check(
        all(
            len(override_actual[item]) == expected_count
            and all(
                row["boundary"] == "substitute"
                and row["representation"] == "surrogate_simulated"
                and str(row["ms_validation"]).lower() == "l0"
                for row in override_actual[item]
            )
            for item, expected_count in override_expected_counts.items()
        ),
        "override BDD evidence is honestly retained as Substitute / Surrogate / L0 with explicit null and empty-value partitions",
    )
    partial_coverage_contracts = {
        contract_id
        for contract_id, expected in structured_expectations.items()
        if not expected["coverage_pass"]
    } | {
        contract_id
        for contract_id, expected in provider_expectations.items()
        if not expected.get("coverage_pass", True)
    } | {
        "REQ_SENSITIVE_DATA_PROTECTION",
        "TREQ_VCR_RESPONSE_CONTENT_REDACTION",
    }
    complete_fault_contracts = set(developer_fault_expectations)
    for contract_id, page in contract_pages.items():
        coverage_class = (
            "not-met" if contract_id in partial_coverage_contracts else "met"
        )
        coverage_label = (
            "FAIL" if contract_id in partial_coverage_contracts else "PASS"
        )
        fault_complete = contract_id in complete_fault_contracts
        fault_class = "met" if fault_complete else "not-met"
        fault_label = "PASS" if fault_complete else "FAIL"
        overall_class = (
            "met"
            if fault_complete and contract_id not in partial_coverage_contracts
            else "not-met"
        )
        overall_label = "PASS" if overall_class == "met" else "FAIL"
        check(
            f'<div class="overall {overall_class}">{overall_label}</div>' in page
            and re.search(
                rf'<strong>Verification coverage</strong><span class="status {coverage_class}">{coverage_label}</span>',
                page,
                flags=re.DOTALL,
            )
            and re.search(
                rf'<strong>Fault model</strong><span class="status {fault_class}">{fault_label}</span>',
                page,
                flags=re.DOTALL,
            )
            and "No blocking fault checks selected" not in page
            and "This Verification Profile does not make fault-based testing a blocking target." not in page
            and 'class="fault-layout no-inspector"' not in page
            and 'data-fault="' in page,
            f"{contract_id}: rendered Coverage, Fault Model, and Overall reflect retained Target/Actual evidence without false-green or stale-red status",
        )


    check(
        "data-fault=" in assurance_page
        and all(label in assurance_page for label in (
            "Implementation", "Runtime / dependency", "Interface / protocol",
            "Architecture", "Specification / model",
        )),
        "canonical Fault model renders all project Test Model groups",
    )
    fault_group_help = (
        "Checks that small code mistakes—wrong comparisons, limits, branches, returns, or exception paths—are caught.",
        "Checks that dependency failures—timeouts, disconnects, unavailability, or malformed replies—cannot change the required behavior.",
        "Checks that wrong external calls, error statuses, or malformed payloads are caught at the boundary.",
        "Checks that code cannot bypass a required layer or depend on a forbidden layer.",
        "Checks that tests catch the wrong result, a missing case, or the wrong ordering or boundary rule.",
    )
    check(
        all(assurance_page.count(text) == 1 for text in fault_group_help)
        and "EXTRA" not in assurance_page,
        "each Fault model group has one distinct plain-language explanation",
    )
    invalid_config_groups = (
        (fault_model.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    ).get("groups") or {}
    mutation_chain_labels = [
        label
        for group in invalid_config_groups.values()
        for label in (
            f"{int(group.get('reached') or 0)}/{int(group.get('generated') or 0)}",
            f"{int(group.get('killed') or 0)}/{int(group.get('reached') or 0)}",
        )
    ]
    check(
        len(mutation_chain_labels) == 4
        and all(label in assurance_page for label in (
            "Fault classes", "Required", "Challenged", "Detected",
            "Mutation checks", "Generated", "Reached", "Killed",
            *mutation_chain_labels,
        ))
        and "31/31" not in assurance_page
        and "27/27" not in assurance_page,
        "canonical fault detail renders the current retained mutation denominator chains, not the lightweight-runner numbers",
    )
    optional_faults = {
        item["id"]
        for group in contract_monitor["target"]["fault_groups"]
        for item in group["items"]
        if item["state"] == "optional"
    }
    check(optional_faults == {"runtime.latency-timeout", "architecture.forbidden-edge"},
          "optional fault evidence remains in underlying facts despite having no monitor badge")
    check("Why this group?" not in assurance_page,
          "canonical Fault model contains no inline semantic rationale")
    check("Profile ↗" in assurance_page and "Raw ↗" in assurance_page,
          "canonical Fault model retains profile/raw drill-downs")

    check(
        "Current" in assurance_page
        and 'href="assurance-snapshots.json">History ↗</a>' in assurance_page,
        "canonical History stays compact and links to retained history",
    )
    check(
        "Assurance is not pass/fail" not in assurance_page
        and "tf-gap-hero" not in assurance_page
        and "tf-path-group-grid" not in assurance_page
        and "tf-trust-item" not in assurance_page,
        "canonical monitor contains no superseded prose/dashboard sections",
    )

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
    check(
        "TREQ_RATE_LIMIT_STATE" not in (strength.get("contracts") or {}),
        "legacy Rate-limit state target does not fabricate a current uniquely attributable Test Strength score",
    )
    rate_tests = [
        row
        for row in depth_facts.get("tests") or []
        if "TREQ_RATE_LIMIT_STATE" in (row.get("verifies") or [])
    ]
    check(
        rate_tests
        and all(
            row.get("system_reach") == "component"
            and row.get("boundary_mode") == "none"
            and row.get("representation_fidelity") == "actual"
            for row in rate_tests
        ),
        "Rate-limit state remains backed by current Component×Local×Actual execution paths without an attributed mutation score",
    )

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
    async_tests = [
        row
        for row in depth_facts.get("tests") or []
        if "REQ_ASYNC_PROVIDER_EXECUTION" in (row.get("verifies") or [])
        and str(row.get("nodeid") or "").startswith(
            "tests/llm_router/bdd/execution/test_async.py::"
        )
    ]
    async_upper_tests = [
        row
        for row in depth_facts.get("tests") or []
        if "REQ_ASYNC_PROVIDER_EXECUTION" in (row.get("verifies") or [])
        and row not in async_tests
    ]
    check(
        len(async_tests) == 5
        and all(
            row.get("system_reach") == "system_integration"
            and row.get("boundary_mode") == "replay"
            and row.get("representation_fidelity") == "surrogate_simulated"
            for row in async_tests
        ),
        "Async provider contract evidence keeps five real System-integration×Replay×Surrogate paths",
    )
    check(
        len(async_upper_tests) == 2
        and all(
            row.get("system_reach") == "system_integration"
            and row.get("boundary_mode") == "substitute"
            and row.get("representation_fidelity") == "surrogate_simulated"
            for row in async_upper_tests
        ),
        "Provider upper-assurance scenarios remain distinct Substitute evidence and do not inflate the Async Requirement frontier",
    )
    check(
        not any(row.get("boundary_mode") == "direct" for row in async_tests),
        "Async provider execution currently has no Direct-live contract path, creating the intended target-derived release gap",
    )
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
    def consistent_group(group: dict, reach_label: str) -> bool:
        generated = int(group.get("generated") or 0)
        reached = int(group.get("reached") or 0)
        killed = int(group.get("killed") or 0)
        mutants = group.get("mutants") or []
        return (
            generated > 0
            and killed <= reached <= generated
            and int(group.get("survived") or 0) == reached - killed
            and group.get("mutation_reach") == round(100 * reached / generated, 1)
            and group.get("sensitivity") == (round(100 * killed / reached, 1) if reached else None)
            and isinstance(group.get("invalid"), int)
            and len(mutants) == generated
            and sum(bool(row.get("reached")) for row in mutants) == reached
            and sum(bool(row.get("killed")) for row in mutants) == killed
            and group.get("system_reach") == reach_label
            and group.get("boundary_mode") == "none"
        )

    check(consistent_group(component_faults, "component"),
          "Component×Local fault cell is an exact, internally consistent projection of the retained full-pytest mutation run")
    check(consistent_group(system_faults, "system"),
          "System×Local fault cell is an exact, internally consistent projection of the retained full-pytest mutation run")
    check(int(component_faults.get("killed") or 0) < int(component_faults.get("reached") or 0)
          and int(system_faults.get("killed") or 0) < int(system_faults.get("reached") or 0),
          "surviving mutants stay visible instead of the former lightweight-runner kills")
    check(set(component_faults.get("families") or {}) <= {"boundary", "comparison", "boolean", "return"}
          and {"boundary", "comparison"} <= set(component_faults.get("families") or {})
          and sum(int(row.get("generated") or 0) for row in (component_faults.get("families") or {}).values())
          == int(component_faults.get("generated") or 0)
          and component_faults.get("engine_metadata") == "native pytest-gremlins operator metadata",
          "fault-family classifier uses engine-native pytest-gremlins metadata and partitions the whole denominator")
    overlap = invalid_config_faults.get("detection_overlap") or {}
    implementation_layer = (invalid_config_faults.get("layers") or {}).get("implementation") or {}
    detail_rows = implementation_layer.get("mutant_detail") or []
    component_killed_ids = {row.get("gremlin_id") for row in detail_rows if row.get("component_killed")}
    system_killed_ids = {row.get("gremlin_id") for row in detail_rows if row.get("system_killed")}
    check((overlap.get("mutant_universe"), overlap.get("detected_union"), overlap.get("corroborated"),
           overlap.get("component_only"), overlap.get("system_only")) ==
          (max(int(component_faults.get("generated") or 0), int(system_faults.get("generated") or 0)),
           len(component_killed_ids | system_killed_ids), len(component_killed_ids & system_killed_ids),
           len(component_killed_ids - system_killed_ids), len(system_killed_ids - component_killed_ids))
          and overlap.get("undetected") == int(overlap.get("mutant_universe") or 0) - int(overlap.get("detected_union") or 0),
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
    check((req_layers["implementation"].get("generated"), req_layers["implementation"].get("detected"))
          == (overlap.get("mutant_universe"), overlap.get("detected_union")),
          "Requirement implementation fault layer is backed by the same mutant universe with exact union detection")
    implementation = req_layers["implementation"]
    impl_reach = implementation.get("implementation_reach") or {}
    check(int(impl_reach.get("covered_statements") or 0) <= int(impl_reach.get("executable_statements") or 0) and
          int(impl_reach.get("executable_statements") or 0) > 0 and
          impl_reach.get("percent") == round(100 * int(impl_reach.get("covered_statements") or 0) / int(impl_reach.get("executable_statements") or 1), 1) and
          len(impl_reach.get("missing_statements") or []) == int(impl_reach.get("executable_statements") or 0) - int(impl_reach.get("covered_statements") or 0) and
          impl_reach.get("metric") == "implementation_statement_reach" and
          "coverage.py executable statements" in impl_reach.get("basis", ""),
          "Implementation statement reach has an explicit coverage.py denominator")
    check(implementation.get("overall_detection")
          == round(100 * int(overlap.get("detected_union") or 0) / max(1, int(overlap.get("mutant_universe") or 0)), 1),
          "Overall Detection is retained as the secondary killed/generated metric")
    native_mutants = implementation.get("mutant_detail") or []
    check(len(native_mutants) == overlap.get("mutant_universe")
          and len({row.get("gremlin_id") for row in native_mutants}) == len(native_mutants),
          "exact native mutant detail retains every engine-native gremlin ID without tuple-key collapse")
    check(sum(bool(row.get("component_killed")) for row in native_mutants) == component_faults.get("killed") and
          sum(bool(row.get("system_killed")) for row in native_mutants) == system_faults.get("killed") and
          sum(bool(row.get("system_reached")) for row in native_mutants) == system_faults.get("reached"),
          "exact native mutant table agrees with Component/System killed and reached counts")
    check(all("covering_tests" in row for group in (component_faults, system_faults) for row in group.get("mutants") or []),
          "per-mutant retained facts include covering tests without inventing killing tests")
    retained_mutmut = implementation.get("retained_mutmut") or {}
    check(
        (
            retained_mutmut.get("killed"),
            retained_mutmut.get("survived"),
            retained_mutmut.get("valid_mutants"),
        )
        == (84, 26, 110)
        and retained_mutmut.get("new_survivors") == 0
        and retained_mutmut.get("existing_survivors") == 26
        and retained_mutmut.get("resolved_survivors") == 0
        and "mutate_only_covered_lines=true"
        in retained_mutmut.get("denominator_warning", ""),
        "retained mutmut Test Strength keeps its separate covered-lines denominator without fabricating triage across the adapter-fingerprint change",
    )
    for layer_id, required_fields in {
        "specification": ("claim_section", "mutation", "parser_validity", "execution_command", "detector", "source_url", "test_source_url"),
        "architecture": ("declared_rule", "baseline_summary", "injected_violation", "execution_command", "detector", "source_url"),
        "interface": ("dependency", "expected_interaction", "observed_interaction", "expected_public_error", "public_error", "detector", "source_url"),
        "runtime": ("dependency", "injected_fault", "expected_invariant", "observed_behavior", "detector", "source_url"),
    }.items():
        check(all(req_layers[layer_id].get(field) not in (None, "", []) for field in required_fields),
              f"{layer_id} fault detail retains all promised claim/challenge/detector/drill-down fields")

    # Evaluate current blocking mutation checks from retained facts.
    current_actual = {
        "component-reach": component_faults.get("mutation_reach"),
        "component-sensitivity": component_faults.get("sensitivity"),
        "system-reach": system_faults.get("mutation_reach"),
        "system-sensitivity": system_faults.get("sensitivity"),
    }
    unmet_mutation_checks = sorted(
        name for name, value in current_actual.items() if float(value or 0.0) < 80.0
    )
    invalid_config_page = (HTML / "verification-assurance.html").read_text()
    check(
        all(value is not None for value in current_actual.values())
        and (not unmet_mutation_checks or '<div class="overall not-met">FAIL</div>' in invalid_config_page),
        f"Invalid Configuration mutation Reach/Sensitivity are judged against the 80% floor; unmet checks fail the monitor: {unmet_mutation_checks}",
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
          "historical P31 primary-Requirement snapshot remains immutable and preserves its original obligations, gaps, Reach/Sensitivity and Test Strength")
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
    component_fault = contract_monitor["fault_actual"]["groups"]["component_local"]
    model_declaration_contract = monitor_facts["contracts"][
        "TREQ_CONFIG_MODEL_DECLARATION"
    ]
    component_target = next(
        row
        for row in model_declaration_contract["target"]["coverage"]
        if row["level"] == "component" and row["boundary"] == "none"
    )
    check(
        component_fault["sensitivity"] == component_faults.get("sensitivity")
        and "VC_CONFIG_MODEL_DECLARATION" in component_target["items"]
        and len(
            model_declaration_contract["coverage_actual"].get(
                "VC_CONFIG_MODEL_DECLARATION"
            )
            or []
        )
        == 1,
        "parent mutation history and first-class model-declaration TREQ retain their distinct current facts",
    )

    history = fault_model.get("history") or {}
    check(
        history.get("tool") == "DVC plots"
        and len(history.get("rows") or []) == 3
        and {row.get("run_id") for row in history.get("rows") or []}
        == {"p31-local-1", "p32-local-1", "p33-local-1"},
        "system Assurance History is rendered by DVC from the retained P31-P33 assurance snapshot registry",
    )
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
    configuration_trace_routes = {
        "REQ_REQUEST_OVERRIDE_PRECEDENCE": "contract-evidence-request-override-precedence.html#ce-coverage-req_request_override_precedence",
        "REQ_CREDENTIAL_RESOLUTION": "contract-evidence-credential-resolution.html#ce-coverage-req_credential_resolution",
        "REQ_CONFIG_INSTALLATION_COHERENCE": "contract-evidence-config-installation-coherence.html#ce-coverage-req_config_installation_coherence",
        "REQ_INVALID_CONFIGURATION_ERRORS": "verification-assurance.html#ce-coverage-req_invalid_configuration_errors",
        "TREQ_CONFIG_CACHE_INVALIDATION": "contract-evidence-config-cache-invalidation.html#ce-coverage-treq_config_cache_invalidation",
        "TREQ_CONFIG_PROVIDER_IDENTITY": "contract-evidence-config-provider-identity.html#ce-coverage-treq_config_provider_identity",
        "TREQ_CONFIG_MODEL_DECLARATION": "contract-evidence-config-model-declaration.html#ce-coverage-treq_config_model_declaration",
        "TREQ_CONFIG_REQUIRED_BASE_URL": "contract-evidence-config-required-base-url.html#ce-coverage-treq_config_required_base_url",
        "TREQ_CONFIG_ATTEMPT_TIMEOUT": "contract-evidence-config-attempt-timeout.html#ce-coverage-treq_config_attempt_timeout",
        "TREQ_CONFIG_RETRY_ATTEMPTS": "contract-evidence-config-retry-attempts.html#ce-coverage-treq_config_retry_attempts",
        "TREQ_CONFIG_RETRY_WAIT_BOUNDS": "contract-evidence-config-retry-wait-bounds.html#ce-coverage-treq_config_retry_wait_bounds",
        "TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT": "contract-evidence-config-route-attempt-limit.html#ce-coverage-treq_config_route_attempt_limit",
        "TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES": "contract-evidence-config-fallback-shuffle-min-routes.html#ce-coverage-treq_config_fallback_shuffle_min_routes",
        "TREQ_CONFIG_TOOL_ROUND_LIMIT": "contract-evidence-config-tool-round-limit.html#ce-coverage-treq_config_tool_round_limit",
        "TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS": "contract-evidence-config-structured-output-attempts.html#ce-coverage-treq_config_structured_output_attempts",
        "TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION": "contract-evidence-config-default-provider-declaration.html#ce-coverage-treq_config_default_provider_declaration",
        "TREQ_CONFIG_DEFAULT_MODEL_MAPPING": "contract-evidence-config-default-model-mapping.html#ce-coverage-treq_config_default_model_mapping",
        "TREQ_CONFIG_MODEL_PROVIDER_REFERENCES": "contract-evidence-config-model-provider-references.html#ce-coverage-treq_config_model_provider_references",
    }
    check(
        "TERNFORGE-P27-TRACE-EVIDENCE-START" in trace_reader_page
        and all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in configuration_trace_routes.items()
        ),
        "Traceability Reader routes all Configuration REQ/TREQ contracts to their first-class Contract Evidence pages",
    )
    routing_trace_routes = {
        "REQ_SYNC_ROUTE_FALLBACK": "contract-evidence-sync-route-fallback.html#ce-coverage-req_sync_route_fallback",
        "REQ_ROUTE_TIMEOUT_FALLBACK": "contract-evidence-route-timeout-fallback.html#ce-coverage-req_route_timeout_fallback",
        "REQ_ROUTE_ATTEMPT_LIMIT": "contract-evidence-route-attempt-limit.html#ce-coverage-req_route_attempt_limit",
        "REQ_ROUTE_STICKY_START": "contract-evidence-route-sticky-start.html#ce-coverage-req_route_sticky_start",
        "TREQ_ROUTE_ORDER": "contract-evidence-route-order.html#ce-coverage-treq_route_order",
        "REQ_RATE_LIMIT_ROUTING": "contract-evidence-rate-limit-routing.html#ce-coverage-req_rate_limit_routing",
        "TREQ_RATE_LIMIT_STATE": "contract-evidence-rate-limit-state.html#ce-coverage-treq_rate_limit_state",
        "TREQ_RATE_LIMIT_COOLDOWN_POLICY": "contract-evidence-rate-limit-cooldown-policy.html#ce-coverage-treq_rate_limit_cooldown_policy",
        "TREQ_RATE_LIMIT_AVAILABILITY_SELECTION": "contract-evidence-rate-limit-availability-selection.html#ce-coverage-treq_rate_limit_availability_selection",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in routing_trace_routes.items()
        ),
        "Traceability Reader routes Routing REQ/TREQ contracts to their accepted first-class Contract Evidence pages",
    )
    tool_trace_routes = {
        "REQ_TOOL_CHOICE": "contract-evidence-tool-choice.html#ce-coverage-req_tool_choice",
        "REQ_MULTI_ROUND_TOOL_EXECUTION": "contract-evidence-multi-round-tool-execution.html#ce-coverage-req_multi_round_tool_execution",
        "TREQ_TOOL_REGISTRY": "contract-evidence-tool-registry.html#ce-coverage-treq_tool_registry",
        "REQ_TOOL_RUNTIME_SAFETY": "contract-evidence-tool-runtime-safety.html#ce-coverage-req_tool_runtime_safety",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in tool_trace_routes.items()
        ),
        "Traceability Reader routes Tool Orchestration REQ/TREQ contracts to first-class Contract Evidence pages",
    )
    resilience_trace_routes = {
        "REQ_PROVIDER_RETRY": "contract-evidence-provider-retry.html#ce-coverage-req_provider_retry",
        "TREQ_PROVIDER_RETRY_CLASSIFICATION": "contract-evidence-provider-retry-classification.html#ce-coverage-treq_provider_retry_classification",
        "TREQ_PROVIDER_RETRY_BOUNDS": "contract-evidence-provider-retry-bounds.html#ce-coverage-treq_provider_retry_bounds",
        "REQ_STRUCTURED_OUTPUT_REPAIR": "contract-evidence-structured-output-repair.html#ce-coverage-req_structured_output_repair",
        "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS": "contract-evidence-structured-output-attempt-bounds.html#ce-coverage-treq_structured_output_attempt_bounds",
        "TREQ_REPAIR_PROMPT_BOUNDS": "contract-evidence-repair-prompt-bounds.html#ce-coverage-treq_repair_prompt_bounds",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in resilience_trace_routes.items()
        ),
        "Traceability Reader routes Resilience REQ/TREQ contracts to first-class Contract Evidence pages",
    )
    security_trace_routes = {
        "REQ_SENSITIVE_DATA_PROTECTION": "contract-evidence-sensitive-data-protection.html#ce-coverage-req_sensitive_data_protection",
        "TREQ_RUNTIME_LOG_SAFETY": "contract-evidence-runtime-log-safety.html#ce-coverage-treq_runtime_log_safety",
        "TREQ_VCR_AUTH_REDACTION": "contract-evidence-vcr-auth-redaction.html#ce-coverage-treq_vcr_auth_redaction",
        "TREQ_VCR_REQUEST_CONTENT_REDACTION": "contract-evidence-vcr-request-content-redaction.html#ce-coverage-treq_vcr_request_content_redaction",
        "TREQ_VCR_RESPONSE_CONTENT_REDACTION": "contract-evidence-vcr-response-content-redaction.html#ce-coverage-treq_vcr_response_content_redaction",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in security_trace_routes.items()
        ),
        "Traceability Reader routes Data Safety REQ/TREQ contracts to their first-class Contract Evidence pages",
    )
    provider_trace_routes = {
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_OPENAI_ADAPTER_BOUNDARY": "contract-evidence-openai-adapter-boundary.html#ce-coverage-treq_openai_adapter_boundary",
        "TREQ_QWENCHAT_ADAPTER_BOUNDARY": "contract-evidence-qwenchat-adapter-boundary.html#ce-coverage-treq_qwenchat_adapter_boundary",
        "TREQ_AISTUDIO_ADAPTER_BOUNDARY": "contract-evidence-aistudio-adapter-boundary.html#ce-coverage-treq_aistudio_adapter_boundary",
        "TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY": "contract-evidence-gemini-webapi-adapter-boundary.html#ce-coverage-treq_gemini_webapi_adapter_boundary",
        "TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY": "contract-evidence-google-genai-adapter-boundary.html#ce-coverage-treq_google_genai_adapter_boundary",
        "REQ_ASYNC_PROVIDER_EXECUTION": "contract-evidence-async-provider-execution.html#ce-coverage-req_async_provider_execution",
        "REQ_RESPONSE_NORMALIZATION": "contract-evidence-response-normalization.html#ce-coverage-req_response_normalization",
        "TREQ_USAGE_NORMALIZATION": "contract-evidence-usage-normalization.html#ce-coverage-treq_usage_normalization",
        "REQ_PROVIDER_ERROR_BOUNDARY": "contract-evidence-provider-error-boundary.html#ce-coverage-req_provider_error_boundary",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in provider_trace_routes.items()
        ),
        "Traceability Reader routes Provider REQ/TREQ contracts to first-class Contract Evidence pages",
    )
    session_trace_routes = {
        "REQ_SESSION_LIFECYCLE": "contract-evidence-session-lifecycle.html#ce-coverage-req_session_lifecycle",
        "REQ_SESSION_PERSISTENCE": "contract-evidence-session-persistence.html#ce-coverage-req_session_persistence",
        "TREQ_SESSION_SERIALIZATION": "contract-evidence-session-serialization.html#ce-coverage-treq_session_serialization",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in session_trace_routes.items()
        ),
        "Traceability Reader routes Session Requirement/TREQ contracts to their first-class Contract Evidence pages",
    )
    developer_trace_routes = {
        "REQ_PUBLIC_API_SURFACE": "contract-evidence-public-api-surface.html#ce-coverage-req_public_api_surface",
        "REQ_EXAMPLE_IMPORT_SAFETY": "contract-evidence-example-import-safety.html#ce-coverage-req_example_import_safety",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in developer_trace_routes.items()
        ),
        "Traceability Reader routes Developer contracts to the accepted parent Contract Evidence pages",
    )
    structured_trace_routes = {
        "REQ_STRUCTURED_TEXT_OUTPUT": "contract-evidence-structured-text-output.html#ce-coverage-req_structured_text_output",
        "REQ_DOCUMENT_INPUT": "contract-evidence-document-input.html#ce-coverage-req_document_input",
        "REQ_IMAGE_INPUT": "contract-evidence-image-input.html#ce-coverage-req_image_input",
        "REQ_VIDEO_INPUT": "contract-evidence-video-input.html#ce-coverage-req_video_input",
        "REQ_STRUCTURED_SCHEMA_CONTRACT": "contract-evidence-structured-schema-contract.html#ce-coverage-req_structured_schema_contract",
        "REQ_MULTIMODAL_CONTENT_NORMALIZATION": "contract-evidence-multimodal-content-normalization.html#ce-coverage-req_multimodal_content_normalization",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in structured_trace_routes.items()
        ),
        "Traceability Reader routes Rich input/output contracts to their accepted Contract Evidence pages",
    )
    check(
        "Assurance reading path" in verification_page
        and "Requirements and Technical requirements with an accepted Verification Profile" in verification_page
        and "unprofiled contracts do not claim one yet" in verification_page,
        "Verification overview documents Traceability Reader as the honest Contract Evidence entry path",
    )

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

    index_page = (HTML / "index.html").read_text()
    check('href="mutation-analysis.html"' in health_page, "Health: portal navigation links Mutation Analysis")
    check(
        'href="verification-health-map.html"' in index_page
        and "Verification Health Map" in index_page
        and "verification-depth-map" not in index_page
        and "Verification Depth Map" not in index_page
        and "verification-depth-map" not in (BRIDGE.parent / "docs/index.md").read_text()
        and not (BRIDGE.parent / "docs/verification-depth-map.md").exists()
        and not (HTML / "verification-depth-map.html").exists()
        and not (HTML / "verification-map.html").exists(),
        "portal navigation exposes the Verification Health Map as a native document; the Verification Depth Map and the "
        "Verification Map prototype are retired into it, with no source, navigation entry or page left",
    )
    check(
        'href="specification-map.html"' not in index_page
        and 'href="specification-health.html"' not in index_page,
        "portal navigation no longer exposes legacy Specification Map/Health pages",
    )
    # One model feeds the page: health's verdicts and, beside them, the measures' facts.
    map_model_match = re.search(r"const model=(\{.*?\});\n// Health judges", health_page, flags=re.DOTALL)
    map_model = json.loads(map_model_match.group(1)) if map_model_match else {}
    check(
        set(map_model) == {"health", "depth"},
        "Verification Health Map embeds one model: its layered health and its measures' depth facts",
    )
    health_model = map_model.get("health") or {}
    health_layers = (health_model.get("summary") or {}).get("layers") or {}
    health_layer_keys = ("overall", "execution", "coverage", "faults", "evidence", "assurance")
    check(
        set(health_layers) == set(health_layer_keys),
        "Verification Health Map exposes Overall, Execution, Coverage, Faults, Evidence, and Assurance layers",
    )
    health_rows = {
        row.get("id"): row
        for row in health_model.get("rows") or []
        if row.get("id")
    }
    invalid_config_health = health_rows.get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    check(
        ((invalid_config_health.get("layers") or {}).get("execution") or {}).get("status") == "passed"
        and ((invalid_config_health.get("layers") or {}).get("overall") or {}).get("status") == "failed",
        "Health Map distinguishes passing execution from failing canonical assurance for REQ_INVALID_CONFIGURATION_ERRORS",
    )
    invalid_layers = invalid_config_health.get("layers") or {}
    check(
        any(metric.get("label") == "Tests" and int(metric.get("total") or 0) > 0
            for metric in ((invalid_layers.get("execution") or {}).get("metrics") or []))
        and any(metric.get("label") == "Fault groups" and int(metric.get("total") or 0) > 0
                for metric in ((invalid_layers.get("faults") or {}).get("metrics") or []))
        and any(metric.get("label") == "TREQ support" and int(metric.get("total") or 0) > 0
                for metric in ((invalid_layers.get("assurance") or {}).get("metrics") or [])),
        "Verification Health Map exposes numeric drilldown metrics in cell hover data",
    )

    # Own marks: every node carries only the checks that belong to it; child verdicts are not repainted.
    health_children: dict[str, list[dict[str, Any]]] = {}
    for row in (health_model.get("rows") or [])[1:]:
        health_children.setdefault(str(row.get("parent") or ""), []).append(row)

    def health_subtree(row: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [row]
        for child in health_children.get(str(row.get("id")), []):
            rows.extend(health_subtree(child))
        return rows

    def own_status(row: dict[str, Any], key: str) -> str:
        return str(((row.get("own") or {}).get(key) or {}).get("status") or "")

    def canonical_status(row: dict[str, Any], key: str) -> str:
        return str(((row.get("layers") or {}).get(key) or {}).get("status") or "")

    check(
        bool(health_rows)
        and all(
            own_status(row, key) in {"passed", "failed", "na"}
            for row in health_rows.values()
            for key in health_layer_keys
        ),
        "Verification Health Map gives every node an own PASS / FAIL / N/A status in every layer",
    )
    hidden_failures = [
        (row_id, key)
        for row_id, row in health_rows.items()
        for key in health_layer_keys
        if canonical_status(row, key) == "failed"
        and not any(
            own_status(item, source) == "failed"
            for item in health_subtree(row)
            for source in (("assurance", "overall") if key == "assurance" else (key,))
        )
    ]
    check(
        not hidden_failures,
        f"Health Map never hides a canonical FAIL: every failing branch contains an own failure mark {hidden_failures[:5]}",
    )
    orphan_marks = []
    for row_id, row in health_rows.items():
        for key in health_layer_keys:
            if own_status(row, key) != "failed":
                continue
            current: dict[str, Any] | None = row
            while current:
                if canonical_status(current, key) != "failed":
                    orphan_marks.append((row_id, key, current.get("id")))
                    break
                current = health_rows.get(str(current.get("parent") or "")) if current.get("parent") else None
    check(
        not orphan_marks,
        f"every own failure mark sits inside a canonically failing branch {orphan_marks[:5]}",
    )
    unattributed = [
        (row_id, key)
        for row_id, row in health_rows.items()
        for key in health_layer_keys
        if ((row.get("own") or {}).get(key) or {}).get("unattributed")
    ]
    check(
        not unattributed,
        f"all current Health Map failures are attributed to a concrete own check {unattributed[:5]}",
    )
    check(
        all(
            own_status(row, "faults") == "na"
            for row in health_rows.values()
            if row.get("level") in {"product", "goal", "feature"}
        )
        and all(
            own_status(row, "assurance") == "na"
            for row in health_rows.values()
            if row.get("level") in {"requirement", "treq"}
        ),
        "fault groups belong to contracts and Assurance support stays with the children that cause it",
    )
    check(
        all(
            int((health_layers.get(key) or {}).get("failing", -1))
            == sum(own_status(row, key) == "failed" for row in health_rows.values())
            and (health_layers.get(key) or {}).get("status")
            == canonical_status((health_model.get("rows") or [{}])[0], key)
            for key in health_layer_keys
        ),
        "layer cards count exactly the red marks on the map and keep the canonical system verdict",
    )
    # Each layer answers its own question: a missing scenario is a coverage gap (not a
    # failed execution), absent evidence is not "untrustworthy" evidence, and a test
    # result counts once, for the criterion it was written for.
    upper_facts_for_map = json.loads((HTML / "upper-assurance-facts.json").read_text())
    upper_entities = {
        **{entity["id"]: entity for entity in (upper_facts_for_map.get("features") or {}).values()},
        **{entity["id"]: entity for entity in (upper_facts_for_map.get("goals") or {}).values()},
    }
    execution_without_failed_run = [
        entity_id
        for entity_id, entity in upper_entities.items()
        if own_status(health_rows.get(entity_id) or {}, "execution") == "failed"
        and not any(
            row.get("result") != "passed"
            for section in entity.values()
            if isinstance(section, dict)
            for criterion in section.get("criteria") or []
            for row in criterion.get("rows") or []
        )
    ]
    tool_goal = health_rows.get("GOAL_TOOL_ORCHESTRATION") or {}
    check(
        not execution_without_failed_run
        and own_status(tool_goal, "coverage") == "failed"
        and own_status(tool_goal, "execution") != "failed",
        f"Execution reports only scenarios that ran; a missing scenario stays a Coverage gap {execution_without_failed_run}",
    )
    monitor_facts_for_map = json.loads((HTML / "requirement-monitor-facts.json").read_text())
    evidence_without_retained_rows = [
        contract_id
        for contract_id, contract in (monitor_facts_for_map.get("contracts") or {}).items()
        if not any((contract.get("coverage_actual") or {}).values())
        and own_status(health_rows.get(contract_id) or {}, "evidence") != "na"
    ]
    check(
        not evidence_without_retained_rows,
        f"Evidence quality judges only retained evidence; targets without evidence stay Coverage gaps {evidence_without_retained_rows}",
    )
    junit_bindings: dict[str, dict[str, str]] = {}
    for testcase in ET.parse(ROOT / "test-results/pytest-junit.xml").getroot().iter("testcase"):
        testcase_props = {
            prop.attrib.get("name"): prop.attrib.get("value")
            for prop in testcase.findall("./properties/property")
        }
        testcase_nodeid = (
            f"{(testcase.attrib.get('classname') or '').replace('.', '/')}.py::"
            f"{testcase.attrib.get('name') or ''}"
        )
        junit_bindings[testcase_nodeid] = {
            "coverage_item": (testcase_props.get("coverage_item") or "").strip(),
            "assurance_item": (testcase_props.get("assurance_item") or "").strip(),
            "fault_challenge": "yes" if (testcase_props.get("fault_items") or "").strip() else "",
        }
    criterion_owners = {
        criterion_id: owner
        for contract in (monitor_facts_for_map.get("contracts") or {}).values()
        for criterion_id, owner in ((contract.get("target") or {}).get("criterion_contracts") or {}).items()
    }
    needs_versions = json.loads((HTML / "needs.json").read_text()).get("versions") or {}
    needs_current = next(iter(needs_versions.values()), {}).get("needs") or {}
    linked_tests: dict[str, set[str]] = {}
    for need in needs_current.values():
        if need.get("type") != "testcase" or not need.get("nodeid"):
            continue
        for value in need.get("verifies") or []:
            for linked_id in re.findall(r"T?REQ_[A-Z0-9_]+", str(value)):
                linked_tests.setdefault(linked_id, set()).add(str(need["nodeid"]))
    attribution_errors = []
    for contract_id in monitor_facts_for_map.get("contracts") or {}:
        owned = unbound_count = 0
        for nodeid in linked_tests.get(contract_id, set()):
            binding = junit_bindings.get(nodeid) or {}
            owner = criterion_owners.get(binding.get("coverage_item") or "")
            if binding.get("assurance_item") or (owner and owner != contract_id):
                continue
            owned += 1
            unbound_count += 0 if owner or binding.get("fault_challenge") else 1
        row = health_rows.get(contract_id) or {}
        execution_metrics = ((row.get("own") or {}).get("execution") or {}).get("metrics") or []
        shown = sum(int(metric.get("total") or 0) for metric in execution_metrics if metric.get("label") == "Tests")
        shown_unbound = int((((row.get("own") or {}).get("coverage") or {}).get("unbound_tests")) or 0)
        if shown != owned or shown_unbound != unbound_count:
            attribution_errors.append((contract_id, shown, owned, shown_unbound, unbound_count))
    check(
        not attribution_errors,
        f"each test result counts once, for the criterion it was written for; unbound linked tests are surfaced {attribution_errors[:3]}",
    )
    domain_spec = importlib.util.spec_from_file_location(
        "validator_assurance_domain", BRIDGE / "assurance_monitor_domain.py"
    )
    assert domain_spec is not None and domain_spec.loader is not None
    assurance_domain = importlib.util.module_from_spec(domain_spec)
    domain_spec.loader.exec_module(assurance_domain)
    unchallenged = assurance_domain.fault_state(
        {"fault_actual": {"classes": {}, "groups": {}}, "target": {}},
        {"label": "Architecture", "items": [{"id": "architecture.layer-bypass", "state": "required"}]},
        {},
    )
    check(
        unchallenged["status"] == "NOT MET"
        and unchallenged["detection_status"] == "N/A"
        and unchallenged["detection_actual"] is None
        and "<span>Detection</span><strong>—</strong><i></i>"
        in (HTML / "contract-evidence-config-cache-invalidation.html").read_text(),
        "fault detection is undefined (—) when nothing was challenged, while the unchallenged group still fails",
    )
    # --- Infrastructure honesty audit (MAP-P20) ---------------------------------
    adapter_source = (BRIDGE / "build-mutation-report-prototype.py").read_text()
    impl_campaign_path = ROOT / "test-results/implementation-faults/campaign.json"
    impl_campaign = load(impl_campaign_path) if impl_campaign_path.exists() else {}
    class_map = impl_campaign.get("class_by_operator") or {}
    check(
        impl_campaign.get("engine", {}).get("name") == "pytest-gremlins"
        and class_map.get("comparison") == "impl.comparison"
        and class_map.get("boundary") == "impl.boundary"
        and class_map.get("boolean") == "impl.control-flow"
        and class_map.get("return") == "impl.control-flow",
        "Implementation fault campaign is retained and maps native operator families onto all three Implementation classes",
    )
    full_pytest_plugin = BRIDGE / "pytest_plugins/gremlins_full_pytest.py"
    check(
        full_pytest_plugin.exists()
        and "build_lightweight_command" in full_pytest_plugin.read_text()
        and "IMPL_FAULTS.engine_command" in adapter_source
        and '"--with","pytest-gremlins","pytest"' not in adapter_source,
        "every gremlins run executes each mutant with full pytest, never the fixture-less lightweight runner",
    )
    check(
        'class_actual["impl.control-flow"]={"exercised":False' not in adapter_source,
        "impl.control-flow is measured, not hard-coded as unchallenged",
    )
    campaign_engine = impl_campaign.get("engine_configuration") or {}
    campaign_entries = impl_campaign.get("contracts") or {}
    out_of_scope = []
    for contract_id, entry in campaign_entries.items():
        allowed = {
            (path, int(line))
            for path, lines in ((entry.get("plan") or {}).get("attributable_lines") or {}).items()
            for line in lines
        }
        report_path = ROOT / str((entry.get("run") or {}).get("report_path") or "")
        rows = (load(report_path).get("results") or []) if report_path.is_file() else []
        for row in rows:
            try:
                relative = str(Path(str(row.get("file_path"))).resolve().relative_to(ROOT.resolve()))
            except ValueError:
                relative = str(row.get("file_path"))
            if (relative, int(row.get("line_number") or -1)) not in allowed:
                out_of_scope.append(f"{contract_id}:{relative}:{row.get('line_number')}")
    check(
        campaign_engine.get("scope") == "attributable @impl lines only"
        and bool(campaign_entries)
        and not out_of_scope,
        f"the campaign executes only mutants on each contract's attributable @impl lines: {out_of_scope[:4]}",
    )
    check(
        all(
            entry.get("engine") == campaign_engine
            and entry.get("plan_key")
            and entry.get("shared_inputs_sha256") == impl_campaign.get("shared_inputs_sha256")
            and isinstance(entry.get("inputs"), dict)
            and entry.get("inputs")
            for entry in campaign_entries.values()
        )
        and "def retained_campaign_entry_state" in adapter_source
        and '"--full"' in adapter_source,
        "every retained contract result carries the engine, scope, tests and input digests it is reused against",
    )
    gremlins_qualification = (evidence_qualification.get("producers") or {}).get("PRODUCER_PYTEST_GREMLINS") or {}
    gremlins_control = gremlins_qualification.get("control") or {}
    gremlins_strong = gremlins_control.get("strong") or {}
    check(
        gremlins_qualification.get("status") == "QUALIFIED"
        and ((evidence_qualification.get("producers") or {}).get("PRODUCER_IMPLEMENTATION_FAULT_ADAPTER") or {}).get("status") == "QUALIFIED"
        and (gremlins_control.get("weak") or {}).get("caught") == 0
        and (gremlins_control.get("scoped") or {}).get("same_as_full_run") is True
        and int(gremlins_strong.get("faults") or 0) > 0
        and gremlins_strong.get("caught") == gremlins_strong.get("faults"),
        "mutation engine and class projection are qualified: assert-nothing fixture/param/BDD tests catch no mutant, and a scoped run reproduces the full run",
    )
    impl_rows = [
        (contract_id, class_id, row)
        for contract_id, contract in (monitor_facts.get("contracts") or {}).items()
        for class_id, row in ((contract.get("fault_actual") or {}).get("classes") or {}).items()
        if class_id.startswith("impl.")
    ]
    campaign_states = {}
    for _, _, row in impl_rows:
        campaign_states[row.get("campaign_state")] = campaign_states.get(row.get("campaign_state"), 0) + 1
    check(
        bool(impl_rows)
        and all(row.get("campaign_state") and row.get("basis") for _, _, row in impl_rows)
        and not set(campaign_states) - {"current", "blocked", "not_applicable"},
        f"every Implementation class comes from a current campaign or an explained block: {campaign_states}",
    )
    false_detection = [
        f"{contract_id}:{class_id}"
        for contract_id, class_id, row in impl_rows
        if row.get("detected")
        and row.get("source") == "implementation_fault_campaign"
        and not (int(row.get("judged") or 0) > 0 and row.get("killed") == row.get("judged"))
    ]
    check(not false_detection, f"an Implementation class is detected only when every attributable fault is caught: {false_detection[:4]}")
    check(
        any(class_id == "impl.control-flow" and row.get("exercised") for _, class_id, row in impl_rows),
        "impl.control-flow is actually challenged for real contracts",
    )
    unexplained = [
        f"{contract_id}:{class_id}"
        for contract_id, contract in (monitor_facts.get("contracts") or {}).items()
        for class_id, row in ((contract.get("fault_actual") or {}).get("classes") or {}).items()
        if not row.get("basis")
    ]
    check(not unexplained, f"every fault class states why it is caught, missed, or not challenged: {unexplained[:4]}")
    model_records = depth_facts.get("model_validation_records") or {}
    check(
        bool(model_records)
        and "def derive_model_validation_records" in adapter_source
        and all(row.get("ms_validation") in {"l0", "l2"} for row in model_records.values())
        and all((row.get("ms_validation") == "l2") == bool(row.get("calibration")) for row in model_records.values()),
        "M&S validation is derived from the graph: L2 exactly when a current calibrating experiment exists, otherwise L0",
    )
    l0_cells = []
    for contract_id, contract in (monitor_facts.get("contracts") or {}).items():
        for coverage_target in (contract.get("target") or {}).get("coverage") or []:
            if str(coverage_target.get("ms_validation_target") or "").upper() == "L0":
                state = assurance_domain.cell_state(contract, coverage_target)
                l0_cells.append((contract_id, state["ms_status"], state["ms_applicable_count"]))
    check(
        bool(l0_cells) and all(status == "N/A" for _, status, _ in l0_cells),
        "a vacuous L0 model-validation target is shown as not required, never as a pass",
    )
    run_inputs_binding = evidence_provenance.get("inputs") or {}
    check(
        run_inputs_binding.get("run_bound") is True
        and "def snapshot_run_binding" in adapter_source
        and "def probe_env" in adapter_source,
        "the freshness baseline is the retained run's own session-start snapshot, and probes cannot overwrite it",
    )
    primary_monitor_page = (HTML / "verification-assurance.html").read_text()
    check(
        "fault-class-row" in primary_monitor_page
        and "Not caught:" in primary_monitor_page
        and "impl.control-flow" in primary_monitor_page,
        "the fault inspector lists each required class with its state, plain reason, and surviving mutants",
    )

    goal_short_labels = {
        row_id: row.get("short")
        for row_id, row in health_rows.items()
        if row.get("level") == "goal"
    }
    check(
        bool(goal_short_labels)
        and goal_short_labels.get("GOAL_ROUTING_RELIABILITY") == "Routing reliability"
        and all(label and len(str(label)) <= 32 for label in goal_short_labels.values()),
        "Goal containers use concise names derived from their authored IDs; full outcomes stay in hover",
    )

    d3_hierarchy_path = BRIDGE / "vendor/d3-hierarchy-3.1.2/d3-hierarchy.min.js"
    d3_hierarchy_source = d3_hierarchy_path.read_text() if d3_hierarchy_path.exists() else ""
    check(
        d3_hierarchy_path.exists()
        and hashlib.sha256(d3_hierarchy_path.read_bytes()).hexdigest()
        == "a8771380454be89ec5ffe9a6396ba7c247081e348ae740dc9cb9629abd4c0e43"
        and (BRIDGE / "vendor/d3-hierarchy-3.1.2/LICENSE").exists()
        and d3_hierarchy_source in health_page,
        "Verification Health Map inlines the pinned, licensed d3-hierarchy 3.1.2 layout verbatim",
    )
    check(
        "plotly" not in health_page.lower()
        and "cdn.plot.ly" not in health_page
        and 'data-map-layer="' in health_page
        and "d3.treemap().size([width,map.height]).tile(tile)" in health_page
        and "const map=mapTreemap(tree.root,tree.children,o.dots?21:10);" in health_page
        and "tiles:{dots:true," in health_page
        and "d3.treemapBinary" in health_page,
        "Verification Health Map renders one order-preserving d3-hierarchy treemap and switches it between layers without Plotly",
    )
    check(
        "Click → monitor" not in health_page
        and "Select a health layer." not in health_page
        and 'class="tf-map-help"' in health_page
        and '["execution","Execution","Did the tests and scenarios that ran pass?"]' in health_page
        and '["faults","Fault model",' in health_page
        and '["evidence","Evidence quality",' in health_page
        and '" of "+applicableOf(key)+" fail"' in health_page
        and "tiles.thumb=(leaf,mark)=>map.thumb(" in health_page
        and 'aria-describedby="tf-map-help-' in health_page,
        "layer cards show the verdict, the number of red marks, a mini-map, and one-sentence help",
    )
    check(
        "function layerOrder(){" in health_page
        and ".sort((a,b)=>failingOf(b)-failingOf(a))" in health_page
        and 'passing:rest.filter(key=>verdictOf(key)==="passed")' in health_page
        and 'class="tf-map-group pinned"' in health_page
        and ".tf-map-group:not(.pinned)+.tf-map-group::before" in health_page
        and '{tone:"failed",icon:"fa-circle-xmark",label:"Failing",keys:order.failing}' in health_page
        and 'data-map-scroll="1"' in health_page
        and "grid-template-columns:repeat(6,minmax(0,1fr))" not in health_page,
        "layer strip stays one scrollable row: Overall first, failing layers by red marks, passing layers in their order behind a pass line, and the scroll edges count hidden failing layers",
    )
    check(
        '<div class="tf-map-table" id="tf-map-table" role="dialog" aria-label="All health layers" hidden>' in health_page
        and 'aria-controls="tf-map-table"' in health_page
        and 'role="listbox"' in health_page
        and 'data-map-row="' in health_page
        and "function pick(key,leaf,pointer){" in health_page
        and "entry.link.focus()" in health_page,
        "the all-layers table stays hidden until asked for; a row opens its layer's map and a contract cell opens that contract on the map",
    )
    check(
        'id="tf-map-rings"' in health_page
        and "rings.draw=(frame,force)=>{" in health_page
        and "function ringBands(outer){" in health_page
        and "const order=layerOrder(),keys=[...order.failing,...order.passing];" in health_page
        and '"data-map-ring":item.key' in health_page
        and 'if(view.form==="rings")return ringSets[view.ring].thumb();' in health_page
        and 'ringList.forEach(rings=>rings.svg.toggleAttribute("hidden",!(view.form==="rings"&&rings===ringSets[view.ring])));' in health_page
        and "card.show(hoverKey(entry),()=>cardHtml(entry),entry.anchor,entry,immediate)" in health_page
        and 'const projectionOf=entry=>entry.layer||(entry.radial?entry.set.projection:page.tiled);' in health_page,
        "Overall shows the whole system at once: goal, capability and contract rings around the verdict, one ring per layer in strip order; a ring name opens that layer's map and a ring cell opens that layer's evidence",
    )
    health_insights = health_model.get("insights") or {}
    health_causes = health_insights.get("causes") or {}
    check(
        'FACETS["why-"+key]={label:"Why "+label+" fails",title:"Why it fails"' in health_page
        and "function applyFocus(){" in health_page
        and "function whyLine(row,key){" in health_page
        and 'id="tf-health-causes"' not in health_page
        and all(
            {row_id for cause in health_causes.get(key, []) for row_id in cause.get("ids", [])}
            == {
                row_id
                for row_id, row in health_rows.items()
                if ((row.get("own") or {}).get(key) or {}).get("status") == "failed"
            }
            for key in health_layer_keys[1:]
        )
        and all(cause.get("label") and cause.get("hint") is not None for causes in health_causes.values() for cause in causes),
        "every red mark of every layer is explained by at least one named cause; the causes filter the map from the side panel and show in the hover card",
    )
    contract_evidence_pages = sorted(HTML.glob("contract-evidence-*.html"))
    upper_map_pages = sorted(HTML.glob("assurance-goal-*.html")) + sorted(HTML.glob("assurance-feat-*.html"))
    check(
        "history.replaceState(history.state" in health_page
        and "function readHash(){" in health_page
        and 'window.addEventListener("hashchange",readHash);' in health_page
        and bool(contract_evidence_pages)
        and all(
            all(f"verification-health-map.html#{key}:" in page.read_text() for key in ("overall", "coverage", "faults"))
            for page in contract_evidence_pages
        )
        and bool(upper_map_pages)
        and all("verification-health-map.html#overall:" in page.read_text() for page in upper_map_pages),
        "the map view has an address (#layer:ID); contract, goal and capability pages link back to their place on the map",
    )
    health_builder_source = (BRIDGE / "build-mutation-report-prototype.py").read_text()
    check(
        'id="tf-map-find"' in health_page
        and 'if(event.key==="/"){event.preventDefault();find.open();return}' in health_page
        and 'id="tf-map-stamp"' in health_page
        and '$("tf-map-stamp").innerHTML=mapStamp(o.insights?.run);' in health_page
        and "function mapDelta(delta,key,words){" in health_page
        and 'HEALTH_RUN_SNAPSHOTS=ROOT/"test-results/health-map/runs"' in health_builder_source
        and "if snapshot.get(\"run_id\")!=run_id" in health_builder_source
        and (health_insights.get("run") or {}).get("started_at")
        and "delta" in health_insights,
        "the page names its retained run, finds any goal, capability or contract, and compares with the previous retained run only",
    )
    check(
        '["overall","Overall","Overall health; the rings show which layers fail where."]' in health_page
        and "failing layers sit inside the dashed line, passing ones outside" in health_page
        and "if(rect.bottom<0||rect.top>innerHeight)card.hide(true);else place(rect);" in health_page,
        "Overall help names the rings, the legend explains the pass line, and the hover card follows its tile while the page scrolls",
    )
    # The measures (DEPTH-P34, once the Verification Depth Map): Overall depth as rings or a table, four map
    # projections, and a side panel with the level × boundary matrix and facets. They measure; health judges.
    depth_model = map_model.get("depth") or {}
    check(bool(depth_model.get("rows")), "Verification Health Map embeds its measures' depth model")
    depth_contracts = depth_model.get("contracts") or {}
    depth_req_facts = json.loads((HTML / "requirement-monitor-facts.json").read_text()).get("contracts") or {}
    # Health and the measures run one map: the shared script and styles, then each part's own constant in the pages
    # module, which the page runs after the shared map.
    map_pages_module = (BRIDGE / "assurance_map_pages.py").read_text()
    map_pages_js = map_pages_module.split('MAP_SHARED_JS = r"""', 1)[-1].split('"""', 1)[0]
    map_pages_css = map_pages_module.split('MAP_SHARED_CSS = r"""', 1)[-1].split('"""', 1)[0]
    page_own = {
        name: map_pages_module.split(f'{name.upper()}_MAP_JS = r"""', 1)[-1].split('"""', 1)[0]
        for name in ("health", "depth")
    }
    depth_own_css = map_pages_module.split('DEPTH_MAP_CSS = r"""', 1)[-1].split('"""', 1)[0]

    def depth_expected_detection(contract: dict) -> list[int] | None:
        classes = {
            name: state
            for name, state in (((contract.get("fault_actual") or {}).get("classes")) or {}).items()
            if name.startswith("impl.")
        }
        killed = sum(int(state.get("killed") or 0) for state in classes.values())
        judged = killed + sum(int(state.get("survived") or 0) for state in classes.values())
        return [killed, judged] if judged else None

    check(
        "plotly" not in health_page.lower()
        and not re.search(r'<script[^>]+src="https?://', health_section)
        and "d3.treemap()" in health_section,
        "the page renders with the vendored d3-hierarchy, without Plotly or any remote script",
    )
    check(
        [row.get("id") for row in depth_model.get("rows") or []]
        == [row.get("id") for row in health_model.get("rows") or []],
        "the measures use health's hierarchy and order, so every contract sits in the same place in every view",
    )
    check(
        bool(depth_contracts)
        and set(depth_contracts) == set(depth_req_facts)
        and all(
            depth_contracts[contract_id].get("detect") == depth_expected_detection(contract)
            for contract_id, contract in depth_req_facts.items()
        )
        and all(bool(item.get("detect")) != bool(item.get("reason")) for item in depth_contracts.values()),
        "the measures cover every contract; fault detection is the current campaign's caught-of-judged implementation mutants, and every unmeasured contract says why",
    )
    check(
        all(sum(cell[2] for cell in item.get("cells") or []) == item.get("tests") for item in depth_contracts.values())
        and [cell[:2] for cell in (depth_contracts.get("REQ_ASYNC_PROVIDER_EXECUTION") or {}).get("cells") or []]
        == [["system_integration", "replay"]]
        and "Each test counts once, for the entity" in health_builder_source,
        "each test counts once, for the entity it was written for: goal and capability scenarios do not deepen the contracts they also verify",
    )
    check(
        "Test Strength" not in health_section
        and "verification-test-strength-facts" not in health_section
        and not any(tone in page_own["depth"] + depth_own_css for tone in ("tf-hm-fail", "tf-hm-pass")),
        "the measures drop the legacy mutmut Test Strength projection and use no pass/fail colours",
    )
    check(
        all(f'["{key}","' in health_section for key in ("overall", "level", "boundary", "trust", "detect"))
        and '{key:"table",layer:"overall",projection:"overall",form:"table",label:"Table",ask:"Health and measures per contract"}' in health_section
        and "const VIEWS=o.views;" in health_section
        and 'data-map-view="\'+view.key+\'"' in health_section
        and 'if(!readHash())select(VIEWS[0].key,false);' in health_section
        and 'data-depth-mode="representation"' not in health_page
        and 'mode==="representation"' not in health_page,
        "the measures are views of their layers: Overall's depth rings, the contracts table of both, and four map projections; the page opens on Overall's health; Representation is not a projection",
    )
    check(
        ".tf-map-body{display:flex" in health_section
        and ".tf-map-body.panel-open .tf-map-panel{width:" in health_section
        and ".tf-map-panel{position:sticky" in health_section
        and "panel.inert=!open" in health_section
        and all(f"{key}:{{label:" in health_section for key in ("cell", "producer", "kind", "profile", "detect", "goal")),
        "the level × boundary matrix, the substitutes and the facets sit in a side panel that pushes the view instead of covering it, and filter every view",
    )
    check(
        "const PANELS={" in health_section
        and all(f"{key}:{{title:" in health_section for key in ("overall", "level", "boundary", "trust", "detect"))
        and 'const view=viewOf(key),panel=o.panels[view.key]||(view.form==="table"?{...o.panels[view.projection],help:MAP_TABLE_HELP}:o.panels[view.projection]);' in health_section
        and 'previews:key=>viewOf(key).form!=="table"' in health_section
        and "if(next&&!o.previews(o.view()))next=null;" in health_section
        and "button[data-facet]:not(:disabled)" in health_section,
        "the side panel follows the view: only controls that match what it shows, no hover preview in the table, and empty options are disabled",
    )
    check(
        "const splits=new Map();" in health_section
        and "if(record||wide===undefined)" in health_section
        and "const heightFor=width=>" in health_section
        and "new ResizeObserver(()=>{o.follow(frame.stageWidth());" in health_section
        and ".tf-map-view{display:block;width:100%;height:var(--tf-map-view-h,auto)" in health_section
        and "function fitLegend(){" in health_section
        and 'legend.classList.toggle("tight",' in health_section
        and ".tf-map-legendbar{position:relative;display:flex;" in health_section
        and ".tf-map-legend>.tf-map-over{display:none}" in health_section
        and "box.scrollLeft=left;box.scrollTop=top;" in health_section
        and 'id="tf-map-filters"' in health_section.split('id="tf-map-tools"', 1)[-1].split("</div>", 1)[0],
        "the map keeps one tiling and one height: the side panel narrows it frame by frame, the legend is one line whose overflow opens from a +N, the table keeps its place when it redraws, and a filter, a layer or a view never moves the page",
    )
    check(
        'groups:[["tree","Goal › capability"]' in health_section
        and "const table=mapTable({" in health_section
        and "link.download=o.csv.file;" in health_section
        and 'data-sort="' in health_section
        and 'csv:{file:"verification-health.csv",head:[...H.table.csv.head,...D.table.csv.head]' in health_section
        and "verification-depth.csv" not in health_section,
        "Overall shows as rings or as the contracts table, which filters, groups with aggregates, sorts and downloads one CSV of health and its measures",
    )
    check(
        "const filters=mapFilters({facets,rows:o.filterRows," in health_section
        and "facets:FACETS,panels:PANELS," in health_section
        and "const frame=mapFrame({layout:layoutViews,follow:followStage});" in health_section
        and 'id="tf-map-panel-toggle"' in health_section
        and 'if(event.key==="f"||event.key==="F"){event.preventDefault();filters.setPanel(!filters.open,true);return}' in health_section
        and "const PANELS=Object.fromEntries(LAYERS.map(" in health_page
        and 'const view=viewOf(key),panel=o.panels[view.key]||(view.form==="table"?{...o.panels[view.projection],help:MAP_TABLE_HELP}:o.panels[view.projection]);' in health_page
        and 'VERDICTS=[["failed","Fail"],["passed","Pass"],["na","N/A"]]' in health_page
        and "FACETS[key]={label,options:VERDICTS," in health_page,
        "the Filters panel sits beside the view and follows it: health filters by verdict and by why a layer fails, a measure by what it measures",
    )
    check(
        len(map_pages_js) > 2000
        and map_pages_js in health_section
        and all(len(own) > 2000 for own in page_own.values())
        and page_own["health"] in health_page
        and page_own["depth"] in health_section
        and "function mapPage(o){" in map_pages_js
        and "function mapTiles(svg,tree,o){" in map_pages_js
        and "function mapRings(svg,tree,o){" in map_pages_js
        and "function mapTree(rows){" in map_pages_js
        and all(
            "mapTree(" in own
            and "attach:page=>{map=page}" in own
            and not any(
                name in own
                for name in (
                    "function select(",
                    "function readHash(",
                    "function writeHash(",
                    "function focusRow(",
                    "mapStrip(",
                    "mapFilters(",
                    "mapTable(",
                    "mapFind(",
                    "mapCard(",
                    "mapFrame(",
                    'addEventListener("keydown"',
                    "function ancestors(",
                )
            )
            for own in page_own.values()
        ),
        "health and the measures run one shared map (views, strip, filters, table, hover card, Find, address and keys); each part only describes its layers and draws what it alone knows",
    )
    check(
        "function cardHtml(entry){" in map_pages_js
        and 'mapOpens(row,entry.link.getAttribute("href"))' in map_pages_js
        and "function mapMatrix(o){" in map_pages_js
        and "function mapLegendItem" not in page_own["health"] + page_own["depth"]
        and "const mapLegendItem=" in map_pages_js
        and ".tf-map-sw{" in map_pages_css
        and 'kind:{label:"Kind",' in map_pages_js
        and "function mapKinds(o){" in map_pages_js
        and 'columns:[["name","Contract","Contract, grouped as chosen","name"],...o.table.columns],' in map_pages_js
        and '"id","title","kind","goal","capability",...o.table.csv.head' in map_pages_js
        and "data-cell" not in map_pages_js
        and all(
            "mapMatrix({" in own
            and "mapLegendItem(" in own
            and "says," in own
            and not any(
                fragment in own
                for fragment in (
                    "tf-map-card-head",
                    "Opens <b>",
                    '<button type="button" class="tf-map-mx-cell"',
                    'kind:{label:"Kind"',
                    "mapKinds(",
                    "data-kind=",
                    '["tree","Goal › capability"]',
                    '"id","title","kind","goal","capability"',
                    "tf-health-swatch",
                    "tf-depth-sw",
                    "(()=>{",
                )
            )
            for own in page_own.values()
        ),
        "the shared map builds the hover card, the Overall matrix, legends, swatches, the Kind switch, the Goal filter and the table's first columns in one place; health and the measures give only their own content",
    )
    # A card says where a click goes, named as on that page: the page by the mark's kind, the section by the anchor.
    opens_names = dict(re.findall(r'(\w+):"([^"]+)"', (re.search(r"const MAP_OPENS=\{(.*?)\};", map_pages_js) or re.match("", "")).group(1) or ""))
    section_names = re.findall(r'\["([a-z-]+)","([^"]+)"\]', (re.search(r"const MAP_SECTIONS=\[(.*?)\];", map_pages_js) or re.match("", "")).group(1) or "")

    def page_title(path: Path) -> str:
        match = re.search(r"<title>(.*?)(?: &#8212;| —)", path.read_text())
        return match.group(1).strip().lower() if match else ""

    def section_heading(mark: str) -> str:
        for path in sorted(HTML.glob("contract-evidence-*.html")) + sorted(HTML.glob("assurance-*.html")):
            text = path.read_text()
            found = re.search(r'id="[^"]*' + re.escape(mark) + r'[^"]*"', text)
            if found:
                after = text[found.end() : found.end() + 600].split(">", 1)[-1]
                return " ".join(re.sub(r"<[^>]+>", " ", after).split()).lower()
        return ""

    treq_page = next((path for path in sorted(HTML.glob("contract-evidence-*.html")) if path.read_text().count("<title>Technical Assurance")), None)
    check(
        opens_names.get("requirement", "").lower() == page_title(HTML / "contract-evidence-credential-resolution.html")
        and treq_page is not None
        and opens_names.get("treq", "").lower() == page_title(treq_page)
        and opens_names.get("goal", "").lower() == page_title(next(iter(sorted(HTML.glob("assurance-goal-*.html")))))
        and opens_names.get("feature", "").lower() == page_title(next(iter(sorted(HTML.glob("assurance-feat-*.html")))))
        and opens_names.get("product", "").lower() == page_title(HTML / "assurance-product-system.html")
        and len(section_names) >= 9
        and all(section_heading(mark).startswith(name.lower()) for mark, name in section_names),
        "a hover card says where its click goes in the words of the target page: the page's title and the section's heading",
    )
    check(
        set(health_model) == {"rows", "summary", "insights"}
        and all(not ({"value", "persistent_label", "kind"} & set(row)) for row in health_model.get("rows") or [])
        and all(set(layer) == {"status", "failing", "applicable"} for layer in health_layers.values())
        and "tests" not in depth_model
        and [row.get("id") for row in depth_model.get("rows") or []] == [row.get("id") for row in health_model.get("rows") or []],
        "health and the measures receive the same tree as rows with the product first and carry only the facts the page reads",
    )
    # The Verification Health Map pairs every health verdict with its measures (MAP-P41: the Verification Map
    # prototype became the page, the Depth Map its measures).
    pairs_js = map_pages_module.split('PAIRS_MAP_JS = r"""', 1)[-1].split('"""', 1)[0]
    pairs_views = re.findall(r'\{key:"([^"]+)",layer:"([^"]+)",projection:"([^"]+)",form:"(\w+)"', pairs_js)
    pairs_measures = {projection for _key, _layer, projection, _form in pairs_views} - set(health_layer_keys)
    check(
        bool(health_section)
        and "views:viewsHtml,viewTip:" in health_section
        and all(own in health_section for own in page_own.values())
        and pairs_js in health_section
        and re.findall(r"mapPage\(\w+Map\(", health_section) == ["mapPage(pairsMap("]
        and "mapPage(pairsMap(healthMap(model.health),depthMap(model.depth))).start();" in health_section
        and {layer for _key, layer, _projection, _form in pairs_views} == set(health_layer_keys)
        and all(any(key == layer for key, _layer, _projection, _form in pairs_views) for layer in health_layer_keys)
        and pairs_measures == {"depth", "level", "boundary", "trust", "detect"}
        and 'const MEASURE={depth:"overall",level:"level",boundary:"boundary",trust:"trust",detect:"detect"};' in pairs_js
        and pairs_js.count('label:"Health",') == 6
        and "Verdict" not in pairs_js
        and 'document.getElementById("verification-health-map")?.classList.toggle("tf-pairs-measuring",measured(view.projection))' in pairs_js
        and "#verification-health-map.tf-pairs-measuring{--tf-map-up:var(--tf-map-ring);--tf-map-down:var(--tf-map-ring)}" in health_section
        and "verification-depth-map" not in health_page
        and 'id="verification-map"' not in health_page
        and "def render_health_map_page():" in health_builder_source
        and 'MAP_PAGES.health_map_article(stable_json({"health":health_payload,"depth":depth_payload}),vendored_d3_hierarchy())' in health_builder_source
        and "render_verification_map_page" not in health_builder_source
        and "render_depth_map_page" not in health_builder_source
        and "for retired in RETIRED_MAP_PAGES:" in health_builder_source,
        "the Verification Health Map pairs each health verdict with its measures on one page: every health layer is a "
        "card, its measures are views on its card beside its health, every measure of the former Depth Map is one of "
        "them, a measure outlines Changes without red or green, and the builder writes this one page and removes the "
        "retired Depth Map and Verification Map pages",
    )
    # Kind opens the side panel, the same in every view, rather than a facet repeated in every panel.
    check(
        "const kinds=mapKinds({leaves:tree.leaves,filters});" in map_pages_js
        and 'return{...panel,facets:[...panel.facets,"goal"]};' in map_pages_js
        and 'facets:[...panel.facets,"kind","goal"]' not in map_pages_js
        and 'kind:{label:"Kind",switch:true,options:' in map_pages_js
        and "chip:false" not in map_pages_js
        and 'class="tf-map-kind" data-facet="kind" data-value="' in map_pages_js
        and "(facets[target.dataset.facet].switch?f.only:f.toggle)(target.dataset.facet,target.dataset.value)" in map_pages_js
        and "f.only=(key,value)=>" in map_pages_js
        and "f.matches(row,preview.facet)" in map_pages_js
        and '"Technical requirements","Only technical requirements:' in map_pages_js
        and "const MAP_KIND_ICON={" in map_pages_js
        and map_pages_js.count("mapKindIcon(") >= 3
        and 'id="tf-map-kinds"' in health_section.split('class="tf-map-panel-kinds"', 1)[-1].split('id="tf-map-panel-body"', 1)[0]
        and 'id="tf-map-total"' in health_section.split('id="tf-map-filters"', 1)[-1].split('id="tf-map-panel-toggle"', 1)[0]
        and 'class="tf-map-head"' not in health_section
        and ".tf-map-panel-kinds{margin:0 0 .7rem;padding:0 0 .7rem;border-bottom:1px solid var(--tf-map-line-strong)}" in map_pages_css
        and ".tf-map-kind.hit{" in map_pages_css
        and "box.innerHTML=KINDS.map(" in map_pages_js
        and ".tf-map-kind[aria-pressed=true]{" in map_pages_css,
        "Kind opens the side panel, the same in every view and apart from the view's filters below it: all contracts, requirements or technical requirements, each a tile with its glyph, its name and its count under the other filters, drawn once so it never shifts; its tiles are the options of a switch facet, so pointing at one lights its contracts, a click keeps one kind, and a contract on the map marks its kind; a chosen kind shows as a chip like every filter, the count of what the filters keep sits by the chips, and the card, the table and Find name a kind with the same glyph",
    )
    # A layer's views live on its open card as a slider of their thumbnails; the legend bar holds only the legend.
    pairs_asks = re.findall(r'label:"[^"]+",ask:"([^"]+)"', pairs_js)
    pairs_bar = health_section.split('id="tf-map-legendbar"', 1)[-1].split('id="tf-map-body"', 1)[0]
    knob_rule = map_pages_css.split("\n.tf-map-knob{", 1)[-1].split("}", 1)[0]
    check(
        len(pairs_asks) == len(pairs_views) == 12
        and all(len(ask) <= 40 for ask in pairs_asks)
        and "function viewsHtml(key,lone){" in map_pages_js
        and '<span class="tf-map-views-track" role="radiogroup" aria-label="Views of \'' in map_pages_js
        and '<span class="tf-map-knob" aria-hidden="true"></span>' in map_pages_js
        and '<button type="button" role="radio" class="tf-map-choice" data-map-view="\'+view.key+\'" aria-checked="false"'
        in map_pages_js
        and "const tip=view.ask||view.tip,name=view.label||labelOf(view.layer);" in map_pages_js
        and "function tableThumb(){" in map_pages_js
        and "if(thumb&&thumb.dataset.view!==view)thumb.outerHTML=o.thumb(key);" in map_pages_js
        and '\'<div class="tf-map-tab-wrap" data-map-wrap="\'+key+\'">\'' in map_pages_js
        and "views.inert=!open;" in map_pages_js
        and "function placeKnob(views,instant){" in map_pages_js
        and 'const knobShape=(at,count)=>count===1?" only":at===0?" first":at===count-1?" last":"";' in map_pages_js
        and 'knob.className="tf-map-knob"+knobShape(at,buttons.length);' in map_pages_js
        and "next=list[(step+list.length)%list.length];" in map_pages_js
        and "function mapSpread(rows,tone,titled){" in map_pages_js
        and '<span class="tf-map-ask" title="' in map_pages_js
        and "tone:toneOf," in page_own["health"]
        and "tone,blank,measure,measureHtml,measureGroupHtml," in page_own["depth"]
        and knob_rule.startswith("position:absolute;")
        and "border-radius:0;" in knob_rule
        and ".tf-map-knob.first{border-radius:7px 0 0 7px}" in map_pages_css
        and ".tf-map-knob.last{border-radius:0 7px 7px 0}" in map_pages_css
        and ".tf-map-knob.only{border-radius:7px}" in map_pages_css
        and ".tf-map-tab-wrap.open>.tf-map-views{max-width:calc(var(--tf-map-track-w,508px) + 12px);opacity:1;"
        in map_pages_css
        and "@media(min-width:961px){.tf-map-legendbar:has(+ .tf-map-body.panel-open)"
        "{padding-left:calc(var(--tf-map-panel) + 16px)}}" in map_pages_css
        and "inset 0 -2px 0" not in map_pages_css
        and "tf-map-lens" not in map_pages_js + map_pages_css
        and 'id="tf-map-mode"' not in health_section and "data-lens-scroll" not in health_section
        and 'id="tf-map-legend"' in pairs_bar
        and "<button" not in pairs_bar,
        "a layer's views live on its open card: the card keeps its look and a slider of the views' thumbnails grows out of it, a sunken track whose raised knob glides to the chosen view (only the slider's two ends are rounded, a view between them is square, and the arrow keys move it); the card's own thumbnail shows the view it opens, a view's question is its thumbnail's hint and opens the legend, and the legend bar holds only the legend, which keeps clear of the open panel's column",
    )
    # A narrow page has no room beside the open card; a wide one keeps the card and its views in sight as one.
    check(
        'const narrow=matchMedia("(max-width:640px)");' in map_pages_js
        and "open=!!views&&key===current&&!narrow.matches&&folded!==key;" in map_pages_js
        and "if(fresh){viewsRow.dataset.layer=key;viewsRow.innerHTML=o.views(key,true)}" in map_pages_js
        and 'if(views.length<2&&!lone)return"";' in map_pages_js
        and 'narrow.addEventListener("change",()=>{sync(true);show(o.current())});' in map_pages_js
        and ".tf-map-views-row{display:none}" in map_pages_css
        and "@media(max-width:640px){\n.tf-map-views-row{display:flex;height:60px;" in map_pages_css
        and '<div class="tf-map-views-row" id="tf-map-views-row"></div>' in health_section
        and "const delta=left<start||right-left>end-start?left-start:right>end?right-end:0;" in map_pages_js
        and "if(picked){reveal(picked);return}" in map_pages_js
        and '<span class="tf-map-choice-name" data-name="\'+escapeHtml(name)+\'">' in map_pages_js
        and ".tf-map-choice-name::after{content:attr(data-name);height:0;overflow:hidden;visibility:hidden;"
        "font-weight:750}" in map_pages_css
        and 'class="tf-map-view"' not in map_pages_js,
        "on a page 640 px wide or less the open layer's views take a row of their own under the strip, a lone view too, so the row keeps its height from layer to layer; on a wider page the open card and its views come into sight as one, a card too wide for the strip keeps its start in sight, a view picked on the slider leaves the strip where it is, and every name keeps room for its bold width so choosing a view never changes the slider's width",
    )
    # What the references taught the slider: views that fold at once and at the pace they grow, a strip that moves
    # once, one Tab stop, dots on closed cards, equal views and a knob that can be dragged.
    check(
        'views.style.setProperty("--tf-map-track-w",track.offsetWidth+"px");' in map_pages_js
        and "document.fonts?.ready?.then(()=>sync(true));" in map_pages_js
        and "inStrip" not in map_pages_js
        and ".held" not in map_pages_css
        and "grown=setTimeout(()=>{syncBar();" in map_pages_js
        and "if(box.right<=view.left+pinWidth||box.left>=view.right)reveal(tab);" in map_pages_js
        and 'role="radiogroup"' in map_pages_js
        and "button.tabIndex=on&&active?0:-1;" in map_pages_js
        and "const step={ArrowRight:at+1,ArrowDown:at+1,ArrowLeft:at-1,ArrowUp:at-1,Home:0,End:list.length-1}[event.key];"
        in map_pages_js
        and '<span class="tf-map-dots" aria-hidden="true">' in map_pages_js
        and 'wrap.querySelectorAll("[data-dot]").forEach(dot=>dot.classList.toggle("on",dot.dataset.dot===view));'
        in map_pages_js
        and '" Views: "' in map_pages_js
        and ".tf-map-dots{grid-column:2;grid-row:3;align-self:end;justify-self:center;" in map_pages_css
        and ".tf-map-tab-wrap.open .tf-map-dots{opacity:0}" in map_pages_css
        and "@media(max-width:640px){.tf-map-tab[aria-selected=true]>.tf-map-dots{opacity:0}}" in map_pages_css
        and ".tf-map-views-track{position:relative;flex:none;display:grid;grid-auto-flow:column;grid-auto-columns:1fr;"
        in map_pages_css
        and ".tf-map-choice .tf-map-thumb{width:54px;height:30px}" in map_pages_css
        and '<svg class="tf-map-thumb tabular"' in map_pages_js
        and 'class="tf-map-thumb table"' not in map_pages_js
        and "function knobDown(event){" in map_pages_js
        and "function knobMove(event){" in map_pages_js
        and "function knobUp(event){" in map_pages_js
        and 'if(event.type==="click"&&dropped){dropped=false;return true}' in map_pages_js
        and ".tf-map-knob.pressed{scale:.94}" in map_pages_css
        and ".tf-map-views:not(.lone) .tf-map-choice[aria-checked=true]{cursor:grab;touch-action:pan-y}" in map_pages_css,
        "a card's views fold as soon as another card opens, and fold and grow over the same time because a slider is as wide as its track, its padding and its border; the strip moves once, after they have grown and folded, to where everything ends up; the views are a radio group with one Tab stop whose arrow keys go round and whose Home and End go to either end; a closed card with several views shows a dot for each, the one it opens in filled, and names them to a screen reader; every view on a slider has the same width and the same thumbnail frame, the table's thumbnail clear of the theme's table margin; and the knob can be dragged along the track, pressed smaller, landing on the nearest view",
    )
    # A view with nothing to show under the filters fades on its slider and says why, rather than leaving.
    check(
        "function idleNote(view){" in map_pages_js
        and 'if(!view||view.form!=="tiles"||!o.blank)return"";' in map_pages_js
        and "if(!rows.length||!rows.every(row=>o.blank(row,view.projection)))return\"\";" in map_pages_js
        and 'button.classList.toggle("idle",!!note);' in map_pages_js
        and 'if(note)button.setAttribute("aria-description",note);else button.removeAttribute("aria-description");'
        in map_pages_js
        and 'changed:()=>{applyFocus();if(viewOf(page.view).form==="table")table.render();strip.sync();writeHash()}'
        in map_pages_js
        and ".tf-map-choice.idle .tf-map-thumb{opacity:.28;filter:grayscale(1)}" in map_pages_css
        and "function blank(row,key){" in page_own["depth"]
        and 'blank:(row,key)=>status(row,key)==="na",' in page_own["health"]
        and "blank:(row,projection)=>side(projection).blank(as(row,projection),own(projection))," in pairs_js,
        "a map view with nothing to show under the filters, because every contract they keep is blank in it (not measured, no substitute, no passing tests, N/A), stays in its place on its slider, faded, and its hint and its spoken description say why; it can still be chosen, Overall's rings and table never fade, and no contract kept at all fades nothing",
    )
    # Progressive disclosure: a layer's views open part way, a +N shows them all, a second click folds them.
    check(
        "if(current!==lastLayer){lastLayer=current;folded=null;full=null}" in map_pages_js
        and 'if(open&&buttons.findIndex(button=>button.dataset.mapView===view)>0)full=key;' in map_pages_js
        and 'const peek=open&&buttons.length>2&&full!==key&&!wrap.closest(".tf-map-group.pinned");' in map_pages_js
        and "const more=views.length>2&&key!==o.layers[0][0]?" in map_pages_js
        and 'views.style.setProperty("--tf-map-peek-w",Math.round(buttons[1].offsetLeft+buttons[1].offsetWidth/2+1)+"px");'
        in map_pages_js
        and "if(more){full=more.dataset.mapMore;sync();revealGrown(full);return}" in map_pages_js
        and "folded=folded===key?null:key;" in map_pages_js
        and 'if(cut){full=cut.dataset.mapWrap;cut.classList.remove("peek");revealGrown(full)}' in map_pages_js
        and 'wrap.querySelector(".tf-map-tab").setAttribute("aria-expanded",String(open||narrow.matches&&key===current));'
        in map_pages_js
        and 'class="tf-map-views-more" data-map-more="' in map_pages_js
        and ".tf-map-tab-wrap.open.peek>.tf-map-views{max-width:calc(var(--tf-map-peek-w,120px) + 6px)}" in map_pages_css
        and ".tf-map-tab-wrap.peek .tf-map-views-more{opacity:1;visibility:visible}" in map_pages_css
        and "room=80;" in map_pages_js,
        "a card with three views or more opens them part way, except Overall, which always shows all its views: one and a half in sight, the cut one fading under a +N that shows them all; with two views both are in sight; choosing a view past the first, by a click, a key or a drag of the knob, shows them all too, until the card folds or another card opens; a second click on the open card folds its views, its dots showing again, and the next click opens them; another layer starts part way again; on a narrow page the row under the strip keeps every view; and a revealed card keeps clear of the strip's 72 px scroll edges",
    )
    # A failing goal or capability among few draws the eye: a slow ring from its dot, an outline that turns amber.
    health_css = map_pages_module.split('HEALTH_MAP_CSS = r"""', 1)[-1].split('"""', 1)[0]
    check(
        "const judged=entries.filter(entry=>entry.kind!==\"leaf\"&&status(entry.row,key)!==\"na\");" in page_own["health"]
        and 'svg.classList.toggle("tf-health-alert",failing>0&&failing<=Math.max(3,judged.length/4));' in page_own["health"]
        and "#verification-health-map .tf-health-alert .tf-map-dot.failed{stroke:var(--tf-hm-fail);stroke-width:0;"
        "animation:tf-health-ping 2.6s" in health_css
        and "#verification-health-map .tf-health-alert .tf-health-own-failed{animation:tf-health-amber 3.2s ease-in-out infinite}"
        in health_css
        and "@keyframes tf-health-ping{0%{stroke-width:0;stroke-opacity:.8}75%,100%{stroke-width:8px;stroke-opacity:0}}" in health_css
        and "@keyframes tf-health-amber{0%,100%{stroke:var(--tf-hm-fail);filter:none}50%{stroke:var(--tf-hm-alert);" in health_css
        and "@media(prefers-reduced-motion:reduce){#verification-health-map .tf-health-alert .tf-map-dot.failed{stroke-width:5px;"
        in health_css
        and all(part in health_page for part in ("tf-health-ping", "tf-health-amber")),
        "on the map of a layer where few goals or capabilities fail their own check, at most three or a quarter of those judged, each failing one draws the eye without shouting: its dot sends out a slow ring that fades and its outline turns amber and back with a soft glow, while passing marks stay still; where more fail nothing moves, since the red is plain; card thumbnails stay still; with reduced motion a still halo and an amber outline take their place",
    )
    # Its contracts table is Overall's rings unrolled, in the order of the tabs.
    check(
        "function headerHtml(){" in map_pages_js
        and "const pathOf=column=>" in map_pages_js
        and 'cell.style.top=top+"px"' in map_pages_js
        and ".tf-map-list-table .name{position:sticky;left:0;" in map_pages_css
        and "function tableColumns(){" in pairs_js
        and "H.strip.groups().flatMap(group=>group.keys)" in pairs_js
        and '[...D.levels,"tests"]' in pairs_js
        and 'depthColumn("classes",[label])' in pairs_js
        and "groupCells:list=>" in pairs_js
        and "const tableOrder=()=>" in page_own["health"]
        and "countOfChecks" in page_own["health"]
        and all("function groupCell(list,key){" in own for own in page_own.values())
        and "function tableCell(row,key){" in page_own["depth"]
        and "levels:LEVELS" in page_own["depth"]
        and 'if(group==="boundary")return[c.real||"notests"];' in page_own["depth"],
        "the contracts table is Overall's rings unrolled: a column group per layer in the strip's order, each layer's views in tab order with every column of health's and the measures' tables (Overall's depth by test level and own tests, Fault model's classes), a group row that sums every column, and headers and the contract name kept in sight",
    )
    check(
        "const RING_CORE={center:.27,goal:[.29,.355],feature:[.365,.425],rays:.44};" in map_pages_js
        and all("RING_CORE.rays*outer" in own for own in page_own.values())
        and 'kicker:"OVERALL",big:word(verdict),tone:verdict' in page_own["health"]
        and 'kicker:"DEEPEST",big:LEVEL_SHORT[topLevel]' in page_own["depth"]
        and 'id="tf-map-rings"' in health_section
        and 'id="tf-map-tiles"' in health_section,
        "health's and the depth rings share one core (centre, goals, capabilities) and one centre layout; each adds only its own rings beyond it",
    )
    check(
        'PANELS.overall={title:"Layer × health",' in page_own["health"]
        and 'overall:{title:"Test level × boundary",' in page_own["depth"]
        and all("PANELS.table" not in own for own in page_own.values())
        and "const view=viewOf(key),words=o.words(view.projection),legend=o.legend(view.projection);" in map_pages_js
        and "'<span class=\"tf-map-changes-key\"><i class=\"up\"></i>'" in map_pages_js
        and "--tf-map-up:var(--tf-hm-fail-ink);--tf-map-down:var(--tf-hm-pass-ink)" in health_page
        and "--tf-map-up:" not in page_own["depth"] + depth_own_css,
        "Overall's views and its table share one legend and one panel with one matrix per Overall view (layer × health, test level × boundary); Changes outlines up solid and down dashed, red and green only where health judges",
    )
    check(
        "history.replaceState(history.state" in health_section
        and 'addEventListener("hashchange",readHash);' in health_section
        and 'id="tf-map-find"' in health_page
        and 'id="tf-map-copy"' in health_section
        and bool(contract_evidence_pages)
        and all(
            all(f"verification-health-map.html#{view}:" in page.read_text() for view in ("overall/depth", "faults/detect"))
            and "verification-depth-map" not in page.read_text()
            for page in contract_evidence_pages
        ),
        "every view has an address (#view:ID?filters); every Contract Evidence page links to its contract in the depth rings and in the mutants caught",
    )
    check(
        "which is a way of testing and not a score" in health_section
        and 'const BOUNDS=["none","substitute","replay","direct"];' in health_section
        and 'direct:"Direct live"' in health_section,
        "the measures keep the Local → Substitute → Replay → Direct live vocabulary and do not rank the boundary as strength",
    )
    check(
        all(
            sum(case[3] for case in (depth_contracts.get(contract_id) or {}).get("cases") or [])
            == sum(int(criterion.get("declared_count") or 0) for criterion in (contract.get("target") or {}).get("coverage") or [])
            for contract_id, contract in depth_req_facts.items()
        )
        and (depth_contracts.get("REQ_CREDENTIAL_RESOLUTION") or {}).get("cases")
        == [["component", "none", 4, 4], ["system", "none", 1, 1]]
        and "covered/required cases" in health_section,
        "a required cell counts covered/required cases exactly like the Contract Evidence matrix; tests beyond the profile show as +N",
    )
    strip_call = "strip:{groups:layerGroups,card:layerCard,row:layerRow"
    depth_insights = depth_model.get("insights") or {}
    check(
        len(map_pages_js) > 2000
        and len(map_pages_css) > 2000
        and map_pages_js in health_section
        and map_pages_css in health_section
        and strip_call in health_section
        and 'id="tf-map-layerbar"' in health_section
        and 'id="tf-map-table-toggle"' in health_section
        and 'id="tf-map-changes"' in health_section
        and "mapChanges(document.getElementById(\"tf-map-changes\")" in health_section.replace('$("tf-map-changes")', 'document.getElementById("tf-map-changes")')
        and "strip:{row:layerRow,cells:" in page_own["depth"]
        and "strip:{groups:H.strip.groups,card:H.strip.card," in pairs_js,
        "the page runs one shared layer strip, All layers table and Changes: health groups the layers into failing and passing and gives each its card, and a measure adds only its row in the All layers table",
    )
    check(
        "def run_delta(snapshots,schema,stamp,values,compare):" in health_builder_source
        and 'return run_delta(HEALTH_RUN_SNAPSHOTS,"health-map-run-2",stamp,statuses,health_changes)' in health_builder_source
        and 'DEPTH_RUN_SNAPSHOTS=ROOT/"test-results/depth-map/runs"' in health_builder_source
        and "run_delta(DEPTH_RUN_SNAPSHOTS,\"depth-map-run-1\",stamp,depth_values(payload),depth_changes)" in health_builder_source
        and (depth_insights.get("run") or {}).get("started_at") == (health_insights.get("run") or {}).get("started_at")
        and set(depth_insights.get("delta") or {}) >= {"baseline", "layers"}
        and set(health_insights.get("delta") or {}) >= {"baseline", "layers"}
        and all(
            set(change) == {"up", "down"}
            for insights in (health_insights, depth_insights)
            for change in ((insights.get("delta") or {}).get("layers") or {}).values()
        ),
        "Changes compares health and the measures each with its own snapshot of the previous retained run, in one shape: what went up and what went down in every layer",
    )
    health_nav = health_page.split('<main id="main-content"', 1)[0]
    # The theme renders the navigation twice (header and mobile sidebar): Mutation Analysis follows the Health Map in both.
    # The theme separates items with two blank lines and an inserted item brings one more; a longer run of blank lines
    # means a patch landed on top of an earlier one.
    check(
        len(re.findall(r">\s*Verification Health Map\s*</a>", health_nav))
        == len(re.findall(r">\s*Verification Health Map\s*</a>\s*</li>\s*<li[^>]*>\s*<a[^>]*>\s*Mutation Analysis\s*</a>", health_nav))
        > 0
        and "Verification Depth Map" not in health_nav
        and all("\n" * 5 not in page.split('<main id="main-content"', 1)[0] for page in (health_page, index_page)),
        "the Health Map page lists itself once in each portal navigation, Mutation Analysis right after it, and no Depth "
        "Map; patching an already patched navigation adds nothing",
    )
    qualification_harness_source = (BRIDGE / "qualify-evidence-confidence.py").read_text()
    check(
        "'<section id=\"verification-health-map\">\\n<h1>Verification Health Map'" in map_pages_module
        and "f'<style id=\"tf-health-map-style\">\\n{css}\\n</style>\\n'" in map_pages_module
        and re.findall(r"^def (\w+)\(", map_pages_module, flags=re.MULTILINE) == ["map_tools", "map_frame", "map_strip", "health_map_article"]
        and "verification-depth-map" not in map_pages_module
        and '<section id="verification-health-map">' not in health_builder_source
        and "MAP_PAGES.health_map_article(" in health_builder_source
        and health_builder_source.count("MAP_PAGES.") == 1
        and "assurance_map_pages" not in qualification_harness_source
        and "assurance_monitor_ui" not in qualification_harness_source
        and '"assurance_monitor_ui_sha256"' not in health_builder_source
        and all(
            name in qualification_harness_source
            for name in (
                "build-mutation-report-prototype.py",
                "build-requirement-monitor.py",
                "build-upper-assurance-pilot.py",
                "assurance_monitor_domain.py",
                "assurance_monitor_registry.py",
                "implementation_faults.py",
            )
        ),
        "page markup lives outside the evidence-producer fingerprint: the builder passes only facts, every file that computes facts stays fingerprinted",
    )
    layers_block = re.search(r"const LAYERS=\[(.*?)\];", health_page, flags=re.DOTALL)
    layer_tips = re.findall(r'\["(\w+)","[^"]+","([^"]+)"\]', layers_block.group(1) if layers_block else "")
    check(
        len(layer_tips) == len(health_layer_keys)
        and all(len(tip) <= 72 for _key, tip in layer_tips)
        and "const METRIC_LABELS={" in health_page
        and '"Fault groups":"Fault checks passed"' in health_page,
        "layer help and hover labels use short plain-language sentences",
    )
    check(
        'id="tf-map-card"' in health_page
        and "tf-map-lineage" in health_page
        and "tf-hierarchy-overlay" not in health_page
        and "getBoundingClientRect()" in health_page
        and "showTimer=setTimeout" in health_page
        and 'link.addEventListener("focus"' in health_page
        and "Opens <b>" in health_page
        and "tf-health-strip" in health_page,
        "Verification Health Map keeps cell-anchored hover and keyboard focus with lineage, a six-layer strip, and the click destination",
    )
    check(
        'if(candidate.length>=7&&width(candidate)<=max)return candidate' in health_page
        and "fitLabel(node.data.row.short||node.data.row.label" in health_page
        and 'if(kind!=="goal"&&kind!=="feature"&&kind!=="leaf")return;' in health_page
        and 'if(!map.label(node)||room<(kind==="goal"?40:22))map.compact.add(node.data.row.id)' in health_page
        and 'const named=kind!=="leaf"&&!map.compact.has(row.id);' in health_page
        and "slicetext" not in health_page,
        "only Goal and Capability containers carry labels, cut at whole words; a container without room gets a compact header instead of starving its tiles",
    )
    check(
        "const PAD={product:[14,0,0],goal:[8,30,8],feature:[5,24,6],cluster:[2,0,0]};" in health_page
        and "const RADIUS={goal:12,feature:8,leaf:3.5};" in health_page
        and "#verification-health-map .tf-map-goal{fill:var(--tf-map-goal)" in health_page
        and "#verification-health-map .tf-map-feature{fill:var(--tf-map-feature)" in health_page
        and "through.forEach(entry=>tone(entry.shape,entry.value))" in health_page
        and "#verification-health-map .tf-health-own-failed{stroke:var(--tf-hm-fail);stroke-width:1.6}" in health_page
        and "html[data-theme=dark] #verification-health-map{" in health_page
        and "prefers-reduced-motion:reduce" in health_page
        and "LEVEL_COLORS" not in health_page
        and not any(
            re.search(r"stroke-width:(?:8|14)px", body)
            for _selector, body in re.findall(r"([^{}]*\.tf-map-(?:goal|feature)\b[^{}]*)\{([^{}]*)\}", health_page)
        ),
        "Verification Health Map keeps hierarchy in neutral rounded geometry and status only on contracts and own-check marks: no rule for a goal or capability shape draws the thick 8 or 14 px border of the old treemap (a status ring on an own-check dot may grow that wide)",
    )
    check(
        "pst-color-primary" not in health_section
        and ".tf-map-outline{fill:none;stroke:var(--tf-map-ring)" in health_section
        and 'if(view.form==="tiles"&&view.projection!==page.tiled){page.tiled=view.projection;paint(true)}' in health_section
        and ".tf-map-tile{transition:fill" in health_section
        and 'tone(entry.shape,neutral?"na":value);' in health_section
        and "@keyframes tf-map-in" in health_section,
        "map interaction stays neutral (no accent hue); layer switches recolor in place and pass red↔green through neutral gray",
    )
    for name, text in {
        "Health": health_page,
    }.items():
        check(
            'id="tf-map-focus-layout"' in text
            and "bd-sidebar-primary bd-sidebar pst-squeeze" in text
            and 'id="pst-collapse-sidebar-button" aria-expanded="false"' in text
            and ".bd-page-width{max-width:100%}" in text
            and ".bd-main .bd-content .bd-article-container{max-width:100%}" in text,
            f"{name}: map uses native collapsed primary-sidebar rail and full-width article layout",
        )
        check(
            'id="pst-secondary-sidebar"' not in text
            and "sidebar-toggle secondary-toggle" not in text,
            f"{name}: useless secondary sidebar is removed at the page level",
        )

    measurement_contract_ids = {row["contract_id"] for row in depth_facts.get("contracts") or []}
    check(len(measurement_contract_ids) == 63,
          "verification-depth / mutation measurement universe contains all 63 current contracts")
    requirements_text = "\n".join(
        path.read_text() for path in sorted((ROOT / "docs/requirements").glob("*.md"))
    )
    normative_contract_ids = set(re.findall(
        r"^:id:\s+((?:REQ|TREQ)_[A-Z0-9_]+)\s*$", requirements_text, flags=re.MULTILINE
    ))
    check(len(normative_contract_ids) == 63,
          "normative Sphinx-Needs graph contains 63 Requirement/TREQ contracts")
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
          "collectively **13/13 criteria PASS · 16/16 paths**" in manifest and
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
        "assurance_monitor_domain.py",
        "assurance_monitor_registry.py",
        "assurance_monitor_ui.py",
        "assurance_map_pages.py",
        "build-requirement-monitor.py",
        "build-upper-assurance-pilot.py",
        "implementation_faults.py",
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
    check(
        not (BRIDGE / "__pycache__").exists() and not (BRIDGE / "pytest_plugins/__pycache__").exists(),
        "no .ai-bridge __pycache__ debris remains",
    )

    generated_paths = [
        str(path.relative_to(ROOT))
        for path in RESULTS.rglob("*")
        if path.is_file()
    ]
    generated_paths += [
        "docs/_build/html/mutation-analysis.html",
        "docs/_build/html/verification-test-strength-facts.json",
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/verification-assurance.html",
        "docs/_build/html/contract-evidence-request-override-precedence.html",
        "docs/_build/html/contract-evidence-credential-resolution.html",
        "docs/_build/html/contract-evidence-config-installation-coherence.html",
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
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/test-plan.html",
        "docs/_build/html/_static/mutation-test-elements.js",
        "docs/_build/html/evidence-classification-facts.json",
        "test-results/implementation-faults/campaign.json",
    ]
    generated_paths += [
        str(path.relative_to(ROOT))
        for path in (ROOT / "test-results/health-map/runs").glob("*.json")
    ]
    history_glob = "`docs/_build/html/mutation-results/campaign-history/*.json`"
    contract_evidence_glob = "`docs/_build/html/contract-evidence-*.html`"
    health_run_glob = "`test-results/health-map/runs/*.json`"
    missing_artifacts = sorted(
        path
        for path in generated_paths
        if f"`{path}`" not in manifest
        and not (
            path.startswith("docs/_build/html/mutation-results/campaign-history/")
            and path.endswith(".json")
            and history_glob in manifest
        )
        and not (
            path.startswith("docs/_build/html/contract-evidence-")
            and path.endswith(".html")
            and contract_evidence_glob in manifest
        )
        and not (
            path.startswith("test-results/health-map/runs/")
            and path.endswith(".json")
            and health_run_glob in manifest
        )
    )
    check(not missing_artifacts, f"extraction manifest inventories all retained generated artifact classes: {missing_artifacts}")

    check(not (ROOT / "mutants").exists(), "temporary mutmut workspace absent")
    setup = ROOT / "setup.cfg"
    check(not setup.exists() or "[mutmut]" not in setup.read_text(), "temporary mutmut setup config absent")

    # With -z a rename or a copy names its source in the record after its own, which carries no status of its own.
    status = []
    source_follows = False
    for record in subprocess.check_output(
        ["git", "status", "--porcelain", "-z"],
        cwd=ROOT,
        text=True,
    ).split("\0"):
        if source_follows or not record:
            source_follows = False
            continue
        status.append(record)
        source_follows = "R" in record[:2] or "C" in record[:2]
    approved_pilot_sources = {
        ".ai-bridge/build-mutation-report-prototype.py",
        ".ai-bridge/assurance_monitor_domain.py",
        ".ai-bridge/assurance_monitor_registry.py",
        ".ai-bridge/assurance_monitor_ui.py",
        ".ai-bridge/assurance_map_pages.py",
        ".ai-bridge/build-requirement-monitor.py",
        ".ai-bridge/build-upper-assurance-pilot.py",
        ".ai-bridge/monitor-readiness.md",
        ".ai-bridge/system-level-ownership.md",
        ".ai-bridge/mutation-testing-platform-extraction-manifest.md",
        ".ai-bridge/mutation-testing-integration-plan.md",
        ".ai-bridge/qualify-evidence-confidence.py",
        ".ai-bridge/validate-mutation-pilot.py",
        ".ai-bridge/verification-health-map-local-prototype.md",
        ".ai-bridge/verification-depth-map-local-prototype.md",
        ".ai-bridge/implementation_faults.py",
        ".ai-bridge/pytest_plugins/",
        ".ai-bridge/vendor/",
        ".ai-bridge/development-history/",
        ".ai-bridge/exemplars/",
        "docs/index.md",
        "docs/README.md",
        "docs/test-plan.md",
        "docs/verification-health-map.md",
        "docs/verification-depth-map.md",
        "docs/assurance-profiles/",
        "docs/experiments/index.md",
        "docs/requirements/configuration.md",
        "docs/requirements/tools.md",
        "docs/requirements/routing.md",
        "docs/requirements/resilience.md",
        "docs/requirements/security.md",
        "docs/requirements/providers.md",
        "docs/requirements/sessions.md",
        "docs/requirements/developer.md",
        "docs/requirements/structured_output.md",
        "docs/verification-profiles/",
        "features/configuration/overrides.feature",
        "features/configuration/assurance.feature",
        "features/tools/",
        "features/routing/",
        "features/resilience/",
        "features/security/",
        "features/sessions/lifecycle.feature",
        "features/sessions/assurance.feature",
        "features/structured_output/",
        "pyproject.toml",
        "uv.lock",
        "src/llm_router/_api/router.py",
        "src/llm_router/_api/errors.py",
        "src/llm_router/_internal/capabilities/schema.py",
        "src/llm_router/_internal/capabilities/content.py",
        "src/llm_router/_internal/config/validation.py",
        "src/llm_router/_internal/providers/_prompted.py",
        "src/llm_router/_internal/providers/aistudio.py",
        "src/llm_router/_internal/providers/base.py",
        "src/llm_router/_internal/providers/gemini_webapi.py",
        "src/llm_router/_internal/providers/google_genai.py",
        "src/llm_router/_internal/providers/openai_compatible.py",
        "src/llm_router/_internal/providers/qwenchat.py",
        "src/llm_router/_internal/providers/retry.py",
        "src/llm_router/_internal/runtime/executor.py",
        "src/llm_router/_internal/runtime/limiter.py",
        "src/llm_router/_internal/runtime/router.py",
        "src/llm_router/_internal/runtime/routes.py",
        "src/llm_router/_internal/runtime/tracing.py",
        "tests/conftest.py",
        "tests/llm_router/conftest.py",
        "features/responses/public_contract.feature",
        "features/providers/",
        "tests/llm_router/bdd/providers/",
        "tests/llm_router/bdd/responses/test_public_contract.py",
        "tests/llm_router/bdd/configuration/test_overrides.py",
        "tests/llm_router/bdd/configuration/test_configuration_assurance.py",
        "tests/llm_router/bdd/execution/test_async.py",
        "tests/llm_router/bdd/routing/",
        "tests/llm_router/bdd/tools/",
        "tests/llm_router/bdd/resilience/",
        "tests/llm_router/bdd/security/",
        "tests/llm_router/bdd/sessions/",
        "tests/llm_router/bdd/structured_output/",
        "tests/llm_router/bdd/execution/cassettes/",
        "tests/llm_router/bdd/structured_output/cassettes/",
        "tests/llm_router/property_based/internal/test_invariants.py",
        "tests/llm_router/support/fault_server.py",
        "tests/llm_router/support/fault_observation.py",
        "tests/llm_router/support/_vcr_body_matching.py",
        "tests/llm_router/support/vcr_extensions.py",
        "tests/llm_router/support/workers/contract_worker.py",
        "tests/llm_router/support/workers/error_boundary.py",
        "tests/llm_router/support/workers/retry.py",
        "tests/llm_router/support/workers/retry_worker.py",
        "tests/llm_router/support/workers/structured_recovery.py",
        "tests/llm_router/support/workers/structured_recovery_worker.py",
        "tests/llm_router/support/workers/timeout_worker.py",
        "tests/llm_router/support/workers/worker_patches.py",
        "tests/llm_router/integration/test_config_installation_runtime_effect.py",
        "tests/llm_router/integration/test_content_pre_provider_rejection.py",
        "tests/llm_router/integration/test_vcr_redaction.py",
        "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py",
        "tests/llm_router/integration/test_qwenchat_adapter_fake.py",
        "tests/llm_router/integration/test_aistudio_adapter_fake.py",
        "tests/llm_router/integration/test_gemini_webapi_adapter_fake.py",
        "tests/llm_router/integration/test_google_genai_adapter_fake.py",
        "tests/llm_router/integration/test_provider_interoperability_matrix.py",
        "tests/llm_router/unit/test_internal_config_validation.py",
        "tests/llm_router/unit/test_internal_usage_normalization.py",
        "tests/llm_router/unit/test_internal_session_serialization.py",
        "tests/llm_router/unit/test_internal_schema_normalization.py",
        "tests/llm_router/unit/test_internal_content_normalization.py",
        "tests/llm_router/unit/test_public_package.py",
        "tests/test_examples.py",
        "tests/llm_router/unit/test_internal_provider_retry.py",
        "tests/llm_router/unit/test_internal_log_safety.py",
        "tests/llm_router/unit/test_internal_key_resolution.py",
        "tests/llm_router/unit/test_internal_limiter.py",
        "tests/llm_router/unit/test_internal_route_order.py",
        "tests/llm_router/unit/test_internal_tool_choice.py",
        "tests/llm_router/unit/test_internal_tool_registry.py",
    }
    unexpected = []
    for line in status:
        if line.startswith("?? .ai-bridge"):
            continue
        path = line[3:]
        if any(
            path == approved
            or (approved.endswith("/") and path.startswith(approved))
            for approved in approved_pilot_sources
        ):
            continue
        unexpected.append(line)
    check(not unexpected, f"repository has no unrelated source changes outside approved pilot authoring files: {unexpected}")

    print("\nACTIVE LLM-ROUTER MUTATION PILOT STRUCTURAL GATE: PASS")


if __name__ == "__main__":
    main()
