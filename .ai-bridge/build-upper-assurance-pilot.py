"""Build the routing upper-assurance pilot from normative targets and retained evidence."""

# ruff: noqa: D103, E501, EM101, EM102, PERF401, PLR0913, PLR2004, S314, TRY003

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_FACTS = ROOT / "docs/_build/html/requirement-monitor-facts.json"
JUNIT = ROOT / "test-results/pytest-junit.xml"
RUN_INPUTS = ROOT / "test-results/evidence-run-inputs.json"
OUT_DIR = ROOT / "docs/_build/html"
QUALIFICATION = OUT_DIR / "evidence-confidence-qualification.json"
FACTS_OUT = OUT_DIR / "upper-assurance-facts.json"
SHELL = OUT_DIR / "verification-assurance.html"

DOMAIN_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_domain", ROOT / ".ai-bridge/assurance_monitor_domain.py"
)
if DOMAIN_SPEC is None or DOMAIN_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor domain helpers")
domain = importlib.util.module_from_spec(DOMAIN_SPEC)
DOMAIN_SPEC.loader.exec_module(domain)

UI_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_ui", ROOT / ".ai-bridge/assurance_monitor_ui.py"
)
if UI_SPEC is None or UI_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor UI helpers")
ui = importlib.util.module_from_spec(UI_SPEC)
UI_SPEC.loader.exec_module(ui)

REGISTRY_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_registry", ROOT / ".ai-bridge/assurance_monitor_registry.py"
)
if REGISTRY_SPEC is None or REGISTRY_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor registry")
registry = importlib.util.module_from_spec(REGISTRY_SPEC)
REGISTRY_SPEC.loader.exec_module(registry)

esc = ui.esc

UPPER_HELP = {
    "requirement_support": "Checks that every Requirement needed by this capability is independently proven.",
    "capability_integration": "Checks that the Requirements inside this capability work correctly together.",
    "capability_validation": "Checks that this capability actually delivers the behavior it exists to provide.",
    "capability_support": "Checks that every capability needed by this Goal is independently proven.",
    "cross_capability_integration": "Checks that the capabilities inside this Goal work correctly together.",
    "outcome_validation": "Checks that the Goal's intended product outcome is achieved in a realistic scenario.",
    "goal_support": "Checks that every Goal required for whole-product assurance is independently proven.",
    "cross_goal_integration": "Checks that product Goals do not break each other when they interact.",
    "operational_validation": "Checks that the whole product works in the intended end-to-end operating scenario.",
}


PAGE_SPECS = registry.PAGE_SPECS
OUTPUTS = {spec.entity_id: OUT_DIR / spec.output for spec in PAGE_SPECS}


def living_spec_url(rows: list[dict]) -> str | None:
    feature = next(
        (
            str(row.get("gherkin_feature") or "").strip()
            for row in rows
            if row.get("gherkin_feature")
        ),
        "",
    )
    if not feature.startswith("features/") or not feature.endswith(".feature"):
        return None
    relative = feature.removeprefix("features/").removesuffix(".feature")
    return f"specifications/_generated/{relative}.html"


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def required_producers(target: dict) -> list[str]:
    producers = [
        "PRODUCER_PYTEST",
        "PRODUCER_PY_TESTKIT",
        "PRODUCER_UPPER_ASSURANCE_MONITOR",
    ]
    if str(target.get("method") or "").strip().lower() == "pytest-bdd":
        producers.append("PRODUCER_PYTEST_BDD")
    if str(target.get("boundary") or "").strip().lower() == "substitute":
        producers.append("PRODUCER_SCRIPTED_HTTP_SERVER")
    return producers


def producer_gate(target: dict, qualification: dict) -> dict:
    producers = qualification.get("producers") or {}
    required = required_producers(target)
    rows = []
    statuses = []
    for producer_id in required:
        raw = (producers.get(producer_id) or {}).get("status")
        if raw == "QUALIFIED":
            status = "MET"
        elif raw == "NOT QUALIFIED":
            status = "NOT MET"
        else:
            status = "UNKNOWN"
        statuses.append(status)
        rows.append(
            {
                "id": producer_id,
                "actual": raw or "UNKNOWN",
                "target": "QUALIFIED",
                "status": status,
            }
        )
    return {"status": domain.combine(statuses), "producers": rows}


