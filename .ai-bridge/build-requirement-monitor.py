from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
PRODUCER = ["QUALIFIED", "NOT QUALIFIED", "UNKNOWN"]
FRESHNESS = ["CURRENT", "STALE", "UNKNOWN"]
FAULT_GROUP_HELP = {
    "Implementation": "Checks that small code mistakes—wrong comparisons, limits, branches, returns, or exception paths—are caught.",
    "Runtime / dependency": "Checks that dependency failures—timeouts, disconnects, unavailability, or malformed replies—cannot change the required behavior.",
    "Interface / protocol": "Checks that wrong external calls, error statuses, or malformed payloads are caught at the boundary.",
    "Architecture": "Checks that code cannot bypass a required layer or depend on a forbidden layer.",
    "Specification / model": "Checks that tests catch the wrong result, a missing case, or the wrong ordering or boundary rule.",
}
MS_LEVELS = ["N/A", "L0", "L1", "L2", "L3", "L4", "UNKNOWN", "NOT DECLARED"]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def help_tip(text: str, *, focusable: bool = True) -> str:
    tabindex = ' tabindex="0"' if focusable else ""
    return f'<span class="help"{tabindex}>?<span class="help-tip">{esc(text)}</span></span>'


def status_class(status: str) -> str:
    return {"MET": "met", "NOT MET": "not-met", "UNKNOWN": "unknown", "N/A": "na"}.get(status, "unknown")


def status_label(status: str) -> str:
    return {"MET": "PASS", "NOT MET": "FAIL", "UNKNOWN": "UNKNOWN", "N/A": "N/A"}.get(status, status)


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


def marker(actual: bool, target: bool) -> str:
    if actual and target:
        return '<span class="marker both">ACTUAL = TARGET</span>'
    result = []
    if actual:
        result.append('<span class="marker actual">ACTUAL</span>')
    if target:
        result.append('<span class="marker target">TARGET</span>')
    return "".join(result)


def scope_count(matched: int, total: int, status: str, label: str = "paths") -> str:
    shown_label = label
    if total == 1 and label == "paths":
        shown_label = "path"
    elif total == 1 and label == "evidence paths":
        shown_label = "evidence path"
    elif total == 1 and label == "model paths":
        shown_label = "model path"
    if status == "N/A":
        return f'<span class="scope-count na"><b>{total}</b><small>{esc(shown_label)}</small></span>'
    return f'<span class="scope-count {status_class(status)}"><b>{matched}/{total}</b><small>{esc(shown_label)}</small></span>'


def state_option_label(signal: str, option: str) -> str:
    if signal == "M&S validation":
        return {
            "N/A": "N/A",
            "L0": "L0",
            "L1": "L1",
            "L2": "L2",
            "L3": "L3",
            "L4": "L4",
            "UNKNOWN": "UNKNOWN",
            "NOT DECLARED": "NOT DECLARED",
        }.get(option, option)
    return option


def lane(
    label: str,
    options: list[str],
    actual_values: list[str],
    target: str,
    status: str,
    tip: str,
    matched: int,
    total: int,
    scope_label: str = "paths",
    extra_class: str = "",
) -> str:
    actual_set = set(actual_values)
    cells = []
    for option in options:
        is_actual = option in actual_set
        is_target = option == target
        selected = " selected" if is_actual or is_target else ""
        display = state_option_label(label, option)
        if status == "N/A" and option == "N/A":
            option_marker = '<span class="marker inactive">INACTIVE</span>'
        else:
            option_marker = marker(is_actual, is_target)
        cells.append(f'<span class="state-option{selected}"><span>{esc(display)}</span>{option_marker}</span>')
    class_name = f"signal-card {status_class(status)}-signal {extra_class}".strip()
    return (
        f'<div class="{esc(class_name)}">'
        f'<div class="signal-head"><strong>{esc(label)} <span class="help" tabindex="0">?<span class="help-tip">{esc(tip)}</span></span></strong>'
        f'<span class="signal-rule">{scope_count(matched, total, status, scope_label)}<span class="status {status_class(status)}">{esc(status_label(status))}</span></span></div>'
        f'<div class="state-lane">{"".join(cells)}</div></div>'
    )


def metric(label: str, actual: str, target: str, status: str, tip: str = "", rule: str | None = None, subject: str = "items") -> str:
    help_html = f' <span class="help" tabindex="0">?<span class="help-tip">{esc(tip)}</span></span>' if tip else ""
    return (
        f'<div class="signal-card metric-card {status_class(status)}-signal">'
        f'<div class="signal-head"><strong>{esc(label)}{help_html}</strong><span class="signal-rule"><span class="status {status_class(status)}">{esc(status_label(status))}</span></span></div>'
        '<div class="metric-values">'
        f'<div><span>Actual</span><strong>{esc(actual)}</strong></div>'
        f'<div><span>Target</span><strong>{esc(target)}</strong></div>'
        '</div></div>'
    )


