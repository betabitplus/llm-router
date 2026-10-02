from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_ui", ROOT / ".ai-bridge/assurance_monitor_ui.py"
)
if UI_SPEC is None or UI_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor UI helpers")
ui = importlib.util.module_from_spec(UI_SPEC)
UI_SPEC.loader.exec_module(ui)

DOMAIN_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_domain", ROOT / ".ai-bridge/assurance_monitor_domain.py"
)
if DOMAIN_SPEC is None or DOMAIN_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor domain helpers")
domain = importlib.util.module_from_spec(DOMAIN_SPEC)
DOMAIN_SPEC.loader.exec_module(domain)

REGISTRY_SPEC = importlib.util.spec_from_file_location(
    "assurance_monitor_registry", ROOT / ".ai-bridge/assurance_monitor_registry.py"
)
if REGISTRY_SPEC is None or REGISTRY_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor registry")
registry = importlib.util.module_from_spec(REGISTRY_SPEC)
REGISTRY_SPEC.loader.exec_module(registry)

esc = ui.esc
help_tip = ui.help_tip
status_class = ui.status_class
status_label = ui.status_label
lane = ui.lane
coverage_card = ui.coverage_card

combine = domain.combine
cell_state = domain.cell_state
fault_state = domain.fault_state
contract_slug = registry.contract_slug
contract_domain_state = domain.contract_domain_state
REPRESENTATION = domain.REPRESENTATION
PROVENANCE = domain.PROVENANCE
PRODUCER = domain.PRODUCER
FRESHNESS = domain.FRESHNESS
MS_LEVELS = domain.MS_LEVELS
FACTS = ROOT / "docs/_build/html/requirement-monitor-facts.json"
NEEDS = ROOT / "docs/_build/html/needs.json"
CANONICAL_OUT = ROOT / "docs/_build/html/verification-assurance.html"
PRIMARY_CONTRACT_ID = "REQ_INVALID_CONFIGURATION_ERRORS"

OUT = CANONICAL_OUT
CONTRACT_ID = PRIMARY_CONTRACT_ID
CONTRACT_URL = "requirements/configuration.html#REQ_INVALID_CONFIGURATION_ERRORS"
PROFILE_URL = "verification-profiles/invalid-configuration.html"
HEALTH_MAP_URL = "verification-health-map.html"
MODEL_URL = "test-plan.html#test-plan-configuration-validation-model"

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
FAULT_GROUP_HELP = {
    "Implementation": "Checks that small code mistakes—a wrong comparison, limit, branch or return, a lost call, write or raise—are caught.",
    "Runtime / dependency": "Checks that dependency failures—timeouts, disconnects, unavailability, or malformed replies—cannot change the required behavior.",
    "Interface / protocol": "Checks that wrong external calls, error statuses, or malformed payloads are caught at the boundary.",
    "Architecture": "Checks that code cannot bypass a required layer or depend on a forbidden layer.",
    "Specification / model": "Checks that tests catch the wrong result, a missing case, or the wrong ordering or boundary rule.",
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
        rungs=domain.SCALES["representation"],
    )
    ms = lane(
        "M&S validation",
        MS_LEVELS,
        state["ms_actual_values"],
        state["ms_target"],
        state["ms_status"],
        "Target L0: this target does not require a validated model, so nothing is judged."
        if state["ms_target"] == "L0"
        else "Checks that any surrogate or model used as evidence is validated strongly enough for this target.",
        state["ms_matched"],
        state["ms_applicable_count"],
        "model paths",
        "dependent-signal",
        rungs=domain.SCALES["ms_validation"],
    )
    confidence_parts = [
        lane(
            "Provenance",
            PROVENANCE,
            state["provenance_actual_values"],
            "COMPLETE",
            state["provenance_status"],
            "Checks that each result belongs to the exact test, run, source version, and artifact it claims.",
            state["provenance_matched"],
            state["retained_count"],
            rungs=domain.SCALES["provenance"],
        ),
        lane(
            f"Producer qualification · {state['producer_count']} producers",
            PRODUCER,
            state["producer_actual_values"],
            "QUALIFIED",
            state["producer_status"],
            "Checks that every evidence producer used by this proof is qualified for its role.",
            state["producer_matched"],
            state["retained_count"],
            "evidence paths",
            rungs=domain.SCALES["producer"],
        ),
    ]
    if state["freshness_status"] != "MET":
        confidence_parts.append(
            lane(
                "Freshness",
                FRESHNESS,
                state["freshness_actual_values"],
                "CURRENT",
                state["freshness_status"],
                "Checks that retained evidence still matches every input relevant to this proof.",
                state["freshness_matched"],
                state["retained_count"],
                rungs=domain.SCALES["freshness"],
            )
        )
    confidence = "".join(confidence_parts)
    signals = ui.signal_group(
        title="Required evidence",
        body=coverage,
        class_name="primary-group",
    ) + ui.signal_group(
        title="Retained path properties",
        body=(
            ui.no_retained_evidence()
            if not state["retained_count"]
            else f'<div class="representation-stack">{representation}'
            f'<div class="dependent-wrap">{ms}</div></div>'
            + ui.confidence_subgroup(confidence)
        ),
        class_name="path-properties",
        scope=f"{state['retained_count']}/{state['required_path_count']} paths",
    )
    return (
        ui.inspector_head(
            eyebrow="Selected verification cell",
            title=f"{state['level_label']} × {state['boundary_label']}",
            status=state["overall"],
        )
        + f'<div class="signal-grid">{signals}</div>'
        + ui.drilldowns(
            (
                (
                    "Explorer ↗",
                    ui.explorer_href(
                        CONTRACT_ID,
                        layer="coverage",
                        level=state["key"].split("|")[0],
                        boundary=state["key"].split("|")[1],
                    ),
                ),
                ("Requirement ↗", CONTRACT_URL),
                ("Verification profile ↗", PROFILE_URL),
                ("Test model ↗", MODEL_URL),
                ("Raw facts ↗", "requirement-monitor-facts.json"),
            )
        )
    )


