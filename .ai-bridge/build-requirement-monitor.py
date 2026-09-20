from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_ui", ROOT / ".ai-bridge/assurance_monitor_ui.py"
)
if UI_SPEC is None or UI_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor UI helpers")
ui = importlib.util.module_from_spec(UI_SPEC)
UI_SPEC.loader.exec_module(ui)

esc = ui.esc
help_tip = ui.help_tip
status_class = ui.status_class
status_label = ui.status_label
lane = ui.lane
coverage_card = ui.coverage_card
FACTS = ROOT / "docs/_build/html/requirement-monitor-facts.json"
CANONICAL_OUT = ROOT / "docs/_build/html/verification-assurance.html"
PRIMARY_CONTRACT_ID = "REQ_INVALID_CONFIGURATION_ERRORS"

OUT = CANONICAL_OUT
CONTRACT_ID = PRIMARY_CONTRACT_ID
CONTRACT_URL = "requirements/configuration.html#REQ_INVALID_CONFIGURATION_ERRORS"
PROFILE_URL = "verification-profiles/invalid-configuration.html"
MODEL_URL = "test-plan.html#test-plan-configuration-validation-model"
MUTATION_URL: str | None = "mutation-analysis.html#mutation-req_invalid_configuration_errors"

LEVELS = [
    ("component", "Component"),
    ("component_integration", "Component integration"),
    ("system", "System"),
    ("system_integration", "System integration"),
    ("acceptance", "Acceptance"),
]
BOUNDARIES = [
    ("none", "Local"),
    ("substitute", "Substitute"),
    ("replay", "Replay"),
    ("direct", "Direct live"),
]
REPRESENTATION = ["Synthetic / abstract", "Surrogate / simulated", "Representative", "Actual", "UNKNOWN"]
PROVENANCE = ["COMPLETE", "INCOMPLETE", "UNKNOWN"]
PRODUCER = ui.PRODUCER
FRESHNESS = ui.FRESHNESS
FAULT_GROUP_HELP = {
    "Implementation": "Checks that small code mistakes—wrong comparisons, limits, branches, returns, or exception paths—are caught.",
    "Runtime / dependency": "Checks that dependency failures—timeouts, disconnects, unavailability, or malformed replies—cannot change the required behavior.",
    "Interface / protocol": "Checks that wrong external calls, error statuses, or malformed payloads are caught at the boundary.",
    "Architecture": "Checks that code cannot bypass a required layer or depend on a forbidden layer.",
    "Specification / model": "Checks that tests catch the wrong result, a missing case, or the wrong ordering or boundary rule.",
}
MS_LEVELS = ["N/A", "L0", "L1", "L2", "L3", "L4", "UNKNOWN", "NOT DECLARED"]



def combine(statuses: list[str]) -> str:
    if statuses and all(value == "N/A" for value in statuses):
        return "N/A"
    values = [value for value in statuses if value != "N/A"]
    if "NOT MET" in values:
        return "NOT MET"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    if values and all(value == "MET" for value in values):
        return "MET"
    return "UNKNOWN"


def representation_label(value: str | None) -> str:
    return {
        "synthetic_abstract": "Synthetic / abstract",
        "surrogate_simulated": "Surrogate / simulated",
        "representative": "Representative",
        "actual": "Actual",
    }.get(value or "", "UNKNOWN")


def ms_label(value: str | None) -> str:
    if not value:
        return "UNKNOWN"
    value = value.upper()
    return "N/A" if value == "NA" else value


def gate_rule(contract: dict, signal: str, default: str = "ALL") -> str:
    rule = (((contract.get("target") or {}).get("gate_aggregation") or {}).get(signal) or {}).get("rule", default)
    return rule if rule in {"ALL", "ANY"} else default


def quantified_status(values: list[str], target: str, rule: str) -> str:
    if not values:
        return "UNKNOWN"
    if rule == "ANY":
        if any(value == target for value in values):
            return "MET"
        if any(value == "UNKNOWN" for value in values):
            return "UNKNOWN"
        return "NOT MET"
    if any(value not in {target, "UNKNOWN"} for value in values):
        return "NOT MET"
    if any(value == "UNKNOWN" for value in values):
        return "UNKNOWN"
    return "MET"


def ordered_values(values: set[str], options: list[str]) -> list[str]:
    return [option for option in options if option in values]


def minimum_ordered_status(
    values: list[str],
    target: str,
    rule: str,
    order: list[str],
) -> tuple[str, int]:
    """Evaluate an ordered evidence property as a minimum required strength."""
    if not values or target not in order:
        return "UNKNOWN", 0
    target_rank = order.index(target)
    matched = sum(
        1
        for value in values
        if value in order and order.index(value) >= target_rank
    )
    unknown = sum(value == "UNKNOWN" for value in values)
    below = len(values) - matched - unknown
    if rule == "ANY":
        if matched:
            return "MET", matched
        if unknown:
            return "UNKNOWN", matched
        return "NOT MET", matched
    if below:
        return "NOT MET", matched
    if unknown:
        return "UNKNOWN", matched
    return "MET", matched


