"""Build the routing upper-assurance pilot from normative targets and retained evidence."""

# ruff: noqa: D103, E501, EM101, EM102, PERF401, PLR0913, PLR2004, S314, TRY003

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs/assurance-profiles/routing.md"
REQ_FACTS = ROOT / "docs/_build/html/requirement-monitor-facts.json"
JUNIT = ROOT / "test-results/pytest-junit.xml"
RUN_INPUTS = ROOT / "test-results/evidence-run-inputs.json"
OUT_DIR = ROOT / "docs/_build/html"
QUALIFICATION = OUT_DIR / "evidence-confidence-qualification.json"
FACTS_OUT = OUT_DIR / "upper-assurance-facts.json"
SHELL = OUT_DIR / "contract-evidence-route-sticky-start.html"

OUTPUTS = {
    "FEAT_ROUTE_FALLBACK": OUT_DIR / "assurance-feat-route-fallback.html",
    "FEAT_RATE_LIMIT_ROUTING": OUT_DIR / "assurance-feat-rate-limit-routing.html",
    "GOAL_ROUTING_RELIABILITY": OUT_DIR / "assurance-goal-routing-reliability.html",
    "PRODUCT_SYSTEM": OUT_DIR / "assurance-product-system.html",
}

REQMON_SPEC = importlib.util.spec_from_file_location(
    "requirement_monitor", ROOT / ".ai-bridge/build-requirement-monitor.py"
)
if REQMON_SPEC is None or REQMON_SPEC.loader is None:
    raise RuntimeError("Could not load requirement monitor helpers")
reqmon = importlib.util.module_from_spec(REQMON_SPEC)
REQMON_SPEC.loader.exec_module(reqmon)

STATUS_ORDER = ("NOT MET", "UNKNOWN", "MET", "N/A")
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