def fault_stage(
    label: str, value: str, status: str | None = None, target: str | None = None
) -> str:
    status_html = (
        f'<span class="status {status_class(status)}">{esc(status_label(status))}</span>'
        if status
        else ""
    )
    target_html = f"<small>{esc(target)}</small>" if target else ""
    return (
        f'<div class="fault-stage {status_class(status) if status else "neutral"}{" zero" if value in ("0", "—") else ""}">'
        f"<span>{esc(label)}</span>"
        f"<strong>{esc(value)}</strong>{target_html}{status_html}</div>"
    )


CLASS_WORD = {"caught": "caught", "missed": "missed", "unknown": "undecided", "not challenged": "not challenged"}


def class_boxes(contract: dict, group: dict) -> str:
    """The group's classes in the fault model's order, each a small box: its name and what became of it."""
    classes = (contract.get("fault_actual") or {}).get("classes") or {}
    boxes = []
    for item in group["items"]:
        name = item["id"].split(".", 1)[-1].replace("-", " ")
        description = str(item.get("description") or "")
        if item["state"] == "required":
            verdict = domain.class_verdict(classes.get(item["id"]) or {})
            tone, word = {"caught": "met", "unknown": "unknown"}.get(verdict, "not-met"), CLASS_WORD[verdict]
        elif item["state"] == "optional":
            tone, word = "optional", "optional"
        else:
            tone, word = "air", "not asked"
        boxes.append(f'<div class="class-box {tone}" title="{esc(name)} — {esc(word)}. {esc(description)}"><strong>{esc(name)}</strong><small>{esc(word)}</small></div>')
    return '<div class="class-boxes">' + "".join(boxes) + "</div>"