def minimum_ms_status(values: list[str], target: str, rule: str) -> tuple[str, int]:
    """Evaluate M&S as a minimum qualification level, never exact equality."""
    return minimum_ordered_status(
        values,
        target,
        rule,
        ["L0", "L1", "L2", "L3", "L4"],
    )


def minimum_representation_status(
    values: list[str],
    target: str,
    rule: str,
) -> tuple[str, int]:
    """Evaluate representation realism as a minimum required strength."""
    return minimum_ordered_status(
        values,
        target,
        rule,
        ["Synthetic / abstract", "Surrogate / simulated", "Representative", "Actual"],
    )


def cell_state(contract: dict, target: dict) -> dict:
    rows = []
    passed = 0
    failed = 0
    covered = 0
    required_path_count = 0
    path_identity_gaps = []
    for item_id in target["items"]:
        expected_paths = int((target.get("item_path_counts") or {}).get(item_id, 1))
        expected_path_ids = list(
            (target.get("item_path_ids") or {}).get(item_id, [])
        )
        required_path_count += expected_paths
        item_rows = [
            row
            for row in contract["coverage_actual"].get(item_id, [])
            if row.get("level") == target["level"] and row.get("boundary") == target["boundary"]
        ]
        if not item_rows:
            if expected_path_ids:
                path_identity_gaps.append(
                    {
                        "criterion": item_id,
                        "missing": expected_path_ids,
                        "unexpected": [],
                        "duplicates": [],
                    }
                )
            continue
        covered += 1
        rows.extend(item_rows)
        identity_ok = True
        if expected_path_ids:
            actual_path_ids = [
                str(row.get("coverage_path") or "").strip()
                for row in item_rows
            ]
            populated_path_ids = [value for value in actual_path_ids if value]
            actual_set = set(populated_path_ids)
            expected_set = set(expected_path_ids)
            duplicates = sorted(
                {
                    value
                    for value in populated_path_ids
                    if populated_path_ids.count(value) > 1
                }
            )
            missing_ids = sorted(expected_set - actual_set)
            unexpected_ids = sorted(actual_set - expected_set)
            identity_ok = bool(
                len(actual_path_ids) == expected_paths
                and len(populated_path_ids) == expected_paths
                and not duplicates
                and not missing_ids
                and not unexpected_ids
            )
            if not identity_ok:
                path_identity_gaps.append(
                    {
                        "criterion": item_id,
                        "missing": missing_ids,
                        "unexpected": unexpected_ids,
                        "duplicates": duplicates,
                    }
                )
        if (
            len(item_rows) == expected_paths
            and all(row.get("result") == "passed" for row in item_rows)
            and identity_ok
        ):
            passed += 1
        else:
            failed += 1

    retained = len(rows)
    missing = max(0, int(target["declared_count"]) - covered)
    boundary_bases = [
        str(row.get("boundary_basis") or "")
        for row in rows
        if row.get("boundary_basis")
    ]
    if target["boundary"] == "none" and any("zero HTTP requests" in value for value in boundary_bases):
        boundary_summary = "This proof stays local: no provider HTTP request is part of the retained path."
    elif target["boundary"] == "replay":
        boundary_summary = f"{retained} retained path(s) replay recorded provider traffic."
    elif target["boundary"] == "substitute":
        boundary_summary = f"{retained} retained path(s) use a controlled substitute at the external boundary."
    elif target["boundary"] == "direct":
        boundary_summary = f"{retained} retained path(s) call the real external dependency."
    else:
        boundary_summary = "This proof does not need an external participant."

    semantic_rule = gate_rule(contract, "semantic_coverage")
    semantic_status = "MET" if (passed == target["declared_count"] if semantic_rule == "ALL" else passed > 0) else "NOT MET"
    semantic_target = target["declared_count"] if semantic_rule == "ALL" else "≥ 1"

    rep_rule = gate_rule(contract, "representation")
    rep_values = [representation_label(row.get("representation")) for row in rows]
    rep_target = representation_label(target.get("representation"))
    rep_status, rep_matched = minimum_representation_status(
        rep_values,
        rep_target,
        rep_rule,
    )

    provenance_rule = gate_rule(contract, "provenance")
    provenance_values = [
        str(row.get("provenance") or "UNKNOWN").upper()
        if row.get("provenance_scope") == "full_chain"
        else "UNKNOWN"
        for row in rows
    ]
    provenance_status = quantified_status(provenance_values, "COMPLETE", provenance_rule)
    provenance_matched = sum(1 for value in provenance_values if value == "COMPLETE")

    producer_rule = gate_rule(contract, "producer_qualification")
    producer_values = [
        str(row.get("producer_qualification") or "UNKNOWN").upper()
        if row.get("producer_qualification_scope") == "full_chain"
        else "UNKNOWN"
        for row in rows
    ]
    producer_ids = sorted({
        producer_id
        for row in rows
        for producer_id in (row.get("producer_ids") or [])
    })
    producer_status = quantified_status(producer_values, "QUALIFIED", producer_rule)
    producer_matched = sum(1 for value in producer_values if value == "QUALIFIED")

    freshness_rule = gate_rule(contract, "freshness")
    freshness_values = [str(row.get("freshness") or "UNKNOWN").upper() for row in rows]
    freshness_status = quantified_status(freshness_values, "CURRENT", freshness_rule)
    freshness_matched = sum(1 for value in freshness_values if value == "CURRENT")

    ms_rule = gate_rule(contract, "ms_validation")
    ms_rows = [row for row in rows if representation_label(row.get("representation")) == "Surrogate / simulated"]
    ms_values = [ms_label(row.get("ms_validation")) for row in ms_rows]
    declared_ms_target = target.get("ms_validation_target") or target.get("ms_validation")
    if not ms_rows:
        ms_target = "N/A"
        ms_status = "N/A"
    elif declared_ms_target:
        ms_target = ms_label(str(declared_ms_target))
        ms_status, ms_matched = minimum_ms_status(ms_values, ms_target, ms_rule)
    else:
        ms_target = "NOT DECLARED"
        ms_status = "UNKNOWN"
        ms_matched = 0
    if not ms_rows:
        ms_matched = 0

    overall = combine([semantic_status, rep_status, provenance_status, producer_status, freshness_status, ms_status])
    return {
        "key": f"{target['level']}|{target['boundary']}",
        "level_label": target["level_label"],
        "boundary_label": target["boundary_label"],
        "overall": overall,
        "semantic_actual": passed,
        "semantic_target": semantic_target,
        "semantic_status": semantic_status,
        "semantic_rule": semantic_rule,
        "required_count": int(target["declared_count"]),
        "retained_count": retained,
        "required_path_count": required_path_count,
        "path_identity_gaps": path_identity_gaps,
        "failed_count": failed,
        "missing_count": missing,
        "boundary_summary": boundary_summary,
        "representation_actual_values": ordered_values(set(rep_values), REPRESENTATION),
        "representation_target": rep_target,
        "representation_status": rep_status,
        "representation_rule": rep_rule,
        "representation_matched": rep_matched,
        "provenance_actual_values": ordered_values(set(provenance_values), PROVENANCE),
        "provenance_status": provenance_status,
        "provenance_rule": provenance_rule,
        "provenance_matched": provenance_matched,
        "producer_actual_values": ordered_values(set(producer_values), PRODUCER),
        "producer_status": producer_status,
        "producer_rule": producer_rule,
        "producer_matched": producer_matched,
        "producer_count": len(producer_ids),
        "freshness_actual_values": ordered_values(set(freshness_values), FRESHNESS),
        "freshness_status": freshness_status,
        "freshness_rule": freshness_rule,
        "freshness_matched": freshness_matched,
        "ms_actual_values": ordered_values(set(ms_values), MS_LEVELS),
        "ms_target": ms_target,
        "ms_status": ms_status,
        "ms_rule": ms_rule,
        "ms_applicable_count": len(ms_rows),
        "ms_matched": ms_matched,
    }