def freshness_gate(target: dict, rows: list[dict], run_inputs: dict) -> dict:
    retained_inputs = run_inputs.get("inputs") or {}
    checks = []
    profile_rel = str(target.get("profile_path") or "").strip()
    profile_path = ROOT / profile_rel if profile_rel else None
    profile_retained = retained_inputs.get(profile_rel) if profile_rel else None
    profile_current = sha256_file(profile_path) if profile_path is not None else None
    if profile_retained is None:
        profile_status = "UNKNOWN"
    elif profile_current == profile_retained:
        profile_status = "MET"
    else:
        profile_status = "NOT MET"
    checks.append(
        {
            "kind": "assurance_profile",
            "path": profile_rel,
            "retained_sha256": profile_retained,
            "current_sha256": profile_current,
            "status": profile_status,
        }
    )

    for row in rows:
        source_path = str(row.get("source_path") or "").strip()
        junit_sha = row.get("source_sha256")
        if not source_path:
            checks.append(
                {
                    "kind": "test_source",
                    "path": None,
                    "retained_sha256": None,
                    "current_sha256": None,
                    "status": "UNKNOWN",
                }
            )
            continue
        source = ROOT / source_path
        snapshot_sha = retained_inputs.get(source_path)
        current_sha = sha256_file(source)
        if snapshot_sha is None or junit_sha is None or current_sha is None:
            status = "UNKNOWN"
        elif snapshot_sha == junit_sha == current_sha:
            status = "MET"
        else:
            status = "NOT MET"
        checks.append(
            {
                "kind": "test_source",
                "path": source_path,
                "junit_sha256": junit_sha,
                "retained_sha256": snapshot_sha,
                "current_sha256": current_sha,
                "status": status,
            }
        )

    statuses = [check["status"] for check in checks]
    return {
        "status": domain.combine(statuses) if statuses else "UNKNOWN",
        "checks": checks,
    }


def parse_need_graph() -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    pattern = re.compile(
        r"^\x60\x60\x60\{(?P<type>goal|feature|req|treq)\}\s+(?P<title>[^\n]+)\n"
        r"(?P<meta>.*?)(?:\n\n(?P<body>.*?))?^\x60\x60\x60\s*$",
        flags=re.MULTILINE | re.DOTALL,
    )
    for path in sorted((ROOT / "docs/requirements").glob("*.md")):
        for match in pattern.finditer(path.read_text()):
            meta = match.group("meta") or ""
            id_match = re.search(r"^:id:\s+(\S+)\s*$", meta, flags=re.MULTILINE)
            if not id_match:
                continue
            node_id = id_match.group(1)
            derives_match = re.search(
                r"^:derives:\s+(\S+)\s*$", meta, flags=re.MULTILINE
            )
            revision_match = re.search(
                r"^:revision:\s+(\d+)\s*$", meta, flags=re.MULTILINE
            )
            nodes[node_id] = {
                "id": node_id,
                "type": match.group("type"),
                "title": match.group("title").strip(),
                "derives": derives_match.group(1) if derives_match else None,
                "revision": int(revision_match.group(1)) if revision_match else None,
                "source": str(path.relative_to(ROOT)),
                "url": f"requirements/{path.stem}.html#{node_id}",
            }
    for node in nodes.values():
        node["children"] = sorted(
            child["id"]
            for child in nodes.values()
            if child.get("derives") == node["id"]
        )
    return nodes


def section_between(text: str, heading: str, *, level: int) -> str:
    marker = f"{'#' * level} {heading}"
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"Missing Assurance Profile heading: {heading}")
    body_start = start + len(marker)
    next_heading = re.search(
        rf"^#{{1,{level}}}\s+",
        text[body_start:],
        flags=re.MULTILINE,
    )
    end = body_start + next_heading.start() if next_heading else len(text)
    return text[body_start:end]