def fault_inspector(state: dict) -> str:
    class_chain = (
        '<div class="fault-chain">'
        + fault_stage("Required", str(state["required"]))
        + "<i>→</i>"
        + fault_stage(
            "Challenged",
            f"{state['exercised']}/{state['required']}",
            state["class_status"],
        )
        + "<i>→</i>"
        + fault_stage(
            "Detected",
            f"{state['detected']}/{state['exercised']}"
            if state["exercised"]
            else "—",
            state["detection_status"],
        )
        + "</div>"
    )
    # The inspector counts; which classes fail and why, with their surviving mutants, are the explorer's rows.
    sections = [
        ui.signal_group(
            title="Fault classes",
            body=class_chain + state.get("class_boxes", ""),
            class_name="fault-class-group",
        )
    ]
    # The mutants behind the classes, counted by outcome; each one is a row in the explorer.
    if state.get("mutants"):
        tally = state["mutants"]
        stages = [
            ("Caught", tally["caught"], None),
            ("Survived", tally["survived"], "NOT MET" if tally["survived"] else None),
            ("Not reached", tally["unreached"], "NOT MET" if tally["unreached"] else None),
            ("Undecided", tally["unknown"], "UNKNOWN" if tally["unknown"] else None),
            ("Suppressed", tally["suppressed"], None),
            ("Invalid", tally["invalid"], None),
        ]
        sections.append(
            ui.signal_group(
                title="Mutants",
                body='<div class="fault-chain mutant-tally">'
                + "".join(
                    fault_stage(label, str(count), status)
                    for label, count, status in stages
                    if count or label in {"Caught", "Survived", "Not reached"}
                )
                + "</div>",
                class_name="mutant-group mutants-group",
            )
        )
    # How many semantic mutants the group's classes asked for (ADR_0004); what generating them made and
    # cost is the whole contract's and stands once, under the fault groups.
    generation = state.get("semantic_generation")
    if generation:
        stages = [
            ("Targets", str(generation["targets"]), None),
            ("Not generated", str(generation["not_generated"]), "UNKNOWN" if generation["not_generated"] else None),
        ]
        sections.append(
            ui.signal_group(
                title="Semantic generation",
                body='<div class="fault-chain mutant-tally">'
                + "".join(
                    fault_stage(label, value, status)
                    for label, value, status in stages
                    if value != "0" or label == "Targets"
                )
                + "</div>",
                class_name="mutant-group generation-group",
            )
        )
    # What the survivor judgement found about the group's survivors (ADR_0005).
    judgement = state.get("survivor_judgement")
    if judgement:
        stages = [
            ("Input found", str(judgement.get("found") or 0), None),
            ("Likely equivalent", str(judgement.get("likely-equivalent") or 0), None),
            ("Unsure", str(judgement.get("unsure") or 0), None),
            ("Not judged", str(judgement.get("not-applicable") or 0), None),
        ]
        # What the verdicts that count decided (ADR_0006); only an escalation waits for the person.
        verdicts = [
            ("Pinned", int(judgement.get("verdict_pinned") or 0), None),
            ("Pin pending", int(judgement.get("verdict_pin_pending") or 0), None),
            ("Suppressed", int(judgement.get("verdict_suppressed") or 0), None),
            ("For you", int(judgement.get("verdict_escalated") or 0), "fail" if judgement.get("verdict_escalated") else None),
        ]
        if any(value for _label, value, _status in verdicts):
            stages += [(label, str(value), status) for label, value, status in verdicts]
        sections.append(
            ui.signal_group(
                title="Survivor judgement",
                body='<div class="fault-chain mutant-tally">'
                + "".join(fault_stage(label, value, status) for label, value, status in stages)
                + "</div>",
                class_name="mutant-group judgement-group",
            )
        )
    fault_profile_url = PROFILE_URL.split("#", 1)[0] + "#fault-applicability"
    links = [
        ("Explorer ↗", ui.explorer_href(CONTRACT_ID, layer="faults", group=state["label"])),
        ("Verification profile ↗", fault_profile_url),
        ("Fault model ↗", "test-plan.html#test-plan-fault-model"),
        (
            "Raw facts ↗",
            str(state.get("raw_url") or "requirement-monitor-facts.json"),
        ),
    ]
    return (
        ui.inspector_head(
            eyebrow="Selected fault group",
            title=state["label"],
            status=state["status"],
        )
        + f'<div class="signal-grid fault-signals">{"".join(sections)}</div>'
        + ui.drilldowns(tuple(links))
    )


def generation_summary(generation: dict) -> str:
    """What generating the contract's semantic mutants made and cost, once for all its fault groups (ADR_0004)."""
    spend = generation.get("spend") or {}
    origins = generation.get("mutants") or {}
    tokens = int((spend.get("tokens") or {}).get("total") or 0)
    stages = [
        ("By a model", str(origins.get("model") or 0)),
        ("By an agent", str(origins.get("agent") or 0)),
        ("Model calls", str(spend.get("calls") or 0)),
        ("Deferred", str(spend.get("deferred") or 0)),
        ("Tokens", f"{tokens / 1000:.1f}k" if tokens >= 1000 else str(tokens)),
        ("List price", f"${spend['list_usd']:.2f}" if spend.get("list_usd") is not None else "—"),
    ]
    return ui.signal_group(
        title="Semantic generation · whole contract",
        body='<div class="fault-chain mutant-tally">'
        + "".join(
            fault_stage(label, value)
            for label, value in stages
            if value not in {"0", "—"} or label == "Model calls"
        )
        + "</div>",
        class_name="mutant-group",
    )


CAUSE_PROPERTIES = (
    ("Representation", "representation_status"),
    ("M&S validation", "ms_status"),
    ("Provenance", "provenance_status"),
    ("Producer qualification", "producer_status"),
    ("Freshness", "freshness_status"),
)