SECTION_LABELS = {
    "FEAT_ROUTE_FALLBACK": (
        ("Requirement support", "requirement_support"),
        ("Capability integration", "capability_integration"),
        ("Capability validation", "capability_validation"),
    ),
    "FEAT_RATE_LIMIT_ROUTING": (
        ("Requirement support", "requirement_support"),
        ("Capability integration", "capability_integration"),
        ("Capability validation", "capability_validation"),
    ),
    "GOAL_ROUTING_RELIABILITY": (
        ("Capability support", "capability_support"),
        ("Cross-capability integration", "cross_capability_integration"),
        ("Outcome validation", "outcome_validation"),
    ),
    "PRODUCT_SYSTEM": (
        ("Goal support", "goal_support"),
        ("Cross-goal integration", "cross_goal_integration"),
        ("Operational validation", "operational_validation"),
    ),
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


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
    return {"status": reqmon.combine(statuses), "producers": rows}


def freshness_gate(rows: list[dict], run_inputs: dict) -> dict:
    retained_inputs = run_inputs.get("inputs") or {}
    checks = []
    profile_rel = str(PROFILE.relative_to(ROOT))
    profile_retained = retained_inputs.get(profile_rel)
    profile_current = sha256_file(PROFILE)
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
        "status": reqmon.combine(statuses) if statuses else "UNKNOWN",
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


def parse_profile() -> dict[str, dict]:
    text = PROFILE.read_text()
    owners = {
        "FEAT_ROUTE_FALLBACK": section_between(
            text, "Feature · FEAT_ROUTE_FALLBACK", level=2
        ),
        "FEAT_RATE_LIMIT_ROUTING": section_between(
            text, "Feature · FEAT_RATE_LIMIT_ROUTING", level=2
        ),
        "GOAL_ROUTING_RELIABILITY": section_between(
            text, "Goal · GOAL_ROUTING_RELIABILITY", level=2
        ),
        "PRODUCT_SYSTEM": section_between(text, "Product / System", level=2),
    }
    mapping = {
        "FEAT_ROUTE_FALLBACK": (
            ("capability_integration", "Capability integration"),
            ("capability_validation", "Capability validation"),
        ),
        "FEAT_RATE_LIMIT_ROUTING": (
            ("capability_integration", "Capability integration"),
            ("capability_validation", "Capability validation"),
        ),
        "GOAL_ROUTING_RELIABILITY": (
            ("cross_capability_integration", "Cross-capability integration"),
            ("outcome_validation", "Outcome validation"),
        ),
        "PRODUCT_SYSTEM": (
            ("cross_goal_integration", "Cross-goal integration"),
            ("operational_validation", "Operational validation"),
        ),
    }
    result: dict[str, dict] = {}
    seen: set[str] = set()
    for owner, section in owners.items():
        result[owner] = {}
        for key, label in mapping[owner]:
            rows = markdown_table_after(section, label)
            criteria = []
            for row in rows:
                criterion = row.get("Criterion", "").strip().strip("`")
                if not criterion:
                    raise RuntimeError(f"{owner}/{label}: empty criterion")
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
                    }
                )
            result[owner][key] = {
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
    freshness = freshness_gate(rows, run_inputs)
    status = reqmon.combine(
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
        "status": reqmon.combine([row["status"] for row in criteria]),
        "criteria": criteria,
    }


def contract_status(contract: dict, policy: dict) -> dict:
    coverage_states = [
        reqmon.cell_state(contract, target)["overall"]
        for target in contract["target"].get("coverage", [])
    ]
    fault_states = [
        reqmon.fault_state(contract, group, policy)["status"]
        for group in contract["target"].get("fault_groups", [])
    ]
    coverage = reqmon.combine(coverage_states)
    fault = reqmon.combine(fault_states)
    return {
        "coverage": coverage,
        "fault": fault,
        "overall": reqmon.combine([coverage, fault]),
    }


def build_facts() -> dict:
    graph = parse_need_graph()
    profile = parse_profile()
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
        contract_direct[contract_id] = contract_status(contract, policy)

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
            "status": reqmon.combine(
                [direct["overall"], *[row["status"] for row in treq_rows]]
            ),
            "direct": direct["overall"],
            "treqs": treq_rows,
        }

    features: dict[str, dict] = {}
    for feature_id in ("FEAT_ROUTE_FALLBACK", "FEAT_RATE_LIMIT_ROUTING"):
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
                "url": f"contract-evidence-{reqmon.contract_slug(req_id)}.html",
                "technical_support": effective_req(req_id)["treqs"],
            }
            for req_id in requirement_ids
        ]
        support = reqmon.combine([row["status"] for row in children])
        direct_sections = {
            key: direct_section_state(
                profile[feature_id][key],
                actual,
                run_inputs=run_inputs,
                qualification=qualification,
            )
            for key in ("capability_integration", "capability_validation")
        }
        overall = reqmon.combine(
            [support, *[section["status"] for section in direct_sections.values()]]
        )
        features[feature_id] = {
            "id": feature_id,
            "title": graph[feature_id]["title"],
            "status": overall,
            "requirement_support": {"status": support, "children": children},
            **direct_sections,
        }

    goal_id = "GOAL_ROUTING_RELIABILITY"
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
    capability_support = reqmon.combine([row["status"] for row in feature_rows])
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
        "capability_support": {"status": capability_support, "children": feature_rows},
        **goal_direct,
    }
    goal["status"] = reqmon.combine(
        [capability_support, *[value["status"] for value in goal_direct.values()]]
    )

    all_goal_ids = sorted(
        node_id for node_id, node in graph.items() if node.get("type") == "goal"
    )
    goal_rows = []
    for current_id in all_goal_ids:
        if current_id == goal_id:
            status = goal["status"]
            url = OUTPUTS[goal_id].name
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
    goal_support = reqmon.combine([row["status"] for row in goal_rows])
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
    system["status"] = reqmon.combine(
        [goal_support, *[value["status"] for value in system_direct.values()]]
    )

    profile_rel = str(PROFILE.relative_to(ROOT))
    retained_profile_sha = (run_inputs.get("inputs") or {}).get(profile_rel)
    current_profile_sha = sha256_file(PROFILE)
    return {
        "schema": "ternforge-upper-assurance-pilot-1",
        "profile": profile_rel,
        "profile_captured_at_run_start": retained_profile_sha is not None,
        "profile_fresh": (
            retained_profile_sha is not None
            and retained_profile_sha == current_profile_sha
        ),
        "profile_retained_sha256": retained_profile_sha,
        "profile_current_sha256": current_profile_sha,
        "qualification_environment": qualification.get("environment") or {},
        "declared_criteria": sorted(declared),
        "actual_criteria": sorted(actual),
        "features": features,
        "goal": goal,
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
    return (
        f'<a class="domain" href="#{esc(href)}"><strong>{esc(label)} {reqmon.help_tip(help_text, focusable=False)}</strong>'
        f'<span class="status {reqmon.status_class(status)}">{esc(reqmon.status_label(status))}</span>'
        f'<span class="domain-meta">{esc(meta)}</span></a>'
    )


def support_section(
    section_id: str,
    title: str,
    state: dict,
    profile_url: str,
    help_text: str,
) -> str:
    tiles = []
    for row in state["children"]:
        tiles.append(
            f'<a class="fault-tile upper-child-tile {reqmon.status_class(row["status"])}" '
            f'href="{esc(row["url"])}">'
            '<div class="tile-head">'
            f"<strong>{esc(row['id'])}</strong>"
            f'<span class="status {reqmon.status_class(row["status"])}">{esc(reqmon.status_label(row["status"]))}</span>'
            "</div>"
            f'<div class="coverage-summary"><small>{esc(row["title"])}</small></div>'
            "</a>"
        )
    return (
        f'<section class="section" id="{esc(section_id)}">'
        f'<div class="section-head"><h3>{esc(title)} {reqmon.help_tip(help_text)}</h3>'
        f'<div class="section-links"><a class="section-link" href="{esc(profile_url)}">Profile ↗</a>'
        '<a class="section-link" href="upper-assurance-facts.json">Raw ↗</a></div></div>'
        '<div class="panel upper-support-panel"><div class="fault-grid upper-support-grid">'
        + "".join(tiles)
        + "</div></div></section>"
    )


def criterion_inspector(criterion: dict, profile_url: str) -> str:
    execution_status = criterion["execution_status"]
    producer_state = criterion["producer_qualification"]
    freshness_state = criterion["freshness"]
    producer_rows = producer_state["producers"]
    freshness_rows = freshness_state["checks"]
    producer_actual = sum(row["status"] == "MET" for row in producer_rows)
    freshness_actual = sum(row["status"] == "MET" for row in freshness_rows)
    scenario = next(
        (
            str(row.get("gherkin_scenario") or "").strip()
            for row in criterion["rows"]
            if row.get("gherkin_scenario")
        ),
        criterion["id"],
    )
    bdd_url = living_spec_url(criterion["rows"])
    bdd_link = f'<a href="{esc(bdd_url)}">BDD evidence ↗</a>' if bdd_url else ""
    scenario_card = reqmon.metric(
        "Scenario coverage",
        f'{criterion["passed_executions"]}/{criterion["actual_executions"]} scenarios passed',
        f'{criterion["required_executions"]} scenario required',
        execution_status,
        "Checks that the declared assurance scenario passes.",
    )
    producer = reqmon.metric(
        "Producer qualification",
        f"{producer_actual}/{len(producer_rows)} producers qualified",
        f"{len(producer_rows)} producers required",
        producer_state["status"],
        "Checks that every evidence producer used by this proof is qualified for its role.",
    )
    freshness = reqmon.metric(
        "Freshness",
        f"{freshness_actual}/{len(freshness_rows)} inputs current",
        f"{len(freshness_rows)} inputs current",
        freshness_state["status"],
        "Checks that the retained test source and Assurance Profile still match the current files.",
    )
    return (
        '<div class="inspector-head">'
        '<div><span class="eyebrow">Assurance scenario</span>'
        f"<h3>{esc(scenario)}</h3></div>"
        f'<span class="status big {reqmon.status_class(criterion["status"])}">{esc(reqmon.status_label(criterion["status"]))}</span></div>'
        '<div class="signal-grid">'
        '<div class="signal-group primary-group"><div class="signal-group-head"><strong>Required evidence</strong></div>'
        f"{scenario_card}</div>"
        '<div class="signal-group path-properties"><div class="signal-group-head"><strong>Evidence confidence</strong></div>'
        f'<div class="confidence-grid">{producer}{freshness}</div></div></div>'
        '<div class="drilldowns">'
        f'{bdd_link}<a href="{esc(profile_url)}">Assurance profile ↗</a>'
        '<a href="upper-assurance-facts.json">Raw facts ↗</a></div>'
    )


def direct_section(
    section_id: str,
    title: str,
    state: dict,
    profile_url: str,
    help_text: str,
) -> tuple[str, dict[str, str], str | None]:
    if state["status"] == "N/A":
        markup = (
            f'<section class="section" id="{esc(section_id)}">'
            f'<div class="section-head"><h3>{esc(title)} {reqmon.help_tip(help_text)}</h3>'
            f'<div class="section-links"><a class="section-link" href="{esc(profile_url)}">Profile ↗</a>'
            '<a class="section-link" href="upper-assurance-facts.json">Raw ↗</a></div></div>'
            '<div class="fault-layout no-inspector"><div class="fault-grid">'
            '<div class="fault-tile na" aria-disabled="true">'
            '<div class="tile-head"><strong>Target</strong><span class="status na">N/A</span></div>'
            '<div class="na-center">N/A</div></div></div></div></section>'
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
            f'<button class="fault-tile upper-criterion-tile {reqmon.status_class(criterion["status"])}" '
            f'type="button" data-upper="{esc(criterion["id"])}" data-upper-inspector="upper-inspector-{esc(section_id)}">'
            '<div class="tile-head">'
            f"<strong>{esc(scenario)}</strong>"
            f'<span class="status {reqmon.status_class(criterion["status"])}">{esc(reqmon.status_label(criterion["status"]))}</span></div>'
            '<div class="tile-metrics">'
            f'<div class="{reqmon.status_class(execution_status)}"><span>Scenarios</span>'
            f"<strong>{criterion['passed_executions']}</strong><i>/ {criterion['required_executions']}</i></div>"
            f'<div class="{reqmon.status_class(criterion["producer_qualification"]["status"])}"><span>Producers</span>'
            f"<strong>{producer_actual}</strong><i>/ {len(producer_rows)}</i></div>"
            "</div></button>"
        )
    markup = (
        f'<section class="section" id="{esc(section_id)}">'
        f'<div class="section-head"><h3>{esc(title)} {reqmon.help_tip(help_text)}</h3>'
        f'<div class="section-links"><a class="section-link" href="{esc(profile_url)}">Profile ↗</a>'
        '<a class="section-link" href="upper-assurance-facts.json">Raw ↗</a></div></div>'
        '<div class="fault-layout"><div class="fault-grid">'
        + "".join(tiles)
        + f'</div><aside class="inspector" id="upper-inspector-{esc(section_id)}">{inspectors[default]}</aside></div></section>'
    )
    return markup, inspectors, default


def history_section(section_id: str, status: str) -> str:
    return (
        f'<section class="section" id="{esc(section_id)}"><div class="section-head">'
        '<h3>History</h3><a class="section-link" href="upper-assurance-facts.json">Raw ↗</a></div>'
        '<div class="panel history"><strong>Current</strong><div class="history-line">'
        f'<i class="history-point {reqmon.status_class(status)}"></i></div>'
        f'<span class="status {reqmon.status_class(status)}">{esc(reqmon.status_label(status))}</span>'
        "</div></section>"
    )


def render_page(
    *,
    page_title: str,
    entity_id: str,
    entity: dict,
    labels: tuple[tuple[str, str], ...],
    profile_url: str,
    output: Path,
) -> None:
    source = SHELL.read_text()
    style_match = re.search(
        r'<style id="tf-requirement-monitor-style">.*?</style>',
        source,
        flags=re.DOTALL,
    )
    if style_match is None:
        raise RuntimeError("Canonical Contract Evidence style is missing from shell")
    source = re.sub(
        r'<style id="tf-requirement-monitor-style">.*?</style>',
        "",
        source,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'<script id="tf-requirement-monitor-script">.*?</script>',
        "",
        source,
        flags=re.DOTALL,
    )

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
                    UPPER_HELP[key],
                )
            )
        else:
            markup, inspectors, default = direct_section(
                section_ids[key],
                label,
                state,
                profile_url,
                UPPER_HELP[key],
            )
            sections.append(markup)
            upper_inspectors.update(inspectors)
            if default is not None:
                upper_defaults.append((section_ids[key], default))
    history_id = f"ua-{entity_id.lower().replace('_', '-')}-history"
    sections.append(history_section(history_id, entity["status"]))

    monitor = (
        '<div id="tf-requirement-monitor">'
        '<header class="verdict"><div class="verdict-main"><div>'
        '<div class="kicker">Assurance status</div>'
        f"<h2>{esc(entity_id)}</h2></div>"
        f'<div class="overall {reqmon.status_class(entity["status"])}">{esc(reqmon.status_label(entity["status"]))}</div>'
        '</div><div class="domain-strip with-support">'
        + "".join(cards)
        + "</div></header>"
        + "".join(sections)
        + "</div>"
    )
    article = (
        f'<section id="assurance-{esc(entity_id.lower())}"><h1>{esc(page_title)}'
        f'<a class="headerlink" href="#assurance-{esc(entity_id.lower())}" title="Link to this heading">#</a></h1>'
        f"{monitor}</section>"
    )
    source, count = re.subn(
        r'(<article class="bd-article">).*?(</article>)',
        lambda match: match.group(1) + article + match.group(2),
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("Could not replace upper-assurance article body")

    extra_style = style_match.group(0).replace(
        "</style>",
        "#tf-requirement-monitor .upper-support-panel{padding:.55rem}"
        "#tf-requirement-monitor .upper-child-tile{display:block;min-height:0;text-decoration:none}"
        "#tf-requirement-monitor .upper-child-tile.unknown{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}"
        "#tf-requirement-monitor .upper-child-tile:hover{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}"
        "@media(max-width:760px){#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:1fr}}"
        "</style>",
    )
    source = source.replace("</head>", extra_style + "\n</head>", 1)

    default_js = "".join(
        f"selectUpper(document.querySelector('[data-upper=\\\"{criterion}\\\"]'));"
        for _, criterion in upper_defaults
    )
    script = f"""<script id="tf-requirement-monitor-script">
(()=>{{const root=document.querySelector('#tf-requirement-monitor');if(!root)return;const upperInspectors={json.dumps(upper_inspectors, ensure_ascii=False)};function syncSticky(){{const header=document.querySelector('.bd-header');const top=header?.getBoundingClientRect().bottom||0;root.style.setProperty('--sticky-top',top+'px')}}function selectUpper(button){{if(!button)return;const key=button.dataset.upper;const inspectorId=button.dataset.upperInspector;const value=upperInspectors[key];const inspector=root.querySelector('#'+inspectorId);if(!value||!inspector)return;inspector.innerHTML=value;root.querySelectorAll('[data-upper-inspector="'+inspectorId+'"]').forEach(item=>item.classList.toggle('selected',item===button));}}root.querySelectorAll('[data-upper]').forEach(button=>button.addEventListener('click',()=>selectUpper(button)));let flashTimer;function flashTarget(hash){{if(!hash||!hash.startsWith('#'))return;const target=root.querySelector(hash);if(!target||!target.classList.contains('section'))return;root.querySelectorAll('.section.nav-flash').forEach(node=>node.classList.remove('nav-flash'));void target.offsetWidth;target.classList.add('nav-flash');clearTimeout(flashTimer);flashTimer=setTimeout(()=>target.classList.remove('nav-flash'),1700);}}document.querySelectorAll('a[href^="#ua-"]').forEach(link=>link.addEventListener('click',()=>requestAnimationFrame(()=>flashTarget(link.getAttribute('href')))));window.addEventListener('hashchange',()=>flashTarget(location.hash));window.addEventListener('resize',syncSticky);syncSticky();{default_js}if(location.hash)requestAnimationFrame(()=>flashTarget(location.hash));}})();
</script>"""
    source = source.replace("</body>", script + "\n</body>", 1)

    source = source.replace(
        '<span class="ellipsis">Contract Evidence</span>',
        f'<span class="ellipsis">{esc(page_title)}</span>',
    )
    source = re.sub(
        r"<title>.*?— llm-router documentation</title>",
        f"<title>{esc(page_title)} — llm-router documentation</title>",
        source,
        count=1,
    )
    toc = "".join(
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#{esc(section_ids[key])}">{esc(label)}</a></li>'
        for label, key in labels
    ) + (
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#{esc(history_id)}">History</a></li>'
    )
    secondary = (
        '<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc"><div class="sidebar-secondary-items sidebar-secondary__inner">'
        '<div class="sidebar-secondary-item"><div class="tocsection onthispage"><i class="fa-solid fa-list"></i> On this page</div>'
        '<nav class="bd-toc-nav page-toc"><ul class="visible nav section-nav flex-column">'
        f"{toc}</ul></nav></div></div></div>"
    )
    source, sidebar_count = re.subn(
        r'<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc">.*?</div></div>\s*</div>\s*<footer class="bd-footer-content">',
        secondary + '\n</div>\n<footer class="bd-footer-content">',
        source,
        count=1,
        flags=re.DOTALL,
    )
    if sidebar_count != 1:
        raise RuntimeError("Could not replace canonical secondary sidebar")
    output.write_text(source)


def build() -> None:
    facts = build_facts()
    FACTS_OUT.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")
    profile_url = "assurance-profiles/routing.html"

    render_page(
        page_title="Capability Assurance",
        entity_id="FEAT_ROUTE_FALLBACK",
        entity=facts["features"]["FEAT_ROUTE_FALLBACK"],
        labels=SECTION_LABELS["FEAT_ROUTE_FALLBACK"],
        profile_url=profile_url,
        output=OUTPUTS["FEAT_ROUTE_FALLBACK"],
    )
    render_page(
        page_title="Capability Assurance",
        entity_id="FEAT_RATE_LIMIT_ROUTING",
        entity=facts["features"]["FEAT_RATE_LIMIT_ROUTING"],
        labels=SECTION_LABELS["FEAT_RATE_LIMIT_ROUTING"],
        profile_url=profile_url,
        output=OUTPUTS["FEAT_RATE_LIMIT_ROUTING"],
    )
    render_page(
        page_title="Outcome Assurance",
        entity_id="GOAL_ROUTING_RELIABILITY",
        entity=facts["goal"],
        labels=SECTION_LABELS["GOAL_ROUTING_RELIABILITY"],
        profile_url=profile_url,
        output=OUTPUTS["GOAL_ROUTING_RELIABILITY"],
    )
    render_page(
        page_title="Product / System Assurance",
        entity_id="PRODUCT_SYSTEM",
        entity=facts["product_system"],
        labels=SECTION_LABELS["PRODUCT_SYSTEM"],
        profile_url=profile_url,
        output=OUTPUTS["PRODUCT_SYSTEM"],
    )

    for output in OUTPUTS.values():
        print(output)
    print(FACTS_OUT)


if __name__ == "__main__":
    build()
