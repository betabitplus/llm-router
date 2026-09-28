from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape as html_unescape
from pathlib import Path
from urllib.parse import unquote as urllib_unquote
from typing import Any, cast

ROOT = Path.cwd()
HTML = ROOT / "docs/_build/html"
BRIDGE = ROOT / ".ai-bridge"


def load_domain():
    """The shared assurance algebra the monitors judge with."""
    spec = importlib.util.spec_from_file_location("gate_assurance_domain", BRIDGE / "assurance_monitor_domain.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the assurance domain module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fingerprints():
    """The campaign's own fingerprints by meaning (implementation_faults.plugin_sha256), so the gate
    judges freshness by the same rule the campaign and the qualification use."""
    spec = importlib.util.spec_from_file_location("gate_implementation_faults", BRIDGE / "implementation_faults.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the implementation faults module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    return json.loads(path.read_text())


def only_campaign_extras(contract: dict, challenged: set, expected: set) -> bool:
    """Classes challenged beyond the declared retained challenges may only come from
    the current Implementation fault campaign, or, for a specification or interface class,
    from current semantic mutants that the cascade decided (caught or told apart)."""
    classes = (contract.get("fault_actual") or {}).get("classes") or {}

    def semantic_challenge(class_id: str) -> bool:
        row = classes.get(class_id, {})
        counts = row.get("semantic_counts") or {}
        return (
            class_id.startswith(("spec.", "interface."))
            and row.get("semantic_state") == "current"
            and int(counts.get("caught") or 0) + int(counts.get("distinguished") or 0) > 0
        )

    return set(expected) <= set(challenged) and all(
        (class_id.startswith("impl.") and classes.get(class_id, {}).get("campaign_state") == "current")
        or semantic_challenge(class_id)
        for class_id in set(challenged) - set(expected)
    )


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def explorer_matches(item: dict, facet: str, value: str, changes: dict | None = None) -> bool:
    """One filter of the Verification Explorer, as its page applies it: a producer belongs to the owners it served;
    a change is what the item did since the previous retained run; text is found in what the row says."""
    attrs = item.get("attrs") or {}
    if facet == "change":
        parts = ("up", "down", "new") if value == "any" else value.split(",")
        return any(item["id"] in set((changes or {}).get(part) or []) for part in parts)
    if facet == "q":
        text = " ".join(str(item.get(key) or "") for key in ("name", "what", "note", "state", "owner")).lower()
        return value.lower() in text
    holders = [item["owner"]] if item.get("owner") else list(attrs.get("users") or [])
    if facet == "contract":
        return value in holders
    if facet == "kind":
        return item.get("kind") == value
    if facet == "layer":
        return value in (item.get("layers") or [])
    if facet in {"level", "boundary", "group"}:
        return attrs.get(facet) == value
    if facet == "status":
        return item.get("status") == value
    if facet == "cause":
        return value in (item.get("causes") or [])
    raise AssertionError(f"the gate does not know the explorer filter {facet}")


def check_verification_explorer(module: str) -> None:
    """The Verification Explorer lists every item behind the monitors, judged as the monitors judge them: the gate
    recounts each kind from the retained facts, refuses a false PASS, wants a cause on every red row, resolves every
    link and follows every monitor link to a list that is not empty."""
    page = (HTML / "verification-explorer.html").read_text()
    start = page.index("const model=") + len("const model=")
    model, _end = json.JSONDecoder().raw_decode(page, start)
    items = model["items"]
    by_kind: dict[str, list[dict]] = {}
    for item in items:
        by_kind.setdefault(item["kind"], []).append(item)
    explorer_js = module.split('EXPLORER_JS = r"""', 1)[-1].split('"""', 1)[0]
    shared_js = module.split('MAP_SHARED_JS = r"""', 1)[-1].split('"""', 1)[0]
    check(
        page.count('<section id="verification-explorer">') == 1
        and "<h1>Verification Explorer" in page
        and '<style id="tf-explorer-style">' in page
        and "explorerPage(model).start();" in page
        and shared_js in page
        and explorer_js in page
        and "#verification-explorer{--tf-map-ease" in page
        and "#verification-health-map" not in page
        and 'id="tf-map-changes"' in page
        and set(model.get("delta") or {}) >= {"baseline", "layers"}
        and (
            set(((model["delta"].get("layers") or {}).get("items") or {})) == {"up", "down", "new", "gone"}
            and all(
                set(model["delta"]["layers"]["items"][part]) <= {item["id"] for item in items}
                for part in ("up", "down", "new")
            )
            if model["delta"].get("baseline")
            else not model["delta"].get("layers")
        )
        and "No earlier retained run to compare with yet" in explorer_js
        and "Nothing here changed since" in explorer_js
        and "const LAYERS=MAP_HEALTH_LAYERS.filter" in explorer_js
        and "const LAYERS=MAP_HEALTH_LAYERS;" in module,
        "the Verification Explorer is one section on the map's shared runtime and styles, scoped to itself; it names its "
        "layers with the Health Map's own questions and compares its items with the previous retained run, saying so "
        "when there is none yet or nothing changed",
    )
    kinds = set(re.findall(r'^  \["(\w+)","fa-', explorer_js, flags=re.MULTILINE))
    fixes = set(re.findall(r'^  "?([\w:&]+)"?:"', explorer_js.split("const FIX={", 1)[1].split("};", 1)[0], flags=re.MULTILINE))
    used_causes = {cause for item in items for cause in item["causes"]}
    check(
        {item["kind"] for item in items} <= kinds
        and kinds == {"path", "unbound", "fault", "mutant", "check", "support", "producer"}
        and used_causes <= set(model["causes"])
        and used_causes <= fixes
        and all(item["causes"] for item in items if item["status"] in {"fail", "unknown"})
        and not any(item["causes"] for item in items if item["status"] in {"pass", "na"})
        and len({item["id"] for item in items}) == len(items),
        "every explorer item is of a declared kind with a unique id; every failing or unknown item names a cause that "
        "says what it means and how to fix it, and a passing or N/A item names none",
    )
    facts = json.loads((HTML / "requirement-monitor-facts.json").read_text())["contracts"]
    upper = json.loads((HTML / "upper-assurance-facts.json").read_text())
    slots = 0
    false_pass = []
    wrong_missing = []
    for contract_id, contract in facts.items():
        target = contract.get("target") or {}
        for cell in target.get("coverage") or []:
            for criterion in cell.get("items") or []:
                named = list((cell.get("item_path_ids") or {}).get(criterion) or [])
                slots += len(named) or int((cell.get("item_path_counts") or {}).get(criterion, 1))
                rows = [
                    row
                    for row in (contract.get("coverage_actual") or {}).get(criterion, [])
                    if row.get("level") == cell["level"] and row.get("boundary") == cell["boundary"]
                ]
                for item in by_kind.get("path", []):
                    if item["object"] != f"criterion|{contract_id}|{criterion}":
                        continue
                    found = [row for row in rows if not named or str(row.get("coverage_path") or "").strip() == item["name"]]
                    sound = [
                        row
                        for row in found
                        if row.get("result") == "passed"
                        and str(row.get("freshness") or "").upper() == "CURRENT"
                        and row.get("provenance_scope") == "full_chain"
                        and str(row.get("provenance") or "").upper() == "COMPLETE"
                        and row.get("producer_qualification_scope") == "full_chain"
                        and str(row.get("producer_qualification") or "").upper() == "QUALIFIED"
                    ]
                    if item["status"] == "pass" and not sound:
                        false_pass.append(item["id"])
                    if item["state"] == "Missing" and (found if named else len(rows) >= len([
                        other for other in by_kind["path"] if other["object"] == item["object"]
                    ])):
                        wrong_missing.append(item["id"])
    unexpected = [item for item in by_kind.get("path", []) if item["state"] == "Unexpected"]
    required_classes = [
        (contract_id, spec["id"], spec["state"])
        for contract_id, contract in facts.items()
        for group in (contract.get("target") or {}).get("fault_groups") or []
        for spec in group.get("items") or []
        if spec.get("state") in {"required", "optional"}
    ]
    def class_caught(actual: dict) -> bool:
        return bool(actual.get("exercised") and actual.get("detected") and not int(actual.get("undecided") or 0))

    caught = {
        (contract_id, class_id)
        for contract_id, class_id, state in required_classes
        if state == "required"
        and class_caught(((facts[contract_id].get("fault_actual") or {}).get("classes") or {}).get(class_id, {}))
    }
    fault_pass = {(item["owner"], item["name"]) for item in by_kind.get("fault", []) if item["status"] == "pass"}
    check(
        len(by_kind.get("path", [])) == slots + len(unexpected)
        and not false_pass
        and not wrong_missing
        and len(by_kind.get("unbound", [])) == sum(len(contract.get("linked_outside_profile") or []) for contract in facts.values())
        and len(by_kind.get("fault", [])) == len(required_classes)
        and fault_pass == caught
        and all(item["status"] == "na" for item in by_kind.get("fault", []) if item["attrs"]["applicability"] == "optional"),
        f"the explorer lists every required path of every criterion ({slots}) and every required or optional fault "
        f"class ({len(required_classes)}): a path passes only on a passing, current, traceable, qualified retained test "
        "at its cell, a missing path has none, a class passes only when caught, an optional class never judges",
    )
    listed = {(contract_id, class_id) for contract_id, class_id, _state in required_classes}
    campaign = load(ROOT / "test-results/implementation-faults/campaign.json")
    # A survivor a recorded verdict judged equivalent or irrelevant (ADR_0006) may show as suppressed: the person's
    # decision wins over the model's answer, and the class says how many of its survivors a verdict suppressed.
    recorded_verdicts = {}
    verdict_root = BRIDGE / "survivor-verdicts"
    for folder in sorted(path for path in verdict_root.iterdir() if path.is_dir()) if verdict_root.is_dir() else []:
        answered = load(folder / "verdicts.json") if (folder / "verdicts.json").is_file() else {}
        decided = load(folder / "decisions.json") if (folder / "decisions.json").is_file() else {}
        for key in set(answered) | set(decided):
            recorded_verdicts[(folder.name, key)] = effective_verdict(answered.get(key) or {}, decided.get(key))
    mutants_expected = []
    for contract_id, entry in sorted((campaign.get("contracts") or {}).items()):
        classes_actual = ((facts.get(contract_id) or {}).get("fault_actual") or {}).get("classes") or {}
        plan = entry.get("plan") or {}
        allowed = {(path, line) for path, lines in (plan.get("attributable_lines") or {}).items() for line in lines}
        report_path = ROOT / str((entry.get("run") or {}).get("report_path") or "")
        for result in (load(report_path).get("results") or []) if report_path.is_file() else []:
            klass = MUTATION_CLASSES.get(str(result.get("operator")))
            if (contract_id, klass) not in listed or (relative_path(result.get("file_path")), int(result.get("line_number") or -1)) not in allowed:
                continue
            # A result that no longer counts shows on its class, never as mutants.
            if (classes_actual.get(klass) or {}).get("campaign_state") != "current":
                continue
            raw = str(result.get("status"))
            status = "pass" if raw in {"zapped", "timeout"} else "na" if raw in {"pardoned", "error"} else "fail"
            cause = [] if status != "fail" else ["notreached" if result.get("covered") is False else "survivors"]
            fingerprint = str(result.get("fingerprint"))
            judged = recorded_verdicts.get((contract_id, fingerprint)) if raw == "survived" and cause in (["survivors"], ["notreached"]) else None
            mutants_expected.append((contract_id, fingerprint, status, cause, klass, judged if judged in {"equivalent", "irrelevant"} else None))
    semantic_expected = []
    for contract_id in sorted(semantic_selections()):
        retained_path = ROOT / f"test-results/semantic-mutants/{contract_id}.json"
        for row in (load(retained_path).get("results") or []) if retained_path.is_file() else []:
            if (contract_id, row["class"]) in listed:
                semantic_expected.append((contract_id, row["id"], SEMANTIC_OUTCOME_STATUS[row["outcome"]]))
    mutant_rows = {item["id"]: item for item in by_kind.get("mutant", [])}
    not_generated = []
    for contract_id in sorted(semantic_selections()):
        proposals_path = BRIDGE / f"semantic-mutants/{contract_id}/proposals.json"
        targets = {row["target"] for row in (load(proposals_path).get("proposals") or [])} if proposals_path.is_file() else set()
        for selection in ((facts.get(contract_id) or {}).get("target") or {}).get("semantic_mutants") or []:
            if selection["target"] not in targets and (contract_id, selection["class"]) in listed:
                not_generated.append(f"mutant|{contract_id}|semantic-target:{selection['target']}")
    check(
        all(
            (mutant_rows.get(row_id) or {}).get("status") == "unknown" and (mutant_rows.get(row_id) or {}).get("causes") == ["generate"]
            for row_id in not_generated
        )
        and {key for key in mutant_rows if "|semantic-target:" in key} == set(not_generated),
        f"the explorer lists the {len(not_generated)} selected targets without a semantic mutant as Not generated, UNKNOWN, never green",
    )
    check(
        all(
            (mutant_rows.get(f"mutant|{contract_id}|semantic:{proposal_id}") or {}).get("status") == status
            and (mutant_rows.get(f"mutant|{contract_id}|semantic:{proposal_id}") or {}).get("attrs", {}).get("origin") == "semantic"
            for contract_id, proposal_id, status in semantic_expected
        ),
        f"the explorer lists the {len(semantic_expected)} semantic mutants under their class, with the cascade's outcome",
    )
    mutant_rows = {key: item for key, item in mutant_rows.items() if item.get("attrs", {}).get("origin") != "semantic"}

    def row_right(contract_id: str, fingerprint: str, status: str, cause: list, judged: str | None) -> bool:
        item = mutant_rows.get(f"mutant|{contract_id}|{fingerprint}") or {}
        if judged and item.get("status") == "na":
            return item.get("causes") == [] and item.get("state") == f"Suppressed · {judged}"
        return item.get("status") == status and item.get("causes") == cause

    by_verdict = Counter(
        (contract_id, klass) for contract_id, fingerprint, _status, _cause, klass, judged in mutants_expected
        if judged and (mutant_rows.get(f"mutant|{contract_id}|{fingerprint}") or {}).get("status") == "na"
    )
    check(
        len(mutant_rows) == len(mutants_expected)
        and all(row_right(contract_id, fingerprint, status, cause, judged) for contract_id, fingerprint, status, cause, _klass, judged in mutants_expected)
        and all(
            by_verdict.get((contract_id, klass), 0)
            == int(((((facts.get(contract_id) or {}).get("fault_actual") or {}).get("classes") or {}).get(klass) or {}).get("suppressed_by_verdict") or 0)
            for contract_id, klass in {(row[0], row[4]) for row in mutants_expected}
        )
        and all(item["object"] in {row["id"] for row in by_kind["fault"]} for item in mutant_rows.values())
        and all(item["attrs"].get("origin") in {"rule", "semantic"} for item in mutant_rows.values()),
        f"the explorer lists the {len(mutants_expected)} mutants whose campaign result counts, one row each under its class: "
        "caught when a test failed on it, survived when its line runs and none did, not reached when no test runs its "
        f"line, N/A when suppressed or invalid, and suppressed by a recorded verdict ({sum(by_verdict.values())}) exactly as its class counts",
    )
    upper_entities = [*upper.get("features", {}).values(), *upper.get("goals", {}).values(), upper.get("product_system") or {}]
    upper_criteria = sum(
        len((block or {}).get("criteria") or [])
        for entity in upper_entities
        for key, block in entity.items()
        if isinstance(block, dict) and "criteria" in block
    )
    upper_children = sum(
        len((block or {}).get("children") or [])
        for entity in upper_entities
        for key, block in entity.items()
        if isinstance(block, dict) and "children" in block
    )
    qualification = load(HTML / "evidence-confidence-qualification.json")
    check(
        len(by_kind.get("check", [])) == upper_criteria
        and len(by_kind.get("support", [])) == upper_children + sum(len((contract.get("target") or {}).get("required_treqs") or []) for contract in facts.values())
        and len(by_kind.get("producer", [])) == len(qualification.get("producers") or {})
        and all(item["status"] == "pass" for item in by_kind.get("producer", []) if (qualification["producers"].get(item["attrs"]["producer"]) or {}).get("status") == "QUALIFIED")
        and model["rows"][0]["id"] == "PRODUCT_SYSTEM",
        f"the explorer lists every own check of goals and capabilities ({upper_criteria}), everything each item rests on "
        "and every evidence producer as qualified now; the product is PRODUCT_SYSTEM, as on its monitor",
    )
    texts: dict[str, str] = {}
    broken = []
    links = [link for item in items for link in item["links"]] + [link for obj in model["objects"].values() for link in obj.get("links") or []]
    for link in links:
        href = link[1]
        if href.startswith(("http://", "https://", "#")):
            continue
        name, _sep, anchor = href.partition("#")
        path = HTML / name
        if not path.exists():
            broken.append(href)
            continue
        if name == "mutation-report.html" and anchor.startswith("mutant/"):
            # Mutation Testing Elements routes by file, not by element id: the file must be in the report.
            report_files = texts.setdefault("mutation-report.json#files", "\n".join(load(HTML / "mutation-report.json").get("files") or {}))
            if anchor.removeprefix("mutant/") not in report_files.split("\n"):
                broken.append(href)
            continue
        if anchor and not name.startswith("test-results/"):
            text = texts.setdefault(name, path.read_text())
            if f'id="{anchor}"' not in text:
                broken.append(href)
    evidence_links = sorted(
        {
            str(row.get("evidence_url") or "")
            for contract in facts.values()
            for rows in (contract.get("coverage_actual") or {}).values()
            for row in rows
        }
    )
    evidence_record_page = (HTML / "ternforge-test-evidence.html").read_text()
    check(
        bool(evidence_links)
        and all(
            url.startswith("ternforge-test-evidence.html#") and f'id="{url.split("#", 1)[1]}"' in evidence_record_page
            for url in evidence_links
        ),
        f"every retained path's evidence link in the monitor facts opens the test's own evidence record ({len(evidence_links)})",
    )
    spec_links = sum(1 for link in links if link[0] == "Spec")
    check(
        not broken and spec_links > 0,
        f"every explorer link opens a page that exists at an anchor that exists ({len(links)} links, {spec_links} to "
        f"Living Specification scenarios): {broken[:5]}",
    )
    dead = []
    monitors = sorted(HTML.glob("contract-evidence-*.html")) + [HTML / "verification-assurance.html"] + sorted(HTML.glob("assurance-*.html"))
    for monitor in monitors:
        text = monitor.read_text()
        # An inspector is embedded as a JSON string, where its quotes are escaped.
        found = re.findall(r'href=\\?"verification-explorer\.html#([^"\\]+)', text)
        if not found:
            dead.append(f"{monitor.name}: no link")
        changes = (model["delta"].get("layers") or {}).get("items") or {}
        for query in found:
            params = [pair.split("=", 1) for pair in html_unescape(query).split("&")]
            keep = [
                item
                for item in items
                if all(
                    explorer_matches(item, key, urllib_unquote(value.replace("+", " ")), changes)
                    for key, value in params
                )
            ]
            # A list of changes may be empty: the page then says there is nothing to compare with yet or that
            # nothing changed.
            if not keep and not any(key == "change" for key, _value in params):
                dead.append(f"{monitor.name}#{query}")
    check(
        not dead and len(monitors) >= 88,
        f"every Contract Evidence and assurance monitor ({len(monitors)}) links to its items in the explorer, and every "
        f"such link opens a list that is not empty: {dead[:5]}",
    )


MUTATION_OPERATORS = ["comparison", "boundary", "arithmetic", "boolean", "return", "statement", "body"]
MUTATION_CLASSES = {
    "comparison": "impl.comparison",
    "boundary": "impl.boundary",
    "arithmetic": "impl.arithmetic",
    "boolean": "impl.control-flow",
    "return": "impl.control-flow",
    "statement": "impl.effect",
    "body": "impl.effect",
}
MTE_STATUSES = {"Killed", "Survived", "NoCoverage", "Timeout", "RuntimeError", "CompileError", "Ignored", "Pending"}


def relative_path(value: object) -> str:
    path = Path(str(value or ""))
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def expected_mte_status(result: dict) -> str:
    status = str(result.get("status") or "error")
    if status == "zapped":
        return "Killed"
    if status == "timeout":
        return "Timeout"
    if status == "pardoned":
        return "Ignored"
    if status == "error":
        return "RuntimeError"
    return "NoCoverage" if result.get("covered") is False else "Survived"


def check_mutation_system(monitor_facts: dict) -> None:
    """Mutation testing after ADR_0003: one qualified engine behind the campaign, classes judged by
    outcome, the standard report recounted from the retained engine reports, visible pragmas, the
    pull-request diff, and no trace of mutmut or of mutation scores."""
    campaign = load(ROOT / "test-results/implementation-faults/campaign.json")
    extension_digest = load_fingerprints().plugin_sha256()
    engine = campaign.get("engine_configuration") or {}
    check(
        campaign.get("schema") == "ternforge-implementation-fault-campaign-2"
        and engine.get("operators") == MUTATION_OPERATORS
        and engine.get("plugin_sha256") == extension_digest
        and campaign.get("class_by_operator") == MUTATION_CLASSES,
        "the campaign runs the seven operators of the current engine extension, arithmetic to impl.arithmetic and statement and body removal to impl.effect",
    )
    entries = campaign.get("contracts") or {}
    stale_engine = sorted(
        contract_id for contract_id, entry in entries.items() if (entry.get("engine") or {}).get("plugin_sha256") != extension_digest
    )
    check(bool(entries) and not stale_engine, f"every retained campaign entry ran the current engine extension: {stale_engine}")
    policy = monitor_facts.get("policy") or {}
    arid_ids = {rule.get("id") for rule in policy.get("arid_rules") or []}
    check(
        arid_ids == {"arid.logging", "arid.sleep", "arid.type-checking", "arid.repr"}
        and "mutation_reach_floor" not in policy
        and "mutation_sensitivity_floor" not in policy
        and policy.get("mutation_policy_url") == "test-plan.html#test-plan-mutation-policy",
        "the monitors read the Test Plan's four arid-code rules and no mutation floor",
    )
    contracts = monitor_facts.get("contracts") or {}
    effect_states = {
        contract_id: next(
            (item.get("state") for group in (contract.get("target") or {}).get("fault_groups") or [] for item in group.get("items") or [] if item.get("id") == "impl.effect"),
            None,
        )
        for contract_id, contract in contracts.items()
    }
    check(
        len(effect_states) == 63 and all(state in {"required", "optional", "na"} for state in effect_states.values())
        and not any("mutation" in (contract.get("target") or {}) for contract in contracts.values()),
        "every one of the 63 verification profiles classifies impl.effect, and none selects a mutation threshold",
    )
    arithmetic_states = {
        contract_id: next(
            (item.get("state") for group in (contract.get("target") or {}).get("fault_groups") or [] for item in group.get("items") or [] if item.get("id") == "impl.arithmetic"),
            None,
        )
        for contract_id, contract in contracts.items()
    }
    check(
        len(arithmetic_states) == 63 and all(state in {"required", "optional", "na"} for state in arithmetic_states.values())
        and {contract_id for contract_id, state in arithmetic_states.items() if state == "required"}
        == {"REQ_CREDENTIAL_RESOLUTION", "REQ_STRUCTURED_OUTPUT_REPAIR", "TREQ_RATE_LIMIT_STATE", "TREQ_USAGE_NORMALIZATION"},
        "every one of the 63 verification profiles classifies impl.arithmetic, required where the contract's code computes with it",
    )
    check(
        not any("### Blocking mutation checks" in path.read_text() for path in (ROOT / "docs/verification-profiles").glob("*.md")),
        "no verification profile keeps a Blocking mutation checks table",
    )

    # Every retained entry: its report is the recorded file, every mutant carries the extension's facts,
    # and every entry uses only Test Plan arid rules.
    reports = {}
    for contract_id, entry in sorted(entries.items()):
        run = entry.get("run") or {}
        path = ROOT / str(run.get("report_path") or "")
        ok = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == run.get("report_sha256")
        report = load(path) if ok else {}
        reports[contract_id] = report
        results = report.get("results") or []
        check(
            ok
            and (report.get("ternforge") or {}).get("schema") == "ternforge-mutation-extension-1"
            and set((entry.get("plan") or {}).get("arid_rules") or []) <= arid_ids
            and all(
                row.get("fingerprint") and row.get("location") and "covered" in row and row.get("origin") == "rule"
                for row in results
            ),
            f"{contract_id}: the retained engine report is the recorded file and every mutant carries its fingerprint, location, reach and origin",
        )

    # Reach: a mutant the engine reports as not reached sits on a line that none of its contract's tests
    # ran in the retained run either (Coverage.py dynamic contexts).
    from coverage import CoverageData

    retained_coverage = CoverageData(basename=str(ROOT / "test-results/.coverage"))
    retained_coverage.read()
    measured = {Path(name).resolve(): name for name in retained_coverage.measured_files()}
    contexts_by_file: dict[str, dict] = {}
    reach_conflicts = []
    not_reached = 0
    for contract_id, entry in sorted(entries.items()):
        tests = set((entry.get("plan") or {}).get("tests") or [])
        for row in (reports.get(contract_id) or {}).get("results") or []:
            if row.get("status") != "survived" or row.get("covered") is not False:
                continue
            not_reached += 1
            name = measured.get(Path(str(row.get("file_path"))).resolve())
            if name is None:
                continue
            if name not in contexts_by_file:
                contexts_by_file[name] = retained_coverage.contexts_by_lineno(name)
            ran = {context.split("|", 1)[0] for context in contexts_by_file[name].get(int(row.get("line_number") or -1), [])}
            if ran & tests:
                reach_conflicts.append(f"{contract_id}:{relative_path(row.get('file_path'))}:{row.get('line_number')}")
    check(
        not reach_conflicts,
        f"all {not_reached} mutants reported as not reached sit on lines their contract's tests did not run in the retained run either: {reach_conflicts[:5]}",
    )

    # The standard report, recounted from the retained engine reports of the contracts whose result counts.
    report = load(HTML / "mutation-report.json")
    config = report.get("config") or {}
    current = [
        contract_id
        for contract_id, contract in contracts.items()
        if contract_id in entries
        and any((row or {}).get("campaign_state") == "current" for row in ((contract.get("fault_actual") or {}).get("classes") or {}).values())
    ]
    check(
        report.get("schemaVersion") == "2"
        and report.get("thresholds") == {"high": 100, "low": 100}
        and sorted(config.get("contracts") or []) == sorted(current)
        and sorted([*(config.get("contracts") or []), *(config.get("not_current") or [])]) == sorted(entries),
        "the mutation report follows the Mutation Testing Report Schema 2 and holds every contract whose result counts, naming the others",
    )
    expected: dict[str, str] = {}
    for contract_id in config.get("contracts") or []:
        plan = entries[contract_id].get("plan") or {}
        allowed = {(path, line) for path, lines in (plan.get("attributable_lines") or {}).items() for line in lines}
        raw = reports.get(contract_id) or {}
        for row in raw.get("results") or []:
            if row.get("operator") in MUTATION_CLASSES and (relative_path(row.get("file_path")), int(row.get("line_number") or -1)) in allowed:
                expected[str(row.get("fingerprint"))] = expected_mte_status(row)
        for row in (raw.get("ternforge") or {}).get("not_planted") or []:
            if (relative_path(row.get("file_path")), int(row.get("line_number") or -1)) in allowed:
                expected[str(row.get("fingerprint"))] = "Ignored"
    mutants = [(path, row) for path, source in (report.get("files") or {}).items() for row in source.get("mutants") or []]
    actual = {str(row.get("id")): str(row.get("status")) for _path, row in mutants}
    check(
        bool(expected) and actual == expected and len(actual) == len(mutants),
        f"the mutation report lists exactly the {len(expected)} mutants of the retained reports (arid ones as Ignored) with their statuses",
    )
    check(
        all(row.get("status") in MTE_STATUSES for _path, row in mutants)
        and all(row.get("statusReason") for _path, row in mutants if row.get("status") in {"Ignored", "NoCoverage"})
        and all(source.get("source") == (ROOT / path).read_text() for path, source in (report.get("files") or {}).items()),
        "every mutant has a schema status, every ignored or uncovered one says why, and every file's source is the current file",
    )
    page = (HTML / "mutation-report.html").read_text()
    check(
        'src="mutation-report.json"' in page
        and 'src="_static/mutation-test-elements.js"' in page
        and 'href="verification-explorer.html#kind=mutant"' in page
        and 'href="test-plan.html#test-plan-mutation-policy"' in page,
        "the mutation report page renders the report with the pinned Mutation Testing Elements and leads back to the explorer and the policy",
    )

    # Pragmas: every `# mutation:` pragma parses and suppresses a mutant; the engine's own pragma is not used.
    pragma_lines = {
        (str(path.relative_to(ROOT)), number)
        for path in (ROOT / "src").rglob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if re.search(r"#\s*mutation:", line)
    }
    matched, broken = set(), []
    for raw in reports.values():
        for path, items in ((raw.get("ternforge") or {}).get("pragmas") or {}).items():
            for item in items:
                if item.get("error"):
                    broken.append(f"{path}:{item.get('line')} {item.get('error')}")
                if item.get("matched"):
                    matched.add((path, int(item.get("line") or -1)))
    check(not broken, f"every mutation pragma names a known category and operators and gives a reason: {broken}")
    check(pragma_lines <= matched, f"every mutation pragma in the source suppresses at least one mutant: {sorted(pragma_lines - matched)}")
    check(
        not any(re.search(r"#\s*gremlin:", path.read_text()) for path in (ROOT / "src").rglob("*.py")),
        "the engine's own pardon pragma is not used",
    )

    # The pull-request diff: changed, attributable, covered lines; one finding per line, each on its line.
    diff = load(ROOT / "test-results/implementation-faults/diff/summary.json")
    findings = diff.get("findings") or []
    per_line: dict[tuple, int] = {}
    for finding in findings:
        per_line[(finding.get("source"), finding.get("line"))] = per_line.get((finding.get("source"), finding.get("line")), 0) + 1
    annotations = [line for line in (ROOT / "test-results/implementation-faults/diff/annotations.txt").read_text().splitlines() if line]
    survived_in_diff = set()
    for contract_id, row in (diff.get("contracts") or {}).items():
        raw = load(ROOT / row["report_path"]) if row.get("report_path") else {}
        survived_in_diff |= {
            (contract_id, str(result.get("fingerprint")))
            for result in raw.get("results") or []
            if result.get("status") == "survived" and result.get("covered") is True
        }
        check(
            all(result.get("run_skipped") == "not covered" for result in raw.get("results") or [] if result.get("covered") is False)
            and (raw.get("ternforge") or {}).get("skip_uncovered") is True,
            f"{contract_id}: the diff run does not run the mutants no test covers",
        )
    check(
        diff.get("schema") == "ternforge-mutation-diff-1"
        and bool(diff.get("merge_base"))
        and all(count == 1 for count in per_line.values())
        and all((finding.get("contract_id"), finding.get("fingerprint")) in survived_in_diff for finding in findings)
        and len(annotations) == len(findings)
        and all(line.startswith("::warning file=") and ",line=" in line for line in annotations),
        f"the pull-request diff reports {len(findings)} findings: at most one surviving, covered mutant per changed line, each as one annotation on its line",
    )

    # Retired: mutmut, its page, raw pages, strength facts, suppression ledger, P31 targets, snapshots and history.
    for retired in (
        HTML / "mutation-analysis.html",
        HTML / "mutation-results",
        HTML / "verification-test-strength-facts.json",
        HTML / "assurance-history",
        HTML / "assurance-snapshots.json",
        HTML / "assurance-targets.json",
        BRIDGE / "assurance-targets.json",
        BRIDGE / "assurance-snapshots.json",
        BRIDGE / "mutation-suppressions.json",
    ):
        check(not retired.exists(), f"retired with mutmut (ADR_0003): {retired.relative_to(ROOT)} is gone")
    builder = (BRIDGE / "build-mutation-report-prototype.py").read_text()
    check(
        all(token not in builder for token in ("def run_mutmut", "MUTMUT_VERSION", "STRENGTH", '"--suppress"', '"--mode"', "write_mutation_analysis_page", "build_dvc_assurance_history"))
        and all("mutmut" not in (BRIDGE / name).read_text().lower() for name in (
            "assurance_map_pages.py", "assurance_monitor_ui.py", "assurance_monitor_domain.py",
            "build-requirement-monitor.py", "build-upper-assurance-pilot.py", "implementation_faults.py",
        )),
        "no mutmut campaign, flag, page writer or trend history remains in the builder, and no renderer mentions mutmut",
    )
    check_semantic_mutants(monitor_facts)
    adr = (ROOT / "docs/decisions/0003-mutation-testing-strategy.md").read_text()
    check(
        ":id: ADR_0003" in adr
        and ":status: accepted" in adr
        and all(section in adr for section in ("**Context.**", "**Decision.**", "**Consequences.**", "**Alternatives considered.**"))
        and all(owner in adr for owner in ("`py-testkit`", "`ternforge-tooling-docops`", "`ternforge-infra-ci`", "project template"))
        and "0003-mutation-testing-strategy" in (ROOT / "docs/decisions/index.md").read_text(),
        "ADR_0003 records the mutation strategy, its alternatives and where each piece moves after the pilot",
    )
    adr4 = (ROOT / "docs/decisions/0004-metered-model-generation.md").read_text()
    check(
        ":id: ADR_0004" in adr4
        and ":status: accepted" in adr4
        and all(section in adr4 for section in ("**Context.**", "**Decision.**", "**Consequences.**", "**Alternatives considered.**"))
        and all(owner in adr4 for owner in ("`py-testkit`", "`ternforge-tooling-docops`", "`ternforge-infra-ci`", "project template"))
        and "0004-metered-model-generation" in (ROOT / "docs/decisions/index.md").read_text(),
        "ADR_0004 records metered model generation through subscription CLIs, its alternatives and where each piece moves after the pilot",
    )
    adr5 = (ROOT / "docs/decisions/0005-survivor-judgement.md").read_text()
    check(
        ":id: ADR_0005" in adr5
        and ":status: accepted" in adr5
        and all(section in adr5 for section in ("**Context.**", "**Decision.**", "**Consequences.**", "**Alternatives considered.**"))
        and all(owner in adr5 for owner in ("`py-testkit`", "`ternforge-tooling-docops`", "`ternforge-infra-ci`", "project template"))
        and "advisory" in adr5
        and "0005-survivor-judgement" in (ROOT / "docs/decisions/index.md").read_text(),
        "ADR_0005 records the survivor judgement: symbolic search first, calibrated assessors second, their equivalent advisory",
    )
    adr6 = (ROOT / "docs/decisions/0006-survivor-verdicts.md").read_text()
    check(
        ":id: ADR_0006" in adr6
        and ":status: accepted" in adr6
        and all(section in adr6 for section in ("**Context.**", "**Decision.**", "**Consequences.**", "**Alternatives considered.**"))
        and all(owner in adr6 for owner in ("`py-testkit`", "`ternforge-tooling-docops`", "`ternforge-infra-ci`", "project template"))
        and "escalate" in adr6 and "canaries" in adr6
        and "0006-survivor-verdicts" in (ROOT / "docs/decisions/index.md").read_text(),
        "ADR_0006 records the verdict model: pins, suppressed equivalents, escalations only at Features and Goals, canaries on every model change",
    )


SEMANTIC_OUTCOME_STATUS = {
    "caught": "pass",
    "distinguished": "fail",
    "undecided": "unknown",
    "stale": "unknown",
    "equivalent": "na",
    "identical": "na",
    "duplicate": "na",
    "invalid": "na",
}


def semantic_selections() -> set[str]:
    selected = set()
    for path in sorted((ROOT / "docs/verification-profiles").glob("*.md")):
        for section in path.read_text().split("\n## Profile · ")[1:]:
            if "\n### Semantic mutants\n" in section:
                selected.add(section.split("\n", 1)[0].strip())
    return selected


# What must never appear in a ledger row or a stored model answer: credentials, tokens, sign-in links.
SECRET_PATTERNS = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{10,}"
    r"|ya29\.[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|accounts\.google\.com/signin"
)


def load_bridge_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    # Its dataclasses resolve their annotations through sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_semantic_mutants(monitor_facts: dict) -> None:
    """Semantic mutants: frozen proposals with their provenance, judged by the qualified cascade, and
    counted on their class beside its other challenges; an undecided one keeps the class UNKNOWN. A
    generated mutant or draft is exactly what a ledgered model call returned, and a selected target
    without any mutant keeps its class UNKNOWN."""
    models = load_bridge_module("gate_model_generation", "model_generation.py")
    cascade = load_bridge_module("gate_semantic_mutants", "semantic_mutants.py")
    selected = semantic_selections()
    check(bool(selected), f"at least one profile selects semantic mutants: {sorted(selected)}")
    junit_text = (ROOT / "test-results/pytest-junit.xml").read_text()
    check(
        'classname=".ai-bridge' not in junit_text and "semantic-mutants" not in junit_text,
        "no draft test, calibration check or other .ai-bridge file is part of the retained test run",
    )
    qualification = load(HTML / "evidence-confidence-qualification.json")
    record = (qualification.get("producers") or {}).get("PRODUCER_SEMANTIC_MUTANT_CASCADE") or {}
    control = record.get("control") or {}
    check(
        record.get("status") == "QUALIFIED"
        and control.get("outcomes") == control.get("expected")
        and set((control.get("expected") or {}).values()) >= {"identical", "duplicate", "invalid", "caught", "undecided", "distinguished", "stale", "equivalent"}
        and (control.get("kept_draft") or {}).get("accepted") is True
        and (control.get("rejected_draft") or {}).get("accepted") is False
        and (control.get("primitive_draft") or {}).get("ran") is False
        and "adds an import" in (control.get("reasons") or {}).get("C-CONFINED", "")
        and (control.get("target_without_proposals") or {}).get("undecided") == 1,
        "the semantic mutant cascade is qualified: every calibration proposal got its known outcome, model code that reaches "
        "beyond its module is invalid, a draft is kept or rejected as specified and one that reaches beyond is never run, "
        "and a target without proposals stays undecided",
    )
    adapter = (qualification.get("producers") or {}).get("PRODUCER_MODEL_GENERATION_ADAPTER") or {}
    usable = set(adapter.get("backends_qualified") or [])
    check(
        adapter.get("status") == "QUALIFIED"
        and "claude-cli" in usable
        and bool(adapter.get("control"))
        and all((adapter.get("control") or {}).values()),
        f"the model generation adapter is qualified for {sorted(usable)}: recorded answers and their failing variants, "
        "deferral above the budget, fallback in order, the call limit and bound answers all behave as specified",
    )
    policy = (monitor_facts.get("policy") or {}).get("model_generation") or {}
    check(
        set(policy.get("roles") or {}) == set(models.ROLES.values())
        and set(policy.get("budget") or {}) == set(models.BUDGET_LABELS.values()),
        "the Test Plan names every model role with its backends in order and every generation limit",
    )
    ledger_path = BRIDGE / "semantic-mutants/model-ledger.jsonl"
    ledger = models.read_ledger(ledger_path)
    by_call = {row["call_id"]: row for row in ledger}
    stored = {
        path.stem: path
        for pattern in ("semantic-mutants/*/responses/*.json", "survivor-triage/*/responses/*.json", "survivor-verdicts/*/responses/*.json")
        for path in BRIDGE.glob(pattern)
    }
    check(
        all(row.get("schema") == models.LEDGER_SCHEMA and row.get("outcome") in models.OUTCOMES and row.get("call_id") and row.get("run_id") for row in ledger)
        and len(by_call) == len(ledger),
        f"the model ledger's {len(ledger)} rows are well formed, one per call",
    )
    check(
        all(row["call_id"] in stored for row in ledger if row["outcome"] == "ok" and row.get("role") != "probe")
        and all(by_call.get(call_id, {}).get("outcome") == "ok" for call_id in stored)
        and all(not row.get("response_sha256") for row in ledger if row["outcome"] != "ok"),
        f"each of the {len(stored)} stored model answers belongs to an accepted call, and no failed, deferred or unavailable call left one",
    )
    texts = [ledger_path.read_text() if ledger_path.is_file() else ""] + [path.read_text() for path in stored.values()]
    check(
        not any(SECRET_PATTERNS.search(text) for text in texts),
        "no ledger row or stored model answer carries a credential, a token or a sign-in link",
    )
    for call_id, path in sorted(stored.items()):
        response = load(path)
        check(
            not models.verify_response(response) and models.response_sha256(response) == by_call[call_id].get("response_sha256"),
            f"stored answer {call_id}: its prompt, schema and answer match their digests and its ledger row",
        )

    def bound(generator: dict, contract_id: str) -> dict:
        """The stored answer a model-made mutant or draft names, when it and its ledger row agree."""
        response_path = BRIDGE / f"semantic-mutants/{contract_id}/responses/{generator.get('call_id')}.json"
        response = load(response_path) if response_path.is_file() else {}
        call = by_call.get(str(generator.get("call_id"))) or {}
        agrees = (
            response
            and models.response_sha256(response) == generator.get("response_sha256") == call.get("response_sha256")
            and call.get("outcome") == "ok"
            and generator.get("backend") == response.get("backend") == call.get("backend")
            and generator.get("model") == response.get("model") == call.get("model")
            and generator.get("backend") in usable
        )
        return response if agrees else {}

    for contract_id in sorted(selected):
        folder = BRIDGE / f"semantic-mutants/{contract_id}"
        proposals = load(folder / "proposals.json") if (folder / "proposals.json").is_file() else {}
        rows_proposed = proposals.get("proposals") or []
        top = proposals.get("generator") or {}
        selections = ((monitor_facts.get("contracts") or {}).get(contract_id, {}).get("target") or {}).get("semantic_mutants") or []
        classes = ((monitor_facts.get("contracts") or {}).get(contract_id, {}).get("fault_actual") or {}).get("classes") or {}
        missing = [selection for selection in selections if selection["target"] not in {row["target"] for row in rows_proposed}]
        for class_id in {selection["class"] for selection in missing}:
            count = sum(selection["class"] == class_id for selection in missing)
            actual = classes.get(class_id) or {}
            check(
                int(actual.get("undecided") or 0) >= count
                and int(actual.get("semantic_not_generated") or 0) == count
                and not (actual.get("exercised") and actual.get("detected") and not int(actual.get("undecided") or 0)),
                f"{contract_id} · {class_id}: {count} selected target(s) without a semantic mutant keep the class undecided",
            )
        for proposal in rows_proposed:
            generator = proposal.get("generator") or top
            if generator.get("kind") == "model":
                response = bound(generator, contract_id)
                items = (response.get("structured") or {}).get("proposals") or []
                index = int(generator.get("index", -1))
                item = items[index] if 0 <= index < len(items) else {}
                check(
                    bool(response)
                    and item.get("replacement") == proposal.get("replacement")
                    and item.get("defect") == proposal.get("rationale")
                    and proposal.get("prompt_sha256") == response.get("prompt_sha256")
                    and proposal.get("id") == cascade.proposal_id(proposal.get("replacement") or ""),
                    f"{contract_id} · {proposal['id']}: the generated mutant is exactly item {index} of what ledgered call {generator.get('call_id')} returned",
                )
            else:
                check(
                    generator.get("kind") == "agent" and bool(generator.get("model")) and bool(generator.get("prompt_template_sha256")) and bool(proposal.get("prompt_sha256")),
                    f"{contract_id} · {proposal['id']}: the agent-written mutant names its model and the prompt it answered",
                )
        provenance_path = folder / "drafts/provenance.json"
        provenance = load(provenance_path) if provenance_path.is_file() else {}
        for draft_path in sorted((folder / "drafts").glob("*.draft.py")) if (folder / "drafts").is_dir() else []:
            content = draft_path.read_text()
            match = re.search(r"# semantic-mutant: (\S+)", content)
            mutant_id = match.group(1) if match else ""
            origin = provenance.get(mutant_id) or {}
            if origin.get("kind") == "model":
                response = bound(origin, contract_id)
                check(
                    bool(response) and content == cascade.draft_from_answer(mutant_id, response.get("structured") or {}),
                    f"{contract_id} · draft for {mutant_id}: it is exactly the test module ledgered call {origin.get('call_id')} returned",
                )
            else:
                check(
                    bool(mutant_id) and top.get("kind") == "agent",
                    f"{contract_id} · draft for {mutant_id}: an agent-written draft is covered by its proposal set's agent provenance",
                )
        if not rows_proposed:
            continue
        retained = load(ROOT / f"test-results/semantic-mutants/{contract_id}.json")
        rows = {row["id"]: row for row in retained.get("results") or []}
        check(
            retained.get("schema") == "ternforge-semantic-mutants-1"
            and set(rows) == {row["id"] for row in rows_proposed}
            and all(row["outcome"] in SEMANTIC_OUTCOME_STATUS for row in rows.values())
            and all(row.get("original_sha256") and row.get("context_sha256") and row.get("prompt_sha256") and row.get("replacement") for row in rows_proposed),
            f"{contract_id}: every frozen semantic mutant carries its provenance, and the cascade judged each one",
        )
        check(
            all((row.get("differential") or {}).get("found") and (row.get("differential") or {}).get("input") for row in rows.values() if row["outcome"] == "distinguished")
            and all((row.get("tests") or {}).get("returncode") == 1 for row in rows.values() if row["outcome"] == "caught")
            and all((row.get("tests") or {}).get("returncode") == 0 for row in rows.values() if row["outcome"] in {"distinguished", "undecided"})
            and all(
                (row.get("draft") or {}).get("passes_on_original") == 5 and (row.get("draft") or {}).get("fails_on_mutant") is True
                for row in rows.values()
                if (row.get("draft") or {}).get("accepted")
            )
            and all((row.get("draft") or {}).get("ran") is False for row in rows.values() if (row.get("draft") or {}).get("primitives") or (row.get("draft") or {}).get("imports_beyond_allowed") or (row.get("draft") or {}).get("lint")),
            f"{contract_id}: a caught mutant failed a contract test, a survivor passed them all, a distinguished one names its input, "
            "a kept draft passes five times and fails on its mutant, and a draft that reaches beyond or breaks a lint rule was never run",
        )
        for class_id in {row["class"] for row in rows.values()}:
            counts = {outcome: sum(row["outcome"] == outcome for row in rows.values() if row["class"] == class_id) for outcome in SEMANTIC_OUTCOME_STATUS}
            actual = classes.get(class_id) or {}
            check(
                actual.get("semantic_state") == "current"
                and actual.get("semantic_counts") == counts
                and int(actual.get("undecided") or 0) >= counts["undecided"] + counts["stale"]
                and (not counts["distinguished"] or actual.get("detected") is False)
                and ((counts["caught"] + counts["distinguished"]) == 0 or actual.get("exercised") is True),
                f"{contract_id} · {class_id}: the class counts its current semantic mutants, and a distinguished one keeps it from being caught",
            )
        for proposal in rows_proposed:
            check(
                (HTML / f"semantic-mutants/{contract_id}/{proposal['id']}.diff").is_file(),
                f"{contract_id} · {proposal['id']}: its frozen patch is published as a raw diff",
            )
    published = {path.name for path in (HTML / "semantic-mutants").glob("*/responses/*.json")}
    own = {path.name for contract_id in selected for path in (BRIDGE / f"semantic-mutants/{contract_id}/responses").glob("*.json")}
    check(
        published == own,
        f"every stored model answer of a semantic mutant is published beside the mutants it produced ({len(published)})",
    )
    check_survivor_judgement(monitor_facts, models, by_call, usable)
    check_survivor_verdicts(models, by_call, usable)
    check_draft_attempts(by_call)
    check_ladder(monitor_facts)


DRAFT_CAUSES = {"kept", "syntax", "grounding", "runtime-api", "rules", "lint", "behaviour", "weak", "unknown"}


def check_draft_attempts(by_call: dict) -> None:
    """The draft attempts and their check (049): every recorded attempt a ledgered draft-author call
    with a known cause, a grounding problem only behind that cause; and the grounding check, which
    rejects a draft before it runs, finding nothing in the project's own tests and pins, all of which
    run green: a false alarm there would reject good drafts."""
    semantic = semantic_module()
    verdict_dir = BRIDGE / "survivor-verdicts"
    attempts = [
        (folder.name, key, row)
        for folder in sorted(path for path in verdict_dir.iterdir() if path.is_dir()) if verdict_dir.is_dir()
        for key, rows in (load(folder / "drafts.json") if (folder / "drafts.json").is_file() else {}).items()
        for row in rows
    ]
    check(
        all(
            (by_call.get(str(row.get("call_id"))) or {}).get("purpose") == "mutation-pin"
            and str((by_call.get(str(row.get("call_id"))) or {}).get("role") or "").startswith("draft_author")
            and row.get("cause") in DRAFT_CAUSES - {"unknown"}
            and bool(row.get("grounding")) == (row.get("cause") == "grounding")
            and len(str(row.get("question_sha256") or "")) == 64
            # The rung an attempt names is the role its call was made in.
            and str((by_call.get(str(row.get("call_id"))) or {}).get("role")) in {1: ("draft_author", "draft_author_retry"), 2: ("draft_author_tools",), 3: ("draft_author_last",)}.get(int(row.get("level") or 1), ())
            for _contract, _key, row in attempts
        ),
        f"every one of the {len(attempts)} recorded draft attempts is a ledgered draft-author call with a known cause, made on the rung it names",
    )
    corpus = [
        path for path in sorted((ROOT / "tests").rglob("test_*.py"))
        if "__pycache__" not in path.parts
    ]
    flagged = {
        str(path.relative_to(ROOT)): problems
        for path in corpus
        if (problems := semantic.grounding_problems(ROOT, path.read_text())[0])
    }
    check(
        not flagged,
        f"the grounding check finds nothing in the project's {len(corpus)} test modules and pins, which all run green: {flagged}",
    )


def check_ladder(monitor_facts: dict) -> None:
    """The draft author's ladder (ADR_0004): its rungs with tools served only by the claude CLI, whose
    permissions hold the tools to the copy, and its last resort the verdict's own model."""
    roles = ((monitor_facts.get("policy") or {}).get("model_generation") or {}).get("roles") or {}
    tools = [entry for role in ("draft_author_tools", "draft_author_last") for entry in roles.get(role) or []]
    check(
        bool(tools) and all(entry.get("backend") == "claude-cli" for entry in tools)
        and [entry.get("model") for entry in roles.get("draft_author_last") or []][:1] == [entry.get("model") for entry in roles.get("verdict") or []][:1],
        "the draft author's rungs with tools run only through the claude CLI, and its last resort is the verdict's own model "
        f"({[entry.get('model') for entry in roles.get('draft_author_last') or []]})",
    )


def recorded_answer_files() -> dict[tuple[str, str], Path]:
    """Every stored answer a current record names, by the page folder it is published in and its
    call: draft attempts, verdicts, reviews and pins by contract, assessor answers by contract, the
    calibration's and the canaries'."""
    found: dict[tuple[str, str], Path] = {}

    def add(group: str, folder: Path, call_id: object) -> None:
        path = folder / "responses" / f"{call_id}.json"
        if call_id and path.is_file():
            found[(group, str(call_id))] = path

    verdict_dir = BRIDGE / "survivor-verdicts"
    for folder in sorted(path for path in verdict_dir.iterdir() if path.is_dir()) if verdict_dir.is_dir() else []:
        for rows in (load(folder / "drafts.json") if (folder / "drafts.json").is_file() else {}).values():
            for row in rows:
                add(folder.name, folder, row.get("call_id"))
        for entry in (load(folder / "verdicts.json") if (folder / "verdicts.json").is_file() else {}).values():
            for part in ("answer", "review", "pin"):
                add(folder.name, folder, (entry.get(part) or {}).get("call_id"))
    for store in (BRIDGE / "survivor-triage", BRIDGE / "semantic-mutants"):
        for path in sorted(store.glob("*/assessments.json")) if store.is_dir() else []:
            for entry in load(path).values():
                for answer in (entry.get("answers") or {}).values():
                    add(path.parent.name, path.parent, answer.get("call_id"))
    calibration = BRIDGE / "semantic-mutants/assessor-calibration"
    record = load(calibration / "calibration.json") if (calibration / "calibration.json").is_file() else {}
    for answers in (record.get("answers") or {}).values():
        for answer in answers.values():
            add("calibration", calibration, answer.get("call_id"))
    canaries = BRIDGE / "semantic-mutants/canary-results"
    for canary in (load(canaries / "results.json") if (canaries / "results.json").is_file() else {}).values():
        for case in (canary.get("cases") or {}).values():
            add("canaries", canaries, case.get("call_id"))
    return found


def check_model_roles_page() -> None:
    """The Model roles page (049): one section drawn from the retained records, whose draft counts
    and health the gate recounts from the recorded attempts, with each canary as its record says."""
    page_path = HTML / "model-roles.html"
    page = page_path.read_text() if page_path.is_file() else ""
    marker = '<script type="application/json" id="tf-model-roles-facts">'
    check(
        page.count('<section id="model-roles">') == 1 and "<h1>Model roles" in page and marker in page
        and '<style id="tf-model-roles-style">' in page and "#model-roles{--tf-map-ease" in page,
        "the Model roles page is one section with its own scoped styles and the facts it was drawn from",
    )
    if marker not in page:
        return
    facts = json.loads(page.split(marker, 1)[1].split("</script>", 1)[0].replace("<\\/", "</"))
    verdict_dir = BRIDGE / "survivor-verdicts"
    recorded = sorted(
        (row for folder in sorted(path for path in verdict_dir.iterdir() if path.is_dir()) if verdict_dir.is_dir()
         for rows in (load(folder / "drafts.json") if (folder / "drafts.json").is_file() else {}).values() for row in rows),
        key=lambda row: (str(row.get("at") or ""), str(row.get("call_id") or "")),
    )
    draft = facts.get("draft") or {}
    recent = recorded[-int(draft.get("window") or 0):] if draft.get("window") else []
    kept = sum(row.get("cause") == "kept" for row in recent)
    status = "unknown" if len(recent) < int(draft.get("minimum") or 0) else "fail" if kept / len(recent) < float(draft.get("floor") or 0) else "pass"
    check(
        draft.get("recorded") == len(recorded) and draft.get("recent") == len(recent) and draft.get("kept") == kept
        and draft.get("status") == status and (draft.get("window"), draft.get("floor"), draft.get("minimum")) == (20, 0.2, 10),
        f"the Model roles page counts the {len(recorded)} recorded draft attempts as they are: {kept} of the last {len(recent)} kept, {status}",
    )
    canaries = load(BRIDGE / "semantic-mutants/canary-results/results.json")
    check(
        all(row.get("passed") == bool((canaries.get(row.get("entry")) or {}).get("passed")) for row in facts.get("canaries") or [])
        and bool(facts.get("canaries")),
        "every canary on the Model roles page stands as its record says",
    )
    # Every stored question and answer a record names is published byte for byte beside the page,
    # and every link the page gives to one is there.
    stored = recorded_answer_files()
    published = {(path.parent.name, path.stem) for path in (HTML / "model-roles").glob("*/*.json")}
    linked = [
        *(row.get("answer") for row in [*(draft.get("rejected") or []), *(draft.get("last_resort") or []), *((facts.get("judging") or {}).get("troubled") or [])]),
        *(path for row in facts.get("canaries") or [] for _case, path in row.get("answers") or []),
    ]
    check(
        published == set(stored)
        and all((HTML / "model-roles" / group / f"{call}.json").read_bytes() == stored[(group, call)].read_bytes() for group, call in published)
        and all(f'href="{link}"' in page and (HTML / str(link)).is_file() for link in linked if link),
        f"every stored question and answer a record names is published beside the Model roles page ({len(published)}), and every link to one resolves",
    )
    # The page recounts the judging roles' sources from their records.
    judged = [
        answer
        for folder in sorted(path for path in verdict_dir.iterdir() if path.is_dir()) if verdict_dir.is_dir()
        for entry in (load(folder / "verdicts.json") if (folder / "verdicts.json").is_file() else {}).values()
        for answer in (entry.get("answer") or {}, entry.get("review") or {}) if answer.get("call_id") and "sources" in answer
    ] + [
        answer
        for path in sorted((BRIDGE / "survivor-triage").glob("*/assessments.json"))
        for entry in load(path).values() for answer in (entry.get("answers") or {}).values() if answer.get("call_id") and "sources" in answer
    ]
    roles = (facts.get("judging") or {}).get("roles") or []
    check(
        sum(row.get("answers", 0) for row in roles) == len(judged) and sum(row.get("troubled", 0) for row in roles) == sum(bool(answer.get("problems")) for answer in judged),
        f"the Model roles page counts the {len(judged)} judging answers that cite, {sum(bool(answer.get('problems')) for answer in judged)} of them not holding up, as their records are",
    )


JUDGEMENT_STATUSES = {"found", "likely-equivalent", "unsure", "not-applicable"}


PIN_HEADERS = ("# mutation-pin:", "# pinned-by:", "# written-by:", "# semantic-mutant:")
# The draft author's rungs: who may have written a pin, and through which role (ADR_0004).
PIN_WRITERS = {"draft author": ("draft_author", "draft_author_retry"), "draft author with tools": ("draft_author_tools",), "last resort": ("draft_author_last",)}


def pin_body(text: str) -> str:
    """A pin or draft without its header lines: the test exactly as the cascade judged it."""
    return "\n".join(line for line in text.splitlines() if not line.startswith(PIN_HEADERS)).strip() + "\n"


_SEMANTIC = None


def semantic_module():
    """The cascade's module, loaded once: the gate normalizes a pin's origin as the cascade did."""
    global _SEMANTIC
    if _SEMANTIC is None:
        spec = importlib.util.spec_from_file_location("gate_semantic_mutants", BRIDGE / "semantic_mutants.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load the semantic mutant cascade")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SEMANTIC = module
    return _SEMANTIC


VERDICTS = ("pin", "equivalent", "irrelevant", "escalate")
SUPPRESSING = ("equivalent", "irrelevant")


def effective_verdict(entry: dict, decided: dict | None = None) -> str | None:
    """The verdict a record holds as it counts (ADR_0006): the person's; else the model's pin or
    escalate; its equivalent or irrelevant only with a review that agrees, pin against one that
    does not, none without one."""
    if decided and decided.get("verdict") in VERDICTS and decided.get("reason"):
        return decided["verdict"]
    answer = entry.get("answer") or {}
    if answer.get("problems") or answer.get("verdict") not in VERDICTS:
        return None
    if answer["verdict"] not in SUPPRESSING:
        return answer["verdict"]
    review = entry.get("review") or {}
    if review.get("prompt_sha256") != entry.get("prompt_sha256") or review.get("problems") or review.get("verdict") not in VERDICTS:
        return None
    return answer["verdict"] if review["verdict"] in SUPPRESSING else "pin"


def pin_origin_holds(models, by_call: dict, folder: Path, key: str, pin: dict) -> bool:
    """A pin's test is what its origin wrote, in the project's style: the draft author's stored,
    ledgered answer, or the semantic draft the cascade kept, normalized again by the same ruff into
    exactly the pin's body, with no lint rule left broken."""
    semantic = semantic_module()
    if pin.get("source") in PIN_WRITERS:
        path = folder / "responses" / f"{pin.get('call_id')}.json"
        response = load(path) if path.is_file() else {}
        call = by_call.get(str(pin.get("call_id"))) or {}
        # A rung with tools wrote it in a copy of the project: its stored answer names that copy's one file.
        with_tools = pin.get("source") != "draft author"
        if not (
            bool(response) and not models.verify_response(response)
            and models.response_sha256(response) == pin.get("response_sha256") == call.get("response_sha256")
            and call.get("outcome") == "ok" and response.get("purpose") == "mutation-pin" and response.get("subject") == key
            and str(call.get("role")) in PIN_WRITERS[str(pin.get("source"))]
            and bool((response.get("workspace") or {}).get("write")) == with_tools
        ):
            return False
        draft = semantic.draft_from_answer(key, response.get("structured") or {})
    elif pin.get("source") == "kept semantic draft":
        drafts = sorted((BRIDGE / "semantic-mutants" / folder.name / "drafts").glob("*.draft.py"))
        kept = [path.read_text() for path in drafts if re.search(rf"# semantic-mutant: {re.escape(key)}\s", path.read_text())]
        if len(kept) != 1:
            return False
        draft = kept[0]
    else:
        return False
    if hashlib.sha256(pin_body(draft).encode()).hexdigest() != pin.get("answer_sha256") or pin.get("normalizer") != semantic.ruff_version():
        return False
    normalized, lint = semantic.normalize_draft(draft, str(pin.get("path")))
    return not lint and hashlib.sha256(pin_body(normalized).encode()).hexdigest() == pin.get("draft_sha256")


def check_survivor_verdicts(models, by_call: dict, usable: set) -> None:
    """The survivor verdicts (ADR_0006): the model canaries qualified for their current records; every
    model verdict a stored, ledgered call's answer; every mutation pin naming its contract and mutant,
    carrying exactly the draft the cascade kept after a pin verdict, that draft its origin's own, and
    no pin without its record."""
    qualification = load(HTML / "evidence-confidence-qualification.json")
    canary = (qualification.get("producers") or {}).get("PRODUCER_MODEL_CANARIES") or {}
    results_path = BRIDGE / "semantic-mutants/canary-results/results.json"
    check(
        canary.get("status") == "QUALIFIED"
        and (canary.get("control") or {}).get("results_sha256") == (hashlib.sha256(results_path.read_bytes()).hexdigest() if results_path.is_file() else None),
        f"the model canaries are qualified for their current records {sorted(key for key, passed in ((canary.get('control') or {}).get('records') or {}).items() if passed)}",
    )
    verdict_dir = BRIDGE / "survivor-verdicts"
    judge = load_bridge_module("gate_verdict_equivalence", "survivor_equivalence.py")
    recorded: set[str] = set()
    for folder in sorted(path for path in verdict_dir.iterdir() if path.is_dir()) if verdict_dir.is_dir() else []:
        verdicts = load(folder / "verdicts.json") if (folder / "verdicts.json").is_file() else {}
        decided = load(folder / "decisions.json") if (folder / "decisions.json").is_file() else {}
        bound = pins_ok = True
        for key, entry in verdicts.items():
            # The verdict and, for a suppression, its review: each a stored, ledgered call's answer to the
            # entry's question (asked once more, it says what broke), its sources and problems read from it
            # by the current rule.
            for answer in [entry.get("answer") or {}, *([entry["review"]] if entry.get("review") else [])]:
                response_path = folder / "responses" / f"{answer.get('call_id')}.json"
                response = load(response_path) if response_path.is_file() else {}
                call = by_call.get(str(answer.get("call_id"))) or {}
                structured = response.get("structured") or {}
                asked = judge.asked_question(str(response.get("prompt") or ""))
                bound = bound and bool(response) and (
                    models.response_sha256(response) == answer.get("response_sha256") == call.get("response_sha256")
                    and call.get("outcome") == "ok" and response.get("backend") in usable
                    and hashlib.sha256(asked.encode()).hexdigest() == entry.get("prompt_sha256")
                    and all(structured.get(name) == answer.get(name) for name in ("verdict", "level", "reason", "test_focus", "sources"))
                    and ("confirmed" not in answer or judge.verdict_problems(structured, bool(answer["confirmed"]), str(response.get("prompt") or "")) == answer.get("problems"))
                )
            pin = entry.get("pin")
            if not pin:
                continue
            recorded.add(str(pin.get("path")))
            pin_file = ROOT / str(pin.get("path"))
            pin_text = pin_file.read_text() if pin_file.is_file() else ""
            pins_ok = pins_ok and (
                pin_text.startswith(f"# mutation-pin: {folder.name} {key}\n")
                and hashlib.sha256(pin_body(pin_text).encode()).hexdigest() == pin.get("draft_sha256")
                and (pin.get("cascade") or {}).get("accepted") is True
                and effective_verdict(entry, decided.get(key)) == "pin"
                and pin_origin_holds(models, by_call, folder, key, pin)
            )
        check(bound, f"{folder.name}: every verdict about its survivors is a stored, ledgered call's answer")
        check(pins_ok, f"{folder.name}: every mutation pin names its mutant and is the draft the cascade kept after a pin verdict, as its origin wrote it")
    pin_files = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "tests/llm_router/mutation_pins").glob("test_pin_*.py"))
    check(all(path in recorded for path in pin_files), f"every one of the {len(pin_files)} mutation pins is recorded with its verdict")