def cell_cause(state: dict) -> str:
    """The word a cell needs when its count alone does not explain its verdict."""
    if not state["retained_count"]:
        return "no test result yet"
    if state["overall"] in ("MET", "N/A") or state["semantic_status"] == state["overall"]:
        return ""
    return next((label for label, key in CAUSE_PROPERTIES if state[key] == state["overall"]), "")


def coverage_meta(statuses: list[str], linked: dict) -> str:
    """The coverage card in words: how many asked cells pass, and a failing linked test when there is one."""
    total = len(statuses)
    failing, unknown = statuses.count("NOT MET"), statuses.count("UNKNOWN")
    noun = "asked cell" if total == 1 else "asked cells"
    if failing:
        text = f"{failing} of {total} {noun} fail" if total != 1 else "the asked cell fails"
    elif unknown:
        text = f"{unknown} of {total} {noun} unknown"
    else:
        text = f"{total} of {total} {noun} pass"
    if linked["failed"]:
        text += f" · {len(linked['failed'])} linked test{'s' if len(linked['failed']) != 1 else ''} fail{'' if len(linked['failed']) != 1 else 's'}"
    return text


def fault_meta(statuses: list[str]) -> str:
    """The fault card in words: how many asked groups pass, and how many the profile does not ask."""
    asked = [status for status in statuses if status != "N/A"]
    not_asked = len(statuses) - len(asked)
    failing, unknown = asked.count("NOT MET"), asked.count("UNKNOWN")
    noun = "asked group" if len(asked) == 1 else "asked groups"
    if not asked:
        text = "no group asked"
    elif failing:
        text = f"{failing} of {len(asked)} {noun} fail"
    elif unknown:
        text = f"{unknown} of {len(asked)} {noun} undecided"
    else:
        text = f"{len(asked)} of {len(asked)} {noun} pass"
    return text + (f" · {not_asked} N/A" if not_asked else "")


def thumb_strip(statuses: list[str]) -> str:
    return f'<span class="thumb thumb-strip" style="--n:{len(statuses)}" aria-hidden="true">' + "".join(
        f'<i class="{status_class(status)}"></i>' for status in statuses
    ) + "</span>"


def map_legend(question: str, statuses: list[str], na_title: str) -> str:
    """The map's legend: the section's question, then each verdict it shows with its count."""
    parts = []
    for status, word in (("NOT MET", "Fail"), ("UNKNOWN", "Unknown"), ("MET", "Pass"), ("N/A", "N/A")):
        count = statuses.count(status)
        if count or status == "N/A":
            title = f' title="{esc(na_title)}"' if status == "N/A" else ""
            parts.append(f'<span{title}><i class="{status_class(status)}"></i>{word} <b>{count}</b></span>')
    return f'<div class="map-legend"><span class="q">{esc(question)}</span>{"".join(parts)}</div>'


def nav_thumb_matrix(cells: dict) -> str:
    """The matrix in miniature: an asked cell is a button that selects it below; the selected one is marked."""
    parts = []
    for level, level_label in LEVELS:
        for boundary, boundary_label in BOUNDARIES:
            key = level + "|" + boundary
            if key in cells:
                state = cells[key]
                parts.append(
                    f'<button type="button" class="t {status_class(state["overall"])}" data-goto-cell="{esc(key)}" '
                    f'title="{esc(level_label)} × {esc(boundary_label)} · {esc(status_label(state["overall"]))}" '
                    f'aria-label="Select {esc(level_label)} × {esc(boundary_label)}"></button>'
                )
            else:
                parts.append('<i class="t na" aria-hidden="true"></i>')
    return '<span class="thumb thumb-matrix nav">' + "".join(parts) + "</span>"


def nav_thumb_faults(faults: dict) -> str:
    """The fault groups in miniature: an asked group is a button that selects it below."""
    parts = []
    for key, state in faults.items():
        if state["status"] == "N/A":
            parts.append(f'<i class="t na" title="{esc(state["label"])} · N/A" aria-hidden="true"></i>')
        else:
            parts.append(
                f'<button type="button" class="t {status_class(state["status"])}" data-goto-fault="{esc(key)}" '
                f'title="{esc(state["label"])} · {esc(status_label(state["status"]))}" aria-label="Select {esc(state["label"])}"></button>'
            )
    return f'<span class="thumb thumb-strip nav" style="--n:{len(faults)}">' + "".join(parts) + "</span>"


