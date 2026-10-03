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
        f'<div class="fault-stage {status_class(status) if status else "neutral"}">'
        f"<span>{esc(label)}</span>"
        f"<strong>{esc(value)}</strong>{target_html}{status_html}</div>"
    )


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
            body=class_chain,
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
                class_name="mutant-group",
            )
        )
    # Where the group's semantic mutants came from and what generating them cost (ADR_0004).
    generation = state.get("semantic_generation")
    if generation:
        spend = generation.get("spend") or {}
        origins = generation.get("mutants") or {}
        tokens = int((spend.get("tokens") or {}).get("total") or 0)
        stages = [
            ("Targets", str(generation.get("targets") or 0), None),
            ("Not generated", str(generation.get("not_generated") or 0), "UNKNOWN" if generation.get("not_generated") else None),
            ("By a model", str(origins.get("model") or 0), None),
            ("By an agent", str(origins.get("agent") or 0), None),
            ("Model calls", str(spend.get("calls") or 0), None),
            ("Deferred", str(spend.get("deferred") or 0), None),
            ("Tokens", f"{tokens / 1000:.1f}k" if tokens >= 1000 else str(tokens), None),
            ("List price", f"${spend['list_usd']:.2f}" if spend.get("list_usd") is not None else "—", None),
        ]
        sections.append(
            ui.signal_group(
                title="Semantic generation",
                body='<div class="fault-chain mutant-tally">'
                + "".join(
                    fault_stage(label, value, status)
                    for label, value, status in stages
                    if value not in {"0", "—"} or label in {"Targets", "Model calls"}
                )
                + "</div>",
                class_name="mutant-group",
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
        # What the verdicts that count decided (ADR_0006). A finding shows under its kind, open or
        # closed, and fails while one is open (ADR_0007); only an escalation waits for the person.
        verdicts = [
            ("Pinned", int(judgement.get("verdict_pinned") or 0), None),
            ("Pin pending", int(judgement.get("verdict_pin_pending") or 0), None),
            ("Suppressed", int(judgement.get("verdict_suppressed") or 0), None),
            ("Silent requirement", int(judgement.get("verdict_unspecified") or 0), "NOT MET" if judgement.get("verdict_unspecified_open") else None),
            ("No effect", int(judgement.get("verdict_ineffective") or 0), "NOT MET" if judgement.get("verdict_ineffective_open") else None),
            ("For you", int(judgement.get("verdict_escalated") or 0), "NOT MET" if judgement.get("verdict_escalated") else None),
        ]
        if any(value for _label, value, _status in verdicts):
            stages += [(label, str(value), status) for label, value, status in verdicts]
        sections.append(
            ui.signal_group(
                title="Survivor judgement",
                body='<div class="fault-chain mutant-tally">'
                + "".join(fault_stage(label, value, status) for label, value, status in stages)
                + "</div>",
                class_name="mutant-group",
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


def domain_meta(states: list[str]) -> str:
    parts = []
    for value in ("NOT MET", "UNKNOWN", "MET", "N/A"):
        count = states.count(value)
        if count:
            parts.append(f"{count} {status_label(value).lower()}")
    return " · ".join(parts)


def contract_output_path(contract_id: str) -> Path:
    if contract_id == PRIMARY_CONTRACT_ID:
        return CANONICAL_OUT
    return CANONICAL_OUT.with_name(
        f"contract-evidence-{contract_slug(contract_id)}.html"
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
    semantic_classes = {row["class"] for row in target.get("semantic_mutants") or []}
    for index, group in enumerate(contract["target"]["fault_groups"]):
        faults[str(index)] = fault_state(contract, group, policy)
        if generation and semantic_classes & {item["id"] for item in group["items"]}:
            faults[str(index)]["semantic_generation"] = generation
        judged = (contract.get("fault_actual") or {}).get("survivor_judgement") or {}
        group_counts: dict[str, int] = {}
        for item in group["items"]:
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
    # Whether a requirement or the delegate's decision settles all a caller sees (ADR_0007).
    completeness = domain.completeness_state(contract)
    overall_inputs = [cell_domain, fault_domain, completeness["status"]]
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
                    '<td><div class="matrix-cell na" aria-disabled="true"><span>N/A</span></div></td>'
                )
            else:
                row.append(
                    "<td>"
                    f'<button class="matrix-cell {status_class(state["overall"])}" type="button" data-cell="{esc(state["key"])}">'
                    f'<span class="cell-status status {status_class(state["overall"])}">{esc(status_label(state["overall"]))}</span>'
                    '<span class="cell-values">'
                    f"<span><small>Passing</small><strong>{state['semantic_actual']}</strong></span>"
                    f"<span><small>Required</small><strong>{state['required_count']}</strong></span>"
                    "</span></button></td>"
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
        secondary_label = "Detection"
        secondary_actual = (
            "—"
            if state["detection_actual"] is None
            else f"{state['detection_actual']:.0f}%"
        )
        secondary_target = "" if state["detection_actual"] is None else "100%"
        secondary_status = state["detection_status"]
        fault_tiles.append(
            ui.metric_tile(
                title=state["label"],
                status=state["status"],
                data_attrs=(("fault", key),),
                metrics=(
                    (
                        "Classes",
                        str(state["exercised"]),
                        f"/ {state['required']}",
                        None,
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
    fault_inspector_markup = (
        f'<aside class="inspector" id="fault-inspector">{fault_inspectors[default_fault]}</aside>'
        if default_fault is not None
        else ""
    )
    fault_layout_class = (
        "fault-layout" if default_fault is not None else "fault-layout no-inspector"
    )

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
        meta=domain_meta(cell_statuses),
    )
    fault_domain_card = ui.domain_card(
        label="Fault model",
        status=fault_domain,
        href=f"#ce-faults-{contract_key}",
        meta=domain_meta(fault_statuses),
    )
    completeness_domain_card = (
        ui.domain_card(
            label="Completeness",
            status=completeness["status"],
            # The silent requirements, or the contract's items when it has none.
            href=(
                ui.explorer_href(CONTRACT_ID, kind="silent")
                if completeness["open"] or completeness["closed"]
                else ui.explorer_href(CONTRACT_ID)
            ),
            # In the explorer's words: undecided, a requirement to add, or not required.
            meta=(
                " · ".join(
                    part
                    for part in (
                        f"{completeness['undecided']} undecided" if completeness["undecided"] else "",
                        f"{completeness['to_add']} requirement{'' if completeness['to_add'] == 1 else 's'} to add"
                        if completeness["to_add"]
                        else "",
                        f"{completeness['closed']} not required" if completeness["closed"] else "",
                    )
                    if part
                )
                if completeness["open"] or completeness["closed"]
                else "No silent requirement"
            ),
        )
        if completeness["status"] != "N/A"
        else ""
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
                f"/ {len(technical_support_rows)} pass"
            ),
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
            coverage_domain_card
            + fault_domain_card
            + completeness_domain_card
            + technical_support_domain_card
        ),
        domain_strip_class=domain_strip_class,
        map_href=f"{HEALTH_MAP_URL}#overall:{CONTRACT_ID}",
        explorer_href=ui.explorer_href(CONTRACT_ID),
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

    monitor = f"""<div id="tf-requirement-monitor">
{verdict_header}
<section class="section" id="ce-coverage-{contract_key}">{coverage_section_head}<div class="dashboard-layout"><div class="panel matrix-wrap"><table><thead><tr><th>Test level</th>{"".join(f"<th>{esc(label)}</th>" for _, label in BOUNDARIES)}</tr></thead><tbody>{"".join(matrix_rows)}</tbody></table>{linked_note}</div><aside class="inspector" id="cell-inspector">{cell_inspectors[default_cell]}</aside></div></section>
<section class="section" id="ce-faults-{contract_key}">{fault_section_head}<div class="{fault_layout_class}"><div class="fault-grid">{"".join(fault_tiles)}</div>{fault_inspector_markup}</div></section>
{technical_support_section}
{history_section}
</div>"""

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