def check_survivor_judgement(monitor_facts: dict, models, by_call: dict, usable: set) -> None:
    """The survivor judgement (ADR_0005): its two producers qualified; a survivor decided only by an
    input that execution confirmed; an assessors' equivalent only a label, above the calibrated
    threshold and unanimous, never an outcome; the rule survivors' triage never changing an outcome;
    every assessor answer a stored, ledgered call's."""
    qualification = load(HTML / "evidence-confidence-qualification.json")
    producers = qualification.get("producers") or {}
    symbolic = producers.get("PRODUCER_SYMBOLIC_DIFFERENTIAL") or {}
    ensemble = producers.get("PRODUCER_ASSESSOR_ENSEMBLE") or {}
    check(
        symbolic.get("status") == "QUALIFIED" and all(((symbolic.get("control") or {}).get("checks") or {}).values()),
        "the symbolic search and the witness check are qualified on the labelled pairs",
    )
    record_path = BRIDGE / "semantic-mutants/assessor-calibration/calibration.json"
    record = load(record_path) if record_path.is_file() else {}
    # The replayed calibration is the whole folder: the record and every stored answer it cites.
    calibration_files = sorted(path for path in record_path.parent.rglob("*") if path.is_file()) if record_path.is_file() else []
    calibration_sha256 = hashlib.sha256(
        b"".join(str(path.relative_to(record_path.parent)).encode() + b"\0" + path.read_bytes() for path in calibration_files)
    ).hexdigest() if calibration_files else None
    check(
        ensemble.get("status") == "QUALIFIED"
        and all(((ensemble.get("control") or {}).get("checks") or {}).values())
        and (ensemble.get("control") or {}).get("threshold") == record.get("threshold")
        and (ensemble.get("control") or {}).get("record_sha256") == hashlib.sha256(record_path.read_bytes()).hexdigest()
        and (ensemble.get("control") or {}).get("calibration_sha256") == calibration_sha256,
        f"the assessor ensemble is qualified by its replayed calibration (threshold {record.get('threshold')}, "
        f"{(record.get('metrics') or {}).get('distinct')} distinct pairs, rate {record.get('alpha')})",
    )
    policy = (monitor_facts.get("policy") or {}).get("model_generation") or {}
    members = [row["key"] for row in policy.get("assessors") or []]
    check(
        bool(members) and (policy.get("judgement") or {}).get("assessed_equivalence") == "advisory",
        f"the Test Plan names the survivor assessors {members} and keeps their equivalent advisory",
    )
    threshold = record.get("threshold")
    # One usable model per assessor: the combinations the calibration gave a threshold.
    configurations = [row.get("members") for row in record.get("configurations") or []]
    judge = load_bridge_module("gate_survivor_equivalence", "survivor_equivalence.py")

    def answers_bound(folder: Path) -> bool:
        assessments = load(folder / "assessments.json") if (folder / "assessments.json").is_file() else {}
        for entry in assessments.values():
            for answer in (entry.get("answers") or {}).values():
                response_path = folder / "responses" / f"{answer.get('call_id')}.json"
                response = load(response_path) if response_path.is_file() else {}
                call = by_call.get(str(answer.get("call_id"))) or {}
                structured = response.get("structured") or {}
                # The stored answer is its response read by the current rule, arguments and problems included.
                if not (
                    response and models.response_sha256(response) == answer.get("response_sha256") == call.get("response_sha256")
                    and call.get("outcome") == "ok" and response.get("backend") in usable
                    and structured.get("verdict") == answer.get("verdict") and structured.get("confidence") == answer.get("confidence")
                    and {key: judge.argument_text(value) for key, value in (structured.get("arguments") or {}).items()} == answer.get("arguments")
                    and judge.answer_problems(structured, str(response.get("prompt") or "")) == answer.get("problems")
                ):
                    return False
        return True

    def judged_right(judged: dict, outcome_ok: bool) -> bool:
        status = judged.get("status")
        if status not in JUDGEMENT_STATUSES or not outcome_ok:
            return False
        if status == "found":
            witness = judged.get("witness") or {}
            return (
                bool(witness.get("display")) and witness.get("original") != witness.get("mutant")
                and witness.get("original_sha256") != witness.get("mutant_sha256")
            )
        if status == "likely-equivalent":
            voted = judged.get("members") or []
            return (
                judged.get("calibrated") is True and threshold is not None and judged.get("threshold") == threshold
                and float(judged.get("score") or 0) > threshold and [row.get("member") for row in voted] in configurations
                and all(row.get("verdict") == "equivalent" for row in voted)
            )
        return True

    for contract_id in sorted(semantic_selections()):
        retained_path = ROOT / f"test-results/semantic-mutants/{contract_id}.json"
        rows = (load(retained_path).get("results") or []) if retained_path.is_file() else []
        judged_rows = [row for row in rows if row.get("judgement")]
        check(
            all(
                judged_right(row["judgement"], row["outcome"] == "distinguished" if row["judgement"].get("status") == "found" else row["outcome"] == "undecided")
                for row in judged_rows
            )
            and all((row.get("differential") or {}).get("by") for row in judged_rows if row["judgement"].get("status") == "found"),
            f"{contract_id}: {len(judged_rows)} judged survivors: distinguished only by a confirmed input, likely equivalent only above the "
            "calibrated threshold and unanimous, and every other one undecided",
        )
        check(
            answers_bound(BRIDGE / f"semantic-mutants/{contract_id}"),
            f"{contract_id}: every assessor answer about its survivors is a stored, ledgered call's answer",
        )
    campaign = load(ROOT / "test-results/implementation-faults/campaign.json")
    triaged = 0
    for path in sorted((ROOT / "test-results/survivor-triage").glob("*.json")):
        retained = load(path)
        contract_id = retained.get("contract_id")
        entry = (campaign.get("contracts") or {}).get(contract_id) or {}
        report_path = ROOT / ((entry.get("run") or {}).get("report_path") or "")
        statuses = {str(row.get("fingerprint")): row.get("status") for row in (load(report_path).get("results") or [])} if report_path.is_file() else {}
        rows = retained.get("rows") or []
        triaged += len(rows)
        check(
            retained.get("schema") == "ternforge-survivor-triage-1"
            and all(statuses.get(str(row.get("fingerprint"))) == "survived" for row in rows)
            and all(judged_right(row, True) for row in rows),
            f"{contract_id}: its {len(rows)} surviving rule mutants are judged without a changed outcome; a test goal has a confirmed "
            "input, a likely equivalent is above the calibrated threshold and unanimous",
        )
    check(triaged > 0, f"the triage judged {triaged} surviving rule mutants")
    # Every stored answer, also of a contract with no survivor left: the triage reuses an answer whenever its question returns.
    for folder in sorted(path for path in (BRIDGE / "survivor-triage").iterdir() if path.is_dir()):
        check(answers_bound(folder), f"{folder.name}: every assessor answer about its rule survivors is a stored, ledgered call's answer")


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
        ROOT / "test-results/implementation-faults/campaign.json",
        ROOT / "test-results/implementation-faults/diff/summary.json",
        HTML / "mutation-report.html",
        HTML / "mutation-report.json",
        ROOT / "docs/decisions/0003-mutation-testing-strategy.md",
        HTML / "decisions/0003-mutation-testing-strategy.html",
        ROOT / "docs/decisions/0004-metered-model-generation.md",
        HTML / "decisions/0004-metered-model-generation.html",
        BRIDGE / "model_generation.py",
        ROOT / "docs/decisions/0005-survivor-judgement.md",
        HTML / "decisions/0005-survivor-judgement.html",
        ROOT / "docs/decisions/0006-survivor-verdicts.md",
        HTML / "decisions/0006-survivor-verdicts.html",
        BRIDGE / "survivor_equivalence.py",
        BRIDGE / "pytest_plugins/ternforge_mutation.py",
        BRIDGE / "pytest_plugins/gremlins_full_pytest.py",
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
        HTML / "favicon.ico",
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

    depth_facts = load(HTML / "verification-depth-facts.json")
    monitor_facts = load(HTML / "requirement-monitor-facts.json")
    upper_facts = load(HTML / "upper-assurance-facts.json")
    evidence_provenance = load(HTML / "evidence-run-provenance.json")
    evidence_qualification = load(HTML / "evidence-confidence-qualification.json")
    evidence_run_inputs = load(ROOT / "test-results/evidence-run-inputs.json")
    fault_model = load(HTML / "assurance-fault-model-facts.json")

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
        "(test-plan-mutation-policy)=",
        "Evidence freshness",
        "relevant inputs current",
        "Implementation fault detection",
        "every valid mutant caught",
        "Mutation signal",
        "surviving mutant on a changed line",
        "`impl.effect`",
        "`impl.arithmetic`",
        "##### Mutant outcomes",
        "##### Arid code",
        "##### Validity",
        "##### Suppression",
        "##### Cadence and signal",
        "##### Semantic mutants",
        "impl.comparison",
        "interface.unexpected-interaction",
        "spec.wrong-outcome",
        "required coverage = **100%**",
        "required deterministic fault detection = **100%**",
    )), "project Test Plan keeps only llm-router-specific decisions and reusable domain models")
    for retired_token in ("mutmut", "Mutation Reach", "Mutation Sensitivity", "Test Strength", "≥ 80%"):
        check(retired_token not in test_plan_source,
              f"project Test Plan carries no retired mutation score or engine: {retired_token}")
    # The retired floors were percentages among the project decisions; a percentage elsewhere (the
    # generation budget's window limits) is not a mutation score.
    project_decisions = test_plan_source.split("## Project decisions", 1)[1].split("\n## ", 1)[0]
    check("%" not in project_decisions,
          "the Test Plan's project decisions set no percentage floor: no mutation score gates a contract or the project")
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
    )) and "### Blocking mutation checks" not in verification_profile_source,
    "Invalid Configuration profile splits the parent public rejection claim from all thirteen first-class Technical requirements and selects no mutation threshold")
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
    required_choice = tool_choice_actual.get("VC_TOOL_CHOICE_REQUIRED") or []
    replay_choice = tool_choice_actual.get("VC_TOOL_CHOICE_REPLAY_FAMILIES") or []
    local_choice = tool_choice_actual.get("VC_TOOL_CHOICE_GOOGLE_GENAI") or []
    check(
        tool_choice_targets.get(("component", "none"), {}).get("item_path_counts")
            == {
                "VC_TOOL_CHOICE_NAMED_INPUT_FORMS": 2,
                "VC_TOOL_CHOICE_NAMED_SERIALIZERS": 4,
                "VC_TOOL_CHOICE_REQUIRED": 5,
            }
        and tool_choice_targets.get(("system_integration", "replay"), {}).get("item_path_counts")
            == {"VC_TOOL_CHOICE_REPLAY_FAMILIES": 4}
        and tool_choice_targets.get(("system_integration", "substitute"), {}).get("item_path_counts")
            == {"VC_TOOL_CHOICE_GOOGLE_GENAI": 1}
        and len(named_forms) == 2
        and len(named_serializers) == 4
        and len(required_choice) == 5
        and len(replay_choice) == 4
        and len(local_choice) == 1,
        "Tool Choice preserves independent public-input, provider-serializer, required-call and provider-family denominators without last-test-wins collapse",
    )
    check(
        all(
            row.get("result") == "passed"
            and row.get("level") == "component"
            and row.get("boundary") == "none"
            and row.get("representation") == "actual"
            for row in [*named_forms, *named_serializers, *required_choice]
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
        "`.ai-bridge/assurance-targets.json` is retired (ADR_0003)",
        "Test Coverage → Fault-based Testing → History",
    )), "monitor readiness ledger records the completed P34 target/actual cutover and first-class Configuration ownership")
    check("Test plan" in test_plan_html and "Reusable Test Models" in test_plan_html,
          "generated Test Plan page renders the project-wide strategy")

    check_mutation_system(monitor_facts)

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
        and "def support_summary(" in ui_source
        and "def technical_support_card(" not in ui_source
        and "def domain_card(" in ui_source
        and "def history_section(" in ui_source
        and "def inspector_head(" in ui_source
        and "def signal_group(" in ui_source
        and "def confidence_subgroup(" in ui_source
        and "def drilldowns(" in ui_source
        and "def section_head(" in ui_source
        and "def verdict_header(" in ui_source
        and "def support_panel(" not in ui_source
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
            and "technical-support-panel" in page
            and "technical-support-card" not in page
            and "kind=support" in page
            for page in upper_assurance_pages.values()
        ),
        "upper child-support sections count how many of their children pass and leave the children to the explorer",
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
        # The fallback that succeeds and, since revision 2, the request whose every route fails.
        "REQ_SYNC_ROUTE_FALLBACK": {
            "interface.error-status": (2, 2),
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
            "impl.effect",
            "spec.wrong-outcome",
            "spec.missing-partition",
            "spec.wrong-ordering-boundary",
        },
        "REQ_SESSION_PERSISTENCE": {
            "impl.control-flow",
            "impl.effect",
            "spec.wrong-outcome",
            "spec.missing-partition",
        },
        "TREQ_SESSION_SERIALIZATION": {
            "impl.comparison",
            "impl.boundary",
            "impl.control-flow",
            "impl.effect",
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
        "Checks that small code mistakes—a wrong comparison, limit, branch or return, a lost call, write or raise—are caught.",
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
    invalid_implementation = next(
        (
            load_domain().fault_state(contract_monitor, group, monitor_facts.get("policy") or {})
            for group in contract_monitor["target"]["fault_groups"]
            if group["label"] == "Implementation"
        ),
        {},
    )
    tally = invalid_implementation.get("mutants") or {}
    check(
        bool(tally)
        and all(label in assurance_page for label in ("Fault classes", "Required", "Challenged", "Detected", "Mutants", "Caught", "Survived", "Not reached"))
        and "Mutation checks" not in assurance_page
        and "sensitivity" not in assurance_page.lower().split("<main", 1)[-1]
        and "Generated" not in assurance_page,
        "canonical Fault model counts the mutants behind its classes by outcome (caught, survived, not reached) and carries no mutation score",
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
        and 'href="verification-explorer.html#contract=REQ_INVALID_CONFIGURATION_ERRORS&amp;change=any">Changes ↗</a>'
        in assurance_page
        and 'href="assurance-snapshots.json"' not in assurance_page,
        "canonical History stays compact and routes to what changed since the previous retained run in the explorer",
    )
    check(
        "Assurance is not pass/fail" not in assurance_page
        and "tf-gap-hero" not in assurance_page
        and "tf-path-group-grid" not in assurance_page
        and "tf-trust-item" not in assurance_page,
        "canonical monitor contains no superseded prose/dashboard sections",
    )

    check(fault_model.get("schema_version") == "ternforge-specialized-fault-probes-1"
          and set(fault_model.get("contracts") or {}) == {"REQ_INVALID_CONFIGURATION_ERRORS"}
          and "layers" not in fault_model and "history" not in fault_model,
          "the retained fault probe facts hold only the specialized probes of REQ_INVALID_CONFIGURATION_ERRORS; the P31 ladder, mutation groups and trend history are retired")
    invalid_config_faults = (fault_model.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    check("groups" not in invalid_config_faults and "detection_overlap" not in invalid_config_faults and "history" not in invalid_config_faults,
          "the specialized probe facts carry no mutation Reach/Sensitivity groups, mutmut overlap or DVC history")
    check(((contract_monitor.get("fault_actual") or {}).get("specialized_probe_current")) is True,
          "the specialized probes are bound to the current contract, profile, sources and tests, so their classes count")
    # A mutation pin (ADR_0006) pins one mutant: it verifies its contract but is no evidence of depth.
    depth_tests = [row for row in depth_facts.get("tests") or [] if not str(row.get("nodeid") or "").startswith("tests/llm_router/mutation_pins/")]
    rate_tests = [
        row
        for row in depth_tests
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
        "Rate-limit state remains backed by current Component×Local×Actual execution paths",
    )

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
        for row in depth_tests
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
        "Async provider execution currently has no Direct-live contract path; its profile does not claim one",
    )
    req_layers = invalid_config_faults.get("layers") or {}
    check(set(req_layers) == {"specification", "architecture", "interface", "runtime"} and
          all(int(row.get("detected") or 0) > 0 for row in req_layers.values()),
          "REQ_INVALID_CONFIGURATION_ERRORS keeps real, caught specialized probes for its specification, architecture, interface and runtime classes; implementation faults are the campaign's")
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
    for layer_id, required_fields in {
        "specification": ("claim_section", "mutation", "parser_validity", "execution_command", "detector", "source_url", "test_source_url"),
        "architecture": ("declared_rule", "baseline_summary", "injected_violation", "execution_command", "detector", "source_url"),
        "interface": ("dependency", "expected_interaction", "observed_interaction", "expected_public_error", "public_error", "detector", "source_url"),
        "runtime": ("dependency", "injected_fault", "expected_invariant", "observed_behavior", "detector", "source_url"),
    }.items():
        check(all(req_layers[layer_id].get(field) not in (None, "", []) for field in required_fields),
              f"{layer_id} fault detail retains all promised claim/challenge/detector/drill-down fields")

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
    check(
        'href="mutation-analysis.html"' not in health_page.split('<main id="main-content"', 1)[0]
        and not (HTML / "mutation-analysis.html").exists(),
        "Mutation Analysis is retired: the navigation carries no item and the build leaves no page (ADR_0003)",
    )
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
            # A mutation pin (ADR_0006) is bound by the mutant it pins, not by a coverage case.
            unbound_count += 0 if owner or binding.get("fault_challenge") or nodeid.startswith("tests/llm_router/mutation_pins/") else 1
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
        and class_map.get("arithmetic") == "impl.arithmetic"
        and class_map.get("boolean") == "impl.control-flow"
        and class_map.get("return") == "impl.control-flow"
        and class_map.get("statement") == "impl.effect"
        and class_map.get("body") == "impl.effect",
        "Implementation fault campaign is retained and maps its operator families onto all five Implementation classes",
    )
    full_pytest_plugin = BRIDGE / "pytest_plugins/gremlins_full_pytest.py"
    faults_source = (BRIDGE / "implementation_faults.py").read_text()
    check(
        full_pytest_plugin.exists()
        and "build_lightweight_command = _no_lightweight_runner" in full_pytest_plugin.read_text()
        and '"-p", "gremlins_full_pytest"' in faults_source
        and "IMPL_FAULTS.run_engine" in adapter_source
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
        "fault-class-row" not in primary_monitor_page
        and "Not caught:" not in primary_monitor_page
        and "is also claimed by" not in primary_monitor_page
        and "technical-support-card" not in primary_monitor_page
        and "mutation-analysis.html" not in primary_monitor_page
        and "fault-chain" in primary_monitor_page
        and "layer=faults&amp;group=Implementation" in primary_monitor_page,
        "the fault inspector counts required, challenged and detected classes and routes to the explorer, which lists "
        "each class with its reason and surviving mutants; the monitor carries no class list, prose or Mutation Analysis link",
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
    explorer_page_text = (HTML / "verification-explorer.html").read_text()
    # The theme renders the navigation twice (header and mobile sidebar): the Verification Explorer follows the Health
    # Map and Mutation Analysis follows the explorer in both, on the map's page and on the explorer's. The theme
    # separates items with two blank lines and an inserted item brings one more; a longer run of blank lines means a
    # patch landed on top of an earlier one.
    nav_run = r">\s*Verification Health Map\s*</a>\s*</li>\s*<li[^>]*>\s*<a[^>]*>\s*Verification Explorer\s*</a>"
    check(
        all(
            len(re.findall(r">\s*Verification Health Map\s*</a>", nav)) == len(re.findall(nav_run, nav)) > 0
            for nav in (health_nav, explorer_page_text.split('<main id="main-content"', 1)[0])
        )
        and "Mutation Analysis" not in health_nav
        and "Mutation Analysis" not in explorer_page_text.split('<main id="main-content"', 1)[0]
        and "Verification Depth Map" not in health_nav
        and all(
            "\n" * 5 not in page.split('<main id="main-content"', 1)[0]
            for page in (health_page, index_page, explorer_page_text)
        ),
        "the Health Map and the Verification Explorer are listed once in each portal navigation, the explorer right after "
        "the map, and neither Mutation Analysis nor a Depth Map; patching an already patched navigation adds nothing",
    )
    check_verification_explorer(map_pages_module)
    check_model_roles_page()
    qualification_harness_source = (BRIDGE / "qualify-evidence-confidence.py").read_text()
    check(
        "'<section id=\"verification-health-map\">\\n<h1>Verification Health Map'" in map_pages_module
        and "f'<style id=\"tf-health-map-style\">\\n{css}\\n</style>\\n'" in map_pages_module
        and re.findall(r"^def (\w+)\(", map_pages_module, flags=re.MULTILINE)
        == ["map_tools", "map_panel", "map_find", "map_frame", "map_strip", "health_map_article", "explorer_article", "_palette", "model_roles_article"]
        and "verification-depth-map" not in map_pages_module
        and '<section id="verification-health-map">' not in health_builder_source
        and "MAP_PAGES.health_map_article(" in health_builder_source
        and "MAP_PAGES.explorer_article(" in health_builder_source
        and "MAP_PAGES.model_roles_article(" in health_builder_source
        and health_builder_source.count("MAP_PAGES.") == 3
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
    layers_block = re.search(r"const MAP_HEALTH_LAYERS=\[(.*?)\];", health_page, flags=re.DOTALL)
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
          "old custom Assurance Target/Profile registry is retired (ADR_0003)" in manifest
          and "Mutation strategy: ADR_0003" in manifest
          and "mutmut" not in manifest.split("## Premature platform spike cleanup", 1)[0].replace("mutmut, its Test Strength score", ""),
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
        "build-mutation-report-prototype.py",
        "semantic_mutants.py",
        "model_generation.py",
        "survivor_equivalence.py",
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
        "verification-explorer-local-prototype.md",
    }
    actual_bridge_files = {path.name for path in BRIDGE.iterdir() if path.is_file()}
    check(actual_bridge_files == expected_bridge_files,
          f"only substantive active-pilot .ai-bridge files remain: {sorted(actual_bridge_files)}")
    check(
        not (BRIDGE / "__pycache__").exists() and not (BRIDGE / "pytest_plugins/__pycache__").exists(),
        "no .ai-bridge __pycache__ debris remains",
    )

    generated_paths = [
        "docs/_build/html/mutation-report.html",
        "docs/_build/html/mutation-report.json",
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/verification-assurance.html",
        "docs/_build/html/contract-evidence-request-override-precedence.html",
        "docs/_build/html/contract-evidence-credential-resolution.html",
        "docs/_build/html/contract-evidence-config-installation-coherence.html",
        "docs/_build/html/assurance-fault-model-facts.json",
        "docs/_build/html/favicon.ico",
        "docs/_build/html/verification-health-map.html",
        "docs/_build/html/test-plan.html",
        "docs/_build/html/_static/mutation-test-elements.js",
        "docs/_build/html/evidence-classification-facts.json",
        "test-results/implementation-faults/campaign.json",
        "test-results/implementation-faults/diff/summary.json",
        "test-results/implementation-faults/diff/annotations.txt",
        "test-results/implementation-faults/diff/summary.md",
    ]
    generated_paths += [
        str(path.relative_to(ROOT))
        for path in (ROOT / "test-results/health-map/runs").glob("*.json")
    ]
    generated_paths += [
        str(path.relative_to(ROOT))
        for path in (ROOT / "test-results/implementation-faults").glob("*.gremlins.json")
    ]
    contract_evidence_glob = "`docs/_build/html/contract-evidence-*.html`"
    health_run_glob = "`test-results/health-map/runs/*.json`"
    gremlins_glob = "`test-results/implementation-faults/*.gremlins.json`"
    missing_artifacts = sorted(
        path
        for path in generated_paths
        if f"`{path}`" not in manifest
        and not (
            path.startswith("test-results/implementation-faults/")
            and path.endswith(".gremlins.json")
            and gremlins_glob in manifest
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

    check(not (ROOT / "mutants").exists(), "no leftover mutmut workspace")
    setup = ROOT / "setup.cfg"
    check(not setup.exists() or "[mutmut]" not in setup.read_text(), "no leftover mutmut setup config")
    check(not (ROOT / "coverage").exists(), "no leftover engine report directory in the repository root")

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
        # Retired with mutmut and the P31 assurance model (ADR_0003): deleted, not replaced.
        ".ai-bridge/assurance-targets.json",
        ".ai-bridge/assurance-snapshots.json",
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
        ".ai-bridge/verification-explorer-local-prototype.md",
        ".ai-bridge/implementation_faults.py",
        ".ai-bridge/semantic_mutants.py",
        ".ai-bridge/model_generation.py",
        ".ai-bridge/survivor_equivalence.py",
        ".ai-bridge/survivor-triage/",
        ".ai-bridge/survivor-verdicts/",
        ".ai-bridge/semantic-mutants/",
        ".ai-bridge/pytest_plugins/",
        ".ai-bridge/vendor/",
        ".ai-bridge/development-history/",
        ".ai-bridge/exemplars/",
        "docs/index.md",
        "docs/README.md",
        "docs/decisions/index.md",
        "docs/decisions/0003-mutation-testing-strategy.md",
        "docs/decisions/0004-metered-model-generation.md",
        "docs/decisions/0005-survivor-judgement.md",
        "docs/decisions/0006-survivor-verdicts.md",
        "docs/test-plan.md",
        "docs/verification-health-map.md",
        "docs/verification-explorer.md",
        "docs/model-roles.md",
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
        # Its @impl link follows REQ_TOOL_CHOICE to revision 2, the owner's decision (history 046).
        "src/llm_router/_internal/capabilities/tools.py",
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
        "tests/llm_router/mutation_pins/",
        ".flake8",
        "typos.toml",
        ".pre-commit-config.yaml",
        ".github/workflows/mutation-pilot.yml",
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
        # A person's test for the owner's decision on REQ_SYNC_ROUTE_FALLBACK 80df5312: a failed attempt is
        # recorded for its provider and key (TREQ_RATE_LIMIT_STATE revision 2, history 049).
        "tests/llm_router/unit/test_internal_sync_failure_recording.py",
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