PROPERTY_BARS = (
    ("Representation", "representation_status"),
    ("M&S validation", "ms_status"),
    ("Provenance", "provenance_status"),
    ("Producer qualification", "producer_status"),
)


def cell_properties(state: dict) -> str:
    """The cell's path properties as small bars, Freshness only when it is not current, as in its detail."""
    if not state["retained_count"]:
        return ""
    parts = list(PROPERTY_BARS) + ([("Freshness", "freshness_status")] if state["freshness_status"] != "MET" else [])
    title = " · ".join(f"{label} {status_label(state[key])}" for label, key in parts)
    bars = "".join(f'<i class="{status_class(state[key])}"></i>' for _label, key in parts)
    return f'<span class="cell-props" title="{esc(title)}" aria-label="{esc(title)}">{bars}</span>'


def contract_output_path(contract_id: str) -> Path:
    if contract_id == PRIMARY_CONTRACT_ID:
        return CANONICAL_OUT
    return CANONICAL_OUT.with_name(
        f"contract-evidence-{contract_slug(contract_id)}.html"
    )


def layers(inspectors: dict[str, str], default: str | None) -> str:
    return "".join(
        f'<div class="ins-layer{" on" if key == default else ""}" data-for="{esc(key)}">{value}</div>'
        for key, value in inspectors.items()
    )


