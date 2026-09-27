from __future__ import annotations

import argparse
import binascii
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from html import escape as html_escape
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from coverage import CoverageData

ROOT=Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
DEPTH_FACTS_PATH=ROOT/"docs/_build/html/verification-depth-facts.json"
# A fresh checkout (the pull-request run) has no depth facts yet: the portal refresh writes them.
DEPTH: dict[str, Any]=json.loads(DEPTH_FACTS_PATH.read_text()) if DEPTH_FACTS_PATH.exists() else {"tests":[]}
TEST_META: dict[str, dict[str, Any]]={r["nodeid"]:r for r in DEPTH["tests"]}
COVERAGE_DB=ROOT/"test-results/.coverage"
COVERAGE_JSON_PATH=ROOT/"test-results/coverage.json"
JUNIT_PATH=ROOT/"test-results/pytest-junit.xml"
ALLURE_RESULTS_DIR=ROOT/"test-results/allure-results"
EVIDENCE_RUN_PROVENANCE_PATH=ROOT/"docs/_build/html/evidence-run-provenance.json"
EVIDENCE_RUN_INPUTS_PATH=ROOT/"test-results/evidence-run-inputs.json"
EVIDENCE_QUALIFICATION_PATH=ROOT/"docs/_build/html/evidence-confidence-qualification.json"
ASSURANCE_FACTS_PATH=ROOT/"docs/_build/html/assurance-fault-model-facts.json"
HEALTH_PAGE=ROOT/"docs/_build/html/verification-health-map.html"
EXPLORER_PAGE=ROOT/"docs/_build/html/verification-explorer.html"
# The Verification Depth Map and the Verification Map prototype became the Verification Health Map (MAP-P41).
RETIRED_MAP_PAGES=(ROOT/"docs/_build/html/verification-depth-map.html",ROOT/"docs/_build/html/verification-map.html")
REQ_MONITOR_FACTS_PATH=ROOT/"docs/_build/html/requirement-monitor-facts.json"
UPPER_ASSURANCE_FACTS_PATH=ROOT/"docs/_build/html/upper-assurance-facts.json"
EVIDENCE_CLASSIFICATION_PATH=ROOT/"docs/_build/html/evidence-classification-facts.json"
ALLURE_REPORT_PAGE=ROOT/"docs/_build/html/test-results/index.html"
MUTATION_REPORT_PAGE=ROOT/"docs/_build/html/mutation-report.html"
ASSURANCE_PAGE=ROOT/"docs/_build/html/verification-assurance.html"
MTE_VENDOR_PATH=ROOT/".ai-bridge/vendor/mutation-testing-elements-3.9.0/mutation-test-elements.js.gz"
MTE_VENDOR_SHA256="751fb010242b0b44e32d84fe7fe0b9ff1da182823b94f59f5c52b001fcfc163b"
D3_HIERARCHY_VENDOR_PATH=ROOT/".ai-bridge/vendor/d3-hierarchy-3.1.2/d3-hierarchy.min.js"
D3_HIERARCHY_VENDOR_SHA256="a8771380454be89ec5ffe9a6396ba7c247081e348ae740dc9cb9629abd4c0e43"

ASSURANCE_DOMAIN_SPEC=importlib.util.spec_from_file_location(
  "health_map_assurance_domain",ROOT/".ai-bridge/assurance_monitor_domain.py"
)
if ASSURANCE_DOMAIN_SPEC is None or ASSURANCE_DOMAIN_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor domain helpers")
ASSURANCE_DOMAIN=importlib.util.module_from_spec(ASSURANCE_DOMAIN_SPEC)
ASSURANCE_DOMAIN_SPEC.loader.exec_module(ASSURANCE_DOMAIN)

ASSURANCE_REGISTRY_SPEC=importlib.util.spec_from_file_location(
  "health_map_assurance_registry",ROOT/".ai-bridge/assurance_monitor_registry.py"
)
if ASSURANCE_REGISTRY_SPEC is None or ASSURANCE_REGISTRY_SPEC.loader is None:
    raise RuntimeError("Could not load assurance monitor registry")
ASSURANCE_REGISTRY=importlib.util.module_from_spec(ASSURANCE_REGISTRY_SPEC)
ASSURANCE_REGISTRY_SPEC.loader.exec_module(ASSURANCE_REGISTRY)

IMPL_FAULTS_SPEC=importlib.util.spec_from_file_location(
  "implementation_faults",ROOT/".ai-bridge/implementation_faults.py"
)
if IMPL_FAULTS_SPEC is None or IMPL_FAULTS_SPEC.loader is None:
    raise RuntimeError("Could not load implementation fault helpers")
IMPL_FAULTS=importlib.util.module_from_spec(IMPL_FAULTS_SPEC)
IMPL_FAULTS_SPEC.loader.exec_module(IMPL_FAULTS)
# The engine extension implements the Test Plan's arid-code rules; the policy must name exactly those.
MUTATION_EXTENSION_SPEC=importlib.util.spec_from_file_location(
  "ternforge_mutation",ROOT/".ai-bridge/pytest_plugins/ternforge_mutation.py"
)
if MUTATION_EXTENSION_SPEC is None or MUTATION_EXTENSION_SPEC.loader is None:
    raise RuntimeError("Could not load the mutation engine extension")
MUTATION_EXTENSION=importlib.util.module_from_spec(MUTATION_EXTENSION_SPEC)
# Its dataclasses resolve their annotations through sys.modules.
sys.modules.setdefault("ternforge_mutation",MUTATION_EXTENSION)
MUTATION_EXTENSION_SPEC.loader.exec_module(MUTATION_EXTENSION)
# The semantic mutant cascade: frozen proposals for a named risk, judged without a model.
SEMANTIC_SPEC=importlib.util.spec_from_file_location("semantic_mutants",ROOT/".ai-bridge/semantic_mutants.py")
if SEMANTIC_SPEC is None or SEMANTIC_SPEC.loader is None:
    raise RuntimeError("Could not load the semantic mutant cascade")
SEMANTIC=importlib.util.module_from_spec(SEMANTIC_SPEC)
sys.modules.setdefault("semantic_mutants",SEMANTIC)
SEMANTIC_SPEC.loader.exec_module(SEMANTIC)
SEMANTIC_RESULTS_DIR=ROOT/"test-results/semantic-mutants"
SEMANTIC_PRODUCERS=("PRODUCER_SEMANTIC_MUTANT_CASCADE",)
# The metered adapter every model call goes through (ADR_0004); only an explicit generation run uses it.
MODELS_SPEC=importlib.util.spec_from_file_location("model_generation",ROOT/".ai-bridge/model_generation.py")
if MODELS_SPEC is None or MODELS_SPEC.loader is None:
    raise RuntimeError("Could not load the model generation adapter")
MODELS=importlib.util.module_from_spec(MODELS_SPEC)
sys.modules.setdefault("model_generation",MODELS)
MODELS_SPEC.loader.exec_module(MODELS)
MODEL_PRODUCERS=("PRODUCER_MODEL_GENERATION_ADAPTER",)
# The survivor judgement (ADR_0005): symbolic search, confirmed witnesses, calibrated assessors.
EQ_SPEC=importlib.util.spec_from_file_location("survivor_equivalence",ROOT/".ai-bridge/survivor_equivalence.py")
if EQ_SPEC is None or EQ_SPEC.loader is None:
    raise RuntimeError("Could not load the survivor judgement")
EQ=importlib.util.module_from_spec(EQ_SPEC)
sys.modules.setdefault("survivor_equivalence",EQ)
EQ_SPEC.loader.exec_module(EQ)
SYMBOLIC_PRODUCERS=("PRODUCER_SYMBOLIC_DIFFERENTIAL",)
ASSESSOR_PRODUCERS=("PRODUCER_ASSESSOR_ENSEMBLE",)
ASSESSOR_CALIBRATION_DIR=SEMANTIC.PROPOSAL_ROOT/"assessor-calibration"
EQUIVALENCE_PAIRS_DIR=SEMANTIC.PROPOSAL_ROOT/"calibration"/"equivalence"
TRIAGE_ANSWERS_DIR=ROOT/".ai-bridge/survivor-triage"
TRIAGE_RESULTS_DIR=ROOT/"test-results/survivor-triage"
# Symbolic results of every survivor, semantic or rule, by what they depend on (both modules, the
# harness, CrossHair and its bounds); a found input is confirmed by execution again on every use.
SYMBOLIC_CACHE_PATH=ROOT/"test-results/survivor-judgement/symbolic-cache.json"
CROSSHAIR_REQUIREMENT=f"crosshair-tool=={EQ.CROSSHAIR_VERSION}"
# Page markup lives in its own module, outside the qualification fingerprint (see its docstring).
MAP_PAGES_SPEC=importlib.util.spec_from_file_location(
  "assurance_map_pages",ROOT/".ai-bridge/assurance_map_pages.py"
)
if MAP_PAGES_SPEC is None or MAP_PAGES_SPEC.loader is None:
    raise RuntimeError("Could not load the map page templates")
MAP_PAGES=importlib.util.module_from_spec(MAP_PAGES_SPEC)
MAP_PAGES_SPEC.loader.exec_module(MAP_PAGES)
IMPL_FAULT_DIR=ROOT/"test-results/implementation-faults"
IMPL_FAULT_CAMPAIGN_PATH=IMPL_FAULT_DIR/"campaign.json"


def utc_now():
    return datetime.now(UTC).isoformat().replace("+00:00","Z")

def stable_json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha256_text(value):
    return sha256_bytes(value.encode())

def sha256_file(path):
    return sha256_bytes(path.read_bytes()) if path.exists() else None

def git_sha(ref="HEAD"):
    return subprocess.check_output(["git","rev-parse",ref],cwd=ROOT,text=True).strip()

def repo_blob_url(path,ref=None):
    return f"https://github.com/betabitplus/llm-router/blob/{ref or git_sha()}/{path}"


# TERNFORGE-P34-CLEAN-MAPS-START
NORMATIVE_MAP_TYPES = {"goal", "feature", "req", "treq"}


def assurance_map_graph():
    needs = current_needs()
    nodes = {
        need_id: need
        for need_id, need in needs.items()
        if str(need.get("type") or "").lower() in NORMATIVE_MAP_TYPES
    }
    parent = {}
    children = defaultdict(list)
    for need_id, need in nodes.items():
        for candidate in need.get("derives") or []:
            if candidate in nodes:
                parent[need_id] = candidate
                children[candidate].append(need_id)
                break
    roots = [need_id for need_id in nodes if need_id not in parent]

    ordered = []
    seen = set()

    def visit(need_id):
        if need_id in seen:
            return
        seen.add(need_id)
        ordered.append(need_id)
        for child_id in children.get(need_id) or []:
            visit(child_id)

    for need_id in roots:
        visit(need_id)
    for need_id in nodes:
        visit(need_id)

    descendants = {}

    def collect(need_id):
        result = {need_id}
        for child_id in children.get(need_id) or []:
            result.update(collect(child_id))
        return result

    for need_id in ordered:
        descendants[need_id] = collect(need_id)

    return needs, nodes, parent, children, ordered, descendants


def map_test_rows(needs):
    rows = []
    for need in needs.values():
        if need.get("type") != "testcase" or not need.get("nodeid"):
            continue
        verifies = []
        for value in need.get("verifies") or []:
            verifies.extend(re.findall(r"T?REQ_[A-Z0-9_]+", str(value)))
        rows.append({
            "nodeid": str(need.get("nodeid") or ""),
            "title": str(need.get("title") or need.get("case_name") or need.get("nodeid") or ""),
            "result": str(need.get("result") or "unknown").lower(),
            "verification_kind": str(need.get("verification_kind") or "unknown").lower(),
            "verifies": list(dict.fromkeys(verifies)),
        })
    return rows


def map_contract_test_index(test_rows):
    index = defaultdict(list)
    for row in test_rows:
        for contract_id in row.get("verifies") or []:
            index[contract_id].append(row)
    return index


def map_rows_for_scope(scope_ids, direct_index):
    seen = set()
    rows = []
    for contract_id in scope_ids:
        for row in direct_index.get(contract_id) or []:
            nodeid = row.get("nodeid")
            if nodeid in seen:
                continue
            seen.add(nodeid)
            rows.append(row)
    return rows


def portal_map_shell(shell_path, title, article_html):
    if not shell_path.exists():
        raise RuntimeError(
            f"clean map generation requires the native Sphinx shell at {shell_path.relative_to(ROOT)}"
        )
    text = shell_path.read_text()
    text = re.sub(
        r"<title>.*?( &#8212; .*?</title>)",
        lambda match: f"<title>{html_escape(title)}{match.group(1)}",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'(<li class="breadcrumb-item active" aria-current="page"><span class="ellipsis">).*?(</span></li>)',
        lambda match: match.group(1) + html_escape(title) + match.group(2),
        text,
        count=1,
        flags=re.DOTALL,
    )
    focus_layout = """<style id="tf-map-focus-layout">
.bd-page-width{max-width:100%}
.bd-main .bd-content .bd-article-container{max-width:100%}
@media (max-width:959.98px){
  #pst-primary-sidebar.pst-squeeze{width:75%;overflow:auto}
  #pst-primary-sidebar.pst-squeeze .sidebar-primary-item:not(.pst-sidebar-collapse){
    opacity:1;
    visibility:visible;
  }
}
</style>"""
    text = text.replace(
        'id="pst-primary-sidebar" class="bd-sidebar-primary bd-sidebar"',
        'id="pst-primary-sidebar" class="bd-sidebar-primary bd-sidebar pst-squeeze"',
        1,
    )
    text = text.replace(
        'id="pst-collapse-sidebar-button" aria-expanded="true"',
        'id="pst-collapse-sidebar-button" aria-expanded="false"',
        1,
    )
    # Re-rendering an already generated page must not accumulate shell patches.
    text = re.sub(r'<style id="tf-map-focus-layout">.*?</style>\n?', "", text, flags=re.DOTALL)
    text = text.replace("</head>", focus_layout + "\n</head>", 1)
    # A callable replacement keeps backslashes in inlined scripts and JSON literal.
    text, count = re.subn(
        r'<article class="bd-article">.*?</article>',
        lambda _match: '<article class="bd-article">' + article_html + "</article>",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError(f"could not replace native map article for {title}")
    return text


def health_layer_status(status):
    value=str(status or "UNKNOWN").upper().replace("_"," ")
    if value in {"MET","PASSED","PASS"}:
        return "passed"
    if value in {"N/A","NA"}:
        return "na"
    return "failed"


def health_metric(label, statuses):
    normalized=[status for status in statuses if health_layer_status(status)!="na"]
    return {
      "label":label,
      "passed":sum(health_layer_status(status)=="passed" for status in normalized),
      "total":len(normalized),
    }


def merge_health_metrics(results):
    merged={}
    order=[]
    for result in results:
        for metric in result.get("metrics") or []:
            label=metric["label"]
            if label not in merged:
                merged[label]={"label":label,"passed":0,"total":0}
                order.append(label)
            merged[label]["passed"]+=int(metric.get("passed") or 0)
            merged[label]["total"]+=int(metric.get("total") or 0)
    return [merged[label] for label in order if merged[label]["total"]]


def health_layer_result(statuses, *, href, label, detail="", applicable=True, metrics=None):
    metrics=list(metrics or [])
    if not applicable:
        return {"status":"na","label":label,"detail":detail,"href":href,"passed":0,"total":0,"metrics":[]}
    normalized=[status for status in statuses if health_layer_status(status)!="na"]
    passed=sum(health_layer_status(status)=="passed" for status in normalized)
    total=len(normalized)
    status="passed" if total and passed==total else "failed"
    return {
      "status":status,
      "label":label,
      "detail":detail or f"{passed}/{total} checks pass",
      "href":href,
      "passed":passed,
      "total":total,
      "metrics":metrics,
    }


def upper_section_anchor(entity_id, key):
    return f"ua-{entity_id.lower().replace('_','-')}-{key.replace('_','-')}"


def junit_test_bindings():
    """Map each retained testcase to the verification criterion it was written for."""
    if not JUNIT_PATH.exists():
        return {}
    bindings={}
    for testcase in ET.parse(JUNIT_PATH).getroot().iter("testcase"):
        props={
          prop.attrib.get("name"):prop.attrib.get("value")
          for prop in testcase.findall("./properties/property")
        }
        nodeid=f"{(testcase.attrib.get('classname') or '').replace('.','/')}.py::{testcase.attrib.get('name') or ''}"
        bindings[nodeid]={
          "coverage_item":(props.get("coverage_item") or "").strip(),
          "assurance_item":(props.get("assurance_item") or "").strip(),
          "fault_challenge":bool((props.get("fault_items") or "").strip()),
        }
    return bindings


def health_map_payload():
    needs,nodes,parent,_children,ordered,descendants=assurance_map_graph()
    tests=map_test_rows(needs)
    direct_tests=map_contract_test_index(tests)
    req_facts=json.loads(REQ_MONITOR_FACTS_PATH.read_text())
    upper_facts=json.loads(UPPER_ASSURANCE_FACTS_PATH.read_text())
    contracts=req_facts.get("contracts") or {}
    policy=req_facts.get("policy") or {}
    contract_ids=set(contracts)
    monitor_urls=ASSURANCE_REGISTRY.monitor_urls(contract_ids)

    # A test result belongs to the criterion it was written for. Goal/capability
    # scenarios also `verify` Requirements for traceability, but their results are
    # owned (and shown) by the goal or capability, not repeated on every Requirement.
    criterion_owner={
      criterion_id:owner
      for contract in contracts.values()
      for criterion_id,owner in ((contract.get("target") or {}).get("criterion_contracts") or {}).items()
    }
    bindings=junit_test_bindings()
    owned_tests=defaultdict(list)
    unbound_tests=defaultdict(int)
    for contract_id,rows in direct_tests.items():
        for row in rows:
            binding=bindings.get(row.get("nodeid")) or {}
            if binding.get("assurance_item"):
                continue
            owner=criterion_owner.get(binding.get("coverage_item") or "")
            if owner and owner!=contract_id:
                continue
            owned_tests[contract_id].append(row)
            # A mutation pin pins a fault, not a coverage case (ADR_0006): it is bound by what it pins.
            if not owner and not binding.get("fault_challenge") and not is_mutation_pin(row.get("nodeid")):
                unbound_tests[contract_id]+=1

    contract_layers={}
    contract_direct={}
    for contract_id,contract in contracts.items():
        cells=[
          ASSURANCE_DOMAIN.cell_state(contract,target)
          for target in (contract.get("target") or {}).get("coverage",[])
        ]
        faults=[
          ASSURANCE_DOMAIN.fault_state(contract,group,policy)
          for group in (contract.get("target") or {}).get("fault_groups",[])
        ]
        direct_state=ASSURANCE_DOMAIN.contract_domain_state(contract,policy)
        contract_direct[contract_id]=direct_state
        base=monitor_urls.get(contract_id) or ""
        coverage_href=base+f"#ce-coverage-{contract_id.lower()}"
        fault_href=base+f"#ce-faults-{contract_id.lower()}"
        coverage_statuses=[cell["semantic_status"] for cell in cells]
        linked_state=ASSURANCE_DOMAIN.linked_tests_state(contract)
        if linked_state["failed"]:
            coverage_statuses.append(linked_state["status"])
        # Evidence quality judges retained evidence only; a target with no retained
        # evidence at all is a coverage gap, not untrustworthy evidence.
        judged=[cell for cell in cells if cell["retained_count"]]
        evidence_parts={
          "Representation":[cell["representation_status"] for cell in judged if cell["representation_status"]!="N/A"],
          "Provenance":[cell["provenance_status"] for cell in judged if cell["provenance_status"]!="N/A"],
          "Producers":[cell["producer_status"] for cell in judged if cell["producer_status"]!="N/A"],
          "Freshness":[cell["freshness_status"] for cell in judged if cell["freshness_status"]!="N/A"],
          "M&S":[cell["ms_status"] for cell in judged if cell["ms_status"]!="N/A"],
        }
        evidence_statuses=[status for statuses in evidence_parts.values() for status in statuses]
        fault_statuses=[fault["status"] for fault in faults if fault["status"]!="N/A"]
        contract_layers[contract_id]={
          "coverage":health_layer_result(
            coverage_statuses,
            href=coverage_href,
            label="Coverage",
            metrics=[health_metric("Targets",coverage_statuses)],
          ),
          "faults":health_layer_result(
            fault_statuses,
            href=fault_href,
            label="Faults",
            applicable=bool(fault_statuses),
            metrics=[health_metric("Fault groups",fault_statuses)],
          ),
          "evidence":health_layer_result(
            evidence_statuses,
            href=coverage_href,
            label="Evidence",
            applicable=bool(evidence_statuses),
            metrics=[health_metric(label,statuses) for label,statuses in evidence_parts.items() if statuses],
          ),
        }

    def effective_contract_overall(contract_id):
        direct=contract_direct.get(contract_id,{}).get("overall","UNKNOWN")
        required_treqs=list(((contracts.get(contract_id) or {}).get("target") or {}).get("required_treqs") or [])
        if not required_treqs:
            return direct
        child=[contract_direct.get(child_id,{}).get("overall","UNKNOWN") for child_id in required_treqs]
        return ASSURANCE_DOMAIN.combine([direct,*child])

    upper_by_id={}
    for entity in (upper_facts.get("features") or {}).values():
        upper_by_id[entity["id"]]=entity
    for entity in (upper_facts.get("goals") or {}).values():
        upper_by_id[entity["id"]]=entity
    product=upper_facts.get("product_system") or {}
    if product:
        upper_by_id["__PRODUCT_INTENT__"]=product

    def upper_direct_checks(entity_id, signal):
        entity=upper_by_id.get(entity_id) or {}
        if entity_id=="__PRODUCT_INTENT__":
            keys=("cross_goal_integration","operational_validation")
        elif entity_id.startswith("GOAL_"):
            keys=("cross_capability_integration","outcome_validation")
        elif entity_id.startswith("FEAT_"):
            keys=("capability_integration","capability_validation")
        else:
            return []
        checks=[]
        page_id="PRODUCT_SYSTEM" if entity_id=="__PRODUCT_INTENT__" else entity_id
        page=monitor_urls.get(page_id) or ""
        for key in keys:
            section=entity.get(key) or {}
            if section.get("status")=="N/A":
                continue
            href=page+"#"+upper_section_anchor(page_id,key)
            for criterion in section.get("criteria") or []:
                ran=[row for row in criterion.get("rows") or [] if row.get("result")!="skipped"]
                if signal=="execution":
                    # Execution reports what actually ran; a scenario that never ran
                    # is missing coverage, not a failed execution.
                    if not ran:
                        continue
                    statuses=["MET" if all(row.get("result")=="passed" for row in ran) else "NOT MET"]
                    label="Scenario execution"
                elif signal=="coverage":
                    statuses=[criterion.get("execution_status","UNKNOWN")]
                    label="Required assurance scenario"
                elif signal=="evidence":
                    if not ran:
                        continue
                    statuses=[
                      criterion.get("producer_qualification",{}).get("status","UNKNOWN"),
                      criterion.get("freshness",{}).get("status","UNKNOWN"),
                    ]
                    label="Assurance evidence trust"
                else:
                    continue
                checks.append({"statuses":statuses,"href":href,"label":label})
        return checks

    all_upper_ids=set(upper_by_id)-{"__PRODUCT_INTENT__"}

    def scoped_contracts(need_id):
        if need_id=="__PRODUCT_INTENT__":
            return set(contract_ids)
        return descendants.get(need_id,{need_id}) & contract_ids

    def scoped_upper_ids(need_id):
        if need_id=="__PRODUCT_INTENT__":
            return set(all_upper_ids)|{"__PRODUCT_INTENT__"}
        ids={need_id} if need_id in upper_by_id else set()
        ids|=(descendants.get(need_id,{need_id}) & all_upper_ids)
        return ids

    def first_href(results, fallback):
        failed=next((row["href"] for row in results if row["status"]=="failed" and row.get("href")),None)
        return failed or next((row["href"] for row in results if row.get("href")),fallback)

    def aggregate_contract_layer(scope_ids,key,fallback):
        results=[contract_layers[cid][key] for cid in sorted(scope_ids) if cid in contract_layers]
        statuses=[row["status"] for row in results if row["status"]!="na"]
        return health_layer_result(
          statuses,
          href=first_href(results,fallback),
          label={"coverage":"Coverage","faults":"Faults","evidence":"Evidence"}[key],
          applicable=bool(statuses),
          metrics=merge_health_metrics(results),
        )

    def aggregate_execution(need_id,scope_ids,fallback):
        rows=[row for row in map_rows_for_scope(scope_ids,owned_tests) if row.get("result")!="skipped"]
        checks=[{"status":health_layer_status(row.get("result")),"href":fallback} for row in rows]
        upper_checks=[]
        for upper_id in sorted(scoped_upper_ids(need_id)):
            for check in upper_direct_checks(upper_id,"execution"):
                status=health_layer_result(check["statuses"],href=check["href"],label=check["label"])
                upper_checks.append(status)
        statuses=[row["status"] for row in checks]+[row["status"] for row in upper_checks]
        test_statuses=[row["status"] for row in checks]
        scenario_statuses=[row["status"] for row in upper_checks]
        metrics=[]
        if test_statuses:
            metrics.append(health_metric("Tests",test_statuses))
        if scenario_statuses:
            metrics.append(health_metric("Scenarios",scenario_statuses))
        return health_layer_result(
          statuses,
          href=first_href([*checks,*upper_checks],fallback),
          label="Execution",
          applicable=bool(statuses),
          metrics=metrics,
        )

    def aggregate_coverage(need_id,scope_ids,fallback):
        contract_results=[contract_layers[cid]["coverage"] for cid in sorted(scope_ids) if cid in contract_layers]
        scenario_results=[]
        for upper_id in sorted(scoped_upper_ids(need_id)):
            for check in upper_direct_checks(upper_id,"coverage"):
                scenario_results.append(health_layer_result(
                  check["statuses"],
                  href=check["href"],
                  label=check["label"],
                  metrics=[health_metric("Required scenarios",check["statuses"])],
                ))
        results=[*contract_results,*scenario_results]
        statuses=[row["status"] for row in results if row["status"]!="na"]
        return health_layer_result(
          statuses,
          href=first_href(results,fallback),
          label="Coverage",
          applicable=bool(statuses),
          metrics=[*merge_health_metrics(contract_results),*merge_health_metrics(scenario_results)],
        )

    def assurance_layer(need_id,fallback):
        if need_id.startswith("TREQ_"):
            return health_layer_result([],href=fallback,label="Assurance",applicable=False)
        if need_id.startswith("REQ_"):
            required=list(((contracts.get(need_id) or {}).get("target") or {}).get("required_treqs") or [])
            if not required:
                return health_layer_result([],href=fallback,label="Technical support",applicable=False)
            statuses=[contract_direct.get(cid,{}).get("overall","UNKNOWN") for cid in required]
            return health_layer_result(
              statuses,
              href=fallback+f"#ce-technical-support-{need_id.lower()}",
              label="Assurance",
              metrics=[health_metric("TREQ support",statuses)],
            )
        entity=upper_by_id.get(need_id) or {}
        if not entity:
            return health_layer_result([],href=fallback,label="System assurance",applicable=False)
        if need_id=="__PRODUCT_INTENT__":
            keys=("goal_support","cross_goal_integration","operational_validation")
            page_id="PRODUCT_SYSTEM"
        elif need_id.startswith("GOAL_"):
            keys=("capability_support","cross_capability_integration","outcome_validation")
            page_id=need_id
        else:
            keys=("requirement_support","capability_integration","capability_validation")
            page_id=need_id
        rows=[]
        metric_labels={keys[0]:"Support",keys[1]:"Integration",keys[2]:"Validation"}
        metrics=[]
        for key in keys:
            state=entity.get(key) or {}
            if state.get("status")=="N/A":
                continue
            row_status=health_layer_status(state.get("status"))
            rows.append({
              "status":row_status,
              "href":fallback+"#"+upper_section_anchor(page_id,key),
            })
            members=state.get("children") or state.get("criteria") or []
            member_statuses=[
              member.get("status") or member.get("execution_status") or "UNKNOWN"
              for member in members
            ]
            if not member_statuses:
                member_statuses=[state.get("status","UNKNOWN")]
            metrics.append(health_metric(metric_labels[key],member_statuses))
        return health_layer_result(
          [row["status"] for row in rows],
          href=first_href(rows,fallback),
          label="Assurance",
          applicable=bool(rows),
          metrics=metrics,
        )

    def canonical_overall(need_id,fallback):
        if need_id in contracts:
            status=effective_contract_overall(need_id)
        else:
            status=(upper_by_id.get(need_id) or {}).get("status","UNKNOWN")
        return health_layer_result(
          [status],
          href=fallback,
          label="Overall",
        )

    def own_layers(need_id,fallback):
        """Checks that belong to this node itself; child verdicts are never repeated here."""
        not_applicable=lambda label:health_layer_result([],href=fallback,label=label,applicable=False)
        if need_id in contracts or need_id.startswith(("REQ_","TREQ_")):
            layers=contract_layers.get(need_id) or {}
            test_statuses=[
              health_layer_status(row.get("result"))
              for row in map_rows_for_scope({need_id},owned_tests)
              if row.get("result")!="skipped"
            ]
            execution=health_layer_result(
              test_statuses,
              href=fallback,
              label="Execution",
              applicable=bool(test_statuses),
              metrics=[health_metric("Tests",test_statuses)] if test_statuses else [],
            )
            direct=(contract_direct.get(need_id) or {}).get("overall","UNKNOWN")
            return {
              "overall":health_layer_result([direct],href=fallback,label="Overall"),
              "execution":execution,
              "coverage":{
                **(layers.get("coverage") or health_layer_result(["UNKNOWN"],href=fallback,label="Coverage")),
                "unbound_tests":unbound_tests.get(need_id,0),
              },
              "faults":layers.get("faults") or not_applicable("Faults"),
              "evidence":layers.get("evidence") or not_applicable("Evidence"),
              "assurance":not_applicable("Assurance"),
            }
        entity=upper_by_id.get(need_id)
        if not entity:
            missing=health_layer_result(
              ["UNKNOWN"],href=fallback,label="Overall",
              metrics=[{"label":"Assurance profile","passed":0,"total":1}],
            )
            return {
              "overall":missing,
              "execution":not_applicable("Execution"),
              "coverage":not_applicable("Coverage"),
              "faults":not_applicable("Faults"),
              "evidence":not_applicable("Evidence"),
              "assurance":{**missing,"label":"Assurance"},
            }

        def scenario_layer(signal,label,metric_label):
            results=[
              health_layer_result(check["statuses"],href=check["href"],label=check["label"])
              for check in upper_direct_checks(need_id,signal)
            ]
            statuses=[row["status"] for row in results]
            return health_layer_result(
              statuses,
              href=first_href(results,fallback),
              label=label,
              applicable=bool(statuses),
              metrics=[health_metric(metric_label,statuses)] if statuses else [],
            )

        evidence_checks=upper_direct_checks(need_id,"evidence")
        evidence_results=[
          health_layer_result(check["statuses"],href=check["href"],label=check["label"])
          for check in evidence_checks
        ]
        evidence=health_layer_result(
          [row["status"] for row in evidence_results],
          href=first_href(evidence_results,fallback),
          label="Evidence",
          applicable=bool(evidence_results),
          metrics=[
            health_metric("Producers",[check["statuses"][0] for check in evidence_checks]),
            health_metric("Freshness",[check["statuses"][1] for check in evidence_checks]),
          ] if evidence_checks else [],
        )
        if need_id=="__PRODUCT_INTENT__":
            page_id="PRODUCT_SYSTEM"
            keys=(("cross_goal_integration","Integration"),("operational_validation","Validation"))
        elif need_id.startswith("GOAL_"):
            page_id=need_id
            keys=(("cross_capability_integration","Integration"),("outcome_validation","Validation"))
        else:
            page_id=need_id
            keys=(("capability_integration","Integration"),("capability_validation","Validation"))
        section_rows=[]
        section_metrics=[]
        for key,label in keys:
            state=entity.get(key) or {}
            if state.get("status")=="N/A":
                continue
            section_rows.append({
              "status":health_layer_status(state.get("status")),
              "href":fallback+"#"+upper_section_anchor(page_id,key),
            })
            members=state.get("criteria") or state.get("children") or []
            member_statuses=[
              member.get("status") or member.get("execution_status") or "UNKNOWN"
              for member in members
            ] or [state.get("status","UNKNOWN")]
            section_metrics.append(health_metric(label,member_statuses))
        assurance=health_layer_result(
          [row["status"] for row in section_rows],
          href=first_href(section_rows,fallback),
          label="Assurance",
          applicable=bool(section_rows),
          metrics=section_metrics,
        )
        execution=scenario_layer("execution","Execution","Scenarios")
        coverage=scenario_layer("coverage","Coverage","Required scenarios")
        own_parts=[layer for layer in (execution,coverage,evidence,assurance) if layer["status"]!="na"]
        overall=health_layer_result(
          [layer["status"] for layer in own_parts],
          href=first_href(own_parts,fallback),
          label="Overall",
          applicable=bool(own_parts),
        )
        return {
          "overall":overall,
          "execution":execution,
          "coverage":coverage,
          "faults":not_applicable("Faults"),
          "evidence":evidence,
          "assurance":assurance,
        }

    def map_level(need_id):
        if need_id=="__PRODUCT_INTENT__":
            return "product"
        if need_id.startswith("GOAL_"):
            return "goal"
        if need_id.startswith("FEAT_"):
            return "feature"
        if need_id.startswith("TREQ_"):
            return "treq"
        return "requirement"

    def short_label(need_id,title):
        # Goal outcomes are long sentences; their authored IDs already carry a concise name.
        if need_id.startswith("GOAL_"):
            words=need_id.removeprefix("GOAL_").lower().split("_")
            return " ".join(words).capitalize()
        return title

    def item_for(need_id,need,parent_id):
        scope=scoped_contracts(need_id)
        page_id="PRODUCT_SYSTEM" if need_id=="__PRODUCT_INTENT__" else need_id
        fallback=monitor_urls.get(page_id) or "assurance-product-system.html"
        execution=aggregate_execution(need_id,scope,fallback)
        coverage=aggregate_coverage(need_id,scope,fallback)
        faults=aggregate_contract_layer(scope,"faults",fallback)
        evidence=aggregate_contract_layer(scope,"evidence",fallback)
        # Upper-level producer/freshness gates are part of evidence trust too.
        upper_evidence=[]
        for upper_id in sorted(scoped_upper_ids(need_id)):
            for check in upper_direct_checks(upper_id,"evidence"):
                upper_evidence.append(health_layer_result(
                  check["statuses"],
                  href=check["href"],
                  label=check["label"],
                  metrics=[
                    health_metric("Producers",[check["statuses"][0]]),
                    health_metric("Freshness",[check["statuses"][1]]),
                  ],
                ))
        if upper_evidence:
            statuses=[evidence["status"]] if evidence["status"]!="na" else []
            statuses.extend(row["status"] for row in upper_evidence if row["status"]!="na")
            evidence_inputs=([evidence] if evidence["status"]!="na" else [])+upper_evidence
            evidence=health_layer_result(
              statuses,
              href=first_href(evidence_inputs,fallback),
              label="Evidence",
              metrics=merge_health_metrics(evidence_inputs),
            )
        assurance=assurance_layer(need_id,fallback)
        overall=canonical_overall(need_id,fallback)
        overall_metrics=[]
        if coverage["status"]!="na":
            overall_metrics.append({
              "label":"Coverage",
              "passed":sum(metric["passed"] for metric in coverage.get("metrics") or []),
              "total":sum(metric["total"] for metric in coverage.get("metrics") or []),
            })
        if faults["status"]!="na":
            overall_metrics.extend(faults.get("metrics") or [])
        if evidence["status"]!="na":
            overall_metrics.append({
              "label":"Evidence",
              "passed":sum(metric["passed"] for metric in evidence.get("metrics") or []),
              "total":sum(metric["total"] for metric in evidence.get("metrics") or []),
            })
        if assurance["status"]!="na":
            overall_metrics.extend(assurance.get("metrics") or [])
        overall["metrics"]=[metric for metric in overall_metrics if metric["total"]]
        layers={
          "overall":overall,
          "execution":execution,
          "coverage":coverage,
          "faults":faults,
          "evidence":evidence,
          "assurance":assurance,
        }
        label="Product / System" if need_id=="__PRODUCT_INTENT__" else str(need.get("title") or need_id)
        return {
          "id":need_id,
          "label":label,
          "short":short_label(need_id,label),
          "level":map_level(need_id),
          "parent":parent_id,
          "layers":layers,
          "own":own_layers(need_id,fallback),
        }

    items=[item_for(need_id,nodes[need_id],parent.get(need_id) or "__PRODUCT_INTENT__") for need_id in ordered]
    root=item_for("__PRODUCT_INTENT__",{},"")
    rows=[root,*items]
    layer_keys=(
      ("overall","Overall"),
      ("execution","Execution"),
      ("coverage","Coverage"),
      ("faults","Faults"),
      ("evidence","Evidence"),
      ("assurance","Assurance"),
    )
    row_children=defaultdict(list)
    for row in items:
        row_children[row["parent"]].append(row)

    # False-green guard: a canonical FAIL must stay visible as at least one own mark in its branch.
    # Assurance support is the children's canonical verdict, so it is attributed to their Overall marks.
    def attribute_failures(row):
        marked={}
        child_marks=[attribute_failures(child) for child in row_children.get(row["id"],[])]
        for key,label in layer_keys:
            own=row["own"][key]
            sources=("assurance","overall") if key=="assurance" else (key,)
            marked[key]=own["status"]=="failed" or any(
              marks[source] for marks in child_marks for source in sources
            )
            if row["layers"][key]["status"]=="failed" and not marked[key]:
                row["own"][key]={
                  **health_layer_result(
                    ["UNKNOWN"],href=row["layers"][key].get("href"),label=label,
                    metrics=[{"label":"Unattributed failure","passed":0,"total":1}],
                  ),
                  "unattributed":True,
                }
                marked[key]=True
        return marked

    attribute_failures(root)
    # One row per goal, capability and contract with the product first, in the same shape as the measures' rows; the
    # summary is each layer's verdict and how many of its own marks fail.
    layer_summary={}
    for key,_label in layer_keys:
        own_applicable=[row["own"][key] for row in rows if row["own"][key]["status"]!="na"]
        layer_summary[key]={
          "status":root["layers"][key]["status"],
          "failing":sum(row["status"]=="failed" for row in own_applicable),
          "applicable":len(own_applicable),
        }
    return {"rows":rows,"summary":{"layers":layer_summary}}

HEALTH_RUN_SNAPSHOTS=ROOT/"test-results/health-map/runs"
DEPTH_RUN_SNAPSHOTS=ROOT/"test-results/depth-map/runs"
HEALTH_LAYER_KEYS=("overall","execution","coverage","faults","evidence","assurance")
HEALTH_LAYER_NAMES={"execution":"Execution","coverage":"Coverage","faults":"Fault model","evidence":"Evidence quality","assurance":"Assurance"}
# Why a red mark is red, in the words a reader acts on. Fault causes come from the contract's
# required fault classes; the other layers name the check that fails.
HEALTH_CAUSES={
  "faults":(
    ("unchallenged","Unchallenged fault classes","A required fault class has no retained test that challenges it for this contract."),
    ("shared","Shared @impl","Its code is also claimed by other contracts, so a fault there cannot be pinned on this one."),
    ("survivors","Surviving mutants","The contract's tests run the mutated code and still pass: they do not check what the mutant changes."),
    ("notreached","Code not reached","No test of the contract runs the code where its mutants sit."),
    ("unproven","Equivalence not proven","A semantic mutant survives and no input yet tells it apart from the original."),
    ("generate","Semantic mutants not generated","A target the profile selects has no semantic mutant: it was never generated, or its generation was deferred by the budget, found no available model or got an answer the adapter rejected."),
    ("regenerate","Semantic mutants not current","The cascade has not judged the current proposals: they are new, their target or its context changed, or the cascade has not run since."),
    ("suppressed","All mutants suppressed","Every mutant of a required class carries a suppression pragma, so none is judged."),
    ("invalid","Mutants break collection","Every mutant of a required class broke test collection, so none could be judged."),
    ("nosite","No fault site","A required class has no mutable site in the attributable code; the profile may ask for too much."),
    ("noimpl","No @impl","No code is annotated as implementing this contract, so implementation faults have no target."),
    ("notests","No passing tests","The contract has no passing test to judge its faults with."),
    ("missed","Challenge not caught","A retained challenge ran, but the contract's tests did not catch it."),
    ("campaign","Campaign not current","The implementation fault campaign result is stale or failed; run it again."),
    ("blocked","Campaign blocked","The implementation fault campaign could not run for this contract."),
  ),
  "coverage":(
    ("uncovered","Required case not covered","A required case of the verification profile has no passing test."),
    ("scenario","Required scenario missing or failing","A required scenario did not pass."),
    ("unbound","Linked test outside the profile","A failing test verifies the contract outside every required case."),
  ),
}
HEALTH_METRIC_CAUSES={
  "Tests":("Tests fail","A test linked to this item failed."),
  "Scenarios":("Scenarios fail","A scenario linked to this item failed."),
  "Required scenarios":("Required scenario missing or failing","A required scenario did not pass."),
  "Targets":("Required case not covered","A required case of the verification profile has no passing test."),
  "Fault groups":("Fault checks fail","A required fault group is not caught."),
  "Representation":("Wrong kind of target","The evidence does not represent the target it claims."),
  "Provenance":("Not traceable to its run","The evidence cannot be traced to the retained run."),
  "Producers":("Unqualified producer","A tool that produced the evidence is not qualified."),
  "Freshness":("Stale evidence","Evidence inputs changed after the retained run."),
  "M&S":("Model not validated","The model or simulation behind the evidence is not validated to the required level."),
  "Integration":("Integration check fails","An integration check of this goal or capability fails."),
  "Validation":("Validation check fails","A validation check of this goal or capability fails."),
  "Unattributed failure":("Fails for an unclear reason","The layer fails here, but no own check says why."),
  "Assurance profile":("No assurance plan","The goal or capability has no assurance profile."),
}


def health_fault_cause(state,plan):
    """Why a required fault class is not caught, in the words a reader acts on."""
    if not state:
        return "campaign"
    undecided=int(state.get("undecided") or 0)
    if state.get("detected") and not undecided:
        return None
    campaign=state.get("campaign_state")
    if campaign=="blocked":
        return {"shared_scope":"shared","no_impl_scope":"noimpl","no_passing_tests":"notests"}.get((plan or {}).get("blocked"),"blocked")
    if campaign=="current":
        if int(state.get("survived_reached") or 0):
            return "survivors"
        if int(state.get("unreached") or 0):
            return "notreached"
        if int(state.get("judged") or 0)==0:
            if int(state.get("suppressed") or 0):
                return "suppressed"
            if int(state.get("invalid") or 0):
                return "invalid"
            return "nosite"
        return "survivors"
    if campaign:
        return "campaign"
    if state.get("exercised") and not state.get("detected"):
        return "missed"
    if undecided and int(state.get("semantic_not_generated") or 0):
        return "generate"
    if undecided and state.get("semantic_state") in {"stale","not_run","unqualified"}:
        return "regenerate"
    if undecided:
        return "unproven"
    return "unchallenged"


def health_layer_causes(rows,contracts,plans):
    """For every layer, which red marks fail and why; each red mark carries at least one cause."""
    failing={key:{row["id"] for row in rows if row["own"][key]["status"]=="failed"} for key in HEALTH_LAYER_KEYS}
    causes={key:defaultdict(set) for key in HEALTH_LAYER_KEYS}
    for row in rows:
        for key in HEALTH_LAYER_KEYS[1:]:
            if row["id"] not in failing[key]:
                continue
            own=row["own"][key]
            found=set()
            if key=="faults" and row["id"] in contracts:
                contract=contracts[row["id"]]
                required={
                  item.get("id")
                  for group in (contract.get("target") or {}).get("fault_groups") or []
                  for item in group.get("items") or []
                  if item.get("state")=="required"
                }
                classes=(contract.get("fault_actual") or {}).get("classes") or {}
                for name in sorted(required):
                    cause=health_fault_cause(classes.get(name),plans.get(row["id"]))
                    if cause:
                        found.add(cause)
            if key=="coverage":
                if own.get("unbound_tests"):
                    found.add("unbound")
            for metric in own.get("metrics") or []:
                if not metric.get("total") or metric.get("passed",0)>=metric["total"]:
                    continue
                label=metric.get("label")
                if key=="coverage" and label=="Targets":
                    found.add("uncovered")
                elif key=="coverage" and label=="Required scenarios":
                    found.add("scenario")
                elif key=="faults" and label=="Fault groups" and found:
                    continue
                else:
                    found.add("metric:"+str(label))
            for cause in found or {"metric:Unattributed failure"}:
                causes[key][cause].add(row["id"])
    known={key:{cause_id:(label,hint) for cause_id,label,hint in entries} for key,entries in HEALTH_CAUSES.items()}
    out={}
    for key in HEALTH_LAYER_KEYS[1:]:
        order=[cause_id for cause_id,_label,_hint in HEALTH_CAUSES.get(key,())]
        listed=[]
        for cause_id,ids in causes[key].items():
            if cause_id.startswith("metric:"):
                label,hint=HEALTH_METRIC_CAUSES.get(cause_id[7:],(cause_id[7:],""))
            else:
                label,hint=known[key][cause_id]
            listed.append({"id":cause_id,"label":label,"hint":hint,"ids":sorted(ids)})
        listed.sort(key=lambda item:(-len(item["ids"]),order.index(item["id"]) if item["id"] in order else len(order)))
        out[key]=listed
    # Overall fails because a layer fails: its causes are the layers themselves, most red marks first.
    out["overall"]=sorted(
      [
        {"id":key,"label":HEALTH_LAYER_NAMES[key],"hint":"Fails in the "+HEALTH_LAYER_NAMES[key]+" layer.","ids":sorted(failing[key])}
        for key in HEALTH_LAYER_KEYS[1:]
        if failing[key]
      ],
      key=lambda item:-len(item["ids"]),
    )
    return out


def health_run_stamp(root):
    provenance=json.loads(EVIDENCE_RUN_PROVENANCE_PATH.read_text()) if EVIDENCE_RUN_PROVENANCE_PATH.exists() else {}
    execution=root["layers"]["execution"]
    freshness=next((metric for metric in root["layers"]["evidence"].get("metrics") or [] if metric.get("label")=="Freshness"),None)
    return {
      "run_id":provenance.get("run_id"),
      "started_at":(provenance.get("execution") or {}).get("started_at"),
      "commit":str(provenance.get("git_head") or "")[:7],
      "checks":execution.get("total"),
      "fresh":{"passed":freshness["passed"],"total":freshness["total"]} if freshness else None,
    }


def run_delta(snapshots,schema,stamp,values,compare):
    """Compare with the snapshot of the previous retained run of the same page. Each run keeps one
    snapshot, so re-rendering the same run never moves the baseline; the page's compare says what
    went up and what went down in each layer."""
    run_id,started_at=stamp.get("run_id"),stamp.get("started_at")
    if not run_id or not started_at:
        return {"baseline":None,"layers":{}}
    snapshots.mkdir(parents=True,exist_ok=True)
    earlier=[]
    for path in sorted(snapshots.glob("*.json")):
        try:
            snapshot=json.loads(path.read_text())
        except (OSError,ValueError):
            continue
        if snapshot.get("run_id")!=run_id and str(snapshot.get("started_at") or "")<started_at:
            earlier.append(snapshot)
    snapshot_name=re.sub(r"[^A-Za-z0-9_.-]","-",str(run_id))+".json"
    (snapshots/snapshot_name).write_text(
      json.dumps({"schema":schema,"run_id":run_id,"started_at":started_at,"values":values},sort_keys=True)+"\n"
    )
    kept=sorted(snapshots.glob("*.json"),key=lambda path:path.stat().st_mtime,reverse=True)
    for stale in kept[10:]:
        stale.unlink()
    if not earlier:
        return {"baseline":None,"layers":{}}
    base=max(earlier,key=lambda snapshot:str(snapshot.get("started_at")))
    before=base.get("values") or base.get("statuses") or {}
    return {"baseline":{"run_id":base.get("run_id"),"started_at":base.get("started_at")},"layers":compare(before,values)}


def health_changes(before,after):
    """Up: a mark that fails now and did not fail before. Down: one that failed and no longer fails."""
    return {
      key:{
        "up":sorted(row_id for row_id,value in after.items() if value[key]=="failed" and (before.get(row_id) or {}).get(key)!="failed"),
        "down":sorted(row_id for row_id,value in before.items() if row_id in after and value.get(key)=="failed" and after[row_id][key]!="failed"),
      }
      for key in HEALTH_LAYER_KEYS
    }


def health_run_delta(rows,stamp):
    statuses={row["id"]:{key:row["own"][key]["status"] for key in HEALTH_LAYER_KEYS} for row in rows}
    return run_delta(HEALTH_RUN_SNAPSHOTS,"health-map-run-2",stamp,statuses,health_changes)


def health_map_insights(payload):
    rows=payload["rows"]
    contracts=(json.loads(REQ_MONITOR_FACTS_PATH.read_text()).get("contracts") or {})
    stamp=health_run_stamp(rows[0])
    return {
      "causes":health_layer_causes(rows,contracts,implementation_fault_plans()),
      "run":stamp,
      "delta":health_run_delta(rows,stamp),
    }


def vendored_d3_hierarchy():
    if not D3_HIERARCHY_VENDOR_PATH.exists():
        raise RuntimeError("pinned d3-hierarchy 3.1.2 asset is missing")
    source=D3_HIERARCHY_VENDOR_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest()!=D3_HIERARCHY_VENDOR_SHA256:
        raise RuntimeError("pinned d3-hierarchy 3.1.2 asset digest mismatch")
    text=source.decode("utf-8")
    if "</script" in text.lower():
        raise RuntimeError("pinned d3-hierarchy 3.1.2 asset cannot be inlined")
    return text


def health_facts():
    payload=health_map_payload()
    payload["insights"]=health_map_insights(payload)
    return payload


DEPTH_LEVELS=("component","component_integration","system","system_integration","acceptance")
DEPTH_BOUNDARIES=("none","substitute","replay","direct")
DEPTH_LEVEL_RANK={value:index for index,value in enumerate(DEPTH_LEVELS)}
DEPTH_BOUNDARY_RANK={value:index for index,value in enumerate(DEPTH_BOUNDARIES)}
DEPTH_MS_LEVELS=("l0","l1","l2","l3","l4")
DEPTH_UPPER_SECTIONS={
  "feature":("capability_integration","capability_validation"),
  "goal":("cross_capability_integration","outcome_validation"),
  "product":("cross_goal_integration","operational_validation"),
}


def depth_passing(nodeid):
    return str((TEST_META.get(nodeid) or {}).get("result") or "").lower()=="passed"


def depth_cells(nodeids):
    """Passing tests per (test level, boundary) cell, with the substitutes that stand at the boundary."""
    cells={}
    for nodeid in dict.fromkeys(nodeids):
        if not depth_passing(nodeid):
            continue
        test=TEST_META[nodeid]
        cell=cells.setdefault((str(test.get("system_reach") or "none"),str(test.get("boundary_mode") or "none")),{"tests":0,"producers":Counter()})
        cell["tests"]+=1
        if test.get("model_producer"):
            cell["producers"][test["model_producer"]]+=1
    return [
      [level,boundary,value["tests"],dict(sorted(value["producers"].items()))]
      for (level,boundary),value in sorted(
        cells.items(),key=lambda item:(DEPTH_LEVEL_RANK.get(item[0][0],9),DEPTH_BOUNDARY_RANK.get(item[0][1],9))
      )
    ]


def depth_fault_measure(contract,plan):
    """Implementation faults caught of the judged mutants, from the current campaign, or why it is not measured."""
    classes={
      name:state
      for name,state in (((contract.get("fault_actual") or {}).get("classes")) or {}).items()
      if name.startswith("impl.")
    }
    killed=sum(int(state.get("caught") or state.get("killed") or 0) for state in classes.values())
    judged=sum(int(state.get("judged") or 0) for state in classes.values())
    if judged:
        return [killed,judged],""
    asked={
      item.get("state")
      for group in (contract.get("target") or {}).get("fault_groups") or []
      for item in group.get("items") or []
      if str(item.get("id") or "").startswith("impl.")
    }
    if not asked-{"na"}:
        return None,"not_asked"
    blocked=(plan or {}).get("blocked")
    if blocked:
        return None,{"shared_scope":"shared","no_impl_scope":"noimpl","no_passing_tests":"notests"}.get(blocked,"campaign")
    if any(state.get("campaign_state")=="current" for state in classes.values()):
        return None,"nosite"
    return None,"campaign"


def depth_map_payload(health_payload):
    """Evidence depth: where each contract's own passing tests sit by test level and boundary,
    which substitutes stand at the boundary and how well their model is validated, and how
    many injected implementation faults the tests catch. Each test counts once, for the entity
    it was written for, as on the Health Map; the hierarchy is the Health Map's own. A mutation
    pin pins one mutant: it is no evidence of depth, so it does not count here."""
    req_facts=json.loads(REQ_MONITOR_FACTS_PATH.read_text())
    upper_facts=json.loads(UPPER_ASSURANCE_FACTS_PATH.read_text())
    contracts=req_facts.get("contracts") or {}
    monitor_urls=ASSURANCE_REGISTRY.monitor_urls(set(contracts))
    bindings=junit_test_bindings()
    plans=implementation_fault_plans()
    criterion_owner={
      criterion_id:owner
      for contract in contracts.values()
      for criterion_id,owner in ((contract.get("target") or {}).get("criterion_contracts") or {}).items()
    }
    own=defaultdict(list)
    failing=Counter()
    for test in DEPTH.get("tests") or []:
        binding=bindings.get(test.get("nodeid")) or {}
        if binding.get("assurance_item") or is_mutation_pin(test.get("nodeid")):
            continue
        owner=criterion_owner.get(binding.get("coverage_item") or "")
        for contract_id in test.get("verifies") or []:
            if contract_id not in contracts or (owner and owner!=contract_id):
                continue
            own[contract_id].append(test["nodeid"])
            if str(test.get("result") or "").lower() not in {"passed","skipped"}:
                failing[contract_id]+=1

    records=DEPTH.get("model_validation_records") or {}
    producer_contracts=defaultdict(set)
    depth_contracts={}
    for contract_id,contract in sorted(contracts.items()):
        cells=depth_cells(own.get(contract_id) or [])
        passing=[nodeid for nodeid in dict.fromkeys(own.get(contract_id) or []) if depth_passing(nodeid)]
        levels=sorted({
          DEPTH_MS_LEVELS.index(TEST_META[nodeid]["ms_validation"])
          for nodeid in passing
          if TEST_META[nodeid].get("model_producer") and TEST_META[nodeid].get("ms_validation") in DEPTH_MS_LEVELS
        })
        producers=sorted({pid for cell in cells for pid in cell[3]})
        for pid in producers:
            producer_contracts[pid].add(contract_id)
        detect,reason=depth_fault_measure(contract,plans.get(contract_id))
        classes=((contract.get("fault_actual") or {}).get("classes")) or {}
        required=[
          item.get("id")
          for group in (contract.get("target") or {}).get("fault_groups") or []
          for item in group.get("items") or []
          if item.get("state")=="required"
        ]
        base=monitor_urls.get(contract_id) or ""
        # Required cases per cell, counted exactly as the Contract Evidence matrix counts them.
        cases={}
        for target in (contract.get("target") or {}).get("coverage") or []:
            state=ASSURANCE_DOMAIN.cell_state(contract,target)
            key=(str(target.get("level")),str(target.get("boundary")))
            covered_cases,required_cases=cases.get(key,(0,0))
            cases[key]=(covered_cases+int(state["semantic_actual"]),required_cases+int(state["required_count"]))
        depth_contracts[contract_id]={
          "cells":cells,
          "cases":[
            [level,boundary,covered_cases,required_cases]
            for (level,boundary),(covered_cases,required_cases) in sorted(
              cases.items(),key=lambda item:(DEPTH_LEVEL_RANK.get(item[0][0],9),DEPTH_BOUNDARY_RANK.get(item[0][1],9))
            )
          ],
          "target":sorted(
            {(str(item.get("level")),str(item.get("boundary"))) for item in (contract.get("target") or {}).get("coverage") or []},
            key=lambda cell:(DEPTH_LEVEL_RANK.get(cell[0],9),DEPTH_BOUNDARY_RANK.get(cell[1],9)),
          ),
          "deepest":max((cell[0] for cell in cells),key=lambda value:DEPTH_LEVEL_RANK.get(value,-1),default=None),
          "real":max((cell[1] for cell in cells),key=lambda value:DEPTH_BOUNDARY_RANK.get(value,-1),default=None),
          "trust":DEPTH_MS_LEVELS[levels[0]] if levels else "na",
          "producers":producers,
          "tests":len(passing),
          "failing":failing[contract_id],
          "kinds":dict(sorted(Counter(str(TEST_META[nodeid].get("verification_kind") or "other") for nodeid in passing).items())),
          "detect":detect,
          "reason":reason,
          "classes":{
            "required":len(required),
            "caught":sum(bool((classes.get(name) or {}).get("detected")) for name in required),
          },
          "href":base+f"#ce-coverage-{contract_id.lower()}" if base else "",
          "fault_href":base+f"#ce-faults-{contract_id.lower()}" if base else "",
        }

    # Goals and capabilities own their integration and validation scenarios.
    checks={}
    criteria_by_test=defaultdict(set)
    upper_entities=[("feature",entity) for entity in (upper_facts.get("features") or {}).values()]
    upper_entities+=[("goal",entity) for entity in (upper_facts.get("goals") or {}).values()]
    if upper_facts.get("product_system"):
        upper_entities.append(("product",{**upper_facts["product_system"],"id":"__PRODUCT_INTENT__"}))
    for kind,entity in upper_entities:
        nodeids=[]
        target=set()
        count=0
        for key in DEPTH_UPPER_SECTIONS[kind]:
            for criterion in (entity.get(key) or {}).get("criteria") or []:
                count+=1
                for check in (criterion.get("classification") or {}).get("checks") or []:
                    goal=check.get("target") or {}
                    if goal.get("level") and goal.get("boundary"):
                        target.add((str(goal["level"]),str(goal["boundary"])))
                for row in criterion.get("rows") or []:
                    if row.get("nodeid"):
                        nodeids.append(row["nodeid"])
                        criteria_by_test[row["nodeid"]].add(criterion.get("id") or "")
        if count:
            checks[entity["id"]]={
              "cells":depth_cells(nodeids),
              "target":sorted(target,key=lambda cell:(DEPTH_LEVEL_RANK.get(cell[0],9),DEPTH_BOUNDARY_RANK.get(cell[1],9))),
              "criteria":count,
            }

    # System cells count distinct passing tests, whoever owns them.
    system_tests=defaultdict(set)
    system_producers=defaultdict(lambda:defaultdict(set))
    system_checks=defaultdict(set)
    for test in DEPTH.get("tests") or []:
        nodeid=test.get("nodeid")
        if not depth_passing(nodeid):
            continue
        key=f"{test.get('system_reach') or 'none'}|{test.get('boundary_mode') or 'none'}"
        system_tests[key].add(nodeid)
        if test.get("model_producer"):
            system_producers[key][test["model_producer"]].add(nodeid)
        system_checks[key].update(criteria_by_test.get(nodeid) or ())
    producers={}
    for pid,record in sorted(records.items()):
        producers[pid]={
          "title":str(record.get("title") or pid),
          "level":str(record.get("ms_validation") or "l0"),
          "referent":str(record.get("referent") or ""),
          "basis":str(record.get("basis") or ""),
          "tests":sum(1 for test in DEPTH.get("tests") or [] if test.get("model_producer")==pid and depth_passing(test.get("nodeid"))),
          "contracts":sorted(producer_contracts.get(pid) or ()),
        }

    health_rows=health_payload["rows"]
    return {
      "rows":[
        {
          "id":row["id"],
          "parent":row.get("parent") or "",
          "level":row["level"],
          "label":row["label"],
          "short":row.get("short") or row["label"],
          "href":((row.get("layers") or {}).get("overall") or {}).get("href") or "",
        }
        for row in health_rows
      ],
      "contracts":{
        contract_id:depth_contracts[contract_id]
        for contract_id in (row["id"] for row in health_rows)
        if contract_id in depth_contracts
      },
      "checks":checks,
      "cells":{
        key:{
          "tests":len(tests),
          "producers":{pid:len(ids) for pid,ids in sorted(system_producers[key].items())},
          "checks":len(system_checks[key]),
        }
        for key,tests in sorted(system_tests.items())
      },
      "producers":producers,
    }


DEPTH_CHANGE_KEYS=("level","boundary","trust","detect")


def depth_values(payload):
    """What the next run is compared with: each contract's cells and its value in every depth layer."""
    values={}
    for contract_id,contract in payload["contracts"].items():
        detect=contract.get("detect")
        values[contract_id]={
          "cells":sorted(f"{cell[0]}|{cell[1]}" for cell in contract["cells"]),
          "level":DEPTH_LEVEL_RANK.get(contract.get("deepest"),-1),
          "boundary":DEPTH_BOUNDARY_RANK.get(contract.get("real"),-1),
          "trust":DEPTH_MS_LEVELS.index(contract["trust"]) if contract.get("trust") in DEPTH_MS_LEVELS else None,
          "detect":round(detect[0]/detect[1],4) if detect else None,
        }
    return values


def depth_changes(before,after):
    """Up: a contract whose value in a layer rose since the previous run (a new cell, a deeper level,
    a more realistic boundary, a better checked model, more mutants caught). Down: one whose value
    fell. Depth judges neither: a layer the contract cannot be compared in (no model, not measured)
    stays out."""
    layers={key:{"up":[],"down":[]} for key in ("overall",*DEPTH_CHANGE_KEYS)}
    for contract_id,now in sorted(after.items()):
        then=before.get(contract_id)
        if not then:
            continue
        if set(now["cells"])-set(then["cells"]):
            layers["overall"]["up"].append(contract_id)
        if set(then["cells"])-set(now["cells"]):
            layers["overall"]["down"].append(contract_id)
        for key in DEPTH_CHANGE_KEYS:
            if now[key] is None or then.get(key) is None or now[key]==then[key]:
                continue
            layers[key]["up" if now[key]>then[key] else "down"].append(contract_id)
    return layers


def depth_map_insights(payload,health_payload):
    stamp=health_run_stamp(health_payload["rows"][0])
    return {"run":stamp,"delta":run_delta(DEPTH_RUN_SNAPSHOTS,"depth-map-run-1",stamp,depth_values(payload),depth_changes)}


def depth_facts(health_payload):
    payload=depth_map_payload(health_payload)
    payload["insights"]=depth_map_insights(payload,health_payload)
    return payload


def render_health_map_page():
    """The Verification Health Map: every layer's health and, beside it, its measures (how deep, how realistic and
    how strong the evidence is), from the health facts and the depth facts side by side."""
    health_payload=health_facts()
    depth_payload=depth_facts(health_payload)
    article=MAP_PAGES.health_map_article(stable_json({"health":health_payload,"depth":depth_payload}),vendored_d3_hierarchy())
    HEALTH_PAGE.write_text(portal_map_shell(HEALTH_PAGE,"Verification Health Map",article))
    for retired in RETIRED_MAP_PAGES:
        retired.unlink(missing_ok=True)
    return health_payload,depth_payload


# The Verification Explorer lists every item behind the monitors, one row each: the evidence paths of every
# criterion, tests outside the profiles, fault classes and their mutants, the own checks of goals and capabilities,
# what each item depends on and the evidence producers. It judges nothing a monitor does not judge: statuses come
# from the same domain algebra as Contract Evidence and the Health Map, causes in the Health Map's own words.
# Causes that only a single row can have; the rest are the Health Map's.
EXPLORER_CAUSES={
  "support":("Supporting item fails","Something this item depends on fails, so it cannot pass until that passes."),
  "unexpected":("Path the profile does not declare","A retained test claims a path the profile does not list, so its criterion cannot be judged."),
}
EXPLORER_SUPPORT_SECTIONS={"feature":"requirement_support","goal":"capability_support","product":"goal_support"}
EXPLORER_SECTION_LABELS={
  key:label
  for labels in (ASSURANCE_REGISTRY.FEATURE_SECTION_LABELS,ASSURANCE_REGISTRY.GOAL_SECTION_LABELS,ASSURANCE_REGISTRY.PRODUCT_SECTION_LABELS)
  for label,key in labels
}
EXPLORER_STATUS={"MET":"pass","NOT MET":"fail","N/A":"na"}
# A semantic mutant in the explorer: its status, state word and causes, by the cascade's outcome.
EXPLORER_SEMANTIC_OUTCOMES={
  "caught":("pass","Caught",[]),
  "distinguished":("fail","Survived",["survivors"]),
  "undecided":("unknown","Undecided",["unproven"]),
  "stale":("unknown","Stale",["regenerate"]),
  "equivalent":("na","Equivalent",[]),
  "identical":("na","Filtered · identical",[]),
  "duplicate":("na","Filtered · duplicate",[]),
  "invalid":("na","Filtered · invalid",[]),
}
# One mutant in the explorer: its status, state word, causes and what it means, by outcome.
EXPLORER_MUTANT_OUTCOMES={
  "caught":("pass","Caught",[],"A test of the contract fails on this change, so the tests catch it."),
  "survived":("fail","Survived",["survivors"],"Its tests run this line and none fails."),
  "notreached":("fail","Not reached",["notreached"],"No test of the contract runs this line."),
  "suppressed":("na","Suppressed",[],"Suppressed by a pragma."),
  "invalid":("na","Invalid",[],"The change broke test collection, so it proves nothing either way."),
}
EXPLORER_WORD={"MET":"PASS","NOT MET":"FAIL","N/A":"N/A","UNKNOWN":"UNKNOWN"}
# What one backend's attempt at a target without mutants came to.
EXPLORER_GENERATION_OUTCOMES={
  "deferred":"was deferred by the budget",
  "unavailable":"was unavailable",
  "rejected":"was rejected by its plan's usage window",
  "invalid":"answered outside its schema",
  "error":"failed",
  "timeout":"timed out",
}


def tokens_text(count):
    count=int(count or 0)
    return f"{count/1000:.1f}k" if count>=1000 else str(count)


def explorer_generation_note(contract_id,generator,calls,verb,label,shared=1):
    """Who wrote a semantic mutant or its draft, and what the call cost, for its explorer row; a call that
    produced several mutants is named with how many, so its cost is not read as each one's."""
    if generator.get("kind")=="model":
        call=calls.get(generator.get("call_id")) or {}
        tokens=call.get("tokens") or {}
        spent=[]
        if tokens:
            spent.append(
              f"{tokens_text(sum(int(tokens.get(key) or 0) for key in ('input','cache_read','cache_write')))} in and "
              f"{tokens_text(tokens.get('output'))} out tokens"
            )
        if call.get("list_usd") is not None:
            spent.append(f"${call['list_usd']:.3f} at list price")
        if call.get("seconds"):
            spent.append(f"{float(call['seconds']):.0f} s")
        text=f" {verb} by {generator.get('model')} through {generator.get('backend')} {generator.get('backend_version') or ''}".rstrip()
        text+=f" on {str(call['at'])[:10]}" if call.get("at") else ""
        text+=f", one call for {shared} mutants" if shared>1 else ""
        text+=(f" ({', '.join(spent)})" if spent else "")+"."
        return text,[[label,f"semantic-mutants/{contract_id}/responses/{generator.get('call_id')}.json","raw"]]
    if generator.get("kind")=="agent":
        return f" {verb} by an agent session ({generator.get('model')}) from the same prompt.",[]
    return "",[]


def explorer_causes():
    causes={cause_id:{"label":label,"hint":hint} for entries in HEALTH_CAUSES.values() for cause_id,label,hint in entries}
    causes.update({"metric:"+name:{"label":label,"hint":hint} for name,(label,hint) in HEALTH_METRIC_CAUSES.items()})
    causes.update({cause_id:{"label":label,"hint":hint} for cause_id,(label,hint) in EXPLORER_CAUSES.items()})
    return causes


def explorer_test_links():
    """Where each test has its own pages: its Living Specification scenario, its evidence record and its exact Allure
    result. A scenario is found by its title on the page of its feature file; an ambiguous match links nowhere."""
    base=ROOT/"docs/_build/html"
    scenarios=[]
    for path in sorted((base/"specifications").rglob("*.html")):
        page=path.relative_to(base).as_posix()
        scenarios.extend((anchor,page) for anchor in re.findall(r'id="(living-scenario-[a-z0-9-]+)"',path.read_text()))
    allure={}
    for nodeid,rows in allure_monitor_index().items():
        if len(rows)==1 and rows[0].get("uuid"):
            allure[nodeid]="test-results/index.html#"+hashlib.md5(str(rows[0]["uuid"]).encode()).hexdigest()
    links={}
    for need in current_needs().values():
        nodeid=need.get("nodeid")
        if need.get("type")!="testcase" or not nodeid:
            continue
        spec=None
        title,feature=str(need.get("gherkin_scenario") or ""),str(need.get("gherkin_feature") or "")
        if title and feature:
            slug=re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")
            page_tail="/"+Path(feature).parent.name.replace("_","-")+"/"+Path(feature).stem.replace("_","-")+".html"
            hits=[(anchor,page) for anchor,page in scenarios if anchor.endswith("-"+slug) and page.endswith(page_tail)]
            if len(hits)==1:
                spec=hits[0][1]+"#"+hits[0][0]
        links[nodeid]={"spec":spec,"evidence":test_evidence_url(nodeid),"allure":allure.get(nodeid)}
    return links


def explorer_path_checks(row,cell):
    """How one retained path stands against its cell's target, property by property, as cell_state judges the paths
    it aggregates (every profile aggregates its paths with ALL)."""
    domain=ASSURANCE_DOMAIN
    representation=domain.representation_label(row.get("representation"))
    checks={
      "Representation":domain.minimum_representation_status([representation],domain.representation_label(cell.get("representation")),"ALL")[0],
      "Provenance":domain.quantified_status([str(row.get("provenance") or "UNKNOWN").upper() if row.get("provenance_scope")=="full_chain" else "UNKNOWN"],"COMPLETE","ALL"),
      "Producers":domain.quantified_status([str(row.get("producer_qualification") or "UNKNOWN").upper() if row.get("producer_qualification_scope")=="full_chain" else "UNKNOWN"],"QUALIFIED","ALL"),
      "Freshness":domain.quantified_status([str(row.get("freshness") or "UNKNOWN").upper()],"CURRENT","ALL"),
      "M&S":"N/A",
    }
    declared=cell.get("ms_validation_target") or cell.get("ms_validation")
    if representation=="Surrogate / simulated":
        if not declared:
            checks["M&S"]="UNKNOWN"
        elif domain.ms_label(str(declared))!="L0":
            checks["M&S"]=domain.minimum_ms_status([domain.ms_label(row.get("ms_validation"))],domain.ms_label(str(declared)),"ALL")[0]
    return checks


def explorer_clip(value,limit):
    value=str(value)
    return value if len(value)<=limit else value[:limit-1]+"…"


def explorer_verdict_note(contract_id,key):
    """What the verdict that counts says about one survivor, for its explorer row (ADR_0006)."""
    entry=((verdict_state().get(contract_id) or {}).get("items") or {}).get(str(key)) or {}
    verdict=entry.get("verdict")
    if not verdict:
        return ""
    by="the person" if verdict.get("by")=="person" else str(verdict.get("by"))+(f", confirmed by {verdict['reviewed_by']}" if verdict.get("reviewed_by") else "")
    reason=explorer_clip(" ".join(str(verdict.get("reason") or "").split()),260)
    if verdict["verdict"]=="pin":
        pin=entry.get("pin") or {}
        return f" Verdict by {by}: pin. {reason} "+(f"Pinned by {pin['path']}." if pin else "A pinning test is still to be written and kept.")
    if verdict["verdict"]=="escalate":
        return f" Verdict by {by}: escalated, it waits for you. {reason}"
    return f" Verdict by {by}: {verdict['verdict']}. {reason}"


def explorer_judgement_note(judged,rule):
    """What the survivor judgement found about a survivor, for its explorer row (ADR_0005)."""
    status=judged.get("status")
    if status=="found":
        witness=judged.get("witness") or {}
        author="the symbolic search" if witness.get("by")=="symbolic search" else f"{str(witness.get('by')).split(':',1)[-1]}, an assessor,"
        # Where the two outcomes differ, not their shared beginning.
        original,mutant=EQ.contrast(str(witness.get("original") or ""),str(witness.get("mutant") or ""),120)
        return (
          f" {'Test goal' if rule else 'Input'}: {explorer_clip(witness.get('display'),220)}: the original gives "
          f"{original}; the mutant gives {mutant}. "
          f"Found by {author} and confirmed by execution."
        )
    if status=="not-applicable":
        return f" Not judged: {judged.get('reason')}."
    parts=[]
    symbolic=judged.get("symbolic") or {}
    if symbolic.get("status") in {"none","exhausted"}:
        parts.append(
          f"the symbolic search found no input in {int(symbolic.get('paths') or 0)} paths"+(", having explored them all" if symbolic.get("status")=="exhausted" else "")
          +(f", trying plain values for {', '.join(judged['substituted'])} in place of the declared type" if judged.get("substituted") else "")
        )
    elif symbolic.get("status")=="error":
        parts.append("the symbolic search could not run ("+explorer_clip(symbolic.get("reason") or "",120)+")")
    elif symbolic.get("status")=="different":
        reasons=[item.get("reason") for item in judged.get("refuted") or [] if item.get("by")=="symbolic search"]
        parts.append("the symbolic search's inputs are refuted"+(f" ({explorer_clip(reasons[0],120)})" if reasons else ""))
    elif symbolic.get("status")=="timeout":
        parts.append("the symbolic search ran out of time")
    answered=[member for member in judged.get("members") or [] if member.get("verdict")]
    if answered:
        parts.append("the assessors answer "+", ".join(
          f"{str(member['member']).split(':',1)[-1]} {member['verdict']} ({float(member.get('confidence') or 0):.2f})" for member in answered
        ))
    elif judged.get("members"):
        parts.append("no assessor has answered yet")
    parts.extend(
      f"the input {str(item['by']).split(':',1)[-1]} proposed is refuted: {item.get('reason')}"
      for item in judged.get("refuted") or [] if item.get("by")!="symbolic search"
    )
    said=(" "+"; ".join(parts)[:1].upper()+"; ".join(parts)[1:]+".") if parts else ""
    if status=="likely-equivalent":
        return said+(
          f" Likely equivalent in what the judgement observes (returns, object state and exception types, not effects such as logging): "
          f"every assessor judges it equivalent above the calibrated {float(judged.get('threshold') or 0):.2f}. Advisory: "
          +("if you agree, suppress it with `# mutation: equivalent` and the reason." if rule else "if you agree, record the verdict with its reason.")
        )
    return said+" Unsure."+("" if judged.get("calibrated") or not answered else " The assessors are not calibrated, so they label nothing.")


def explorer_not_planted(actual):
    """How many would-be mutants of a class the arid-code rules kept out, by rule."""
    rules=actual.get("not_planted") or {}
    total=sum(int(count) for count in rules.values())
    if not total:
        return ""
    return f"{total} more sit in arid code and were not planted ("+", ".join(f"{rule} {count}" for rule,count in sorted(rules.items()))+")."


def explorer_mutant_change(mutant):
    """What the mutant changes, in code: the original and its replacement where both are short."""
    original,replacement=mutant.get("original") or "",mutant.get("replacement") or ""
    if mutant["operator"]=="statement":
        return "removed: "+original if original else mutant["description"]
    if mutant["operator"]=="body":
        return f"{mutant.get('qualname') or 'function'} body → {replacement}"
    if original and replacement and len(original)+len(replacement)<=110:
        return f"{original} → {replacement}"
    return mutant["description"]


def working_changed_lines(base_ref="main"):
    """Lines the working tree changes against its merge base with the base branch:
    the lines a pull request from this branch would change."""
    try:
        merge_base=subprocess.run(
          ["git","merge-base","HEAD",base_ref],cwd=ROOT,text=True,capture_output=True,check=True,
        ).stdout.strip()
        diff=subprocess.run(
          ["git","diff","--unified=0","--no-color",merge_base,"--","src"],cwd=ROOT,text=True,capture_output=True,check=True,
        ).stdout
    except (subprocess.CalledProcessError,FileNotFoundError):
        return set(),None
    changed=set()
    current=None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current=line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@") and current:
            match=re.search(r"\+(\d+)(?:,(\d+))?",line)
            if match:
                start,count=int(match.group(1)),int(match.group(2) or 1)
                changed.update((current,number) for number in range(start,start+count))
    return changed,merge_base


def explorer_payload(health_payload):
    rows=health_payload["rows"]
    req_facts=json.loads(REQ_MONITOR_FACTS_PATH.read_text())
    upper_facts=json.loads(UPPER_ASSURANCE_FACTS_PATH.read_text())
    contracts=req_facts.get("contracts") or {}
    policy=req_facts.get("policy") or {}
    descriptions=policy.get("fault_class_descriptions") or {}
    plans=implementation_fault_plans()
    semantic_actual=semantic_mutant_actual(plans)
    triage_actual=survivor_triage_actual()
    tests=explorer_test_links()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    head=git_sha()
    changed_lines,merge_base=working_changed_lines()
    # The product is PRODUCT_SYSTEM here, as on its monitor, so that its monitor can link to its items.
    product_id=ASSURANCE_REGISTRY.PRODUCT_SYSTEM_ID
    root_id=rows[0]["id"]
    tree=[
      {
        "id":product_id if row["id"]==root_id else row["id"],"level":row["level"],
        "parent":product_id if row.get("parent")==root_id else row.get("parent") or "",
        "label":row["label"],"short":row.get("short") or row["label"],"href":row["layers"]["overall"]["href"],
      }
      for row in rows
    ]
    href={row["id"]:row["href"] for row in tree}
    items=[]
    objects={}

    def test_links(nodeid,source_url=None):
        found=tests.get(nodeid) or {}
        links=[[label,found[key],kind] for key,label,kind in (("spec","Spec","semantic"),("evidence","Evidence","semantic"),("allure","Allure","raw")) if found.get(key)]
        if source_url:
            links.append(["Source",source_url,"raw"])
        return links

    def test_name(nodeid):
        return str(nodeid).split("::")[-1]

    for contract_id,contract in contracts.items():
        target=contract.get("target") or {}
        profile=target.get("profile_url") or target.get("source_url") or "verification-profiles/index.html"
        model=target.get("model_url") or "test-plan.html"
        actual_rows=contract.get("coverage_actual") or {}
        # Coverage: every required path of every criterion, found or missing, in the profile's order.
        for cell in target.get("coverage") or []:
            for criterion in cell.get("items") or []:
                object_id=f"criterion|{contract_id}|{criterion}"
                named=list((cell.get("item_path_ids") or {}).get(criterion) or [])
                count=len(named) or int((cell.get("item_path_counts") or {}).get(criterion,1))
                here=[row for row in actual_rows.get(criterion,[]) if row.get("level")==cell["level"] and row.get("boundary")==cell["boundary"]]
                elsewhere=[row for row in actual_rows.get(criterion,[]) if row not in here]
                objects[object_id]={
                  "kind":"criterion","owner":contract_id,"name":criterion,
                  "what":(target.get("item_descriptions") or {}).get(criterion,""),
                  "level":cell["level"],"boundary":cell["boundary"],"paths":count,
                  "links":[["Profile",profile,"semantic"],["Test model",model,"semantic"]],
                }
                slots=[]
                if named:
                    by_path=defaultdict(list)
                    for row in here:
                        by_path[str(row.get("coverage_path") or "").strip()].append(row)
                    slots=[(path,(by_path.get(path) or [None])[0]) for path in named]
                    # A path the profile does not name, or a second test on one path, keeps its criterion from passing.
                    extra=[row for path,found in by_path.items() for row in (found if path not in named else found[1:])]
                else:
                    slots=[("",here[index] if index<len(here) else None) for index in range(count)]
                    extra=here[count:]
                for index,(path,row) in enumerate(slots+[(str(row.get("coverage_path") or ""),row) for row in extra]):
                    unexpected=index>=len(slots)
                    causes=[]
                    layers=["coverage"]
                    attrs={"level":cell["level"],"boundary":cell["boundary"]}
                    if row is None:
                        status,state="fail","Missing"
                        causes.append("uncovered")
                        note="No retained test covers this path."
                        if elsewhere:
                            note+=" A test for this criterion ran at another level or boundary: "+", ".join(sorted({test_name(other.get("nodeid")) for other in elsewhere}))+"."
                        name=path or "Required path"
                        links=[]
                    else:
                        passed=row.get("result")=="passed"
                        checks=explorer_path_checks(row,cell)
                        # What fails outright makes the path fail; what cannot be judged makes it unknown, with its cause
                        # all the same: the Health Map paints both red.
                        unknown=[]
                        if unexpected:
                            causes.append("unexpected")
                        if not passed:
                            causes.append("uncovered")
                            layers.append("execution")
                        for metric,value in checks.items():
                            if value=="NOT MET":
                                causes.append("metric:"+metric)
                            elif value=="UNKNOWN":
                                unknown.append("metric:"+metric)
                        if any(value in {"NOT MET","UNKNOWN"} for value in checks.values()):
                            layers.append("evidence")
                        status="fail" if causes else ("unknown" if unknown else "pass")
                        causes+=unknown
                        state="Unexpected" if unexpected else ("Failed" if not passed else ("Passed" if status=="pass" else "Unknown"))
                        name=path or test_name(row.get("nodeid"))
                        note=(test_name(row.get("nodeid"))+" · " if path else "")+str(row.get("kind") or "test").upper()
                        attrs.update({
                          "representation":row.get("representation"),"ms":row.get("ms_validation"),
                          "freshness":row.get("freshness"),"provenance":row.get("provenance"),
                          "qualification":row.get("producer_qualification"),
                          "checks":{metric:value for metric,value in checks.items() if value!="N/A"},
                        })
                        links=test_links(row.get("nodeid"),row.get("source_url"))
                    items.append({
                      "id":f"path|{contract_id}|{criterion}|{path if path and not unexpected else index}","kind":"path","owner":contract_id,"object":object_id,
                      "layers":layers,"status":status,"state":state,"causes":causes,"name":name,"note":note,
                      "attrs":attrs,"producers":list((row or {}).get("producer_ids") or []),"links":links,
                    })
        # Tests that verify the contract outside every required case prove no case, but their failure fails it.
        for row in contract.get("linked_outside_profile") or []:
            failed=row.get("result")=="failed"
            nodeid=str(row.get("nodeid") or "")
            items.append({
              "id":f"unbound|{contract_id}|{nodeid}","kind":"unbound","owner":contract_id,"object":"",
              "layers":["coverage","execution"] if failed else ["coverage"],
              "status":"fail" if failed else "na","state":"Failed" if failed else "Counts for no case",
              "causes":["unbound"] if failed else [],"name":test_name(nodeid),
              "note":"It verifies the contract, but its profile names no case it proves.",
              "attrs":{},"producers":[],"links":test_links(nodeid,repo_blob_url(nodeid.split("::")[0],head)),
            })
        # Fault model: every required and optional class, and under an implementation class its mutants.
        classes=(contract.get("fault_actual") or {}).get("classes") or {}
        listed=set()
        for group in target.get("fault_groups") or []:
            object_id=f"group|{contract_id}|{group['label']}"
            objects[object_id]={"kind":"group","owner":contract_id,"name":group["label"],"what":group.get("rationale") or ""}
            for spec in group.get("items") or []:
                if spec.get("state") not in {"required","optional"}:
                    continue
                listed.add(spec["id"])
                actual=classes.get(spec["id"]) or {}
                # The monitors' own verdict: caught, missed, undecided (UNKNOWN) or not challenged.
                verdict=ASSURANCE_DOMAIN.class_verdict(actual)
                word={"caught":"Caught","missed":"Missed","unknown":"Undecided"}.get(verdict,"Not challenged")
                cause=None
                if spec["state"]=="required":
                    status={"caught":"pass","unknown":"unknown"}.get(verdict,"fail")
                    cause=None if verdict=="caught" else health_fault_cause(actual or None,plans.get(contract_id))
                else:
                    status,word="na","Optional · "+word.lower()
                items.append({
                  "id":f"fault|{contract_id}|{spec['id']}","kind":"fault","owner":contract_id,"object":object_id,
                  "layers":["faults"],"status":status,"state":word,"causes":[cause] if cause else [],
                  "name":spec["id"],"what":descriptions.get(spec["id"]) or spec.get("description") or "",
                  "note":" ".join(filter(None,[str(actual.get("basis") or ""),explorer_not_planted(actual)])),
                  "attrs":{"group":group["label"],"class":spec["id"],"applicability":spec["state"]},
                  "producers":list(actual.get("producer_ids") or []),
                  "links":[["Profile",profile,"semantic"],["Test plan","test-plan.html#test-plan-fault-model","semantic"]],
                })
        report_path=IMPL_FAULT_DIR/f"{contract_id}.gremlins.json"
        if report_path.exists() and contract_id in plans:
            report=json.loads(report_path.read_text())
            # The rows say what the class counts: a survivor a verdict judged equivalent or irrelevant is suppressed.
            for mutant in IMPL_FAULTS.suppress_by_verdict(IMPL_FAULTS.contract_mutants(plans[contract_id],report,ROOT),verdict_suppressions(contract_id)):
                klass=mutant["class"]
                # A result that no longer counts (stale, blocked, unqualified) shows on its class, not as mutants.
                if klass not in listed or (classes.get(klass) or {}).get("campaign_state")!="current":
                    continue
                outcome=mutant["outcome"]
                suppression=mutant.get("suppression") or {}
                status,word,causes,note=EXPLORER_MUTANT_OUTCOMES[outcome]
                triaged=None
                if outcome=="suppressed" and suppression.get("verdict"):
                    word=f"Suppressed · {suppression['verdict']}"
                    confirmed=f" (confirmed by {suppression['reviewed_by']})" if suppression.get("reviewed_by") else ""
                    note=f"Judged {suppression['verdict']} by {suppression.get('by')}{confirmed}: "+explorer_clip(" ".join(str(suppression.get("reason") or "").split()),300)
                elif outcome=="suppressed":
                    word=f"Suppressed · {suppression.get('category') or 'pardoned'}"
                    note=str(suppression.get("reason") or "Suppressed by a pragma.")
                elif outcome=="survived":
                    note=f"{mutant['selected_tests']} of its tests run this line and none fails."
                    triaged=((triage_actual.get(contract_id) or {}).get("rows") or {}).get(str(mutant["fingerprint"]))
                    if triaged:
                        note+=explorer_judgement_note(triaged,rule=True)
                    note+=explorer_verdict_note(contract_id,mutant["fingerprint"])
                elif outcome=="notreached" and mutant.get("run_skipped"):
                    note+=" The pull-request diff does not run uncovered mutants."
                elif outcome=="notreached":
                    note+=explorer_verdict_note(contract_id,mutant["fingerprint"])
                source=Path(mutant["source"])
                line=int(mutant["line"])
                change=explorer_mutant_change(mutant)
                items.append({
                  "id":f"mutant|{contract_id}|{mutant['fingerprint']}","kind":"mutant","owner":contract_id,
                  "object":f"fault|{contract_id}|{klass}","layers":["faults"],"status":status,"state":word,"causes":causes,
                  "name":f"{source.name}:{line}"+(f" · {mutant['qualname']}" if mutant.get("qualname") and mutant["qualname"]!="<module>" else ""),
                  "what":change,"note":note,
                  "attrs":{
                    "group":"Implementation","class":klass,"operator":mutant["operator"],"origin":"rule",
                    **({"judgement":triaged["status"]} if outcome=="survived" and triaged else {}),
                    **({"diff":"yes"} if (mutant["source"],line) in changed_lines else {}),
                  },
                  "producers":list(IMPL_FAULTS.PRODUCERS),
                  "links":[
                    ["Source",repo_blob_url(mutant["source"],campaign.get("head_sha") or head)+f"#L{line}","raw"],
                    *([["Mutation report",f"mutation-report.html#mutant/{mutant['source']}","raw"]] if MUTATION_REPORT_PAGE.exists() else []),
                  ],
                })
        # Semantic mutants, frozen proposals for the risks the profile names, under their class.
        semantic=semantic_actual.get(contract_id) or {}
        by_id={row["id"]:row for row in semantic.get("results") or []}
        calls=semantic.get("calls") or {}
        per_call=Counter((proposal.get("generator") or {}).get("call_id") for proposal in semantic.get("proposals") or [])
        for proposal in semantic.get("proposals") or []:
            klass=proposal["class"]
            if klass not in listed:
                continue
            result=by_id.get(proposal["id"])
            outcome=(result or {}).get("outcome") or ("stale" if semantic.get("state")=="stale" else "undecided")
            status,word,causes=EXPLORER_SEMANTIC_OUTCOMES[outcome]
            note=str((result or {}).get("reason") or semantic.get("reason") or "")
            note=note[:1].upper()+note[1:]+("" if note.endswith(".") else ".")
            found=(result or {}).get("differential") or {}
            judged=(result or {}).get("judgement") or {}
            if found.get("found"):
                clip=lambda value,limit:(value if len(value)<=limit else value[:limit-1]+"…")
                note+=(
                  f" Input: {clip(str(found.get('input')),220)}. The original gives {clip(str(found.get('original')),140)};"
                  f" the mutant gives {clip(str(found.get('mutant')),140)}."
                )
                if found.get("by"):
                    note+=" Found by "+("the symbolic search" if found["by"]=="symbolic search" else f"{str(found['by']).split(':',1)[-1]}, an assessor,")+" and confirmed by execution."
            elif outcome=="undecided" and judged:
                note+=explorer_judgement_note(judged,rule=False)
            if outcome in {"distinguished","undecided"}:
                note+=explorer_verdict_note(contract_id,proposal["id"])
            draft=(result or {}).get("draft") or {}
            source,_,qualname=proposal["target"].partition("::")
            group_label=next((group["label"] for group in target.get("fault_groups") or [] if any(item["id"]==klass for item in group.get("items") or [])),"")
            origin_note,origin_links=explorer_generation_note(
              contract_id,proposal.get("generator") or semantic.get("generator") or {},calls,"Generated","Model answer",
              per_call.get((proposal.get("generator") or {}).get("call_id"),1),
            )
            links=[["Patch",f"semantic-mutants/{contract_id}/{proposal['id']}.diff","raw"],*origin_links,["Source",repo_blob_url(source,head),"raw"]]
            if draft:
                links.insert(1,["Draft test",f"semantic-mutants/{contract_id}/{proposal['id']}.test.py","raw"])
                note+=" Draft test "+(f"kept: in the project's style it passes on the original {SEMANTIC.DRAFT_PASSES} times and fails on the mutant." if draft.get("accepted") else "rejected: "+SEMANTIC.draft_rejection(draft)+".")
                draft_note,draft_links=explorer_generation_note(contract_id,(semantic.get("draft_provenance") or {}).get(proposal["id"]) or {},calls,"The draft was written","Draft answer")
                note+=draft_note
                links[2:2]=draft_links
            note+=origin_note
            items.append({
              "id":f"mutant|{contract_id}|semantic:{proposal['id']}","kind":"mutant","owner":contract_id,
              "object":f"fault|{contract_id}|{klass}","layers":["faults"],"status":status,"state":word,"causes":causes,
              "name":f"{proposal['id']} · {qualname}","what":proposal.get("risk") or "","note":note.strip(),
              "attrs":{
                "group":group_label,"class":klass,"operator":"semantic","origin":"semantic",
                **({"draft":"kept" if draft.get("accepted") else "rejected"} if draft else {}),
                **({"judgement":judged["status"]} if judged.get("status") else {}),
              },
              "producers":list(SEMANTIC_PRODUCERS),"links":links,
            })
        # A selected target without any semantic mutant: its class stays undecided until one is generated.
        for selection in semantic.get("missing") or []:
            klass=selection["class"]
            if klass not in listed:
                continue
            source,_,qualname=selection["target"].partition("::")
            attempts=selection.get("attempts") or []
            group_label=next((group["label"] for group in target.get("fault_groups") or [] if any(item["id"]==klass for item in group.get("items") or [])),"")
            note=(
              f"The last generation, on {str(attempts[-1].get('at'))[:10]}, made no mutant: "+"; ".join(
                f"{row['backend']}:{row['model']} {EXPLORER_GENERATION_OUTCOMES.get(row['outcome'],row['outcome'])}"
                +(f" ({row['reason']})" if row.get("reason") else "")
                for row in attempts
              )+"."
              if attempts else "No generation has run for this target yet."
            )
            items.append({
              "id":f"mutant|{contract_id}|semantic-target:{selection['target']}","kind":"mutant","owner":contract_id,
              "object":f"fault|{contract_id}|{klass}","layers":["faults"],"status":"unknown","state":"Not generated","causes":["generate"],
              "name":f"{qualname} · up to {selection['budget']}","what":selection["risk"],"note":note,
              "attrs":{"group":group_label,"class":klass,"operator":"semantic","origin":"semantic"},
              "producers":list(SEMANTIC_PRODUCERS),"links":[["Source",repo_blob_url(source,head),"raw"]],
            })
        # What a requirement needs from its technical requirements.
        for treq_id in target.get("required_treqs") or []:
            child=contracts.get(treq_id)
            state=ASSURANCE_DOMAIN.contract_domain_state(child,policy) if child else {"overall":"UNKNOWN","coverage":"UNKNOWN","fault":"UNKNOWN"}
            status=EXPLORER_STATUS.get(state["overall"],"unknown")
            items.append({
              "id":f"support|{contract_id}|{treq_id}","kind":"support","owner":contract_id,"object":"","layers":[],
              "status":status,"state":{"pass":"Passes","fail":"Fails","na":"N/A"}.get(status,"Unknown"),
              "causes":["support"] if status=="fail" else [],"name":treq_id,"what":(child or {}).get("title") or treq_id,
              "note":"Coverage "+EXPLORER_WORD.get(state["coverage"],"UNKNOWN")+" · Fault model "+EXPLORER_WORD.get(state["fault"],"UNKNOWN"),
              "attrs":{"child":treq_id},"producers":[],"links":[["Opens",href[treq_id],"semantic"]] if href.get(treq_id) else [],
            })

    # Goals, capabilities and the product: their own integration and validation checks, and what they rest on.
    entities=[("feature",entity_id,entity) for entity_id,entity in (upper_facts.get("features") or {}).items()]
    entities+=[("goal",entity_id,entity) for entity_id,entity in (upper_facts.get("goals") or {}).items()]
    entities.append(("product",ASSURANCE_REGISTRY.PRODUCT_SYSTEM_ID,upper_facts.get("product_system") or {}))
    for level,entity_id,entity in entities:
        owner=product_id if level=="product" else entity_id
        page=href.get(owner,"")
        for section in DEPTH_UPPER_SECTIONS[level]:
            criteria=(entity.get(section) or {}).get("criteria") or []
            if not criteria:
                continue
            object_id=f"section|{owner}|{section}"
            objects[object_id]={
              "kind":"section","owner":owner,"name":EXPLORER_SECTION_LABELS.get(section,section),"what":"",
              "links":[[EXPLORER_SECTION_LABELS.get(section,section),page+"#"+upper_section_anchor(entity_id,section),"semantic"]] if page else [],
            }
            for criterion in criteria:
                status=EXPLORER_STATUS.get(criterion.get("status"),"unknown")
                causes=[]
                if status!="pass":
                    if criterion.get("execution_status") not in {None,"MET"}:
                        causes.append("scenario")
                    for key,metric in (("classification","Representation"),("freshness","Freshness"),("producer_qualification","Producers")):
                        if (criterion.get(key) or {}).get("status")=="NOT MET":
                            causes.append("metric:"+metric)
                    if status in {"fail","unknown"} and not causes:
                        causes.append("metric:Validation" if section.endswith("validation") else "metric:Integration")
                runs=criterion.get("rows") or []
                items.append({
                  "id":f"check|{owner}|{criterion.get('id')}","kind":"check","owner":owner,"object":object_id,
                  "layers":["assurance"],"status":status,
                  "state":{"pass":"Passes","fail":"Fails","na":"N/A"}.get(status,"Unknown"),"causes":causes,
                  "name":str(criterion.get("id") or ""),"what":str(criterion.get("success_criterion") or ""),
                  "note":(f"{int(criterion.get('passed_executions') or 0)} of {int(criterion.get('required_executions') or 0)} required runs passed"
                          +("" if runs else "; no scenario ran")),
                  "attrs":{"level":(runs[0].get("level") if runs else None),"boundary":(runs[0].get("boundary") if runs else None),"representation":(runs[0].get("representation") if runs else None),"section":section},
                  "producers":sorted({producer for run in runs for producer in run.get("producer_ids") or []}),
                  "links":[link for run in runs for link in test_links(run.get("nodeid"),repo_blob_url(run.get("source_path"),head) if run.get("source_path") else None)]
                  +([["Profile",criterion["profile_url"],"semantic"]] if criterion.get("profile_url") else []),
                })
        for child in (entity.get(EXPLORER_SUPPORT_SECTIONS[level]) or {}).get("children") or []:
            status=EXPLORER_STATUS.get(child.get("status"),"unknown")
            items.append({
              "id":f"support|{owner}|{child.get('id')}","kind":"support","owner":owner,"object":"","layers":[],
              "status":status,"state":{"pass":"Passes","fail":"Fails","na":"N/A"}.get(status,"Unknown"),
              "causes":["support"] if status=="fail" else [],"name":str(child.get("id") or ""),"what":str(child.get("title") or ""),
              "note":"","attrs":{"child":child.get("id")},"producers":[],
              "links":[["Opens",href.get(child.get("id")) or child.get("url") or "","semantic"]] if (href.get(child.get("id")) or child.get("url")) else [],
            })

    # The evidence producers, each with the contracts whose evidence it made.
    users=defaultdict(set)
    for item in items:
        for producer_id in item.get("producers") or []:
            users[producer_id].add(item["owner"])
    qualification=load_evidence_qualification()
    records=current_needs()
    qualified_now=qualification_is_current(qualification)
    for producer_id,record in sorted((qualification.get("producers") or {}).items()):
        need=records.get(producer_id) or {}
        raw=str(record.get("status") or "UNKNOWN").upper() if qualified_now else "UNKNOWN"
        status="pass" if raw=="QUALIFIED" else ("fail" if raw=="NOT QUALIFIED" else "unknown")
        items.append({
          "id":f"producer|{producer_id}","kind":"producer","owner":"","object":"","layers":["evidence"],
          "status":status,"state":{"pass":"Qualified","fail":"Not qualified"}.get(status,"Unknown"),
          "causes":["metric:Producers"] if status!="pass" else [],
          "name":need.get("title") or producer_id.removeprefix("PRODUCER_").replace("_"," ").capitalize(),
          "what":need.get("producer_purpose") or record.get("intended_use") or "",
          "note":"False-green control: "+str(record.get("false_green_control") or "none recorded"),
          "attrs":{"producer":producer_id,"users":sorted(users.get(producer_id) or ())},"producers":[],
          "links":([["Evidence trust","evidence-trust.html#"+producer_id,"semantic"]] if need else [])+[["Qualification","evidence-confidence-qualification.json","raw"]],
        })
    return {
      "rows":tree,"items":items,"objects":objects,"causes":explorer_causes(),
      "levels":req_facts.get("levels") or [],"boundaries":req_facts.get("boundaries") or [],
      "run":(health_payload.get("insights") or {}).get("run") or {},
      # "In this change": the lines this branch changes against its merge base with main.
      "change_base":{"base":"main","merge_base":merge_base,"lines":len(changed_lines)},
    }


EXPLORER_RUN_SNAPSHOTS=ROOT/"test-results/explorer/runs"
EXPLORER_FAILING={"fail","unknown"}


def explorer_changes(before,after):
    """Up: an item that fails now and did not before; down: one that failed and passes now; new: one the earlier run did
    not have. What the earlier run had and this one does not is only counted."""
    return {"items":{
      "up":sorted(item_id for item_id,status in after.items() if item_id in before and status in EXPLORER_FAILING and before[item_id] not in EXPLORER_FAILING),
      "down":sorted(item_id for item_id,status in after.items() if item_id in before and status not in EXPLORER_FAILING and before[item_id] in EXPLORER_FAILING),
      "new":sorted(item_id for item_id in after if item_id not in before),
      "gone":sum(1 for item_id in before if item_id not in after),
    }}


def render_explorer_page(health_payload):
    """The Verification Explorer, from the facts the Health Map was drawn from, with what changed since the previous
    retained run."""
    payload=explorer_payload(health_payload)
    values={item["id"]:item["status"] for item in payload["items"]}
    payload["delta"]=run_delta(EXPLORER_RUN_SNAPSHOTS,"explorer-run-1",payload["run"],values,explorer_changes)
    article=MAP_PAGES.explorer_article(stable_json(payload))
    EXPLORER_PAGE.write_text(portal_map_shell(EXPLORER_PAGE,"Verification Explorer",article))
    return payload


def history_changes_text(owner_id,items,delta):
    """What changed for one owner since the previous retained run, in the explorer's words."""
    baseline=delta.get("baseline") or {}
    if not baseline:
        return "No earlier retained run to compare with yet."
    changes=(delta.get("layers") or {}).get("items") or {}
    own={item["id"] for item in items if item.get("owner")==owner_id}
    counts=[(len(own & set(changes.get(key) or [])),word) for key,word in (("up","fail now"),("down","pass now"),("new","new"))]
    since="the run of "+str(baseline.get("started_at") or "")[:16].replace("T"," ")
    parts=[f"{count} {word}" for count,word in counts if count]
    return ("Since "+since+": "+" · ".join(parts)+".") if parts else f"Nothing changed since {since}."


def patch_monitor_history(explorer):
    """Write into every monitor's History what changed for its owner since the previous retained run."""
    items=explorer.get("items") or []
    delta=explorer.get("delta") or {}
    pattern=re.compile(r'(<span class="history-changes" data-history-owner="([A-Z0-9_]+)">)[^<]*(</span>)')
    base=ROOT/"docs/_build/html"
    for path in [*base.glob("contract-evidence-*.html"),*base.glob("assurance-*.html"),ASSURANCE_PAGE]:
        if not path.is_file():
            continue
        text=path.read_text()
        if 'class="history-changes"' not in text:
            continue
        text=pattern.sub(lambda match:match.group(1)+html_escape(history_changes_text(match.group(2),items,delta))+match.group(3),text)
        path.write_text(text)


def patch_allure_scope_tags():
    if not ALLURE_REPORT_PAGE.exists():
        return
    needs, nodes, parent, _children, _ordered, _descendants = assurance_map_graph()
    tests = map_test_rows(needs)
    test_by_nodeid = {row["nodeid"]: row for row in tests}
    scope_tags = {}
    for nodeid, row in test_by_nodeid.items():
        tags = set()
        for contract_id in row.get("verifies") or []:
            current = contract_id
            while current in nodes:
                tags.add("TF_SCOPE__" + current)
                current = parent.get(current)
                if not current:
                    break
        kind = str(row.get("verification_kind") or "unknown").upper()
        tags.add("TF_LAYER__" + re.sub(r"[^A-Z0-9]+", "_", kind).strip("_"))
        scope_tags[nodeid] = sorted(tags)

    report_ids = {}
    for nodeid, rows in allure_monitor_index().items():
        if len(rows) != 1 or not rows[0].get("uuid"):
            continue
        report_ids[nodeid] = hashlib.md5(str(rows[0]["uuid"]).encode()).hexdigest()

    text = ALLURE_REPORT_PAGE.read_text()

    def embedded(name):
        match = re.search(r'd\("' + re.escape(name) + r'","([A-Za-z0-9+/=]+)"\)', text)
        if not match:
            return None, None
        try:
            payload = json.loads(__import__("base64").b64decode(match.group(1)))
        except Exception:
            return match, None
        return match, payload

    replacements = []
    all_tags = set()
    for nodeid, tags in scope_tags.items():
        report_id = report_ids.get(nodeid)
        if not report_id:
            continue
        name = f"data/test-results/{report_id}.json"
        match, payload = embedded(name)
        if not match or payload is None:
            continue
        labels = list(payload.get("labels") or [])
        existing = {(str(row.get("name") or ""), str(row.get("value") or "")) for row in labels}
        for tag in tags:
            all_tags.add(tag)
            if ("tag", tag) not in existing:
                labels.append({"name": "tag", "value": tag})
        payload["labels"] = labels
        grouped = dict(payload.get("groupedLabels") or {})
        grouped_tags = list(grouped.get("tag") or [])
        for tag in tags:
            if tag not in grouped_tags:
                grouped_tags.append(tag)
        grouped["tag"] = grouped_tags
        payload["groupedLabels"] = grouped
        encoded = __import__("base64").b64encode(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        ).decode()
        replacements.append((match.span(1), encoded))

    filters_match, filters = embedded("widgets/tree-filters.json")
    if filters_match and filters is not None:
        filters["tags"] = sorted(set(filters.get("tags") or []) | all_tags)
        encoded = __import__("base64").b64encode(
            json.dumps(filters, separators=(",", ":"), ensure_ascii=False).encode()
        ).decode()
        replacements.append((filters_match.span(1), encoded))

    for (start, end), encoded in sorted(replacements, reverse=True):
        text = text[:start] + encoded + text[end:]
    ALLURE_REPORT_PAGE.write_text(text)


def regenerate_verification_maps():
    patch_allure_scope_tags()
# TERNFORGE-P34-CLEAN-MAPS-END


def portal_nav_item(label,href,active=False,kind=""):
    active_class=" current active" if active else " "
    target="#" if active else href
    marker=f' data-ternforge-p22-nav="{kind}"' if kind else ""
    return (
      f'\n<li class="nav-item{active_class}"{marker}>\n'
      f'  <a class="nav-link nav-internal" href="{target}">\n'
      f'    {html_escape(label)}\n'
      f'  </a>\n'
      f'</li>\n'
    )

def patch_navigation_text(text,current=None):
    # An item was inserted with its own leading and trailing newline, so removing it whole restores the text before it
    # and patching an already patched page changes nothing.
    text=re.sub(
      r'\n<li class="nav-item[^"]*" data-ternforge-p22-nav="(?:health|mutation)">.*?</li>\n',
      "",text,flags=re.DOTALL
    )
    nav_prefix=text.split('<main id="main-content"',1)[0]
    health_pattern=re.compile(
      r'(<li class="nav-item[^"]*">\s*<a class="nav-link nav-internal" href="(?:verification-health-map\.html|#)">\s*Verification Health Map\s*</a>\s*</li>)'
    )
    verification_pattern=re.compile(
      r'(<li class="nav-item[^"]*">\s*<a class="nav-link nav-internal" href="verification\.html">\s*Verification\s*</a>\s*</li>)'
    )
    # Mutation Analysis and mutmut are retired (ADR_0003): the Verification Explorer lists the mutants that judge the
    # Fault model. An old item is removed above; a page whose navigation lacks the Health Map gets it after Verification.
    if health_pattern.search(nav_prefix):
        return text
    health_item=portal_nav_item(
      "Verification Health Map","verification-health-map.html",
      active=current=="health",kind="health"
    )
    return verification_pattern.sub(lambda m:m.group(1)+health_item,text)


PROBE_SCRATCH_DIR=Path(tempfile.gettempdir())/"ternforge-probe-scratch"


def probe_env(env=None):
    """Keep probe pytest sessions from rewriting the retained run's input snapshot.

    tests/conftest.py snapshots verification inputs at every session start; a probe
    that runs pytest in the repository must write that snapshot elsewhere, or the
    retained freshness baseline silently becomes "whatever is on disk now".
    """
    PROBE_SCRATCH_DIR.mkdir(parents=True,exist_ok=True)
    result=dict(os.environ if env is None else env)
    result["TERNFORGE_EVIDENCE_RUN_INPUTS"]=str(PROBE_SCRATCH_DIR/"probe-run-inputs.json")
    return result


def run_checked(command,*,cwd=ROOT,env=None):
    completed=subprocess.run(
      command,cwd=cwd,env=probe_env(env),text=True,
      stdout=subprocess.PIPE,stderr=subprocess.STDOUT
    )
    if completed.returncode:
        tail="\n".join(completed.stdout.splitlines()[-80:])
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(map(str,command))}\n{tail}")
    return completed.stdout


def free_port():
    sock=socket.socket()
    try:
        sock.bind(("127.0.0.1",0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def probe_invalid_config_specification_fault():
    """Challenge the exact REQ scenario with a plausible wrong public outcome."""
    from gherkin.parser import Parser

    feature=ROOT/"features/responses/public_contract.feature"
    original=feature.read_text()
    old="      Then it fails with a configuration error\n"
    new="      Then it fails with a provider error\n"
    if original.count(old)!=1:
        raise RuntimeError("REQ_INVALID_CONFIGURATION_ERRORS Gherkin outcome step is no longer unique")
    Parser().parse(original)
    mutant_text=original.replace(old,new,1)
    Parser().parse(mutant_text)
    with tempfile.TemporaryDirectory(prefix="ternforge-spec-fault-") as temp_dir:
        temp=Path(temp_dir)
        shutil.copy2(ROOT/"pyproject.toml",temp/"pyproject.toml")
        for name in ("src","tests","features"):
            shutil.copytree(ROOT/name,temp/name)
        (temp/"features/responses/public_contract.feature").write_text(mutant_text)
        env=os.environ.copy()
        env["PYTHONPATH"]=f"{temp/'src'}:{temp}"
        completed=subprocess.run(
          [
            str(ROOT/".venv/bin/pytest"),"-q",
            "tests/llm_router/bdd/responses/test_public_contract.py::test_invalid_model_configuration_surfaces_as_a_configuration_error",
            "--no-cov",
          ],
          cwd=temp,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        )
    detected=(
      completed.returncode!=0
      and "ConfigurationError" in completed.stdout
      and "ProviderError" in completed.stdout
    )
    return {
      "engine":"Cucumber Gherkin parser + pytest-bdd",
      "mode":"scenario outcome negative-control mutation",
      "generated":1,
      "detected":1 if detected else 0,
      "score":100.0 if detected else 0.0,
      "target":"REQ_INVALID_CONFIGURATION_ERRORS · Then outcome",
      "fault_family":"wrong public error category",
      "mutation":"Then it fails with a configuration error → Then it fails with a provider error",
      "ast_validated":True,
      "native_metadata":False,
      "note":"Agentic Test Forge was also validated in the pilot (6/6 on a Scenario Outline), but it mutates Examples cells only. This Requirement is a simple Scenario, so its requirement-specific specification challenge uses the official Gherkin parser plus pytest-bdd rather than pretending ATF produced a mutant it cannot generate.",
      "output_tail":"\n".join(completed.stdout.splitlines()[-16:]),
    }


def probe_invalid_config_architecture_fault():
    baseline=run_checked([str(ROOT/".venv/bin/lint-imports"),"--no-cache"])
    match=re.search(r"Contracts:\s+(\d+) kept,\s+(\d+) broken",baseline)
    with tempfile.TemporaryDirectory(prefix="ternforge-config-arch-") as temp_dir:
        temp=Path(temp_dir)
        shutil.copy2(ROOT/"pyproject.toml",temp/"pyproject.toml")
        for name in ("src","tests","examples"):
            shutil.copytree(ROOT/name,temp/name)
        mutant=temp/"src/llm_router/_internal/config/validation.py"
        mutant.write_text(
          mutant.read_text()
          +"\nfrom llm_router._internal.providers import registry as _provider_registry"
          +"  # intentional REQ_INVALID_CONFIGURATION_ERRORS architecture mutant\n"
        )
        env=os.environ.copy()
        env["PYTHONPATH"]=f"{temp/'src'}:{temp}"
        completed=subprocess.run(
          [str(ROOT/".venv/bin/lint-imports"),"--no-cache"],
          cwd=temp,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        )
    detected=(
      completed.returncode!=0
      and "Private implementation must stay layered BROKEN" in completed.stdout
      and "config.validation" in completed.stdout
      and "providers.registry" in completed.stdout
    )
    return {
      "engine":"Import Linter",
      "mode":"requirement-specific architecture negative control",
      "baseline_kept":int(match.group(1)) if match else None,
      "baseline_broken":int(match.group(2)) if match else None,
      "generated":1,
      "detected":1 if detected else 0,
      "score":100.0 if detected else 0.0,
      "target":"config.validation → providers.registry forbidden lower-to-upper dependency",
      "fault_family":"wrong architecture boundary",
      "native_metadata":True,
      "contract_id":"private-core-layering",
      "output_tail":"\n".join(completed.stdout.splitlines()[-24:]),
    }


def _install_openrouter_base_url(base_url):
    from dataclasses import replace

    from llm_router import Provider, get_config, install_config

    original=get_config()
    provider_base_urls=dict(original.catalog.provider_base_urls)
    provider_base_urls[Provider.OPENROUTER]=f"{base_url}/v1"
    install_config(
      replace(
        original,
        catalog=replace(original.catalog,provider_base_urls=provider_base_urls),
      )
    )
    return original


def probe_invalid_config_interface_isolation():
    from llm_router import install_config
    from tests.llm_router.support.fault_server import (
        ScriptedHTTPServer,
        ScriptedResponse,
    )
    from tests.llm_router.support.workers.error_boundary import (
        run_error_boundary_inprocess,
    )
    from tests.llm_router.support.workers.retry import (
        openai_chat_path,
        openai_success_response,
    )

    path=openai_chat_path()
    routes={
      ("POST",path):[
        ScriptedResponse(
          status_code=200,
          headers={"Content-Type":"application/json"},
          body=openai_success_response(text="provider must not be touched"),
        )
      ]
    }
    with ScriptedHTTPServer(port=0,routes=routes) as server:
        original=_install_openrouter_base_url(server.base_url)
        try:
            result=run_error_boundary_inprocess(scenario="invalid_model")
            request_count=server.request_count("POST",path)
        finally:
            install_config(original)
    detected=(
      not result.ok
      and result.error_type=="ConfigurationError"
      and request_count==0
    )
    return {
      "engine":"pytest-bdd public boundary + ScriptedHTTPServer sentinel",
      "mode":"provider-interface isolation challenge",
      "generated":1,
      "detected":1 if detected else 0,
      "score":100.0 if detected else 0.0,
      "target":"REQ_INVALID_CONFIGURATION_ERRORS · provider boundary must remain untouched",
      "fault_family":"unexpected provider interaction",
      "provider_requests":request_count,
      "public_error":result.error_type,
      "generic_mutator":False,
      "note":"For this pre-provider Requirement the meaningful interface fault is an unexpected provider call. A local HTTP sentinel proves the public configuration error occurs with zero provider requests.",
    }


def probe_invalid_config_runtime_isolation():
    binary=shutil.which("toxiproxy-server")
    if not binary:
        return {
          "engine":"Toxiproxy",
          "mode":"pre-provider runtime/dependency isolation challenge",
          "available":False,
          "generated":0,"detected":0,"score":None,
          "reason":"toxiproxy-server is not installed",
        }
    import httpx

    from llm_router import install_config
    from tests.llm_router.support.fault_server import (
        ScriptedHTTPServer,
        ScriptedResponse,
    )
    from tests.llm_router.support.workers.error_boundary import (
        run_error_boundary_inprocess,
    )
    from tests.llm_router.support.workers.retry import (
        openai_chat_path,
        openai_success_response,
    )

    api_port=free_port()
    proxy_port=free_port()
    process=subprocess.Popen(
      [binary,"-host","127.0.0.1","-port",str(api_port)],
      stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,
    )
    try:
        api=f"http://127.0.0.1:{api_port}"
        for _ in range(80):
            try:
                if httpx.get(api+"/version",timeout=.2).status_code==200:
                    break
            except Exception:
                time.sleep(.05)
        else:
            raise RuntimeError("Toxiproxy API did not start")
        path=openai_chat_path()
        routes={
          ("POST",path):[
            ScriptedResponse(
              status_code=200,
              headers={"Content-Type":"application/json"},
              body=openai_success_response(text="provider must remain unreachable"),
            )
          ]
        }
        with ScriptedHTTPServer(port=0,routes=routes) as server:
            upstream=urllib.parse.urlparse(server.base_url)
            httpx.post(api+"/proxies",json={
              "name":"invalid-config-provider",
              "listen":f"127.0.0.1:{proxy_port}",
              "upstream":f"{upstream.hostname}:{upstream.port}",
              "enabled":True,
            }).raise_for_status()
            httpx.post(api+"/proxies/invalid-config-provider/toxics",json={
              "name":"provider-latency",
              "type":"latency",
              "stream":"downstream",
              "toxicity":1.0,
              "attributes":{"latency":1500,"jitter":0},
            }).raise_for_status()
            original=_install_openrouter_base_url(f"http://127.0.0.1:{proxy_port}")
            try:
                started=time.perf_counter()
                result=run_error_boundary_inprocess(scenario="invalid_model")
                elapsed=round(time.perf_counter()-started,3)
                request_count=server.request_count("POST",path)
            finally:
                install_config(original)
        detected=(
          not result.ok
          and result.error_type=="ConfigurationError"
          and request_count==0
          and elapsed<1.0
        )
        return {
          "engine":"Toxiproxy",
          "engine_version":"2.12.0",
          "mode":"pre-provider runtime/dependency isolation challenge",
          "available":True,
          "generated":1,
          "detected":1 if detected else 0,
          "score":100.0 if detected else 0.0,
          "target":"REQ_INVALID_CONFIGURATION_ERRORS · provider degradation must be irrelevant before provider execution",
          "fault_family":"provider latency",
          "latency_ms":1500,
          "provider_requests":request_count,
          "public_error":result.error_type,
          "elapsed_seconds":elapsed,
          "native_metadata":True,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


def invalid_config_fault_probe_input_paths():
    """Return the current source set that can change specialized fault-probe meaning."""
    paths={
      "docs/requirements/configuration.md",
      "docs/verification-profiles/invalid-configuration.md",
      "src/llm_router/_internal/config/validation.py",
      "features/responses/public_contract.feature",
      "tests/llm_router/bdd/responses/test_public_contract.py",
      "tests/llm_router/unit/test_internal_config_validation.py",
      "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py",
      "tests/llm_router/support/fault_server.py",
      "tests/llm_router/support/workers/error_boundary.py",
      "tests/llm_router/support/workers/timeout.py",
      "pyproject.toml",
    }
    return sorted(paths)


def invalid_config_fault_probe_binding():
    """Bind specialized fault facts to the exact current contract and probe inputs."""
    registry=normative_contract_registry()
    contract_id="REQ_INVALID_CONFIGURATION_ERRORS"
    contract=registry[contract_id]
    inputs={
      relative:sha256_file(ROOT/relative)
      for relative in invalid_config_fault_probe_input_paths()
      if (ROOT/relative).is_file()
    }
    return {
      "contract_id":contract_id,
      "revision":int(contract["revision"]),
      "source_path":contract["source_path"],
      "source_sha256":sha256_file(ROOT/contract["source_path"]),
      "probe_inputs":inputs,
      "probe_input_set_sha256":sha256_text(stable_json(inputs)),
    }


def specialized_fault_binding_current(contract_id, contract_fault):
    """Fail closed when specialized probe facts no longer match current source bytes."""
    if not contract_fault:
        return False
    binding=contract_fault.get("binding") or {}
    if binding.get("contract_id")!=contract_id:
        return False
    try:
        current=invalid_config_fault_probe_binding()
    except Exception:
        return False
    return (
      contract_id=="REQ_INVALID_CONFIGURATION_ERRORS"
      and int(binding.get("revision") or -1)==int(current["revision"])
      and binding.get("source_path")==current["source_path"]
      and binding.get("source_sha256")==current["source_sha256"]
      and binding.get("probe_input_set_sha256")==current["probe_input_set_sha256"]
      and binding.get("probe_inputs")==current["probe_inputs"]
    )


INVALID_CONFIG_PUBLIC_TEST="tests/llm_router/bdd/responses/test_public_contract.py::test_invalid_model_configuration_surfaces_as_a_configuration_error"


def build_fault_model_facts():
    """Specialized fault probes of REQ_INVALID_CONFIGURATION_ERRORS.

    Its public rejection path is challenged where mutation cannot reach: a mutated
    specification outcome, an injected forbidden import edge, a provider boundary that
    must see no request, and injected provider latency. Each probe runs against an
    isolated copy or a controlled boundary and is retained with the exact inputs it
    ran on; implementation faults are the campaign's.
    """
    req_spec=probe_invalid_config_specification_fault()
    req_spec.update({
      "claim_section":"public error-category outcome",
      "expected_outcome":"ConfigurationError",
      "mutated_outcome":"ProviderError",
      "parser_validity":"Original and mutated feature text both parse successfully with the Cucumber Gherkin parser.",
      "execution_nodeid":INVALID_CONFIG_PUBLIC_TEST,
      "execution_command":f"uv run pytest -q {INVALID_CONFIG_PUBLIC_TEST} --no-cov",
      "detector":"pytest-bdd exact Then-step assertion on the public error type",
      "source_url":repo_blob_url("features/responses/public_contract.feature"),
      "test_source_url":repo_blob_url("tests/llm_router/bdd/responses/test_public_contract.py"),
      "raw_facts_url":"assurance-fault-model-facts.json",
    })
    req_arch=probe_invalid_config_architecture_fault()
    req_arch.update({
      "declared_rule":"Private implementation must stay layered",
      "baseline_summary":f"{int(req_arch.get('baseline_kept') or 0)} kept / {int(req_arch.get('baseline_broken') or 0)} broken",
      "injected_violation":"llm_router._internal.config.validation → llm_router._internal.providers.registry",
      "detector":"Import Linter contract private-core-layering",
      "execution_command":".venv/bin/lint-imports --no-cache against an isolated temporary source copy",
      "source_url":repo_blob_url("src/llm_router/_internal/config/validation.py"),
      "raw_facts_url":"assurance-fault-model-facts.json",
    })
    req_interface=probe_invalid_config_interface_isolation()
    req_interface.update({
      "dependency":"OpenAI-compatible provider HTTP boundary selected for the invalid-model route",
      "expected_interaction":"0 provider HTTP requests; configuration must fail before provider execution",
      "observed_interaction":f"{int(req_interface.get('provider_requests') or 0)} provider HTTP requests",
      "expected_public_error":"ConfigurationError",
      "detector":"ScriptedHTTPServer request journal + public result from the real router path",
      "source_url":repo_blob_url("tests/llm_router/support/workers/error_boundary.py"),
      "raw_facts_url":"assurance-fault-model-facts.json",
    })
    req_runtime=probe_invalid_config_runtime_isolation()
    req_runtime.update({
      "dependency":"provider HTTP path behind a Toxiproxy TCP proxy",
      "injected_fault":{"type":"latency","stream":"downstream","toxicity":1.0,"latency_ms":int(req_runtime.get("latency_ms") or 0),"jitter_ms":0},
      "expected_invariant":"Invalid configuration still raises ConfigurationError before any provider request; injected provider latency is irrelevant.",
      "observed_behavior":f"{req_runtime.get('public_error')}; provider requests={int(req_runtime.get('provider_requests') or 0)}; elapsed={req_runtime.get('elapsed_seconds')}s",
      "detector":"public error result + ScriptedHTTPServer request journal while Toxiproxy latency toxic is active",
      "source_url":repo_blob_url("tests/llm_router/support/workers/error_boundary.py"),
      "raw_facts_url":"assurance-fault-model-facts.json",
    })
    requirement_layers={
      "specification":{"id":"specification","label":"Specification / model","kind":"scenario-mutation",**req_spec},
      "architecture":{"id":"architecture","label":"Architecture","kind":"negative-control",**req_arch},
      "interface":{"id":"interface","label":"Interface / protocol","kind":"isolation-challenge",**req_interface},
      "runtime":{"id":"runtime","label":"Runtime / dependency","kind":"fault-injection-isolation",**req_runtime},
    }
    payload={
      "schema_version":"ternforge-specialized-fault-probes-1",
      "generated_at":utc_now(),
      "head_sha":git_sha(),
      "obligation_semantics":"A probe covers its fault class only when its challenge actually ran against the contract's public path; a probe whose inputs changed no longer counts.",
      "contracts":{
        "REQ_INVALID_CONFIGURATION_ERRORS":{
          "binding":invalid_config_fault_probe_binding(),
          "layers":requirement_layers,
        }
      },
      "known_limitations":[
        "REQ_INVALID_CONFIGURATION_ERRORS uses a claim-specific boundary-isolation sentinel for its interface class, because llm-router has no machine-readable provider interface schema for a generic interface mutator.",
        "Its specification probe mutates a simple Scenario parsed by the official Cucumber Gherkin parser and executed by pytest-bdd.",
      ],
    }
    ASSURANCE_FACTS_PATH.write_text(json.dumps(payload,indent=2))
    return payload


def markdown_table_after(text, heading):
    match=re.search(
      rf"^{re.escape(heading)}\s*$\n\n((?:\|.*\|\n?)+)",
      text,flags=re.MULTILINE,
    )
    if not match:
        return []
    lines=[line.strip() for line in match.group(1).splitlines() if line.strip()]
    if len(lines)<3:
        return []
    split=lambda line:[cell.strip() for cell in line.strip("|").split("|")]
    headers=split(lines[0])
    rows=[]
    for line in lines[2:]:
        cells=split(line)
        if len(cells)!=len(headers):
            continue
        rows.append(dict(zip(headers,cells)))
    return rows


def verification_profile_source(contract_id):
    marker=f"## Profile · {contract_id}"
    for path in sorted((ROOT/"docs/verification-profiles").glob("**/*.md")):
        text=path.read_text()
        start=text.find(marker)
        if start<0:
            continue
        tail=text[start:]
        next_profile=tail.find("\n## Profile · ",len(marker))
        return path,tail[:next_profile if next_profile>0 else len(tail)]
    return None,""


def verification_profile_contract_ids():
    result=[]
    for path in sorted((ROOT/"docs/verification-profiles").glob("**/*.md")):
        result.extend(
          re.findall(r"^## Profile · (T?REQ_[A-Z0-9_]+)\s*$",path.read_text(),flags=re.MULTILINE)
        )
    return sorted(set(result))


def normative_contract_registry():
    result={}
    pattern=re.compile(
      r"\x60\x60\x60\{(?:req|treq)\}.*?\n(?P<body>.*?)\n\x60\x60\x60",
      flags=re.DOTALL,
    )
    for path in sorted((ROOT/"docs/requirements").glob("*.md")):
        for match in pattern.finditer(path.read_text()):
            body=match.group("body")
            id_match=re.search(r"^:id:\s*(T?REQ_[A-Z0-9_]+)\s*$",body,flags=re.MULTILINE)
            if not id_match:
                continue
            contract_id=id_match.group(1)
            revision_match=re.search(r"^:revision:\s*(\d+)\s*$",body,flags=re.MULTILINE)
            derives_match=re.search(r"^:derives:\s*(.+?)\s*$",body,flags=re.MULTILINE)
            if not revision_match:
                raise RuntimeError(f"{contract_id}: normative contract has no integer revision")
            if contract_id in result:
                raise RuntimeError(f"duplicate normative contract id: {contract_id}")
            result[contract_id]={
              "revision":int(revision_match.group(1)),
              "derives":(
                re.findall(r"(?:T?REQ_[A-Z0-9_]+|FEAT_[A-Z0-9_]+)",derives_match.group(1))
                if derives_match else []
              ),
              "source_path":str(path.relative_to(ROOT)),
            }
    return result


def parse_revisioned_verifies(raw):
    return list(dict.fromkeys(
      (contract_id,int(revision))
      for contract_id,revision in re.findall(
        r"((?:T?REQ_[A-Z0-9_]+))\[revision==(\d+)\]",
        str(raw or ""),
      )
    ))


def verifies_current_revision(raw,contract_id,registry=None):
    contracts=registry or normative_contract_registry()
    current=contracts.get(contract_id)
    return bool(
      current
      and (contract_id,int(current["revision"])) in parse_revisioned_verifies(raw)
    )


def contract_in_profile_scope(profile_contract_id,criterion_contract_id,registry=None):
    if criterion_contract_id==profile_contract_id:
        return True
    contracts=registry or normative_contract_registry()
    child=contracts.get(criterion_contract_id)
    if not child or not criterion_contract_id.startswith("TREQ_"):
        return False
    pending=list(child.get("derives") or [])
    seen=set()
    while pending:
        current=pending.pop()
        if current==profile_contract_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        parent=contracts.get(current)
        if parent:
            pending.extend(parent.get("derives") or [])
    return False


def verification_criterion_contracts():
    result={}
    policy=project_monitor_policy()
    for contract_id in verification_profile_contract_ids():
        target=requirement_monitor_target(contract_id,policy)
        for criterion_id,criterion_contract in (target.get("criterion_contracts") or {}).items():
            if criterion_id in result:
                raise RuntimeError(
                  f"verification criterion {criterion_id} is declared by multiple profiles"
                )
            result[criterion_id]=criterion_contract
    return result


def project_monitor_policy():
    text=(ROOT/"docs/test-plan.md").read_text()
    decisions=markdown_table_after(text,"## Project decisions")
    thresholds={}
    decision_values={}
    for row in decisions:
        decision=row.get("Decision","")
        value=re.sub(r"\*\*","",row.get("Value","")).strip()
        decision_values[decision]=value
        match=re.search(r"(\d+(?:\.\d+)?)%",value)
        if match:
            thresholds[decision]=float(match.group(1))
    fault_class_descriptions={}
    fault_class_challenges={}
    for row in markdown_table_after(text,"#### Fault-class semantics"):
        ids=re.findall(r"\x60([^\x60]+)\x60",row.get("Fault class",""))
        for class_id in ids:
            fault_class_descriptions[class_id]=row.get("Meaning","")
            fault_class_challenges[class_id]=row.get("Challenged by","")
    arid_rules=[]
    for row in markdown_table_after(text,"##### Arid code"):
        ids=re.findall(r"\x60(arid\.[a-z-]+)\x60",row.get("Rule",""))
        if len(ids)!=1:
            raise RuntimeError("Test Plan: each Arid code row must name exactly one rule")
        arid_rules.append({"id":ids[0],"covers":row.get("Code it covers",""),"why":row.get("Why it is not mutated","")})
    declared_rules={rule["id"] for rule in arid_rules}
    if declared_rules!=set(MUTATION_EXTENSION.ARID_RULES):
        raise RuntimeError(
          f"Test Plan arid rules {sorted(declared_rules)} differ from the engine extension's "
          f"{sorted(MUTATION_EXTENSION.ARID_RULES)}"
        )
    fault_groups=[]
    for row in markdown_table_after(text,"### Fault-based testing"):
        ids=re.findall(r"\x60([^\x60]+)\x60",row.get("Fault classes",""))
        fault_groups.append({
          "label":row.get("Group",""),
          "classes":ids,
          "descriptions":{class_id:fault_class_descriptions.get(class_id,"") for class_id in ids},
        })
    return {
      "freshness_rule":decision_values.get("Evidence freshness"),
      "fault_detection_rule":decision_values.get("Implementation fault detection"),
      "mutation_signal":decision_values.get("Mutation signal"),
      "fault_class_descriptions":fault_class_descriptions,
      "fault_class_challenges":fault_class_challenges,
      "fault_groups":fault_groups,
      "arid_rules":arid_rules,
      "model_generation":model_generation_policy(text),
      "mutation_policy_url":"test-plan.html#test-plan-mutation-policy",
      "url":"test-plan.html#test-plan",
    }


def requirement_monitor_target(contract_id, policy):
    path,section=verification_profile_source(contract_id)
    if not section:
        return None
    registry=normative_contract_registry()
    if contract_id not in registry:
        raise RuntimeError(f"{contract_id}: Verification Profile has no current normative contract")

    coverage=[]
    item_descriptions={}
    item_anchors={}
    criterion_contracts={}
    level_keys={
      "Component":"component",
      "Component Integration":"component_integration",
      "System":"system",
      "System Integration":"system_integration",
      "Acceptance":"acceptance",
    }
    boundary_keys={
      "Local":"none",
      "Substitute":"substitute",
      "Replay":"replay",
      "Direct live":"direct",
    }
    representation_keys={
      "Synthetic":"synthetic_abstract",
      "Surrogate":"surrogate_simulated",
      "Representative":"representative",
      "Actual":"actual",
    }

    coverage_rows=markdown_table_after(section,"### Required coverage")
    if not coverage_rows:
        raise RuntimeError(f"{contract_id}: Verification Profile has no Required coverage rows")
    boundaries_by_level=defaultdict(set)
    coverage_cells=set()
    normalized_coverage_rows=[]
    for coverage_row in coverage_rows:
        level=coverage_row.get("Test level","").strip()
        boundary_label=coverage_row.get("Boundary","").strip()
        representation_label=coverage_row.get("Representation","").strip()
        level_key=level_keys.get(level)
        boundary_key=boundary_keys.get(boundary_label)
        representation=representation_keys.get(representation_label)
        if not level_key:
            raise RuntimeError(f"{contract_id}: unknown Test level in Required coverage: {level!r}")
        if not boundary_key:
            raise RuntimeError(f"{contract_id}: unknown Boundary in Required coverage: {boundary_label!r}")
        if not representation:
            raise RuntimeError(
              f"{contract_id}: unknown Representation in Required coverage: {representation_label!r}"
            )
        cell_key=(level_key,boundary_key)
        if cell_key in coverage_cells:
            raise RuntimeError(
              f"{contract_id}: duplicate Required coverage cell {level} × {boundary_label}"
            )
        coverage_cells.add(cell_key)
        boundaries_by_level[level_key].add(boundary_key)

        ms_raw=coverage_row.get("M&S target","").strip()
        ms_target=None if ms_raw in {"","—","-","N/A"} else ms_raw.upper()
        if ms_target is not None and ms_target not in {"L0","L1","L2","L3","L4"}:
            raise RuntimeError(f"{contract_id}: invalid M&S target {ms_raw!r}")
        if representation=="surrogate_simulated" and ms_target is None:
            raise RuntimeError(
              f"{contract_id}: Surrogate Required coverage must declare an explicit M&S target"
            )
        target_match=re.search(
          r"(\d+)\s+(?:item|items|criterion|criteria)\b",
          coverage_row.get("Target",""),
          flags=re.IGNORECASE,
        )
        if not target_match:
            raise RuntimeError(
              f"{contract_id}: Required coverage cell {level} × {boundary_label} "
              "must declare an explicit criterion count"
            )
        normalized_coverage_rows.append({
          "level":level,
          "level_key":level_key,
          "boundary_label":boundary_label,
          "boundary_key":boundary_key,
          "representation_label":representation_label,
          "representation":representation,
          "ms_validation_target":ms_target,
          "declared_count":int(target_match.group(1)),
        })

    criterion_rows=markdown_table_after(section,"### Verification criteria")
    if not criterion_rows:
        raise RuntimeError(f"{contract_id}: Verification Profile has no Verification criteria")
    criteria_by_cell=defaultdict(list)
    criterion_path_counts={}
    criterion_path_ids={}
    for criterion_row in criterion_rows:
        criterion_ids=re.findall(r"\x60([^\x60]+)\x60",criterion_row.get("Criterion",""))
        contract_ids=sorted(set(
          re.findall(r"(?:T?REQ_[A-Z0-9_]+)",criterion_row.get("Contract",""))
        ))
        level=criterion_row.get("Test level","").strip()
        level_key=level_keys.get(level)
        if len(criterion_ids)!=1:
            raise RuntimeError(
              f"{contract_id}: each Verification criteria row must declare exactly one criterion id"
            )
        criterion_id=criterion_ids[0]
        if len(contract_ids)!=1:
            raise RuntimeError(
              f"{contract_id}: criterion {criterion_id} must bind exactly one Requirement/TREQ"
            )
        criterion_contract=contract_ids[0]
        if not level_key:
            raise RuntimeError(
              f"{contract_id}: criterion {criterion_id} has unknown Test level {level!r}"
            )
        if not contract_in_profile_scope(contract_id,criterion_contract,registry):
            raise RuntimeError(
              f"{contract_id}: criterion {criterion_id} binds out-of-scope contract "
              f"{criterion_contract}; only the parent or its derived technical requirements are allowed"
            )

        declared_boundary=criterion_row.get("Boundary","").strip()
        if declared_boundary:
            criterion_boundary=boundary_keys.get(declared_boundary)
            if not criterion_boundary:
                raise RuntimeError(
                  f"{contract_id}: criterion {criterion_id} has unknown Boundary "
                  f"{declared_boundary!r}"
                )
            if (level_key,criterion_boundary) not in coverage_cells:
                raise RuntimeError(
                  f"verification criterion {criterion_id} declares "
                  f"{level} × {declared_boundary}, which is not a Required coverage cell"
                )
        else:
            possible=boundaries_by_level.get(level_key,set())
            if len(possible)!=1:
                raise RuntimeError(
                  f"verification criterion {criterion_id} is ambiguous at {level}; "
                  "add a Boundary column because this Test level has multiple Required coverage cells"
                )
            criterion_boundary=next(iter(possible))

        if criterion_id in criterion_path_counts:
            raise RuntimeError(f"verification criterion {criterion_id} is declared more than once")
        required_paths_text=criterion_row.get("Required paths","").strip()
        required_paths_match=re.fullmatch(r"\*{0,2}\s*(\d+)\s*\*{0,2}",required_paths_text)
        if not required_paths_match:
            raise RuntimeError(
              f"{contract_id}: criterion {criterion_id} must declare an explicit integer Required paths"
            )
        required_paths=int(required_paths_match.group(1))
        if required_paths<1:
            raise RuntimeError(
              f"verification criterion {criterion_id} must require at least one path"
            )
        path_ids_text=criterion_row.get("Required path IDs","").strip()
        path_ids=[]
        if path_ids_text and path_ids_text not in {"—","-","N/A","n/a"}:
            path_ids=re.findall(r"\x60([^\x60]+)\x60",path_ids_text)
            if len(path_ids)!=required_paths or len(set(path_ids))!=len(path_ids):
                raise RuntimeError(
                  f"{contract_id}: criterion {criterion_id} Required path IDs must "
                  f"declare exactly {required_paths} unique backtick-delimited ids"
                )
        success=re.sub(
          r"\x60([^\x60]+)\x60",r"\1",criterion_row.get("Success criterion","")
        ).strip()
        if not success:
            raise RuntimeError(
              f"{contract_id}: criterion {criterion_id} must declare a Success criterion"
            )
        criteria_by_cell[(level_key,criterion_boundary)].append(criterion_id)
        criterion_path_counts[criterion_id]=required_paths
        criterion_path_ids[criterion_id]=path_ids
        criterion_contracts[criterion_id]=criterion_contract
        item_descriptions[criterion_id]=success
        anchor_match=re.search(r'id="([^"]+)"',criterion_row.get("Criterion",""))
        if anchor_match:
            item_anchors[criterion_id]=anchor_match.group(1)

    for row in normalized_coverage_rows:
        cell_key=(row["level_key"],row["boundary_key"])
        criteria=list(criteria_by_cell.get(cell_key) or [])
        declared_count=row["declared_count"]
        if not criteria:
            raise RuntimeError(
              f"{contract_id}: Required coverage cell {row['level']} × "
              f"{row['boundary_label']} has no Verification criteria"
            )
        if declared_count!=len(criteria):
            raise RuntimeError(
              f"{contract_id}: Required coverage cell {row['level']} × "
              f"{row['boundary_label']} declares {declared_count} criteria but the "
              f"Verification criteria table assigns {len(criteria)}"
            )
        coverage.append({
          "level":row["level_key"],
          "level_label":row["level"],
          "boundary":row["boundary_key"],
          "boundary_label":row["boundary_label"],
          "representation":row["representation"],
          "representation_label":row["representation_label"],
          "ms_validation_target":row["ms_validation_target"],
          "items":criteria,
          "item_path_counts":{
            criterion_id:criterion_path_counts[criterion_id]
            for criterion_id in criteria
          },
          "item_path_ids":{
            criterion_id:list(criterion_path_ids[criterion_id])
            for criterion_id in criteria
            if criterion_path_ids[criterion_id]
          },
          "declared_count":declared_count,
        })

    basis_match=re.search(
      r"\*\*Coverage basis\.\*\*\s*(.+?)(?=\n\n|\Z)",
      section,
      flags=re.DOTALL,
    )
    coverage_basis=(" ".join(basis_match.group(1).split()) if basis_match else "")
    if not coverage_basis:
        raise RuntimeError(f"{contract_id}: missing non-empty Coverage basis")
    representation_basis_match=re.search(
      r"\*\*Representation basis\.\*\*\s*(.+?)(?=\n\n|\Z)",
      section,
      flags=re.DOTALL,
    )
    representation_basis=(
      " ".join(representation_basis_match.group(1).split())
      if representation_basis_match else ""
    )
    if not representation_basis:
        raise RuntimeError(f"{contract_id}: missing non-empty Representation basis")

    model_match=re.search(r"\*\*Models?:\*\*.*?<([^>]+)>",section)
    if not model_match:
        raise RuntimeError(f"{contract_id}: missing explicit test-plan Model link")
    model_url=f"test-plan.html#{model_match.group(1)}"

    gate_aggregation={}
    gate_keys={
      "Semantic coverage":"semantic_coverage",
      "Representation":"representation",
      "Provenance":"provenance",
      "Producer qualification":"producer_qualification",
      "Freshness":"freshness",
      "M&S validation":"ms_validation",
    }
    aggregation_rows=markdown_table_after(section,"### Evidence aggregation")
    if not aggregation_rows:
        raise RuntimeError(f"{contract_id}: missing Evidence aggregation table")
    for row in aggregation_rows:
        signal_label=row.get("Signal","").strip()
        signal=gate_keys.get(signal_label)
        if not signal:
            raise RuntimeError(
              f"{contract_id}: unknown Evidence aggregation signal {signal_label!r}"
            )
        if signal in gate_aggregation:
            raise RuntimeError(
              f"{contract_id}: duplicate Evidence aggregation signal {signal_label}"
            )
        rule=row.get("Rule","").strip().upper()
        if rule not in {"ALL","ANY"}:
            raise RuntimeError(
              f"{contract_id}: Evidence aggregation {signal_label} has invalid rule {rule!r}"
            )
        applies_to=row.get("Applies to","").strip()
        if not applies_to:
            raise RuntimeError(
              f"{contract_id}: Evidence aggregation {signal_label} has empty scope"
            )
        gate_aggregation[signal]={
          "rule":rule,
          "applies_to":applies_to,
        }
    if set(gate_aggregation)!=set(gate_keys.values()):
        missing=sorted(set(gate_keys.values())-set(gate_aggregation))
        raise RuntimeError(
          f"{contract_id}: Evidence aggregation must declare all six signals; missing={missing}"
        )

    policy_fault_groups=list(policy.get("fault_groups") or [])
    expected_fault_classes={
      class_id
      for group in policy_fault_groups
      for class_id in group["classes"]
    }
    expected_fault_groups={group["label"] for group in policy_fault_groups}
    rationale_rows=markdown_table_after(section,"#### Fault-group rationale")
    fault_group_rationales={
      row.get("Group","").strip():row.get("Why","").strip()
      for row in rationale_rows
      if row.get("Group","").strip()
    }
    fault_cells=markdown_table_after(section,"### Fault applicability")
    if not fault_cells:
        raise RuntimeError(
          f"{contract_id}: every Contract Evidence profile must explicitly classify "
          "every project fault class as REQUIRED, OPTIONAL, or N/A"
        )
    class_state={}
    duplicates=[]
    for row in fault_cells:
        for column,state in (("REQUIRED","required"),("OPTIONAL","optional"),("N/A","na")):
            for class_id in re.findall(r"\x60([^\x60]+)\x60",row.get(column,"")):
                if class_id in class_state:
                    duplicates.append(class_id)
                    continue
                class_state[class_id]=state
    unknown_fault_classes=sorted(set(class_state)-expected_fault_classes)
    missing_fault_classes=sorted(expected_fault_classes-set(class_state))
    if duplicates or unknown_fault_classes or missing_fault_classes:
        raise RuntimeError(
          f"{contract_id}: fault classification must cover each project class exactly once; "
          f"duplicates={sorted(set(duplicates))}, unknown={unknown_fault_classes}, "
          f"missing={missing_fault_classes}"
        )
    missing_rationales=sorted(
      group_label
      for group_label in expected_fault_groups
      if not fault_group_rationales.get(group_label)
    )
    if missing_rationales:
        raise RuntimeError(
          f"{contract_id}: missing Fault-group rationale for {missing_rationales}"
        )
    fault_groups=[]
    for group in policy_fault_groups:
        items=[
          {
            "id":class_id,
            "state":class_state[class_id],
            "description":(group.get("descriptions") or {}).get(class_id,""),
          }
          for class_id in group["classes"]
        ]
        fault_groups.append({
          "label":group["label"],
          "items":items,
          "rationale":fault_group_rationales[group["label"]],
        })

    required_treqs=[]
    technical_support_rows=markdown_table_after(section,"### Required technical support")
    if technical_support_rows and contract_id.startswith("TREQ_"):
        raise RuntimeError(
          f"{contract_id}: Technical requirements cannot declare Required technical support"
        )
    for row in technical_support_rows:
        ids=sorted(set(
          re.findall(r"TREQ_[A-Z0-9_]+",row.get("Technical requirement",""))
        ))
        if len(ids)!=1:
            raise RuntimeError(
              f"{contract_id}: each Required technical support row must reference exactly one TREQ"
            )
        treq_id=ids[0]
        target=re.sub(r"\*\*","",row.get("Target","")).strip().upper()
        if target!="PASS":
            raise RuntimeError(
              f"{contract_id}: Required technical support {treq_id} must target PASS"
            )
        if treq_id in required_treqs:
            raise RuntimeError(
              f"{contract_id}: duplicate Required technical support {treq_id}"
            )
        if treq_id not in registry:
            raise RuntimeError(
              f"{contract_id}: Required technical support references unknown {treq_id}"
            )
        if not contract_in_profile_scope(contract_id,treq_id,registry):
            raise RuntimeError(
              f"{contract_id}: Required technical support {treq_id} is not derived from this Requirement"
            )
        treq_path,treq_section=verification_profile_source(treq_id)
        if not treq_path or not treq_section:
            raise RuntimeError(
              f"{contract_id}: Required technical support {treq_id} has no first-class Verification Profile"
            )
        required_treqs.append(treq_id)

    # Where the contract's own code is the subject of an arid rule, its profile turns the rule off.
    arid_ids={rule["id"] for rule in policy.get("arid_rules") or []}
    arid_overrides=[]
    for row in markdown_table_after(section,"### Mutation policy"):
        ids=re.findall(r"\x60(arid\.[a-z-]+)\x60",row.get("Rule",""))
        decision=row.get("Decision","").strip()
        why=row.get("Why","").strip()
        if len(ids)!=1 or ids[0] not in arid_ids:
            raise RuntimeError(f"{contract_id}: each Mutation policy row must name one Test Plan arid rule")
        if decision!="Mutate":
            raise RuntimeError(f"{contract_id}: Mutation policy decision for {ids[0]} must be Mutate, not {decision!r}")
        if not why:
            raise RuntimeError(f"{contract_id}: Mutation policy row for {ids[0]} must say why")
        if any(item["rule"]==ids[0] for item in arid_overrides):
            raise RuntimeError(f"{contract_id}: duplicate Mutation policy row for {ids[0]}")
        arid_overrides.append({"rule":ids[0],"why":why})
    # Semantic mutants challenge only a specification or interface class the profile applies.
    semantic_mutants=[]
    for row in markdown_table_after(section,"### Semantic mutants"):
        class_ids=re.findall(r"\x60((?:spec|interface)\.[a-z-]+)\x60",row.get("Fault class",""))
        refs=re.findall(r"\x60([^\x60]+)\x60",row.get("Target",""))
        budget=row.get("Budget","").strip()
        risk=row.get("Risk","").strip()
        if len(class_ids)!=1 or class_state.get(class_ids[0]) not in {"required","optional"}:
            raise RuntimeError(
              f"{contract_id}: a Semantic mutants row must name one spec.* or interface.* class the profile applies"
            )
        if len(refs)!=1 or "::" not in refs[0] or not (ROOT/refs[0].split("::",1)[0]).is_file():
            raise RuntimeError(f"{contract_id}: a Semantic mutants target must be `path/to/module.py::qualname`")
        if not budget.isdigit() or not 1<=int(budget)<=3:
            raise RuntimeError(f"{contract_id}: a Semantic mutants budget must be 1 to 3 per target")
        if not risk:
            raise RuntimeError(f"{contract_id}: a Semantic mutants row must name the risk it probes")
        source,qualname=refs[0].split("::",1)
        if SEMANTIC.function_source((ROOT/source).read_text(),qualname) is None:
            raise RuntimeError(f"{contract_id}: the Semantic mutants target {refs[0]} names no function in its module")
        semantic_mutants.append({
          "class":class_ids[0],"target":refs[0],"source":source,"qualname":qualname,
          "budget":int(budget),"risk":risk,
        })
    return {
      "contract_id":contract_id,
      "source_path":str(path.relative_to(ROOT)) if path else None,
      "source_url":(
        f"{str(path.relative_to(ROOT/'docs')).removesuffix('.md')}.html"
        if path else None
      ),
      "profile_url":(
        f"{str(path.relative_to(ROOT/'docs')).removesuffix('.md')}.html#verification-profile-{contract_id.lower().replace('_', '-')}"
        if path else None
      ),
      "coverage":coverage,
      "coverage_basis":coverage_basis,
      "representation_basis":representation_basis,
      "model_url":model_url,
      "gate_aggregation":gate_aggregation,
      "item_descriptions":item_descriptions,
      "item_anchors":item_anchors,
      "criterion_contracts":criterion_contracts,
      "required_treqs":required_treqs,
      "fault_groups":fault_groups,
      "arid_overrides":arid_overrides,
      "semantic_mutants":semantic_mutants,
    }


TEST_EVIDENCE_IDS: dict[str, str]={}


def test_evidence_url(nodeid):
    """A test's own evidence record in the portal: what it checked, how far it reached and what was real."""
    if not TEST_EVIDENCE_IDS:
        TEST_EVIDENCE_IDS.update({
          need["nodeid"]:need["id"]
          for need in current_needs().values()
          if need.get("type")=="testcase" and need.get("nodeid")
        })
    need_id=TEST_EVIDENCE_IDS.get(nodeid)
    return f"ternforge-test-evidence.html#{need_id}" if need_id else None


def package_version_or_unknown(name):
    try:
        return package_version(name)
    except Exception:
        return "UNKNOWN"


def current_evidence_qualification_environment():
    # A tool counts by what it does (IMPL_FAULTS.code_digest): a comment or a reformatting keeps
    # the qualification current, a changed line of code does not.
    code=IMPL_FAULTS.code_digest
    return {
      "python":sys.version.split()[0],
      "pytest":package_version_or_unknown("pytest"),
      "pytest_bdd":package_version_or_unknown("pytest-bdd"),
      "allure_pytest":package_version_or_unknown("allure-pytest"),
      "py_lib_testkit":package_version_or_unknown("py-lib-testkit"),
      "coverage":package_version_or_unknown("coverage"),
      "hypothesis":package_version_or_unknown("hypothesis"),
      "vcrpy":package_version_or_unknown("vcrpy"),
      "pytest_recording":package_version_or_unknown("pytest-recording"),
      "assurance_adapter_sha256":code(ROOT/".ai-bridge/build-mutation-report-prototype.py"),
      "requirement_monitor_sha256":code(ROOT/".ai-bridge/build-requirement-monitor.py"),
      "upper_assurance_monitor_sha256":code(ROOT/".ai-bridge/build-upper-assurance-pilot.py"),
      "assurance_monitor_domain_sha256":code(ROOT/".ai-bridge/assurance_monitor_domain.py"),
      "assurance_monitor_registry_sha256":code(ROOT/".ai-bridge/assurance_monitor_registry.py"),
      "implementation_faults_sha256":code(ROOT/".ai-bridge/implementation_faults.py"),
      "mutation_extension_sha256":IMPL_FAULTS.plugin_sha256(),
      "semantic_mutants_sha256":code(ROOT/".ai-bridge/semantic_mutants.py"),
      "semantic_calibration_sha256":semantic_calibration_sha256(),
      "model_generation_sha256":code(ROOT/".ai-bridge/model_generation.py"),
      "survivor_equivalence_sha256":code(ROOT/".ai-bridge/survivor_equivalence.py"),
      "qualification_harness_sha256":code(ROOT/".ai-bridge/qualify-evidence-confidence.py"),
      "trace_bridge_sha256":code(ROOT/"tests/conftest.py"),
    }


def assessor_calibration_sha256():
    """One digest over the assessors' frozen calibration answers and their record."""
    files=sorted(path for path in ASSESSOR_CALIBRATION_DIR.rglob("*") if path.is_file()) if ASSESSOR_CALIBRATION_DIR.is_dir() else []
    if not files:
        return None
    return hashlib.sha256(b"".join(str(path.relative_to(ASSESSOR_CALIBRATION_DIR)).encode()+b"\0"+path.read_bytes() for path in files)).hexdigest()


def semantic_calibration_sha256():
    """One digest over the calibration set that qualifies the semantic mutant cascade."""
    folder=ROOT/".ai-bridge/semantic-mutants/calibration"
    files=sorted(path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    if not files:
        return None
    return hashlib.sha256(b"".join(str(path.relative_to(folder)).encode()+b"\0"+path.read_bytes() for path in files)).hexdigest()


def load_evidence_qualification():
    if not EVIDENCE_QUALIFICATION_PATH.exists():
        return {}
    try:
        return json.loads(EVIDENCE_QUALIFICATION_PATH.read_text())
    except Exception:
        return {}


def qualification_is_current(record):
    return bool(record) and record.get("environment")==current_evidence_qualification_environment()


def producer_chain_status(producer_ids,qualification,monitor_producer="PRODUCER_REQUIREMENT_MONITOR"):
    if not qualification_is_current(qualification):
        return "UNKNOWN", "qualification record is missing or does not match current tool/code fingerprints"
    required=list(dict.fromkeys(list(producer_ids or [])+["PRODUCER_LLM_ROUTER_TRACE_BRIDGE","PRODUCER_ASSURANCE_ADAPTER",monitor_producer]))
    producers=qualification.get("producers") or {}
    states=[str((producers.get(pid) or {}).get("status") or "UNKNOWN").upper() for pid in required]
    if any(state=="NOT QUALIFIED" for state in states):
        return "NOT QUALIFIED", "at least one producer failed its intended-use false-green control"
    if not states or any(state!="QUALIFIED" for state in states):
        missing=[pid for pid,state in zip(required,states) if state!="QUALIFIED"]
        return "UNKNOWN", "qualification is missing for: "+", ".join(missing)
    return "QUALIFIED", "every producer in the observed evidence chain passed current intended-use false-green controls"


def junit_suite_window(root):
    suite=next(root.iter("testsuite"),None)
    if suite is None:
        return None,None,None
    raw=suite.attrib.get("timestamp")
    try:
        start=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        if start.tzinfo is None:
            start=start.replace(tzinfo=UTC)
        start=start.astimezone(UTC)
        duration=float(suite.attrib.get("time") or 0.0)
        end=start+timedelta(seconds=max(duration,0.0))
        return int(start.timestamp()*1000),int(end.timestamp()*1000),start.isoformat()
    except Exception:
        return None,None,raw


def allure_attachments(payload):
    for attachment in payload.get("attachments") or []:
        yield attachment
    for step in payload.get("steps") or []:
        yield from allure_attachments(step)


def allure_monitor_index():
    result=defaultdict(list)
    if not ALLURE_RESULTS_DIR.exists():
        return result
    for path in sorted(ALLURE_RESULTS_DIR.glob("*-result.json")):
        try:
            payload=json.loads(path.read_text())
        except Exception:
            continue
        observations=[]
        test_observation=None
        observed_producer_ids=[]
        for attachment in allure_attachments(payload):
            if attachment.get("type")!="application/vnd.ternforge.verification-observation+json":
                continue
            candidate=ALLURE_RESULTS_DIR/str(attachment.get("source") or "")
            if not candidate.exists():
                continue
            try:
                observation=json.loads(candidate.read_text())
            except Exception:
                continue
            obs_payload=observation.get("payload") or {}
            row={
              "kind":observation.get("kind"),
              "payload":obs_payload,
              "path":str(candidate.relative_to(ROOT)),
              "sha256":sha256_file(candidate),
            }
            observations.append(row)
            producer_id=(
              obs_payload.get("producer_id")
              if observation.get("kind") in {
                "evidence-producer-use","external-substitute","external-replay","external-direct"
              }
              else None
            )
            if producer_id and producer_id not in observed_producer_ids:
                observed_producer_ids.append(producer_id)
            if observation.get("kind")=="test-execution" and obs_payload.get("nodeid"):
                test_observation=row
        if not test_observation:
            continue
        obs_payload=test_observation["payload"]
        nodeid=obs_payload.get("nodeid")
        producer_ids=list(dict.fromkeys(list(obs_payload.get("producer_ids") or [])+observed_producer_ids))
        observation_digest=sha256_text(stable_json(sorted((row["path"],row["sha256"]) for row in observations)))
        result[nodeid].append({
          "path":str(path.relative_to(ROOT)),
          "sha256":sha256_file(path),
          "uuid":payload.get("uuid"),
          "status":str(payload.get("status") or "unknown").lower(),
          "start":payload.get("start"),
          "stop":payload.get("stop"),
          "full_name":payload.get("fullName"),
          "observation_path":test_observation.get("path"),
          "observation_sha256":test_observation.get("sha256"),
          "observation_aggregate_sha256":observation_digest,
          "observation_nodeid":nodeid,
          "producer_ids":producer_ids,
          "verification_kind":obs_payload.get("verification_kind"),
          "source_path":obs_payload.get("path"),
          "fixtures":list(obs_payload.get("fixtures") or []),
          "markers":list(obs_payload.get("markers") or []),
          "labels":{
            str(row.get("name") or ""):str(row.get("value") or "")
            for row in payload.get("labels") or []
            if row.get("name")
          },
          "observations":observations,
        })
    return result

def coverage_context_present(nodeid):
    if not COVERAGE_DB.exists():
        return False
    try:
        data=CoverageData(basename=str(COVERAGE_DB))
        data.read()
        return f"{nodeid}|run" in set(data.measured_contexts())
    except Exception:
        return False


SNAPSHOT_RUN_BINDING_WINDOW_SECONDS=(-300,60)


def snapshot_run_binding(captured_at,suite_start_ms):
    """The freshness baseline must be the retained run's own session-start snapshot.

    tests/conftest.py writes it at pytest session start, so a snapshot captured far
    from the retained JUnit suite start was written by some other pytest session and
    cannot tell whether the retained evidence is still current.
    """
    if suite_start_ms is None:
        return False,"the retained JUnit run has no start time"
    try:
        captured=datetime.fromisoformat(str(captured_at).replace("Z","+00:00"))
        if captured.tzinfo is None:
            captured=captured.replace(tzinfo=UTC)
    except Exception:
        return False,"the retained input snapshot has no capture time"
    delta=(captured.timestamp()*1000-suite_start_ms)/1000
    low,high=SNAPSHOT_RUN_BINDING_WINDOW_SECONDS
    if low<=delta<=high:
        return True,"the input snapshot was captured at the retained run's session start"
    side="after" if delta>0 else "before"
    return False,(
      f"the input snapshot was captured {abs(delta):.0f}s {side} the retained run started, "
      "so it is not that run's freshness baseline; re-run the retained test suite"
    )


def load_evidence_run_inputs():
    if not EVIDENCE_RUN_INPUTS_PATH.exists():
        return {}
    try:
        snapshot=json.loads(EVIDENCE_RUN_INPUTS_PATH.read_text())
    except Exception:
        return {}
    suite_start_ms=None
    if JUNIT_PATH.exists():
        try:
            suite_start_ms,_,_=junit_suite_window(ET.parse(JUNIT_PATH).getroot())
        except Exception:
            suite_start_ms=None
    bound,basis=snapshot_run_binding(snapshot.get("captured_at"),suite_start_ms)
    snapshot["_run_binding"]={"bound":bound,"basis":basis}
    return snapshot


def unbound_snapshot_basis(snapshot):
    binding=(snapshot or {}).get("_run_binding") or {}
    if binding and not binding.get("bound"):
        return str(binding.get("basis") or "the input snapshot is not bound to the retained run")
    return None


def current_input_snapshot(snapshot):
    if not snapshot or not snapshot.get("inputs"):
        return "UNKNOWN","retained run input snapshot is missing",None
    unbound=unbound_snapshot_basis(snapshot)
    if unbound:
        return "UNKNOWN",unbound,None
    paths=set()
    for pattern in snapshot.get("input_scope") or []:
        paths.update(path for path in ROOT.glob(str(pattern)) if path.is_file())
    for relative in snapshot.get("explicit_inputs") or []:
        path=ROOT/str(relative)
        if path.is_file():
            paths.add(path)
    current={}
    for path in sorted(paths,key=lambda value:value.as_posix()):
        try:
            relative=str(path.resolve().relative_to(ROOT.resolve()))
        except Exception:
            continue
        current[relative]=sha256_file(path)
    current_digest=sha256_text(stable_json(current))
    retained=dict(snapshot.get("inputs") or {})
    retained_digest=snapshot.get("input_set_sha256") or sha256_text(stable_json(retained))
    if current==retained and current_digest==retained_digest:
        return "CURRENT","all retained verification inputs still have the exact bytes captured at pytest session start",current_digest
    changed=sorted(
      path for path in set(current)|set(retained)
      if current.get(path)!=retained.get(path)
    )
    sample=", ".join(changed[:4])
    more=f" (+{len(changed)-4} more)" if len(changed)>4 else ""
    return "STALE",f"verification inputs changed since the retained run: {sample}{more}",current_digest


def evidence_input_paths(snapshot,nodeid,contract_id,source_path,gherkin_feature,registry):
    paths=set(str(value) for value in (snapshot.get("explicit_inputs") or []) if value)
    if source_path:
        paths.add(str(source_path))
    paths.update(
      path for path in current_context_files(nodeid)
      if str(path).startswith("src/")
    )
    contract=registry.get(contract_id) or {}
    if contract.get("source_path"):
        paths.add(str(contract["source_path"]))
    profile_path,_=verification_profile_source(contract_id)
    if profile_path:
        paths.add(str(profile_path.relative_to(ROOT)))
    feature=str(gherkin_feature or "").strip()
    if feature:
        if not feature.startswith("features/"):
            feature="features/"+feature
        paths.add(feature)
    test_path=ROOT/source_path if source_path else None
    retained=dict(snapshot.get("inputs") or {})
    if test_path is not None:
        cassette_dir=test_path.parent/"cassettes"/test_path.stem
        cassette_prefix=str(cassette_dir.relative_to(ROOT)).rstrip("/")+"/"
        paths.update(
          str(path.relative_to(ROOT))
          for path in cassette_dir.rglob("*")
          if path.is_file()
        )
        paths.update(path for path in retained if path.startswith(cassette_prefix))
        for parent in [test_path.parent,*test_path.parents]:
            if parent==ROOT:
                break
            conftest=parent/"conftest.py"
            relative=str(conftest.relative_to(ROOT))
            if conftest.is_file() or relative in retained:
                paths.add(relative)
    support_root=ROOT/"tests/llm_router/support"
    paths.update(
      str(path.relative_to(ROOT))
      for path in support_root.rglob("*.py")
      if path.is_file()
    )
    data_root=ROOT/"tests/llm_router/data"
    paths.update(
      str(path.relative_to(ROOT))
      for path in data_root.rglob("*")
      if path.is_file() and "__pycache__" not in path.parts
    )
    paths.update(
      path for path in retained
      if path.startswith("tests/llm_router/support/")
      or path=="tests/llm_router/bdd/_support.py"
      or path.startswith("tests/llm_router/data/")
    )
    return sorted(paths)


def evidence_input_state(snapshot,paths):
    retained=dict(snapshot.get("inputs") or {})
    if not retained:
        return "UNKNOWN","retained run input snapshot is missing",None,[]
    unbound=unbound_snapshot_basis(snapshot)
    if unbound:
        return "UNKNOWN",unbound,None,[]
    if not paths:
        return "UNKNOWN","no relevant verification inputs could be resolved",None,[]
    current={}
    changed=[]
    unknown=[]
    for relative in sorted(set(paths)):
        path=ROOT/relative
        current_sha=sha256_file(path) if path.is_file() else None
        retained_sha=retained.get(relative)
        current[relative]=current_sha
        if retained_sha is None:
            unknown.append(relative)
        elif current_sha!=retained_sha:
            changed.append(relative)
    digest=sha256_text(stable_json(current))
    if unknown:
        sample=", ".join(unknown[:3])
        more=f" (+{len(unknown)-3} more)" if len(unknown)>3 else ""
        return "STALE",f"relevant input was not captured by the retained run: {sample}{more}",digest,sorted(set(unknown+changed))
    if changed:
        sample=", ".join(changed[:3])
        more=f" (+{len(changed)-3} more)" if len(changed)>3 else ""
        return "STALE",f"relevant verification input changed since the retained run: {sample}{more}",digest,changed
    return "CURRENT","all inputs relevant to this evidence still match the retained run",digest,[]


def evidence_run_manifest(junit_root,allure_index):
    start_ms,end_ms,start_iso=junit_suite_window(junit_root)
    allure_rows=[row for rows in allure_index.values() for row in rows]
    allure_digest=sha256_text(stable_json(sorted((row["path"],row["sha256"]) for row in allure_rows)))
    run_inputs=load_evidence_run_inputs()
    subjects={
      "junit":{"path":str(JUNIT_PATH.relative_to(ROOT)),"sha256":sha256_file(JUNIT_PATH)},
      "allure":{"path":str(ALLURE_RESULTS_DIR.relative_to(ROOT)),"results":len(allure_rows),"aggregate_sha256":allure_digest},
      "coverage":{"path":str(COVERAGE_JSON_PATH.relative_to(ROOT)),"sha256":sha256_file(COVERAGE_JSON_PATH)},
      "coverage_db":{"path":str(COVERAGE_DB.relative_to(ROOT)),"sha256":sha256_file(COVERAGE_DB)},
      "input_snapshot":{
        "path":str(EVIDENCE_RUN_INPUTS_PATH.relative_to(ROOT)),
        "sha256":sha256_file(EVIDENCE_RUN_INPUTS_PATH),
        "input_set_sha256":run_inputs.get("input_set_sha256"),
      },
    }
    run_id="evidence-"+sha256_text(stable_json(subjects))[:16]
    manifest={
      "schema":"ternforge-evidence-run-provenance-1",
      "run_id":run_id,
      "git_head":run_inputs.get("git_head") or "UNKNOWN",
      "projected_from_git_head":git_sha(),
      "execution":{"started_at":start_iso,"start_ms":start_ms,"end_ms":end_ms},
      "inputs":{
        "captured_at":run_inputs.get("captured_at"),
        "input_set_sha256":run_inputs.get("input_set_sha256"),
        "count":len(run_inputs.get("inputs") or {}),
        "run_bound":bool((run_inputs.get("_run_binding") or {}).get("bound")),
        "run_binding_basis":(run_inputs.get("_run_binding") or {}).get("basis"),
      },
      "subjects":subjects,
      "builder":{
        "pytest":package_version_or_unknown("pytest"),
        "pytest_bdd":package_version_or_unknown("pytest-bdd"),
        "allure_pytest":package_version_or_unknown("allure-pytest"),
        "py_lib_testkit":package_version_or_unknown("py-lib-testkit"),
        "coverage":package_version_or_unknown("coverage"),
      },
    }
    EVIDENCE_RUN_PROVENANCE_PATH.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def execution_link_state(junit_state,allure_row,suite_start_ms,suite_end_ms,nodeid):
    if not allure_row:
        return {"coherent":False,"freshness":"UNKNOWN","reason":"no exact Allure result with a Ternforge observation for this nodeid"}
    if allure_row.get("observation_nodeid")!=nodeid:
        return {"coherent":False,"freshness":"UNKNOWN","reason":"Allure observation nodeid does not match the JUnit testcase"}
    allure_status=str(allure_row.get("status") or "unknown").lower()
    expected={"passed":"passed","failed":"failed","skipped":"skipped"}.get(junit_state,junit_state)
    if allure_status!=expected:
        return {"coherent":False,"freshness":"UNKNOWN","reason":f"JUnit status {junit_state} disagrees with Allure status {allure_status}"}
    start=allure_row.get("start")
    stop=allure_row.get("stop")
    if not isinstance(start,(int,float)) or not isinstance(stop,(int,float)) or suite_start_ms is None or suite_end_ms is None:
        return {"coherent":False,"freshness":"UNKNOWN","reason":"execution timestamps are missing"}
    slack_ms=5000
    if start<suite_start_ms-slack_ms or stop>suite_end_ms+slack_ms:
        return {"coherent":False,"freshness":"STALE","reason":"Allure result is outside the retained JUnit run window"}
    return {"coherent":True,"freshness":"CURRENT","reason":"JUnit and exact Allure result agree and belong to the same retained execution window"}


def current_context_files(nodeid):
    if not COVERAGE_DB.exists():
        return []
    try:
        data=CoverageData(basename=str(COVERAGE_DB))
        data.read()
        data.set_query_context(f"{nodeid}|run")
        rows=[]
        for measured in data.measured_files():
            if not (data.lines(measured) or []):
                continue
            path=Path(measured)
            try:
                rows.append(str(path.resolve().relative_to(ROOT.resolve())))
            except Exception:
                rows.append(str(path))
        return sorted(set(rows))
    except Exception:
        return []


DEPTH_REACH_ORDER=["component","component_integration","system","system_integration"]
DEPTH_REPRESENTATION_ORDER=["synthetic_abstract","surrogate_simulated","representative","actual"]
DEPTH_MS_ORDER=["na","l0","l1","l2","l3","l4"]
DEPTH_TEST_EVIDENCE_KINDS={"unit","bdd","integration","property","e2e"}


def calibrating_experiment_state(needs,experiment_id):
    need=needs.get(experiment_id) or {}
    capsule_name=Path(str(need.get("docname") or "")).parent.name
    capsules=sorted(ROOT.glob(f"experiments/*/{capsule_name}")) if capsule_name else []
    if need.get("type")!="exp" or len(capsules)!=1:
        return {"id":experiment_id,"valid":False,"errors":["calibrating capsule is not resolvable from the graph"]}
    try:
        from ternforge_docops._internal.experiments.report import validate_report
        errors=list(validate_report(capsules[0]))
    except Exception as exc:
        errors=[f"capsule report validation could not run: {type(exc).__name__}"]
    return {
      "id":experiment_id,
      "title":need.get("title") or experiment_id,
      "capsule":str(capsules[0].relative_to(ROOT)),
      "valid":not errors,
      "errors":errors,
    }


MODEL_VALIDATION_CACHE={}


def depth_model_validation_records():
    """Derive M&S validation (NASA-STD-7009A validation factor) from the graph.

    L2 needs a declared intended use plus at least one Engineering Experiment
    that `calibrates` the model and whose captured capsule report is still
    valid. Everything else stays L0; L1/L3/L4 have no structured source yet.
    """
    needs_path=ROOT/"docs/_build/html/needs.json"
    key=sha256_text(needs_path.read_text()) if needs_path.exists() else ""
    if key not in MODEL_VALIDATION_CACHE:
        MODEL_VALIDATION_CACHE.clear()
        MODEL_VALIDATION_CACHE[key]=derive_model_validation_records()
    return json.loads(json.dumps(MODEL_VALIDATION_CACHE[key]))


def derive_model_validation_records():
    needs=current_needs()
    records={}
    for producer_id,need in sorted(needs.items()):
        if need.get("type")!="producer" or need.get("producer_role")!="test-substitute":
            continue
        intended_use=str(need.get("producer_purpose") or "").strip()
        experiments=[
          calibrating_experiment_state(needs,experiment_id)
          for experiment_id in sorted(need.get("calibrates_back") or [])
        ]
        valid=[row for row in experiments if row["valid"]]
        if intended_use and valid:
            level="l2"
            basis=(
              "Intended use is declared and "+", ".join(row["id"] for row in valid)
              +" calibrates this model against the live referent with a current captured report. "
              "No intended-domain coverage record exists, so L3 is not claimed."
            )
        elif not intended_use:
            level="l0"
            basis="No declared intended use, so no validation level above L0 can be claimed."
        elif experiments:
            level="l0"
            basis=(
              "Calibration is declared but its capsule report is not currently valid: "
              +"; ".join(f"{row['id']}: {', '.join(row['errors'])}" for row in experiments)
              +". Therefore L2 is not claimed."
            )
        else:
            level="l0"
            basis=(
              "Tool mechanics can be qualified, but no Engineering Experiment calibrates this model "
              "against a live referent. Therefore no validation level above L0 is claimed."
            )
        records[producer_id]={
          "title":need.get("title") or producer_id,
          "representation_fidelity":"surrogate_simulated",
          "ms_validation":level,
          "intended_use":intended_use or None,
          "referent":", ".join(f"{row['id']} {row['title']}" for row in valid) or None,
          "basis":basis,
          "calibration":[row["id"] for row in valid],
          "calibration_checks":experiments,
        }
    return records


def current_needs():
    path=ROOT/"docs/_build/html/needs.json"
    payload=json.loads(path.read_text())
    version=payload.get("current_version","")
    return (payload.get("versions") or {}).get(version,{}).get("needs") or {}


def junit_depth_rows():
    root=ET.parse(JUNIT_PATH).getroot()
    registry=normative_contract_registry()
    result=[]
    for testcase in root.iter("testcase"):
        classname=testcase.attrib.get("classname") or ""
        test_name=testcase.attrib.get("name") or ""
        nodeid=f"{classname.replace('.','/')}.py::{test_name}"
        props={
          prop.attrib.get("name"):prop.attrib.get("value")
          for prop in testcase.findall("./properties/property")
        }
        state="passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            state="failed"
        elif testcase.find("skipped") is not None:
            state="skipped"
        verifies_ref=str(props.get("verifies") or "")
        verifies_refs=parse_revisioned_verifies(verifies_ref)
        verifies=[
          contract_id
          for contract_id,revision in verifies_refs
          if contract_id in registry
          and revision==int(registry[contract_id]["revision"])
        ]
        verifies_revision_mismatches=[
          {
            "contract_id":contract_id,
            "declared_revision":revision,
            "current_revision":(
              int(registry[contract_id]["revision"])
              if contract_id in registry else None
            ),
          }
          for contract_id,revision in verifies_refs
          if contract_id not in registry
          or revision!=int(registry[contract_id]["revision"])
        ]
        result.append({
          "nodeid":nodeid,
          "result":state,
          "seconds":float(testcase.attrib["time"]) if testcase.attrib.get("time") else None,
          "verification_kind":props.get("verification_kind"),
          "verifies":verifies,
          "verifies_refs":[
            {"contract_id":contract_id,"revision":revision}
            for contract_id,revision in verifies_refs
          ],
          "verifies_revision_mismatches":verifies_revision_mismatches,
          "source_path":nodeid.split("::",1)[0],
          "gherkin_feature":props.get("gherkin_feature"),
          "gherkin_scenario":props.get("gherkin_scenario"),
        })
    return result


def depth_boundary_fact(allure_row):
    observations=(allure_row or {}).get("observations") or []
    zero_provider_http=False
    positive_provider_http=[]
    replay_rows=[]
    substitute_rows=[]
    direct_rows=[]
    for observation in observations:
        kind=observation.get("kind")
        payload=observation.get("payload") or {}
        if kind=="boundary-interaction-check" and payload.get("boundary")=="provider-http":
            requests=payload.get("requests_received")
            if isinstance(requests,int):
                if requests==0:
                    zero_provider_http=True
                else:
                    positive_provider_http.append(payload)
        elif kind=="external-replay" and int(payload.get("play_count") or 0)>0:
            replay_rows.append(payload)
        elif kind=="external-substitute":
            substitute_rows.append(payload)
        elif kind=="external-direct":
            direct_rows.append(payload)
    if direct_rows:
        row=direct_rows[-1]
        return "direct","direct_runtime_observation",row,None
    if replay_rows:
        row=replay_rows[-1]
        return "replay","vcr_play_count",{
          "play_count":int(row.get("play_count") or 0),
          "all_played":bool(row.get("all_played")),
        },str(row.get("producer_id") or "PRODUCER_VCR")
    if positive_provider_http:
        row=positive_provider_http[-1]
        producer=next(
          (
            str(candidate.get("producer_id"))
            for candidate in reversed(substitute_rows)
            if candidate.get("producer_id")
          ),
          "PRODUCER_SCRIPTED_HTTP_SERVER",
        )
        return "substitute","request_journal",{
          "requests_received":int(row.get("requests_received") or 0),
          "sample_paths":list(row.get("sample_paths") or []),
        },producer
    if substitute_rows and not zero_provider_http:
        row=substitute_rows[-1]
        producer=str(row.get("producer_id") or "") or None
        return "substitute","substitute_observation",{
          key:row.get(key)
          for key in ("producer","producer_id","boundary","mode","transport","target")
          if row.get(key) is not None
        },producer
    if zero_provider_http:
        return "none","no_boundary_event",{"requests_received":0},None
    return "none","no_boundary_event",{},None


def depth_test_level(nodeid,verification_kind,boundary):
    product=[
      path for path in current_context_files(nodeid)
      if path.startswith("src/llm_router/")
    ]
    has_router_api="src/llm_router/_api/router.py" in product
    has_runtime=any(path.startswith("src/llm_router/_internal/runtime/") for path in product)
    has_provider=any(path.startswith("src/llm_router/_internal/providers/") for path in product)
    if boundary!="none" and has_router_api and has_runtime and has_provider:
        level="system_integration"
        basis="public router entry → runtime → provider adapter → observed external boundary"
    elif has_router_api and has_runtime:
        level="system"
        basis="public router entry → runtime without a material external boundary"
    elif verification_kind=="integration" or (verification_kind=="bdd" and len(product)>1):
        level="component_integration"
        basis="multiple production components execute across an internal/component boundary"
    else:
        level="component"
        basis="focused production component execution"
    return level,basis,product


def depth_test_fact(junit_row,allure_row,model_records):
    nodeid=junit_row["nodeid"]
    verification_kind=(allure_row or {}).get("verification_kind") or junit_row.get("verification_kind")
    boundary,boundary_basis,boundary_detail,model_producer=depth_boundary_fact(allure_row)
    level,level_basis,product=depth_test_level(nodeid,verification_kind,boundary)
    representation="actual" if boundary in {"none","direct"} else "surrogate_simulated"
    model_record=model_records.get(model_producer) or {}
    if representation=="actual":
        ms_validation="na"
        representation_basis="Actual target implementation participated and no material external surrogate was required by this evidence path."
        ms_basis="No material M&S/surrogate participates in this evidence path."
        calibration=[]
    else:
        ms_validation=str(model_record.get("ms_validation") or "l0")
        representation_basis=str(
          model_record.get("basis")
          or "A material external substitute/replay participates in this evidence path."
        )
        ms_basis=str(
          model_record.get("basis")
          or "No structured validation record supports promotion above L0."
        )
        calibration=list(model_record.get("calibration") or [])
    boundary_interactions=[
      dict(observation.get("payload") or {})
      for observation in (allure_row or {}).get("observations") or []
      if observation.get("kind") in {
        "boundary-interaction-check","external-substitute","external-replay","external-direct"
      }
    ]
    return {
      "nodeid":nodeid,
      "result":junit_row.get("result"),
      "verification_kind":verification_kind,
      "verifies":list(junit_row.get("verifies") or []),
      "system_reach":level,
      "system_reach_basis":level_basis,
      "boundary_mode":boundary,
      "boundary_evidence_basis":boundary_basis,
      "boundary_evidence_detail":boundary_detail,
      "boundary_interactions":boundary_interactions,
      "production_run_files":product,
      "legacy_scope_reach":{
        "component":"component",
        "component_integration":"integration_boundary",
        "system":"public_workflow",
        "system_integration":"public_workflow",
      }.get(level,"component"),
      "legacy_external_reach":{
        "none":"local","substitute":"substitute","replay":"replay","direct":"direct"
      }.get(boundary,"local"),
      "environment":"controlled",
      "environment_basis":"retained hermetic test execution; no representative or operational environment attestation is claimed",
      "representation_fidelity":representation,
      "representation_basis":representation_basis,
      "model_producer":model_producer,
      "ms_validation":ms_validation,
      "ms_validation_basis":ms_basis,
      "ms_validation_calibration":calibration,
      "runtime_fixtures":list((allure_row or {}).get("fixtures") or []),
      "runtime_markers":list((allure_row or {}).get("markers") or []),
      "source_path":junit_row.get("source_path"),
      "source_line":None,
      "gherkin_feature":junit_row.get("gherkin_feature"),
      "gherkin_scenario":junit_row.get("gherkin_scenario")
        or ((allure_row or {}).get("labels") or {}).get("story"),
    }


def depth_contract_universe(needs):
    normative={
      need_id:need
      for need_id,need in needs.items()
      if need.get("type") in {"req","treq"}
    }
    direct={
      need_id
      for need_id,need in normative.items()
      if DEPTH_TEST_EVIDENCE_KINDS.intersection(set(need.get("required_evidence") or []))
    }
    delegated={
      need_id
      for need_id,need in normative.items()
      if any(child in direct for child in need.get("derives_back") or [])
    }
    return sorted(direct|delegated)


def depth_direct_rows(contract_id,test_rows,needs,universe):
    rows=[row for row in test_rows if contract_id in (row.get("verifies") or [])]
    for child_id in (needs.get(contract_id) or {}).get("derives_back") or []:
        child=needs.get(child_id) or {}
        if child.get("type") not in {"req","treq"} or child_id in universe:
            continue
        rows.extend(
          row for row in test_rows
          if child_id in (row.get("verifies") or [])
        )
    return sorted({row["nodeid"]:row for row in rows}.values(),key=lambda row:row["nodeid"])


def depth_direct_contract(contract_id,rows):
    reach=max(rows,key=lambda row:DEPTH_REACH_ORDER.index(row["system_reach"]))["system_reach"]
    representation=max(
      rows,key=lambda row:DEPTH_REPRESENTATION_ORDER.index(row["representation_fidelity"])
    )["representation_fidelity"]
    representation_row=next(
      row for row in rows if row["representation_fidelity"]==representation
    )
    model_rows=[row for row in rows if row.get("ms_validation")!="na"]
    if model_rows:
        ms=max(model_rows,key=lambda row:DEPTH_MS_ORDER.index(row["ms_validation"]))["ms_validation"]
        ms_row=next(row for row in model_rows if row["ms_validation"]==ms)
        ms_nodeid=ms_row["nodeid"]
    else:
        ms="na"
        ms_nodeid=None
    return {
      "contract_id":contract_id,
      "system_reach":reach,
      "environment":"controlled",
      "basis":"direct_test_evidence",
      "test_count":len(rows),
      "nodeids":[row["nodeid"] for row in rows],
      "child_contracts":[],
      "representation_fidelity":representation,
      "representation_nodeid":representation_row["nodeid"],
      "ms_validation":ms,
      "ms_validation_nodeid":ms_nodeid,
    }


def depth_contract_rows(test_rows,needs,universe):
    cache={}
    universe_set=set(universe)

    def build(contract_id):
        if contract_id in cache:
            return cache[contract_id]
        direct=depth_direct_rows(contract_id,test_rows,needs,universe_set)
        if direct:
            cache[contract_id]=depth_direct_contract(contract_id,direct)
            return cache[contract_id]
        child_ids=[
          child
          for child in (needs.get(contract_id) or {}).get("derives_back") or []
          if child in universe_set
        ]
        children=[build(child) for child in child_ids]
        children=[row for row in children if row]
        if not children:
            cache[contract_id]={
              "contract_id":contract_id,
              "system_reach":"component",
              "environment":"controlled",
              "basis":"no_retained_test_evidence",
              "test_count":0,
              "nodeids":[],
              "child_contracts":child_ids,
              "representation_fidelity":"synthetic_abstract",
              "representation_nodeid":None,
              "ms_validation":"na",
              "ms_validation_nodeid":None,
            }
            return cache[contract_id]
        reach=min(
          (row["system_reach"] for row in children),
          key=DEPTH_REACH_ORDER.index,
        )
        representation=min(
          (row["representation_fidelity"] for row in children),
          key=DEPTH_REPRESENTATION_ORDER.index,
        )
        child_ms=[row["ms_validation"] for row in children if row["ms_validation"]!="na"]
        ms=min(child_ms,key=DEPTH_MS_ORDER.index) if child_ms else "na"
        nodeids=sorted({nodeid for row in children for nodeid in row.get("nodeids") or []})
        cache[contract_id]={
          "contract_id":contract_id,
          "system_reach":reach,
          "environment":"controlled",
          "basis":"weakest_child_contract",
          "test_count":len(nodeids),
          "nodeids":nodeids,
          "child_contracts":child_ids,
          "representation_fidelity":representation,
          "representation_nodeid":None,
          "ms_validation":ms,
          "ms_validation_nodeid":None,
        }
        return cache[contract_id]

    return [build(contract_id) for contract_id in universe]


def refresh_verification_depth_facts():
    global DEPTH,TEST_META
    needs=current_needs()
    junit_rows=junit_depth_rows()
    allure_index=allure_monitor_index()
    allure_rows=[row for rows in allure_index.values() for row in rows]
    allure_digest=sha256_text(stable_json(sorted(
      (row["path"],row["sha256"]) for row in allure_rows
    )))
    model_records=depth_model_validation_records()
    tests=[]
    duplicate_allure=[]
    for junit_row in junit_rows:
        matches=allure_index.get(junit_row["nodeid"]) or []
        if len(matches)!=1:
            duplicate_allure.append(junit_row["nodeid"])
        allure_row=matches[0] if len(matches)==1 else {}
        tests.append(depth_test_fact(junit_row,allure_row,model_records))
    universe=depth_contract_universe(needs)
    contracts=depth_contract_rows(tests,needs,universe)
    coverage_payload=json.loads(COVERAGE_JSON_PATH.read_text()) if COVERAGE_JSON_PATH.exists() else {}
    coverage_total=float((coverage_payload.get("totals") or {}).get("percent_covered") or 0.0)
    passed=sum(row.get("result")=="passed" for row in tests)
    coverage_contexts=sum(bool(row.get("production_run_files")) for row in tests)
    bdd_errors=sum(
      row.get("verification_kind")=="bdd"
      and (not row.get("gherkin_feature") or not row.get("gherkin_scenario"))
      for row in tests
    )
    testcase_needs=sum(need.get("type")=="testcase" for need in needs.values())
    branch=subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
    payload={
      "schema_version":4,
      "source_run":{
        "branch":branch,
        "commit":git_sha()[:12],
        "tests":len(tests),
        "passed":passed,
        "coverage_total_percent":round(coverage_total,2),
        "generated_at":utc_now(),
        "inputs":{
          "junit":{
            "path":str(JUNIT_PATH.relative_to(ROOT)),
            "sha256":sha256_file(JUNIT_PATH),
          },
          "allure":{
            "path":str(ALLURE_RESULTS_DIR.relative_to(ROOT)),
            "results":len(allure_rows),
            "aggregate_sha256":allure_digest,
          },
          "coverage":{
            "path":str(COVERAGE_JSON_PATH.relative_to(ROOT)),
            "sha256":sha256_file(COVERAGE_JSON_PATH),
          },
          "coverage_db":{
            "path":str(COVERAGE_DB.relative_to(ROOT)),
            "sha256":sha256_file(COVERAGE_DB),
          },
        },
        "methodology":"DEPTH-P05 · reproducible retained-evidence projection",
        "execution_environment_evidence":{
          "block_network_fixture_tests":sum("block_network" in row.get("runtime_fixtures",[]) for row in tests),
          "record_mode_fixture_tests":sum("record_mode" in row.get("runtime_fixtures",[]) for row in tests),
          "vcr_fixture_tests":sum("vcr" in row.get("runtime_fixtures",[]) for row in tests),
          "environment_attestation":"none",
          "classification":"controlled",
          "basis":"retained test runtime uses controlled network/record-mode fixtures; no representative or operational environment identity/conformance evidence exists",
        },
      },
      "classification":{
        "system_reach_order":DEPTH_REACH_ORDER,
        "system_reach_semantics":"Observed architectural/test-object reach aligned to ISTQB test-object boundaries: Component, Component integration, System, System integration. This does not infer a test-level label from verification_kind alone.",
        "environment_order":["controlled","representative","operational"],
        "environment_semantics":"Environment fidelity is independent of dependency interaction mode. Representative requires explicit, versioned environment conformance evidence. Operational requires execution identity from the actual operational platform.",
        "boundary_mode_order":["none","substitute","replay","direct"],
        "boundary_semantics":"Boundary mode is an orthogonal runtime fact. Substitute requires retained substitute/request evidence; replay requires a retained replay observation with play_count > 0; direct requires a retained direct-interaction observation.",
        "contract_rollup":"deepest direct test reach; an intentionally delegated parent uses the weakest child contract conservatively",
        "representation_fidelity_order":DEPTH_REPRESENTATION_ORDER,
        "representation_fidelity_semantics":"Synthetic/Abstract → Surrogate/Simulated → Representative → Actual. Representative means a non-live setup with explicit evidence that it represents the real target for this use; replay alone is not enough.",
        "ms_validation_order":DEPTH_MS_ORDER,
        "ms_validation_semantics":"NASA-STD-7009A validation-factor projection derived from the graph: L2 requires a declared intended use and a calibrating Engineering Experiment with a current captured report; every other surrogate stays L0.",
      },
      "tests":tests,
      "contracts":contracts,
      "audit":{
        "junit_cases":len(junit_rows),
        "runtime_evidence":len(junit_rows)-len(duplicate_allure),
        "coverage_contexts":coverage_contexts,
        "needs_testcases":testcase_needs,
        "nodeid_mismatches":len(duplicate_allure),
        "verifies_mismatches":sum(
          bool(row.get("verifies_revision_mismatches"))
          for row in tests
        ),
        "bdd_feature_scenario_errors":bdd_errors,
        "contracts":len(contracts),
        "actual_scripted_http_tests":sum(row.get("model_producer")=="PRODUCER_SCRIPTED_HTTP_SERVER" for row in tests),
        "actual_vcr_replay_tests":sum(row.get("boundary_mode")=="replay" for row in tests),
        "actual_fake_sdk_tests":sum(row.get("model_producer") in {"PRODUCER_GOOGLE_GENAI_FAKE_SDK","PRODUCER_GEMINI_WEBAPI_FAKE_SDK"} for row in tests),
        "actual_boundary_tests":sum(row.get("boundary_mode")!="none" for row in tests),
        "methodology_status":"P05 runtime facts regenerated from current retained JUnit + Allure + Coverage",
        "p05_model_records":len(model_records),
        "p05_ms_l2_calibrated_producers":sum(row.get("ms_validation")=="l2" for row in model_records.values()),
        "p05_ms_l3_l4_claimed":sum(row.get("ms_validation") in {"l3","l4"} for row in model_records.values()),
        "p05_generic_surrogates_validation":"L0",
      },
      "model_validation_records":model_records,
    }
    DEPTH_FACTS_PATH.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    DEPTH=payload
    TEST_META={row["nodeid"]:row for row in tests}
    return payload


def current_allure_aggregate(allure_index):
    rows=[row for values in allure_index.values() for row in values]
    return sha256_text(stable_json(sorted(
      (row["path"],row["sha256"]) for row in rows
    )))


def depth_run_artifacts_current(allure_index):
    inputs=((DEPTH.get("source_run") or {}).get("inputs") or {})
    expected={
      "junit":(inputs.get("junit") or {}).get("sha256"),
      "allure":(inputs.get("allure") or {}).get("aggregate_sha256"),
      "coverage":(inputs.get("coverage") or {}).get("sha256"),
      "coverage_db":(inputs.get("coverage_db") or {}).get("sha256"),
    }
    actual={
      "junit":sha256_file(JUNIT_PATH),
      "allure":current_allure_aggregate(allure_index),
      "coverage":sha256_file(COVERAGE_JSON_PATH),
      "coverage_db":sha256_file(COVERAGE_DB),
    }
    current=all(expected.get(key) and expected.get(key)==actual.get(key) for key in expected)
    if current:
        return True,"Depth facts are bound to this exact JUnit, Allure, coverage JSON and coverage DB"
    mismatches=[key for key in expected if expected.get(key)!=actual.get(key)]
    return False,"Depth artifact mismatch: "+", ".join(mismatches)


def current_depth_classification(nodeid,depth,allure_row):
    if not depth:
        return {
          "current":False,
          "basis":"no current Depth fact exists for this testcase",
          "level":"unknown",
          "boundary":"unknown",
          "representation":"unknown",
          "ms_validation":None,
        }
    observed_boundary,_,_,observed_producer=depth_boundary_fact(allure_row)
    verification_kind=(allure_row or {}).get("verification_kind") or depth.get("verification_kind")
    observed_level,_,observed_product=depth_test_level(
      nodeid,verification_kind,observed_boundary
    )
    observed_representation=(
      "actual" if observed_boundary in {"none","direct"} else "surrogate_simulated"
    )
    model_record=depth_model_validation_records().get(observed_producer) or {}
    observed_ms=(
      "na"
      if observed_representation=="actual"
      else str(model_record.get("ms_validation") or "l0")
    )
    expected_product=sorted(depth.get("production_run_files") or [])
    boundary_basis=str(depth.get("boundary_evidence_basis") or "")
    boundary_detail=depth.get("boundary_evidence_detail") or {}
    if boundary_basis=="no_boundary_event" and boundary_detail.get("requests_received")==0:
        boundary_basis="current retained provider-boundary observation recorded zero HTTP requests"
    elif boundary_basis=="request_journal" and isinstance(boundary_detail.get("requests_received"),int):
        boundary_basis=(
          "current retained provider-boundary observation recorded "
          f"{boundary_detail['requests_received']} HTTP request(s)"
        )
    elif boundary_basis=="vcr_play_count" and isinstance(boundary_detail.get("play_count"),int):
        boundary_basis=(
          f"current retained VCR replay recorded {boundary_detail['play_count']} played interaction(s)"
        )
    checks={
      "production coverage":sorted(observed_product)==expected_product,
      "Test level":observed_level==depth.get("system_reach"),
      "Boundary":observed_boundary==depth.get("boundary_mode"),
      "Representation":observed_representation==depth.get("representation_fidelity"),
      "M&S":observed_ms==depth.get("ms_validation"),
      "model producer":observed_producer==depth.get("model_producer"),
    }
    current=all(checks.values())
    mismatches=[name for name,value in checks.items() if not value]
    return {
      "current":current,
      "basis":(
        "current runtime/coverage facts reproduce the retained Depth classification"
        if current else
        "Depth classification mismatch: "+", ".join(mismatches)
      ),
      "level":depth.get("system_reach") if current else "unknown",
      "level_basis":depth.get("system_reach_basis") or "",
      "boundary":depth.get("boundary_mode") if current else "unknown",
      "boundary_basis":boundary_basis,
      "representation":depth.get("representation_fidelity") if current else "unknown",
      "representation_basis":depth.get("representation_basis") or "",
      "ms_validation":depth.get("ms_validation") if current else None,
    }


def junit_monitor_actual():
    if not JUNIT_PATH.exists():
        return {}
    root=ET.parse(JUNIT_PATH).getroot()
    allure_index=allure_monitor_index()
    depth_run_current,depth_run_basis=depth_run_artifacts_current(allure_index)
    run_inputs=load_evidence_run_inputs()
    _,_,current_input_digest=current_input_snapshot(run_inputs)
    manifest=evidence_run_manifest(root,allure_index)
    suite_start_ms,suite_end_ms,_=junit_suite_window(root)
    qualification=load_evidence_qualification()
    criterion_contracts=verification_criterion_contracts()
    registry=normative_contract_registry()
    actual=defaultdict(list)
    snapshot_inputs=dict(run_inputs.get("inputs") or {})
    for testcase in root.iter("testcase"):
        props={
          prop.attrib.get("name"):prop.attrib.get("value")
          for prop in testcase.findall("./properties/property")
        }
        coverage_item=props.get("coverage_item")
        coverage_path=props.get("coverage_path")
        if not coverage_item:
            continue
        classname=testcase.attrib.get("classname") or ""
        test_name=testcase.attrib.get("name") or ""
        nodeid=f"{classname.replace('.','/')}.py::{test_name}"
        depth=TEST_META.get(nodeid) or {}
        state="passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            state="failed"
        elif testcase.find("skipped") is not None:
            state="skipped"
        verifies_ref=props.get("verifies") or ""
        criterion_contract=criterion_contracts.get(coverage_item)
        if not criterion_contract:
            raise RuntimeError(
              f"{nodeid}: coverage_item references unknown Verification criterion "
              f"{coverage_item!r}"
            )
        revision_current=verifies_current_revision(
          verifies_ref,criterion_contract,registry
        )
        requirement_id=criterion_contract if revision_current else None
        source_path=nodeid.split("::",1)[0]
        retained_source_path=props.get("source_path") or ""
        retained_source_sha=props.get("source_sha256") or ""
        snapshot_source_sha=snapshot_inputs.get(source_path)
        relevant_inputs=evidence_input_paths(
          run_inputs,nodeid,criterion_contract,source_path,props.get("gherkin_feature"),registry
        )
        input_state,input_basis,relevant_input_digest,changed_inputs=evidence_input_state(
          run_inputs,relevant_inputs
        )
        traceability_complete=bool(
          requirement_id
          and criterion_contract==requirement_id
          and source_path
          and retained_source_path==source_path
          and retained_source_sha
          and retained_source_sha==snapshot_source_sha
          and (ROOT/source_path).exists()
        )
        matches=allure_index.get(nodeid) or []
        allure_row=matches[0] if len(matches)==1 else None
        link=execution_link_state(state,allure_row,suite_start_ms,suite_end_ms,nodeid)
        coverage_current=coverage_context_present(nodeid)
        depth_state=current_depth_classification(nodeid,depth,allure_row)
        classification_current=bool(depth_run_current and depth_state.get("current"))
        reach=depth_state.get("level") or "unknown"
        reach_basis=(
          depth_state.get("level_basis")
          if classification_current
          else depth_run_basis+"; "+str(depth_state.get("basis") or "")
        )
        boundary=depth_state.get("boundary") or "unknown"
        boundary_basis=(
          depth_state.get("boundary_basis")
          if classification_current
          else depth_run_basis+"; "+str(depth_state.get("basis") or "")
        )
        representation=depth_state.get("representation") or "unknown"
        representation_basis=(
          depth_state.get("representation_basis")
          if classification_current
          else depth_run_basis+"; "+str(depth_state.get("basis") or "")
        )
        ms_validation=depth_state.get("ms_validation") if classification_current else None
        provenance_complete=bool(
          traceability_complete
          and len(matches)==1
          and link.get("coherent")
          and coverage_current
          and classification_current
          and (allure_row or {}).get("sha256")
          and (allure_row or {}).get("observation_sha256")
          and (allure_row or {}).get("observation_aggregate_sha256")
          and manifest.get("subjects",{}).get("junit",{}).get("sha256")
          and manifest.get("subjects",{}).get("coverage",{}).get("sha256")
          and manifest.get("subjects",{}).get("input_snapshot",{}).get("sha256")
        )
        producer_ids=list((allure_row or {}).get("producer_ids") or [])
        producer_status,producer_basis=producer_chain_status(producer_ids,qualification)
        link_freshness=str(link.get("freshness") or "UNKNOWN").upper()
        if link_freshness=="STALE" or input_state=="STALE":
            freshness="STALE"
            freshness_basis=input_basis if input_state=="STALE" else str(link.get("reason") or "retained execution is stale")
        elif link_freshness=="CURRENT" and input_state=="CURRENT" and coverage_current:
            freshness="CURRENT"
            freshness_basis="exact JUnit/Allure execution belongs to the retained run and all captured verification inputs still match byte-for-byte"
        else:
            freshness="UNKNOWN"
            reasons=[]
            if link_freshness!="CURRENT":
                reasons.append(str(link.get("reason") or "run membership is unknown"))
            if input_state!="CURRENT":
                reasons.append(input_basis)
            if not coverage_current:
                reasons.append("matching current coverage run context is missing")
            freshness_basis="; ".join(reason for reason in reasons if reason) or "current-run membership could not be established"
        provenance_basis=(
          "revision-pinned Requirement and coverage-item binding; exact test-source digest from run start; exact JUnit/Allure status agreement; current coverage-derived reach/representation; observed boundary fact; SHA-256-bound run artifacts"
          if provenance_complete else
          "one or more required links between Requirement, testcase source, retained run, execution observation, coverage context, boundary fact or artifact digest are missing/inconsistent"
        )
        full_producer_chain=list(dict.fromkeys(producer_ids+[
          "PRODUCER_LLM_ROUTER_TRACE_BRIDGE",
          "PRODUCER_ASSURANCE_ADAPTER",
          "PRODUCER_REQUIREMENT_MONITOR",
        ]))
        actual[coverage_item].append({
          "coverage_item":coverage_item,
          "coverage_path":coverage_path or None,
          "nodeid":nodeid,
          "result":state,
          "verifies_revision_current":revision_current,
          "required_revision":int(registry[criterion_contract]["revision"]),
          "kind":depth.get("verification_kind") or props.get("verification_kind") or (allure_row or {}).get("verification_kind"),
          "level":reach,
          "level_basis":reach_basis,
          "boundary":boundary,
          "boundary_basis":boundary_basis,
          "representation":representation,
          "representation_basis":representation_basis,
          "ms_validation":ms_validation,
          "provenance":"COMPLETE" if provenance_complete else "INCOMPLETE",
          "provenance_scope":"full_chain",
          "provenance_basis":provenance_basis,
          "producer_qualification":producer_status,
          "producer_qualification_scope":"full_chain",
          "producer_qualification_basis":producer_basis,
          "producer_ids":full_producer_chain,
          "freshness":freshness,
          "freshness_basis":freshness_basis,
          "freshness_input_count":len(relevant_inputs),
          "freshness_changed_inputs":changed_inputs,
          "freshness_input_sha256":relevant_input_digest,
          "run_id":manifest.get("run_id"),
          "source_path":source_path or None,
          "source_sha256":retained_source_sha or None,
          "current_source_sha256":sha256_file(ROOT/source_path) if source_path and (ROOT/source_path).exists() else None,
          "source_url":repo_blob_url(source_path) if source_path else None,
          "evidence_url":test_evidence_url(nodeid),
          "provenance_manifest":{
            "git_head":manifest.get("git_head"),
            "projected_from_git_head":manifest.get("projected_from_git_head"),
            "junit_sha256":manifest.get("subjects",{}).get("junit",{}).get("sha256"),
            "coverage_sha256":manifest.get("subjects",{}).get("coverage",{}).get("sha256"),
            "input_snapshot_sha256":manifest.get("subjects",{}).get("input_snapshot",{}).get("sha256"),
            "retained_input_set_sha256":manifest.get("inputs",{}).get("input_set_sha256"),
            "current_input_set_sha256":current_input_digest,
            "allure_result":(allure_row or {}).get("path"),
            "allure_result_sha256":(allure_row or {}).get("sha256"),
            "test_execution_observation":(allure_row or {}).get("observation_path"),
            "test_execution_observation_sha256":(allure_row or {}).get("observation_sha256"),
            "all_verification_observations_sha256":(allure_row or {}).get("observation_aggregate_sha256"),
        },
        })
    return {
      item_id:sorted(rows,key=lambda row:row.get("nodeid") or "")
      for item_id,rows in actual.items()
    }


def evidence_classification_index():
    """Classify every retained testcase once, from runtime facts, for all monitors."""
    if not JUNIT_PATH.exists():
        return {}
    root=ET.parse(JUNIT_PATH).getroot()
    allure_index=allure_monitor_index()
    depth_run_current,depth_run_basis=depth_run_artifacts_current(allure_index)
    qualification=load_evidence_qualification()
    index={}
    for testcase in root.iter("testcase"):
        classname=testcase.attrib.get("classname") or ""
        nodeid=f"{classname.replace('.','/')}.py::{testcase.attrib.get('name') or ''}"
        result="passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            result="failed"
        elif testcase.find("skipped") is not None:
            result="skipped"
        matches=allure_index.get(nodeid) or []
        allure_row=matches[0] if len(matches)==1 else None
        depth_state=current_depth_classification(nodeid,TEST_META.get(nodeid) or {},allure_row)
        current=bool(depth_run_current and depth_state.get("current"))
        producer_ids=list((allure_row or {}).get("producer_ids") or [])
        chains={}
        for monitor_producer in ("PRODUCER_REQUIREMENT_MONITOR","PRODUCER_UPPER_ASSURANCE_MONITOR"):
            status,basis=producer_chain_status(producer_ids,qualification,monitor_producer)
            chains[monitor_producer]={
              "status":status,
              "basis":basis,
              "producer_ids":list(dict.fromkeys(producer_ids+[
                "PRODUCER_LLM_ROUTER_TRACE_BRIDGE","PRODUCER_ASSURANCE_ADAPTER",monitor_producer,
              ])),
            }
        index[nodeid]={
          "result":result,
          "classification_current":current,
          "classification_basis":(
            depth_state.get("basis") if current
            else depth_run_basis+"; "+str(depth_state.get("basis") or "")
          ),
          "level":depth_state.get("level") if current else "unknown",
          "boundary":depth_state.get("boundary") if current else "unknown",
          "representation":depth_state.get("representation") if current else "unknown",
          "producer_chains":chains,
        }
    return index


def parse_fault_items(raw):
    if not raw:
        return []
    try:
        rows=json.loads(raw)
    except Exception:
        return []
    if not isinstance(rows,list):
        return []
    result=[]
    for row in rows:
        if not isinstance(row,dict):
            continue
        contract_id=str(row.get("contract_id") or "")
        fault_class=str(row.get("fault_class") or "")
        if contract_id and fault_class:
            result.append({
              "contract_id":contract_id,
              "fault_class":fault_class,
            })
    return result


def junit_fault_actual(policy):
    if not JUNIT_PATH.exists():
        return {}
    root=ET.parse(JUNIT_PATH).getroot()
    allure_index=allure_monitor_index()
    run_inputs=load_evidence_run_inputs()
    input_state,input_basis,_=current_input_snapshot(run_inputs)
    snapshot_inputs=dict(run_inputs.get("inputs") or {})
    suite_start_ms,suite_end_ms,_=junit_suite_window(root)
    qualification=load_evidence_qualification()
    registry=normative_contract_registry()
    declared=defaultdict(lambda:defaultdict(list))
    target_cache={}

    for testcase in root.iter("testcase"):
        props={
          prop.attrib.get("name"):prop.attrib.get("value")
          for prop in testcase.findall("./properties/property")
        }
        fault_items=parse_fault_items(props.get("fault_items"))
        if not fault_items:
            continue

        classname=testcase.attrib.get("classname") or ""
        test_name=testcase.attrib.get("name") or ""
        nodeid=f"{classname.replace('.','/')}.py::{test_name}"
        state="passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            state="failed"
        elif testcase.find("skipped") is not None:
            state="skipped"

        matches=allure_index.get(nodeid) or []
        allure_row=matches[0] if len(matches)==1 else None
        link=execution_link_state(
          state,allure_row,suite_start_ms,suite_end_ms,nodeid
        )
        source_path=nodeid.split("::",1)[0]
        retained_source_path=props.get("source_path") or ""
        retained_source_sha=props.get("source_sha256") or ""
        source_current=bool(
          input_state=="CURRENT"
          and source_path
          and retained_source_path==source_path
          and retained_source_sha
          and retained_source_sha==snapshot_inputs.get(source_path)
        )
        producer_status,producer_basis=producer_chain_status(
          list((allure_row or {}).get("producer_ids") or []),
          qualification,
        )
        observations=(allure_row or {}).get("observations") or []
        verifies_ref=props.get("verifies") or ""

        for declaration in fault_items:
            contract_id=declaration["contract_id"]
            fault_class=declaration["fault_class"]
            revision_current=verifies_current_revision(
              verifies_ref,contract_id,registry
            )
            if contract_id not in target_cache:
                target_cache[contract_id]=requirement_monitor_target(contract_id,policy)
            target=target_cache[contract_id]
            if not target:
                raise RuntimeError(
                  f"{nodeid}: fault_item references contract without a Verification Profile: "
                  f"{contract_id}"
                )
            class_state={
              item["id"]:item["state"]
              for group in (target.get("fault_groups") or [])
              for item in (group.get("items") or [])
            }
            if fault_class not in class_state:
                raise RuntimeError(
                  f"{nodeid}: fault_item references unknown project fault class "
                  f"{fault_class!r} for {contract_id}"
                )
            if class_state[fault_class]=="na":
                raise RuntimeError(
                  f"{nodeid}: fault_item cannot challenge N/A class "
                  f"{fault_class!r} for {contract_id}"
                )
            matching=[
              row for row in observations
              if row.get("kind")=="fault-injection"
              and (row.get("payload") or {}).get("contract_id")==contract_id
              and (row.get("payload") or {}).get("fault_class")==fault_class
            ]
            observed=bool(
              revision_current
              and len(matches)==1
              and link.get("coherent")
              and link.get("freshness")=="CURRENT"
              and source_current
              and matching
            )
            detected=bool(
              observed
              and state=="passed"
              and producer_status=="QUALIFIED"
            )
            payload=(matching[-1].get("payload") or {}) if matching else {}
            declared[contract_id][fault_class].append({
              "nodeid":nodeid,
              "result":state,
              "verifies_revision_current":revision_current,
              "required_revision":(
                int(registry[contract_id]["revision"])
                if contract_id in registry else None
              ),
              "exercised":observed,
              "detected":detected,
              "mechanism":payload.get("mechanism"),
              "details":payload.get("details") or {},
              "producer_qualification":producer_status,
              "producer_qualification_basis":producer_basis,
              "freshness":(
                "CURRENT"
                if observed else
                ("STALE" if input_state=="STALE" or link.get("freshness")=="STALE" else "UNKNOWN")
              ),
              "freshness_basis":(
                str(link.get("reason") or input_basis)
                if not observed else
                "matching declared fault challenge and runtime injection observation belong to the current retained run"
              ),
              "evidence_url":test_evidence_url(nodeid),
              "observation_path":matching[-1].get("path") if matching else None,
              "observation_sha256":matching[-1].get("sha256") if matching else None,
            })

    result={}
    for contract_id,classes in declared.items():
        result[contract_id]={}
        for fault_class,rows in classes.items():
            exercised=bool(rows) and all(row["exercised"] for row in rows)
            detected=bool(rows) and exercised and all(row["detected"] for row in rows)
            result[contract_id][fault_class]={
              "exercised":exercised,
              "detected":detected,
              "declared_paths":len(rows),
              "exercised_paths":sum(row["exercised"] for row in rows),
              "detected_paths":sum(row["detected"] for row in rows),
              "source":"retained_test_fault_challenge",
              "evidence_url":rows[0].get("evidence_url") if len(rows)==1 else None,
              "rows":sorted(rows,key=lambda row:row["nodeid"]),
            }
    return result


def implementation_fault_plans(test_rows=None):
    """What the campaign may challenge per contract, and which arid rules apply to it:
    every Test Plan rule except those its profile turns off."""
    needs=current_needs()
    scopes=IMPL_FAULTS.resolve_impl_scopes(ROOT,needs)
    owners=IMPL_FAULTS.line_owners(scopes)
    descendants=IMPL_FAULTS.descendants_map(needs)
    test_rows=junit_depth_rows() if test_rows is None else test_rows
    policy=project_monitor_policy()
    rules=[rule["id"] for rule in policy.get("arid_rules") or []]
    plans={}
    for contract_id,need in sorted(needs.items()):
        if need.get("type") not in {"req","treq"}:
            continue
        plan=IMPL_FAULTS.contract_plan(contract_id,scopes,owners,descendants,test_rows)
        overrides={row["rule"] for row in (requirement_monitor_target(contract_id,policy) or {}).get("arid_overrides") or []}
        plan["arid_rules"]=[rule for rule in rules if rule not in overrides]
        plans[contract_id]=plan
    return plans


def retained_campaign_entry_state(entry,plan,shared_sha256,test_rows):
    """Current only when engine, scope, tests and every input still match, and the
    retained engine report is the exact file the campaign recorded."""
    run=entry.get("run") or {}
    state,reason=IMPL_FAULTS.entry_state(
      entry,plan,shared_sha256,IMPL_FAULTS.contract_inputs(ROOT,plan,test_rows)
    )
    if state!="current":
        return state,reason
    report_path=ROOT/str(run.get("report_path") or "")
    if run.get("returncode")!=0 or not run.get("report_path"):
        return "engine_error","the mutation engine did not finish cleanly"
    if not report_path.is_file() or sha256_file(report_path)!=run.get("report_sha256"):
        return "report_mismatch","the retained engine report is missing or altered"
    return "current",""


def for_each_in_copies(items,work):
    """Run work(item, copy_root) for every item, as many at once as the engine allows, each in a
    copy of the working tree that no other run uses at the same time."""
    workers=min(IMPL_FAULTS.engine_workers(),len(items))
    if not workers:
        return
    with tempfile.TemporaryDirectory(prefix="ternforge-mutation-copies-") as scratch:
        free=[IMPL_FAULTS.working_tree_copy(ROOT,Path(scratch)/f"copy-{index}") for index in range(workers)]
        lock=threading.Lock()

        def run(item):
            with lock:
                copy_root=free.pop()
            try:
                work(item,copy_root)
            finally:
                with lock:
                    free.append(copy_root)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in as_completed([pool.submit(run,item) for item in items]):
                future.result()


def refresh_implementation_fault_campaign(contract_ids=None,full=False):
    """Run pytest-gremlins where the retained result is missing or no longer current.

    Only mutants on each contract's attributable @impl lines are executed. A contract
    is re-run when the engine, its scope, its passing tests, its own test inputs, or
    any shared input (product code, test support, dependencies) changed; `full`
    re-runs every contract regardless.
    """
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    shared=IMPL_FAULTS.shared_inputs(ROOT)
    shared_sha256=sha256_text(stable_json(shared))
    previous=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    started=time.monotonic()
    asking=contracts_asking_for_implementation_classes()
    campaign_ids=[
      contract_id for contract_id,plan in plans.items()
      if not plan.get("blocked") and contract_id in asking
    ]
    contracts={
      contract_id:entry
      for contract_id,entry in (previous.get("contracts") or {}).items()
      if contract_id in campaign_ids
    }
    selected=[]
    for contract_id in campaign_ids:
        if contract_ids and contract_id not in contract_ids:
            continue
        entry=contracts.get(contract_id)
        state,_=(
          retained_campaign_entry_state(entry,plans[contract_id],shared_sha256,test_rows)
          if entry else ("not_run","")
        )
        if full or state!="current":
            selected.append(contract_id)
    print(
      f"[IMPL] campaign: {len(selected)} to run, {len(campaign_ids)-len(selected)} still current, "
      f"{sum(bool(plan.get('blocked')) for plan in plans.values())} blocked",
      flush=True,
    )

    def write_campaign():
        IMPL_FAULT_CAMPAIGN_PATH.write_text(json.dumps({
          "schema":IMPL_FAULTS.SCHEMA,
          "engine":{"name":"pytest-gremlins","version":IMPL_FAULTS.GREMLINS_VERSION,"operators":list(IMPL_FAULTS.OPERATORS)},
          "engine_configuration":IMPL_FAULTS.engine_configuration(),
          "class_by_operator":IMPL_FAULTS.CLASS_BY_OPERATOR,
          "shared_input_scope":[*IMPL_FAULTS.SHARED_INPUT_SCOPE,"tests/**/*.py (support modules)",*IMPL_FAULTS.SHARED_EXPLICIT_INPUTS],
          "shared_inputs_sha256":shared_sha256,
          "head_sha":git_sha(),
          "updated_at":utc_now(),
          "last_full_run_at":utc_now() if full and not contract_ids else previous.get("last_full_run_at"),
          "contracts":contracts,
        },indent=2,sort_keys=True)+"\n")

    # Several contracts at once, each in its own copy of the working tree; each runs its mutants one by one.
    lock=threading.Lock()
    done=[0]

    def mutate(contract_id,copy_root):
        plan=plans[contract_id]
        raw_path=IMPL_FAULT_DIR/f"{contract_id}.gremlins.json"
        raw_path.unlink(missing_ok=True)
        run=IMPL_FAULTS.run_engine_isolated(ROOT,copy_root,plan,raw_path)
        entry={
          "engine":IMPL_FAULTS.engine_configuration(),
          "plan_key":IMPL_FAULTS.plan_key(plan),
          "shared_inputs_sha256":shared_sha256,
          "inputs":IMPL_FAULTS.contract_inputs(ROOT,plan,test_rows),
          "plan":plan,
          "run":{
            **{key:value for key,value in run.items() if key!="command"},
            "report_path":str(raw_path.relative_to(ROOT)) if run["report_retained"] else None,
            "report_sha256":sha256_file(raw_path) if run["report_retained"] else None,
            "finished_at":utc_now(),
          },
        }
        with lock:
            contracts[contract_id]=entry
            done[0]+=1
            print(f"[IMPL] {done[0]}/{len(selected)} {contract_id}: exit {run['returncode']} in {run['duration_seconds']}s",flush=True)
            write_campaign()

    for_each_in_copies(selected,mutate)
    write_campaign()
    print(f"[IMPL] campaign finished in {round(time.monotonic()-started,1)}s",flush=True)


# --- semantic mutants ----------------------------------------------------------------


def need_statement(need):
    match=re.search(r"\*\*Statement\.\*\*\s*(.*?)(?=\n\n\*\*|\Z)",str(need.get("content") or ""),flags=re.DOTALL)
    return " ".join(match.group(1).split()) if match else ""


def semantic_contexts(contract_id,target,needs):
    """What the generator is given for every selected target, and the digest each proposal is bound to."""
    need=needs.get(contract_id) or {}
    requirement={"id":contract_id,"revision":need.get("revision"),"statement":need_statement(need)}
    criteria=[str(value) for _key,value in sorted((target.get("item_descriptions") or {}).items())]
    return {
      selection["target"]:SEMANTIC.generation_context(ROOT,requirement,criteria,selection)
      for selection in target.get("semantic_mutants") or []
    }


def semantic_proposal_set(contract_id,target):
    """The frozen proposals of a contract, checked against its profile's selection: every proposal
    names a selected target and class, and no target has more proposals than its budget."""
    payload=SEMANTIC.load_proposals(contract_id)
    proposals=list(payload.get("proposals") or [])
    selections={row["target"]:row for row in target.get("semantic_mutants") or []}
    per_target=Counter(proposal.get("target") for proposal in proposals)
    for proposal in proposals:
        selection=selections.get(proposal.get("target"))
        if selection is None or selection["class"]!=proposal.get("class"):
            raise RuntimeError(f"{contract_id}: semantic mutant {proposal.get('id')} names no selected target and class")
        if per_target[proposal["target"]]>selection["budget"]:
            raise RuntimeError(f"{contract_id}: {proposal['target']} has more semantic mutants than its budget")
    return payload,proposals


def semantic_binding(contract_id,plan,test_rows,contexts,judgement=None):
    """Everything a retained cascade result depends on; any change makes it stale."""
    folder=SEMANTIC.PROPOSAL_ROOT/contract_id
    sources=sorted({key.split("::",1)[0] for key in contexts})
    return {
      "judgement_sha256":sha256_text(stable_json(judgement or {})),
      "equivalence_sha256":sha256_file(ROOT/".ai-bridge/survivor_equivalence.py"),
      "module_sha256":SEMANTIC.module_sha256(),
      "proposals_sha256":sha256_file(folder/"proposals.json"),
      "drafts_sha256":{path.name:sha256_file(path) for path in sorted((folder/"drafts").glob("*.draft.py"))} if (folder/"drafts").is_dir() else {},
      "contexts":{key:SEMANTIC.context_sha256(context) for key,context in sorted(contexts.items())},
      "tests":list(plan.get("tests") or []),
      "inputs":IMPL_FAULTS.contract_inputs(ROOT,plan,test_rows),
      "sources":{path:sha256_file(ROOT/path) for path in sources},
      "shared_inputs_sha256":sha256_text(stable_json(IMPL_FAULTS.shared_inputs(ROOT))),
    }


def load_assessments(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def save_assessments(path,assessments):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(dict(sorted(assessments.items())),indent=1,sort_keys=True)+"\n")


def semantic_assessment_prompt(contract_id,proposal,need):
    """What the assessors are asked about one semantic survivor, or None when it has no harness."""
    path,qualname=proposal["target"].split("::",1)
    source=(ROOT/path).read_text()
    harness=EQ.harness_for(source,qualname)
    if "reason" in harness:
        return None
    mutated=SEMANTIC.apply_replacement(source,qualname,proposal["replacement"]) or source
    owner=qualname.rpartition(".")[0]
    guide=EQ.input_guide(str(ROOT/path),harness)
    return EQ.assessor_prompt(
      target=qualname,original=EQ.function_source(source,qualname) or "",mutant=EQ.function_source(mutated,qualname) or "",
      harness=harness,context=f"Requirement {contract_id}: {need_statement(need)}\nRisk the change realizes: {proposal.get('risk')}"+(f"\n{guide}" if guide else ""),
      owner_source=EQ.class_source(source,owner) if owner else "",tried=SURVIVOR_TRIED,
    )


def current_answers(assessments,key,prompt):
    """The stored answers for one survivor that answered its current question, without the malformed."""
    entry=assessments.get(key) or {}
    if prompt is None or entry.get("prompt_sha256")!=sha256_text(prompt):
        return {}
    return {member:answer for member,answer in (entry.get("answers") or {}).items() if not answer.get("problems")}


def semantic_judgement_request(contract_id,proposals,needs,policy=None,state=None):
    """The survivor judgement a cascade run is handed: the Test Plan's settings, the calibration state
    and the assessors' current answers per proposal."""
    policy=policy or model_generation_policy()
    state=state or assessor_calibration_state(policy)
    assessments=load_assessments(SEMANTIC.PROPOSAL_ROOT/contract_id/"assessments.json")
    need=needs.get(contract_id) or {}
    answers={}
    for proposal in proposals:
        given=current_answers(assessments,proposal["id"],semantic_assessment_prompt(contract_id,proposal,need))
        if given:
            answers[proposal["id"]]=given
    return {
      "seconds":policy["judgement"]["symbolic_seconds"],"paths":policy["judgement"]["symbolic_paths"],"members":state["members"],
      "threshold":state["threshold"],"calibrated":state["calibrated"],"answers":answers,
    }


def ask_assessors(run,policy,*,purpose,contract_id,subject,prompt,entry,response_dir):
    """Ask every assessor that has not answered this question; return whether one answered."""
    prompt_sha=sha256_text(prompt)
    if entry.get("prompt_sha256")!=prompt_sha:
        entry.clear()
        entry.update({"prompt_sha256":prompt_sha,"answers":{}})
    members=[member for member in policy["assessors"] if member["key"] not in entry["answers"]]
    # The assessors answer the same question independently, so they are asked at once.
    results=run.call_many([
      {"role":f"assessor:{member['assessor']}","purpose":purpose,"contract_id":contract_id,"subject":subject,
       "system":EQ.ASSESSOR_SYSTEM,"prompt":prompt,"schema":EQ.ASSESSOR_SCHEMA,"response_dir":response_dir}
      for member in members
    ])
    asked=False
    for member,(_call,response,attempts) in zip(members,results):
        print(f"[ASSESS] {contract_id} · {subject} · assessor {member['assessor']}: "+attempts_text(attempts),flush=True)
        if response is not None:
            entry["answers"][member["key"]]=assessor_answer(response)
            asked=True
    return asked


def assess_contract_semantic(run,contract_id,target,needs,policy):
    """Ask the assessors about every undecided semantic survivor of one contract that a harness can
    judge and no confirmed input decided yet."""
    path=SEMANTIC_RESULTS_DIR/f"{contract_id}.json"
    retained=json.loads(path.read_text()) if path.exists() else {}
    _payload,proposals=semantic_proposal_set(contract_id,target)
    by_id={proposal["id"]:proposal for proposal in proposals}
    folder=SEMANTIC.PROPOSAL_ROOT/contract_id
    assessments=load_assessments(folder/"assessments.json")
    need=needs.get(contract_id) or {}
    asked=False
    for row in retained.get("results") or []:
        if row.get("outcome")!="undecided" or row["id"] not in by_id or (row.get("judgement") or {}).get("status") in {None,"found","not-applicable"}:
            continue
        prompt=semantic_assessment_prompt(contract_id,by_id[row["id"]],need)
        if prompt is None:
            continue
        entry=assessments.setdefault(row["id"],{})
        asked=ask_assessors(run,policy,purpose="survivor-assessment",contract_id=contract_id,subject=row["id"],prompt=prompt,entry=entry,response_dir=folder/"responses") or asked
    if asked:
        save_assessments(folder/"assessments.json",assessments)
    return asked


def semantic_selections(policy=None):
    policy=policy or project_monitor_policy()
    found={}
    for contract_id in verification_profile_contract_ids():
        target=requirement_monitor_target(contract_id,policy) or {}
        if target.get("semantic_mutants"):
            found[contract_id]=target
    return found


def load_symbolic_cache():
    return json.loads(SYMBOLIC_CACHE_PATH.read_text()) if SYMBOLIC_CACHE_PATH.exists() else {}


def save_symbolic_cache(cache):
    SYMBOLIC_CACHE_PATH.parent.mkdir(parents=True,exist_ok=True)
    SYMBOLIC_CACHE_PATH.write_text(json.dumps(cache,sort_keys=True))


def refresh_semantic_mutants(contract_ids=None):
    """Run the cascade for every contract whose profile selects semantic mutants. The cascade runs in
    the mutation engine's environment, so that no proposal repeats a rule mutant."""
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    needs=current_needs()
    SEMANTIC_RESULTS_DIR.mkdir(parents=True,exist_ok=True)
    cache=load_symbolic_cache()
    for contract_id,target in sorted(semantic_selections().items()):
        if contract_ids and contract_id not in contract_ids:
            continue
        payload,proposals=semantic_proposal_set(contract_id,target)
        if not proposals:
            print(f"[SEMANTIC] {contract_id}: nothing to judge yet; generate its semantic mutants first (--generate-semantic-mutants)",flush=True)
            continue
        contexts=semantic_contexts(contract_id,target,needs)
        plan=plans.get(contract_id) or {}
        judgement=semantic_judgement_request(contract_id,proposals,needs)
        request={
          "root":str(ROOT),"contract_id":contract_id,"proposals":proposals,"tests":list(plan.get("tests") or []),
          "context_sha256":{key:SEMANTIC.context_sha256(context) for key,context in contexts.items()},
          "drafts":SEMANTIC.load_drafts(contract_id),
          "judgement":judgement,
          # Beside the judgement, not in it: the cache remembers searches, it decides nothing.
          "symbolic_cache":cache,
        }
        with tempfile.TemporaryDirectory(prefix="ternforge-semantic-request-") as scratch:
            request_path=Path(scratch)/"request.json"
            result_path=Path(scratch)/"result.json"
            request_path.write_text(json.dumps(request))
            started=time.monotonic()
            completed=subprocess.run(
              [shutil.which("uv") or "uv","run","--with",f"pytest-gremlins=={IMPL_FAULTS.GREMLINS_VERSION}","--with",CROSSHAIR_REQUIREMENT,"python",
               str(ROOT/".ai-bridge/semantic_mutants.py"),"run",str(request_path),str(result_path)],
              cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            )
            if completed.returncode!=0 or not result_path.exists():
                raise RuntimeError(f"{contract_id}: the semantic mutant cascade failed:\n"+"\n".join((completed.stdout or "").splitlines()[-20:]))
            outcome=json.loads(result_path.read_text())
        cache.update(outcome.get("symbolic_cache") or {})
        save_symbolic_cache(cache)
        retained={
          "schema":SEMANTIC.SCHEMA,
          "contract_id":contract_id,
          "generator":payload.get("generator") or {},
          "binding":semantic_binding(contract_id,plan,test_rows,contexts,judgement),
          "results":outcome["results"],
          "seconds":round(time.monotonic()-started,1),
          "ran_at":utc_now(),
          "head_sha":git_sha(),
        }
        (SEMANTIC_RESULTS_DIR/f"{contract_id}.json").write_text(json.dumps(retained,indent=2,sort_keys=True)+"\n")
        counts=Counter(row["outcome"] for row in outcome["results"])
        print(f"[SEMANTIC] {contract_id}: "+", ".join(f"{count} {name}" for name,count in sorted(counts.items()))+f" in {retained['seconds']}s",flush=True)


def model_generation_policy(text=None):
    """The Test Plan's model roles, generation budget, survivor assessors and judgement settings, fail-closed."""
    text=text if text is not None else (ROOT/"docs/test-plan.md").read_text()
    return {
      "roles":MODELS.parse_roles(markdown_table_after(text,"##### Model generation")),
      "budget":MODELS.parse_budget(markdown_table_after(text,"###### Generation budget")),
      "assessors":MODELS.parse_assessors(markdown_table_after(text,"##### Survivor judgement")),
      "judgement":MODELS.parse_judgement(markdown_table_after(text,"###### Judgement settings")),
    }


def assessor_prompt_sha256():
    """What an assessor answer depends on besides its mutant: the question, the system text, the schema."""
    return sha256_text(EQ.ASSESSOR_TEMPLATE+"\0"+EQ.ASSESSOR_SYSTEM+"\0"+stable_json(EQ.ASSESSOR_SCHEMA))


def assessor_roles(policy):
    """Every assessor is a role of its own: each is asked, none stands in for another."""
    return {f"assessor:{row['assessor']}":[{"order":1,"backend":row["backend"],"model":row["model"]}] for row in policy["assessors"]}


def assessor_calibration_state(policy=None):
    """Whether the assessors' labels count: a calibration for the Test Plan's assessors, the current
    question and pairs and the Test Plan's rate, complete, and a qualified ensemble."""
    policy=policy or model_generation_policy()
    members=[row["key"] for row in policy["assessors"]]
    path=ASSESSOR_CALIBRATION_DIR/"calibration.json"
    record=json.loads(path.read_text()) if path.exists() else {}
    qualification=load_evidence_qualification()
    qualified=qualification_is_current(qualification) and all(
      str(((qualification.get("producers") or {}).get(producer_id) or {}).get("status") or "").upper()=="QUALIFIED"
      # The ensemble's qualification is bound to the calibration it replayed, not to the shared environment.
      and (((qualification.get("producers") or {}).get(producer_id) or {}).get("control") or {}).get("calibration_sha256")==assessor_calibration_sha256()
      for producer_id in ASSESSOR_PRODUCERS
    )
    reason=""
    if not record:
        reason="the assessors have not been calibrated yet"
    elif (
      record.get("members")!=members or record.get("prompt_sha256")!=assessor_prompt_sha256()
      or record.get("pairs_sha256")!=EQ.calibration_sha256(EQUIVALENCE_PAIRS_DIR)
      or record.get("alpha")!=policy["judgement"]["alpha"]
    ):
        reason="the assessors' calibration no longer matches the Test Plan's assessors, the question, the pairs or the rate"
    elif not record.get("complete"):
        reason="the assessors' calibration is not complete: "+str(record.get("missing") or "some pairs are unanswered")
    elif record.get("threshold") is None:
        reason="the calibration has too few distinct pairs for the Test Plan's rate"
    elif not qualified:
        reason="the assessor ensemble is not currently qualified"
    return {
      "calibrated":not reason,"threshold":record.get("threshold"),"members":members,"reason":reason,
      "record_sha256":sha256_file(path),
    }


def assessor_calibration_prompt(pair,original_source,mutant_source,harness):
    owner,_,name=pair["target"].rpartition(".")
    return EQ.assessor_prompt(
      target=pair["target"],
      original=EQ.function_source(original_source,pair["target"]) or "",
      mutant=EQ.function_source(mutant_source,pair["target"]) or "",
      harness=harness,
      owner_source=EQ.class_source(original_source,owner) if owner else "",
      tried=SURVIVOR_TRIED,
    )


# What the assessors are told was tried before them; the same for calibration pairs and semantic survivors.
SURVIVOR_TRIED="The tests pass on both versions, and generated inputs and a symbolic search found no input that tells them apart."
# A rule survivor had no differential run of generated inputs: only its tests and the symbolic search.
RULE_SURVIVOR_TRIED="The tests pass on both versions, and a symbolic search found no input that tells them apart."


def assessor_calibration_record(payload,answers,members,policy,prompt_sha,pairs_sha,observed=()):
    """The calibration's result: every answer, its witness checked by execution, the ensemble's score
    per pair and the split-conformal threshold over the distinct pairs, the labelled pairs and the
    observed ones: real survivors the symbolic search left unsure and a mutation pin proves distinct,
    once every assessor answered them."""
    import tempfile as _tempfile
    keys=[row["key"] for row in members]
    scores,rows,missing={}, {}, []
    with _tempfile.TemporaryDirectory(prefix="ternforge-assessor-calibration-") as scratch:
        for pair in payload["pairs"]:
            original_source,mutant_source=EQ.pair_sources(EQUIVALENCE_PAIRS_DIR,pair)
            given={key:value for key,value in (answers.get(pair["id"]) or {}).items() if key in keys and not value.get("problems")}
            judged=EQ.judge_survivor(
              original_source,mutant_source,pair["target"],scratch=Path(scratch),token="cal"+pair["id"].lower(),
              seconds=0,answers=given,members=keys,threshold=None,calibrated=False,
            )
            missing.extend(f"{pair['id']}:{key}" for key in keys if key not in given)
            scores[pair["id"]]=judged.get("score",0.0) if judged.get("status")!="found" else 0.0
            # Each assessor's input is checked on its own, so each is credited with what it found.
            confirmed={
              key:EQ.judge_survivor(
                original_source,mutant_source,pair["target"],scratch=Path(scratch),token=f"cal{pair['id'].lower()}m{keys.index(key)}",
                seconds=0,answers={key:answer},members=[key],threshold=None,calibrated=False,
              ).get("status")=="found"
              for key,answer in given.items() if answer.get("verdict")=="distinct"
            }
            rows[pair["id"]]={
              "label":pair["label"],"status":judged.get("status"),"score":scores[pair["id"]],
              "witness_by":(judged.get("witness") or {}).get("by"),"refuted":[row["by"] for row in judged.get("refuted") or []],
              "confirmed":confirmed,
            }
    alpha=policy["judgement"]["alpha"]
    real,pending={}, []
    for pair in observed:
        given=[pair["answers"][key] for key in keys if key in pair["answers"] and not pair["answers"][key].get("problems")]
        if len(given)<len(keys):
            pending.append(pair["id"])
            continue
        real[pair["id"]]={**{name:pair[name] for name in ("contract_id","fingerprint","pin_path","symbolic","prompt_sha256")},"answers":pair["answers"],"score":EQ.ensemble_score(given,len(keys))}
    distinct=[scores[pair["id"]] for pair in payload["pairs"] if pair["label"]=="distinct"]+[row["score"] for row in real.values()]
    threshold=EQ.conformal_threshold(distinct,alpha)
    labelled=lambda label:[pid for pid,row in rows.items() if row["label"]==label and threshold is not None and row["score"]>threshold]
    metrics={
      "pairs":len(payload["pairs"]),
      "distinct":len(distinct),
      "equivalent_labelled":len(labelled("equivalent")),
      "distinct_labelled":len(labelled("distinct"))+sum(1 for row in real.values() if threshold is not None and row["score"]>threshold),
      "observed":len(real),
      "observed_pending":len(pending),
      "distinct_confirmed":sum(1 for row in rows.values() if row["label"]=="distinct" and row["status"]=="found"),
      "members":{
        key:{
          "distinct_confirmed":sum(1 for row in rows.values() if row["confirmed"].get(key) is True),
          "refuted":sum(1 for row in rows.values() if row["confirmed"].get(key) is False),
          "equivalent_on_distinct":sum(1 for pair in payload["pairs"] if pair["label"]=="distinct" and ((answers.get(pair["id"]) or {}).get(key) or {}).get("verdict")=="equivalent"),
          "equivalent_on_observed":sum(1 for row in real.values() if (row["answers"].get(key) or {}).get("verdict")=="equivalent"),
          "equivalent_on_equivalent":sum(1 for pair in payload["pairs"] if pair["label"]=="equivalent" and ((answers.get(pair["id"]) or {}).get(key) or {}).get("verdict")=="equivalent"),
          "unsure":sum(1 for pair in payload["pairs"] if ((answers.get(pair["id"]) or {}).get(key) or {}).get("verdict")=="unsure"),
        }
        for key in keys
      },
    }
    return {
      "schema":"ternforge-assessor-calibration-1","members":keys,"prompt_sha256":prompt_sha,"pairs_sha256":pairs_sha,
      "alpha":alpha,"answers":answers,"pairs":rows,"observed":real,"observed_pending":pending,"threshold":threshold,"metrics":metrics,
      "complete":not missing,"missing":missing[:12],"calibrated_at":utc_now(),
    }


def observed_calibration_pairs():
    """The real survivors a mutation pin proves distinct (ADR_0005, ADR_0006): the pin passed on the
    original five times and fails on the mutant, and the campaign now catches the mutant. Only the
    ones the symbolic search leaves unsure count: the triage puts only those to the assessors, so only
    they are exchangeable with its questions. Each comes with the triage's own question for it; a
    survivor without a harness has none and is left out."""
    needs=current_needs()
    policy=model_generation_policy()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    cache=load_symbolic_cache()
    pairs=[]
    for folder in sorted(path for path in VERDICTS_DIR.iterdir() if path.is_dir()) if VERDICTS_DIR.is_dir() else []:
        contract_id=folder.name
        report_path=ROOT/str((((campaign.get("contracts") or {}).get(contract_id) or {}).get("run") or {}).get("report_path") or "")
        records={str(row.get("fingerprint")):row for row in (json.loads(report_path.read_text()).get("results") or [])} if report_path.is_file() else {}
        candidates=[]
        for key,entry in sorted(load_verdicts(contract_id).items()):
            pin=entry.get("pin") or {}
            record=records.get(key)
            if not pin or not (pin.get("cascade") or {}).get("accepted") or not record or record.get("status") not in IMPL_FAULTS.KILLED:
                continue
            prompt=rule_assessment_prompt(contract_id,record,needs.get(contract_id) or {})
            if prompt is not None:
                candidates.append((key,record,pin,prompt))
        if not candidates:
            continue
        # The triage's own search without answers, from its cache: what it tells apart never reaches an assessor.
        result=run_triage(triage_request(contract_id,[record for _key,record,_pin,_prompt in candidates],{},needs,policy,{"members":[],"threshold":None,"calibrated":False},cache))
        cache.update(result.get("symbolic_cache") or {})
        searched={str(row["fingerprint"]):row for row in result["rows"]}
        for key,_record,pin,prompt in candidates:
            row=searched.get(key) or {}
            if row.get("status")=="unsure" and (row.get("symbolic") or {}).get("status") in EQ.SEARCH_UNDECIDED:
                pairs.append({"id":f"{contract_id}:{key}","contract_id":contract_id,"fingerprint":key,"pin_path":pin.get("path"),"symbolic":row.get("symbolic"),"prompt":prompt})
    save_symbolic_cache(cache)
    return pairs


def calibrate_assessors(ask=True):
    """Ask every assessor about every labelled pair it has not answered for the current question,
    then recompute the threshold. An answer already paid for is read again from its stored response,
    so a corrected reading applies to it without asking again. Without ``ask`` nothing is asked: the
    record is rebuilt from the answers already stored, a pair still missing one stays pending (as
    after retired pins, revise_pins). Only a person starts it, on request."""
    policy=model_generation_policy()
    path=ASSESSOR_CALIBRATION_DIR/"calibration.json"
    record=json.loads(path.read_text()) if path.exists() else {}
    prompt_sha=assessor_prompt_sha256()
    pairs_sha=EQ.calibration_sha256(EQUIVALENCE_PAIRS_DIR)
    answers=(record.get("answers") or {}) if record.get("prompt_sha256")==prompt_sha and record.get("pairs_sha256")==pairs_sha else {}
    for pair_answers in answers.values():
        for key,answer in list(pair_answers.items()):
            response_path=ASSESSOR_CALIBRATION_DIR/"responses"/f"{answer.get('call_id')}.json"
            if response_path.is_file():
                pair_answers[key]=assessor_answer(json.loads(response_path.read_text()))
    payload=EQ.calibration_payload(EQUIVALENCE_PAIRS_DIR)
    unanswered=[pair for pair in payload["pairs"] if any(row["key"] not in (answers.get(pair["id"]) or {}) for row in policy["assessors"])]
    observed=[]
    for pair in observed_calibration_pairs():
        assessments=load_assessments(TRIAGE_ANSWERS_DIR/pair["contract_id"]/"assessments.json")
        observed.append({**{name:value for name,value in pair.items() if name!="prompt"},"prompt":pair["prompt"],"prompt_sha256":sha256_text(pair["prompt"]),"answers":current_answers(assessments,pair["fingerprint"],pair["prompt"])})
    unanswered_observed=[pair for pair in observed if any(row["key"] not in pair["answers"] for row in policy["assessors"])]
    if not ask:
        unanswered,unanswered_observed=[],[]
    usable=qualified_model_backends()
    if (unanswered or unanswered_observed) and not usable:
        raise SystemExit("assessor calibration: the model adapter is not currently qualified (run qualify-evidence-confidence.py)")
    run=MODELS.Run({**policy["roles"],**assessor_roles(policy)},policy["budget"])
    for name in MODELS.BACKENDS:
        if name not in usable:
            run.availability[name]="the adapter has not yet been shown to read this backend's answers"
    try:
        for pair in unanswered:
            original_source,mutant_source=EQ.pair_sources(EQUIVALENCE_PAIRS_DIR,pair)
            harness=EQ.harness_for(original_source,pair["target"])
            prompt=assessor_calibration_prompt(pair,original_source,mutant_source,harness)
            for row in policy["assessors"]:
                if row["key"] in (answers.get(pair["id"]) or {}):
                    continue
                before=len(run.rows)
                _call,response=run.call(
                  f"assessor:{row['assessor']}",purpose="assessor-calibration",contract_id="CALIBRATION",subject=pair["id"],
                  system=EQ.ASSESSOR_SYSTEM,prompt=prompt,schema=EQ.ASSESSOR_SCHEMA,response_dir=ASSESSOR_CALIBRATION_DIR/"responses",
                )
                print(f"[CALIBRATE] {pair['id']} · assessor {row['assessor']}: "+attempts_text(run.rows[before:]),flush=True)
                if response is None:
                    continue
                answers.setdefault(pair["id"],{})[row["key"]]=assessor_answer(response)
        # A survivor a pin proves distinct is asked the triage's own question, and its answers stay with the triage's.
        for pair in unanswered_observed:
            answers_path=TRIAGE_ANSWERS_DIR/pair["contract_id"]/"assessments.json"
            assessments=load_assessments(answers_path)
            entry=assessments.setdefault(pair["fingerprint"],{})
            if ask_assessors(run,policy,purpose="survivor-assessment",contract_id=pair["contract_id"],subject=pair["fingerprint"],prompt=pair["prompt"],entry=entry,response_dir=TRIAGE_ANSWERS_DIR/pair["contract_id"]/"responses"):
                save_assessments(answers_path,assessments)
            pair["answers"]=current_answers(assessments,pair["fingerprint"],pair["prompt"])
    finally:
        # Answers already paid for are kept even when the run stops early.
        record=assessor_calibration_record(payload,answers,policy["assessors"],policy,prompt_sha,pairs_sha,[{key:value for key,value in pair.items() if key!="prompt"} for pair in observed])
        ASSESSOR_CALIBRATION_DIR.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(record,indent=1,sort_keys=True)+"\n")
    summary=run.summary()
    print(
      f"[CALIBRATE] threshold {record['threshold']} at a {record['alpha']:.0%} false-equivalent rate over {record['metrics']['distinct']} distinct pairs "
      f"({record['metrics']['observed']} of them real survivors a pin proves distinct, {record['metrics']['observed_pending']} still unanswered); "
      f"{record['metrics']['equivalent_labelled']} of {sum(1 for row in record['pairs'].values() if row['label']=='equivalent')} equivalent pairs labelled; "
      f"complete: {record['complete']}; {summary['calls']} calls, ${summary['list_usd'] or 0:.3f} at list price",
      flush=True,
    )
    return record


def assessor_answer(response):
    """What one assessor answered, as stored beside its mutant: the verdict and the call that made it."""
    structured=response["structured"]
    return {
      "verdict":structured.get("verdict"),"confidence":structured.get("confidence"),
      "arguments":{key:EQ.argument_text(value) for key,value in (structured.get("arguments") or {}).items()},
      "reason":structured.get("reason"),"call_id":response["call_id"],"backend":response["backend"],"model":response["model"],
      "response_sha256":MODELS.response_sha256(response),"problems":EQ.answer_problems(structured),
    }


# --- model canaries (ADR_0006) --------------------------------------------------------------

CALIBRATION_PROJECT=ROOT/".ai-bridge/semantic-mutants/calibration"
CANARY_PATH=CALIBRATION_PROJECT/"canaries.json"
CANARY_RESULTS_DIR=ROOT/".ai-bridge/semantic-mutants/canary-results"


def canary_entries(policy):
    """Every (role, backend, model) the Test Plan lets answer for a role that has canaries."""
    return [(role,entry["backend"],entry["model"]) for role in SEMANTIC.CANARY_ROLES for entry in policy["roles"].get(role) or []]


def load_canary_results():
    path=CANARY_RESULTS_DIR/"results.json"
    return json.loads(path.read_text()) if path.exists() else {}


def canary_blocks(policy=None):
    """Why each role entry may not answer yet: no current, passed canary record for its model."""
    policy=policy or model_generation_policy()
    canaries=json.loads(CANARY_PATH.read_text())
    results=load_canary_results()
    questions={role:SEMANTIC.canary_questions_sha256(SEMANTIC.canary_questions(CALIBRATION_PROJECT,canaries,role)) for role in SEMANTIC.CANARY_ROLES}
    # The records count only once the qualification replayed exactly these records.
    qualification=load_evidence_qualification()
    producer=(qualification.get("producers") or {}).get("PRODUCER_MODEL_CANARIES") or {}
    trusted=(
      qualification_is_current(qualification) and str(producer.get("status") or "").upper()=="QUALIFIED"
      and (producer.get("control") or {}).get("results_sha256")==sha256_file(CANARY_RESULTS_DIR/"results.json")
    )
    blocks={}
    for role,backend,model in canary_entries(policy):
        record=results.get(f"{role}|{backend}|{model}") or {}
        if not trusted:
            blocks[(role,backend,model)]="the model canaries are not qualified for their current records (run qualify-evidence-confidence.py after --run-canaries)"
        elif not record:
            blocks[(role,backend,model)]=f"{model} has not run the {role} canaries yet (--run-canaries)"
        elif record.get("questions_sha256")!=questions[role]:
            blocks[(role,backend,model)]=f"the {role} canaries changed since {model} ran them (--run-canaries)"
        elif not record.get("passed"):
            failed="; ".join(str(case.get("detail") or "") for case in (record.get("cases") or {}).values() if not case.get("passed"))
            blocks[(role,backend,model)]=f"{model} failed the {role} canaries: {failed}"
    return blocks


def guarded_run(policy,usable,extra_roles=None):
    """A run over the Test Plan's roles that skips backends the adapter cannot read and models that
    have not passed their role's canaries. A draft's retry goes to the draft author's next model
    first (``draft_author_retry``), under the same canaries."""
    authors=list(policy["roles"].get("draft_author") or [])
    retry={"draft_author_retry":[{**entry,"order":index} for index,entry in enumerate([*authors[1:],*authors[:1]],1)]} if authors else {}
    run=MODELS.Run({**policy["roles"],**assessor_roles(policy),**retry,**(extra_roles or {})},policy["budget"])
    for name in MODELS.BACKENDS:
        if name not in usable:
            run.availability[name]="the adapter has not yet been shown to read this backend's answers"
    blocks=canary_blocks(policy)
    run.blocked.update(blocks)
    run.blocked.update({("draft_author_retry",backend,model):reason for (role,backend,model),reason in blocks.items() if role=="draft_author"})
    return run


def judge_pin_drafts(root,items):
    """Draft tests judged against whole mutated modules by the cascade, in an isolated copy of ``root``."""
    if not items:
        return []
    with tempfile.TemporaryDirectory(prefix="ternforge-pin-request-") as scratch:
        request_path=Path(scratch)/"request.json"
        result_path=Path(scratch)/"result.json"
        request_path.write_text(json.dumps({"root":str(root),"items":items}))
        completed=subprocess.run(
          [shutil.which("uv") or "uv","run","python",str(ROOT/".ai-bridge/semantic_mutants.py"),"judge-pins",str(request_path),str(result_path)],
          cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},
        )
        if completed.returncode!=0 or not result_path.exists():
            raise RuntimeError("judging the pin drafts failed:\n"+"\n".join((completed.stdout or "").splitlines()[-20:]))
        return json.loads(result_path.read_text())["results"]


def run_canaries(roles=None):
    """Ask every model the Test Plan lists for a role its canaries, and record what it answered and
    whether it passed. Only a person starts it, on request; a change of model calls for it."""
    policy=model_generation_policy()
    usable=qualified_model_backends()
    if not usable:
        raise SystemExit("model canaries: the model adapter is not currently qualified (run qualify-evidence-confidence.py)")
    canaries=json.loads(CANARY_PATH.read_text())
    entries=[entry for entry in canary_entries(policy) if not roles or entry[0] in roles]
    own={f"canary:{role}:{backend}:{model}":[{"order":1,"backend":backend,"model":model}] for role,backend,model in entries}
    run=MODELS.Run(own,policy["budget"])
    for name in MODELS.BACKENDS:
        if name not in usable:
            run.availability[name]="the adapter has not yet been shown to read this backend's answers"
    results=load_canary_results()
    CANARY_RESULTS_DIR.mkdir(parents=True,exist_ok=True)
    drafts,standing=[],{}
    try:
        for role,backend,model in entries:
            questions=SEMANTIC.canary_questions(CALIBRATION_PROJECT,canaries,role)
            key=f"{role}|{backend}|{model}"
            cases,asked={},[]
            for question in questions:
                before=len(run.rows)
                row,response=run.call(
                  f"canary:{role}:{backend}:{model}",purpose="canary",contract_id="CANARY",subject=f"{role}:{question['id']}",
                  system=question["system"],prompt=question["prompt"],schema=question["schema"],response_dir=CANARY_RESULTS_DIR/"responses",
                )
                print(f"[CANARY] {role} · {model} · {question['id']}: "+attempts_text(run.rows[before:]),flush=True)
                case={"call_id":row.get("call_id"),"outcome":row.get("outcome"),"response_sha256":row.get("response_sha256") or "","passed":False,"detail":str(row.get("reason") or row.get("outcome"))}
                if response is not None:
                    structured=response["structured"]
                    if role=="generator":
                        case["passed"],case["detail"]=SEMANTIC.generator_canary_passed(CALIBRATION_PROJECT,question,structured)
                    elif role in ("verdict","verdict_review"):
                        case["passed"],case["detail"]=SEMANTIC.verdict_canary_passed(question,structured)
                    else:
                        draft=SEMANTIC.draft_from_answer(question["proposal"]["id"],structured)
                        case["draft_sha256"]=sha256_text(draft)
                        case["detail"]="the draft waits for the cascade"
                        asked.append((key,question,draft))
                cases[question["id"]]=case
            record={
              "role":role,"backend":backend,"model":model,"questions_sha256":SEMANTIC.canary_questions_sha256(questions),
              "cases":cases,"passed":all(case["passed"] for case in cases.values()),"ran_at":utc_now(),
            }
            kept=SEMANTIC.canary_record_after(results.get(key),record)
            if kept is not record:
                standing[key]=next(str(case["detail"]) for case in cases.values() if case["outcome"] in SEMANTIC.UNANSWERED)
                continue
            results[key]=record
            drafts.extend(asked)
        # A draft canary is judged the way every draft is: by the cascade, in the calibration project.
        items=[]
        for key,question,draft in drafts:
            path,qualname=question["proposal"]["target"].split("::",1)
            source=(CALIBRATION_PROJECT/path).read_text()
            items.append({"key":key,"path":path,"mutated_source":SEMANTIC.apply_replacement(source,qualname,question["proposal"]["replacement"]),"draft":draft,"tests":question["tests"]})
        judged={row["key"]:row for row in judge_pin_drafts(CALIBRATION_PROJECT,items)}
        for key,question,_draft in drafts:
            verdict=judged.get(key) or {}
            case=results[key]["cases"][question["id"]]
            case["passed"]=bool(verdict.get("accepted"))
            case["detail"]="the cascade keeps the draft" if case["passed"] else "the cascade rejects the draft: "+(SEMANTIC.draft_rejection(verdict) or "it did not run")
            case["cascade"]={name:verdict.get(name) for name in ("accepted","passes_on_original","fails_on_mutant","imports_beyond_allowed","primitives")}
            results[key]["passed"]=all(item["passed"] for item in results[key]["cases"].values())
    finally:
        (CANARY_RESULTS_DIR/"results.json").write_text(json.dumps(results,indent=1,sort_keys=True)+"\n")
    for key in sorted(f"{role}|{backend}|{model}" for role,backend,model in entries):
        record=results.get(key) or {}
        note=f" (not answered this time: {standing[key]}; the record of {record.get('ran_at')} stands)" if key in standing else ""
        print(f"[CANARY] {key}: "+("passed" if record.get("passed") else "FAILED: "+"; ".join(str(case.get("detail")) for case in (record.get("cases") or {}).values() if not case.get("passed")))+note,flush=True)
    return results


# --- survivor verdicts and mutation pins (ADR_0006) ------------------------------------------

VERDICTS_DIR=ROOT/".ai-bridge/survivor-verdicts"
PINS_DIR=ROOT/"tests/llm_router/mutation_pins"
NEED_KINDS={"goal":"Goal","feature":"Feature","req":"Requirement","treq":"Technical requirement"}


def verdict_context(contract_id,needs,policy):
    """What a verdict weighs a survivor against, top down: the Goal and Feature a requirement
    serves, the requirement itself and its verification criteria."""
    chain,current,seen=[],contract_id,set()
    while current and current not in seen and len(chain)<5:
        seen.add(current)
        need=needs.get(current) or {}
        if not need:
            break
        statement=need_statement(need)
        chain.append(f"{NEED_KINDS.get(need.get('type'),str(need.get('type')))} {current} ({need.get('title')})"+(f": {statement}" if statement else ""))
        current=(need.get("derives") or [None])[0]
    criteria=[value for value in ((requirement_monitor_target(contract_id,policy) or {}).get("item_descriptions") or {}).values() if value]
    return "\n".join([*reversed(chain),*(["Its verification criteria: "+"; ".join(criteria)] if criteria else [])])


def current_campaign_contracts():
    """The contracts whose retained campaign result still counts, without projecting their classes."""
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    asking=contracts_asking_for_implementation_classes()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    shared_sha256=sha256_text(stable_json(IMPL_FAULTS.shared_inputs(ROOT)))
    current=set()
    for contract_id,plan in plans.items():
        entry=(campaign.get("contracts") or {}).get(contract_id) or {}
        if contract_id in asking and not plan.get("blocked") and entry and retained_campaign_entry_state(entry,plan,shared_sha256,test_rows)[0]=="current":
            current.add(contract_id)
    return current


def rule_verdict_item(contract_id,record,context,judged):
    """One rule mutant's verdict question, or None when its mutant cannot be rebuilt."""
    source=Path(record["file_path"]).read_text()
    rebuilt=EQ.rule_mutant_source(source,record)
    if "reason" in rebuilt:
        return None
    qualname=str(record.get("qualname"))
    return {
      "contract_id":contract_id,"key":str(record.get("fingerprint")),"kind":"rule","class":IMPL_FAULTS.CLASS_BY_OPERATOR.get(str(record.get("operator"))),
      "operator":str(record.get("operator")),"path":str(Path(record["file_path"]).resolve().relative_to(ROOT)),
      "qualname":qualname,"original":rebuilt["original"],"mutated":rebuilt["mutated"],"mutated_source":rebuilt["source"],
      "defect":str(record.get("description") or ""),"confirmed":judged.get("status")=="found","judged":judged,
      "prompt":EQ.verdict_prompt(context=context,target=qualname,original=rebuilt["original"],mutant=rebuilt["mutated"],judgement=EQ.judgement_summary(judged)),
    }


def verdict_items(needs,policy):
    """Every survivor and every mutant no test reaches that asks for a verdict, rule or semantic,
    with its question: a survivor once its judgement is current, an unreached mutant once its
    campaign result is."""
    items=[]
    triage=survivor_triage_actual()
    current=current_campaign_contracts()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    for contract_id,entry in sorted((campaign.get("contracts") or {}).items()):
        if contract_id not in current:
            continue
        report_path=ROOT/str((entry.get("run") or {}).get("report_path") or "")
        rows=(json.loads(report_path.read_text()).get("results") or []) if report_path.is_file() else []
        judged_rows=(triage.get(contract_id) or {}).get("rows") or {}
        context=verdict_context(contract_id,needs,policy)
        for record in sorted(rows,key=lambda row:str(row.get("fingerprint"))):
            if record.get("status")!="survived":
                continue
            # A mutant no test of the contract runs gets its verdict too: a pin must reach it.
            judged={"status":"not-reached"} if record.get("covered") is False else judged_rows.get(str(record.get("fingerprint")))
            if not judged:
                continue
            item=rule_verdict_item(contract_id,record,context,judged)
            if item:
                items.append(item)
    actual=semantic_mutant_actual(apply_verdicts=False)
    for contract_id,target in sorted(semantic_selections().items()):
        state=actual.get(contract_id) or {}
        if state.get("state")!="current":
            continue
        by_id={proposal["id"]:proposal for proposal in state.get("proposals") or []}
        drafts=SEMANTIC.load_drafts(contract_id)
        context=verdict_context(contract_id,needs,policy)
        for row in state.get("results") or []:
            proposal=by_id.get(row.get("id"))
            if not proposal or row.get("outcome") not in {"distinguished","undecided"}:
                continue
            file_path,qualname=proposal["target"].split("::",1)
            source=(ROOT/file_path).read_text()
            mutated_source=SEMANTIC.apply_replacement(source,qualname,proposal["replacement"]) or source
            found=row.get("differential") or {}
            judged=row.get("judgement") or (
              {"status":"found","witness":{"display":found.get("input"),"original":found.get("original"),"mutant":found.get("mutant"),"by":found.get("by") or "the differential property run"}}
              if found.get("found") else {"status":"unsure"}
            )
            original=EQ.function_source(source,qualname) or ""
            mutated=EQ.function_source(mutated_source,qualname) or ""
            items.append({
              "contract_id":contract_id,"key":row["id"],"kind":"semantic","class":proposal["class"],"operator":"semantic","path":file_path,"qualname":qualname,
              "original":original,"mutated":mutated,"mutated_source":mutated_source,"defect":str(proposal.get("rationale") or proposal.get("risk") or ""),
              "confirmed":row.get("outcome")=="distinguished","judged":judged,
              "kept_draft":drafts.get(row["id"]) if (row.get("draft") or {}).get("accepted") else None,
              "prompt":EQ.verdict_prompt(context=context,target=qualname,original=original,mutant=mutated,judgement=EQ.judgement_summary(judged)),
            })
    return items


def verdict_answer(response,confirmed):
    structured=response["structured"]
    return {
      **{key:structured.get(key) for key in ("verdict","level","reason","test_focus")},
      "call_id":response["call_id"],"backend":response["backend"],"model":response["model"],
      "response_sha256":MODELS.response_sha256(response),"problems":EQ.verdict_problems(structured,confirmed),
    }


def load_verdicts(contract_id):
    return load_assessments(VERDICTS_DIR/contract_id/"verdicts.json")


def person_decisions(contract_id):
    """Verdicts a person recorded, by survivor: they win over the model's (ADR_0006)."""
    return load_assessments(VERDICTS_DIR/contract_id/"decisions.json")


SUPPRESSING=EQ.SUPPRESSING
reviewed_verdict=EQ.reviewed_verdict


def current_verdict(item,verdicts,decisions):
    """The verdict that counts for one survivor: the person's, else the model's answer to the
    survivor's current question, reviewed as ADR_0006 asks, else none."""
    decided=decisions.get(item["key"]) or {}
    if decided.get("verdict") in EQ.VERDICTS_FINAL and decided.get("reason"):
        return {**decided,"by":"person"}
    entry=verdicts.get(item["key"]) or {}
    if entry.get("prompt_sha256")!=sha256_text(item["prompt"]):
        return None
    return reviewed_verdict(entry)


_VERDICT_STATE=None


def verdict_state(refresh=False):
    """Per contract, per survivor: the item, the verdict that counts (if any) and its pin."""
    global _VERDICT_STATE
    if _VERDICT_STATE is not None and not refresh:
        return _VERDICT_STATE
    state={}
    try:
        items=verdict_items(current_needs(),project_monitor_policy())
    except Exception:  # noqa: BLE001 - a build without the judgement's inputs has no verdicts
        items=[]
    for item in items:
        contract=state.setdefault(item["contract_id"],{"verdicts":load_verdicts(item["contract_id"]),"decisions":person_decisions(item["contract_id"]),"items":{}})
        verdict=current_verdict(item,contract["verdicts"],contract["decisions"])
        pin=((contract["verdicts"].get(item["key"]) or {}).get("pin") or {})
        pin_file=ROOT/str(pin.get("path") or "")
        contract["items"][item["key"]]={
          "item":item,"verdict":verdict,
          "pin":pin if pin and pin_file.is_file() and sha256_text(pin_body(pin_file.read_text()))==pin.get("draft_sha256") else None,
        }
    _VERDICT_STATE=state
    return state


def verdict_suppressions(contract_id):
    """Surviving rule mutants a verdict that counts judged equivalent or irrelevant, by fingerprint."""
    items=(verdict_state().get(contract_id) or {}).get("items") or {}
    return {
      key:{"verdict":entry["verdict"]["verdict"],"reason":entry["verdict"].get("reason"),"by":entry["verdict"].get("by"),"reviewed_by":entry["verdict"].get("reviewed_by")}
      for key,entry in items.items()
      if entry["item"]["kind"]=="rule" and entry["verdict"] and entry["verdict"]["verdict"] in SUPPRESSING
    }


def is_mutation_pin(nodeid):
    return str(nodeid or "").startswith(str(PINS_DIR.relative_to(ROOT))+"/")


def pin_path(contract_id,key):
    return PINS_DIR/f"test_pin_{contract_id.lower()}_{re.sub(r'\W','_',key).lower()}.py"


def pin_body(text):
    """A pin without its header: the draft test exactly as it was judged."""
    return "\n".join(line for line in text.splitlines() if not line.startswith(("# mutation-pin:","# pinned-by:","# semantic-mutant:"))).strip()+"\n"


def module_of(path):
    """The dotted module a source file under src/ is imported as."""
    parts=list(Path(path).with_suffix("").parts)
    if parts and parts[0]=="src":
        parts=parts[1:]
    if parts and parts[-1]=="__init__":
        parts=parts[:-1]
    return ".".join(parts)


def pin_extra_imports(item,need):
    """What a pin may import beyond the contract's tests: for a Technical requirement, the module
    of the code it tests and the project modules that module imports itself, the types its inputs
    are built from (a unit test of an internal obligation); a Requirement stays public."""
    if need.get("type")!="treq":
        return ()
    module=module_of(item["path"])
    return (module,*sorted(SEMANTIC.module_imports(ROOT/item["path"],module)-{module}))


def pin_draft_context(item,verdict,tests,need,criteria,previous=None):
    """What the draft author is given for one survivor a verdict asks to pin: the draft question of
    ADR_0004 with the survivor's input, or the verdict's focus when no input is confirmed."""
    witness=(item["judged"].get("witness") or {}) if item["judged"].get("status")=="found" else {}
    unreached=item["judged"].get("status")=="not-reached"
    owner=item["qualname"].rpartition(".")[0]
    source=(ROOT/item["path"]).read_text()
    return {
      "requirement":{"id":item["contract_id"],"revision":need.get("revision"),"statement":need_statement(need)},
      "criteria":criteria,"mutant_id":item["key"],"target":f"{item['path']}::{item['qualname']}",
      "original":EQ._dedent(item["original"]),"mutated":EQ._dedent(item["mutated"]),
      "defect":(item["defect"]+". " if item["defect"] else "")+"What the test must check: "+str(verdict.get("test_focus") or ""),
      "input":str(witness.get("display") or (
        "no test of the requirement runs this line yet: the test must reach it and tell the versions apart" if unreached
        else "no input is confirmed yet: find one that tells the versions apart"
      )),
      "original_result":str(witness.get("original") or "not observed yet"),"mutant_result":str(witness.get("mutant") or "not observed yet"),
      "owner_source":EQ.class_source(source,owner)[:4000] if owner else "",
      "example":SEMANTIC.example_test(ROOT,tests),
      "imports":sorted({*SEMANTIC.allowed_imports(ROOT,tests),*pin_extra_imports(item,need)}),"previous":previous or {},
    }


_LEDGER_BY_CALL=None


def stored_pin_draft(contract_id,prompt):
    """The latest stored draft-author answer to exactly this pin question: a response whose digests
    hold and whose ledger row accepted it, or None."""
    global _LEDGER_BY_CALL
    if _LEDGER_BY_CALL is None:
        _LEDGER_BY_CALL={row["call_id"]:row for row in MODELS.read_ledger()}
    wanted=sha256_text(prompt)
    found=[]
    for path in sorted((VERDICTS_DIR/contract_id/"responses").glob("*.json")) if (VERDICTS_DIR/contract_id/"responses").is_dir() else []:
        response=json.loads(path.read_text())
        row=_LEDGER_BY_CALL.get(response.get("call_id")) or {}
        if (
          response.get("purpose")=="mutation-pin" and response.get("prompt_sha256")==wanted and not MODELS.verify_response(response)
          and row.get("outcome")=="ok" and row.get("response_sha256")==MODELS.response_sha256(response)
        ):
            found.append(response)
    return found[-1] if found else None


def pin_header(contract_id,key,verdict):
    """A pin's first lines: the mutant it pins and who asked for it (the reason stays in the verdict record)."""
    return f"# mutation-pin: {contract_id} {key}\n# pinned-by: {verdict.get('by')}\n"


def adopt_pins(run,policy,state,plans,needs,monitor_policy):
    """Write, check and adopt a mutation pin for every survivor whose verdict is pin and that has none
    yet: a kept semantic draft first, otherwise drafts from the draft author (ADR_0006)."""
    wanted=[
      (contract_id,key,entry) for contract_id,contract in sorted(state.items()) for key,entry in sorted(contract["items"].items())
      if entry["verdict"] and entry["verdict"]["verdict"]=="pin" and not entry["pin"]
    ]
    first={key:(entry["item"]["kept_draft"],{"source":"kept semantic draft"}) for _contract_id,key,entry in wanted if entry["item"].get("kept_draft")}
    return draft_pins(run,policy,wanted,plans,needs,monitor_policy,first)


def draft_pins(run,policy,wanted,plans,needs,monitor_policy,first=None,replace=False):
    """The pin core. A draft that is free (a kept semantic draft, or the draft an existing pin was
    made from) is judged first; then up to the Test Plan's draft attempts are asked of the draft
    author, the first of its first model and a retry, with the reason, of its next one. The cascade
    judges each draft in the project's style where the pin will live: it must break no lint rule,
    pass on the original five times and fail on the mutant. With ``replace``, an existing pin that
    no draft keeps is removed, and its mutant counts as a survivor again; a pin whose last attempt
    got no answer (deferred by the budget, or no backend) is kept as it is, since nothing judged it."""
    first=dict(first or {})
    budget=int(policy["budget"]["draft_attempts"])
    asked={key:0 for _contract_id,key,_entry in wanted}
    previous,done,adopted,unanswered={}, set(), 0, set()
    normalizer=SEMANTIC.ruff_version()
    for round_index in range(budget+1):
        pending,answered,asking=[],[],[]
        for contract_id,key,entry in wanted:
            if key in done:
                continue
            if round_index==0:
                if key in first:
                    pending.append((contract_id,key,entry,*first[key]))
                continue
            item=entry["item"]
            need=needs.get(contract_id) or {}
            tests=list((plans.get(contract_id) or {}).get("tests") or [])
            criteria=[value for value in ((requirement_monitor_target(contract_id,monitor_policy) or {}).get("item_descriptions") or {}).values() if value]
            prompt=SEMANTIC.draft_prompt(pin_draft_context(item,entry["verdict"],tests,need,criteria,previous.get(key)))
            # A draft already paid for, for exactly this question, is judged again instead of asked again.
            response=stored_pin_draft(contract_id,prompt)
            if response is not None:
                print(f"[PIN] {contract_id} · {key}: the stored draft {response['call_id']} answers this question",flush=True)
                answered.append((contract_id,key,entry,response))
            else:
                role="draft_author" if asked[key]==0 else "draft_author_retry"
                asking.append(((contract_id,key,entry),{"role":role,"purpose":"mutation-pin","contract_id":contract_id,"subject":key,"system":SEMANTIC.DRAFT_SYSTEM,"prompt":prompt,"schema":SEMANTIC.DRAFT_ANSWER_SCHEMA,"response_dir":VERDICTS_DIR/contract_id/"responses"}))
        # The drafts no stored answer covers are asked at once, as many as the backends take.
        for (contract_id,key,entry),(_row,response,attempts) in zip([owner for owner,_request in asking],run.call_many([request for _owner,request in asking])):
            print(f"[PIN] {contract_id} · {key}: "+attempts_text(attempts),flush=True)
            answered.append((contract_id,key,entry,response))
        for contract_id,key,entry,response in answered:
            asked[key]+=1
            if response is None:
                unanswered.add(key)
                continue
            unanswered.discard(key)
            pending.append((contract_id,key,entry,SEMANTIC.draft_from_answer(key,response["structured"]),{"source":"draft author","call_id":response["call_id"],"model":response["model"],"response_sha256":MODELS.response_sha256(response)}))
        if not pending:
            if round_index>0:
                break
            continue
        judged={row["key"]:row for row in judge_pin_drafts(ROOT,[
          {"key":key,"path":entry["item"]["path"],"mutated_source":entry["item"]["mutated_source"],"draft":draft,
           "tests":list((plans.get(contract_id) or {}).get("tests") or []),"as_path":str(pin_path(contract_id,key).relative_to(ROOT)),
           "extra_imports":list(pin_extra_imports(entry["item"],needs.get(contract_id) or {}))}
          for contract_id,key,entry,draft,_origin in pending
        ])}
        for contract_id,key,entry,draft,origin in pending:
            verdict=judged.get(key) or {}
            if not verdict.get("accepted"):
                previous[key]={"reason":SEMANTIC.draft_rejection(verdict) or "it did not run","code":verdict.get("draft") or draft}
                print(f"[PIN] {contract_id} · {key}: the cascade rejects the draft: {previous[key]['reason']}",flush=True)
                continue
            body=pin_body(verdict["draft"])
            target=pin_path(contract_id,key)
            target.parent.mkdir(parents=True,exist_ok=True)
            # The path marks a mutation pin: no shared test input changes, so only its contract's campaign goes stale.
            target.write_text(pin_header(contract_id,key,entry["verdict"])+body)
            verdicts=load_verdicts(contract_id)
            verdicts.setdefault(key,{})["pin"]={
              **origin,"path":str(target.relative_to(ROOT)),"draft_sha256":sha256_text(body),
              "answer_sha256":sha256_text(pin_body(draft)),"normalizer":normalizer,
              "cascade":{name:verdict.get(name) for name in ("accepted","passes_on_original","fails_on_mutant","imports_beyond_allowed","primitives","lint")},
              "adopted_at":utc_now(),
            }
            save_assessments(VERDICTS_DIR/contract_id/"verdicts.json",verdicts)
            done.add(key)
            adopted+=1
            print(f"[PIN] {contract_id} · {key}: adopted as {target.relative_to(ROOT)}",flush=True)
    if replace:
        for contract_id,key,entry in wanted:
            if key in done:
                continue
            if key in unanswered:
                print(f"[PIN] {contract_id} · {key}: kept as it is: its last attempt got no answer, so nothing judged it against the current rules",flush=True)
                continue
            verdicts=load_verdicts(contract_id)
            pin=(verdicts.get(key) or {}).pop("pin",None) or {}
            if pin.get("path"):
                (ROOT/str(pin["path"])).unlink(missing_ok=True)
            save_assessments(VERDICTS_DIR/contract_id/"verdicts.json",verdicts)
            print(f"[PIN] {contract_id} · {key}: no draft meets the rules, the pin is removed and its mutant survives again",flush=True)
    return adopted


def source_revisions(root=ROOT):
    """Every Requirement's and Technical requirement's revision as the docs source declares it, read
    without the portal: a pin of an older revision is exactly what keeps the portal from building."""
    revisions={}
    for path in sorted((root/"docs").rglob("*.md")):
        if "_build" in path.parts:
            continue
        need=None
        for line in path.read_text().splitlines():
            if line.startswith("```"):
                need=None
            if match:=re.fullmatch(r":id: (T?REQ_[A-Z0-9_]+)",line.strip()):
                need=match.group(1)
            elif need and (match:=re.fullmatch(r":revision: (\d+)",line.strip())):
                revisions[need]=int(match.group(1))
    return revisions


def stale_pin_revisions(pin_text,revisions):
    """The requirements a pin verifies at a revision the docs no longer declare."""
    return sorted({
      contract_id for contract_id,revision in re.findall(r"(T?REQ_[A-Z0-9_]+)\[revision==(\d+)\]",pin_text)
      if contract_id in revisions and revisions[contract_id]!=int(revision)
    })


def revise_pins():
    """A requirement's new revision retires the pins of the old one (ADR_0006): each pin that
    verifies an older revision than the docs declare is removed with its record, so its mutant
    survives again and the next --decide-survivors asks the new question and pins it anew; the
    assessors' calibration is rebuilt from stored answers without the pairs those pins proved.
    Asks no model. Only a person starts it, on request, after changing a revision."""
    revisions=source_revisions()
    removed=0
    for folder in sorted(path for path in VERDICTS_DIR.iterdir() if path.is_dir()) if VERDICTS_DIR.is_dir() else []:
        verdicts=load_verdicts(folder.name)
        changed=False
        for key,entry in sorted(verdicts.items()):
            pin=entry.get("pin") or {}
            pin_file=ROOT/str(pin.get("path") or "")
            stale=stale_pin_revisions(pin_file.read_text(),revisions) if pin and pin_file.is_file() else []
            if not stale:
                continue
            pin_file.unlink()
            entry.pop("pin")
            changed=True
            removed+=1
            print(f"[PIN] {folder.name} · {key}: verifies "+", ".join(f"{contract_id} below revision {revisions[contract_id]}" for contract_id in stale)+"; the pin is removed and its mutant survives again",flush=True)
        if changed:
            save_assessments(folder/"verdicts.json",verdicts)
    if removed:
        calibrate_assessors(ask=False)
    print(f"[PIN] {removed} pins of an older revision removed; rerun the retained tests, the portal, --refresh-implementation-faults and --decide-survivors",flush=True)


def refresh_pins(contract_ids=None):
    """Bring every mutation pin to the current pin rules (ADR_0006): the draft it was made from is
    normalized and judged again; when it breaks a rule, the draft author tries again with the
    reason; when no draft keeps it, the pin is removed. Only a person starts it, on request."""
    policy=model_generation_policy()
    usable=qualified_model_backends()
    if not usable:
        raise SystemExit("mutation pins: the model adapter is not currently qualified (run qualify-evidence-confidence.py)")
    run=guarded_run(policy,usable)
    needs=current_needs()
    monitor_policy=project_monitor_policy()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    normalizer=SEMANTIC.ruff_version()
    wanted,first=[],{}
    for folder in sorted(path for path in VERDICTS_DIR.iterdir() if path.is_dir()) if VERDICTS_DIR.is_dir() else []:
        contract_id=folder.name
        if contract_ids and contract_id not in contract_ids:
            continue
        verdicts=load_verdicts(contract_id)
        decided=person_decisions(contract_id)
        context=verdict_context(contract_id,needs,monitor_policy)
        report_path=ROOT/str((((campaign.get("contracts") or {}).get(contract_id) or {}).get("run") or {}).get("report_path") or "")
        records={str(row.get("fingerprint")):row for row in (json.loads(report_path.read_text()).get("results") or [])} if report_path.is_file() else {}
        proposals={row["id"]:row for row in SEMANTIC.load_proposals(contract_id).get("proposals") or []}
        for key,entry in sorted(verdicts.items()):
            pin=entry.get("pin") or {}
            person=decided.get(key) or {}
            verdict={**person,"by":"person"} if person.get("verdict") in EQ.VERDICTS_FINAL and person.get("reason") else reviewed_verdict(entry)
            if not pin or not verdict or verdict.get("verdict")!="pin":
                continue
            # A pin already made under the current rules and unchanged since is left as it is.
            pin_file=ROOT/str(pin.get("path") or "")
            if (
              pin.get("normalizer")==normalizer and pin.get("answer_sha256") and pin_file.is_file()
              and sha256_text(pin_body(pin_file.read_text()))==pin.get("draft_sha256")
            ):
                continue
            if key in proposals:
                file_path,qualname=proposals[key]["target"].split("::",1)
                source=(ROOT/file_path).read_text()
                mutated_source=SEMANTIC.apply_replacement(source,qualname,proposals[key]["replacement"]) or source
                item={
                  "contract_id":contract_id,"key":key,"kind":"semantic","class":proposals[key]["class"],"operator":"semantic","path":file_path,"qualname":qualname,
                  "original":EQ.function_source(source,qualname) or "","mutated":EQ.function_source(mutated_source,qualname) or "","mutated_source":mutated_source,
                  "defect":str(proposals[key].get("rationale") or proposals[key].get("risk") or ""),"confirmed":True,"judged":{"status":"pinned"},
                }
            elif key in records:
                item=rule_verdict_item(contract_id,records[key],context,{"status":"pinned"})
            else:
                item=None
            if item is None:
                print(f"[PIN] {contract_id} · {key}: its mutant is gone from the campaign, so the pin stays as it is",flush=True)
                continue
            if pin.get("source")=="draft author":
                response_path=folder/"responses"/f"{pin.get('call_id')}.json"
                draft=SEMANTIC.draft_from_answer(key,json.loads(response_path.read_text())["structured"]) if response_path.is_file() else None
                origin={name:pin.get(name) for name in ("source","call_id","model","response_sha256")}
            else:
                draft=SEMANTIC.load_drafts(contract_id).get(key)
                origin={"source":"kept semantic draft"}
            wanted.append((contract_id,key,{"item":item,"verdict":verdict}))
            if draft:
                first[key]=(draft,origin)
    adopted=draft_pins(run,policy,wanted,implementation_fault_plans(),needs,monitor_policy,first,replace=True)
    summary=run.summary()
    print(f"[PIN] {len(wanted)} pins checked against the current rules, {adopted} kept or rewritten; {summary['calls']} calls",flush=True)


def verdict_request(role,purpose,item):
    """One verdict or review question about a survivor, as ``Run.call_many`` asks it."""
    return {"role":role,"purpose":purpose,"contract_id":item["contract_id"],"subject":item["key"],
            "system":EQ.VERDICT_SYSTEM,"prompt":item["prompt"],"schema":EQ.VERDICT_SCHEMA,
            "response_dir":VERDICTS_DIR/item["contract_id"]/"responses"}


def decide_survivors(contract_ids=None):
    """Ask the verdict model about every judged survivor whose question has no current answer, then
    adopt a mutation pin for every pin verdict (ADR_0006). Only a person starts it, on request."""
    policy=model_generation_policy()
    usable=qualified_model_backends()
    if not usable:
        raise SystemExit("survivor verdicts: the model adapter is not currently qualified (run qualify-evidence-confidence.py)")
    run=guarded_run(policy,usable)
    needs=current_needs()
    monitor_policy=project_monitor_policy()
    items=[item for item in verdict_items(needs,monitor_policy) if not contract_ids or item["contract_id"] in contract_ids]
    # Verdicts and reviews are asked a chunk at a time, as many at once as the backends take, and a
    # chunk is saved before the next, so a run that stops keeps every answer it paid for.
    chunk=2*run.parallel
    for start in range(0,len(items),chunk):
        rows: list[list[Any]]=[]
        for item in items[start:start+chunk]:
            entry=dict(load_verdicts(item["contract_id"]).get(item["key"]) or {})
            prompt_sha256=sha256_text(item["prompt"])
            current=bool(entry.get("prompt_sha256")==prompt_sha256 and entry.get("answer") and not (entry.get("answer") or {}).get("problems"))
            rows.append([item,entry,prompt_sha256,current])
        asking=[row for row in rows if not row[3]]
        for row,(_call,response,attempts) in zip(asking,run.call_many([verdict_request("verdict","survivor-verdict",row[0]) for row in asking])):
            item,entry,prompt_sha256,_current=row
            answer=verdict_answer(response,item["confirmed"]) if response is not None else None
            print(f"[VERDICT] {item['contract_id']} · {item['key']}: "+attempts_text(attempts)+(f" → {answer['verdict']} ({answer['level']})"+(" · "+"; ".join(answer["problems"]) if answer["problems"] else "") if answer else ""),flush=True)
            same=entry.get("prompt_sha256")==prompt_sha256
            # No answer, nothing to keep: the survivor stays as it was until a later run answers.
            row[1]={**{name:value for name,value in entry.items() if name in {"pin","review"} and same},"prompt_sha256":prompt_sha256,"answer":answer} if answer else None
        # A verdict that would hide a survivor asks a model of another family the same question.
        reviewing=[row for row in rows if row[1] is not None and (row[1].get("answer") or {}).get("verdict") in SUPPRESSING and (row[1].get("review") or {}).get("prompt_sha256")!=row[2]]
        for row,(_call,response,attempts) in zip(reviewing,run.call_many([verdict_request("verdict_review","survivor-verdict-review",row[0]) for row in reviewing])):
            item,entry,prompt_sha256,_current=row
            review=verdict_answer(response,item["confirmed"]) if response is not None else None
            print(f"[REVIEW] {item['contract_id']} · {item['key']}: "+attempts_text(attempts)+(f" → {review['verdict']}" if review else ""),flush=True)
            if review is not None:
                entry["review"]={**review,"prompt_sha256":prompt_sha256}
        for item,entry,_prompt_sha256,_current in rows:
            if entry is None:
                continue
            entry["operator"]=item.get("operator")
            verdicts=load_verdicts(item["contract_id"])
            verdicts[item["key"]]=entry
            save_assessments(VERDICTS_DIR/item["contract_id"]/"verdicts.json",verdicts)
    state=verdict_state(refresh=True)
    if contract_ids:
        state={contract_id:contract for contract_id,contract in state.items() if contract_id in contract_ids}
    adopted=adopt_pins(run,policy,state,implementation_fault_plans(),needs,monitor_policy)
    summary=run.summary()
    counts=Counter(entry["verdict"]["verdict"] if entry["verdict"] else "none" for contract in state.values() for entry in contract["items"].values())
    print(f"[VERDICT] {summary['calls']} calls, {tokens_text(summary['tokens']['total'])} tokens"+(f", ${summary['list_usd']:.3f} at list price" if summary["list_usd"] is not None else "")+"; verdicts "+", ".join(f"{count} {name}" for name,count in sorted(counts.items()))+f"; {adopted} pins adopted",flush=True)
    if adopted:
        print("[VERDICT] new mutation pins: rerun the retained tests, then --refresh-implementation-faults and --refresh-semantic-mutants",flush=True)


def qualified_model_backends():
    """The backends whose answers the qualified adapter has been shown to read; generation uses no other."""
    qualification=load_evidence_qualification()
    record=(qualification.get("producers") or {}).get(MODEL_PRODUCERS[0]) or {}
    if not qualification_is_current(qualification) or str(record.get("status") or "").upper()!="QUALIFIED":
        return set()
    return set(record.get("backends_qualified") or [])


def load_draft_provenance(folder):
    path=folder/"drafts"/"provenance.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def save_draft_provenance(folder,provenance):
    (folder/"drafts").mkdir(parents=True,exist_ok=True)
    (folder/"drafts"/"provenance.json").write_text(json.dumps(dict(sorted(provenance.items())),indent=1)+"\n")


def retire_drafts(folder,mutant_ids):
    """Drafts of proposals that were replaced: they tested a mutant that no longer exists."""
    if not mutant_ids:
        return
    provenance=load_draft_provenance(folder)
    for mutant_id in mutant_ids:
        (folder/"drafts"/f"{mutant_id}.draft.py").unlink(missing_ok=True)
        provenance.pop(mutant_id,None)
    if (folder/"drafts").is_dir():
        save_draft_provenance(folder,provenance)


def attempts_text(rows):
    """Every backend one call tried, in order, with what each came to."""
    return "; ".join(
      f"{row['backend']}:{row['model']} {row['outcome']}"+(f" ({row['reason']})" if row.get("reason") else "")
      for row in rows if row.get("role")!="probe"
    )


def generate_contract_proposals(run,contract_id,target,needs,force=False):
    """Ask the generator for every target of one contract that has no current proposal (or for
    every target, with force); an accepted answer replaces that target's proposals."""
    payload,proposals=semantic_proposal_set(contract_id,target)
    contexts=semantic_contexts(contract_id,target,needs)
    folder=SEMANTIC.PROPOSAL_ROOT/contract_id
    changed=False
    for selection in target.get("semantic_mutants") or []:
        key=selection["target"]
        context=contexts[key]
        digest=SEMANTIC.context_sha256(context)
        current=[proposal for proposal in proposals if proposal["target"]==key and SEMANTIC.proposal_inputs(ROOT,proposal,digest)[0]]
        if current and not force:
            continue
        path,qualname=key.split("::",1)
        original=SEMANTIC.function_source((ROOT/path).read_text(),qualname) or ""
        before=len(run.rows)
        _row,response=run.call(
          "generator",purpose="semantic-mutants",contract_id=contract_id,subject=key,
          system=SEMANTIC.GENERATOR_SYSTEM,prompt=SEMANTIC.prompt(context),
          schema=SEMANTIC.mutant_answer_schema(selection["budget"]),response_dir=folder/"responses",
        )
        print(f"[GENERATE] {contract_id} · {qualname}: "+attempts_text(run.rows[before:]),flush=True)
        if response is None:
            continue
        fresh=SEMANTIC.proposals_from_answer(selection,context,response,MODELS.response_sha256(response),original)
        replaced={proposal["id"] for proposal in proposals if proposal["target"]==key}
        proposals=[proposal for proposal in proposals if proposal["target"]!=key]+fresh
        retire_drafts(folder,replaced-{proposal["id"] for proposal in fresh})
        changed=True
    if changed:
        written={"schema":SEMANTIC.PROPOSALS_SCHEMA,"contract_id":contract_id}
        if payload.get("generator") and any(not proposal.get("generator") for proposal in proposals):
            written["generator"]=payload["generator"]
        written["proposals"]=proposals
        folder.mkdir(parents=True,exist_ok=True)
        (folder/"proposals.json").write_text(json.dumps(written,indent=1,ensure_ascii=False)+"\n")
    return changed


def generate_contract_drafts(run,contract_id,target,needs,plans,attempts):
    """Ask the draft author for every distinguished mutant of one contract without a kept draft, within
    the attempts the budget allows; a rejected draft and its reason go into the next request."""
    path=SEMANTIC_RESULTS_DIR/f"{contract_id}.json"
    retained=json.loads(path.read_text()) if path.exists() else {}
    _payload,proposals=semantic_proposal_set(contract_id,target)
    by_id={proposal["id"]:proposal for proposal in proposals}
    folder=SEMANTIC.PROPOSAL_ROOT/contract_id
    provenance=load_draft_provenance(folder)
    drafts=SEMANTIC.load_drafts(contract_id)
    need=needs.get(contract_id) or {}
    requirement={"id":contract_id,"revision":need.get("revision"),"statement":need_statement(need)}
    criteria=[str(value) for _key,value in sorted((target.get("item_descriptions") or {}).items())]
    tests=list((plans.get(contract_id) or {}).get("tests") or [])
    wrote=False
    for row in retained.get("results") or []:
        if row.get("outcome")!="distinguished" or row["id"] not in by_id:
            continue
        judged=row.get("draft") or {}
        if judged.get("accepted") or (row["id"] in drafts and not judged):
            continue
        record=provenance.get(row["id"]) or {}
        made=int(record.get("attempt") or 0) if record.get("kind")=="model" else int(row["id"] in drafts)
        if made>=attempts:
            continue
        previous={"reason":SEMANTIC.draft_rejection(judged),"code":drafts[row["id"]]} if row["id"] in drafts else None
        context=SEMANTIC.draft_context(ROOT,requirement,criteria,by_id[row["id"]],row.get("differential") or {},tests,previous)
        before=len(run.rows)
        _call,response=run.call(
          "draft_author",purpose="semantic-draft",contract_id=contract_id,subject=row["id"],
          system=SEMANTIC.DRAFT_SYSTEM,prompt=SEMANTIC.draft_prompt(context),
          schema=SEMANTIC.DRAFT_ANSWER_SCHEMA,response_dir=folder/"responses",
        )
        print(f"[GENERATE] {contract_id} · draft for {row['id']} (attempt {made+1}): "+attempts_text(run.rows[before:]),flush=True)
        if response is None:
            continue
        (folder/"drafts").mkdir(parents=True,exist_ok=True)
        (folder/"drafts"/f"{row['id']}.draft.py").write_text(SEMANTIC.draft_from_answer(row["id"],response["structured"]))
        provenance[row["id"]]={
          "kind":"model","call_id":response["call_id"],"backend":response["backend"],
          "backend_version":response.get("backend_version") or "","model":response["model"],
          "response_sha256":MODELS.response_sha256(response),"attempt":made+1,
        }
        wrote=True
    if wrote:
        save_draft_provenance(folder,provenance)
    return wrote


def generate_semantic_mutants(contract_ids=None,force=False):
    """One generation run: mutants for every selected target without a current proposal, the cascade
    over them, then draft tests for the distinguished ones, judged again, as often as the budget allows.
    Only a person starts it, on request; the gate and the portal build never do."""
    policy=model_generation_policy()
    usable=qualified_model_backends()
    if not usable:
        raise SystemExit("model generation: the adapter is not currently qualified (run qualify-evidence-confidence.py)")
    run=guarded_run(policy,usable)
    needs=current_needs()
    scope=sorted(contract_id for contract_id in semantic_selections() if not contract_ids or contract_id in contract_ids)
    generated={contract_id for contract_id in scope if generate_contract_proposals(run,contract_id,semantic_selections()[contract_id],needs,force)}
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    actual=semantic_mutant_actual(plans,test_rows)
    stale={contract_id for contract_id in scope if (actual.get(contract_id) or {}).get("state") in {"stale","not_run"}}
    if generated|stale:
        refresh_semantic_mutants(generated|stale)
    assessed={contract_id for contract_id in scope if assess_contract_semantic(run,contract_id,semantic_selections()[contract_id],needs,policy)}
    if assessed:
        refresh_semantic_mutants(assessed)
    for _round in range(int(policy["budget"]["draft_attempts"])):
        drafted={
          contract_id for contract_id in scope
          if generate_contract_drafts(run,contract_id,semantic_selections()[contract_id],needs,plans,int(policy["budget"]["draft_attempts"]))
        }
        if not drafted:
            break
        refresh_semantic_mutants(drafted)
    summary=run.summary()
    outcomes=", ".join(f"{count} {name}" for name,count in summary["outcomes"].items() if count) or "no calls"
    windows=", ".join(f"{key} {values[0]:.0%}→{values[1]:.0%}" for key,values in summary["windows"].items())
    print(
      f"[GENERATE] run {summary['run_id']}: {summary['calls']} calls ({outcomes}); "
      f"{tokens_text(summary['tokens']['total'])} tokens"
      +(f", ${summary['list_usd']:.3f} at list price" if summary["list_usd"] is not None else "")
      +(f"; windows {windows}" if windows else ""),
      flush=True,
    )
    return summary


def rule_survivors(entry):
    """The surviving rule mutants of one campaign entry that its tests reach, with the report they come from."""
    report_path=ROOT/((entry.get("run") or {}).get("report_path") or "")
    if not report_path.is_file():
        return report_path,[]
    report=json.loads(report_path.read_text())
    return report_path,[row for row in report.get("results") or [] if row.get("status")=="survived" and row.get("covered") is not False]


def rule_assessment_prompt(contract_id,record,need):
    """What the assessors are asked about one surviving rule mutant, or None when it has no harness."""
    source=Path(record["file_path"]).read_text()
    rebuilt=EQ.rule_mutant_source(source,record)
    harness=EQ.harness_for(source,str(record.get("qualname") or ""))
    if "reason" in rebuilt or "reason" in harness:
        return None
    owner=str(record.get("qualname") or "").rpartition(".")[0]
    # How to build the inputs: without it an assessor guesses the project's constructors.
    guide=EQ.input_guide(str(record["file_path"]),harness)
    return EQ.assessor_prompt(
      target=str(record.get("qualname")),original=rebuilt["original"],mutant=rebuilt["mutated"],harness=harness,
      context=f"Requirement {contract_id}: {need_statement(need)}"+(f"\n{guide}" if guide else ""),
      owner_source=EQ.class_source(source,owner) if owner else "",tried=RULE_SURVIVOR_TRIED,
    )


def triage_request(contract_id,records,assessments,needs,policy,state,cache):
    need=needs.get(contract_id) or {}
    answers={}
    for record in records:
        given=current_answers(assessments,str(record.get("fingerprint")),rule_assessment_prompt(contract_id,record,need))
        if given:
            answers[str(record.get("fingerprint"))]=given
    return {
      "survivors":records,"seconds":policy["judgement"]["symbolic_seconds"],"paths":policy["judgement"]["symbolic_paths"],"members":state["members"],
      "threshold":state["threshold"],"calibrated":state["calibrated"],"answers":answers,"symbolic_cache":cache,
    }


def triage_binding(request,report_path,records):
    """Everything a retained triage depends on; any change makes it stale."""
    return {
      "report_sha256":sha256_file(report_path),
      "sources":{path:sha256_file(Path(path)) for path in sorted({str(record["file_path"]) for record in records})},
      "judgement_sha256":sha256_text(stable_json({key:value for key,value in request.items() if key not in {"survivors","symbolic_cache"}})),
      "equivalence_sha256":sha256_file(ROOT/".ai-bridge/survivor_equivalence.py"),
    }


def run_triage(request):
    with tempfile.TemporaryDirectory(prefix="ternforge-triage-request-") as scratch:
        request_path=Path(scratch)/"request.json"
        result_path=Path(scratch)/"result.json"
        request_path.write_text(json.dumps(request))
        completed=subprocess.run(
          [shutil.which("uv") or "uv","run","--with",CROSSHAIR_REQUIREMENT,"python",str(ROOT/".ai-bridge/survivor_equivalence.py"),"triage",str(request_path),str(result_path)],
          cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},
        )
        if completed.returncode!=0 or not result_path.exists():
            raise RuntimeError("the survivor triage failed:\n"+"\n".join((completed.stdout or "").splitlines()[-20:]))
        return json.loads(result_path.read_text())


def assess_survivors(contract_ids=None):
    """Judge the surviving rule mutants of every contract whose campaign result counts: the symbolic
    search first, then the assessors for the ones it leaves unsure, within the budget. Nothing here
    changes a mutant's outcome. Only a person starts it, on request."""
    policy=model_generation_policy()
    state=assessor_calibration_state(policy)
    usable=qualified_model_backends()
    run=None
    if usable:
        run=MODELS.Run({**policy["roles"],**assessor_roles(policy)},policy["budget"])
        for name in MODELS.BACKENDS:
            if name not in usable:
                run.availability[name]="the adapter has not yet been shown to read this backend's answers"
    else:
        print("[TRIAGE] the model adapter is not qualified: symbolic search only",flush=True)
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    actual=implementation_fault_actual()
    needs=current_needs()
    TRIAGE_RESULTS_DIR.mkdir(parents=True,exist_ok=True)
    cache=load_symbolic_cache()
    for contract_id,entry in sorted((campaign.get("contracts") or {}).items()):
        if contract_ids and contract_id not in contract_ids:
            continue
        if (actual.get(contract_id) or {}).get("state")!="current":
            continue
        report_path,records=rule_survivors(entry)
        if not records:
            # Nothing survives any more: a triage of earlier survivors would describe another run.
            if (TRIAGE_RESULTS_DIR/f"{contract_id}.json").exists():
                (TRIAGE_RESULTS_DIR/f"{contract_id}.json").unlink()
                print(f"[TRIAGE] {contract_id}: no survivors left, its triage removed",flush=True)
            continue
        answers_path=TRIAGE_ANSWERS_DIR/contract_id/"assessments.json"
        assessments=load_assessments(answers_path)
        started=time.monotonic()
        result=run_triage(triage_request(contract_id,records,assessments,needs,policy,state,cache))
        cache.update(result.get("symbolic_cache") or {})
        asked=False
        if run is not None:
            by_fingerprint={str(record.get("fingerprint")):record for record in records}
            for row in result["rows"]:
                # A symbolic search that could not run leaves the harness usable: an assessor's input is still checked by execution.
                if row.get("status")!="unsure":
                    continue
                record=by_fingerprint[str(row["fingerprint"])]
                prompt=rule_assessment_prompt(contract_id,record,needs.get(contract_id) or {})
                if prompt is None:
                    continue
                entry_answers=assessments.setdefault(str(row["fingerprint"]),{})
                asked=ask_assessors(run,policy,purpose="survivor-assessment",contract_id=contract_id,subject=str(row["fingerprint"]),prompt=prompt,entry=entry_answers,response_dir=TRIAGE_ANSWERS_DIR/contract_id/"responses") or asked
            if asked:
                save_assessments(answers_path,assessments)
                result=run_triage(triage_request(contract_id,records,assessments,needs,policy,state,cache))
                cache.update(result.get("symbolic_cache") or {})
        request=triage_request(contract_id,records,assessments,needs,policy,state,{})
        retained={
          "schema":"ternforge-survivor-triage-1","contract_id":contract_id,
          "binding":triage_binding(request,report_path,records),
          "rows":[{key:value for key,value in row.items() if key not in {"original","mutated"}} for row in result["rows"]],
          "seconds":round(time.monotonic()-started,1),"judged_at":utc_now(),
        }
        (TRIAGE_RESULTS_DIR/f"{contract_id}.json").write_text(json.dumps(retained,indent=1,sort_keys=True)+"\n")
        counts=Counter(row.get("status") for row in result["rows"])
        print(f"[TRIAGE] {contract_id}: "+", ".join(f"{count} {name}" for name,count in sorted(counts.items()))+f" in {retained['seconds']}s",flush=True)
        save_symbolic_cache(cache)
    if run is not None:
        summary=run.summary()
        print(f"[TRIAGE] {summary['calls']} assessor calls, {tokens_text(summary['tokens']['total'])} tokens"+(f", ${summary['list_usd']:.3f} at list price" if summary["list_usd"] is not None else ""),flush=True)


def survivor_judgement_counts(triage,semantic,decided=None):
    """How the survivor judgement stands per fault class: rule survivors by their operator's class,
    undecided and judged semantic mutants by theirs, and what the verdicts that count decided."""
    counts={}
    for entry in (decided or {}).values():
        verdict=entry.get("verdict")
        klass=entry["item"].get("class")
        if not verdict or not klass:
            continue
        name={"pin":"pinned" if entry.get("pin") else "pin_pending","equivalent":"suppressed","irrelevant":"suppressed","escalate":"escalated"}[verdict["verdict"]]
        counts.setdefault(klass,Counter())["verdict_"+name]+=1
    for row in (triage.get("rows") or {}).values():
        klass=IMPL_FAULTS.CLASS_BY_OPERATOR.get(str(row.get("operator")))
        if klass:
            state=counts.setdefault(klass,Counter())
            state[str(row.get("status"))]+=1
    for row in semantic.get("results") or []:
        status=(row.get("judgement") or {}).get("status")
        if status:
            counts.setdefault(row["class"],Counter())[status]+=1
    return {klass:dict(sorted(state.items())) for klass,state in sorted(counts.items())}


def survivor_triage_actual():
    """Per contract, the retained triage of its surviving rule mutants while it still counts."""
    policy=model_generation_policy()
    state=assessor_calibration_state(policy)
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    needs=current_needs()
    result={}
    for contract_id,entry in sorted((campaign.get("contracts") or {}).items()):
        path=TRIAGE_RESULTS_DIR/f"{contract_id}.json"
        if not path.exists():
            continue
        retained=json.loads(path.read_text())
        report_path,records=rule_survivors(entry)
        assessments=load_assessments(TRIAGE_ANSWERS_DIR/contract_id/"assessments.json")
        request=triage_request(contract_id,records,assessments,needs,policy,state,{})
        current=retained.get("binding")==triage_binding(request,report_path,records)
        result[contract_id]={"current":current,"rows":{str(row["fingerprint"]):row for row in retained.get("rows") or []} if current else {}}
    return result


def semantic_mutant_actual(plans=None,test_rows=None,apply_verdicts=True):
    """Per contract that selects semantic mutants: whether the retained cascade result still counts,
    what it says about each class, and where its proposals came from and what they cost. A result
    that does not count, and a selected target without any proposal, leave their classes undecided."""
    test_rows=junit_depth_rows() if test_rows is None else test_rows
    plans=implementation_fault_plans(test_rows) if plans is None else plans
    needs=current_needs()
    qualification=load_evidence_qualification()
    producers_ok=qualification_is_current(qualification) and all(
      str(((qualification.get("producers") or {}).get(producer_id) or {}).get("status") or "").upper()=="QUALIFIED"
      for producer_id in SEMANTIC_PRODUCERS
    )
    ledger=MODELS.read_ledger()
    result={}
    for contract_id,target in semantic_selections().items():
        payload,proposals=semantic_proposal_set(contract_id,target)
        path=SEMANTIC_RESULTS_DIR/f"{contract_id}.json"
        retained=json.loads(path.read_text()) if path.exists() else {}
        contexts=semantic_contexts(contract_id,target,needs)
        selections=target.get("semantic_mutants") or []
        missing=SEMANTIC.targets_without_proposals(selections,proposals)
        if not proposals:
            state,reason="not_generated","no semantic mutant has been generated for its targets yet"
        elif not retained:
            state,reason="not_run","the semantic mutant cascade has not run for this contract yet"
        elif retained.get("binding")!=semantic_binding(contract_id,plans.get(contract_id) or {},test_rows,contexts,semantic_judgement_request(contract_id,proposals,needs)):
            state,reason="stale","its proposals, drafts, target code, tests or generation context changed since the cascade ran"
        elif not producers_ok:
            state,reason="unqualified","the semantic mutant cascade is not currently qualified"
        else:
            state,reason="current",""
        classes={}
        if state=="current" and apply_verdicts:
            # A verdict that counts and calls a survivor equivalent or irrelevant takes it out of its class (ADR_0006).
            decided=(verdict_state().get(contract_id) or {}).get("items") or {}
            retained={**retained,"results":[
              {**row,"outcome":"equivalent","reason":f"judged {decided[row['id']]['verdict']['verdict']} by {decided[row['id']]['verdict'].get('by')}: {decided[row['id']]['verdict'].get('reason')}","by":decided[row["id"]]["verdict"].get("by")}
              if row.get("id") in decided and decided[row["id"]]["verdict"] and decided[row["id"]]["verdict"]["verdict"] in {"equivalent","irrelevant"} else row
              for row in retained.get("results") or []
            ]}
        if state=="current":
            classes=SEMANTIC.class_projection(retained.get("results") or [])
        else:
            for proposal in proposals:
                row=classes.setdefault(proposal["class"],{"exercised":False,"detected":False,"undecided":0,"counts":{}})
                row["undecided"]+=1
        classes=SEMANTIC.add_targets_without_proposals(classes,missing)
        calls=[row for row in ledger if row.get("contract_id")==contract_id and row.get("role")!="probe"]
        # The attempts of the last call for each target: every backend it tried, in order.
        last_attempts={}
        for row in calls:
            if row.get("purpose")!="semantic-mutants":
                continue
            group=last_attempts.get(row.get("subject")) or []
            last_attempts[row.get("subject")]=[*group,row] if group and group[-1].get("run_id")==row.get("run_id") else [row]
        # What generating the mutants and drafts cost; judging survivors is counted apart.
        generation_calls=[row for row in calls if row.get("purpose") in {"semantic-mutants","semantic-draft"}]
        top=payload.get("generator") or {}
        origins=Counter(str((proposal.get("generator") or top).get("kind") or "unknown") for proposal in proposals)
        judged=[row.get("draft") or {} for row in retained.get("results") or [] if state=="current" and row.get("draft")]
        result[contract_id]={
          "state":state,"reason":reason,"classes":classes,
          "results":retained.get("results") or [] if state=="current" else [],
          "proposals":proposals,"generator":top,
          "missing":[{**selection,"attempts":last_attempts.get(selection["target"]) or []} for selection in missing],
          "draft_provenance":load_draft_provenance(SEMANTIC.PROPOSAL_ROOT/contract_id),
          "calls":{row["call_id"]:row for row in calls},
          "generation":{
            "targets":len(selections),
            "not_generated":len(missing),
            "mutants":dict(sorted(origins.items())),
            "drafts":{"kept":sum(bool(row.get("accepted")) for row in judged),"rejected":sum(not row.get("accepted") for row in judged)},
            "runs":len({row.get("run_id") for row in generation_calls}),
            "spend":MODELS.spend(generation_calls),
          },
        }
    return result


def contracts_asking_for_implementation_classes(policy=None):
    policy=policy or project_monitor_policy()
    asking=set()
    for contract_id,need in current_needs().items():
        if need.get("type") not in {"req","treq"}:
            continue
        target=requirement_monitor_target(contract_id,policy) or {}
        if any(
          item.get("id") in IMPL_FAULTS.CLASSES and item.get("state") in {"required","optional"}
          for group in target.get("fault_groups") or []
          for item in group.get("items") or []
        ):
            asking.add(contract_id)
    return asking


def implementation_fault_actual():
    """Current Implementation fault classes per contract, fail-closed."""
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    asking=contracts_asking_for_implementation_classes()
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    shared_sha256=sha256_text(stable_json(IMPL_FAULTS.shared_inputs(ROOT)))
    qualification=load_evidence_qualification()
    producers_ok=qualification_is_current(qualification) and all(
      str(((qualification.get("producers") or {}).get(producer_id) or {}).get("status") or "").upper()=="QUALIFIED"
      for producer_id in IMPL_FAULTS.PRODUCERS
    )
    result={}
    for contract_id,plan in plans.items():
        entry=(campaign.get("contracts") or {}).get(contract_id) or {}
        run=entry.get("run") or {}
        if contract_id not in asking:
            classes=IMPL_FAULTS.blocked_classes("The verification profile does not ask for Implementation fault classes.")
            state="not_applicable"
        elif plan.get("blocked"):
            classes=IMPL_FAULTS.blocked_classes(IMPL_FAULTS.blocked_basis(plan))
            state="blocked"
        elif not entry:
            classes=IMPL_FAULTS.blocked_classes("The implementation fault campaign has not run for this contract yet.")
            state="not_run"
        else:
            state,reason=retained_campaign_entry_state(entry,plan,shared_sha256,test_rows)
            if state=="current":
                classes=IMPL_FAULTS.project_classes(plan,json.loads((ROOT/run["report_path"]).read_text()),ROOT,verdict_suppressions(contract_id))
            else:
                classes=IMPL_FAULTS.blocked_classes(
                  f"The last mutation result no longer counts ({reason}); re-run the campaign."
                )
        if state=="current" and not producers_ok:
            classes={
              class_id:{**row,"exercised":False,"detected":False,"basis":"The mutation engine or its class mapping is not currently qualified, so its result is not trusted: "+row["basis"]}
              for class_id,row in classes.items()
            }
            state="unqualified"
        for row in classes.values():
            row["source"]="implementation_fault_campaign"
            row["campaign_state"]=state
            row["producer_ids"]=list(IMPL_FAULTS.PRODUCERS)
        result[contract_id]={
          "state":state,
          "classes":classes,
          "shared_with":plan.get("shared_with") or [],
          "scopes":plan.get("scopes") or [],
          "tests":len(plan.get("tests") or []),
          "tests_not_passing":plan.get("tests_not_passing") or [],
        }
    return result


def contract_index():
    """Every Requirement and Technical requirement with the title, revision and page a monitor names."""
    contracts={}
    for contract_id,need in current_needs().items():
        if need.get("type") not in {"req","treq"}:
            continue
        contracts[contract_id]={
          "id":contract_id,
          "title":need.get("title") or contract_id,
          "revision":need.get("revision"),
          "contract_url":f"{need.get('docname')}.html#{contract_id}" if need.get("docname") else f"traceability-reader.html#review-{contract_id}",
        }
    return {"contracts":contracts}


def requirement_monitor_model(base_model):
    policy=project_monitor_policy()
    junit_actual=junit_monitor_actual()
    junit_faults=junit_fault_actual(policy)
    implementation_faults=implementation_fault_actual()
    semantic_faults=semantic_mutant_actual()
    triage_faults=survivor_triage_actual()
    fault_model=json.loads(ASSURANCE_FACTS_PATH.read_text()) if ASSURANCE_FACTS_PATH.exists() else {}
    result={
      "schema":"ternforge-requirement-monitor-p34-2",
      "policy":policy,
      "status_values":["PASS","FAIL","N/A","UNKNOWN"],
      "levels":[
        ["component","Component"],
        ["component_integration","Component integration"],
        ["system","System"],
        ["system_integration","System integration"],
        ["acceptance","Acceptance"],
      ],
      "boundaries":[
        ["none","Local"],
        ["substitute","Substitute"],
        ["replay","Replay"],
        ["direct","Direct live"],
      ],
      "representation":[
        ["synthetic_abstract","Synthetic"],
        ["surrogate_simulated","Surrogate"],
        ["representative","Representative"],
        ["actual","Actual"],
      ],
      "contracts":{},
    }
    for contract_id,base in (base_model.get("contracts") or {}).items():
        target=requirement_monitor_target(contract_id,policy)
        if not target:
            continue
        raw_contract_fault=((fault_model.get("contracts") or {}).get(contract_id) or {})
        specialized_probe_current=specialized_fault_binding_current(
          contract_id,raw_contract_fault
        )
        contract_fault=raw_contract_fault if specialized_probe_current else {}
        layers=contract_fault.get("layers") or {}
        class_actual={}
        # Implementation classes come from the generic mutation campaign for every
        # contract; a class is detected only when all of its attributable faults are.
        class_actual.update(
          json.loads(json.dumps(
            ((implementation_faults.get(contract_id) or {}).get("classes") or {})
          ))
        )
        layer_map={
          "runtime.latency-timeout":"runtime",
          "interface.unexpected-interaction":"interface",
          "architecture.forbidden-edge":"architecture",
          "spec.wrong-outcome":"specification",
        }
        for class_id,layer_id in layer_map.items():
            layer=layers.get(layer_id) or {}
            if not layer:
                continue
            caught=bool(layer.get("detected"))
            class_actual[class_id]={
              "exercised":bool(layer.get("generated")),
              "detected":caught,
              "source":"specialized_probe",
              "basis":(
                f"Specialized {str(layer.get('label') or layer_id).lower()} probe: "
                f"the injected fault was {'caught' if caught else 'not caught'}."
              ),
            }

        retained_classes=(junit_faults.get(contract_id) or {})
        for class_id,retained in retained_classes.items():
            previous=class_actual.get(class_id) or {"exercised":False,"detected":False}
            previous_exercised=bool(previous.get("exercised"))
            retained_exercised=bool(retained.get("exercised"))
            exercised=previous_exercised or retained_exercised
            detected=bool(
              exercised
              and (not previous_exercised or previous.get("detected"))
              and (not retained_exercised or retained.get("detected"))
            )
            declared=int(retained.get("declared_paths") or 0)
            retained_basis=(
              f"{int(retained.get('detected_paths') or 0)} of {declared} retained test "
              "challenge(s) caught the injected fault."
              if retained_exercised else
              f"{declared} retained test challenge(s) declared, but no current run recorded the injected fault."
            )
            class_actual[class_id]={
              **previous,
              **retained,
              "exercised":exercised,
              "detected":detected,
              "basis":" ".join(
                str(part) for part in (
                  previous.get("basis") if previous_exercised else "",
                  retained_basis,
                ) if part
              ),
              "sources":{
                "specialized_probe":previous,
                "retained_test_challenge":retained,
              },
            }

        # Semantic mutants challenge a class beside its retained tests: the class is caught only when every
        # decided challenge is caught, and a challenge that ran but is undecided (or no longer counts) keeps
        # it UNKNOWN.
        semantic=semantic_faults.get(contract_id) or {}
        for class_id,projected in (semantic.get("classes") or {}).items():
            previous=class_actual.get(class_id) or {"exercised":False,"detected":False}
            previous_exercised=bool(previous.get("exercised"))
            semantic_exercised=bool(projected.get("exercised"))
            exercised=previous_exercised or semantic_exercised
            counts=projected.get("counts") or {}
            not_generated=int(projected.get("not_generated") or 0)
            semantic_basis=(
              f"Semantic mutants: {int(counts.get('caught') or 0)} caught, {int(counts.get('distinguished') or 0)} tell apart "
              f"from the original with no test failing, {int(projected.get('undecided') or 0)} undecided."
              +(f" {not_generated} selected target{'s have' if not_generated!=1 else ' has'} no generated mutant yet." if not_generated else "")
              if semantic.get("state")=="current" else
              f"Semantic mutants do not count yet: {semantic.get('reason')}."
            )
            class_actual[class_id]={
              **previous,
              "exercised":exercised,
              "detected":bool(
                exercised
                and (not previous_exercised or previous.get("detected"))
                and (not semantic_exercised or projected.get("detected"))
              ),
              "undecided":int(previous.get("undecided") or 0)+int(projected.get("undecided") or 0),
              # The group's mutant tally counts semantic mutants as the campaign's: caught, and surviving on a
              # distinguishing input.
              "caught":int(previous.get("caught") or 0)+int(counts.get("caught") or 0),
              "survived_reached":int(previous.get("survived_reached") or 0)+int(counts.get("distinguished") or 0),
              "semantic_state":semantic.get("state"),
              "semantic_counts":counts,
              "semantic_not_generated":not_generated,
              "basis":" ".join(part for part in (str(previous.get("basis") or "") if previous_exercised else "",semantic_basis) if part),
              "producer_ids":sorted({*(ids if isinstance(ids:=previous.get("producer_ids"),list) else []),*SEMANTIC_PRODUCERS}),
            }

        for fault_group in policy.get("fault_groups") or []:
            for class_id in fault_group.get("classes") or []:
                class_actual.setdefault(
                  class_id,
                  {
                    "exercised":False,
                    "detected":False,
                    "basis":"Not challenged: no retained test declares this fault class for this contract.",
                  },
                )

        target_criteria={item for cell in (target.get("coverage") or []) for item in (cell.get("items") or [])}
        coverage_actual={key:value for key,value in junit_actual.items() if key in target_criteria}
        result["contracts"][contract_id]={
          "id":contract_id,
          "title":base.get("title") or contract_id,
          "revision":base.get("revision"),
          "contract_url":base.get("contract_url"),
          "target":target,
          "coverage_actual":coverage_actual,
          "fault_actual":{
            "classes":class_actual,
            "specialized_probe_current":specialized_probe_current,
            "specialized_probe_binding":raw_contract_fault.get("binding"),
            "layers":layers,
            "retained_challenges":retained_classes,
            "semantic_generation":(semantic_faults.get(contract_id) or {}).get("generation"),
            "survivor_judgement":survivor_judgement_counts(triage_faults.get(contract_id) or {},semantic_faults.get(contract_id) or {},(verdict_state().get(contract_id) or {}).get("items")),
            "raw_url":"requirement-monitor-facts.json",
          },
        }
    # Tests that claim to verify a contract but serve none of the profile's cases
    # (and are not goal/capability scenarios or fault challenges) are kept visible:
    # a failing one must turn the contract red instead of being silently ignored.
    bindings=junit_test_bindings()
    criterion_owner={
      criterion_id:owner
      for contract in result["contracts"].values()
      for criterion_id,owner in ((contract.get("target") or {}).get("criterion_contracts") or {}).items()
    }
    junit_rows=junit_depth_rows()
    for contract_id,contract in result["contracts"].items():
        linked=[]
        for row in junit_rows:
            if contract_id not in (row.get("verifies") or []):
                continue
            binding=bindings.get(row["nodeid"]) or {}
            if binding.get("assurance_item") or binding.get("fault_challenge") or is_mutation_pin(row["nodeid"]):
                continue
            if criterion_owner.get(binding.get("coverage_item") or ""):
                continue
            linked.append({"nodeid":row["nodeid"],"result":row.get("result")})
        contract["linked_outside_profile"]=linked
    return result


def patch_contract_evidence_view():
    if not ASSURANCE_PAGE.exists():
        return
    text=ASSURANCE_PAGE.read_text()
    if "TERNFORGE-NO-CACHE" not in text:
        text=text.replace(
          "<head>",
          '<head>\n<!-- TERNFORGE-NO-CACHE -->\n'
          '<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">\n'
          '<meta http-equiv="Pragma" content="no-cache">\n'
          '<meta http-equiv="Expires" content="0">',
          1,
        )
    monitor_model=requirement_monitor_model(contract_index())
    (ASSURANCE_PAGE.parent/"requirement-monitor-facts.json").write_text(
        json.dumps(monitor_model,indent=2,sort_keys=True)+"\n"
    )
    EVIDENCE_CLASSIFICATION_PATH.write_text(
        json.dumps(
          {
            "schema":"ternforge-evidence-classification-1",
            "qualification_current":qualification_is_current(load_evidence_qualification()),
            "testcases":evidence_classification_index(),
          },
          indent=2,sort_keys=True,
        )+"\n"
    )

    # Contract Evidence is an assurance/confidence view. Execution health and
    # mutation workflow remain in their own monitors/journals.
    text=re.sub(
      r"<!-- TERNFORGE-P22-MUTATION-START:[^>]+ -->.*?<!-- TERNFORGE-P22-MUTATION-END:[^>]+ -->",
      "",text,flags=re.DOTALL
    )
    text=re.sub(
      r"<!-- TERNFORGE-P27-CONTRACT-EVIDENCE-START -->.*?<!-- TERNFORGE-P27-CONTRACT-EVIDENCE-END -->",
      "",text,flags=re.DOTALL
    )
    text=re.sub(
      r"<!-- TERNFORGE-(?:P2[789]|P3[0-3])-ASSURANCE-EVIDENCE-START -->.*?<!-- TERNFORGE-(?:P2[789]|P3[0-3])-ASSURANCE-EVIDENCE-END -->",
      "",text,flags=re.DOTALL
    )
    text=re.sub(
      r"<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-START -->.*?<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-END -->",
      "",text,flags=re.DOTALL
    )
    text=text.replace("Verification assurance map","Contract Evidence")
    ASSURANCE_PAGE.write_text(text)

    for path in (
      ROOT/"docs/_build/html/llms.txt",
      ROOT/"docs/_build/html/searchindex.js",
    ):
        if path.exists():
            path.write_text(path.read_text().replace("Verification assurance map","Contract Evidence"))


def patch_traceability_contract_evidence_links():
    path=ROOT/"docs/_build/html/traceability-reader.html"
    if not path.exists():
        return
    text=path.read_text()
    text=re.sub(
      r"<!-- TERNFORGE-P27-TRACE-EVIDENCE-START -->.*?<!-- TERNFORGE-P27-TRACE-EVIDENCE-END -->",
      "",text,flags=re.DOTALL
    )
    text=text.replace(
      'For the contract-by-contract runtime proof path, open\n<a class="reference internal" href="verification-assurance.html"><span class="doc">Verification assurance map</span></a>. For a one-screen overview of the same specification,',
      "For contract-level proof, use the <strong>Contract evidence</strong> link on the Requirement / TREQ you are reviewing. For retained execution health,"
    )
    text=text.replace(
      'open <a class="reference internal" href="specification-map.html"><span class="doc">Specification map</span></a>.',
      'open <a class="reference internal" href="verification-health-map.html"><span class="doc">Verification Health Map</span></a>.',
    )
    monitor_path=ROOT/"docs/_build/html/requirement-monitor-facts.json"
    monitor=json.loads(monitor_path.read_text()) if monitor_path.exists() else {"contracts":{}}
    routes={}
    for parent_id,contract_data in (monitor.get("contracts") or {}).items():
        slug=parent_id.lower()
        for prefix in ("req_","treq_"):
            if slug.startswith(prefix):
                slug=slug.removeprefix(prefix)
                break
        slug=slug.replace("_","-")
        href=(
          f"verification-assurance.html#ce-coverage-{parent_id.lower()}"
          if parent_id=="REQ_INVALID_CONFIGURATION_ERRORS"
          else f"contract-evidence-{slug}.html#ce-coverage-{parent_id.lower()}"
        )
        routes[parent_id]=href
        for child_id in set(((contract_data.get("target") or {}).get("criterion_contracts") or {}).values()):
            routes.setdefault(child_id,href)
    routes_json=json.dumps(routes,sort_keys=True)
    block=r"""<!-- TERNFORGE-P27-TRACE-EVIDENCE-START -->
<style>
.tf-contract-evidence-link{display:flex;justify-content:flex-end;margin-top:.35rem;font-size:.74rem;font-weight:650}
</style>
<script>
(() => {
  const routes=__CONTRACT_EVIDENCE_ROUTES__;
  const cards=document.querySelectorAll(".ternforge-trace-current,.ternforge-trace-rule-card");
  for(const card of cards) {
    if(card.querySelector(":scope > .tf-contract-evidence-link")) continue;
    const anchors=[...card.querySelectorAll('a[href*="#REQ_"],a[href*="#TREQ_"]')];
    const contract=anchors.find(a=>/^#(?:REQ|TREQ)_/.test(new URL(a.href).hash));
    if(!contract) continue;
    const id=new URL(contract.href).hash.slice(1);
    const href=routes[id];
    if(!href) continue;
    const reviewId="review-"+id;
    if(!document.getElementById(reviewId)) card.id=reviewId;
    const row=document.createElement("div");
    row.className="tf-contract-evidence-link";
    row.innerHTML='<a href="'+href+'" title="What proves this contract now?">Contract evidence →</a>';
    const technical=card.querySelector(":scope > details.ternforge-review-technical");
    if(technical) card.insertBefore(row,technical); else card.appendChild(row);
  }
  const selected=location.hash ? document.querySelector(location.hash) : null;
  if(selected) window.setTimeout(()=>selected.scrollIntoView({block:"center"}),0);
})();
</script>
<!-- TERNFORGE-P27-TRACE-EVIDENCE-END -->"""
    block=block.replace("__CONTRACT_EVIDENCE_ROUTES__",routes_json)
    text=text.replace("</body>",block+"\n</body>",1)
    path.write_text(text)


def patch_verification_contract_evidence_path():
    path=ROOT/"docs/_build/html/verification.html"
    if path.exists():
        text=path.read_text()
        text=re.sub(
          r'(<section id="assurance-reading-path">\s*<h2>).*?(?=</section>)',
          lambda m:m.group(1)+
          'Assurance reading path<a class="headerlink" href="#assurance-reading-path" title="Link to this heading">#</a></h2>'
          '<p>Start in <a class="reference internal" href="traceability-reader.html"><span class="doc">Traceability Reader</span></a>. '
          'Requirements and Technical requirements with an accepted Verification Profile expose a <strong>Contract evidence</strong> link to their dedicated Target → Actual monitor; unprofiled contracts do not claim one yet. '
          'Use that page to inspect required verification cells, retained path properties, selected fault checks, and current gaps. '
          'The Verification Health Map shows where the system fails and how deep its evidence reaches; the Verification Explorer lists every item behind those counts, mutants included.</p>',
          text,count=1,flags=re.DOTALL
        )
        path.write_text(text)

    trust=ROOT/"docs/_build/html/evidence-trust.html"
    if trust.exists():
        text=trust.read_text().replace(
          "<p>Return to verification-assurance for claim-centric layered proof.</p>",
          '<p>Return to <a href="traceability-reader.html">Traceability Reader</a> and reopen Contract evidence for the Requirement / TREQ under review.</p>'
        )
        trust.write_text(text)


def patch_evidence_trust_need_anchors():
    """Route hidden producer/qualification IDs to visible Evidence Trust anchors."""
    trust_path=ROOT/"docs/_build/html/evidence-trust.html"
    if not trust_path.exists():
        return
    trust=trust_path.read_text()
    need_id_pattern=r"(?:PRODUCER|QUAL)_[A-Z0-9_]+"
    trust=re.sub(
      rf'href="evidence-producers\.html#({need_id_pattern})"',
      lambda match:f'href="#{match.group(1)}"',
      trust,
    )
    trust_ids=sorted(set(re.findall(rf'href="#({need_id_pattern})"',trust)))
    for need_id in trust_ids:
        if f'id="{need_id}"' in trust:
            continue
        trust,count=re.subn(
          rf'(<a class="reference external" href="#{re.escape(need_id)}")',
          f'<span id="{need_id}" class="tf-need-anchor-alias" aria-hidden="true"></span>\\1',
          trust,
          count=1,
        )
        if count!=1:
            raise RuntimeError(f"unable to materialize Evidence Trust anchor {need_id}")
    trust_path.write_text(trust)

    generated_root=ROOT/"docs/_build/html"
    producer_link=re.compile(
      rf'href="(?:(?:\.\./)*)evidence-producers\.html#({need_id_pattern})"'
    )
    for path in generated_root.rglob("*.html"):
        if path==trust_path:
            continue
        text=path.read_text()
        if not producer_link.search(text):
            continue
        relative=os.path.relpath(trust_path,path.parent).replace(os.sep,"/")
        text=producer_link.sub(
          lambda match:f'href="{relative}#{match.group(1)}"',
          text,
        )
        path.write_text(text)


def patch_living_semantic_pages():
    pages=sorted((ROOT/"docs/_build/html/specifications/_generated").glob("**/*.html"))
    block=r"""<!-- TERNFORGE-P28-LIVING-SEMANTICS-START -->
<script>
(() => {
  const root=document.querySelector("article.bd-article");
  if(!root) return;
  const text=node=>(node?.textContent||"").trim();

  // Living Specifications describe semantics and proof logic, not current run health.
  root.querySelectorAll(".sd-badge").forEach(badge=>{
    if(text(badge)==="Verified") badge.remove();
  });
  root.querySelectorAll("strong").forEach(node=>{
    if(/^\d+\/\d+ passed$/.test(text(node))) node.remove();
  });
  root.querySelectorAll("p").forEach(p=>{
    const value=text(p);
    if(/^\d+\/\d+ passed$/.test(value) || /^Verified\s+\d+\/\d+ passed$/.test(value)) {
      p.remove(); return;
    }
    const strong=p.querySelector(":scope > strong:first-child");
    const label=text(strong);
    if(label==="Evidence producers:" || value==="No complementary evidence linked." || label==="Remaining gap:") {
      p.remove(); return;
    }
    if(label==="Boundary basis:") {
      p.remove(); return;
    }
    for(const node of [...p.childNodes]) {
      if(node.nodeType===Node.TEXT_NODE) {
        node.textContent=node.textContent
          .replace(/\s*—\s*\d+\/\d+ passed\s*/g," ")
          .replace(/^\s*\d+\/\d+ passed\s*$/g,"")
          .replace(/\s+—\s*$/g,"");
      }
    }
  });

  // Move the semantic proof criterion out of the runtime-boundary card, then
  // delete the boundary/envelope mechanics from the semantic narrative.
  root.querySelectorAll(".sd-card-title").forEach(title=>{
    if(text(title)!=="Verification boundary") return;
    const card=title.closest(".sd-card");
    if(!card) return;
    const proof=[...card.querySelectorAll("details")].find(d=>text(d.querySelector("summary .sd-summary-text"))==="How this scenario establishes the proof");
    if(proof) {
      const summary=proof.querySelector("summary .sd-summary-text");
      if(summary) summary.textContent="Proof logic";
      proof.querySelectorAll("p").forEach(p=>{
        const strong=p.querySelector("strong");
        if(text(strong)==="Injected condition:") strong.textContent="Condition:";
        if(text(strong)==="Observed proof:") strong.textContent="Proof criterion:";
        if(text(strong)==="Boundary basis:") p.remove();
      });
      card.parentNode.insertBefore(proof,card);
    }
    card.remove();
  });

  root.querySelectorAll("details.living-technical-details").forEach(details=>{
    const summary=details.querySelector("summary .sd-summary-text");
    if(summary) summary.textContent="Binding details";
    details.querySelectorAll("p").forEach(p=>{
      const label=text(p.querySelector("strong"));
      if(label==="Status:" || label==="Executed:" || label==="Duration:") p.remove();
    });
  });

  root.querySelectorAll("a").forEach(a=>{
    if(text(a)==="Execution evidence ↗") a.textContent="Raw execution evidence ↗";
  });
  root.querySelectorAll("strong").forEach(node=>{
    if(text(node)==="Verified contract:") node.textContent="Contract:";
  });

  // From semantics, assurance is a deliberate cross-link, not duplicated data.
  root.querySelectorAll("p").forEach(p=>{
    const strong=p.querySelector(":scope > strong:first-child");
    if(text(strong)!=="Verifies:" || p.querySelector(".tf-contract-evidence-semantic-link")) return;
    const need=p.querySelector('a[href*="#REQ_"],a[href*="#TREQ_"]');
    if(!need) return;
    const id=new URL(need.href).hash.slice(1);
    const a=document.createElement("a");
    a.className="sd-sphinx-override sd-badge sd-outline-secondary sd-text-secondary reference external tf-contract-evidence-semantic-link";
    a.href="../../../verification-assurance.html#assurance-"+id.toLowerCase();
    a.textContent="Why trust this evidence? →";
    p.append(" ");
    p.appendChild(a);
  });
})();
</script>
<!-- TERNFORGE-P28-LIVING-SEMANTICS-END -->"""
    for path in pages:
        text=path.read_text()
        text=re.sub(
          r"<!-- TERNFORGE-P28-LIVING-SEMANTICS-START -->.*?<!-- TERNFORGE-P28-LIVING-SEMANTICS-END -->",
          "",text,flags=re.DOTALL
        )
        text=text.replace("</body>",block+"\n</body>",1)
        path.write_text(text)


def patch_legacy_overview_links():
    """Keep legacy DocOps overview routes out of the normal portal reading flow."""
    html_root = ROOT / "docs/_build/html"
    legacy_pages = {
        html_root / "specification-map.html",
        html_root / "specification-health.html",
    }
    for path in html_root.rglob("*.html"):
        if path in legacy_pages:
            continue
        text = path.read_text()
        original = text
        text = text.replace("specification-map.html", "verification-health-map.html")
        text = text.replace("specification-health.html", "verification-health-map.html")
        text = re.sub(
            r'(<a[^>]*href="[^"]*verification-health-map\.html"[^>]*>\s*(?:<span class="doc">)?)(?:Specification map|Specification health|Release health)(?=(?:</span>)?</a>)',
            lambda match: match.group(1) + "Verification Health Map",
            text,
            flags=re.IGNORECASE,
        )
        if text != original:
            path.write_text(text)


def patch_portal_navigation():
    pages={
      ROOT/"docs/_build/html/index.html":None,
      ROOT/"docs/_build/html/verification.html":None,
      HEALTH_PAGE:None,
      EXPLORER_PAGE:None,
      ASSURANCE_PAGE:None,
    }
    for path,current in pages.items():
        if path.exists():
            path.write_text(patch_navigation_text(path.read_text(),current=current))

def ensure_root_favicon():
    """Keep direct JSON evidence drill-downs free of browser-generated /favicon.ico 404 noise."""
    path=ROOT/"docs/_build/html/favicon.ico"
    if path.exists():
        return
    width=height=16
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",binascii.crc32(kind+data)&0xffffffff)
    raw=b"".join(b"\x00"+(b"\x00\x00\x00\x00"*width) for _ in range(height))
    png=(
      b"\x89PNG\r\n\x1a\n"
      +chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0))
      +chunk(b"IDAT",zlib.compress(raw,9))
      +chunk(b"IEND",b"")
    )
    header=struct.pack("<HHH",0,1,1)
    entry=struct.pack("<BBBBHHII",width,height,0,0,1,32,len(png),22)
    path.write_bytes(header+entry+png)


# --- the mutation report (Mutation Testing Report Schema 2) -------------------------

MUTATION_REPORT_JSON=ROOT/"docs/_build/html/mutation-report.json"
MTE_STATUS={"caught":"Killed","survived":"Survived","notreached":"NoCoverage","invalid":"RuntimeError","suppressed":"Ignored"}


def mutation_report():
    """The retained campaign in the Mutation Testing Report Schema: every mutated source file with the
    mutants of every contract whose result still counts, the suppressed ones and those arid code kept
    out as Ignored with their reason. A contract whose result no longer counts is left out and named."""
    campaign=json.loads(IMPL_FAULT_CAMPAIGN_PATH.read_text()) if IMPL_FAULT_CAMPAIGN_PATH.exists() else {}
    actual=implementation_fault_actual()
    files={}
    tests=defaultdict(set)
    ids=set()
    included,left_out=[],[]

    def add(source,row):
        base=row["id"]
        suffix=1
        while row["id"] in ids:
            suffix+=1
            row["id"]=f"{base}-{suffix}"
        ids.add(row["id"])
        files.setdefault(source,{"language":"python","source":(ROOT/source).read_text(),"mutants":[]})["mutants"].append(row)

    for contract_id,entry in sorted((campaign.get("contracts") or {}).items()):
        if (actual.get(contract_id) or {}).get("state")!="current":
            left_out.append(contract_id)
            continue
        plan=entry.get("plan") or {}
        report=json.loads((ROOT/entry["run"]["report_path"]).read_text())
        raw_by_id={str(row.get("gremlin_id")):row for row in report.get("results") or []}
        for mutant in IMPL_FAULTS.contract_mutants(plan,report,ROOT):
            raw=raw_by_id.get(mutant["id"]) or {}
            outcome=mutant["outcome"]
            row={
              "id":mutant["fingerprint"],
              "mutatorName":mutant["operator"],
              "replacement":mutant["replacement"] or "",
              "location":mutant["location"] or {"start":{"line":mutant["line"],"column":1},"end":{"line":mutant["line"],"column":2}},
              "status":"Timeout" if raw.get("status")=="timeout" else MTE_STATUS[outcome],
              "description":f"{contract_id} · {mutant['class']} · {mutant['description']}",
            }
            if outcome=="suppressed":
                suppression=mutant.get("suppression") or {}
                row["statusReason"]=f"{suppression.get('category') or 'suppressed'}: {suppression.get('reason') or ''}".strip()
            elif outcome=="notreached":
                row["statusReason"]="No test of the contract runs this line."
            elif outcome=="invalid":
                row["statusReason"]=str(raw.get("error_output") or "The mutated code broke test collection.")[:400]
            covered=list(raw.get("selected_tests") or []) if raw.get("covered") else []
            if covered:
                row["coveredBy"]=covered
                for nodeid in covered:
                    tests[nodeid.split("::",1)[0]].add(nodeid)
            add(mutant["source"],row)
        for item in IMPL_FAULTS.not_planted_mutants(plan,report,ROOT):
            add(item["source"],{
              "id":str(item.get("fingerprint") or item.get("gremlin_id")),
              "mutatorName":str(item.get("operator")),
              "replacement":str(item.get("replacement") or ""),
              "location":item.get("location") or {"start":{"line":int(item["line_number"]),"column":1},"end":{"line":int(item["line_number"]),"column":2}},
              "status":"Ignored",
              "statusReason":f"{item.get('rule')}: arid code, not planted",
              "description":f"{contract_id} · {item['class']} · {item.get('description')}",
            })
        included.append(contract_id)
    for source in files.values():
        source["mutants"].sort(key=lambda row:(row["location"]["start"]["line"],row["location"]["start"]["column"],row["id"]))
    return {
      "schemaVersion":"2",
      # Every valid mutant must be caught (Test Plan), so anything less shows as not caught.
      "thresholds":{"high":100,"low":100},
      "projectRoot":".",
      "files":dict(sorted(files.items())),
      "testFiles":{
        path:{"tests":[{"id":nodeid,"name":nodeid.split("::",1)[1]} for nodeid in sorted(nodeids)]}
        for path,nodeids in sorted(tests.items())
      },
      "framework":{"name":"pytest-gremlins","version":IMPL_FAULTS.GREMLINS_VERSION},
      "config":{
        "campaign_schema":campaign.get("schema"),
        "campaign_head_sha":campaign.get("head_sha"),
        "contracts":included,
        "not_current":left_out,
        "rule":"Mutants on each contract's attributable @impl lines, run with the contract's passing tests; NoCoverage means no test of the contract runs the line; Ignored means suppressed by a pragma or kept out as arid code.",
      },
    }


def write_mutation_report_page():
    report=mutation_report()
    MUTATION_REPORT_JSON.write_text(json.dumps(report,separators=(",",":"))+"\n")
    mutants=[row for source in report["files"].values() for row in source["mutants"]]
    judged=[row for row in mutants if row["status"] not in {"Ignored","RuntimeError"}]
    left_out=report["config"]["not_current"]
    summary=(
      f"{len(judged)} judged mutants of {len(report['config']['contracts'])} contracts · "
      f"{sum(row['status'] in {'Killed','Timeout'} for row in judged)} caught · "
      f"{sum(row['status']=='Ignored' for row in mutants)} ignored"
      + (f" · {len(left_out)} contracts left out, their result no longer counts" if left_out else "")
    )
    head=str(report["config"].get("campaign_head_sha") or "")[:12]
    MUTATION_REPORT_PAGE.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mutation report · llm-router</title><script defer src="_static/mutation-test-elements.js"></script>
<style>html,body{{margin:0;min-height:100%;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.tf-bridge{{display:flex;align-items:baseline;gap:.4rem 1rem;flex-wrap:wrap;padding:.6rem 1rem;border-bottom:1px solid #d0d5dd;background:#f8fafc;color:#172033;font-size:.85rem}}
.tf-bridge a{{color:#1d4ed8;text-decoration:none}}.tf-bridge a:hover{{text-decoration:underline}}.tf-bridge span{{color:#475467}}
@media(prefers-color-scheme:dark){{.tf-bridge{{background:#151a21;color:#d0d7de;border-color:#30363d}}.tf-bridge a{{color:#79c0ff}}.tf-bridge span{{color:#9da7b3}}}}</style></head><body>
<nav class="tf-bridge"><a href="verification-explorer.html#kind=mutant">← Verification Explorer</a><strong>Mutation report</strong>
<span>{html_escape(summary)} · campaign at {html_escape(head)}</span>
<a href="verification-health-map.html#faults">Health Map</a><a href="test-plan.html#test-plan-mutation-policy">Mutation policy</a><a href="mutation-report.json">Raw JSON</a></nav>
<mutation-test-report-app src="mutation-report.json" title-postfix="llm-router"></mutation-test-report-app>
</body></html>
""")


# mutmut's page, its raw mutant pages and campaign, its Test Strength facts and the P31 trend
# history are retired (ADR_0003); a build removes what an older build left behind.
RETIRED_MUTATION_ARTIFACTS=(
  ROOT/"docs/_build/html/mutation-analysis.html",
  ROOT/"docs/_build/html/mutation-results",
  ROOT/"docs/_build/html/verification-test-strength-facts.json",
  ROOT/"docs/_build/html/assurance-history",
  ROOT/"docs/_build/html/assurance-snapshots.json",
  ROOT/"docs/_build/html/assurance-targets.json",
)


def remove_retired_mutation_artifacts():
    for path in RETIRED_MUTATION_ARTIFACTS:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def write_semantic_mutant_files():
    """Every semantic mutant's frozen patch as a unified diff of its target, and its draft test, as raw files."""
    import difflib
    base=ROOT/"docs/_build/html/semantic-mutants"
    shutil.rmtree(base,ignore_errors=True)
    for contract_id,_target in semantic_selections().items():
        payload=SEMANTIC.load_proposals(contract_id)
        folder=base/contract_id
        folder.mkdir(parents=True,exist_ok=True)
        drafts=SEMANTIC.load_drafts(contract_id)
        for proposal in payload.get("proposals") or []:
            path,qualname=proposal["target"].split("::",1)
            original=SEMANTIC.function_source((ROOT/path).read_text(),qualname) or ""
            diff="".join(difflib.unified_diff(
              SEMANTIC._dedent(original).splitlines(keepends=True),
              SEMANTIC._dedent(proposal["replacement"]).splitlines(keepends=True),
              fromfile=f"a/{path}::{qualname}",tofile=f"b/{path}::{qualname} ({proposal['id']})",
            ))
            header=f"# {proposal['id']} · {proposal['class']} · {proposal['risk']}\n"
            (folder/f"{proposal['id']}.diff").write_text(header+(diff or "# the proposal repeats the current code\n"))
            if proposal["id"] in drafts:
                (folder/f"{proposal['id']}.test.py").write_text(drafts[proposal["id"]])
        results=SEMANTIC_RESULTS_DIR/f"{contract_id}.json"
        if results.exists():
            shutil.copy2(results,folder/"cascade.json")
        # The model answers the proposals and drafts were taken from, with the prompts they answered.
        responses=SEMANTIC.PROPOSAL_ROOT/contract_id/"responses"
        if responses.is_dir():
            (folder/"responses").mkdir(parents=True,exist_ok=True)
            for response in sorted(responses.glob("*.json")):
                shutil.copy2(response,folder/"responses"/response.name)


def install_mutation_testing_elements():
    """The pinned Mutation Testing Elements bundle that renders the mutation report."""
    if not MTE_VENDOR_PATH.exists():
        raise RuntimeError("pinned Mutation Testing Elements 3.9.0 asset is missing")
    mte_bytes=gzip.decompress(MTE_VENDOR_PATH.read_bytes())
    if hashlib.sha256(mte_bytes).hexdigest()!=MTE_VENDOR_SHA256:
        raise RuntimeError("pinned Mutation Testing Elements 3.9.0 asset digest mismatch")
    mte_target=ROOT/"docs/_build/html/_static/mutation-test-elements.js"
    mte_target.parent.mkdir(parents=True,exist_ok=True)
    mte_target.write_bytes(mte_bytes)


def integrate_mutation_portal():
    ensure_root_favicon()
    remove_retired_mutation_artifacts()
    install_mutation_testing_elements()
    write_mutation_report_page()
    write_semantic_mutant_files()
    patch_contract_evidence_view()
    subprocess.run(
      [sys.executable,str(ROOT/".ai-bridge/build-requirement-monitor.py")],
      cwd=ROOT,check=True,
    )
    subprocess.run(
      [sys.executable,str(ROOT/".ai-bridge/build-upper-assurance-pilot.py")],
      cwd=ROOT,check=True,
    )
    health_payload,_depth_payload=render_health_map_page()
    explorer=render_explorer_page(health_payload)
    patch_monitor_history(explorer)
    patch_traceability_contract_evidence_links()
    patch_verification_contract_evidence_path()
    patch_evidence_trust_need_anchors()
    patch_living_semantic_pages()
    patch_legacy_overview_links()
    patch_portal_navigation()


def refresh_portal():
    """Rebuild every fact and page from the retained runs, without running a test or a mutant."""
    depth_payload=refresh_verification_depth_facts()
    print(
      f"[PORTAL] depth facts: {len(depth_payload.get('tests') or [])} tests · "
      f"{len(depth_payload.get('contracts') or [])} contracts · "
      f"{(depth_payload.get('audit') or {}).get('nodeid_mismatches',0)} nodeid mismatches",
      flush=True,
    )
    regenerate_verification_maps()
    integrate_mutation_portal()


# --- the pull-request diff --------------------------------------------------------

IMPL_FAULT_DIFF_DIR=IMPL_FAULT_DIR/"diff"


def recorded_verdicts():
    """Per contract and mutant, the verdict each verdict record holds, as it counts (the person's
    first, a suppression only with its review), without re-asking the question: what a pull
    request knows, since its runner holds the records but not the judgement behind them."""
    result={}
    for folder in sorted(path for path in VERDICTS_DIR.iterdir() if path.is_dir()) if VERDICTS_DIR.is_dir() else []:
        decided=person_decisions(folder.name)
        for key,entry in load_verdicts(folder.name).items():
            person=decided.get(key) or {}
            verdict={**person,"by":"person"} if person.get("verdict") in EQ.VERDICTS_FINAL and person.get("reason") else reviewed_verdict(entry)
            if verdict:
                result.setdefault(folder.name,{})[key]={**verdict,"operator":entry.get("operator")}
    return result


def operator_priority(recorded=None):
    """The operators, most productive first: the share of an operator's recorded verdicts that ask
    for a pin, weighed against the prior order (Google's) as long as few verdicts are recorded.
    Google orders its operators by how useful their mutants were; here a verdict says so."""
    prior=list(MUTATION_EXTENSION.OPERATOR_PRIORITY)
    counts=defaultdict(Counter)
    for verdicts in (recorded if recorded is not None else recorded_verdicts()).values():
        for verdict in verdicts.values():
            if verdict.get("operator") in prior and verdict.get("verdict") in {"pin",*SUPPRESSING}:
                counts[verdict["operator"]]["pin" if verdict["verdict"]=="pin" else "no"]+=1
    weight=4

    def score(operator):
        index=prior.index(operator)
        expected=1-index/(2*len(prior))
        seen=counts[operator]
        return (seen["pin"]+weight*expected)/(seen["pin"]+seen["no"]+weight)
    return sorted(prior,key=lambda operator:(-score(operator),prior.index(operator)))


def diff_findings(contract_id,mutants,priority=None):
    """At most one surviving mutant per changed line, the most productive operator first:
    the review findings of a pull request (Google's one mutant per line)."""
    order={name:index for index,name in enumerate(priority or MUTATION_EXTENSION.OPERATOR_PRIORITY)}
    by_line=defaultdict(list)
    for mutant in mutants:
        if mutant["outcome"]=="survived":
            by_line[(mutant["source"],mutant["line"])].append(mutant)
    findings=[]
    for (source,line),rows in sorted(by_line.items()):
        chosen=min(rows,key=lambda row:(order.get(row["operator"],len(order)),row["id"]))
        findings.append({
          "contract_id":contract_id,"source":source,"line":line,"operator":chosen["operator"],
          "class":chosen["class"],"change":explorer_mutant_change(chosen),"fingerprint":chosen["fingerprint"],
          "survivors_on_line":len(rows),
        })
    return findings


def github_annotation(finding):
    """A GitHub Actions workflow command: the finding appears on the changed line of the pull request."""
    message=(
      f"{finding['contract_id']} · {finding['class']}: the contract's tests pass with this change: "
      f"{finding['change']}. Add or sharpen an assertion, or suppress it with a reason if it is equivalent."
    )
    escape=lambda value:str(value).replace("%","%25").replace("\r","%0D").replace("\n","%0A")
    return (
      f"::warning file={finding['source']},line={finding['line']},"
      f"title={escape('Surviving mutant ('+finding['operator']+')').replace(',','%2C').replace(':','%3A')}::{escape(message)}"
    )


def run_diff_campaign(base_ref="main",contract_ids=None):
    """The pull-request run: mutate only the attributable lines this branch changes against its merge
    base with base_ref, skip the mutants no test covers, and report surviving mutants per line."""
    changed,merge_base=working_changed_lines(base_ref)
    test_rows=junit_depth_rows()
    plans=implementation_fault_plans(test_rows)
    asking=contracts_asking_for_implementation_classes()
    shutil.rmtree(IMPL_FAULT_DIFF_DIR,ignore_errors=True)
    IMPL_FAULT_DIFF_DIR.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    contracts={}
    findings=[]
    judged_earlier=[]
    not_covered=[0]
    recorded=recorded_verdicts()
    priority=operator_priority(recorded)
    scopes={}
    for contract_id,plan in plans.items():
        if plan.get("blocked") or contract_id not in asking or (contract_ids and contract_id not in contract_ids):
            continue
        scope={
          path:[line for line in lines if (path,line) in changed]
          for path,lines in (plan.get("attributable_lines") or {}).items()
        }
        scope={path:lines for path,lines in scope.items() if lines}
        if scope:
            scopes[contract_id]=scope
    lock=threading.Lock()

    def mutate(contract_id,copy_root):
        plan,scope=plans[contract_id],scopes[contract_id]
        raw_path=IMPL_FAULT_DIFF_DIR/f"{contract_id}.gremlins.json"
        run=IMPL_FAULTS.run_engine_isolated(ROOT,copy_root,plan,raw_path,scope=scope,skip_uncovered=True)
        mutants=[]
        if run["report_retained"]:
            # A survivor a recorded verdict judged equivalent or irrelevant is no finding; it is listed apart.
            suppressions={key:verdict for key,verdict in (recorded.get(contract_id) or {}).items() if verdict.get("verdict") in SUPPRESSING}
            mutants=IMPL_FAULTS.suppress_by_verdict(IMPL_FAULTS.contract_mutants({**plan,"attributable_lines":scope},json.loads(raw_path.read_text()),ROOT),suppressions)
        found=diff_findings(contract_id,mutants,priority)
        earlier=[
          {"contract_id":contract_id,"source":mutant["source"],"line":mutant["line"],"class":mutant["class"],"change":explorer_mutant_change(mutant),
           "verdict":mutant["suppression"]["verdict"],"by":mutant["suppression"].get("by"),"reviewed_by":mutant["suppression"].get("reviewed_by"),
           "reason":" ".join(str(mutant["suppression"].get("reason") or "").split())}
          for mutant in mutants if (mutant.get("suppression") or {}).get("verdict")
        ]
        with lock:
            not_covered[0]+=sum(mutant["outcome"]=="notreached" for mutant in mutants)
            findings.extend(found)
            judged_earlier.extend(earlier)
            contracts[contract_id]={
              "changed_lines":scope,
              "returncode":run["returncode"],
              "duration_seconds":run["duration_seconds"],
              "report_path":str(raw_path.relative_to(ROOT)) if run["report_retained"] else None,
              "mutants":{outcome:sum(mutant["outcome"]==outcome for mutant in mutants) for outcome in IMPL_FAULTS.OUTCOMES},
              "findings":len(found),
            }
            print(f"[DIFF] {contract_id}: {len(mutants)} mutants on {sum(len(lines) for lines in scope.values())} changed lines, {len(found)} findings",flush=True)

    for_each_in_copies(sorted(scopes),mutate)
    findings.sort(key=lambda finding:(finding["source"],finding["line"],finding["contract_id"]))
    judged_earlier.sort(key=lambda item:(item["source"],item["line"],item["contract_id"]))
    summary={
      "schema":"ternforge-mutation-diff-1",
      "base":base_ref,
      "merge_base":merge_base,
      "head_sha":git_sha(),
      "created_at":utc_now(),
      "changed_source_lines":len(changed),
      "duration_seconds":round(time.monotonic()-started,1),
      "rule":"changed, attributable and covered lines; at most one surviving mutant per line, the most productive operator first by the recorded verdicts; a survivor a recorded verdict judged equivalent or irrelevant is listed apart; mutants no test covers are not run",
      "operator_priority":priority,
      "contracts":contracts,
      "findings":findings,
      "judged_earlier":judged_earlier,
      "not_covered_mutants":not_covered[0],
    }
    (IMPL_FAULT_DIFF_DIR/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    (IMPL_FAULT_DIFF_DIR/"annotations.txt").write_text("".join(github_annotation(finding)+"\n" for finding in findings))
    lines=[
      f"### Mutation findings on this change ({base_ref} … {git_sha()[:12]})","",
      f"{len(findings)} surviving mutants on {len({(f['source'],f['line']) for f in findings})} changed lines "
      f"of {len(contracts)} contracts; {not_covered[0]} mutants on changed lines no test covers were not run.","",
    ]
    lines.extend(f"- `{f['source']}:{f['line']}` · {f['contract_id']} · {f['class']}: {f['change']}" for f in findings)
    if judged_earlier:
        lines.extend(["",f"{len(judged_earlier)} surviving mutants on changed lines were judged before and are no findings:",""])
        lines.extend(
          f"- `{item['source']}:{item['line']}` · {item['contract_id']} · {item['class']}: {item['change']} — {item['verdict']} by {item['by']}"
          +(f", confirmed by {item['reviewed_by']}" if item.get("reviewed_by") else "")+f": {explorer_clip(item['reason'],200)}"
          for item in judged_earlier
        )
    (IMPL_FAULT_DIFF_DIR/"summary.md").write_text("\n".join(lines)+"\n")
    print(f"[DIFF] {len(findings)} findings on {len(changed)} changed source lines in {summary['duration_seconds']}s",flush=True)
    return summary


def parse_args():
    parser=argparse.ArgumentParser(description="llm-router assurance portal: facts, monitors and the mutation campaign")
    parser.add_argument("--refresh-freshness",action="store_true",help="rebuild every fact and page from the retained runs (the default)")
    parser.add_argument("--refresh-assurance",action="store_true",help="rerun the specialized fault probes of REQ_INVALID_CONFIGURATION_ERRORS, then rebuild the pages")
    parser.add_argument("--refresh-implementation-faults",action="store_true",help="run the implementation fault campaign for every contract whose retained result is no longer current")
    parser.add_argument("--contracts",nargs="*",help="limit the campaign to these contracts")
    parser.add_argument("--full",action="store_true",help="with --refresh-implementation-faults: re-run every contract, not only stale ones")
    parser.add_argument("--diff",nargs="?",const="main",metavar="BASE",help="with --refresh-implementation-faults: the pull-request run over the lines this branch changes against BASE (default main)")
    parser.add_argument("--refresh-semantic-mutants",action="store_true",help="run the semantic mutant cascade for every contract whose profile selects semantic mutants")
    parser.add_argument("--generate-semantic-mutants",action="store_true",help="call the model (ADR_0004) for every selected target without a current semantic mutant, judge them, draft tests for the distinguished ones, then rebuild the pages")
    parser.add_argument("--force",action="store_true",help="with --generate-semantic-mutants: regenerate every selected target, not only those without a current proposal")
    parser.add_argument("--calibrate-assessors",action="store_true",help="ask every survivor assessor about the labelled calibration pairs it has not answered, then recompute the threshold (ADR_0005)")
    parser.add_argument("--assess-survivors",action="store_true",help="judge the surviving rule mutants: symbolic search, then the assessors within the budget; outcomes never change")
    parser.add_argument("--run-canaries",action="store_true",help="ask every model the Test Plan lists for a role its canaries and record whether it passed (ADR_0006); a change of model calls for it")
    parser.add_argument("--roles",nargs="*",help="with --run-canaries: only these roles (generator, draft_author, verdict)")
    parser.add_argument("--decide-survivors",action="store_true",help="ask the verdict model about every judged survivor and adopt a mutation pin for every pin verdict (ADR_0006)")
    parser.add_argument("--revise-pins",action="store_true",help="remove the mutation pins that verify an older revision of their requirement than the docs declare, with their records, and rebuild the calibration from stored answers; asks no model (ADR_0006)")
    parser.add_argument("--refresh-pins",action="store_true",help="bring every mutation pin to the current pin rules: normalized, lint-clean and judged again; the draft author retries with the reason (ADR_0006)")
    return parser.parse_args()


def portal_left_for_refresh():
    """A stage records its results and leaves the portal alone: rebuilding it costs minutes, so it
    is rebuilt once, by the plain run after the stages, as PIT and Stryker write one report a run."""
    print("[PORTAL] not refreshed by this stage: run the builder without arguments once the stages are done",flush=True)


def main():
    args=parse_args()
    if args.calibrate_assessors:
        calibrate_assessors()
        return
    if args.run_canaries:
        run_canaries(set(args.roles or []) or None)
        return
    if args.decide_survivors:
        decide_survivors(set(args.contracts or []) or None)
        portal_left_for_refresh()
        return
    if args.revise_pins:
        revise_pins()
        return
    if args.refresh_pins:
        refresh_pins(set(args.contracts or []) or None)
        portal_left_for_refresh()
        return
    if args.assess_survivors:
        assess_survivors(set(args.contracts or []) or None)
        portal_left_for_refresh()
        return
    if args.generate_semantic_mutants:
        generate_semantic_mutants(set(args.contracts or []) or None,force=args.force)
        portal_left_for_refresh()
        return
    if args.refresh_semantic_mutants:
        refresh_semantic_mutants(set(args.contracts or []) or None)
        return
    if args.refresh_implementation_faults:
        IMPL_FAULT_DIR.mkdir(parents=True,exist_ok=True)
        contracts=set(args.contracts or []) or None
        if args.diff:
            run_diff_campaign(args.diff,contracts)
        else:
            refresh_implementation_fault_campaign(contracts,full=args.full)
        return
    if args.refresh_assurance:
        facts=build_fault_model_facts()
        layers=((facts.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}).get("layers") or {}
        print(f"[PROBES] REQ_INVALID_CONFIGURATION_ERRORS: {sum(bool(row.get('detected')) for row in layers.values())}/{len(layers)} specialized probes caught their fault",flush=True)
    refresh_portal()


if __name__=="__main__":
    main()