def coverage_card(
    state: dict,
    *,
    label: str = "Semantic coverage",
    subject: str = "criteria",
    retained_subject: str = "paths",
    tip: str = "Checks that every required behavior has the exact evidence path or paths declared by the profile.",
) -> str:
    segments = (
        '<span class="coverage-segment pass"></span>' * state["semantic_actual"]
        + '<span class="coverage-segment fail"></span>' * state["failed_count"]
        + '<span class="coverage-segment missing"></span>' * state["missing_count"]
    )
    return (
        f'<div class="signal-card coverage-card {status_class(state["semantic_status"])}-signal">'
        f'<div class="signal-head"><strong>{esc(label)} {help_tip(tip)}</strong>'
        f'<span class="status {status_class(state["semantic_status"])}">{esc(status_label(state["semantic_status"]))}</span></div>'
        '<div class="coverage-summary">'
        f'<strong>{state["semantic_actual"]}<span>/</span>{state["required_count"]}</strong><small>{esc(subject)} passing</small>'
        '</div>'
        f'<div class="coverage-strip">{segments}</div>'
        '<div class="coverage-counts">'
        f'<span class="pass">{state["semantic_actual"]} {esc(subject)} pass</span>'
        f'<span class="fail">{state["failed_count"]} {esc(subject)} fail</span>'
        f'<span class="missing">{state["missing_count"]} {esc(subject)} missing</span>'
        f'<span>{state["retained_count"]}/{state["required_path_count"]} {esc(retained_subject)} retained</span>'
        f'</div></div>'
    )


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
        '<div class="signal-group primary-group"><div class="signal-group-head"><strong>Required evidence</strong></div>'
        f'{coverage}</div>'
        '<div class="signal-group path-properties"><div class="signal-group-head"><strong>Retained path properties</strong>'
        f'<span class="group-scope">{state["retained_count"]}/{state["required_path_count"]} paths</span></div>'
        f'<div class="representation-stack">{representation}<div class="dependent-wrap">{ms}</div></div>'
        '<div class="confidence-subgroup"><div class="subgroup-head"><strong>Evidence confidence</strong></div>'
        f'<div class="confidence-grid">{confidence}</div></div></div>'
    )
    return (
        '<div class="inspector-head">'
        f'<div><span class="eyebrow">Selected verification cell</span><h3>{esc(state["level_label"])} × {esc(state["boundary_label"])}</h3></div>'
        f'<span class="status big {status_class(state["overall"])}">{esc(status_label(state["overall"]))}</span></div>'
        f'<div class="signal-grid">{signals}</div>'
        f'<div class="drilldowns"><a href="{esc(CONTRACT_URL)}">Requirement ↗</a>'
        f'<a href="{esc(PROFILE_URL)}">Verification profile ↗</a>'
        f'<a href="{esc(MODEL_URL)}">Test model ↗</a>'
        '<a href="requirement-monitor-facts.json">Raw facts ↗</a></div>'
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
        '<div class="signal-group fault-class-group"><div class="signal-group-head"><strong>Fault classes</strong></div>'
        + class_chain
        + "</div>"
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
            '<div class="signal-group mutation-group"><div class="signal-group-head"><strong>Mutation checks</strong></div>'
            f'<div class="mutation-grid">{"".join(cards)}</div></div>'
        )
    fault_profile_url = PROFILE_URL.split("#", 1)[0] + "#fault-applicability"
    links = [
        f'<a href="{esc(fault_profile_url)}">Verification profile ↗</a>',
        '<a href="test-plan.html#test-plan-fault-model">Fault model ↗</a>',
        f'<a href="{esc(str(state.get("raw_url") or "requirement-monitor-facts.json"))}">Raw facts ↗</a>',
    ]
    if state["label"] == "Implementation" and MUTATION_URL:
        links.insert(2, f'<a href="{esc(MUTATION_URL)}">Mutation analysis ↗</a>')
    return (
        '<div class="inspector-head">'
        f'<div><span class="eyebrow">Selected fault group</span><h3>{esc(state["label"])}</h3></div>'
        f'<span class="status big {status_class(state["status"])}">{esc(status_label(state["status"]))}</span></div>'
        f'<div class="signal-grid fault-signals">{"".join(sections)}</div>'
        f'<div class="drilldowns">{"".join(links)}</div>'
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
    coverage_card = (
        f'<a class="domain" href="#ce-coverage-{contract_key}">'
        "<strong>Verification coverage</strong>"
        f'<span class="status {status_class(cell_domain)}">{esc(status_label(cell_domain))}</span>'
        f'<span class="domain-meta">{esc(domain_meta(cell_statuses))}</span></a>'
    )
    fault_card = (
        f'<a class="domain" href="#ce-faults-{contract_key}">'
        "<strong>Fault model</strong>"
        f'<span class="status {status_class(fault_domain)}">{esc(status_label(fault_domain))}</span>'
        f'<span class="domain-meta">{esc(domain_meta(fault_statuses))}</span></a>'
    )
    technical_support_section = ""
    domain_strip_class = "domain-strip"
    technical_support_card = ""
    if technical_support_rows:
        domain_strip_class += " with-support"
        technical_support_card = (
            f'<a class="domain" href="#ce-technical-support-{contract_key}">'
            "<strong>Technical support</strong>"
            f'<span class="status {status_class(technical_support_status)}">'
            f"{esc(status_label(technical_support_status))}</span>"
            f'<span class="domain-meta">{sum(row["status"] == "MET" for row in technical_support_rows)} '
            f'/ {len(technical_support_rows)} pass</span></a>'
        )
        technical_cards = []
        for row in technical_support_rows:
            technical_cards.append(
                f'<a class="signal-card {status_class(row["status"])}-signal technical-support-card" '
                f'href="{esc(row["href"])}">'
                '<div class="signal-head">'
                f'<strong>{esc(row["id"])}</strong>'
                f'<span class="status {status_class(row["status"])}">'
                f"{esc(status_label(row['status']))}</span></div>"
                f'<div class="coverage-summary"><small>{esc(row["title"])}</small></div>'
                '<div class="metric-values">'
                f'<div><span>Verification</span><strong>{esc(status_label(row["coverage"]))}</strong></div>'
                f'<div><span>Fault model</span><strong>{esc(status_label(row["fault"]))}</strong></div>'
                "</div></a>"
            )
        technical_support_section = (
            f'<section class="section" id="ce-technical-support-{contract_key}">'
            '<div class="section-head"><h3>Technical support</h3>'
            f'<div class="section-links"><a class="section-link" href="{esc(PROFILE_URL)}">Profile ↗</a>'
            '<a class="section-link" href="requirement-monitor-facts.json">Raw ↗</a></div></div>'
            '<div class="panel technical-support-panel"><div class="signal-grid">'
            f'{"".join(technical_cards)}</div></div></section>'
        )

    monitor = f"""<div id="tf-requirement-monitor">
<header class="verdict"><div class="verdict-main"><div><div class="kicker">Verification status</div><h2>{esc(CONTRACT_ID)}</h2></div><div class="overall {status_class(overall)}">{esc(status_label(overall))}</div></div><div class="{domain_strip_class}">{coverage_card}{fault_card}{technical_support_card}</div></header>
<section class="section" id="ce-coverage-{contract_key}"><div class="section-head"><h3>Verification matrix</h3><div class="section-links"><a class="section-link" href="{esc(CONTRACT_URL)}">{esc(contract_noun)} ↗</a><a class="section-link" href="{esc(PROFILE_URL)}">Profile ↗</a><a class="section-link" href="requirement-monitor-facts.json">Raw ↗</a></div></div><div class="dashboard-layout"><div class="panel matrix-wrap"><table><thead><tr><th>Test level</th>{''.join(f'<th>{esc(label)}</th>' for _, label in BOUNDARIES)}</tr></thead><tbody>{''.join(matrix_rows)}</tbody></table></div><aside class="inspector" id="cell-inspector">{cell_inspectors[default_cell]}</aside></div></section>
<section class="section" id="ce-faults-{contract_key}"><div class="section-head"><h3>Fault model</h3><div class="section-links"><a class="section-link" href="{esc(PROFILE_URL)}">Profile ↗</a><a class="section-link" href="test-plan.html#test-plan-fault-model">Model ↗</a><a class="section-link" href="requirement-monitor-facts.json">Raw ↗</a></div></div><div class="{fault_layout_class}"><div class="fault-grid">{''.join(fault_tiles)}</div>{fault_inspector_markup}</div></section>
{technical_support_section}
<section class="section" id="ce-history-{contract_key}"><div class="section-head"><h3>History</h3><a class="section-link" href="assurance-snapshots.json">History ↗</a></div><div class="panel history"><strong>Current</strong><div class="history-line"><i class="history-point {status_class(overall)}"></i></div><span class="status {status_class(overall)}">{esc(status_label(overall))}</span></div></section>
</div>"""

    style = """<style id="tf-requirement-monitor-style">
.bd-article-container{overflow:visible!important}
#tf-requirement-monitor{--surface:var(--pst-color-surface);--surface2:color-mix(in srgb,var(--pst-color-surface) 88%,var(--pst-color-background));--text:var(--pst-color-text-base);--muted:var(--pst-color-text-muted);--line:var(--pst-color-border);--green:#2e9d58;--red:#d24b4b;--amber:var(--pst-color-warning);--blue:var(--pst-color-primary);--shadow:0 .35rem 1rem color-mix(in srgb,#000 9%,transparent);--sticky-top:var(--pst-header-height,4rem);color:var(--text);font-size:.86rem;line-height:1.35}
#tf-requirement-monitor *{box-sizing:border-box}#tf-requirement-monitor button{font:inherit;color:inherit}#tf-requirement-monitor a{color:inherit}.tf-exp-badge{display:inline-block;margin-left:.45rem;padding:.12rem .28rem;border:1px solid var(--pst-color-border);border-radius:.25rem;color:var(--pst-color-text-muted);font-size:.55rem;font-weight:800;letter-spacing:.06em;vertical-align:.18rem}
#tf-requirement-monitor .verdict{position:sticky;top:var(--sticky-top);z-index:24;margin:.35rem 0 1rem;padding:.75rem .85rem;background:color-mix(in srgb,var(--pst-color-background) 94%,transparent);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:.45rem;box-shadow:var(--shadow)}#tf-requirement-monitor .verdict-main{display:flex;align-items:center;justify-content:space-between;gap:1rem}#tf-requirement-monitor .kicker,#tf-requirement-monitor .eyebrow{font-size:.62rem;font-weight:800;letter-spacing:.075em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor h2{font-size:1rem;margin:.1rem 0 0}#tf-requirement-monitor h3{font-size:.86rem;letter-spacing:.04em;text-transform:uppercase;margin:0}#tf-requirement-monitor .overall{font-size:.92rem;font-weight:900;padding:.42rem .65rem;border-radius:.45rem;border:1px solid var(--line);background:var(--surface);color:var(--muted)}#tf-requirement-monitor .overall.not-met{border-color:color-mix(in srgb,var(--red) 65%,var(--line));background:color-mix(in srgb,var(--red) 9%,var(--surface));color:var(--red)}#tf-requirement-monitor .overall.met{border-color:color-mix(in srgb,var(--green) 60%,var(--line));background:color-mix(in srgb,var(--green) 8%,var(--surface));color:var(--green)}#tf-requirement-monitor .overall.unknown{border-color:color-mix(in srgb,var(--amber) 60%,var(--line));background:color-mix(in srgb,var(--amber) 8%,var(--surface));color:var(--amber)}
#tf-requirement-monitor .domain-strip{display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.55rem}#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .domain{display:grid;grid-template-columns:1fr auto;gap:.12rem .5rem;align-items:center;padding:.45rem .55rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface);text-decoration:none}#tf-requirement-monitor .domain:hover{border-color:var(--blue)}#tf-requirement-monitor .domain strong{font-size:.67rem;text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}#tf-requirement-monitor .domain-meta{grid-column:1/-1;font-size:.58rem;color:var(--muted)}#tf-requirement-monitor .status{font-size:.63rem;font-weight:900;letter-spacing:.02em;white-space:nowrap}#tf-requirement-monitor .status.met{color:var(--green)}#tf-requirement-monitor .status.not-met{color:var(--red)}#tf-requirement-monitor .status.unknown{color:var(--amber)}#tf-requirement-monitor .status.na{color:var(--muted)}#tf-requirement-monitor .status.big{font-size:.72rem}
#tf-requirement-monitor .section{position:relative;margin-top:1rem;scroll-margin-top:calc(var(--sticky-top) + 8.7rem);border-radius:.55rem}#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash 1.6s ease-out}@keyframes tf-destination-flash{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}16%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 72%,transparent)}68%{box-shadow:0 0 0 2px color-mix(in srgb,var(--blue) 42%,transparent)}100%{box-shadow:0 0 0 0 color-mix(in srgb,var(--blue) 0%,transparent)}}@media(prefers-reduced-motion:reduce){#tf-requirement-monitor .section.nav-flash{animation:tf-destination-flash-reduced .8s linear}}@keyframes tf-destination-flash-reduced{0%,70%{box-shadow:0 0 0 3px color-mix(in srgb,var(--blue) 58%,transparent)}100%{box-shadow:0 0 0 0 transparent}}#tf-requirement-monitor .section-head{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin-bottom:.45rem}#tf-requirement-monitor .section-links{display:flex;gap:.55rem}#tf-requirement-monitor .section-link,#tf-requirement-monitor .drilldowns a{font-size:.62rem;color:var(--muted);text-decoration:none}#tf-requirement-monitor .section-link:hover,#tf-requirement-monitor .drilldowns a:hover{color:var(--text)}#tf-requirement-monitor .dashboard-layout{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(19rem,.88fr);gap:.55rem;align-items:start}#tf-requirement-monitor .panel,#tf-requirement-monitor .inspector{border:1px solid var(--line);border-radius:.5rem;background:var(--surface);box-shadow:var(--shadow)}
#tf-requirement-monitor .matrix-wrap{overflow-x:auto;padding:.38rem}#tf-requirement-monitor table{border-collapse:separate;border-spacing:.25rem;width:100%;margin:0}#tf-requirement-monitor th{font-size:.61rem;color:var(--muted);font-weight:700;text-align:left;white-space:nowrap;padding:.1rem}#tf-requirement-monitor thead th{text-align:center}#tf-requirement-monitor thead th:first-child{text-align:left}#tf-requirement-monitor td{padding:0}#tf-requirement-monitor .matrix-cell{width:100%;height:3.3rem;min-width:5.7rem;padding:.35rem .4rem;border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);text-align:left}#tf-requirement-monitor button.matrix-cell{cursor:pointer}#tf-requirement-monitor button.matrix-cell:hover,#tf-requirement-monitor button.matrix-cell.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .matrix-cell.not-met{border-color:color-mix(in srgb,var(--red) 58%,var(--line));background:color-mix(in srgb,var(--red) 7%,var(--surface))}#tf-requirement-monitor .matrix-cell.unknown{border-color:color-mix(in srgb,var(--amber) 58%,var(--line));background:color-mix(in srgb,var(--amber) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.met{border-color:color-mix(in srgb,var(--green) 55%,var(--line));background:color-mix(in srgb,var(--green) 6%,var(--surface))}#tf-requirement-monitor .matrix-cell.na{display:grid;place-items:center;border-color:transparent;background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);text-align:center}#tf-requirement-monitor .cell-status{display:block;margin-bottom:.22rem}#tf-requirement-monitor .cell-values{display:grid;grid-template-columns:1fr 1fr;gap:.3rem}#tf-requirement-monitor .cell-values small{display:block;font-size:.5rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .cell-values strong{font-size:.82rem}
#tf-requirement-monitor .technical-support-panel{padding:.55rem}#tf-requirement-monitor .technical-support-card{display:block;text-decoration:none}#tf-requirement-monitor .technical-support-card:hover{border-color:var(--blue)}#tf-requirement-monitor .inspector{padding:.55rem}#tf-requirement-monitor .inspector-head{display:flex;align-items:start;justify-content:space-between;gap:.7rem;margin-bottom:.5rem}#tf-requirement-monitor .signal-grid{display:grid;grid-template-columns:1fr;gap:.48rem}#tf-requirement-monitor .signal-group{display:grid;gap:.28rem;padding:.38rem;border:1px solid color-mix(in srgb,var(--line) 82%,transparent);border-radius:.46rem;background:color-mix(in srgb,var(--surface2) 54%,transparent)}#tf-requirement-monitor .signal-group-head{display:flex;align-items:flex-start;justify-content:space-between;gap:.45rem;padding:0 .04rem .26rem;border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .signal-group-head>strong,#tf-requirement-monitor .signal-group-head>div>strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .group-scope{font-size:.52rem;font-weight:800;color:var(--muted);white-space:nowrap}#tf-requirement-monitor .representation-stack{display:grid;gap:.22rem}#tf-requirement-monitor .dependent-wrap{margin-left:.72rem;padding-left:.5rem;border-left:2px solid color-mix(in srgb,var(--line) 78%,transparent)}#tf-requirement-monitor .dependent-signal{background:color-mix(in srgb,var(--surface2) 38%,transparent);border-style:dashed}#tf-requirement-monitor .confidence-subgroup{display:grid;gap:.28rem;margin-top:.12rem;padding-top:.38rem;border-top:1px solid color-mix(in srgb,var(--line) 72%,transparent)}#tf-requirement-monitor .subgroup-head strong{font-size:.57rem;letter-spacing:.065em;text-transform:uppercase;color:var(--muted)}#tf-requirement-monitor .confidence-grid{display:grid;gap:.28rem}#tf-requirement-monitor .signal-card{border:1px solid var(--line);border-radius:.4rem;background:var(--surface2);padding:.38rem .42rem}#tf-requirement-monitor .signal-card.met-signal{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .signal-card.not-met-signal{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .signal-card.unknown-signal{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}#tf-requirement-monitor .signal-card.na-signal{background:color-mix(in srgb,var(--surface2) 35%,transparent);border-style:dashed;padding:.34rem .4rem}#tf-requirement-monitor .na-signal .signal-head strong{color:var(--muted)}#tf-requirement-monitor .na-signal .state-option{color:color-mix(in srgb,var(--muted) 78%,transparent);border-color:color-mix(in srgb,var(--line) 70%,transparent);background:color-mix(in srgb,var(--surface) 70%,transparent)}#tf-requirement-monitor .na-signal .state-option.selected{color:var(--muted);border-color:color-mix(in srgb,var(--muted) 55%,var(--line))}#tf-requirement-monitor .signal-head{display:flex;align-items:center;justify-content:space-between;gap:.45rem;font-size:.67rem}#tf-requirement-monitor .signal-rule{display:flex;align-items:center;gap:.35rem}#tf-requirement-monitor .scope-count{display:inline-flex;align-items:baseline;gap:.16rem;padding:.1rem .24rem;border:1px solid var(--line);border-radius:.28rem;background:var(--surface);white-space:nowrap}#tf-requirement-monitor .scope-count b{font-size:.55rem}#tf-requirement-monitor .scope-count small{font-size:.44rem;color:var(--muted)}#tf-requirement-monitor .scope-count.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .scope-count.not-met{border-color:color-mix(in srgb,var(--red) 48%,var(--line))}#tf-requirement-monitor .scope-count.unknown{border-color:color-mix(in srgb,var(--amber) 46%,var(--line))}#tf-requirement-monitor .coverage-summary{display:flex;align-items:baseline;gap:.38rem;margin-top:.28rem}#tf-requirement-monitor .coverage-summary>strong{font-size:1.08rem;line-height:1}#tf-requirement-monitor .coverage-summary>strong span{font-size:.7rem;color:var(--muted);margin:0 .05rem}#tf-requirement-monitor .coverage-summary small{font-size:.52rem;color:var(--muted)}#tf-requirement-monitor .coverage-strip{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:.18rem;margin-top:.34rem}#tf-requirement-monitor .coverage-segment{height:.28rem;border-radius:999px;background:var(--line)}#tf-requirement-monitor .coverage-segment.pass{background:var(--green)}#tf-requirement-monitor .coverage-segment.fail{background:var(--red)}#tf-requirement-monitor .coverage-segment.missing{background:transparent;border:1px dashed var(--red)}#tf-requirement-monitor .coverage-counts{display:flex;gap:.45rem;margin-top:.25rem;font-size:.48rem;font-weight:700;color:var(--muted)}#tf-requirement-monitor .coverage-counts .pass{color:var(--green)}#tf-requirement-monitor .coverage-counts .fail,#tf-requirement-monitor .coverage-counts .missing{color:var(--red)}#tf-requirement-monitor .metric-values{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.32rem}#tf-requirement-monitor .metric-values div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface)}#tf-requirement-monitor .metric-values span{display:block;font-size:.49rem;color:var(--muted);text-transform:uppercase}#tf-requirement-monitor .metric-values strong{display:block;font-size:.78rem;margin-top:.05rem}#tf-requirement-monitor .state-lane{display:flex;gap:.22rem;flex-wrap:wrap;margin-top:.32rem}#tf-requirement-monitor .state-option{display:inline-flex;align-items:center;gap:.22rem;padding:.2rem .3rem;border:1px solid var(--line);border-radius:.3rem;background:var(--surface);font-size:.55rem;color:var(--muted)}#tf-requirement-monitor .state-option.selected{color:var(--text);border-color:var(--blue)}#tf-requirement-monitor .marker{font-size:.43rem;font-weight:900;padding:.08rem .16rem;border-radius:.2rem;white-space:nowrap}#tf-requirement-monitor .marker.both{background:color-mix(in srgb,var(--blue) 13%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.actual{background:color-mix(in srgb,var(--green) 12%,var(--surface));color:var(--green)}#tf-requirement-monitor .marker.target{background:color-mix(in srgb,var(--blue) 12%,var(--surface));color:var(--blue)}#tf-requirement-monitor .marker.inactive{background:color-mix(in srgb,var(--muted) 12%,var(--surface));color:var(--muted)}
#tf-requirement-monitor .help{position:relative;display:inline-grid;place-items:center;width:.82rem;height:.82rem;border:1px solid var(--line);border-radius:50%;font-size:.5rem;color:var(--muted);cursor:help;vertical-align:.08rem;text-transform:none;letter-spacing:normal}#tf-requirement-monitor .help-tip{position:absolute;z-index:50;left:50%;bottom:1rem;transform:translateX(-50%);width:15rem;max-width:calc(100vw - 2rem);padding:.36rem .42rem;border:1px solid color-mix(in srgb,var(--line) 82%,var(--text));border-radius:.3rem;background:var(--pst-color-background);box-shadow:0 .45rem 1.4rem rgba(0,0,0,.28);font-size:.55rem;font-weight:600;color:var(--text);line-height:1.35;text-transform:none;letter-spacing:normal;opacity:0;visibility:hidden;pointer-events:none}#tf-requirement-monitor .help:hover .help-tip,#tf-requirement-monitor .help:focus .help-tip{opacity:1;visibility:visible}#tf-requirement-monitor .signal-group-head>.help .help-tip{left:auto;right:0;transform:none}#tf-requirement-monitor .tile-metrics .help{display:inline-grid;font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics .help-tip{font-size:.55rem;color:var(--text)}#tf-requirement-monitor .drilldowns{display:flex;justify-content:flex-end;gap:.55rem;margin-top:.45rem;padding-top:.4rem;border-top:1px solid var(--line)}
#tf-requirement-monitor .fault-layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(19rem,.95fr);gap:.55rem;align-items:start}#tf-requirement-monitor .fault-layout.no-inspector{grid-template-columns:1fr}#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(5,minmax(0,1fr))}#tf-requirement-monitor .fault-grid{display:grid;grid-template-columns:1fr 1fr;gap:.38rem}#tf-requirement-monitor .fault-tile{min-height:5.3rem;padding:.48rem;border:1px solid var(--line);border-radius:.42rem;background:var(--surface);text-align:left}#tf-requirement-monitor button.fault-tile{cursor:pointer}#tf-requirement-monitor button.fault-tile:hover,#tf-requirement-monitor button.fault-tile.selected{outline:2px solid color-mix(in srgb,var(--blue) 55%,transparent);outline-offset:1px}#tf-requirement-monitor .fault-tile.not-met{border-color:color-mix(in srgb,var(--red) 55%,var(--line))}#tf-requirement-monitor .fault-tile.met{border-color:color-mix(in srgb,var(--green) 50%,var(--line))}#tf-requirement-monitor .fault-tile.na{background:color-mix(in srgb,var(--surface2) 45%,transparent);color:var(--muted);border-style:dashed}#tf-requirement-monitor .tile-head{display:flex;align-items:start;justify-content:space-between;gap:.4rem;font-size:.61rem}#tf-requirement-monitor .tile-metrics{display:grid;grid-template-columns:1fr 1fr;gap:.28rem;margin-top:.5rem}#tf-requirement-monitor .tile-metrics div{padding:.28rem .32rem;border-radius:.3rem;background:var(--surface2)}#tf-requirement-monitor .tile-metrics span{display:block;font-size:.49rem;color:var(--muted)}#tf-requirement-monitor .tile-metrics strong{font-size:.72rem}#tf-requirement-monitor .tile-metrics i{font-size:.49rem;color:var(--muted);font-style:normal;margin-left:.16rem}#tf-requirement-monitor .tile-metrics .not-met strong{color:var(--red)}#tf-requirement-monitor .na-center{display:flex;align-items:center;justify-content:center;gap:.4rem;height:3rem;font-size:.61rem;color:var(--muted)}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .fault-chain{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto minmax(0,1fr);align-items:stretch;gap:.28rem}#tf-requirement-monitor .fault-chain>i{align-self:center;color:var(--muted);font-style:normal;font-weight:800}#tf-requirement-monitor .fault-stage{display:grid;grid-template-columns:1fr auto;gap:.12rem .35rem;align-items:center;padding:.36rem .42rem;border:1px solid var(--line);border-radius:.38rem;background:var(--surface)}#tf-requirement-monitor .fault-stage>span{font-size:.5rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>strong{font-size:.82rem}#tf-requirement-monitor .fault-stage>small{grid-column:1/-1;font-size:.47rem;color:var(--muted)}#tf-requirement-monitor .fault-stage>.status{justify-self:end}#tf-requirement-monitor .fault-stage.met{border-color:color-mix(in srgb,var(--green) 42%,var(--line))}#tf-requirement-monitor .fault-stage.not-met{border-color:color-mix(in srgb,var(--red) 50%,var(--line))}#tf-requirement-monitor .fault-stage.unknown{border-color:color-mix(in srgb,var(--amber) 45%,var(--line))}#tf-requirement-monitor .mutation-grid{display:grid;gap:.32rem}#tf-requirement-monitor .mutation-chain{padding:.34rem;border:1px solid var(--line);border-radius:.4rem;background:color-mix(in srgb,var(--surface2) 52%,transparent)}#tf-requirement-monitor .mutation-chain-head{margin:0 0 .28rem .05rem}#tf-requirement-monitor .mutation-chain-head strong{font-size:.55rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
#tf-requirement-monitor .history{display:flex;align-items:center;gap:.55rem;padding:.55rem .65rem}#tf-requirement-monitor .history-line{flex:1;height:2px;background:var(--line);position:relative}#tf-requirement-monitor .history-point{position:absolute;right:0;top:50%;transform:translate(50%,-50%);width:.5rem;height:.5rem;border-radius:50%;background:var(--muted);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--muted) 12%,transparent)}#tf-requirement-monitor .history-point.not-met{background:var(--red);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--red) 12%,transparent)}#tf-requirement-monitor .history-point.met{background:var(--green);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--green) 12%,transparent)}#tf-requirement-monitor .history-point.unknown{background:var(--amber);box-shadow:0 0 0 .22rem color-mix(in srgb,var(--amber) 12%,transparent)}#tf-requirement-monitor .history strong{font-size:.67rem}
@media(max-width:1200px){#tf-requirement-monitor .dashboard-layout,#tf-requirement-monitor .fault-layout{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:repeat(3,minmax(0,1fr))}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:repeat(3,1fr)}#tf-requirement-monitor .fault-tile:nth-child(3n+1) .tile-metrics .help-tip{left:0;transform:none}}@media(max-width:760px){#tf-requirement-monitor .domain-strip,#tf-requirement-monitor .domain-strip.with-support{grid-template-columns:1fr}#tf-requirement-monitor .confidence-grid{grid-template-columns:1fr}#tf-requirement-monitor .fault-grid,#tf-requirement-monitor .fault-layout.no-inspector .fault-grid{grid-template-columns:1fr 1fr}#tf-requirement-monitor .fault-signals{grid-template-columns:1fr}#tf-requirement-monitor .fault-tile:nth-child(odd) .tile-metrics .help-tip{left:0;transform:none}}
</style>"""

    script = f"""<script id="tf-requirement-monitor-script">
(()=>{{const root=document.querySelector('#tf-requirement-monitor');if(!root)return;const cellInspectors={json.dumps(cell_inspectors, ensure_ascii=False)};const faultInspectors={json.dumps(fault_inspectors, ensure_ascii=False)};function syncSticky(){{const header=document.querySelector('.bd-header');const top=header?.getBoundingClientRect().bottom||0;root.style.setProperty('--sticky-top',top+'px')}}function selectCell(key){{const value=cellInspectors[key];if(!value)return;root.querySelector('#cell-inspector').innerHTML=value;root.querySelectorAll('[data-cell]').forEach(button=>button.classList.toggle('selected',button.dataset.cell===key));}}function selectFault(key){{const value=faultInspectors[key];if(!value)return;root.querySelector('#fault-inspector').innerHTML=value;root.querySelectorAll('[data-fault]').forEach(button=>button.classList.toggle('selected',button.dataset.fault===key));}}root.querySelectorAll('[data-cell]').forEach(button=>button.addEventListener('click',()=>selectCell(button.dataset.cell)));root.querySelectorAll('[data-fault]').forEach(button=>button.addEventListener('click',()=>selectFault(button.dataset.fault)));let flashTimer;function flashTarget(hash){{if(!hash||!hash.startsWith('#'))return;const target=root.querySelector(hash);if(!target||!target.classList.contains('section'))return;root.querySelectorAll('.section.nav-flash').forEach(node=>node.classList.remove('nav-flash'));void target.offsetWidth;target.classList.add('nav-flash');clearTimeout(flashTimer);flashTimer=setTimeout(()=>target.classList.remove('nav-flash'),1700);}}document.querySelectorAll('a[href="#ce-coverage-{contract_key}"],a[href="#ce-faults-{contract_key}"],a[href="#ce-technical-support-{contract_key}"],a[href="#ce-history-{contract_key}"]').forEach(link=>link.addEventListener('click',()=>requestAnimationFrame(()=>flashTarget(link.getAttribute('href')))));window.addEventListener('hashchange',()=>flashTarget(location.hash));window.addEventListener('resize',syncSticky);syncSticky();selectCell({json.dumps(default_cell)});selectFault({json.dumps(default_fault)});if(location.hash)requestAnimationFrame(()=>flashTarget(location.hash));}})();
</script>"""

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
