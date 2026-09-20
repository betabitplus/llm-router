"""Shared assurance monitor page registry and hierarchy navigation projection."""

from __future__ import annotations

from typing import NamedTuple

PRODUCT_SYSTEM_ID = "PRODUCT_SYSTEM"
PRODUCT_SYSTEM_LABEL = "Product / System"

FEATURE_SECTION_LABELS = (
    ("Requirement support", "requirement_support"),
    ("Capability integration", "capability_integration"),
    ("Capability validation", "capability_validation"),
)
GOAL_SECTION_LABELS = (
    ("Capability support", "capability_support"),
    ("Cross-capability integration", "cross_capability_integration"),
    ("Outcome validation", "outcome_validation"),
)
PRODUCT_SECTION_LABELS = (
    ("Goal support", "goal_support"),
    ("Cross-goal integration", "cross_goal_integration"),
    ("Operational validation", "operational_validation"),
)


class PageSpec(NamedTuple):
    """Declarative contract for one generated upper-assurance monitor page."""

    entity_id: str
    page_title: str
    facts_path: tuple[str, ...]
    output: str
    labels: tuple[tuple[str, str], ...]
    profile_source: str
    profile_url: str


PAGE_SPECS = (
    PageSpec(
        entity_id="FEAT_ROUTE_FALLBACK",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_ROUTE_FALLBACK"),
        output="assurance-feat-route-fallback.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/routing.md",
        profile_url="assurance-profiles/routing.html",
    ),
    PageSpec(
        entity_id="FEAT_RATE_LIMIT_ROUTING",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_RATE_LIMIT_ROUTING"),
        output="assurance-feat-rate-limit-routing.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/routing.md",
        profile_url="assurance-profiles/routing.html",
    ),
    PageSpec(
        entity_id="GOAL_ROUTING_RELIABILITY",
        page_title="Outcome Assurance",
        facts_path=("goals", "GOAL_ROUTING_RELIABILITY"),
        output="assurance-goal-routing-reliability.html",
        labels=GOAL_SECTION_LABELS,
        profile_source="docs/assurance-profiles/routing.md",
        profile_url="assurance-profiles/routing.html",
    ),
    PageSpec(
        entity_id="FEAT_PUBLIC_API",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_PUBLIC_API"),
        output="assurance-feat-public-api.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/developer.md",
        profile_url="assurance-profiles/developer.html",
    ),
    PageSpec(
        entity_id="FEAT_EXECUTABLE_EXAMPLES",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_EXECUTABLE_EXAMPLES"),
        output="assurance-feat-executable-examples.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/developer.md",
        profile_url="assurance-profiles/developer.html",
    ),
    PageSpec(
        entity_id="GOAL_DEVELOPER_USABILITY",
        page_title="Outcome Assurance",
        facts_path=("goals", "GOAL_DEVELOPER_USABILITY"),
        output="assurance-goal-developer-usability.html",
        labels=GOAL_SECTION_LABELS,
        profile_source="docs/assurance-profiles/developer.md",
        profile_url="assurance-profiles/developer.html",
    ),
    PageSpec(
        entity_id="FEAT_SESSION_LIFECYCLE",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_SESSION_LIFECYCLE"),
        output="assurance-feat-session-lifecycle.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/sessions.md",
        profile_url="assurance-profiles/sessions.html",
    ),
    PageSpec(
        entity_id="GOAL_SESSION_CONTINUITY",
        page_title="Outcome Assurance",
        facts_path=("goals", "GOAL_SESSION_CONTINUITY"),
        output="assurance-goal-session-continuity.html",
        labels=GOAL_SECTION_LABELS,
        profile_source="docs/assurance-profiles/sessions.md",
        profile_url="assurance-profiles/sessions.html",
    ),
    PageSpec(
        entity_id="FEAT_SENSITIVE_DATA_PROTECTION",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_SENSITIVE_DATA_PROTECTION"),
        output="assurance-feat-sensitive-data-protection.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/security.md",
        profile_url="assurance-profiles/security.html",
    ),
    PageSpec(
        entity_id="GOAL_DATA_SAFETY",
        page_title="Outcome Assurance",
        facts_path=("goals", "GOAL_DATA_SAFETY"),
        output="assurance-goal-data-safety.html",
        labels=GOAL_SECTION_LABELS,
        profile_source="docs/assurance-profiles/security.md",
        profile_url="assurance-profiles/security.html",
    ),
    PageSpec(
        entity_id="FEAT_TOOL_SELECTION",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_TOOL_SELECTION"),
        output="assurance-feat-tool-selection.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/tools.md",
        profile_url="assurance-profiles/tools.html",
    ),
    PageSpec(
        entity_id="FEAT_TOOL_EXECUTION",
        page_title="Capability Assurance",
        facts_path=("features", "FEAT_TOOL_EXECUTION"),
        output="assurance-feat-tool-execution.html",
        labels=FEATURE_SECTION_LABELS,
        profile_source="docs/assurance-profiles/tools.md",
        profile_url="assurance-profiles/tools.html",
    ),
    PageSpec(
        entity_id="GOAL_TOOL_ORCHESTRATION",
        page_title="Outcome Assurance",
        facts_path=("goals", "GOAL_TOOL_ORCHESTRATION"),
        output="assurance-goal-tool-orchestration.html",
        labels=GOAL_SECTION_LABELS,
        profile_source="docs/assurance-profiles/tools.md",
        profile_url="assurance-profiles/tools.html",
    ),
    PageSpec(
        entity_id=PRODUCT_SYSTEM_ID,
        page_title="Product / System Assurance",
        facts_path=("product_system",),
        output="assurance-product-system.html",
        labels=PRODUCT_SECTION_LABELS,
        profile_source="docs/assurance-profiles/product-system.md",
        profile_url="assurance-profiles/product-system.html",
    ),
)