def render_current() -> None:
    global CONTRACT_URL, MODEL_URL, PROFILE_URL

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
    CONTRACT_URL = (
        contract.get("contract_url") or f"requirements/configuration.html#{CONTRACT_ID}"
    )
    PROFILE_URL = (
        target.get("profile_url")
        or target.get("source_url")
        or "verification-profiles/index.html"
    )
    MODEL_URL = target.get("model_url") or "test-plan.html#test-plan"

    cells = {}
    for coverage_target in contract["target"]["coverage"]:
        state = cell_state(contract, coverage_target)
        cells[state["key"]] = state
    cell_statuses = [state["overall"] for state in cells.values()]
    linked = domain.linked_tests_state(contract)
    cell_domain = combine(cell_statuses + [linked["status"]])

    faults = {}
    generation = (contract.get("fault_actual") or {}).get("semantic_generation")
    semantic_targets = [row["class"] for row in target.get("semantic_mutants") or []]
    fault_classes = (contract.get("fault_actual") or {}).get("classes") or {}
    for index, group in enumerate(contract["target"]["fault_groups"]):
        faults[str(index)] = fault_state(contract, group, policy)
        faults[str(index)]["class_boxes"] = class_boxes(contract, group)
        # A group counts over its required classes only, as its mutants do, so every count in its
        # inspector speaks of the same classes.
        required_ids = {item["id"] for item in group["items"] if item["state"] == "required"}
        group_targets = [klass for klass in semantic_targets if klass in required_ids]
        if generation and group_targets:
            faults[str(index)]["semantic_generation"] = {
                "targets": len(group_targets),
                "not_generated": sum(
                    int((fault_classes.get(klass) or {}).get("semantic_not_generated") or 0)
                    for klass in set(group_targets)
                ),
            }
        judged = (contract.get("fault_actual") or {}).get("survivor_judgement") or {}
        group_counts: dict[str, int] = {}
        for item in group["items"]:
            if item["id"] not in required_ids:
                continue
            for status, count in (judged.get(item["id"]) or {}).items():
                group_counts[status] = group_counts.get(status, 0) + int(count)
        if group_counts:
            faults[str(index)]["survivor_judgement"] = group_counts
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
                row.append(
                    '<td><div class="matrix-cell na air" aria-disabled="true" title="N/A · the profile does not ask for this cell" '
                    'aria-label="N/A, the profile does not ask for this cell"></div></td>'
                )
            else:
                row.append(
                    "<td>"
                    f'<button class="matrix-cell {status_class(state["overall"])}" type="button" data-cell="{esc(state["key"])}">'
                    f'<span class="cell-status status {status_class(state["overall"])}">{esc(status_label(state["overall"]))}</span>'
                    f'<span class="cell-count"><strong>{state["semantic_actual"]}<span>/</span>{state["required_count"]}</strong>'
                    f'<small>passing</small></span>{cell_properties(state)}'
                    + (f'<span class="cell-cause status {status_class(state["overall"])}">{esc(cell_cause(state))}</span>' if cell_cause(state) else "")
                    + "</button></td>"
                )
        matrix_rows.append(f"<tr>{''.join(row)}</tr>")

    fault_tiles = []
    for key, state in faults.items():
        group_help = FAULT_GROUP_HELP[state["label"]]
        if state["status"] == "N/A":
            fault_tiles.append(
                ui.na_fault_tile(
                    state["label"],
                    help_text=group_help,
                )
            )
            continue
        secondary_label = "Detected"
        secondary_actual = str(state["detected"]) if state["exercised"] else "—"
        secondary_target = f"/ {state['exercised']}" if state["exercised"] else ""
        secondary_status = state["detection_status"]
        fault_tiles.append(
            ui.metric_tile(
                title=state["label"],
                status=state["status"],
                data_attrs=(("fault", key),),
                metrics=(
                    (
                        "Challenged",
                        str(state["exercised"]),
                        f"/ {state['required']}",
                        state["class_status"],
                    ),
                    (
                        secondary_label,
                        secondary_actual,
                        secondary_target,
                        secondary_status,
                    ),
                ),
                help_text=group_help,
            )
        )

    cell_inspectors = {key: cell_inspector(state) for key, state in cells.items()}
    fault_inspectors = {
        key: fault_inspector(state)
        for key, state in faults.items()
        if state["status"] != "N/A"
    }
    default_cell = next(iter(cell_inspectors))
    default_fault = next(iter(fault_inspectors), None)
    # Every selection is rendered and one is shown, so a detail keeps the height of its tallest.
    cell_inspector_markup = '<aside class="inspector stack" id="cell-inspector">' + layers(cell_inspectors, default_cell) + "</aside>"
    fault_inspector_markup = (
        '<aside class="inspector stack" id="fault-inspector">' + layers(fault_inspectors, default_fault) + "</aside>"
        if default_fault is not None
        else ""
    )
    fault_layout_class = (
        "fault-layout" if default_fault is not None else "fault-layout no-inspector"
    )
    fault_column = f'<div class="fault-grid">{"".join(fault_tiles)}</div>'
    if generation and any(state.get("semantic_generation") for state in faults.values()):
        fault_column = f'<div class="signal-grid">{fault_column}{generation_summary(generation)}</div>'

    linked_note = ""
    if linked["rows"]:
        failed_count = len(linked["failed"])
        count = len(linked["rows"])
        if failed_count:
            headline = (
                f"{failed_count} of {count} linked tests outside the profile failed, so coverage fails."
                if count != 1
                else "A linked test outside the profile failed, so coverage fails."
            )
        elif count == 1:
            headline = (
                "1 linked test verifies this contract outside its required cases. "
                "It passes but counts for no case until the profile names one."
            )
        else:
            headline = (
                f"{count} linked tests verify this contract outside its required cases. "
                "They pass but count for no case until the profile names one."
            )
        linked_note = (
            f'<div class="linked-note {"not-met" if failed_count else "na"}">'
            f"<strong>{esc(headline)}</strong>"
            f'<a class="section-link" href="{esc(ui.explorer_href(CONTRACT_ID, kind="unbound"))}">Explorer ↗</a></div>'
        )

    contract_key = CONTRACT_ID.lower()
    coverage_domain_card = ui.domain_card(
        label="Verification coverage",
        status=cell_domain,
        href=f"#ce-coverage-{contract_key}",
        meta=coverage_meta(cell_statuses, linked),
        thumb=nav_thumb_matrix(cells),
        navigator=True,
    )
    fault_domain_card = ui.domain_card(
        label="Fault model",
        status=fault_domain,
        href=f"#ce-faults-{contract_key}",
        meta=fault_meta(fault_statuses),
        thumb=nav_thumb_faults(faults),
        navigator=True,
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
                f"{sum(row['status'] == 'MET' for row in technical_support_rows)} "
                f"of {len(technical_support_rows)} pass"
            ),
            thumb=thumb_strip([row["status"] for row in technical_support_rows]),
        )
        support_parts = tuple(
            (
                label,
                combine([row[key] for row in technical_support_rows]),
                sum(row[key] == "MET" for row in technical_support_rows),
                sum(row[key] == "NOT MET" for row in technical_support_rows),
                len(technical_support_rows),
            )
            for label, key in (("Verification", "coverage"), ("Fault model", "fault"))
        )
        technical_support_section = (
            f'<section class="section" id="ce-technical-support-{contract_key}">'
            + ui.section_head(
                title="Technical support",
                links=(
                    ("Explorer ↗", ui.explorer_href(CONTRACT_ID, kind="support")),
                    ("Profile ↗", PROFILE_URL),
                    ("Raw ↗", "requirement-monitor-facts.json"),
                ),
            )
            + ui.support_summary(noun="technical requirements", parts=support_parts)
            + "</section>"
        )

    history_section = ui.history_section(
        section_id=f"ce-history-{contract_key}",
        status=overall,
        link_href=ui.explorer_href(CONTRACT_ID, change="any"),
        link_label="Changes ↗",
        owner_id=CONTRACT_ID,
    )
    verdict_header = ui.verdict_header(
        kicker="Verification status",
        entity_id=CONTRACT_ID,
        status=overall,
        domain_cards=(
            coverage_domain_card + fault_domain_card + technical_support_domain_card
        ),
        domain_strip_class=domain_strip_class,
        map_href=f"{HEALTH_MAP_URL}#overall:{CONTRACT_ID}",
        explorer_href=ui.explorer_href(CONTRACT_ID),
        title=str(contract.get("title") or CONTRACT_ID),
    )
    coverage_section_head = ui.section_head(
        title="Verification matrix",
        links=(
            ("Health Map ↗", f"{HEALTH_MAP_URL}#coverage:{CONTRACT_ID}"),
            ("Depth ↗", f"{HEALTH_MAP_URL}#overall/depth:{CONTRACT_ID}"),
            ("Explorer ↗", ui.explorer_href(CONTRACT_ID, layer="coverage")),
            (f"{contract_noun} ↗", CONTRACT_URL),
            ("Profile ↗", PROFILE_URL),
            ("Raw ↗", "requirement-monitor-facts.json"),
        ),
    )
    fault_section_head = ui.section_head(
        title="Fault model",
        links=(
            ("Health Map ↗", f"{HEALTH_MAP_URL}#faults:{CONTRACT_ID}"),
            ("Mutants caught ↗", f"{HEALTH_MAP_URL}#faults/detect:{CONTRACT_ID}"),
            ("Explorer ↗", ui.explorer_href(CONTRACT_ID, layer="faults")),
            ("Profile ↗", PROFILE_URL),
            ("Model ↗", "test-plan.html#test-plan-fault-model"),
            ("Raw ↗", "requirement-monitor-facts.json"),
        ),
    )

    matrix_statuses = [
        cells[f"{level}|{boundary}"]["overall"] if f"{level}|{boundary}" in cells else "N/A"
        for level, _level_label in LEVELS
        for boundary, _boundary_label in BOUNDARIES
    ]
    matrix_legend = map_legend("Is every required case tested?", matrix_statuses, "The profile does not ask for these cells")
    fault_legend = map_legend("Are its required faults caught?", fault_statuses, "The profile does not ask for these groups")
    monitor = f"""<div id="tf-requirement-monitor">
{verdict_header}
<section class="section" id="ce-coverage-{contract_key}">{coverage_section_head}<div class="dashboard-layout"><div class="panel matrix-wrap"><table><thead><tr><th>Test level</th>{"".join(f"<th>{esc(label)}</th>" for _, label in BOUNDARIES)}</tr></thead><tbody>{"".join(matrix_rows)}</tbody></table>{matrix_legend}{linked_note}</div>{cell_inspector_markup}</div></section>
<section class="section" id="ce-faults-{contract_key}">{fault_section_head}<div class="{fault_layout_class}"><div class="fault-side">{fault_column}{fault_legend}</div>{fault_inspector_markup}</div></section>
{technical_support_section}
{history_section}
</div>"""

    bind_js = (
        "function selectCell(key){if(!showLayer('cell-inspector',key))return;"
        "root.querySelectorAll('[data-cell]').forEach(button=>button.classList.toggle('selected',button.dataset.cell===key));"
        "aimAt(root.querySelector('.matrix-wrap'),root.querySelector('button[data-cell].selected'),root.querySelector('#cell-inspector'));}"
        "function selectFault(key){if(!showLayer('fault-inspector',key))return;"
        "root.querySelectorAll('[data-fault]').forEach(button=>button.classList.toggle('selected',button.dataset.fault===key));"
        "aimAt(root.querySelector('.fault-grid'),root.querySelector('button[data-fault].selected'),root.querySelector('#fault-inspector'));}"
        "root.querySelectorAll('[data-cell]').forEach(button=>button.addEventListener('click',()=>selectCell(button.dataset.cell)));"
        "root.querySelectorAll('[data-fault]').forEach(button=>button.addEventListener('click',()=>selectFault(button.dataset.fault)));"
        # The header's pictures pick a cell or a group below, show it and mark it once.
        "function pulse(node){if(!node)return;node.classList.remove('attn');void node.offsetWidth;node.classList.add('attn');setTimeout(()=>node.classList.remove('attn'),2200)}"
        "function cellOf(key){return [...root.querySelectorAll('button[data-cell]')].find(node=>node.dataset.cell===key)}"
        "function faultOf(key){return [...root.querySelectorAll('button[data-fault]')].find(node=>node.dataset.fault===key)}"
        "function mirror(){root.querySelectorAll('[data-goto-cell]').forEach(b=>b.classList.toggle('current',!!cellOf(b.dataset.gotoCell)?.classList.contains('selected')));root.querySelectorAll('[data-goto-fault]').forEach(b=>b.classList.toggle('current',!!faultOf(b.dataset.gotoFault)?.classList.contains('selected')))}"
        "function go(node,select,key){select(key);mirror();if(node){node.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});setTimeout(()=>pulse(node),380)}}"
        "root.querySelectorAll('[data-goto-cell]').forEach(b=>{const node=()=>cellOf(b.dataset.gotoCell);b.addEventListener('click',()=>go(node(),selectCell,b.dataset.gotoCell));b.addEventListener('mouseenter',()=>node()?.classList.add('peek'));b.addEventListener('mouseleave',()=>node()?.classList.remove('peek'))});"
        "root.querySelectorAll('[data-goto-fault]').forEach(b=>{const node=()=>faultOf(b.dataset.gotoFault);b.addEventListener('click',()=>go(node(),selectFault,b.dataset.gotoFault));b.addEventListener('mouseenter',()=>node()?.classList.add('peek'));b.addEventListener('mouseleave',()=>node()?.classList.remove('peek'))});"
        "root.querySelectorAll('[data-cell],[data-fault]').forEach(b=>b.addEventListener('click',()=>setTimeout(mirror,0)));"
    )
    nav_selector = (
        f'a[href="#ce-coverage-{contract_key}"],a[href="#ce-faults-{contract_key}"],'
        f'a[href="#ce-technical-support-{contract_key}"],a[href="#ce-history-{contract_key}"]'
    )
    init_js = (
        f"selectCell({json.dumps(default_cell)});selectFault({json.dumps(default_fault)});mirror();"
        "arrows('button[data-cell]',selectCell,node=>node.dataset.cell);arrows('button[data-fault]',selectFault,node=>node.dataset.fault);"
    )
    script = ui.monitor_script(
        setup_js="",
        bind_js=bind_js,
        nav_selector=nav_selector,
        init_js=init_js,
    )

    toc_items = [
        ("Verification matrix", f"#ce-coverage-{CONTRACT_ID.lower()}"),
        ("Fault model", f"#ce-faults-{CONTRACT_ID.lower()}"),
    ]
    if technical_support_rows:
        toc_items.append(
            (
                "Technical support",
                f"#ce-technical-support-{CONTRACT_ID.lower()}",
            )
        )
    toc_items.append(("History", f"#ce-history-{CONTRACT_ID.lower()}"))
    needs_payload = json.loads(NEEDS.read_text())
    needs_version = needs_payload["current_version"]
    needs = needs_payload["versions"][needs_version]["needs"]
    navigation_spec = registry.navigation_spec(
        registry.normalize_needs_graph(needs),
        CONTRACT_ID,
        registry.monitor_urls(set((data.get("contracts") or {}).keys())),
    )
    navigation = ui.assurance_navigation(navigation_spec)
    source = ui.render_monitor_shell(
        CANONICAL_OUT.read_text(),
        page_title=page_title,
        assurance_id=CONTRACT_ID.lower(),
        monitor=monitor,
        script=script,
        toc_items=tuple(toc_items),
        navigation=navigation,
    )
    OUT.write_text(source)
    OUT.with_name("verification-assurance-experiment.html").unlink(missing_ok=True)
    OUT.with_name("requirement-monitor-experiment-facts.json").unlink(missing_ok=True)
    print(OUT)


def build() -> None:
    global CONTRACT_ID, OUT

    data = json.loads(FACTS.read_text())
    contract_ids = list((data.get("contracts") or {}).keys())
    if PRIMARY_CONTRACT_ID not in contract_ids:
        raise RuntimeError(
            f"Missing primary Requirement monitor contract: {PRIMARY_CONTRACT_ID}"
        )
    ordered = [PRIMARY_CONTRACT_ID] + sorted(
        contract_id
        for contract_id in contract_ids
        if contract_id != PRIMARY_CONTRACT_ID
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
