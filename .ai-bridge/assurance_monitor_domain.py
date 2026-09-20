"""Shared assurance status algebra and contract-state projection."""

# ruff: noqa: C901, D103, E501, PLR0911, PLR0912, PLR0915, PLR2004, RUF005

from __future__ import annotations

REPRESENTATION = [
    "Synthetic / abstract",
    "Surrogate / simulated",
    "Representative",
    "Actual",
    "UNKNOWN",
]
PROVENANCE = ["COMPLETE", "INCOMPLETE", "UNKNOWN"]
PRODUCER = ["QUALIFIED", "NOT QUALIFIED", "UNKNOWN"]
FRESHNESS = ["CURRENT", "STALE", "UNKNOWN"]
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
    rule = (
        ((contract.get("target") or {}).get("gate_aggregation") or {}).get(signal) or {}
    ).get("rule", default)
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
        1 for value in values if value in order and order.index(value) >= target_rank
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
        expected_path_ids = list((target.get("item_path_ids") or {}).get(item_id, []))
        required_path_count += expected_paths
        item_rows = [
            row
            for row in contract["coverage_actual"].get(item_id, [])
            if row.get("level") == target["level"]
            and row.get("boundary") == target["boundary"]
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
                str(row.get("coverage_path") or "").strip() for row in item_rows
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
    if target["boundary"] == "none" and any(
        "zero HTTP requests" in value for value in boundary_bases
    ):
        boundary_summary = "This proof stays local: no provider HTTP request is part of the retained path."
    elif target["boundary"] == "replay":
        boundary_summary = (
            f"{retained} retained path(s) replay recorded provider traffic."
        )
    elif target["boundary"] == "substitute":
        boundary_summary = f"{retained} retained path(s) use a controlled substitute at the external boundary."
    elif target["boundary"] == "direct":
        boundary_summary = (
            f"{retained} retained path(s) call the real external dependency."
        )
    else:
        boundary_summary = "This proof does not need an external participant."

    semantic_rule = gate_rule(contract, "semantic_coverage")
    semantic_status = (
        "MET"
        if (
            passed == target["declared_count"] if semantic_rule == "ALL" else passed > 0
        )
        else "NOT MET"
    )
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
    provenance_status = quantified_status(
        provenance_values, "COMPLETE", provenance_rule
    )
    provenance_matched = sum(1 for value in provenance_values if value == "COMPLETE")

    producer_rule = gate_rule(contract, "producer_qualification")
    producer_values = [
        str(row.get("producer_qualification") or "UNKNOWN").upper()
        if row.get("producer_qualification_scope") == "full_chain"
        else "UNKNOWN"
        for row in rows
    ]
    producer_ids = sorted(
        {producer_id for row in rows for producer_id in (row.get("producer_ids") or [])}
    )
    producer_status = quantified_status(producer_values, "QUALIFIED", producer_rule)
    producer_matched = sum(1 for value in producer_values if value == "QUALIFIED")

    freshness_rule = gate_rule(contract, "freshness")
    freshness_values = [str(row.get("freshness") or "UNKNOWN").upper() for row in rows]
    freshness_status = quantified_status(freshness_values, "CURRENT", freshness_rule)
    freshness_matched = sum(1 for value in freshness_values if value == "CURRENT")

    ms_rule = gate_rule(contract, "ms_validation")
    ms_rows = [
        row
        for row in rows
        if representation_label(row.get("representation")) == "Surrogate / simulated"
    ]
    ms_values = [ms_label(row.get("ms_validation")) for row in ms_rows]
    declared_ms_target = target.get("ms_validation_target") or target.get(
        "ms_validation"
    )
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

    overall = combine(
        [
            semantic_status,
            rep_status,
            provenance_status,
            producer_status,
            freshness_status,
            ms_status,
        ]
    )
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


def fault_state(contract: dict, group: dict, policy: dict) -> dict:
    classes = contract["fault_actual"]["classes"]
    required = [item for item in group["items"] if item["state"] == "required"]
    if not required:
        return {"label": group["label"], "status": "N/A"}

    exercised = sum(
        1 for item in required if classes.get(item["id"], {}).get("exercised")
    )
    detected = sum(
        1
        for item in required
        if classes.get(item["id"], {}).get("exercised")
        and classes.get(item["id"], {}).get("detected")
    )
    class_status = "MET" if exercised == len(required) else "NOT MET"
    detection_actual = (
        100.0
        if exercised and detected == exercised
        else (0.0 if not exercised else detected * 100.0 / exercised)
    )
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
                float(reach_target_raw) if reach_target_raw is not None else None
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
                    else ("MET" if sensitivity >= sensitivity_target else "NOT MET")
                )
            )
            mutation.append(
                {
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
                }
            )

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