def cell_inspector(state: dict) -> str:
    coverage = coverage_card(state)
    representation = lane(
        "Representation",
        REPRESENTATION,
        state["representation_actual_values"],
        state["representation_target"],
        state["representation_status"],
        "Checks that the evidence uses the required kind of target: synthetic, surrogate, representative, or actual.",
        state["representation_matched"],
        state["retained_count"],
    )
    ms = lane(
        "M&S validation",
        MS_LEVELS,
        state["ms_actual_values"],
        state["ms_target"],
        state["ms_status"],
        "Checks that any surrogate or model used as evidence is validated strongly enough for this target.",
        state["ms_matched"],
        state["ms_applicable_count"],
        "model paths",
        "dependent-signal",
    )
    confidence = "".join([
        lane(
            "Provenance",
            PROVENANCE,
            state["provenance_actual_values"],
            "COMPLETE",
            state["provenance_status"],
            "Checks that each result belongs to the exact test, run, source version, and artifact it claims.",
            state["provenance_matched"],
            state["retained_count"],
        ),
        lane(
            f'Producer qualification · {state["producer_count"]} producers',
            PRODUCER,
            state["producer_actual_values"],
            "QUALIFIED",
            state["producer_status"],
            "Checks that every evidence producer used by this proof is qualified for its role.",
            state["producer_matched"],
            state["retained_count"],
            "evidence paths",
        ),
        lane(
            "Freshness",
            FRESHNESS,
            state["freshness_actual_values"],
            "CURRENT",
            state["freshness_status"],
            "Checks that the evidence still matches the current code, tests, Gherkin, and verification policy.",
            state["freshness_matched"],
            state["retained_count"],
        ),
    ])
    signals = (
        ui.signal_group(
            title="Required evidence",
            body=coverage,
            class_name="primary-group",
        )
        + ui.signal_group(
            title="Retained path properties",
            body=(
                f'<div class="representation-stack">{representation}'
                f'<div class="dependent-wrap">{ms}</div></div>'
                + ui.confidence_subgroup(confidence)
            ),
            class_name="path-properties",
            scope=f'{state["retained_count"]}/{state["required_path_count"]} paths',
        )
    )
    return (
        ui.inspector_head(
            eyebrow="Selected verification cell",
            title=f'{state["level_label"]} × {state["boundary_label"]}',
            status=state["overall"],
        )
        + f'<div class="signal-grid">{signals}</div>'
        + ui.drilldowns(
            (
                ("Requirement ↗", CONTRACT_URL),
                ("Verification profile ↗", PROFILE_URL),
                ("Test model ↗", MODEL_URL),
                ("Raw facts ↗", "requirement-monitor-facts.json"),
            )
        )
    )


