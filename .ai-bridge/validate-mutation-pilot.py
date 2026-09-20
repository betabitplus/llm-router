from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any, cast

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
        values = {key: False for key in keys}
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
        HTML / "verification-depth-map.html",
        HTML / "verification-assurance.html",
        HTML / "contract-evidence-request-override-precedence.html",
        HTML / "contract-evidence-credential-resolution.html",
        HTML / "contract-evidence-config-installation-coherence.html",
        HTML / "contract-evidence-tool-choice.html",
        HTML / "contract-evidence-multi-round-tool-execution.html",
        HTML / "contract-evidence-tool-runtime-safety.html",
        HTML / "contract-evidence-sync-route-fallback.html",
        HTML / "contract-evidence-route-timeout-fallback.html",
        HTML / "contract-evidence-route-attempt-limit.html",
        HTML / "contract-evidence-route-sticky-start.html",
        HTML / "contract-evidence-rate-limit-routing.html",
        HTML / "contract-evidence-provider-retry.html",
        HTML / "contract-evidence-structured-output-repair.html",
        HTML / "contract-evidence-sensitive-data-protection.html",
        HTML / "contract-evidence-provider-adapter-interoperability.html",
        HTML / "contract-evidence-async-provider-execution.html",
        HTML / "contract-evidence-response-normalization.html",
        HTML / "contract-evidence-provider-error-boundary.html",
        HTML / "contract-evidence-session-lifecycle.html",
        HTML / "contract-evidence-session-persistence.html",
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
    routing_requirements_source = (ROOT / "docs/requirements/routing.md").read_text()
    routing_profile_source = (ROOT / "docs/verification-profiles/routing.md").read_text()
    resilience_requirements_source = (ROOT / "docs/requirements/resilience.md").read_text()
    resilience_profile_source = (ROOT / "docs/verification-profiles/resilience.md").read_text()
    security_requirements_source = (ROOT / "docs/requirements/security.md").read_text()
    security_profile_source = (ROOT / "docs/verification-profiles/security.md").read_text()
    provider_requirements_source = (ROOT / "docs/requirements/providers.md").read_text()
    provider_profile_source = (ROOT / "docs/verification-profiles/providers.md").read_text()
    session_requirements_source = (ROOT / "docs/requirements/sessions.md").read_text()
    session_profile_source = (ROOT / "docs/verification-profiles/sessions.md").read_text()
    developer_requirements_source = (ROOT / "docs/requirements/developer.md").read_text()
    developer_profile_source = (ROOT / "docs/verification-profiles/developer.md").read_text()
    structured_requirements_source = (ROOT / "docs/requirements/structured_output.md").read_text()
    structured_profile_source = (ROOT / "docs/verification-profiles/structured-output.md").read_text()
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
        "## Profile · REQ_STRUCTURED_OUTPUT_REPAIR",
        "VC_PROVIDER_RETRY_STATUS_CLASSIFICATION",
        "VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION",
        "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY",
        "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY",
        "VC_PROVIDER_RETRY_ATTEMPT_BOUND",
        "VC_REPAIR_PROMPT_BOUNDS",
        "VC_STRUCTURED_REPAIR_RECOVERY",
        "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND",
        "### Fault applicability",
    )), "Resilience Verification Profiles own independent coverage targets and explicit Fault Models")
    check(all(token in security_requirements_source for token in (
        ":id: GOAL_DATA_SAFETY",
        ":id: REQ_SENSITIVE_DATA_PROTECTION",
        ":id: TREQ_RUNTIME_LOG_SAFETY",
        ":revision: 2",
        ":id: TREQ_VCR_AUTH_REDACTION",
        ":id: TREQ_VCR_REQUEST_CONTENT_REDACTION",
    )), "Data Safety Goal keeps the complete normative diagnostic and durable-evidence contract set")
    check(
        "**Verification intent.**" not in security_requirements_source,
        "Data Safety normative contracts keep HOW in Verification Profiles rather than Requirement cards",
    )
    check(all(token in security_profile_source for token in (
        "## Profile · REQ_SENSITIVE_DATA_PROTECTION",
        "VC_SECURITY_LOG_CONTEXT_FIELDS",
        "VC_VCR_AUTH_DURABLE_REDACTION",
        "VC_VCR_REQUEST_BODY_DURABLE_REDACTION",
        "VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS",
        "VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS",
        "VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS",
        "### Fault applicability",
    )), "Data Safety Verification Profile owns independent coverage targets and explicit Fault Model")
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
        "## Profile · REQ_ASYNC_PROVIDER_EXECUTION",
        "## Profile · REQ_RESPONSE_NORMALIZATION",
        "## Profile · REQ_PROVIDER_ERROR_BOUNDARY",
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
        "### Fault applicability",
    )), "Provider Verification Profiles own independent coverage targets and explicit Fault Models")
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
        "VC_SESSION_HISTORY_INCLUDED",
        "VC_SESSION_HISTORY_SUPPRESSED",
        "VC_SESSION_FORK_ISOLATION",
        "VC_SESSION_CLEAR_REUSE",
        "VC_SESSION_CONCURRENT_ISOLATION",
        "VC_SESSION_PERSISTENCE_GENERATED_STATE",
        "VC_SESSION_SERIALIZATION_MEDIA",
        "VC_SESSION_SERIALIZATION_VERSION_REJECTION",
        "VC_SESSION_PUBLIC_PERSISTENCE",
        "### Fault applicability",
    )), "Session Verification Profiles own independent coverage targets and explicit Fault Models")
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
    current_paths = [
        row
        for rows in (monitor_contract.get("coverage_actual") or {}).values()
        for row in rows
    ]
    check(len(current_paths) == 17, "Requirement monitor retains all 17 current Invalid Configuration coverage paths")
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
    check(
        depth_facts.get("schema_version") == 4
        and depth_source.get("tests") == 184
        and depth_source.get("passed") == 184
        and depth_audit.get("contracts") == 62
        and depth_audit.get("runtime_evidence") == 184
        and depth_audit.get("nodeid_mismatches") == 0
        and depth_audit.get("verifies_mismatches") == 0
        and depth_audit.get("bdd_feature_scenario_errors") == 0,
        "Depth facts are reproducibly regenerated from the current 184-test retained run",
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
    call_shapes = tool_multi_actual.get("VC_TOOL_REGISTRY_CALL_SHAPES") or []
    replay_multi = tool_multi_actual.get("VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES") or []
    local_multi = tool_multi_actual.get("VC_TOOL_MULTI_ROUND_OPENAI_LOCAL") or []
    check(
        tool_multi_targets.get(("component", "none"), {}).get("item_path_counts")
            == {
                "VC_TOOL_REGISTRY_CALL_SHAPES": 2,
                "VC_TOOL_REGISTRY_DUPLICATE_REJECTION": 1,
                "VC_TOOL_REGISTRY_SCHEMA_EXECUTION": 1,
            }
        and len(call_shapes) == 2
        and len(replay_multi) == 4
        and len(local_multi) == 1,
        "Multi-round Contract Evidence preserves criterion cardinality 2/1/1 plus four Replay paths and one Substitute path",
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
        "13/13 Component criteria · 16/16 paths",
        "Verification Coverage = PASS · Fault Model = FAIL · Overall = FAIL",
        "compatibility-only `.ai-bridge/assurance-targets.json`",
        "Test Coverage → Fault-based Testing → History",
    )), "monitor readiness ledger records the completed P34 target/actual cutover")
    check("Test plan" in test_plan_html and "Reusable Test Models" in test_plan_html,
          "generated Test Plan page renders the project-wide strategy")

    adapter = campaign.get("adapter") or {}
    check(
        adapter.get("version") == "p34-local-2",
        "retained mutation campaign uses the current p34-local-2 adapter provenance",
    )
    check(adapter.get("mutation_semantics_version") == "p21-local-2",
          "mutation semantics compatibility version remains explicit")
    check(campaign.get("mode") == "full", "retained pilot campaign is full audit")
    check(bool(campaign.get("run_id")), "retained pilot campaign has unique run_id")
    check(bool(campaign.get("baseline_run_id")), "retained pilot campaign has baseline_run_id")
    check(campaign.get("run_id") != campaign.get("baseline_run_id"), "run_id is not self-baseline")
    check(bool(campaign.get("finished_at")), "retained pilot campaign finished")
    check(float(campaign.get("duration_seconds") or 0) > 0, "retained pilot campaign has runtime")

    check(
        summary.get("total_contracts") == 62,
        "62 contracts are present in the verification-depth / mutation measurement universe",
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

    measured = campaign.get("contracts") or {}
    check(set(measured) == {
        "REQ_INVALID_CONFIGURATION_ERRORS",
        "TREQ_TOOL_REGISTRY",
    }, "current full audit measures only uniquely attributable pilot contracts")

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
    assurance_page = (HTML / "verification-assurance.html").read_text()
    override_page = (HTML / "contract-evidence-request-override-precedence.html").read_text()
    credential_page = (HTML / "contract-evidence-credential-resolution.html").read_text()
    install_page = (HTML / "contract-evidence-config-installation-coherence.html").read_text()
    tool_choice_page = (HTML / "contract-evidence-tool-choice.html").read_text()
    tool_multi_page = (HTML / "contract-evidence-multi-round-tool-execution.html").read_text()
    tool_runtime_page = (HTML / "contract-evidence-tool-runtime-safety.html").read_text()
    sync_route_page = (HTML / "contract-evidence-sync-route-fallback.html").read_text()
    timeout_route_page = (HTML / "contract-evidence-route-timeout-fallback.html").read_text()
    attempt_limit_page = (HTML / "contract-evidence-route-attempt-limit.html").read_text()
    sticky_route_page = (HTML / "contract-evidence-route-sticky-start.html").read_text()
    rate_limit_page = (HTML / "contract-evidence-rate-limit-routing.html").read_text()
    provider_retry_page = (HTML / "contract-evidence-provider-retry.html").read_text()
    structured_repair_page = (HTML / "contract-evidence-structured-output-repair.html").read_text()
    security_page = (HTML / "contract-evidence-sensitive-data-protection.html").read_text()
    provider_adapter_page = (HTML / "contract-evidence-provider-adapter-interoperability.html").read_text()
    async_provider_page = (HTML / "contract-evidence-async-provider-execution.html").read_text()
    response_normalization_page = (HTML / "contract-evidence-response-normalization.html").read_text()
    provider_error_page = (HTML / "contract-evidence-provider-error-boundary.html").read_text()
    session_lifecycle_page = (HTML / "contract-evidence-session-lifecycle.html").read_text()
    session_persistence_page = (HTML / "contract-evidence-session-persistence.html").read_text()
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
        "Product / System": (HTML / "assurance-product-system.html").read_text(),
    }
    spec_page = (HTML / "specification-health.html").read_text()
    health_page = (HTML / "verification-health-map.html").read_text()
    depth_page = (HTML / "verification-depth-map.html").read_text()
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
    for name, page in upper_assurance_pages.items():
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
    for name in ("Feature fallback", "Goal routing"):
        page = upper_assurance_pages[name]
        check(
            'class="fault-layout"' in page
            and "data-upper=" in page
            and 'class="inspector"' in page
            and "classList.toggle('selected'" in page,
            f"{name}: active upper criteria use canonical tile → selected inspector interaction",
        )
    for name in ("Feature rate limit", "Product / System"):
        check(
            'class="fault-tile na"' in upper_assurance_pages[name],
            f"{name}: undeclared upper Targets use canonical disabled N/A tiles",
        )

    monitor_copy_pages = {
        path.name: path.read_text()
        for path in sorted(HTML.glob("contract-evidence-*.html"))
    }
    monitor_copy_pages.update(upper_assurance_pages)
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
    goal_page = upper_assurance_pages["Goal routing"]
    check(
        "0 / 2 capabilities pass" in goal_page
        and "1 / 1 scenarios pass" in goal_page
        and "Selected assurance scenario" in goal_page
        and "Scenario coverage" in goal_page
        and '<div class="signal-card coverage-card met-signal">' in goal_page
        and "<b>5/5</b><small>producers</small>" in goal_page
        and "<b>2/2</b><small>inputs</small>" in goal_page
        and goal_page.count('class="state-lane"') >= 4
        and 'class="marker both">ACTUAL = TARGET' in goal_page
        and "Retained path properties" in goal_page
        and "Evidence confidence" in goal_page
        and ">Execution<" not in goal_page
        and ">Confidence<" not in goal_page,
        "upper assurance reuses the canonical REQ coverage-card and state-lane inspector pattern",
    )

    check(
        mutation_page.count('id="mutation-') >= 2,
        "Mutation Analysis exposes the measured contract work queue anchors",
    )
    check(
        "Current signal" in mutation_page
        and "New 0" in mutation_page
        and "Debt 29" in mutation_page
        and "Measured 2/62" in mutation_page,
        "Mutation Analysis keeps the current measured mutation signal compact and denominator-explicit",
    )
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
    check(
        mutation_page.count("Fresh</strong> · New 0 · Debt ") >= 2,
        "Mutation Analysis labels each measured contract fresh and keeps survivor debt compact",
    )
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
    check(monitor_facts.get("schema") == "ternforge-requirement-monitor-p34-2",
          "Requirement monitor facts carry the current P34 multi-binding schema")
    profiled_contracts = {
        "REQ_REQUEST_OVERRIDE_PRECEDENCE",
        "REQ_INVALID_CONFIGURATION_ERRORS",
        "REQ_CREDENTIAL_RESOLUTION",
        "REQ_CONFIG_INSTALLATION_COHERENCE",
        "REQ_TOOL_CHOICE",
        "REQ_MULTI_ROUND_TOOL_EXECUTION",
        "REQ_TOOL_RUNTIME_SAFETY",
        "REQ_SYNC_ROUTE_FALLBACK",
        "REQ_ROUTE_TIMEOUT_FALLBACK",
        "REQ_ROUTE_ATTEMPT_LIMIT",
        "REQ_ROUTE_STICKY_START",
        "REQ_RATE_LIMIT_ROUTING",
        "REQ_PROVIDER_RETRY",
        "REQ_STRUCTURED_OUTPUT_REPAIR",
        "REQ_SENSITIVE_DATA_PROTECTION",
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY",
        "REQ_ASYNC_PROVIDER_EXECUTION",
        "REQ_RESPONSE_NORMALIZATION",
        "REQ_PROVIDER_ERROR_BOUNDARY",
        "REQ_SESSION_LIFECYCLE",
        "REQ_SESSION_PERSISTENCE",
        "REQ_PUBLIC_API_SURFACE",
        "REQ_EXAMPLE_IMPORT_SAFETY",
        "REQ_STRUCTURED_TEXT_OUTPUT",
        "REQ_DOCUMENT_INPUT",
        "REQ_IMAGE_INPUT",
        "REQ_VIDEO_INPUT",
        "REQ_STRUCTURED_SCHEMA_CONTRACT",
        "REQ_MULTIMODAL_CONTENT_NORMALIZATION",
        "TREQ_ROUTE_ORDER",
        "TREQ_RATE_LIMIT_STATE",
        "TREQ_RATE_LIMIT_COOLDOWN_POLICY",
        "TREQ_RATE_LIMIT_AVAILABILITY_SELECTION",
    }
    check(
        set(monitor_facts.get("contracts") or {}) == profiled_contracts,
        "All fifteen product features expose twenty-nine parent and four first-class TREQ Contract Evidence profiles",
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
            set((target.get("gate_aggregation") or {})) == required_gate_signals
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
        "REQ_TOOL_CHOICE": tool_choice_page,
        "REQ_MULTI_ROUND_TOOL_EXECUTION": tool_multi_page,
        "REQ_TOOL_RUNTIME_SAFETY": tool_runtime_page,
        "REQ_SYNC_ROUTE_FALLBACK": sync_route_page,
        "REQ_ROUTE_TIMEOUT_FALLBACK": timeout_route_page,
        "REQ_ROUTE_ATTEMPT_LIMIT": attempt_limit_page,
        "REQ_ROUTE_STICKY_START": sticky_route_page,
        "REQ_RATE_LIMIT_ROUTING": rate_limit_page,
        "REQ_PROVIDER_RETRY": provider_retry_page,
        "REQ_STRUCTURED_OUTPUT_REPAIR": structured_repair_page,
        "REQ_SENSITIVE_DATA_PROTECTION": security_page,
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": provider_adapter_page,
        "REQ_ASYNC_PROVIDER_EXECUTION": async_provider_page,
        "REQ_RESPONSE_NORMALIZATION": response_normalization_page,
        "REQ_PROVIDER_ERROR_BOUNDARY": provider_error_page,
        "REQ_SESSION_LIFECYCLE": session_lifecycle_page,
        "REQ_SESSION_PERSISTENCE": session_persistence_page,
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
        check(
            challenged_faults == set(expected_challenges)
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
                ("component", "none"): {
                    "VC_PROVIDER_RETRY_STATUS_CLASSIFICATION": 2,
                    "VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION": 2,
                },
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY": 2,
                    "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY": 2,
                    "VC_PROVIDER_RETRY_ATTEMPT_BOUND": 2,
                },
            },
            "faults": {"interface.error-status": (6, 6)},
        },
        "REQ_STRUCTURED_OUTPUT_REPAIR": {
            "cells": {
                ("component", "none"): {"VC_REPAIR_PROMPT_BOUNDS": 1},
                ("system_integration", "substitute"): {
                    "VC_STRUCTURED_REPAIR_RECOVERY": 1,
                    "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND": 2,
                },
            },
            "faults": {"interface.payload-schema": (3, 3)},
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
            challenged_faults == set(expected["faults"])
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

    security_contract = monitor_facts["contracts"]["REQ_SENSITIVE_DATA_PROTECTION"]
    security_expected_cells = {
        ("component", "none"): {"VC_SECURITY_LOG_CONTEXT_FIELDS": 1},
        ("system_integration", "substitute"): {
            "VC_VCR_AUTH_DURABLE_REDACTION": 1,
            "VC_VCR_REQUEST_BODY_DURABLE_REDACTION": 1,
            "VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS": 1,
            "VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS": 1,
            "VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS": 1,
        },
    }
    security_target_cells = {
        (row.get("level"), row.get("boundary")): row
        for row in (security_contract.get("target") or {}).get("coverage") or []
    }
    check(
        set(security_target_cells) == set(security_expected_cells)
        and all(
            security_target_cells[key].get("item_path_counts") == counts
            for key, counts in security_expected_cells.items()
        ),
        "REQ_SENSITIVE_DATA_PROTECTION: Data Safety coverage target keeps the independently authored Test level/Boundary denominators",
    )
    security_actual = security_contract.get("coverage_actual") or {}
    for (level, boundary), criteria in security_expected_cells.items():
        for criterion_id, expected_paths in criteria.items():
            rows = [
                row
                for row in security_actual.get(criterion_id) or []
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
                f"REQ_SENSITIVE_DATA_PROTECTION: {criterion_id} retains every declared current/qualified evidence path",
            )
    security_faults = (
        (security_contract.get("fault_actual") or {}).get("retained_challenges") or {}
    )
    expected_security_faults = {
        "interface.error-status": (1, 1),
        "interface.payload-schema": (1, 1),
    }
    check(
        set(security_faults) == set(expected_security_faults),
        "REQ_SENSITIVE_DATA_PROTECTION: retained fault challenges contain only explicitly declared runtime-observed classes",
    )
    for fault_class, (exercised, detected) in expected_security_faults.items():
        row = security_faults[fault_class]
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
            f"REQ_SENSITIVE_DATA_PROTECTION: {fault_class} challenge is current, qualified, and detected",
        )
    required_security_faults = {
        item["id"]
        for group in (security_contract.get("target") or {}).get("fault_groups") or []
        for item in group.get("items") or []
        if item.get("state") == "required"
    }
    challenged_security_faults = {
        class_id
        for class_id in required_security_faults
        if ((security_contract.get("fault_actual") or {}).get("classes") or {})
        .get(class_id, {})
        .get("exercised")
    }
    check(
        challenged_security_faults == set(expected_security_faults)
        and challenged_security_faults < required_security_faults,
        "REQ_SENSITIVE_DATA_PROTECTION: partial Data Safety Fault Model remains explicit instead of becoming false-green",
    )
    check(
        '<div class="overall not-met">FAIL</div>' in security_page
        and re.search(
            r'<strong>Verification coverage.*?<span class="status met">PASS</span>',
            security_page,
            re.DOTALL,
        )
        and re.search(
            r'<strong>Fault model.*?<span class="status not-met">FAIL</span>',
            security_page,
            re.DOTALL,
        ),
        "REQ_SENSITIVE_DATA_PROTECTION: rendered monitor keeps Coverage PASS, Fault Model FAIL, and Overall FAIL",
    )

    provider_expectations = {
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": {
            "cells": {
                ("component_integration", "substitute"): {
                    "VC_PROVIDER_OPENAI_ADAPTER_BOUNDARY": 6,
                    "VC_PROVIDER_QWENCHAT_ADAPTER_BOUNDARY": 4,
                    "VC_PROVIDER_AISTUDIO_ADAPTER_BOUNDARY": 3,
                    "VC_PROVIDER_GEMINI_WEBAPI_ADAPTER_BOUNDARY": 5,
                    "VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY": 3,
                },
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_QWENCHAT_UPLOAD_RETRY": 1,
                },
            },
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
                ("component", "none"): {
                    "VC_PROVIDER_USAGE_NORMALIZATION": 3,
                },
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_RESPONSE_EQUIVALENCE": 4,
                },
            },
            "actual": {"VC_PROVIDER_RESPONSE_EQUIVALENCE": 1},
            "coverage_pass": False,
            "faults": {},
        },
        "REQ_PROVIDER_ERROR_BOUNDARY": {
            "cells": {
                ("system_integration", "substitute"): {
                    "VC_PROVIDER_ERROR_HTTP": 1,
                    "VC_PROVIDER_ERROR_SDK": 1,
                },
            },
            "faults": {"interface.error-status": (2, 2)},
        },
    }
    for contract_id, expected in provider_expectations.items():
        contract = monitor_facts["contracts"][contract_id]
        cells = cast(
            dict[tuple[str, str], dict[str, int]],
            cast(dict[str, Any], expected)["cells"],
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
        actual_by_item = contract.get("coverage_actual") or {}
        expected_actual = {
            criterion_id: expected_paths
            for criteria in cells.values()
            for criterion_id, expected_paths in criteria.items()
        }
        expected_actual.update(
            cast(dict[str, int], cast(dict[str, Any], expected).get("actual") or {})
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
            dict[str, tuple[int, int]],
            cast(dict[str, Any], expected)["faults"],
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
            challenged_faults == set(expected_faults)
            and challenged_faults < required_faults,
            f"{contract_id}: partial Provider Fault Model remains explicit instead of becoming false-green",
        )
        page = contract_pages[contract_id]
        coverage_pass = bool(cast(dict[str, Any], expected).get("coverage_pass", True))
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
                "VC_SESSION_SERIALIZATION_MEDIA": 4,
                "VC_SESSION_SERIALIZATION_VERSION_REJECTION": 1,
            },
            ("component_integration", "none"): {
                "VC_SESSION_PUBLIC_PERSISTENCE": 1,
            },
        },
        "REQ_PUBLIC_API_SURFACE": {
            ("component", "none"): {"VC_PUBLIC_API_ROOT_EXPORTS": 1},
        },
        "REQ_EXAMPLE_IMPORT_SAFETY": {
            ("component", "none"): {"VC_EXAMPLE_IMPORT_SAFETY": 6},
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
        check(
            retained == {},
            f"{contract_id}: no fault class is credited without an explicit retained challenge",
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
            bool(required_faults)
            and challenged_faults == set()
            and challenged_faults < required_faults,
            f"{contract_id}: incomplete required Fault Model remains explicit instead of becoming false-green",
        )
        page = contract_pages[contract_id]
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
        all(label in assurance_page for label in (
            "Required evidence", "Semantic coverage", "criteria passing",
            "13 criteria pass", "0 criteria fail", "0 criteria missing",
            "Retained path properties", "16/16 paths retained",
            "Evidence confidence",
        )),
        "canonical Invalid Configuration Component × Local inspector renders compact aggregate counts for all 13 criteria and 16 retained paths",
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
            "Provenance", "Producer qualification", "Freshness",
            "COMPLETE", "QUALIFIED", "CURRENT",
        )),
        "canonical retained-path confidence signals are present",
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
    check(declared_criteria == {
        "VC_CONFIG_PROVIDER_IDENTITY", "VC_CONFIG_MODEL_DECLARATION",
        "VC_CONFIG_REQUIRED_BASE_URL", "VC_CONFIG_ATTEMPT_TIMEOUT",
        "VC_CONFIG_RETRY_ATTEMPTS", "VC_CONFIG_RETRY_WAIT_BOUNDS",
        "VC_CONFIG_ROUTE_ATTEMPT_LIMIT", "VC_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES",
        "VC_CONFIG_TOOL_ROUND_LIMIT", "VC_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS",
        "VC_CONFIG_DEFAULT_PROVIDER_DECLARATION", "VC_CONFIG_DEFAULT_MODEL_MAPPING",
        "VC_CONFIG_MODEL_PROVIDER_REFERENCES", "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION",
    }, "canonical monitor facts retain all fourteen declared Invalid Configuration criteria")
    invalid_targets = {
        (row["level"], row["boundary"]): row
        for row in contract_monitor["target"]["coverage"]
    }
    check(
        invalid_targets[("component", "none")]["declared_count"] == 13
        and sum(invalid_targets[("component", "none")]["item_path_counts"].values()) == 16
        and invalid_targets[("system", "none")]["declared_count"] == 1
        and sum(invalid_targets[("system", "none")]["item_path_counts"].values()) == 1,
        "canonical monitor facts retain the Component 13 criteria / 16 paths plus System 1 / 1 denominator",
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
        install_targets[("component", "none")]["declared_count"] == 3
        and install_targets[("system_integration", "substitute")]["declared_count"] == 1
        and install_targets[("system_integration", "substitute")]["representation"] == "surrogate_simulated"
        and install_targets[("system_integration", "substitute")]["ms_validation_target"] == "L0",
        "configuration-installation profile requires Component state evidence plus a System-integration Substitute/Surrogate/L0 runtime-effect path",
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
            "VC_CONFIG_CACHE_INVALIDATION",
            "VC_CONFIG_INSTALLATION_RUNTIME_EFFECT",
        },
    }
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
    }
    for contract_id, page in contract_pages.items():
        coverage_class = (
            "not-met" if contract_id in partial_coverage_contracts else "met"
        )
        coverage_label = (
            "FAIL" if contract_id in partial_coverage_contracts else "PASS"
        )
        check(
            '<div class="overall not-met">FAIL</div>' in page
            and re.search(
                rf"<strong>Verification coverage</strong><span class=\"status {coverage_class}\">{coverage_label}</span>",
                page,
                flags=re.DOTALL,
            )
            and re.search(
                r"<strong>Fault model</strong><span class=\"status not-met\">FAIL</span>",
                page,
                flags=re.DOTALL,
            )
            and "No blocking fault checks selected" not in page
            and "This Verification Profile does not make fault-based testing a blocking target." not in page
            and 'class="fault-layout no-inspector"' not in page
            and 'data-fault="' in page,
            f"{contract_id}: rendered Coverage reflects Target/Actual completeness while incomplete required faults keep Overall honestly FAIL",
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
    check(
        all(label in assurance_page for label in (
            "Fault classes", "Required", "Challenged", "Detected",
            "Mutation checks", "Generated", "Reached", "Killed",
            "31/31", "29/31", "27/31", "27/27",
        )),
        "canonical fault detail renders the accepted dependent denominator chains",
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
    check((component_faults.get("generated"), component_faults.get("reached"), component_faults.get("killed")) == (31, 31, 29) and
          component_faults.get("mutation_reach") == 100.0 and component_faults.get("sensitivity") == 93.5 and
          component_faults.get("system_reach") == "component" and component_faults.get("boundary_mode") == "none",
          "Component×Local fault cell reflects the expanded validation-test denominator and current mutation detection")
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
           system_faults["families"]["comparison"]["sensitivity"]) == (92.9, 94.1, 100.0, 100.0),
          "native boundary/comparison families retain exact cross-depth sensitivities after coverage expansion")
    overlap = invalid_config_faults.get("detection_overlap") or {}
    check((overlap.get("mutant_universe"), overlap.get("detected_union"), overlap.get("corroborated"),
           overlap.get("component_only"), overlap.get("system_only"), overlap.get("undetected")) == (31, 29, 27, 2, 0, 2),
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
    check((req_layers["implementation"].get("generated"), req_layers["implementation"].get("detected")) == (31, 29),
          "Requirement implementation fault layer is backed by the same 31-mutant universe with exact union detection")
    implementation = req_layers["implementation"]
    impl_reach = implementation.get("implementation_reach") or {}
    check((impl_reach.get("covered_statements"), impl_reach.get("executable_statements"), impl_reach.get("percent")) == (23, 24, 95.8) and
          len(impl_reach.get("missing_statements") or []) == 1 and
          impl_reach.get("metric") == "implementation_statement_reach" and
          "coverage.py executable statements" in impl_reach.get("basis", ""),
          "Implementation statement reach has an explicit honest 23/24 coverage.py denominator")
    check(implementation.get("overall_detection") == 93.5,
          "Overall Detection is retained as the secondary killed/generated metric")
    native_mutants = implementation.get("mutant_detail") or []
    check(len(native_mutants) == 31 and len({row.get("gremlin_id") for row in native_mutants}) == 31,
          "exact native mutant detail retains all 31 engine-native gremlin IDs without tuple-key collapse")
    check(sum(bool(row.get("component_killed")) for row in native_mutants) == 29 and
          sum(bool(row.get("system_killed")) for row in native_mutants) == 27 and
          sum(bool(row.get("system_reached")) for row in native_mutants) == 27,
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
    check(current_actual == {
        "component-reach": 100.0,
        "component-sensitivity": 93.5,
        "system-reach": 87.1,
        "system-sensitivity": 100.0,
    }, "current mutation-check actuals are stable")
    check(
        all(float(value or 0.0) >= 80.0 for value in current_actual.values()),
        "all declared Invalid Configuration mutation Reach/Sensitivity thresholds are currently met",
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
    component_target = next(
        row
        for row in contract_monitor["target"]["coverage"]
        if row["level"] == "component" and row["boundary"] == "none"
    )
    check(
        component_fault["sensitivity"] == 93.5
        and "VC_CONFIG_MODEL_DECLARATION" in component_target["items"]
        and len(contract_monitor["coverage_actual"].get("VC_CONFIG_MODEL_DECLARATION") or []) == 1,
        "canonical monitor facts retain the current Component sensitivity and executed model-declaration criterion",
    )

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
    check(
        "TERNFORGE-P27-TRACE-EVIDENCE-START" in trace_reader_page
        and "contract-evidence-request-override-precedence.html#ce-coverage-req_request_override_precedence" in trace_reader_page
        and "contract-evidence-credential-resolution.html#ce-coverage-req_credential_resolution" in trace_reader_page
        and "contract-evidence-config-installation-coherence.html#ce-coverage-req_config_installation_coherence" in trace_reader_page
        and "verification-assurance.html#ce-coverage-req_invalid_configuration_errors" in trace_reader_page,
        "Traceability Reader routes profiled Configuration contracts to their real Contract Evidence pages",
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
    resilience_trace_routes = {
        "REQ_PROVIDER_RETRY": "contract-evidence-provider-retry.html#ce-coverage-req_provider_retry",
        "TREQ_PROVIDER_RETRY_CLASSIFICATION": "contract-evidence-provider-retry.html#ce-coverage-req_provider_retry",
        "TREQ_PROVIDER_RETRY_BOUNDS": "contract-evidence-provider-retry.html#ce-coverage-req_provider_retry",
        "REQ_STRUCTURED_OUTPUT_REPAIR": "contract-evidence-structured-output-repair.html#ce-coverage-req_structured_output_repair",
        "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS": "contract-evidence-structured-output-repair.html#ce-coverage-req_structured_output_repair",
        "TREQ_REPAIR_PROMPT_BOUNDS": "contract-evidence-structured-output-repair.html#ce-coverage-req_structured_output_repair",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in resilience_trace_routes.items()
        ),
        "Traceability Reader routes Resilience parent/derived contracts to the accepted parent Contract Evidence pages",
    )
    security_trace_routes = {
        "REQ_SENSITIVE_DATA_PROTECTION": "contract-evidence-sensitive-data-protection.html#ce-coverage-req_sensitive_data_protection",
        "TREQ_RUNTIME_LOG_SAFETY": "contract-evidence-sensitive-data-protection.html#ce-coverage-req_sensitive_data_protection",
        "TREQ_VCR_AUTH_REDACTION": "contract-evidence-sensitive-data-protection.html#ce-coverage-req_sensitive_data_protection",
        "TREQ_VCR_REQUEST_CONTENT_REDACTION": "contract-evidence-sensitive-data-protection.html#ce-coverage-req_sensitive_data_protection",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in security_trace_routes.items()
        ),
        "Traceability Reader routes Data Safety parent/derived contracts to the accepted parent Contract Evidence page",
    )
    provider_trace_routes = {
        "REQ_PROVIDER_ADAPTER_INTEROPERABILITY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_OPENAI_ADAPTER_BOUNDARY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_QWENCHAT_ADAPTER_BOUNDARY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_AISTUDIO_ADAPTER_BOUNDARY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY": "contract-evidence-provider-adapter-interoperability.html#ce-coverage-req_provider_adapter_interoperability",
        "REQ_ASYNC_PROVIDER_EXECUTION": "contract-evidence-async-provider-execution.html#ce-coverage-req_async_provider_execution",
        "REQ_RESPONSE_NORMALIZATION": "contract-evidence-response-normalization.html#ce-coverage-req_response_normalization",
        "TREQ_USAGE_NORMALIZATION": "contract-evidence-response-normalization.html#ce-coverage-req_response_normalization",
        "REQ_PROVIDER_ERROR_BOUNDARY": "contract-evidence-provider-error-boundary.html#ce-coverage-req_provider_error_boundary",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in provider_trace_routes.items()
        ),
        "Traceability Reader routes Provider parent/derived contracts to the accepted parent Contract Evidence pages",
    )
    session_trace_routes = {
        "REQ_SESSION_LIFECYCLE": "contract-evidence-session-lifecycle.html#ce-coverage-req_session_lifecycle",
        "REQ_SESSION_PERSISTENCE": "contract-evidence-session-persistence.html#ce-coverage-req_session_persistence",
        "TREQ_SESSION_SERIALIZATION": "contract-evidence-session-persistence.html#ce-coverage-req_session_persistence",
    }
    check(
        all(
            f'"{contract_id}": "{href}"' in trace_reader_page
            for contract_id, href in session_trace_routes.items()
        ),
        "Traceability Reader routes Session parent/derived contracts to the accepted parent Contract Evidence pages",
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
    check(len(measurement_contract_ids) == 62,
          "verification-depth / mutation measurement universe contains all 62 current contracts")
    requirements_text = "\n".join(
        path.read_text() for path in sorted((ROOT / "docs/requirements").glob("*.md"))
    )
    normative_contract_ids = set(re.findall(
        r"^:id:\s+((?:REQ|TREQ)_[A-Z0-9_]+)\s*$", requirements_text, flags=re.MULTILINE
    ))
    check(len(normative_contract_ids) == 62,
          "normative Sphinx-Needs graph contains 62 Requirement/TREQ contracts")
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
          "Component semantic coverage **13/13 PASS · 16/16 paths**" in manifest and
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
        "build-upper-assurance-pilot.py",
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
        "docs/_build/html/specification-health.html",
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/test-plan.html",
        "docs/_build/html/_static/mutation-test-elements.js",
    ]
    history_glob = "`docs/_build/html/mutation-results/campaign-history/*.json`"
    contract_evidence_glob = "`docs/_build/html/contract-evidence-*.html`"
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
    )
    check(not missing_artifacts, f"extraction manifest inventories all retained generated artifact classes: {missing_artifacts}")

    check(not (ROOT / "mutants").exists(), "temporary mutmut workspace absent")
    setup = ROOT / "setup.cfg"
    check(not setup.exists() or "[mutmut]" not in setup.read_text(), "temporary mutmut setup config absent")

    status = [
        record
        for record in subprocess.check_output(
            ["git", "status", "--porcelain", "-z"],
            cwd=ROOT,
            text=True,
        ).split("\0")
        if record
    ]
    approved_pilot_sources = {
        ".ai-bridge/build-mutation-report-prototype.py",
        ".ai-bridge/build-requirement-monitor.py",
        ".ai-bridge/build-upper-assurance-pilot.py",
        ".ai-bridge/monitor-readiness.md",
        ".ai-bridge/mutation-testing-platform-extraction-manifest.md",
        ".ai-bridge/qualify-evidence-confidence.py",
        ".ai-bridge/validate-mutation-pilot.py",
        "docs/index.md",
        "docs/README.md",
        "docs/test-plan.md",
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
        "features/tools/",
        "features/routing/",
        "features/resilience/",
        "features/security/",
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
        "tests/llm_router/bdd/responses/test_public_contract.py",
        "tests/llm_router/bdd/configuration/test_overrides.py",
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