UPPER_MONITOR_URLS = {spec.entity_id: spec.output for spec in PAGE_SPECS}
CONTRACT_MONITOR_OVERRIDES = {
    "REQ_INVALID_CONFIGURATION_ERRORS": "verification-assurance.html",
}


def contract_slug(contract_id: str) -> str:
    """Return the canonical Contract Evidence filename slug for a REQ/TREQ id."""
    slug = contract_id.lower()
    for prefix in ("treq_", "req_"):
        if slug.startswith(prefix):
            slug = slug.removeprefix(prefix)
            break
    return slug.replace("_", "-")


def monitor_urls(
    contract_ids: list[str] | tuple[str, ...] | set[str],
) -> dict[str, str]:
    """Return monitor URLs for all onboarded upper entities plus REQ/TREQ contracts."""
    urls = dict(UPPER_MONITOR_URLS)
    urls.update(
        {
            contract_id: CONTRACT_MONITOR_OVERRIDES.get(
                contract_id,
                f"contract-evidence-{contract_slug(contract_id)}.html",
            )
            for contract_id in contract_ids
        }
    )
    return urls


def short_entity_label(entity_id: str) -> str:
    """Return a compact human-readable hierarchy label from an assurance entity id."""
    if entity_id == PRODUCT_SYSTEM_ID:
        return PRODUCT_SYSTEM_LABEL
    for prefix in ("GOAL_", "FEAT_", "REQ_", "TREQ_"):
        if entity_id.startswith(prefix):
            entity_id = entity_id.removeprefix(prefix)
            break
    acronyms = {"API", "HTTP", "ID", "JSON", "SDK", "URL", "VCR"}
    words = entity_id.split("_")
    rendered = [word if word in acronyms else word.lower() for word in words]
    if rendered:
        rendered[0] = (
            rendered[0] if rendered[0] in acronyms else rendered[0].capitalize()
        )
    return " ".join(rendered)


def normalize_needs_graph(needs: dict[str, dict]) -> dict[str, dict]:
    """Normalize Sphinx-Needs rows into the hierarchy shape used by navigation."""
    graph: dict[str, dict] = {}
    for entity_id, row in needs.items():
        entity_type = str(row.get("type") or "")
        if entity_type not in {"goal", "feature", "req", "treq"}:
            continue
        derives = row.get("derives")
        if isinstance(derives, list):
            parent = str(derives[0]) if derives else None
        else:
            parent = str(derives) if derives else None
        children = row.get("children")
        if children is None:
            children = row.get("derives_back") or []
        docname = str(row.get("docname") or "").strip()
        graph[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "title": str(row.get("title") or entity_id),
            "derives": parent,
            "children": [str(child) for child in children],
            "url": (
                str(row.get("url"))
                if row.get("url")
                else (f"{docname}.html#{entity_id}" if docname else "")
            ),
        }
    return graph


def navigation_spec(
    graph: dict[str, dict],
    current_id: str,
    monitor_url_map: dict[str, str],
) -> dict:
    """Project ancestry and monitor-capable children for one assurance entity."""
    if current_id == PRODUCT_SYSTEM_ID:
        path = [
            {
                "id": PRODUCT_SYSTEM_ID,
                "label": PRODUCT_SYSTEM_LABEL,
                "title": PRODUCT_SYSTEM_LABEL,
                "url": None,
            }
        ]
        child_ids = [
            spec.entity_id
            for spec in PAGE_SPECS
            if spec.entity_id.startswith("GOAL_") and spec.entity_id in graph
        ]
        current_type = "product"
    else:
        if current_id not in graph:
            return {"path": [], "children": [], "children_label": ""}
        chain: list[str] = []
        seen: set[str] = set()
        cursor: str | None = current_id
        while cursor and cursor not in seen and cursor in graph:
            seen.add(cursor)
            chain.append(cursor)
            parent = graph[cursor].get("derives")
            cursor = str(parent) if parent else None
        chain.reverse()
        path = [
            {
                "id": PRODUCT_SYSTEM_ID,
                "label": PRODUCT_SYSTEM_LABEL,
                "title": PRODUCT_SYSTEM_LABEL,
                "url": monitor_url_map.get(PRODUCT_SYSTEM_ID),
            }
        ]
        for entity_id in chain:
            row = graph[entity_id]
            is_current = entity_id == current_id
            label = short_entity_label(entity_id)
            if path and path[-1]["label"] == label:
                suffix = {
                    "goal": "goal",
                    "feature": "capability",
                    "req": "requirement",
                    "treq": "technical requirement",
                }.get(str(row.get("type") or ""))
                if suffix:
                    label = f"{label} · {suffix}"
            path.append(
                {
                    "id": entity_id,
                    "label": label,
                    "title": row.get("title") or entity_id,
                    "url": None
                    if is_current
                    else (monitor_url_map.get(entity_id) or row.get("url") or None),
                }
            )
        child_ids = list(graph[current_id].get("children") or [])
        current_type = str(graph[current_id].get("type") or "")

    children = []
    for child_id in child_ids:
        url = monitor_url_map.get(child_id)
        row = graph.get(child_id)
        if not url or not row:
            continue
        children.append(
            {
                "id": child_id,
                "label": short_entity_label(child_id),
                "title": row.get("title") or child_id,
                "url": url,
            }
        )

    children_label = {
        "product": "Goals",
        "goal": "Capabilities",
        "feature": "Requirements",
        "req": "Technical support",
    }.get(current_type, "")
    return {
        "path": path,
        "children": children,
        "children_label": children_label,
    }