def fault_state(contract: dict, group: dict, policy: dict) -> dict:
    classes = contract["fault_actual"]["classes"]
    required = [item for item in group["items"] if item["state"] == "required"]
    if not required:
        return {"label": group["label"], "status": "N/A"}

    exercised = sum(1 for item in required if classes.get(item["id"], {}).get("exercised"))
    detected = sum(1 for item in required if classes.get(item["id"], {}).get("exercised") and classes.get(item["id"], {}).get("detected"))
    class_status = "MET" if exercised == len(required) else "NOT MET"
    detection_actual = 100.0 if exercised and detected == exercised else (0.0 if not exercised else detected * 100.0 / exercised)
    detection_status = "MET" if detection_actual == 100.0 else "NOT MET"

    mutation = []
    if group["label"] == "Implementation":
        for level_key, label in (("component", "Component"), ("system", "System")):
            actual = contract["fault_actual"]["groups"].get(f"{level_key}_local", {})
            checks = contract["target"].get("mutation", {}).get(level_key, {})
            if not (checks.get("reach") or checks.get("sensitivity")):
                continue
            generated = int(actual.get("generated", 0) or 0)
            reached = int(actual.get("reached", 0) or 0)
            killed = int(actual.get("killed", 0) or 0)
            reach = float(actual.get("mutation_reach", 0) or 0)
            sensitivity = float(actual.get("sensitivity", 0) or 0)
            reach_selected = bool(checks.get("reach"))
            sensitivity_selected = bool(checks.get("sensitivity"))
            reach_target_raw = policy.get("mutation_reach_floor")
            sensitivity_target_raw = policy.get("mutation_sensitivity_floor")
            reach_target = (
                float(reach_target_raw)
                if reach_target_raw is not None
                else None
            )
            sensitivity_target = (
                float(sensitivity_target_raw)
                if sensitivity_target_raw is not None
                else None
            )
            reach_status = (
                "N/A"
                if not reach_selected
                else (
                    "UNKNOWN"
                    if reach_target is None
                    else ("MET" if reach >= reach_target else "NOT MET")
                )
            )
            sensitivity_status = (
                "N/A"
                if not sensitivity_selected
                else (
                    "UNKNOWN"
                    if sensitivity_target is None
                    else (
                        "MET"
                        if sensitivity >= sensitivity_target
                        else "NOT MET"
                    )
                )
            )
            mutation.append({
                "label": label,
                "generated": generated,
                "reached": reached,
                "killed": killed,
                "reach": reach,
                "reach_selected": reach_selected,
                "reach_target": reach_target,
                "reach_status": reach_status,
                "sensitivity": sensitivity,
                "sensitivity_selected": sensitivity_selected,
                "sensitivity_target": sensitivity_target,
                "sensitivity_status": sensitivity_status,
            })

    mutation_statuses = [
        status
        for item in mutation
        for selected, status in (
            (item["reach_selected"], item["reach_status"]),
            (item["sensitivity_selected"], item["sensitivity_status"]),
        )
        if selected
    ]
    overall = combine([class_status, detection_status] + mutation_statuses)
    return {
        "label": group["label"],
        "status": overall,
        "required": len(required),
        "exercised": exercised,
        "detected": detected,
        "class_status": class_status,
        "detection_actual": detection_actual,
        "detection_status": detection_status,
        "mutation": mutation,
        "raw_url": contract["fault_actual"].get("raw_url")
        or "requirement-monitor-facts.json",
    }


def fault_stage(label: str, value: str, status: str | None = None, target: str | None = None) -> str:
    status_html = f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>' if status else ""
    target_html = f"<small>{esc(target)}</small>" if target else ""
    return (
        f'<div class="fault-stage {status_class(status) if status else "neutral"}">'
        f'<span>{esc(label)}</span>'
        f'<strong>{esc(value)}</strong>{target_html}{status_html}</div>'
    )