def markdown_table_after(section: str, heading: str) -> list[dict[str, str]]:
    marker = f"### {heading}"
    start = section.find(marker)
    if start < 0:
        raise RuntimeError(f"Missing section: {heading}")
    tail = section[start + len(marker) :]
    next_heading = re.search(r"^#{1,3}\s+", tail, flags=re.MULTILINE)
    block = tail[: next_heading.start()] if next_heading else tail
    if "**Target:** N/A" in block:
        return []
    lines = [
        line.strip() for line in block.splitlines() if line.strip().startswith("|")
    ]
    if len(lines) < 2:
        raise RuntimeError(f"{heading}: expected a target table or explicit N/A")
    headers = [value.strip() for value in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        values = [value.strip() for value in line.strip("|").split("|")]
        if len(values) != len(headers):
            raise RuntimeError(f"{heading}: malformed markdown table row: {line}")
        rows.append(dict(zip(headers, values, strict=True)))
    return rows


def profile_heading(entity_id: str) -> str:
    if entity_id.startswith("FEAT_"):
        return f"Feature · {entity_id}"
    if entity_id.startswith("GOAL_"):
        return f"Goal · {entity_id}"
    if entity_id == registry.PRODUCT_SYSTEM_ID:
        return "Product / System"
    raise RuntimeError(f"Unsupported upper assurance owner: {entity_id}")


def parse_profiles() -> dict[str, dict]:
    result: dict[str, dict] = {}
    seen: set[str] = set()
    source_cache: dict[str, str] = {}

    for spec in PAGE_SPECS:
        source = spec.profile_source
        if source not in source_cache:
            source_cache[source] = (ROOT / source).read_text()
        section = section_between(
            source_cache[source],
            profile_heading(spec.entity_id),
            level=2,
        )
        result[spec.entity_id] = {}
        for label, key in spec.labels[1:]:
            rows = markdown_table_after(section, label)
            criteria = []
            for row in rows:
                criterion = row.get("Criterion", "").strip().strip("`")
                if not criterion:
                    raise RuntimeError(f"{spec.entity_id}/{label}: empty criterion")
                if criterion in seen:
                    raise RuntimeError(
                        f"Duplicate upper assurance criterion: {criterion}"
                    )
                seen.add(criterion)
                required = int(row.get("Required executions", "1").strip("* ") or "1")
                criteria.append(
                    {
                        "id": criterion,
                        "method": row.get("Method", ""),
                        "test_level": row.get("Test level", ""),
                        "boundary": row.get("Boundary", ""),
                        "representation": row.get("Representation", ""),
                        "required_executions": required,
                        "success_criterion": row.get("Success criterion", ""),
                        "profile_path": source,
                        "profile_url": spec.profile_url,
                    }
                )
            result[spec.entity_id][key] = {
                "target": "N/A" if not rows else "REQUIRED",
                "criteria": criteria,
            }
    return result


def junit_assurance_actual(declared: set[str]) -> dict[str, list[dict]]:
    actual: dict[str, list[dict]] = defaultdict(list)
    if not JUNIT.exists():
        return actual
    root = ET.parse(JUNIT).getroot()
    for testcase in root.iter("testcase"):
        props = {
            prop.attrib.get("name"): prop.attrib.get("value")
            for prop in testcase.findall("./properties/property")
        }
        criterion = (props.get("assurance_item") or "").strip()
        if not criterion:
            continue
        if criterion not in declared:
            raise RuntimeError(
                f"{testcase.attrib.get('classname')}::{testcase.attrib.get('name')}: "
                f"unknown assurance_item {criterion!r}"
            )
        result = "passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            result = "failed"
        elif testcase.find("skipped") is not None:
            result = "skipped"
        actual[criterion].append(
            {
                "nodeid": (
                    f"{(testcase.attrib.get('classname') or '').replace('.', '/')}.py::"
                    f"{testcase.attrib.get('name') or ''}"
                ),
                "result": result,
                "verifies": [
                    value.strip()
                    for value in (props.get("verifies") or "").split(",")
                    if value.strip()
                ],
                "verification_kind": props.get("verification_kind"),
                "gherkin_feature": props.get("gherkin_feature"),
                "gherkin_scenario": props.get("gherkin_scenario"),
                "source_path": props.get("source_path"),
                "source_sha256": props.get("source_sha256"),
            }
        )
    return actual


def criterion_state(
    target: dict,
    rows: list[dict],
    *,
    run_inputs: dict,
    qualification: dict,
) -> dict:
    required = int(target["required_executions"])
    passed = sum(row["result"] == "passed" for row in rows)
    failed = sum(row["result"] != "passed" for row in rows)
    execution_status = (
        "MET"
        if len(rows) >= required and passed >= required and failed == 0
        else "NOT MET"
    )
    producer_qualification = producer_gate(target, qualification)
    freshness = freshness_gate(target, rows, run_inputs)
    status = domain.combine(
        [execution_status, producer_qualification["status"], freshness["status"]]
    )
    return {
        **target,
        "status": status,
        "execution_status": execution_status,
        "producer_qualification": producer_qualification,
        "freshness": freshness,
        "actual_executions": len(rows),
        "passed_executions": passed,
        "rows": rows,
    }


def direct_section_state(
    section: dict,
    actual: dict[str, list[dict]],
    *,
    run_inputs: dict,
    qualification: dict,
) -> dict:
    if section["target"] == "N/A":
        return {"status": "N/A", "criteria": []}
    criteria = [
        criterion_state(
            target,
            actual.get(target["id"], []),
            run_inputs=run_inputs,
            qualification=qualification,
        )
        for target in section["criteria"]
    ]
    return {
        "status": domain.combine([row["status"] for row in criteria]),
        "criteria": criteria,
    }


def profile_capture_facts(run_inputs: dict) -> dict[str, dict]:
    retained_inputs = run_inputs.get("inputs") or {}
    facts: dict[str, dict] = {}
    for profile_rel in sorted({spec.profile_source for spec in PAGE_SPECS}):
        current_sha = sha256_file(ROOT / profile_rel)
        retained_sha = retained_inputs.get(profile_rel)
        facts[profile_rel] = {
            "captured_at_run_start": retained_sha is not None,
            "fresh": retained_sha is not None and retained_sha == current_sha,
            "retained_sha256": retained_sha,
            "current_sha256": current_sha,
        }
    return facts


def build_facts() -> dict:
    graph = parse_need_graph()
    profile = parse_profiles()
    req_data = json.loads(REQ_FACTS.read_text())
    policy = req_data["policy"]
    contracts = req_data["contracts"]
    run_inputs = json.loads(RUN_INPUTS.read_text()) if RUN_INPUTS.exists() else {}
    qualification = (
        json.loads(QUALIFICATION.read_text()) if QUALIFICATION.exists() else {}
    )

    declared = {
        criterion["id"]
        for owner in profile.values()
        for section in owner.values()
        for criterion in section["criteria"]
    }
    actual = junit_assurance_actual(declared)

    contract_direct: dict[str, dict] = {}
    for contract_id, contract in contracts.items():
        contract_direct[contract_id] = domain.contract_domain_state(contract, policy)

    def effective_req(req_id: str) -> dict:
        direct = contract_direct.get(req_id)
        if direct is None:
            return {"status": "UNKNOWN", "direct": "UNKNOWN", "treqs": []}
        treqs = list(
            ((contracts.get(req_id) or {}).get("target") or {}).get("required_treqs")
            or []
        )
        treq_rows = [
            {
                "id": child_id,
                "status": contract_direct.get(child_id, {}).get("overall", "UNKNOWN"),
            }
            for child_id in treqs
        ]
        return {
            "status": domain.combine(
                [direct["overall"], *[row["status"] for row in treq_rows]]
            ),
            "direct": direct["overall"],
            "treqs": treq_rows,
        }

    feature_ids = tuple(
        spec.entity_id for spec in PAGE_SPECS if str(spec.entity_id).startswith("FEAT_")
    )
    goal_ids = tuple(
        spec.entity_id for spec in PAGE_SPECS if str(spec.entity_id).startswith("GOAL_")
    )

    features: dict[str, dict] = {}
    for feature_id in feature_ids:
        requirement_ids = [
            child_id
            for child_id in graph[feature_id]["children"]
            if graph.get(child_id, {}).get("type") == "req"
        ]
        children = [
            {
                "id": req_id,
                "title": graph[req_id]["title"],
                "status": effective_req(req_id)["status"],
                "url": f"contract-evidence-{registry.contract_slug(req_id)}.html",
                "technical_support": effective_req(req_id)["treqs"],
            }
            for req_id in requirement_ids
        ]
        support = domain.combine([row["status"] for row in children])
        direct_sections = {
            key: direct_section_state(
                profile[feature_id][key],
                actual,
                run_inputs=run_inputs,
                qualification=qualification,
            )
            for key in ("capability_integration", "capability_validation")
        }
        overall = domain.combine(
            [support, *[section["status"] for section in direct_sections.values()]]
        )
        features[feature_id] = {
            "id": feature_id,
            "title": graph[feature_id]["title"],
            "status": overall,
            "requirement_support": {"status": support, "children": children},
            **direct_sections,
        }

    goals: dict[str, dict] = {}
    for goal_id in goal_ids:
        feature_rows = [
            {
                "id": feature_id,
                "title": features[feature_id]["title"],
                "status": features[feature_id]["status"],
                "url": OUTPUTS[feature_id].name,
            }
            for feature_id in graph[goal_id]["children"]
            if feature_id in features
        ]
        capability_support = domain.combine([row["status"] for row in feature_rows])
        goal_direct = {
            key: direct_section_state(
                profile[goal_id][key],
                actual,
                run_inputs=run_inputs,
                qualification=qualification,
            )
            for key in ("cross_capability_integration", "outcome_validation")
        }
        goal = {
            "id": goal_id,
            "title": graph[goal_id]["title"],
            "capability_support": {
                "status": capability_support,
                "children": feature_rows,
            },
            **goal_direct,
        }
        goal["status"] = domain.combine(
            [capability_support, *[value["status"] for value in goal_direct.values()]]
        )
        goals[goal_id] = goal

    all_goal_ids = sorted(
        node_id for node_id, node in graph.items() if node.get("type") == "goal"
    )
    goal_rows = []
    for current_id in all_goal_ids:
        if current_id in goals:
            status = goals[current_id]["status"]
            url = OUTPUTS[current_id].name
        else:
            status = "UNKNOWN"
            url = graph[current_id]["url"]
        goal_rows.append(
            {
                "id": current_id,
                "title": graph[current_id]["title"],
                "status": status,
                "url": url,
            }
        )
    goal_support = domain.combine([row["status"] for row in goal_rows])
    system_direct = {
        key: direct_section_state(
            profile["PRODUCT_SYSTEM"][key],
            actual,
            run_inputs=run_inputs,
            qualification=qualification,
        )
        for key in ("cross_goal_integration", "operational_validation")
    }
    system = {
        "id": "PRODUCT_SYSTEM",
        "title": "llm-router whole-product assurance",
        "goal_support": {"status": goal_support, "children": goal_rows},
        **system_direct,
    }
    system["status"] = domain.combine(
        [goal_support, *[value["status"] for value in system_direct.values()]]
    )

    return {
        "schema": "ternforge-upper-assurance-pilot-2",
        "profiles": profile_capture_facts(run_inputs),
        "qualification_environment": qualification.get("environment") or {},
        "declared_criteria": sorted(declared),
        "actual_criteria": sorted(actual),
        "features": features,
        "goals": goals,
        "product_system": system,
    }


def card(label: str, state: dict, href: str, help_text: str) -> str:
    status = state["status"]
    meta = ""
    if state.get("children") is not None:
        children = state["children"]
        subject = {
            "Requirement support": "requirements",
            "Capability support": "capabilities",
            "Goal support": "goals",
        }.get(label, "items")
        meta = (
            f"{sum(row['status'] == 'MET' for row in children)} / {len(children)} {subject} pass"
            if children
            else f"no {subject}"
        )
    elif state.get("criteria") is not None:
        criteria = state["criteria"]
        meta = (
            f"{sum(row['status'] == 'MET' for row in criteria)} / {len(criteria)} scenarios pass"
            if criteria
            else "no target"
        )
    return ui.domain_card(
        label=label,
        status=status,
        href=f"#{href}",
        meta=meta,
        help_text=help_text,
    )


def support_section(
    section_id: str,
    title: str,
    state: dict,
    profile_url: str,
) -> str:
    cards = []
    for row in state["children"]:
        cards.append(
            ui.technical_support_card(
                item_id=row["id"],
                title=row["title"],
                status=row["status"],
                href=row["url"],
            )
        )
    return (
        f'<section class="section" id="{esc(section_id)}">'
        + ui.section_head(
            title=title,
            links=(
                ("Profile ↗", profile_url),
                ("Raw ↗", "upper-assurance-facts.json"),
            ),
        )
        + ui.support_panel("".join(cards))
        + "</section>"
    )


def criterion_inspector(criterion: dict, profile_url: str) -> str:
    execution_status = criterion["execution_status"]
    producer_state = criterion["producer_qualification"]
    freshness_state = criterion["freshness"]
    producer_rows = producer_state["producers"]
    freshness_rows = freshness_state["checks"]
    scenario = next(
        (
            str(row.get("gherkin_scenario") or "").strip()
            for row in criterion["rows"]
            if row.get("gherkin_scenario")
        ),
        criterion["id"],
    )
    actual_executions = int(criterion["actual_executions"])
    required_executions = int(criterion["required_executions"])
    passed_executions = int(criterion["passed_executions"])
    scenario_card = ui.coverage_card(
        {
            "semantic_actual": passed_executions,
            "failed_count": max(0, actual_executions - passed_executions),
            "missing_count": max(0, required_executions - actual_executions),
            "semantic_status": execution_status,
            "required_count": required_executions,
            "retained_count": actual_executions,
            "required_path_count": required_executions,
        },
        label="Scenario coverage",
        subject="scenarios",
        subject_singular="scenario",
        retained_subject="paths",
        retained_subject_singular="path",
        tip="Checks that the declared assurance scenario passes.",
    )
    producer_actual_values = sorted(
        {str(row.get("actual") or "UNKNOWN").upper() for row in producer_rows}
    )
    producer = ui.lane(
        f"Producer qualification · {len(producer_rows)} producers",
        domain.PRODUCER,
        producer_actual_values,
        "QUALIFIED",
        producer_state["status"],
        "Checks that every evidence producer used by this proof is qualified for its role.",
        sum(row["status"] == "MET" for row in producer_rows),
        len(producer_rows),
        "producers",
    )
    freshness_actual_values = sorted(
        {
            "CURRENT"
            if row["status"] == "MET"
            else ("STALE" if row["status"] == "NOT MET" else "UNKNOWN")
            for row in freshness_rows
        }
    )
    freshness = ui.lane(
        "Freshness",
        domain.FRESHNESS,
        freshness_actual_values,
        "CURRENT",
        freshness_state["status"],
        "Checks that the retained test source and Assurance Profile still match the current files.",
        sum(row["status"] == "MET" for row in freshness_rows),
        len(freshness_rows),
        "inputs",
    )
    bdd_url = living_spec_url(criterion["rows"])
    links = []
    if bdd_url:
        links.append(("BDD evidence ↗", bdd_url))
    links.extend(
        (
            ("Assurance profile ↗", profile_url),
            ("Raw facts ↗", "upper-assurance-facts.json"),
        )
    )
    signals = ui.signal_group(
        title="Required evidence",
        body=scenario_card,
        class_name="primary-group",
    ) + ui.signal_group(
        title="Retained path properties",
        body=ui.confidence_subgroup(producer + freshness),
        class_name="path-properties",
        scope=f"{actual_executions}/{required_executions} paths",
    )
    return (
        ui.inspector_head(
            eyebrow="Selected assurance scenario",
            title=scenario,
            status=criterion["status"],
        )
        + f'<div class="signal-grid">{signals}</div>'
        + ui.drilldowns(tuple(links))
    )


def direct_section(
    section_id: str,
    title: str,
    state: dict,
    profile_url: str,
) -> tuple[str, dict[str, str], str | None]:
    if state["status"] == "N/A":
        markup = (
            f'<section class="section" id="{esc(section_id)}">'
            + ui.section_head(
                title=title,
                links=(
                    ("Profile ↗", profile_url),
                    ("Raw ↗", "upper-assurance-facts.json"),
                ),
            )
            + '<div class="fault-layout no-inspector"><div class="fault-grid">'
            + ui.na_fault_tile()
            + "</div></div></section>"
        )
        return markup, {}, None

    inspectors = {
        criterion["id"]: criterion_inspector(criterion, profile_url)
        for criterion in state["criteria"]
    }
    default = next(iter(inspectors))
    tiles = []
    for criterion in state["criteria"]:
        execution_status = criterion["execution_status"]
        producer_rows = criterion["producer_qualification"]["producers"]
        producer_actual = sum(row["status"] == "MET" for row in producer_rows)
        scenario = next(
            (
                str(row.get("gherkin_scenario") or "").strip()
                for row in criterion["rows"]
                if row.get("gherkin_scenario")
            ),
            criterion["id"],
        )
        tiles.append(
            ui.metric_tile(
                title=scenario,
                status=criterion["status"],
                data_attrs=(
                    ("upper", criterion["id"]),
                    ("upper-inspector", f"upper-inspector-{section_id}"),
                ),
                metrics=(
                    (
                        "Scenarios",
                        str(criterion["passed_executions"]),
                        f"/ {criterion['required_executions']}",
                        execution_status,
                    ),
                    (
                        "Producers",
                        str(producer_actual),
                        f"/ {len(producer_rows)}",
                        criterion["producer_qualification"]["status"],
                    ),
                ),
            )
        )
    markup = (
        f'<section class="section" id="{esc(section_id)}">'
        + ui.section_head(
            title=title,
            links=(
                ("Profile ↗", profile_url),
                ("Raw ↗", "upper-assurance-facts.json"),
            ),
        )
        + '<div class="fault-layout"><div class="fault-grid">'
        + "".join(tiles)
        + f'</div><aside class="inspector" id="upper-inspector-{esc(section_id)}">{inspectors[default]}</aside></div></section>'
    )
    return markup, inspectors, default


def render_page(
    *,
    page_title: str,
    entity_id: str,
    entity: dict,
    labels: tuple[tuple[str, str], ...],
    profile_url: str,
    output: Path,
    navigation: str,
) -> None:
    section_ids = {
        key: f"ua-{entity_id.lower().replace('_', '-')}-{key.replace('_', '-')}"
        for _, key in labels
    }
    cards = [
        card(label, entity[key], section_ids[key], UPPER_HELP[key])
        for label, key in labels
    ]
    sections = []
    upper_inspectors: dict[str, str] = {}
    upper_defaults: list[tuple[str, str]] = []
    for label, key in labels:
        state = entity[key]
        if state.get("children") is not None:
            sections.append(
                support_section(
                    section_ids[key],
                    label,
                    state,
                    profile_url,
                )
            )
        else:
            markup, inspectors, default = direct_section(
                section_ids[key],
                label,
                state,
                profile_url,
            )
            sections.append(markup)
            upper_inspectors.update(inspectors)
            if default is not None:
                upper_defaults.append((section_ids[key], default))
    history_id = f"ua-{entity_id.lower().replace('_', '-')}-history"
    sections.append(
        ui.history_section(
            section_id=history_id,
            status=entity["status"],
            link_href="upper-assurance-facts.json",
            link_label="Raw ↗",
        )
    )

    monitor = (
        '<div id="tf-requirement-monitor">'
        + ui.verdict_header(
            kicker="Assurance status",
            entity_id=entity_id,
            status=entity["status"],
            domain_cards="".join(cards),
            domain_strip_class="domain-strip with-support",
        )
        + "".join(sections)
        + "</div>"
    )
    default_js = "".join(
        f"selectUpper(document.querySelector('[data-upper=\\\"{criterion}\\\"]'));"
        for _, criterion in upper_defaults
    )
    setup_js = (
        f"const upperInspectors={json.dumps(upper_inspectors, ensure_ascii=False)};"
    )
    bind_js = (
        "function selectUpper(button){if(!button)return;const key=button.dataset.upper;"
        "const inspectorId=button.dataset.upperInspector;const value=upperInspectors[key];"
        "const inspector=root.querySelector('#'+inspectorId);if(!value||!inspector)return;"
        "inspector.innerHTML=value;root.querySelectorAll('[data-upper-inspector=\"'+inspectorId+'\"]')"
        ".forEach(item=>item.classList.toggle('selected',item===button));}"
        "root.querySelectorAll('[data-upper]').forEach(button=>button.addEventListener('click',()=>selectUpper(button)));"
    )
    script = ui.monitor_script(
        setup_js=setup_js,
        bind_js=bind_js,
        nav_selector='a[href^="#ua-"]',
        init_js=default_js,
    )
    toc_items = [(label, f"#{section_ids[key]}") for label, key in labels]
    toc_items.append(("History", f"#{history_id}"))
    source = ui.render_monitor_shell(
        SHELL.read_text(),
        page_title=page_title,
        assurance_id=entity_id.lower(),
        monitor=monitor,
        script=script,
        toc_items=tuple(toc_items),
        navigation=navigation,
    )
    output.write_text(source)


def build() -> None:
    facts = build_facts()
    FACTS_OUT.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")
    graph = parse_need_graph()
    req_facts = json.loads(REQ_FACTS.read_text())
    monitor_url_map = registry.monitor_urls(
        set((req_facts.get("contracts") or {}).keys())
    )

    for spec in PAGE_SPECS:
        entity = facts
        for key in spec.facts_path:
            entity = entity[key]
        navigation = ui.assurance_navigation(
            registry.navigation_spec(graph, spec.entity_id, monitor_url_map)
        )
        render_page(
            page_title=spec.page_title,
            entity_id=spec.entity_id,
            entity=entity,
            labels=spec.labels,
            profile_url=spec.profile_url,
            output=OUTPUTS[spec.entity_id],
            navigation=navigation,
        )

    for output in OUTPUTS.values():
        print(output)
    print(FACTS_OUT)


if __name__ == "__main__":
    build()