def fault_inspector(state: dict) -> str:
    class_chain = (
        '<div class="fault-chain">'
        + fault_stage("Required", str(state["required"]))
        + "<i>→</i>"
        + fault_stage(
            "Challenged",
            f'{state["exercised"]}/{state["required"]}',
            state["class_status"],
        )
        + "<i>→</i>"
        + fault_stage(
            "Detected",
            f'{state["detected"]}/{state["exercised"]}' if state["exercised"] else "0/0",
            state["detection_status"],
        )
        + "</div>"
    )
    sections = [
        ui.signal_group(
            title="Fault classes",
            body=class_chain,
            class_name="fault-class-group",
        )
    ]
    if state.get("mutation"):
        cards = []
        for item in state["mutation"]:
            cards.append(
                '<div class="mutation-chain">'
                f'<div class="mutation-chain-head"><strong>{esc(item["label"])} mutation</strong></div>'
                '<div class="fault-chain">'
                + fault_stage("Generated", str(item["generated"]))
                + "<i>→</i>"
                + fault_stage(
                    "Reached",
                    f'{item["reached"]}/{item["generated"]}',
                    item["reach_status"],
                    target=f'{item["reach"]:.1f}% · ≥ {item["reach_target"]:.0f}%',
                )
                + "<i>→</i>"
                + fault_stage(
                    "Killed",
                    f'{item["killed"]}/{item["reached"]}' if item["reached"] else "0/0",
                    item["sensitivity_status"],
                    target=f'{item["sensitivity"]:.1f}% · ≥ {item["sensitivity_target"]:.0f}%',
                )
                + "</div></div>"
            )
        sections.append(
            ui.signal_group(
                title="Mutation checks",
                body=f'<div class="mutation-grid">{"".join(cards)}</div>',
                class_name="mutation-group",
            )
        )
    fault_profile_url = PROFILE_URL.split("#", 1)[0] + "#fault-applicability"
    links = [
        ("Verification profile ↗", fault_profile_url),
        ("Fault model ↗", "test-plan.html#test-plan-fault-model"),
        (
            "Raw facts ↗",
            str(state.get("raw_url") or "requirement-monitor-facts.json"),
        ),
    ]
    if state["label"] == "Implementation" and MUTATION_URL:
        links.insert(2, ("Mutation analysis ↗", MUTATION_URL))
    return (
        ui.inspector_head(
            eyebrow="Selected fault group",
            title=state["label"],
            status=state["status"],
        )
        + f'<div class="signal-grid fault-signals">{"".join(sections)}</div>'
        + ui.drilldowns(tuple(links))
    )


def domain_meta(states: list[str]) -> str:
    parts = []
    for value in ("NOT MET", "UNKNOWN", "MET", "N/A"):
        count = states.count(value)
        if count:
            parts.append(f"{count} {status_label(value).lower()}")
    return " · ".join(parts)


def contract_slug(contract_id: str) -> str:
    slug = contract_id.lower()
    for prefix in ("treq_", "req_"):
        if slug.startswith(prefix):
            slug = slug.removeprefix(prefix)
            break
    return slug.replace("_", "-")


def contract_output_path(contract_id: str) -> Path:
    if contract_id == PRIMARY_CONTRACT_ID:
        return CANONICAL_OUT
    return CANONICAL_OUT.with_name(f"contract-evidence-{contract_slug(contract_id)}.html")


def contract_domain_state(contract: dict, policy: dict) -> dict:
    """Return direct Verification/Fault/Overall state for one first-class contract."""
    coverage_states = [
        cell_state(contract, target)["overall"]
        for target in (contract.get("target") or {}).get("coverage", [])
    ]
    fault_states = [
        fault_state(contract, group, policy)["status"]
        for group in (contract.get("target") or {}).get("fault_groups", [])
    ]
    coverage = combine(coverage_states)
    fault = combine(fault_states)
    return {
        "coverage": coverage,
        "coverage_states": coverage_states,
        "fault": fault,
        "fault_states": fault_states,
        "overall": combine([coverage, fault]),
    }


def render_current() -> None:
    global CONTRACT_URL, MODEL_URL, MUTATION_URL, PROFILE_URL

    data = json.loads(FACTS.read_text())
    for contract_data in (data.get("contracts") or {}).values():
        for rows in (contract_data.get("coverage_actual") or {}).values():
            for row in rows:
                row.setdefault("provenance_scope", "traceability_only")
                row.setdefault("producer_qualification_scope", "runner_only")
    contract = data["contracts"][CONTRACT_ID]
    policy = data["policy"]
    target = contract["target"]
    is_treq = CONTRACT_ID.startswith("TREQ_")
    contract_noun = "Technical requirement" if is_treq else "Requirement"
    page_title = "Technical Assurance" if is_treq else "Contract Evidence"
    CONTRACT_URL = contract.get("contract_url") or f"requirements/configuration.html#{CONTRACT_ID}"
    PROFILE_URL = target.get("profile_url") or target.get("source_url") or "verification-profiles/index.html"
    MODEL_URL = target.get("model_url") or "test-plan.html#test-plan"
    mutation_selected = any(
        check.get("reach") or check.get("sensitivity")
        for check in (target.get("mutation") or {}).values()
    )
    MUTATION_URL = (
        f"mutation-analysis.html#mutation-{CONTRACT_ID.lower()}" if mutation_selected else None
    )

    cells = {}
    for coverage_target in contract["target"]["coverage"]:
        state = cell_state(contract, coverage_target)
        cells[state["key"]] = state
    cell_statuses = [state["overall"] for state in cells.values()]
    cell_domain = combine(cell_statuses)

    faults = {}
    for index, group in enumerate(contract["target"]["fault_groups"]):
        faults[str(index)] = fault_state(contract, group, policy)
    fault_statuses = [state["status"] for state in faults.values()]
    fault_domain = combine(fault_statuses)

    required_treqs = list(target.get("required_treqs") or [])
    technical_support_rows = []
    for treq_id in required_treqs:
        child = (data.get("contracts") or {}).get(treq_id)
        if child is None:
            state = {
                "coverage": "UNKNOWN",
                "fault": "UNKNOWN",
                "overall": "UNKNOWN",
            }
        else:
            state = contract_domain_state(child, policy)
        technical_support_rows.append(
            {
                "id": treq_id,
                "title": (child or {}).get("title") or treq_id,
                "status": state["overall"],
                "coverage": state["coverage"],
                "fault": state["fault"],
                "href": contract_output_path(treq_id).name,
            }
        )
    technical_support_status = (
        combine([row["status"] for row in technical_support_rows])
        if technical_support_rows
        else "N/A"
    )
    overall_inputs = [cell_domain, fault_domain]
    if technical_support_rows:
        overall_inputs.append(technical_support_status)
    overall = combine(overall_inputs)

    matrix_rows = []
    for level, level_label in LEVELS:
        row = [f'<th scope="row">{esc(level_label)}</th>']
        for boundary, _ in BOUNDARIES:
            state = cells.get(f"{level}|{boundary}")
            if not state:
                row.append('<td><div class="matrix-cell na" aria-disabled="true"><span>N/A</span></div></td>')
            else:
                row.append(
                    '<td>'
                    f'<button class="matrix-cell {status_class(state["overall"])}" type="button" data-cell="{esc(state["key"])}">'
                    f'<span class="cell-status status {status_class(state["overall"])}">{esc(status_label(state["overall"]))}</span>'
                    '<span class="cell-values">'
                    f'<span><small>Passing</small><strong>{state["semantic_actual"]}</strong></span>'
                    f'<span><small>Required</small><strong>{state["required_count"]}</strong></span>'
                    '</span></button></td>'
                )
        matrix_rows.append(f'<tr>{"".join(row)}</tr>')

    fault_tiles = []
    for key, state in faults.items():
        group_help = FAULT_GROUP_HELP[state["label"]]
        if state["status"] == "N/A":
            fault_tiles.append(
                '<div class="fault-tile na" aria-disabled="true">'
                f'<div class="tile-head"><strong>{esc(state["label"])} {help_tip(group_help, focusable=False)}</strong><span class="status na">N/A</span></div>'
                '<div class="na-center">N/A</div></div>'
            )
            continue
        secondary_label = "Detection"
        secondary_actual = f'{state["detection_actual"]:.0f}%'
        secondary_target = "100%"
        secondary_status = state["detection_status"]
        if state["label"] == "Implementation":
            component_sensitivity = next(
                (item for item in state["mutation"] if item["label"] == "Component"),
                None,
            )
            if component_sensitivity and component_sensitivity.get("sensitivity_selected"):
                secondary_label = "C sensitivity"
                secondary_actual = f'{component_sensitivity["sensitivity"]:.1f}%'
                secondary_target = (
                    f'≥{component_sensitivity["sensitivity_target"]:.0f}%'
                )
                secondary_status = component_sensitivity["sensitivity_status"]
        fault_tiles.append(
            f'<button class="fault-tile {status_class(state["status"])}" type="button" data-fault="{key}">'
            f'<div class="tile-head"><strong>{esc(state["label"])} {help_tip(group_help, focusable=False)}</strong><span class="status {status_class(state["status"])}">{esc(status_label(state["status"]))}</span></div>'
            '<div class="tile-metrics">'
            f'<div><span>Classes</span><strong>{state["exercised"]}</strong><i>/ {state["required"]}</i></div>'
            f'<div class="{status_class(secondary_status)}"><span>{esc(secondary_label)}</span><strong>{esc(secondary_actual)}</strong><i>{esc(secondary_target)}</i></div>'
            '</div></button>'
        )

    cell_inspectors = {key: cell_inspector(state) for key, state in cells.items()}
    fault_inspectors = {key: fault_inspector(state) for key, state in faults.items() if state["status"] != "N/A"}
    default_cell = next(iter(cell_inspectors))
    default_fault = next(iter(fault_inspectors), None)
    fault_inspector_markup = (
        f'<aside class="inspector" id="fault-inspector">{fault_inspectors[default_fault]}</aside>'
        if default_fault is not None
        else ""
    )
    fault_layout_class = "fault-layout" if default_fault is not None else "fault-layout no-inspector"

    contract_key = CONTRACT_ID.lower()
    coverage_domain_card = ui.domain_card(
        label="Verification coverage",
        status=cell_domain,
        href=f"#ce-coverage-{contract_key}",
        meta=domain_meta(cell_statuses),
    )
    fault_domain_card = ui.domain_card(
        label="Fault model",
        status=fault_domain,
        href=f"#ce-faults-{contract_key}",
        meta=domain_meta(fault_statuses),
    )
    technical_support_section = ""
    domain_strip_class = "domain-strip"
    technical_support_domain_card = ""
    if technical_support_rows:
        domain_strip_class += " with-support"
        technical_support_domain_card = ui.domain_card(
            label="Technical support",
            status=technical_support_status,
            href=f"#ce-technical-support-{contract_key}",
            meta=(
                f'{sum(row["status"] == "MET" for row in technical_support_rows)} '
                f'/ {len(technical_support_rows)} pass'
            ),
        )
        technical_cards = []
        for row in technical_support_rows:
            technical_cards.append(
                ui.technical_support_card(
                    item_id=row["id"],
                    title=row["title"],
                    status=row["status"],
                    href=row["href"],
                    metrics=(
                        ("Verification", status_label(row["coverage"])),
                        ("Fault model", status_label(row["fault"])),
                    ),
                )
            )
        technical_support_section = (
            f'<section class="section" id="ce-technical-support-{contract_key}">'
            + ui.section_head(
                title="Technical support",
                links=(
                    ("Profile ↗", PROFILE_URL),
                    ("Raw ↗", "requirement-monitor-facts.json"),
                ),
            )
            + ui.support_panel("".join(technical_cards))
            + "</section>"
        )

    history_section = ui.history_section(
        section_id=f"ce-history-{contract_key}",
        status=overall,
        link_href="assurance-snapshots.json",
        link_label="History ↗",
    )
    verdict_header = ui.verdict_header(
        kicker="Verification status",
        entity_id=CONTRACT_ID,
        status=overall,
        domain_cards=(
            coverage_domain_card + fault_domain_card + technical_support_domain_card
        ),
        domain_strip_class=domain_strip_class,
    )
    coverage_section_head = ui.section_head(
        title="Verification matrix",
        links=(
            (f"{contract_noun} ↗", CONTRACT_URL),
            ("Profile ↗", PROFILE_URL),
            ("Raw ↗", "requirement-monitor-facts.json"),
        ),
    )
    fault_section_head = ui.section_head(
        title="Fault model",
        links=(
            ("Profile ↗", PROFILE_URL),
            ("Model ↗", "test-plan.html#test-plan-fault-model"),
            ("Raw ↗", "requirement-monitor-facts.json"),
        ),
    )

    monitor = f"""<div id="tf-requirement-monitor">
{verdict_header}
<section class="section" id="ce-coverage-{contract_key}">{coverage_section_head}<div class="dashboard-layout"><div class="panel matrix-wrap"><table><thead><tr><th>Test level</th>{''.join(f'<th>{esc(label)}</th>' for _, label in BOUNDARIES)}</tr></thead><tbody>{''.join(matrix_rows)}</tbody></table></div><aside class="inspector" id="cell-inspector">{cell_inspectors[default_cell]}</aside></div></section>
<section class="section" id="ce-faults-{contract_key}">{fault_section_head}<div class="{fault_layout_class}"><div class="fault-grid">{''.join(fault_tiles)}</div>{fault_inspector_markup}</div></section>
{technical_support_section}
{history_section}
</div>"""

    style = ui.MONITOR_STYLE

    setup_js = (
        f"const cellInspectors={json.dumps(cell_inspectors, ensure_ascii=False)};"
        f"const faultInspectors={json.dumps(fault_inspectors, ensure_ascii=False)};"
    )
    bind_js = (
        "function selectCell(key){const value=cellInspectors[key];if(!value)return;"
        "root.querySelector('#cell-inspector').innerHTML=value;"
        "root.querySelectorAll('[data-cell]').forEach(button=>button.classList.toggle('selected',button.dataset.cell===key));}"
        "function selectFault(key){const value=faultInspectors[key];if(!value)return;"
        "root.querySelector('#fault-inspector').innerHTML=value;"
        "root.querySelectorAll('[data-fault]').forEach(button=>button.classList.toggle('selected',button.dataset.fault===key));}"
        "root.querySelectorAll('[data-cell]').forEach(button=>button.addEventListener('click',()=>selectCell(button.dataset.cell)));"
        "root.querySelectorAll('[data-fault]').forEach(button=>button.addEventListener('click',()=>selectFault(button.dataset.fault)));"
    )
    nav_selector = (
        f'a[href="#ce-coverage-{contract_key}"],a[href="#ce-faults-{contract_key}"],'
        f'a[href="#ce-technical-support-{contract_key}"],a[href="#ce-history-{contract_key}"]'
    )
    init_js = f"selectCell({json.dumps(default_cell)});selectFault({json.dumps(default_fault)});"
    script = ui.monitor_script(
        setup_js=setup_js,
        bind_js=bind_js,
        nav_selector=nav_selector,
        init_js=init_js,
    )

    source = CANONICAL_OUT.read_text()
    source = re.sub(
        r"<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-START -->.*?<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-END -->",
        "", source, flags=re.DOTALL,
    )
    source = re.sub(
        r'<style id="tf-requirement-monitor-style">.*?</style>', "", source, flags=re.DOTALL,
    )
    source = re.sub(
        r'<script id="tf-requirement-monitor-script">.*?</script>', "", source, flags=re.DOTALL,
    )
    article = f"""<section id="assurance-{CONTRACT_ID.lower()}">
<h1>{esc(page_title)}<a class="headerlink" href="#assurance-{CONTRACT_ID.lower()}" title="Link to this heading">#</a></h1>
{monitor}
</section>"""
    source, count = re.subn(
        r'(<article class="bd-article">).*?(</article>)',
        lambda match: match.group(1) + article + match.group(2),
        source,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("Could not replace canonical Contract Evidence article body")
    source = source.replace("</head>", style + "\n</head>", 1)
    source = source.replace("</body>", script + "\n</body>", 1)
    source = source.replace(
        '<span class="ellipsis">Contract Evidence · Experiment</span>',
        f'<span class="ellipsis">{esc(page_title)}</span>',
    )
    source = re.sub(
        r"<title>Contract Evidence · Experiment — llm-router documentation</title>",
        f"<title>{esc(page_title)} — llm-router documentation</title>",
        source, count=1,
    )
    technical_support_toc = (
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" '
        f'href="#ce-technical-support-{CONTRACT_ID.lower()}">Technical support</a></li>'
        if technical_support_rows
        else ""
    )
    secondary = (
        '<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc"><div class="sidebar-secondary-items sidebar-secondary__inner">'
        '<div class="sidebar-secondary-item"><div class="tocsection onthispage"><i class="fa-solid fa-list"></i> On this page</div>'
        '<nav class="bd-toc-nav page-toc"><ul class="visible nav section-nav flex-column">'
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#ce-coverage-{CONTRACT_ID.lower()}">Verification matrix</a></li>'
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#ce-faults-{CONTRACT_ID.lower()}">Fault model</a></li>'
        f"{technical_support_toc}"
        f'<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#ce-history-{CONTRACT_ID.lower()}">History</a></li>'
        '</ul></nav></div></div></div>'
    )
    source, sidebar_count = re.subn(
        r'<div id="pst-secondary-sidebar" class="bd-sidebar-secondary bd-toc">.*?</div></div>\s*</div>\s*<footer class="bd-footer-content">',
        secondary + '\n</div>\n<footer class="bd-footer-content">',
        source, count=1, flags=re.DOTALL,
    )
    if sidebar_count != 1:
        raise RuntimeError("Could not replace canonical secondary sidebar")
    OUT.write_text(source)
    OUT.with_name("verification-assurance-experiment.html").unlink(missing_ok=True)
    OUT.with_name("requirement-monitor-experiment-facts.json").unlink(missing_ok=True)
    print(OUT)


def build() -> None:
    global CONTRACT_ID, OUT

    data = json.loads(FACTS.read_text())
    contract_ids = list((data.get("contracts") or {}).keys())
    if PRIMARY_CONTRACT_ID not in contract_ids:
        raise RuntimeError(f"Missing primary Requirement monitor contract: {PRIMARY_CONTRACT_ID}")
    ordered = [PRIMARY_CONTRACT_ID] + sorted(
        contract_id for contract_id in contract_ids if contract_id != PRIMARY_CONTRACT_ID
    )
    expected_outputs = {contract_output_path(contract_id) for contract_id in ordered}
    for stale in CANONICAL_OUT.parent.glob("contract-evidence-*.html"):
        if stale not in expected_outputs:
            stale.unlink()
    for contract_id in ordered:
        CONTRACT_ID = contract_id
        OUT = contract_output_path(contract_id)
        render_current()


if __name__ == "__main__":
    build()
