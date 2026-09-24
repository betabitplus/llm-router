from __future__ import annotations

import argparse
import ast
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
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from html import escape as html_escape
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

from coverage import CoverageData

ROOT=Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
OUT=ROOT/"docs/_build/html/mutation-results"
DEPTH_FACTS_PATH=ROOT/"docs/_build/html/verification-depth-facts.json"
DEPTH: dict[str, Any]=json.loads(DEPTH_FACTS_PATH.read_text())
STRENGTH_PATH=ROOT/"docs/_build/html/verification-test-strength-facts.json"
STRENGTH: dict[str, Any]={}
TEST_META: dict[str, dict[str, Any]]={r["nodeid"]:r for r in DEPTH["tests"]}
COVERAGE_DB=ROOT/"test-results/.coverage"
COVERAGE_JSON_PATH=ROOT/"test-results/coverage.json"
JUNIT_PATH=ROOT/"test-results/pytest-junit.xml"
ALLURE_RESULTS_DIR=ROOT/"test-results/allure-results"
EVIDENCE_RUN_PROVENANCE_PATH=ROOT/"docs/_build/html/evidence-run-provenance.json"
EVIDENCE_RUN_INPUTS_PATH=ROOT/"test-results/evidence-run-inputs.json"
EVIDENCE_QUALIFICATION_PATH=ROOT/"docs/_build/html/evidence-confidence-qualification.json"
CAMPAIGN_PATH=OUT/"campaign.json"
SUMMARY_PATH=OUT/"summary.json"
TRIAGE_PATH=OUT/"triage.json"
OPERATOR_FEEDBACK_PATH=OUT/"operator-feedback.json"
HISTORY_DIR=OUT/"campaign-history"
ASSURANCE_FACTS_PATH=ROOT/"docs/_build/html/assurance-fault-model-facts.json"
ASSURANCE_HISTORY_DIR=ROOT/"docs/_build/html/assurance-history"
ASSURANCE_TARGETS_PATH=ROOT/".ai-bridge/assurance-targets.json"
ASSURANCE_SNAPSHOTS_PATH=ROOT/".ai-bridge/assurance-snapshots.json"
DEPTH_PAGE=ROOT/"docs/_build/html/verification-depth-map.html"
HEALTH_PAGE=ROOT/"docs/_build/html/verification-health-map.html"
REQ_MONITOR_FACTS_PATH=ROOT/"docs/_build/html/requirement-monitor-facts.json"
UPPER_ASSURANCE_FACTS_PATH=ROOT/"docs/_build/html/upper-assurance-facts.json"
EVIDENCE_CLASSIFICATION_PATH=ROOT/"docs/_build/html/evidence-classification-facts.json"
ALLURE_REPORT_PAGE=ROOT/"docs/_build/html/test-results/index.html"
MUTATION_PAGE=ROOT/"docs/_build/html/mutation-analysis.html"
ASSURANCE_PAGE=ROOT/"docs/_build/html/verification-assurance.html"
SUPPRESSIONS_PATH=ROOT/".ai-bridge/mutation-suppressions.json"
MUTATION_SEMANTICS_VERSION="p21-local-2"
MUTATION_ADAPTER_VERSION="p34-local-2"
PROTOTYPE_BUILD_VERSION="p34-local-1"
MUTMUT_VERSION="3.8.0"
MTE_VENDOR_PATH=ROOT/".ai-bridge/vendor/mutation-testing-elements-3.9.0/mutation-test-elements.js.gz"
MTE_VENDOR_SHA256="751fb010242b0b44e32d84fe7fe0b9ff1da182823b94f59f5c52b001fcfc163b"
D3_HIERARCHY_VENDOR_PATH=ROOT/".ai-bridge/vendor/d3-hierarchy-3.1.2/d3-hierarchy.min.js"
D3_HIERARCHY_VENDOR_SHA256="a8771380454be89ec5ffe9a6396ba7c247081e348ae740dc9cb9629abd4c0e43"
MUTATION_CONFIG={
  "process_isolation":"forkserver",
  "forkserver_warmup":"collect",
  "mutate_only_covered_lines":True,
  "max_children":4,
  "thresholds":{"low":60,"high":80},
}

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
# __APPEND__
CONTRACTS={
"REQ_INVALID_CONFIGURATION_ERRORS":{"source":"src/llm_router/_internal/config/validation.py","kind":"function","scope":"validate_config","tests":[
"tests/llm_router/bdd/responses/test_public_contract.py::test_invalid_model_configuration_surfaces_as_a_configuration_error",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_invalid_retry_wait_bounds[min-wait-non-positive]",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_invalid_retry_wait_bounds[max-wait-below-min]",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_undeclared_default_provider",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_provider_spec_key_mismatch",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_model_without_provider_mapping",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_model_mapping_to_undeclared_provider",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_zero_structured_output_attempts",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_missing_required_base_url",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_default_model_without_default_provider_mapping",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_invalid_retry_policy",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_invalid_policy_timeout",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_zero_fallback_shuffle_minimum",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_undeclared_default_model",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_zero_route_attempt_limit",
"tests/llm_router/unit/test_internal_config_validation.py::test_validation_rejects_zero_default_tool_rounds"]},
"TREQ_TOOL_REGISTRY":{"source":"src/llm_router/_internal/capabilities/tools.py","kind":"class","scope":"ToolRegistry","tests":[
"tests/llm_router/unit/test_internal_tool_registry.py::test_callable_tool_schema_and_execution_match_python_signature",
"tests/llm_router/unit/test_internal_tool_registry.py::test_duplicate_tool_names_are_rejected",
"tests/llm_router/unit/test_internal_tool_registry.py::test_tool_call_parser_accepts_supported_provider_shapes[openai-function]",
"tests/llm_router/unit/test_internal_tool_registry.py::test_tool_call_parser_accepts_supported_provider_shapes[google-function]"]}}
SHARED_SCOPE_DIAGNOSTICS={
  "TREQ_RATE_LIMIT_STATE":{
    "shared_with":["TREQ_RATE_LIMIT_COOLDOWN_POLICY"],
    "reason":(
      "LimiterState now implements sibling contracts TREQ_RATE_LIMIT_STATE and "
      "TREQ_RATE_LIMIT_COOLDOWN_POLICY; a class-wide mutation result cannot be "
      "uniquely attributed to either contract."
    ),
  },
}
UNATTRIBUTED_SCOPE_DIAGNOSTICS=[
  {
    "contract_id":"REQ_ROUTE_ATTEMPT_LIMIT",
    "source_path":"src/llm_router/_internal/runtime/routes.py",
    "scope":"ordered_routes",
    "score":85.7,
    "fresh":False,
    "stale_reasons":["shared_scope_not_uniquely_attributable"],
    "shared_with":["TREQ_ROUTE_ORDER"],
    "reason":(
      "ordered_routes implements both REQ_ROUTE_ATTEMPT_LIMIT and TREQ_ROUTE_ORDER; "
      "the retained mutation result is diagnostic only and cannot be uniquely attributed."
    ),
  },
  {
    "contract_id":"REQ_CONFIG_INSTALLATION_COHERENCE",
    "source_path":"src/llm_router/_internal/config/state.py",
    "scope":"install_config",
    "score":17.4,
    "fresh":False,
    "stale_reasons":["shared_scope_not_uniquely_attributable"],
    "shared_with":["TREQ_CONFIG_CACHE_INVALIDATION"],
    "reason":(
      "install_config shares implementation ownership with TREQ_CONFIG_CACHE_INVALIDATION "
      "and includes unrelated logging mutations; the retained result is diagnostic only."
    ),
  },
]
def installed_mutmut_version():
    try:
        return package_version("mutmut")
    except PackageNotFoundError:
        return None


def mutation_engine_version():
    return installed_mutmut_version() or MUTMUT_VERSION


def bootstrap_strength_state():
    return {
      "schema_version":"verification-test-strength-spike-5",
      "engine":{
        "name":"mutmut",
        "version":mutation_engine_version(),
        "thresholds":MUTATION_CONFIG["thresholds"],
      },
      "contracts":{
        contract_id:{
          "contract_id":contract_id,
          "source_path":spec["source"],
          "scope_kind":spec["kind"],
          "scope":spec["scope"],
          "linked_test_count":len(spec["tests"]),
          "score":None,
          "state":"na",
          "killed":0,
          "survived":0,
          "valid_mutants":0,
          "fresh":False,
          "stale_reasons":["not_measured"],
          "report_url":None,
          "allure_url":f"test-results/index.html?tags=TF_SCOPE__{contract_id}",
        }
        for contract_id,spec in CONTRACTS.items()
      },
      "unattributed":[dict(row) for row in UNATTRIBUTED_SCOPE_DIAGNOSTICS],
    }

STRENGTH=(
  json.loads(STRENGTH_PATH.read_text())
  if STRENGTH_PATH.exists()
  else bootstrap_strength_state()
)
STATUS={"killed":"Killed","survived":"Survived","timeout":"Timeout","suspicious":"RuntimeError","skipped":"Ignored","untested":"NoCoverage","no tests":"NoCoverage"}

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

def scope_source(spec):
    path=ROOT/spec["source"]
    text=path.read_text()
    tree=ast.parse(text)
    if spec["kind"]=="class":
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==spec["scope"])
    else:
        node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["scope"])
    lines=text.splitlines(keepends=True)
    start=min([node.lineno,*[d.lineno for d in getattr(node,"decorator_list",[])]])-1
    end=getattr(node,"end_lineno",node.lineno)
    return "".join(lines[start:end])

def requirement_derives_map():
    result={}
    pattern=re.compile(r"```\{(?:req|treq)\}.*?\n```",flags=re.DOTALL)
    for path in sorted((ROOT/"docs/requirements").glob("*.md")):
        for block in pattern.findall(path.read_text()):
            contract_match=re.search(r"^:id:\s*(T?REQ_[A-Z0-9_]+)\s*$",block,flags=re.MULTILINE)
            derives_match=re.search(r"^:derives:\s*([^\n]+)$",block,flags=re.MULTILINE)
            if not contract_match:
                continue
            contract_id=contract_match.group(1)
            parents=(
              re.findall(r"T?REQ_[A-Z0-9_]+",derives_match.group(1))
              if derives_match else []
            )
            result[contract_id]=parents
    return result


def contract_derives_from(contract_id,ancestor_id,derives):
    pending=[contract_id]
    seen=set()
    while pending:
        current=pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for parent in derives.get(current) or []:
            if parent==ancestor_id:
                return True
            pending.append(parent)
    return False


def scope_impl_owners(spec):
    path=ROOT/spec["source"]
    text=path.read_text()
    tree=ast.parse(text)
    if spec["kind"]=="class":
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==spec["scope"])
    else:
        node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["scope"])
    lines=text.splitlines()
    start=node.lineno-1
    while start>0 and lines[start-1].lstrip().startswith("# @impl"):
        start-=1
    end=getattr(node,"end_lineno",node.lineno)
    scope_text="\n".join(lines[start:end])
    return sorted(set(re.findall(r"\[(T?REQ_[A-Z0-9_]+)\[revision==\d+\]\]",scope_text)))


def validate_contract_scope_attribution():
    derives=requirement_derives_map()
    errors=[]
    for contract_id,spec in CONTRACTS.items():
        owners=scope_impl_owners(spec)
        invalid=[
          owner for owner in owners
          if owner!=contract_id and not contract_derives_from(owner,contract_id,derives)
        ]
        if contract_id not in owners or invalid:
            errors.append(
              f"{contract_id}: scope {spec['kind']} {spec['scope']} owners={owners}; "
              f"outside attribution root={invalid}"
            )
    if errors:
        raise RuntimeError(
          "mutation contract scope is not uniquely attributable:\n"
          +"\n".join(errors)
        )


def deattribute_shared_scope_strength():
    unattributed=[
      row for row in (STRENGTH.get("unattributed") or [])
      if row.get("contract_id") not in SHARED_SCOPE_DIAGNOSTICS
    ]
    contracts=STRENGTH.setdefault("contracts",{})
    for contract_id,diagnostic in SHARED_SCOPE_DIAGNOSTICS.items():
        fact=contracts.pop(contract_id,None)
        if not fact:
            continue
        unattributed.append({
          "contract_id":contract_id,
          "source_path":fact.get("source_path"),
          "scope":fact.get("scope"),
          "score":fact.get("score"),
          "killed":int(fact.get("killed") or 0),
          "survived":int(fact.get("survived") or 0),
          "fresh":False,
          "stale_reasons":["shared_scope_not_uniquely_attributable"],
          "shared_with":list(diagnostic.get("shared_with") or []),
          "reason":diagnostic["reason"],
        })
    STRENGTH["unattributed"]=unattributed


def test_source(nodeid):
    file_name,test_name=nodeid.split("::",1)
    fn_name=test_name.split("[",1)[0]
    path=ROOT/file_name
    text=path.read_text()
    try:
        tree=ast.parse(text)
        node=next(
          n for n in ast.walk(tree)
          if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==fn_name
        )
    except (SyntaxError,StopIteration):
        return text
    lines=text.splitlines(keepends=True)
    start=min([node.lineno,*[d.lineno for d in getattr(node,"decorator_list",[])]])-1
    end=getattr(node,"end_lineno",node.lineno)
    return "".join(lines[start:end])

def scope_source_from_text(spec,text):
    try:
        tree=ast.parse(text)
        if spec["kind"]=="class":
            node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==spec["scope"])
        else:
            node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["scope"])
    except (SyntaxError,StopIteration):
        return None
    lines=text.splitlines(keepends=True)
    start=min([node.lineno,*[d.lineno for d in getattr(node,"decorator_list",[])]])-1
    end=getattr(node,"end_lineno",node.lineno)
    return "".join(lines[start:end])

def test_source_from_text(nodeid,text):
    fn_name=nodeid.split("::",1)[1].split("[",1)[0]
    try:
        tree=ast.parse(text)
        node=next(
          n for n in ast.walk(tree)
          if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==fn_name
        )
    except (SyntaxError,StopIteration):
        return text
    lines=text.splitlines(keepends=True)
    start=min([node.lineno,*[d.lineno for d in getattr(node,"decorator_list",[])]])-1
    end=getattr(node,"end_lineno",node.lineno)
    return "".join(lines[start:end])

def git_show_text(ref,path):
    result=subprocess.run(
      ["git","show",f"{ref}:{path}"],cwd=ROOT,text=True,
      stdout=subprocess.PIPE,stderr=subprocess.DEVNULL
    )
    return result.stdout if result.returncode==0 else None

def changed_line_numbers(base_ref,path):
    result=subprocess.run(
      ["git","diff","--unified=0",base_ref,"--",path],cwd=ROOT,text=True,
      stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True
    )
    lines=set()
    for row in result.stdout.splitlines():
        if not row.startswith("@@"):
            continue
        match=re.search(r"\+(\d+)(?:,(\d+))?",row)
        if not match:
            continue
        start=int(match.group(1))
        count=int(match.group(2) or "1")
        lines.update(range(start,start+max(count,1)))
    return sorted(lines)

def resolve_diff_scope(base_ref):
    selection={}
    for contract_id,spec in CONTRACTS.items():
        current_impl=scope_source(spec)
        base_source=git_show_text(base_ref,spec["source"])
        base_impl=scope_source_from_text(spec,base_source) if base_source is not None else None
        implementation_changed=base_impl!=current_impl
        changed_tests=[]
        for nodeid in spec["tests"]:
            file_name=nodeid.split("::",1)[0]
            base_test_file=git_show_text(base_ref,file_name)
            base_test=test_source_from_text(nodeid,base_test_file) if base_test_file is not None else None
            if base_test!=test_source(nodeid):
                changed_tests.append(nodeid)
        reasons=[]
        if implementation_changed:
            reasons.append("implementation_scope_changed")
        if changed_tests:
            reasons.append("linked_test_changed")
        selection[contract_id]={
          "selected":bool(reasons),
          "reasons":reasons,
          "changed_source_lines":changed_line_numbers(base_ref,spec["source"]) if implementation_changed else [],
          "changed_linked_tests":changed_tests,
        }
    return selection

def contract_fingerprints(contract_id,spec,mutmut_version=None):
    mutmut_version=mutmut_version or mutation_engine_version()
    source_fp=sha256_text(scope_source(spec))
    tests_payload=[{"nodeid":nodeid,"source":test_source(nodeid)} for nodeid in spec["tests"]]
    tests_fp=sha256_text(stable_json(tests_payload))
    config_payload={
      "contract_id":contract_id,
      "source":spec["source"],
      "kind":spec["kind"],
      "scope":spec["scope"],
      "tests":spec["tests"],
      "mutation_config":MUTATION_CONFIG,
      "mutation_semantics_version":MUTATION_SEMANTICS_VERSION,
      "mutmut_version":mutmut_version,
    }
    config_fp=sha256_text(stable_json(config_payload))
    combined=sha256_text(stable_json({
      "source":source_fp,
      "tests":tests_fp,
      "config":config_fp,
    }))
    return {
      "source_fingerprint":source_fp,
      "test_set_fingerprint":tests_fp,
      "config_fingerprint":config_fp,
      "combined_fingerprint":combined,
    }

def relevant_allure_run_fingerprint():
    wanted={nodeid for spec in CONTRACTS.values() for nodeid in spec["tests"]}
    keys={(nodeid.split("::",1)[0].removesuffix(".py").replace("/","."),nodeid.split("::",1)[1].split("[",1)[0]) for nodeid in wanted}
    rows=[]
    for path in sorted((ROOT/"test-results/allure-results").glob("*-result.json")):
        try:
            row=json.loads(path.read_text())
        except Exception:
            continue
        if (str(row.get("fullName") or "").split("#",1)[0],str(row.get("name") or "").split("[",1)[0]) in keys:
            rows.append(row)
    return sha256_text(stable_json(rows))

def build_campaign_inputs(mode,base_ref,contract_ids=None,mutmut_version=None):
    ids=list(CONTRACTS.keys()) if contract_ids is None else list(contract_ids)
    mutmut_version=mutmut_version or mutation_engine_version()
    contracts={cid:contract_fingerprints(cid,CONTRACTS[cid],mutmut_version) for cid in ids}
    head=git_sha()
    base=git_sha(base_ref) if base_ref else None
    identity_payload={
      "mode":mode,
      "head_sha":head,
      "base_sha":base,
      "contracts":contracts,
      "adapter_version":MUTATION_ADAPTER_VERSION,
      "adapter_sha256":sha256_file(ROOT/".ai-bridge/build-mutation-report-prototype.py"),
      "mutation_semantics_version":MUTATION_SEMANTICS_VERSION,
      "mutmut_version":mutmut_version,
      "mutation_config":MUTATION_CONFIG,
    }
    campaign_id=f"{mode}-{head[:12]}-{sha256_text(stable_json(identity_payload))[:12]}"
    return {
      "campaign_id":campaign_id,
      "mode":mode,
      "head_sha":head,
      "base_sha":base,
      "contracts":contracts,
      "coverage_run_fingerprint":sha256_file(COVERAGE_DB),
      "allure_run_fingerprint":relevant_allure_run_fingerprint(),
      "mutation_config_fingerprint":sha256_text(stable_json(MUTATION_CONFIG)),
    }

def archive_previous_run(new_run_id):
    if not CAMPAIGN_PATH.exists():
        return None
    previous=json.loads(CAMPAIGN_PATH.read_text())
    previous_run_id=str(previous.get("run_id") or previous.get("campaign_id") or "")
    if not previous_run_id or previous_run_id==new_run_id:
        return previous.get("baseline_run_id") or previous.get("baseline_campaign_id")
    HISTORY_DIR.mkdir(parents=True,exist_ok=True)
    (HISTORY_DIR/f"{previous_run_id}.json").write_text(json.dumps(previous,indent=2))
    for fact in STRENGTH.get("contracts",{}).values():
        if (fact.get("run_id") or fact.get("campaign_id"))==previous_run_id:
            fact["campaign_provenance_url"]=f"../campaign-history/{previous_run_id}.json"
    return previous_run_id

def mutant_symbol(engine_id):
    return re.sub(r"__mutmut_\d+$","",str(engine_id))

def stable_mutant_fingerprint(contract_id,spec,mutant):
    payload={
      "contract_id":contract_id,
      "source_path":spec["source"],
      "scope_kind":spec["kind"],
      "scope":spec["scope"],
      "symbol":mutant_symbol(mutant["id"]),
      "description":mutant.get("description") or "",
      "replacement":mutant.get("replacement") or "",
    }
    return sha256_text(stable_json(payload))

def mutant_record(contract_id,spec,mutant):
    return {
      "fingerprint":stable_mutant_fingerprint(contract_id,spec,mutant),
      "engine_id":mutant["id"],
      "symbol":mutant_symbol(mutant["id"]),
      "status":mutant["status"],
      "source_path":spec["source"],
      "line":int(mutant["location"]["start"]["line"]),
      "description":mutant.get("description") or "",
      "replacement":mutant.get("replacement") or "",
      "covered_by":list(mutant.get("coveredBy") or []),
    }

def empty_suppressions():
    return {"schema_version":"ternforge-mutation-suppressions-prototype-1","suppressions":[]}

def load_suppressions():
    if not SUPPRESSIONS_PATH.exists():
        return empty_suppressions()
    payload=json.loads(SUPPRESSIONS_PATH.read_text())
    rows=list(payload.get("suppressions") or [])
    seen=set()
    for row in rows:
        key=(str(row.get("contract_id") or ""),str(row.get("mutant_fingerprint") or ""))
        if not all(key) or key in seen:
            raise ValueError(f"invalid/duplicate mutation suppression: {key}")
        seen.add(key)
        if not str(row.get("reason") or "").strip():
            raise ValueError(f"mutation suppression requires reason: {key}")
    return {"schema_version":"ternforge-mutation-suppressions-prototype-1","suppressions":rows}

def save_suppressions(payload):
    SUPPRESSIONS_PATH.parent.mkdir(parents=True,exist_ok=True)
    SUPPRESSIONS_PATH.write_text(json.dumps(payload,indent=2))

def suppression_active(row):
    expires=str(row.get("expires_at") or "").strip()
    if not expires:
        return True
    try:
        expiry=datetime.fromisoformat(expires.replace("Z","+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        expiry=expiry.replace(tzinfo=UTC)
    return expiry>datetime.now(UTC)

def suppression_map(contract_id):
    return {
      str(row["mutant_fingerprint"]):row
      for row in load_suppressions()["suppressions"]
      if str(row.get("contract_id"))==contract_id and suppression_active(row)
    }

def load_run(run_id):
    if not run_id:
        return None
    if CAMPAIGN_PATH.exists():
        current=json.loads(CAMPAIGN_PATH.read_text())
        if run_id in {current.get("run_id"),current.get("campaign_id")}:
            return current
    path=HISTORY_DIR/f"{run_id}.json"
    return json.loads(path.read_text()) if path.exists() else None

def triage_contract(campaign,contract_id):
    current_result=campaign["contracts"][contract_id].get("result") or {}
    current_records=list(current_result.get("mutants") or [])
    current_survivors={r["fingerprint"]:r for r in current_records if r.get("status")=="Survived"}

    baseline_run_id=(
      campaign["contracts"][contract_id].get("baseline_run_id")
      or campaign["contracts"][contract_id].get("baseline_campaign_id")
      or campaign.get("baseline_run_id")
      or campaign.get("baseline_campaign_id")
    )
    baseline=load_run(baseline_run_id)
    baseline_contract=(baseline or {}).get("contracts",{}).get(contract_id,{})
    baseline_result=baseline_contract.get("result") or {}
    baseline_records=list(baseline_result.get("mutants") or [])
    baseline_available=bool(baseline_records)
    baseline_survivors={r["fingerprint"]:r for r in baseline_records if r.get("status")=="Survived"}

    current_ids=set(current_survivors)
    baseline_ids=set(baseline_survivors)
    new_ids=current_ids-baseline_ids if baseline_available else set()
    existing_ids=current_ids&baseline_ids if baseline_available else set()
    resolved_ids=baseline_ids-current_ids if baseline_available else set()
    unclassified_ids=current_ids if not baseline_available else set()

    suppressions=suppression_map(contract_id)
    suppressed_ids={fingerprint for fingerprint in current_ids if fingerprint in suppressions}
    new_unresolved_ids=new_ids-suppressed_ids
    unresolved_ids=current_ids-suppressed_ids

    baseline_score=baseline_result.get("score")
    current_score=current_result.get("score")
    baseline_adapter=(baseline or {}).get("adapter") or {}
    current_adapter=campaign.get("adapter") or {}
    baseline_engine=(baseline or {}).get("engine") or {}
    current_engine=campaign.get("engine") or {}
    comparable=bool(
      baseline_available
      and baseline_contract.get("source_path")==campaign["contracts"][contract_id].get("source_path")
      and baseline_contract.get("scope_kind")==campaign["contracts"][contract_id].get("scope_kind")
      and baseline_contract.get("scope")==campaign["contracts"][contract_id].get("scope")
      and baseline_engine.get("name")==current_engine.get("name")
      and baseline_engine.get("version")==current_engine.get("version")
      and baseline.get("mutation_config")==campaign.get("mutation_config")
      and baseline_adapter.get("mutation_semantics_version")
          ==current_adapter.get("mutation_semantics_version")
      and baseline_score is not None and current_score is not None
    )
    score_delta=round(float(current_score)-float(baseline_score),1) if comparable else None

    current_rows=[]
    for fingerprint,row in current_survivors.items():
        if fingerprint in suppressed_ids:
            classification="suppressed"
        elif fingerprint in new_ids:
            classification="new"
        elif fingerprint in existing_ids:
            classification="existing"
        else:
            classification="unclassified"
        item={**row,"classification":classification}
        if fingerprint in suppressions:
            suppression=suppressions[fingerprint]
            item["suppression"]={
              "reason":suppression.get("reason"),
              "owner":suppression.get("owner"),
              "expires_at":suppression.get("expires_at"),
            }
        current_rows.append(item)

    resolved_rows=[
      {**baseline_survivors[fingerprint],"classification":"resolved"}
      for fingerprint in sorted(resolved_ids)
    ]
    return {
      "baseline_available":baseline_available,
      "baseline_run_id":baseline_run_id,
      "baseline_campaign_id":(baseline or {}).get("campaign_id"),
      "baseline_comparable":comparable,
      "baseline_score":baseline_score if baseline_available else None,
      "score_delta":score_delta,
      "current_survivors":len(current_ids),
      "new_survivors":len(new_ids),
      "existing_survivors":len(existing_ids),
      "resolved_survivors":len(resolved_ids),
      "unclassified_survivors":len(unclassified_ids),
      "suppressed_survivors":len(suppressed_ids),
      "new_unresolved_survivors":len(new_unresolved_ids),
      "unresolved_survivors":len(unresolved_ids),
      "readiness":"attention" if new_unresolved_ids else ("clear" if baseline_available else "baseline_unavailable"),
      "survivors":sorted(current_rows,key=lambda row:(row["classification"],row["fingerprint"])),
      "resolved":resolved_rows,
    }

def apply_triage(campaign):
    selected=list(campaign.get("contracts") or {})
    for contract_id in selected:
        triage=triage_contract(campaign,contract_id)
        campaign["contracts"][contract_id]["result"]["triage"]=triage
        STRENGTH["contracts"][contract_id]["triage"]=triage
    return selected

def upsert_suppression(contract_id,fingerprint,reason,owner=None,expires_at=None):
    reason=str(reason or "").strip()
    if not reason:
        raise ValueError("suppression reason is required")
    payload=load_suppressions()
    rows=payload["suppressions"]
    key=(contract_id,fingerprint)
    rows[:]=[
      row for row in rows
      if (str(row.get("contract_id")),str(row.get("mutant_fingerprint")))!=key
    ]
    rows.append({
      "contract_id":contract_id,
      "mutant_fingerprint":fingerprint,
      "reason":reason,
      "owner":owner or None,
      "expires_at":expires_at or None,
      "created_at":utc_now(),
    })
    save_suppressions(payload)

def remove_suppression(contract_id,fingerprint):
    payload=load_suppressions()
    before=len(payload["suppressions"])
    payload["suppressions"]=[
      row for row in payload["suppressions"]
      if not (
        str(row.get("contract_id"))==contract_id
        and str(row.get("mutant_fingerprint"))==fingerprint
      )
    ]
    if len(payload["suppressions"])!=before:
        save_suppressions(payload)
    return before-len(payload["suppressions"])

def validate_linked_test_nodeids():
    errors=[]
    for contract_id,spec in CONTRACTS.items():
        files=sorted({str(nodeid).split("::",1)[0] for nodeid in spec["tests"]})
        completed=subprocess.run(
          [
            sys.executable,"-m","pytest",
            "--collect-only","-q","--no-cov",
            "-p","no:randomly","-p","no:random-order",
            *files,
          ],
          cwd=ROOT,
          env=probe_env(),
          text=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
        )
        if completed.returncode!=0:
            tail=(completed.stdout or "")[-8000:]
            errors.append(
              f"{contract_id}: linked-test collection failed:\n{tail}"
            )
            continue
        # pytest -q collection output is one exact nodeid per line; ignore
        # coverage/plugin prose by requiring the declared test-file prefix.
        collected={
          line.strip()
          for line in (completed.stdout or "").splitlines()
          if any(line.strip().startswith(file_name+"::") for file_name in files)
        }
        missing=[nodeid for nodeid in spec["tests"] if nodeid not in collected]
        if missing:
            errors.append(
              f"{contract_id}: linked mutation nodeids are not in current pytest collection: "
              +", ".join(missing)
            )
    if errors:
        raise RuntimeError(
          "mutation linked-test preflight failed:\n"+"\n".join(errors)
        )


def write_config(spec):
    selected="\n".join("    "+n for n in spec["tests"])
    (ROOT/"setup.cfg").write_text(
      "[mutmut]\nprocess_isolation = forkserver\nforkserver_warmup = collect\nsource_paths =\n    src/llm_router\n"
      f"only_mutate =\n    {spec['source']}\nmutate_only_covered_lines = true\nalso_copy =\n    features\n"
      f"pytest_add_cli_args =\n    --no-cov\npytest_add_cli_args_test_selection =\n{selected}\n")

def run_mutmut(spec):
    shutil.rmtree(ROOT/"mutants",ignore_errors=True)
    write_config(spec)
    env=probe_env()
    env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"]="YES"
    mutmut_executable=shutil.which("mutmut")
    command=[
      *( [mutmut_executable] if mutmut_executable else [sys.executable,"-m","mutmut"] ),
      "run",
      "--max-children",str(MUTATION_CONFIG["max_children"]),
    ]
    completed=subprocess.run(
      command,
      cwd=ROOT,
      env=env,
      text=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
    )
    output=completed.stdout or ""
    if completed.returncode!=0 and "ForkServerCrashError" in output:
        print(
          "[P23] mutmut forkserver crashed; resuming retained mutant set "
          "with max_children=1",
          flush=True,
        )
        resume_command=[*command[:-1],"1"]
        completed=subprocess.run(
          resume_command,
          cwd=ROOT,
          env=env,
          text=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
        )
        output=(output+"\n--- forkserver recovery ---\n"+(completed.stdout or ""))
    if completed.returncode!=0:
        tail=output[-8000:]
        raise RuntimeError(f"mutmut failed with exit {completed.returncode}:\n{tail}")

def scope_matches(name,spec):
    from mutmut.utils.format_utils import (  # ty: ignore[unresolved-import]
        orig_function_and_class_names_from_key,
    )
    fn,cls=orig_function_and_class_names_from_key(name)
    return cls==spec["scope"] if spec["kind"]=="class" else cls is None and fn==spec["scope"]

def function_start(path,name):
    from mutmut.utils.format_utils import (  # ty: ignore[unresolved-import]
        orig_function_and_class_names_from_key,
    )
    fn,cls=orig_function_and_class_names_from_key(name)
    nodes=ast.parse(path.read_text()).body
    if cls:
        nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name==cls).body
    f=next(n for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==fn)
    return min([f.lineno,*[d.lineno for d in f.decorator_list]])

def mutant_detail(path,name):
    from mutmut.mutation.diff_apply import (  # ty: ignore[unresolved-import]
        get_diff_for_mutant,
    )
    diff=get_diff_for_mutant(name,path=str(path.relative_to(ROOT)))
    start=function_start(path,name)
    old=new=0
    changed=None
    before=after=""
    for row in diff.splitlines():
        if row.startswith("@@"):
            m=re.search(r"@@ -(\d+)(?:,\d+)? \+(\d+)",row)
            if m:
                old,new=map(int,m.groups())
        elif row.startswith("---") or row.startswith("+++"):
            continue
        elif row.startswith("-"):
            if changed is None:
                changed=start+old-1
                before=row[1:]
            old+=1
        elif row.startswith("+"):
            if not after:
                after=row[1:]
            new+=1
        else:
            old+=1
            new+=1
    line=changed or start
    common=0
    for a,b in zip(before,after):
        if a!=b:
            break
        common+=1
    col=max(1,common+1)
    loc={"start":{"line":line,"column":col},"end":{"line":line,"column":max(col+1,len(before)+1)}}
    desc=f"{before.strip() or '[removed]'} -> {after.strip() or '[removed]'}"
    return loc,desc,after.strip()

def coverage_by_test(spec):
    source=str((ROOT/spec["source"]).resolve())
    out={}
    for nodeid in spec["tests"]:
        d=CoverageData(basename=str(COVERAGE_DB))
        d.read()
        d.set_query_context(nodeid+"|run")
        out[nodeid]=set(d.lines(source) or [])
    return out

def report_test_files(spec):
    grouped=defaultdict(list)
    for nodeid in spec["tests"]:
        grouped[nodeid.split("::",1)[0]].append(nodeid)
    files={}
    for file_name,nodeids in grouped.items():
        files[file_name]={
          "source":(ROOT/file_name).read_text(),
          "tests":[
            {"id":nodeid,"name":nodeid,"location":{"start":{"line":int(TEST_META.get(nodeid,{}).get("source_line") or 1),"column":1}}}
            for nodeid in nodeids]}
    return files

def allure_report_ids():
    wanted={nodeid for spec in CONTRACTS.values() for nodeid in spec["tests"]}
    keys={}
    for nodeid in wanted:
        file_name,test_name=nodeid.split("::",1)
        keys[(file_name.removesuffix(".py").replace("/","."),test_name)]=nodeid
    found={}
    for path in (ROOT/"test-results/allure-results").glob("*-result.json"):
        try:
            row=json.loads(path.read_text())
        except Exception:
            continue
        full_name=str(row.get("fullName") or "")
        name=str(row.get("name") or "")
        for (package,test_name),nodeid in keys.items():
            base_name=test_name.split("[",1)[0]
            full_name_matches = full_name == package + "#" + base_name
            display_name_matches = name == test_name or name == base_name
            parameterized = "[" in test_name
            if full_name_matches and (display_name_matches or not parameterized):
                uuid=str(row.get("uuid") or "")
                if uuid:
                    import hashlib
                    found[nodeid]=hashlib.md5(uuid.encode()).hexdigest()
    return found

def write_wrapper(contract_id,spec,allure_ids,fact):
    links=[]
    for nodeid in spec["tests"]:
        report_id=allure_ids.get(nodeid)
        target=(f"../../test-results/index.html#{report_id}" if report_id
                else f"../../test-results/index.html?tags=TF_SCOPE__{contract_id}")
        links.append(f'<li><a href="{target}" title="{nodeid}">{nodeid.split("::")[-1]}</a></li>')
    exact="".join(links)
    fresh=bool(fact.get("fresh"))
    freshness_label="Fresh" if fresh else "STALE"
    freshness_class="is-fresh" if fresh else "is-stale"
    stale_reason="" if fresh else " · "+", ".join(fact.get("stale_reasons") or ["fingerprint mismatch"])
    campaign_mode=str(fact.get("campaign_mode") or "unknown")
    campaign_head=str(fact.get("campaign_head_sha") or "")
    campaign_id=str(fact.get("campaign_id") or "unknown")
    run_id=str(fact.get("run_id") or campaign_id)
    provenance_url=str(fact.get("campaign_provenance_url") or "../campaign.json")
    triage=fact.get("triage") or {}
    new_unresolved=int(triage.get("new_unresolved_survivors") or 0)
    if triage.get("baseline_available"):
        delta=("n/a" if triage.get("score_delta") is None else f"{float(triage['score_delta']):+.1f} pp")
        triage_text=(
          f"Mutation delta · New {int(triage.get('new_survivors') or 0)} "
          f"({new_unresolved} unresolved) · Debt {int(triage.get('existing_survivors') or 0)} · "
          f"Resolved {int(triage.get('resolved_survivors') or 0)} · "
          f"Suppressed {int(triage.get('suppressed_survivors') or 0)} · score Δ {delta}"
        )
    elif triage:
        triage_text=f"Mutation delta · baseline unavailable · current survivors {int(triage.get('current_survivors') or 0)}"
    else:
        triage_text="Mutation delta · not retained for this campaign"
    triage_class="is-attention" if new_unresolved else "is-clear"
    suppressed_rows=[row for row in triage.get("survivors") or [] if row.get("classification")=="suppressed"]
    suppressed_html=""
    if suppressed_rows:
        items="".join(
          "<li><code>"+html_escape(str(row.get("fingerprint") or "")[:12])+"</code> · "+
          html_escape(str(row.get("description") or ""))+" · <b>Reason:</b> "+
          html_escape(str((row.get("suppression") or {}).get("reason") or ""))+
          (" · owner "+html_escape(str((row.get("suppression") or {}).get("owner"))) if (row.get("suppression") or {}).get("owner") else "")+
          (" · expires "+html_escape(str((row.get("suppression") or {}).get("expires_at"))) if (row.get("suppression") or {}).get("expires_at") else "")+
          "</li>"
          for row in suppressed_rows
        )
        suppressed_html=f'<details class="tf-suppressions"><summary>Suppressed survivors ({len(suppressed_rows)})</summary><ul>{items}</ul></details>'
    html=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{contract_id} · Raw mutation detail</title><script defer src="../../_static/mutation-test-elements.js"></script>
<style>html,body{{margin:0;min-height:100%;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}.tf-bridge{{display:flex;align-items:flex-start;gap:1rem;flex-wrap:wrap;padding:.65rem .9rem;border-bottom:1px solid #d0d5dd;background:#f8fafc;color:#172033}}.tf-bridge a{{color:#1d4ed8;text-decoration:none}}.tf-bridge a:hover{{text-decoration:underline}}.tf-bridge details{{margin-left:auto}}.tf-bridge summary{{cursor:pointer;font-size:.78rem;color:#475467}}.tf-bridge ul{{font-size:.74rem;line-height:1.5}}.tf-campaign,.tf-triage{{flex-basis:100%;font-size:.76rem;color:#475467}}.tf-suppressions{{flex-basis:100%;margin-left:0!important;font-size:.76rem;color:#475467}}.tf-suppressions code{{font-size:.72rem}}.tf-campaign strong.is-fresh,.tf-triage strong.is-clear{{color:#2f8f5b}}.tf-campaign strong.is-stale,.tf-triage strong.is-attention{{color:#c2413b}}@media(prefers-color-scheme:dark){{.tf-bridge{{background:#151a21;color:#d0d7de;border-color:#30363d}}.tf-bridge a{{color:#79c0ff}}.tf-bridge summary,.tf-campaign,.tf-triage,.tf-suppressions{{color:#9da7b3}}}}</style></head><body>
<nav class="tf-bridge"><a href="../../verification-depth-map.html">← Test Strength map</a><strong>{contract_id} · Raw mutants</strong>
<a href="../../mutation-analysis.html#mutation-{contract_id.lower()}">Changes / history</a>
<a href="../../test-results/index.html?tags=TF_SCOPE__{contract_id}">Allure tests</a>
<details><summary>Exact pytest / Allure tests ({len(spec["tests"])})</summary><ul>{exact}</ul></details>
<div class="tf-campaign"><strong class="{freshness_class}">{freshness_label}</strong> · {campaign_mode} campaign · {campaign_head[:12]} · content {campaign_id} · run {run_id.rsplit("--", maxsplit=1)[-1]}{stale_reason} · <a href="{provenance_url}">campaign provenance</a></div>
<div class="tf-triage"><strong class="{triage_class}">{'Attention' if new_unresolved else 'No new unresolved survivors'}</strong> · {triage_text}</div>
{suppressed_html}</nav>
<mutation-test-report-app src="mutation-report.json" title-postfix="{contract_id} · llm-router"></mutation-test-report-app>
</body></html>"""
    (OUT/contract_id/"index.html").write_text(html)

def freshness_state(record,current):
    reasons=[]
    labels={
      "source_fingerprint":"implementation source changed",
      "test_set_fingerprint":"linked tests changed",
      "config_fingerprint":"mutation configuration changed",
    }
    for key,label in labels.items():
        if record.get(key)!=current.get(key):
            reasons.append(label)
    return not reasons,reasons

def build_summary(campaign):
    rows={}
    fresh=stale=0
    totals={
      "new_survivors":0,
      "existing_survivors":0,
      "resolved_survivors":0,
      "suppressed_survivors":0,
      "new_unresolved_survivors":0,
      "unresolved_survivors":0,
    }
    actionable_contracts=[]
    for contract_id in CONTRACTS:
        fact=STRENGTH["contracts"][contract_id]
        triage=fact.get("triage") or {}
        is_fresh=bool(fact.get("fresh"))
        fresh+=int(is_fresh)
        stale+=int(not is_fresh)
        for key in totals:
            totals[key]+=int(triage.get(key) or 0)
        if int(triage.get("new_unresolved_survivors") or 0)>0:
            actionable_contracts.append(contract_id)
        rows[contract_id]={
          "score":fact.get("score"),
          "state":fact.get("state"),
          "killed":fact.get("killed"),
          "survived":fact.get("survived"),
          "valid_mutants":fact.get("valid_mutants"),
          "fresh":is_fresh,
          "stale_reasons":fact.get("stale_reasons") or [],
          "report_url":fact.get("report_url"),
          "campaign_id":fact.get("campaign_id"),
          "run_id":fact.get("run_id"),
          "campaign_mode":fact.get("campaign_mode"),
          "campaign_head_sha":fact.get("campaign_head_sha"),
          "baseline_run_id":fact.get("baseline_run_id"),
          "baseline_campaign_id":fact.get("baseline_campaign_id"),
          "triage":{
            key:triage.get(key)
            for key in (
              "baseline_available","baseline_comparable","baseline_score","score_delta",
              "current_survivors","new_survivors","existing_survivors","resolved_survivors",
              "unclassified_survivors","suppressed_survivors","new_unresolved_survivors",
              "unresolved_survivors","readiness"
            )
            if key in triage
          },
        }
    return {
      "schema_version":"ternforge-mutation-summary-prototype-4",
      "campaign_id":campaign["campaign_id"],
      "run_id":campaign.get("run_id"),
      "baseline_run_id":campaign.get("baseline_run_id"),
      "baseline_campaign_id":campaign.get("baseline_campaign_id"),
      "mode":campaign["mode"],
      "head_sha":campaign["head_sha"],
      "latest_selected_contracts":campaign.get("selected_contracts") or list(campaign.get("contracts") or {}),
      "latest_skipped_contracts":campaign.get("skipped_contracts") or [],
      "measured_contracts":len(rows),
      "total_contracts":len(DEPTH.get("contracts") or []),
      "fresh_measured_contracts":fresh,
      "stale_measured_contracts":stale,
      **totals,
      "actionable_contracts":actionable_contracts,
      "readiness":"attention" if actionable_contracts else "clear",
      "contracts":rows,
    }

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


def map_status(rows):
    if not rows:
        return "none"
    results = [str(row.get("result") or "unknown").lower() for row in rows]
    if any(result in {"failed", "error", "broken"} for result in results):
        return "failed"
    if any(result != "passed" for result in results):
        return "attention"
    return "passed"


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
            if not owner and not binding.get("fault_challenge"):
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
    # One row per goal, capability and contract with the product first, in the same shape as the Depth Map's rows; the
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
    ("survivors","Surviving mutants","The contract's own tests let injected implementation faults survive."),
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
    if not state:
        return "campaign"
    if state.get("detected"):
        return None
    campaign=state.get("campaign_state")
    if campaign=="blocked":
        return {"shared_scope":"shared","no_impl_scope":"noimpl","no_passing_tests":"notests"}.get((plan or {}).get("blocked"),"blocked")
    if campaign=="current":
        return "survivors" if state.get("generated") else "nosite"
    if campaign:
        return "campaign"
    return "missed" if state.get("exercised") else "unchallenged"


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


def render_health_map_page():
    payload=health_map_payload()
    payload["insights"]=health_map_insights(payload)

    article=MAP_PAGES.health_map_article(stable_json(payload),vendored_d3_hierarchy())
    HEALTH_PAGE.write_text(portal_map_shell(HEALTH_PAGE,"Verification Health Map",article))
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
    killed=sum(int(state.get("killed") or 0) for state in classes.values())
    survived=sum(int(state.get("survived") or 0) for state in classes.values())
    if killed+survived:
        return [killed,killed+survived],""
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
    it was written for, as on the Health Map; the hierarchy is the Health Map's own."""
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
        if binding.get("assurance_item"):
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


def render_depth_map_page(health_payload=None):
    health_payload=health_payload or health_map_payload()
    payload=depth_map_payload(health_payload)
    payload["insights"]=depth_map_insights(payload,health_payload)
    article=MAP_PAGES.depth_map_article(stable_json(payload),vendored_d3_hierarchy())
    DEPTH_PAGE.write_text(portal_map_shell(DEPTH_PAGE,"Verification Depth Map",article))


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


def mutation_family(record):
    description=str(record.get("description") or "")
    replacement=str(record.get("replacement") or "")
    left=description.split(" -> ",1)[0].strip()
    low_replacement=replacement.lower()
    low_description=description.lower()
    if not replacement.strip() or "-> [removed]" in low_description:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*\s*=",left) or left.endswith(","):
            return "Argument / field removal"
        return "Statement removal"
    if "none" in low_replacement:
        return "None / nullification"
    if any(token in low_replacement for token in (" and false"," or true"," and true"," or false")):
        return "Boolean / condition"
    if any(token in low_description for token in (" is none -> "," is not none -> "," == "," != "," <= "," >= "," < "," > ")):
        return "Comparison / condition"
    if re.search(r"['\"][^'\"]*['\"]",left) and re.search(r"['\"][^'\"]*['\"]",replacement):
        return "String literal"
    if re.search(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?![A-Za-z_])",left) and re.search(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?![A-Za-z_])",replacement):
        return "Numeric literal"
    if "(" in left and "(" in replacement:
        return "Call / argument change"
    return "Other"

def retained_runs(current_campaign):
    rows=[]
    seen=set()
    for path in sorted(HISTORY_DIR.glob("*.json")):
        try:
            row=json.loads(path.read_text())
        except Exception:
            continue
        run_id=str(row.get("run_id") or row.get("campaign_id") or path.stem)
        if run_id in seen:
            continue
        seen.add(run_id)
        rows.append(row)
    run_id=str(current_campaign.get("run_id") or current_campaign.get("campaign_id") or "current")
    rows=[row for row in rows if str(row.get("run_id") or row.get("campaign_id"))!=run_id]
    rows.append(current_campaign)
    return rows

def median_value(values):
    values=sorted(float(value) for value in values)
    if not values:
        return None
    middle=len(values)//2
    return values[middle] if len(values)%2 else (values[middle-1]+values[middle])/2

def build_operator_feedback(current_campaign):
    runs=retained_runs(current_campaign)
    families={}
    mode_costs=defaultdict(list)
    run_rows=[]
    mutant_runs=0
    directly_timed_contract_runs=0

    def family_row(name):
        return families.setdefault(name,{
          "family":name,
          "unique_fingerprints":set(),
          "actionable_fingerprints":set(),
          "observations":0,
          "killed_observations":0,
          "survived_observations":0,
          "new_events":0,
          "resolved_events":0,
          "suppressed_events":0,
          "current_survivors":0,
          "estimated_cost_seconds":0.0,
          "cost_observations":0,
        })

    current_run_id=str(current_campaign.get("run_id") or current_campaign.get("campaign_id") or "")
    for run in runs:
        mode=str(run.get("mode") or "unknown")
        duration=run.get("duration_seconds")
        if duration is not None:
            mode_costs[mode].append(float(duration))
        run_id=str(run.get("run_id") or run.get("campaign_id") or "")
        selected=list(run.get("selected_contracts") or (run.get("contracts") or {}).keys())
        run_row={
          "run_id":run_id,
          "campaign_id":run.get("campaign_id"),
          "baseline_run_id":run.get("baseline_run_id"),
          "mode":mode,
          "duration_seconds":duration,
          "finished_at":run.get("finished_at"),
          "selected_contracts":selected,
          "mutants":sum(len((contract.get("result") or {}).get("mutants") or []) for contract in (run.get("contracts") or {}).values()),
          "new_unresolved_survivors":0,
          "existing_survivors":0,
          "resolved_survivors":0,
          "suppressed_survivors":0,
        }
        run_rows.append(run_row)
        run_has_mutants=False
        for contract_id,contract in (run.get("contracts") or {}).items():
            result=contract.get("result") or {}
            records=list(result.get("mutants") or [])
            if not records:
                continue
            run_has_mutants=True
            contract_duration=result.get("duration_seconds")
            if contract_duration is not None:
                directly_timed_contract_runs+=1
                contract_duration=float(contract_duration)
            elif len(selected)==1 and duration is not None:
                contract_duration=float(duration)
            else:
                contract_duration=None
            by_family=defaultdict(list)
            by_fp={}
            for record in records:
                name=mutation_family(record)
                by_family[name].append(record)
                by_fp[str(record.get("fingerprint") or "")]=name
                item=family_row(name)
                fingerprint=str(record.get("fingerprint") or "")
                if fingerprint:
                    item["unique_fingerprints"].add(fingerprint)
                item["observations"]+=1
                if record.get("status")=="Killed":
                    item["killed_observations"]+=1
                if record.get("status")=="Survived":
                    item["survived_observations"]+=1
                    if run_id==current_run_id:
                        item["current_survivors"]+=1
            if contract_duration is not None and records:
                for name,family_records in by_family.items():
                    item=family_row(name)
                    item["estimated_cost_seconds"]+=contract_duration*len(family_records)/len(records)
                    item["cost_observations"]+=1

            triage=result.get("triage") or {}
            run_row["new_unresolved_survivors"]+=int(triage.get("new_unresolved_survivors") or 0)
            run_row["existing_survivors"]+=int(triage.get("existing_survivors") or 0)
            run_row["resolved_survivors"]+=int(triage.get("resolved_survivors") or 0)
            run_row["suppressed_survivors"]+=int(triage.get("suppressed_survivors") or 0)
            for survivor in triage.get("survivors") or []:
                classification=str(survivor.get("classification") or "")
                name=mutation_family(survivor)
                item=family_row(name)
                fingerprint=str(survivor.get("fingerprint") or "")
                if classification=="new":
                    item["new_events"]+=1
                    if fingerprint:
                        item["actionable_fingerprints"].add(fingerprint)
                elif classification=="suppressed":
                    item["suppressed_events"]+=1
                    if fingerprint:
                        item["actionable_fingerprints"].add(fingerprint)
            for resolved in triage.get("resolved") or []:
                name=mutation_family(resolved)
                item=family_row(name)
                fingerprint=str(resolved.get("fingerprint") or "")
                item["resolved_events"]+=1
                if fingerprint:
                    item["actionable_fingerprints"].add(fingerprint)
        mutant_runs+=int(run_has_mutants)

    family_rows=[]
    for item in families.values():
        unique_count=len(item["unique_fingerprints"])
        actionable_count=len(item["actionable_fingerprints"])
        observations=int(item["observations"])
        survived=int(item["survived_observations"])
        action_events=int(item["new_events"])+int(item["resolved_events"])+int(item["suppressed_events"])
        if action_events:
            decision="Retain · demonstrated action events"
        elif int(item["current_survivors"]):
            decision="Observe · persistent survivors"
        else:
            decision="Observe · no filter evidence"
        family_rows.append({
          "family":item["family"],
          "unique_mutants":unique_count,
          "observations":observations,
          "killed_observations":int(item["killed_observations"]),
          "survived_observations":survived,
          "survival_observation_rate":round(100*survived/observations,1) if observations else None,
          "current_survivors":int(item["current_survivors"]),
          "new_events":int(item["new_events"]),
          "resolved_events":int(item["resolved_events"]),
          "suppressed_events":int(item["suppressed_events"]),
          "action_events":action_events,
          "unique_actionable_mutants":actionable_count,
          "actionable_unique_rate":round(100*actionable_count/unique_count,1) if unique_count else None,
          "estimated_cost_seconds":round(float(item["estimated_cost_seconds"]),3),
          "cost_observations":int(item["cost_observations"]),
          "decision":decision,
        })
    family_rows.sort(
        key=lambda row: (
            -int(row["action_events"]),
            -float(row["estimated_cost_seconds"]),
            -int(row["unique_mutants"]),
            str(row["family"]),
        )
    )

    performance={}
    for mode,values in mode_costs.items():
        performance[mode]={
          "runs":len(values),
          "median_seconds":round(median_value(values),3),
          "min_seconds":round(min(values),3),
          "max_seconds":round(max(values),3),
        }

    return {
      "schema_version":"ternforge-mutation-operator-feedback-prototype-1",
      "generated_at":utc_now(),
      "engine":"mutmut",
      "family_basis":"Ternforge-derived diagnostic families from retained mutation descriptions/replacements; not engine-native mutator labels.",
      "cost_basis":"Observed campaign/contract runtime. Family cost is a proportional estimate by family mutant share because retained mutmut data has no per-mutant timing.",
      "sample":{
        "retained_runs":len(runs),
        "runs_with_mutant_records":mutant_runs,
        "unique_campaign_contents":len({str(row.get("campaign_id") or "") for row in runs if row.get("campaign_id")}),
        "measured_contracts":len([fact for fact in STRENGTH.get("contracts",{}).values() if fact.get("score") is not None]),
        "directly_timed_contract_runs":directly_timed_contract_runs,
      },
      "performance_by_mode":performance,
      "families":family_rows,
      "filtering_decision":{
        "decision":"none",
        "reason":"Pilot history is narrow (three uniquely attributable contracts plus controlled acceptance probes); no mutation family is disabled or capped from this sample.",
        "full_audit_preserved":True,
        "diff_mode_filtering_enabled":False,
      },
      "runs":run_rows,
    }

def mutation_priority(fact):
    triage=fact.get("triage") or {}
    if int(triage.get("new_unresolved_survivors") or 0):
        return (0,-int(triage.get("new_unresolved_survivors") or 0))
    if not fact.get("fresh"):
        return (1,0)
    if int(triage.get("suppressed_survivors") or 0):
        return (2,-int(triage.get("suppressed_survivors") or 0))
    if int(triage.get("unresolved_survivors") or 0):
        return (3,-int(triage.get("unresolved_survivors") or 0))
    return (4,0)

def format_delta(value):
    if value is None:
        return "n/a"
    return f"{float(value):+.1f} pp"

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
    text=re.sub(
      r'\n<li class="nav-item[^"]*" data-ternforge-p22-nav="(?:health|depth|mutation)">.*?</li>\n',
      "\n",text,flags=re.DOTALL
    )
    nav_prefix=text.split('<main id="main-content"',1)[0]
    health_pattern=re.compile(
      r'(<li class="nav-item[^"]*">\s*<a class="nav-link nav-internal" href="(?:verification-health-map\.html|#)">\s*Verification Health Map\s*</a>\s*</li>)'
    )
    depth_pattern=re.compile(
      r'(<li class="nav-item[^"]*">\s*<a class="nav-link nav-internal" href="(?:verification-depth-map\.html|#)">\s*Verification Depth Map\s*</a>\s*</li>)'
    )
    verification_pattern=re.compile(
      r'(<li class="nav-item[^"]*">\s*<a class="nav-link nav-internal" href="verification\.html">\s*Verification\s*</a>\s*</li>)'
    )
    mutation_item=portal_nav_item(
      "Mutation Analysis","mutation-analysis.html",
      active=current=="mutation",kind="mutation"
    )
    if depth_pattern.search(nav_prefix):
        return depth_pattern.sub(lambda m:m.group(1)+mutation_item,text)
    depth_item=portal_nav_item(
      "Verification Depth Map","verification-depth-map.html",
      active=current=="depth",kind="depth"
    )
    if health_pattern.search(nav_prefix):
        return health_pattern.sub(lambda m:m.group(1)+depth_item+mutation_item,text)
    health_item=portal_nav_item(
      "Verification Health Map","verification-health-map.html",
      active=current=="health",kind="health"
    )
    return verification_pattern.sub(
      lambda m:m.group(1)+health_item+depth_item+mutation_item,
      text,
    )


def operator_feedback_section(feedback):
    sample=feedback.get("sample") or {}
    performance_rows=[]
    for mode,row in sorted((feedback.get("performance_by_mode") or {}).items()):
        performance_rows.append(
          "<tr>"
          f"<td><code>{html_escape(mode)}</code></td>"
          f"<td>{int(row.get('runs') or 0)}</td>"
          f"<td>{float(row.get('median_seconds') or 0):.3f}s</td>"
          f"<td>{float(row.get('min_seconds') or 0):.3f}s – {float(row.get('max_seconds') or 0):.3f}s</td>"
          "</tr>"
        )
    family_rows=[]
    for row in feedback.get("families") or []:
        cost=(
          f"~{float(row.get('estimated_cost_seconds') or 0):.1f}s proportional · "
          f"{int(row.get('cost_observations') or 0)} observation(s)"
          if int(row.get("cost_observations") or 0)
          else "not directly timed yet"
        )
        family_rows.append(
          "<tr>"
          f"<td><strong>{html_escape(str(row.get('family') or ''))}</strong></td>"
          f"<td>{int(row.get('unique_mutants') or 0)} unique<br><small>{int(row.get('observations') or 0)} retained observations</small></td>"
          f"<td>{int(row.get('current_survivors') or 0)} current<br><small>{float(row.get('survival_observation_rate') or 0):.1f}% survivor observations</small></td>"
          f"<td>New {int(row.get('new_events') or 0)} · Resolved {int(row.get('resolved_events') or 0)} · Suppressed {int(row.get('suppressed_events') or 0)}<br><small>{int(row.get('unique_actionable_mutants') or 0)} unique actionable mutant(s)</small></td>"
          f"<td>{html_escape(cost)}</td>"
          f"<td>{html_escape(str(row.get('decision') or ''))}</td>"
          "</tr>"
        )
    return f"""
<details id="mutation-operator-feedback" class="sd-card sd-sphinx-override sd-shadow-sm sd-mt-3 sd-mb-3 docutils">
<summary><strong>Run cost / mutation diagnostics</strong> · {int(sample.get('retained_runs') or 0)} runs · no filters</summary>
<div class="sd-card-body docutils">
<p><small>Diagnostic only. Family labels are derived from retained mutmut descriptions; full audit remains enabled.</small></p>
<p><a href="mutation-results/operator-feedback.json">Raw operator feedback JSON</a></p>
<h3>Observed run cost</h3>
<div class="pst-scrollable-table-container"><table class="table">
<thead><tr><th>Mode</th><th>Runs</th><th>Median</th><th>Range</th></tr></thead>
<tbody>{''.join(performance_rows)}</tbody>
</table></div>
<h3>Derived mutation families</h3>
<div class="pst-scrollable-table-container"><table class="table">
<thead><tr><th>Family</th><th>Volume</th><th>Survivors</th><th>Action events</th><th>Cost evidence</th><th>Decision</th></tr></thead>
<tbody>{''.join(family_rows)}</tbody>
</table></div>
</div>
</details>
"""

def mutation_history_section(summary,feedback):
    current_run=str(summary.get("run_id") or "")
    runs=list(feedback.get("runs") or [])
    runs.sort(key=lambda row:(str(row.get("finished_at") or ""),str(row.get("run_id") or "")))
    rows=[]
    for row in list(reversed(runs))[:6]:
        run_id=str(row.get("run_id") or "")
        campaign_id=str(row.get("campaign_id") or "")
        if run_id==current_run:
            provenance="mutation-results/campaign.json"
            current=" <strong>current</strong>"
        else:
            candidate=HISTORY_DIR/f"{run_id}.json"
            if not candidate.exists() and campaign_id:
                candidate=HISTORY_DIR/f"{campaign_id}.json"
            provenance=(
              f"mutation-results/campaign-history/{html_escape(candidate.name)}"
              if candidate.exists()
              else "mutation-results/operator-feedback.json"
            )
            current=""
        new_count=int(row.get("new_unresolved_survivors") or 0)
        resolved=int(row.get("resolved_survivors") or 0)
        suppressed=int(row.get("suppressed_survivors") or 0)
        existing=int(row.get("existing_survivors") or 0)
        if new_count:
            signal=f"<strong>New {new_count}</strong> · Debt {existing}"
        elif resolved:
            signal=f"Resolved {resolved} · Debt {existing}"
        else:
            signal=f"No new regression · Debt {existing}"
        if suppressed:
            signal+=f" · Suppressed {suppressed}"
        duration=row.get("duration_seconds")
        duration_text=f"{float(duration):.3f}s" if duration is not None else "n/a"
        selected=len(row.get("selected_contracts") or [])
        rows.append(
          "<tr>"
          f"<td>{signal}</td>"
          f'<td><code>{html_escape(str(row.get("mode") or "unknown"))}</code> · {selected} contract(s)<br><small>{int(row.get("mutants") or 0)} mutants</small></td>'
          f"<td>{duration_text}</td>"
          f'<td><a href="{provenance}"><code>{html_escape(run_id.rsplit("--", maxsplit=1)[-1] or campaign_id)}</code></a>{current}</td>'
          "</tr>"
        )
    return f"""<section id="mutation-history">
<h2>Recent changes<a class="headerlink" href="#mutation-history" title="Link to this heading">#</a></h2>
<p><small>Most recent retained mutation campaign summaries. The current campaign links to raw provenance; older summary-only rows link to the retained operator-feedback record.</small></p>
<div class="pst-scrollable-table-container"><table class="table">
<thead><tr><th>Signal</th><th>Run scope</th><th>Duration</th><th>Evidence</th></tr></thead>
<tbody>{''.join(rows) if rows else '<tr><td colspan="4">No retained campaigns yet.</td></tr>'}</tbody>
</table></div>
</section>"""


def write_mutation_analysis_page(summary,feedback):
    if not ASSURANCE_PAGE.exists():
        return
    template=ASSURANCE_PAGE.read_text()
    # The PyData shell is reused, but assurance-only runtime projections must
    # never leak into the mutation journal on repeated local rebuilds.
    template=re.sub(
      r"<!-- TERNFORGE-(?:P2[789]|P3[0-3])-ASSURANCE-EVIDENCE-START -->.*?<!-- TERNFORGE-(?:P2[789]|P3[0-3])-ASSURANCE-EVIDENCE-END -->",
      "",template,flags=re.DOTALL,
    )
    template=re.sub(
      r"<!-- TERNFORGE-P27-CONTRACT-EVIDENCE-START -->.*?<!-- TERNFORGE-P27-CONTRACT-EVIDENCE-END -->",
      "",template,flags=re.DOTALL,
    )
    template=re.sub(
      r'<style id="tf-requirement-monitor-style">.*?</style>',
      "",
      template,
      flags=re.DOTALL,
    )
    template=re.sub(
      r'<script id="tf-requirement-monitor-script">.*?</script>',
      "",
      template,
      flags=re.DOTALL,
    )
    measured=[]
    for contract_id,fact in STRENGTH.get("contracts",{}).items():
        if fact.get("score") is None:
            continue
        measured.append((contract_id,fact))
    measured.sort(key=lambda item:(mutation_priority(item[1]),item[0]))
    rows=[]
    for contract_id,fact in measured:
        triage=fact.get("triage") or {}
        score=f"{float(fact['score']):.1f}%"
        band=str(fact.get("state") or "n/a").title()
        fresh="Fresh" if fact.get("fresh") else "STALE"
        rows.append(
          f'<tr id="mutation-{html_escape(contract_id.lower())}">'
          f'<td><a href="traceability-reader.html#review-{html_escape(contract_id)}"><code>{html_escape(contract_id)}</code></a></td>'
          f'<td><strong>{score}</strong> · {html_escape(band)}<br><small>{int(fact.get("killed") or 0)} killed · {int(fact.get("survived") or 0)} survived</small></td>'
          f'<td><strong>{fresh}</strong> · New {int(triage.get("new_survivors") or 0)} · Debt {int(triage.get("existing_survivors") or 0)} · Resolved {int(triage.get("resolved_survivors") or 0)} · Suppressed {int(triage.get("suppressed_survivors") or 0)}<br><small>Δ {html_escape(format_delta(triage.get("score_delta")))} · {html_escape(str(fact.get("campaign_mode") or "unknown"))}</small></td>'
          f'<td><a href="{html_escape(str(fact.get("report_url") or "#"))}">Raw mutants</a> · <a href="{html_escape(str(fact.get("allure_url") or "#"))}">Allure</a></td>'
          '</tr>'
        )
    unattributed_rows=[]
    for row in STRENGTH.get("unattributed") or []:
        unattributed_rows.append(
          '<tr>'
          f'<td><code>{html_escape(str(row.get("contract_id") or ""))}</code></td>'
          f'<td>{float(row.get("score") or 0):.1f}% diagnostic<br><small>{int(row.get("killed") or 0)} killed · {int(row.get("survived") or 0)} survived</small></td>'
          f'<td><code>{html_escape(str(row.get("source_path") or ""))}</code> · {html_escape(str(row.get("scope") or ""))}</td>'
          f'<td>{html_escape(str(row.get("reason") or ""))}</td>'
          '</tr>'
        )
    total=int(summary.get("total_contracts") or 0)
    measured_count=int(summary.get("measured_contracts") or 0)
    run_id=str(summary.get("run_id") or "")
    operator_section=operator_feedback_section(feedback)
    history_section=mutation_history_section(summary,feedback)
    debt_count=int(summary.get("existing_survivors") or 0)
    article=f"""
<article class="bd-article">
<section id="mutation-analysis">
<h1>Mutation Analysis<a class="headerlink" href="#mutation-analysis" title="Link to this heading">#</a></h1>
<p><a href="verification-depth-map.html">← Test Strength map</a> · Open this page when the map shows a new/stale signal, when you want to work down known debt, or when you need run history.</p>
<div class="admonition note">
<p class="admonition-title">Current signal</p>
<p><strong>New {int(summary.get("new_unresolved_survivors") or 0)}</strong> · <strong>Debt {debt_count}</strong> · Stale {int(summary.get("stale_measured_contracts") or 0)} · Suppressed {int(summary.get("suppressed_survivors") or 0)} · Measured {measured_count}/{total} · <code>{html_escape(str(summary.get("mode") or ""))}</code> run <a href="mutation-results/campaign.json"><code>{html_escape(run_id.rsplit("--", maxsplit=1)[-1])}</code></a></p>
</div>
<section id="mutation-work-queue">
<h2>Changes &amp; debt<a class="headerlink" href="#mutation-work-queue" title="Link to this heading">#</a></h2>
<p><small>Priority: New → Stale → Suppressed → Debt.</small></p>
<div class="pst-scrollable-table-container"><table class="table">
<thead><tr><th>Contract</th><th>Strength</th><th>Change</th><th>Open</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
</section>
{history_section}
<details id="mutation-unattributed" class="sd-card sd-sphinx-override sd-shadow-sm sd-mt-3 sd-mb-3 docutils">
<summary><strong>Why some contracts are N/A</strong> · {len(STRENGTH.get("unattributed") or [])} shared-scope diagnostics</summary>
<div class="sd-card-body docutils">
<div class="pst-scrollable-table-container"><table class="table">
<thead><tr><th>Contract</th><th>Diagnostic result</th><th>Scope</th><th>Why N/A</th></tr></thead>
<tbody>{''.join(unattributed_rows) if unattributed_rows else '<tr><td colspan="4">None.</td></tr>'}</tbody>
</table></div>
</div>
</details>
{operator_section}
</section>
</article>
"""
    text=re.sub(r'<article class="bd-article">.*?</article>',article,template,count=1,flags=re.DOTALL)
    mutation_toc=(
      '<nav class="bd-toc-nav page-toc"><ul class="visible nav section-nav flex-column">'
      '<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#mutation-work-queue">Changes &amp; debt</a></li>'
      '<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#mutation-history">Recent changes</a></li>'
      '<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#mutation-unattributed">Why some contracts are N/A</a></li>'
      '<li class="toc-h2 nav-item toc-entry"><a class="reference internal nav-link" href="#mutation-operator-feedback">Operator feedback</a></li>'
      '</ul></nav>'
    )
    text=re.sub(
      r'<nav class="bd-toc-nav page-toc">.*?</nav>',
      mutation_toc,
      text,
      count=1,
      flags=re.DOTALL,
    )
    text=re.sub(
      r"<title>.*?(?= &#8212;)",
      "<title>Mutation Analysis",
      text,
      count=1,
      flags=re.DOTALL,
    )
    text=re.sub(
      r'<li class="breadcrumb-item active" aria-current="page"><span class="ellipsis">.*?</span></li>',
      '<li class="breadcrumb-item active" aria-current="page"><span class="ellipsis">Mutation Analysis</span></li>',
      text,count=1,flags=re.DOTALL
    )
    text=text.replace("_sources/verification-assurance.rst.txt","_sources/mutation-analysis.rst.txt")
    text=patch_navigation_text(text,current="mutation")
    MUTATION_PAGE.write_text(text)
    source=MUTATION_PAGE.parent/"_sources/mutation-analysis.rst.txt"
    source.write_text(
      "Mutation Analysis\n=================\n\n"
      "Generated local llm-router pilot work queue over retained mutation campaign, "
      "Test Strength, triage, and standard Mutation Testing Elements reports.\n"
    )


def scope_line_range(spec):
    path=ROOT/spec["source"]
    tree=ast.parse(path.read_text())
    if spec["kind"]=="class":
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==spec["scope"])
    else:
        node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["scope"])
    return int(node.lineno),int(getattr(node,"end_lineno",node.lineno))


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


def coverage_lines_for(nodeids,source_path):
    source=str((ROOT/source_path).resolve())
    covered=set()
    for nodeid in nodeids:
        data=CoverageData(basename=str(COVERAGE_DB))
        data.read()
        data.set_query_context(nodeid+"|run")
        covered.update(data.lines(source) or [])
    return covered


def gremlin_group_metrics(spec,nodeids,report):
    start,end=scope_line_range(spec)
    scoped=[
      row for row in report.get("results") or []
      if start<=int(row.get("line_number") or -1)<=end
    ]
    # Mutants that break collection/import are invalid, as in the Implementation
    # fault campaign: excluded from reach and sensitivity, reported separately.
    rows=[row for row in scoped if row.get("status") not in IMPL_FAULTS.INVALID]
    invalid_count=len(scoped)-len(rows)
    covered=coverage_lines_for(nodeids,spec["source"])
    coverage_by_test={nodeid:coverage_lines_for([nodeid],spec["source"]) for nodeid in nodeids}
    reached=[row for row in rows if int(row.get("line_number") or -1) in covered]
    killed=[row for row in reached if row.get("status")=="zapped"]
    families={}
    for family in sorted({str(row.get("operator") or "unknown") for row in rows}):
        family_rows=[row for row in rows if str(row.get("operator") or "unknown")==family]
        family_reached=[row for row in family_rows if int(row.get("line_number") or -1) in covered]
        family_killed=[row for row in family_reached if row.get("status")=="zapped"]
        families[family]={
          "generated":len(family_rows),
          "reached":len(family_reached),
          "killed":len(family_killed),
          "survived":len(family_reached)-len(family_killed),
          "unreached":len(family_rows)-len(family_reached),
          "mutation_reach":round(100*len(family_reached)/len(family_rows),1) if family_rows else None,
          "sensitivity":round(100*len(family_killed)/len(family_reached),1) if family_reached else None,
          "overall_detection":round(100*len(family_killed)/len(family_rows),1) if family_rows else None,
        }
    stable=lambda row:(int(row.get("line_number") or -1),str(row.get("operator") or ""),str(row.get("description") or ""))
    mutant_rows=[]
    for row in sorted(rows,key=stable):
        line=int(row.get("line_number") or -1)
        row_reached=line in covered
        row_killed=row_reached and row.get("status")=="zapped"
        mutant_rows.append({
          "gremlin_id":row.get("gremlin_id"),
          "line":line,
          "operator":str(row.get("operator") or "unknown"),
          "description":str(row.get("description") or ""),
          "engine_status":row.get("status"),
          "reached":row_reached,
          "killed":row_killed,
          "covering_tests":[nodeid for nodeid,lines in coverage_by_test.items() if line in lines],
          "killing_test":row.get("killing_test"),
          "selected_tests":list(row.get("selected_tests") or []),
        })
    return {
      "generated":len(rows),
      "reached":len(reached),
      "killed":len(killed),
      "survived":len(reached)-len(killed),
      "unreached":len(rows)-len(reached),
      "mutation_reach":round(100*len(reached)/len(rows),1) if rows else None,
      "sensitivity":round(100*len(killed)/len(reached),1) if reached else None,
      "overall_detection":round(100*len(killed)/len(rows),1) if rows else None,
      "families":families,
      "invalid":invalid_count,
      "mutants":mutant_rows,
      "killed_ids":[str(row.get("gremlin_id") or "") for row in killed],
      "engine_metadata":"native pytest-gremlins operator metadata",
      "nodeids":nodeids,
    }


def implementation_line_reach(spec,nodeids):
    """Exact coverage.py statement reach for the declared implementation scope."""
    from coverage import Coverage

    start,end=scope_line_range(spec)
    source=str((ROOT/spec["source"]).resolve())
    cov=Coverage(data_file=str(COVERAGE_DB))
    cov.load()
    analysis=cov._analyze(source)
    statements=sorted(int(line) for line in analysis.statements if start<=int(line)<=end)
    covered=sorted(set(statements)&coverage_lines_for(nodeids,spec["source"]))
    missing=sorted(set(statements)-set(covered))
    return {
      "metric":"implementation_statement_reach",
      "label":"Implementation statement reach",
      "source_path":spec["source"],
      "scope":spec["scope"],
      "start_line":start,
      "end_line":end,
      "executable_statements":len(statements),
      "covered_statements":len(covered),
      "missing_statements":missing,
      "covered_lines":covered,
      "percent":round(100*len(covered)/len(statements),1) if statements else None,
      "basis":"coverage.py executable statements intersected with retained linked-test run contexts",
      "denominator_note":"Executable Python statements in the declared implementation scope; definition-only/non-statement lines are not counted.",
      "nodeids":list(nodeids),
    }


def gremlin_group_probe(spec,nodeids):
    # Same qualified engine configuration as the Implementation fault campaign: every
    # mutant runs through full pytest, never gremlins' fixture-less lightweight runner.
    command=[*IMPL_FAULTS.engine_command(ROOT,list(nodeids),[spec["source"]]),"--no-cov"]
    start,end=scope_line_range(spec)
    coverage_dir_existed=(ROOT/"coverage").exists()
    try:
        run_checked(
          command,
          env=IMPL_FAULTS.engine_env(PROBE_SCRATCH_DIR,scope={spec["source"]:list(range(start,end+1))}),
        )
        report=json.loads((ROOT/"coverage/gremlins/gremlins.json").read_text())
    finally:
        shutil.rmtree(ROOT/"coverage/gremlins",ignore_errors=True)
        if not coverage_dir_existed:
            shutil.rmtree(ROOT/"coverage",ignore_errors=True)
        (ROOT/".coveragerc.gremlins").unlink(missing_ok=True)
    return gremlin_group_metrics(spec,nodeids,report)


def gherkin_mutation_metrics(payload):
    findings=payload.get("findings") or []
    return {
      "engine":"Agentic Test Forge",
      "mode":"Gherkin Examples mutation",
      "generated":sum(int(row.get("total") or 0) for row in findings),
      "detected":sum(int(row.get("killed") or 0) for row in findings),
      "score":round(
        sum(int(row.get("killed") or 0) for row in findings)
        / max(1,sum(int(row.get("total") or 0) for row in findings))*100,1
      ),
      "target":"features/tools/multi_round.feature",
      "native_metadata":True,
      "report":payload,
    }


def probe_gherkin_mutation():
    forge=ROOT/"forge.toml"
    backup=forge.read_bytes() if forge.exists() else None
    with tempfile.TemporaryDirectory(prefix="ternforge-gherkin-") as temp_dir:
        report_path=Path(temp_dir)/"report.json"
        forge.write_text(
          'gherkin_threshold = 0\n'
          'gherkin_runner = "pytest"\n'
          'gherkin_test_cmd = "uv run pytest -q tests/llm_router/bdd/tools/test_multi_round.py"\n'
          'gherkin_paths = ["features/tools/multi_round.feature"]\n'
          'manifest_dir = ".forge"\n'
        )
        try:
            run_checked([
              shutil.which("uvx") or "uvx","--from","agentic-test-forge","forge","mutate-gherkin",
              "--path","features/tools/multi_round.feature","--full","--threshold","0",
              "--json",str(report_path),
            ])
            payload=json.loads(report_path.read_text())
        finally:
            shutil.rmtree(ROOT/".forge",ignore_errors=True)
            if backup is None:
                forge.unlink(missing_ok=True)
            else:
                forge.write_bytes(backup)
    return gherkin_mutation_metrics(payload)


def probe_architecture_fault():
    baseline=run_checked([str(ROOT/".venv/bin/lint-imports"),"--no-cache"])
    match=re.search(r"Contracts:\s+(\d+) kept,\s+(\d+) broken",baseline)
    with tempfile.TemporaryDirectory(prefix="ternforge-arch-") as temp_dir:
        temp=Path(temp_dir)
        shutil.copy2(ROOT/"pyproject.toml",temp/"pyproject.toml")
        for name in ("src","tests","examples"):
            shutil.copytree(ROOT/name,temp/name)
        mutant=temp/"src/llm_router/_internal/runtime/limiter.py"
        mutant.write_text(mutant.read_text()+"\nfrom llm_router._api.router import LLMRouter  # intentional architecture mutant\n")
        env=os.environ.copy()
        env["PYTHONPATH"]=f"{temp/'src'}:{temp}"
        completed=subprocess.run(
          [str(ROOT/".venv/bin/lint-imports"),"--no-cache"],
          cwd=temp,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT
        )
    detected=completed.returncode!=0 and "Private implementation must not depend on facade entrypoints BROKEN" in completed.stdout
    return {
      "engine":"Import Linter",
      "mode":"architecture negative-control injection",
      "baseline_kept":int(match.group(1)) if match else None,
      "baseline_broken":int(match.group(2)) if match else None,
      "generated":1,
      "detected":1 if detected else 0,
      "score":100.0 if detected else 0.0,
      "target":"llm_router._internal → llm_router._api.router forbidden edge",
      "native_metadata":True,
    }


def free_port():
    sock=socket.socket()
    try:
        sock.bind(("127.0.0.1",0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def probe_runtime_fault():
    binary=shutil.which("toxiproxy-server")
    if not binary:
        return {
          "engine":"Toxiproxy",
          "mode":"network fault injection",
          "available":False,
          "generated":0,"detected":0,"score":None,
          "reason":"toxiproxy-server is not installed",
        }
    import httpx

    from tests.llm_router.support.fault_server import (
        ScriptedHTTPServer,
        ScriptedResponse,
    )
    from tests.llm_router.support.workers.retry import (
        openai_chat_path,
        openai_success_response,
    )
    from tests.llm_router.support.workers.timeout import run_timeout_worker

    api_port=free_port()
    proxy_port=free_port()
    process=subprocess.Popen(
      [binary,"-host","127.0.0.1","-port",str(api_port)],
      stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT
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
              body=openai_success_response(text="unexpected success"),
            )
          ]
        }
        with ScriptedHTTPServer(port=0,routes=routes) as server:
            upstream=urllib.parse.urlparse(server.base_url)
            httpx.post(api+"/proxies",json={
              "name":"llm-router-provider",
              "listen":f"127.0.0.1:{proxy_port}",
              "upstream":f"{upstream.hostname}:{upstream.port}",
              "enabled":True,
            }).raise_for_status()
            httpx.post(api+"/proxies/llm-router-provider/toxics",json={
              "name":"provider-latency",
              "type":"latency",
              "stream":"downstream",
              "toxicity":1.0,
              "attributes":{"latency":1500,"jitter":0},
            }).raise_for_status()
            started=time.perf_counter()
            result=run_timeout_worker(
              scenario="terminal_timeout",
              server_base_url=f"http://127.0.0.1:{proxy_port}",
            )
            elapsed=round(time.perf_counter()-started,3)
            detected=(not result.ok and result.error_type=="TimeoutError")
            request_count=server.request_count("POST",path)
        return {
          "engine":"Toxiproxy",
          "engine_version":"2.12.0",
          "mode":"network fault injection",
          "available":True,
          "generated":1,
          "detected":1 if detected else 0,
          "score":100.0 if detected else 0.0,
          "target":"provider HTTP path",
          "faults":[{"family":"latency","latency_ms":1500,"detected":detected,"public_error":result.error_type,"elapsed_seconds":elapsed,"request_count":request_count}],
          "native_metadata":True,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


def probe_interface_faults():
    tests=[
      "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py::test_retryable_status_is_translated_to_provider_error",
      "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py::test_malformed_success_json_is_wrapped_as_provider_error",
      "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py::test_remote_disconnect_is_retryable_transport_failure",
    ]
    output=run_checked([shutil.which("uv") or "uv","run","pytest","-q",*tests,"--no-cov"])
    return {
      "engine":"pytest deterministic boundary challenges",
      "mode":"interface/protocol fault challenges",
      "generated":3,
      "detected":3,
      "score":100.0,
      "target":"TREQ_OPENAI_ADAPTER_BOUNDARY",
      "generic_mutator":False,
      "families":[
        {"family":"retryable HTTP status","detected":True},
        {"family":"malformed success payload","detected":True},
        {"family":"transport disconnect","detected":True},
      ],
      "note":"No machine-readable provider interface schema exists in llm-router today, so this layer is challenge-backed rather than generator-backed.",
      "pytest_output_tail":"\n".join(output.splitlines()[-5:]),
    }




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

def assurance_history_rows(contract_id=None):
    """Project the retained assurance snapshot registry into the DVC journal."""
    payload=json.loads(ASSURANCE_SNAPSHOTS_PATH.read_text())
    snapshots=list(payload.get("snapshots") or [])
    if contract_id:
        snapshots=[
          row for row in snapshots
          if row.get("contract_id")==contract_id and row.get("test_strength") is not None
        ]
        groups=[
          (
            str(row.get("checkpoint") or ""),
            str(row.get("captured_at") or ""),
            [row],
          )
          for row in snapshots
        ]
    else:
        by_checkpoint=defaultdict(list)
        captured_at={}
        for row in snapshots:
            if row.get("test_strength") is None:
                continue
            checkpoint=str(row.get("checkpoint") or "")
            by_checkpoint[checkpoint].append(row)
            captured_at[checkpoint]=max(
              str(row.get("captured_at") or ""),
              captured_at.get(checkpoint,""),
            )
        groups=[
          (checkpoint,captured_at.get(checkpoint,""),rows)
          for checkpoint,rows in by_checkpoint.items()
        ]
    projected=[]
    for checkpoint,captured_at,rows in groups:
        scores=[float(row["test_strength"]) for row in rows]
        if not scores:
            continue
        projected.append({
          "finished_at":captured_at,
          "run_id":checkpoint,
          "mode":"assurance-snapshot",
          "measured_contracts":len(scores),
          "mutation_sensitivity":round(sum(scores)/len(scores),1),
          "new_survivors":sum(int(row.get("new_survivors") or 0) for row in rows),
          "survivor_debt":sum(int(row.get("survivor_debt") or 0) for row in rows),
          "resolved_survivors":sum(int(row.get("resolved_survivors") or 0) for row in rows),
        })
    projected.sort(key=lambda row:(row["finished_at"],row["run_id"]))
    for index,row in enumerate(projected,1):
        row["step"]=index
    return projected


def build_dvc_assurance_history(rows,*,subdir=None,title="Assurance history · Test Strength",metric="mean requirement Test Strength for the contracts measured by each retained mutation campaign"):
    target_dir=ASSURANCE_HISTORY_DIR/(subdir or "")
    target_dir.mkdir(parents=True,exist_ok=True)
    csv_path=target_dir/"assurance-history.csv"
    header="step,finished_at,mode,measured_contracts,mutation_sensitivity,new_survivors,survivor_debt,resolved_survivors\n"
    body="".join(
      f'{row["step"]},{row["finished_at"]},{row["mode"]},{row["measured_contracts"]},{row["mutation_sensitivity"]},{row["new_survivors"]},{row["survivor_debt"]},{row["resolved_survivors"]}\n'
      for row in rows
    )
    csv_path.write_text(header+body)
    rel_dir="assurance-history"+(f"/{subdir}" if subdir else "")
    if os.environ.get("TERNFORGE_REUSE_DVC")=="1" and (target_dir/"index.html").exists():
        return {
          "tool":"DVC plots",
          "url":f"{rel_dir}/index.html",
          "csv_url":f"{rel_dir}/assurance-history.csv",
          "metric":metric,
          "rows":rows,
          "render_reused":True,
          "render_reuse_basis":"DVC/Vega-Lite artifact already exists and the retained mutation-only history rows are unchanged; P31 assurance snapshots are rendered separately.",
        }
    with tempfile.TemporaryDirectory(prefix="ternforge-dvc-") as temp_dir:
        temp=Path(temp_dir)
        run_checked(["git","init","-q"],cwd=temp)
        run_checked(["git","config","user.email","pilot@example.invalid"],cwd=temp)
        run_checked(["git","config","user.name","Ternforge pilot"],cwd=temp)
        run_checked([shutil.which("uvx") or "uvx","--from","dvc","dvc","init","-q"],cwd=temp)
        shutil.copy2(csv_path,temp/"assurance.csv")
        report_dir=temp/"report"
        run_checked([
          shutil.which("uvx") or "uvx","--from","dvc","dvc","plots","show","assurance.csv",
          "-t","simple",
          "-x","step","-y","mutation_sensitivity",
          "--title",title,
          "--x-label","Retained campaign",
          "--y-label","Mean Test Strength (%)",
          "-o",str(report_dir),
        ],cwd=temp)
        # DVC/Vega-Lite is the renderer; this only makes the standard report
        # responsive inside the Contract Evidence iframe instead of keeping
        # DVC's built-in fixed 300 px plot width.
        rendered=(report_dir/"index.html").read_text()
        rendered,replaced=re.subn(
          r'"width": 300, "height": 300',
          '"width": "container", "height": 300',
          rendered,count=1,
        )
        if replaced != 1:
            raise RuntimeError("DVC plot no longer exposes the expected fixed-size Vega-Lite width")
        rendered=rendered.replace(
          "</style>",
          ".vega-embed { width: 100%; max-width: 100%; }\n</style>",
          1,
        )
        # Prevent the standalone local DVC report from producing a spurious
        # /favicon.ico 404 in browser QA. The chart itself still comes from
        # DVC's standard Vega-Lite renderer.
        rendered=rendered.replace(
          "<head>",
          '<head>\n    <link rel="icon" href="data:,">',
          1,
        )
        (target_dir/"index.html").write_text(rendered)
    rel_dir="assurance-history"+(f"/{subdir}" if subdir else "")
    return {
      "tool":"DVC plots",
      "url":f"{rel_dir}/index.html",
      "csv_url":f"{rel_dir}/assurance-history.csv",
      "metric":metric,
      "rows":rows,
    }


def invalid_config_fault_probe_input_paths():
    """Return the current source set that can change specialized fault-probe meaning."""
    config_spec=CONTRACTS["REQ_INVALID_CONFIGURATION_ERRORS"]
    paths={
      "docs/requirements/configuration.md",
      "docs/verification-profiles/invalid-configuration.md",
      str(config_spec["source"]),
      "features/responses/public_contract.feature",
      "tests/llm_router/bdd/responses/test_public_contract.py",
      "tests/llm_router/unit/test_internal_config_validation.py",
      "tests/llm_router/integration/test_openai_compatible_adapter_fake_server.py",
      "tests/llm_router/support/fault_server.py",
      "tests/llm_router/support/workers/error_boundary.py",
      "tests/llm_router/support/workers/timeout.py",
      "pyproject.toml",
    }
    paths.update(str(nodeid).split("::",1)[0] for nodeid in config_spec["tests"])
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
      # Facts produced by another mutation-engine configuration (for example the
      # fixture-less lightweight runner) are not this probe's evidence.
      "engine":IMPL_FAULTS.engine_configuration(),
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
      and binding.get("engine")==current["engine"]
    )


def build_fault_model_facts():
    config_spec=CONTRACTS["REQ_INVALID_CONFIGURATION_ERRORS"]
    component_tests=[
      nodeid
      for nodeid in config_spec["tests"]
      if "/unit/test_internal_config_validation.py::" in nodeid
    ]
    system_tests=[
      "tests/llm_router/bdd/responses/test_public_contract.py::test_invalid_model_configuration_surfaces_as_a_configuration_error",
    ]
    cache_dir_value=str(os.environ.get("TERNFORGE_P29_PROBE_CACHE") or "").strip()
    cache_dir=Path(cache_dir_value) if cache_dir_value else None
    if cache_dir and (cache_dir/"config-unit.json").exists() and (cache_dir/"config-bdd.json").exists():
        component=gremlin_group_metrics(config_spec,component_tests,json.loads((cache_dir/"config-unit.json").read_text()))
        system=gremlin_group_metrics(config_spec,system_tests,json.loads((cache_dir/"config-bdd.json").read_text()))
    else:
        component=gremlin_group_probe(config_spec,component_tests)
        system=gremlin_group_probe(config_spec,system_tests)
    component_killed=set(component.pop("killed_ids"))
    system_killed=set(system.pop("killed_ids"))
    overlap={
      "corroborated":len(component_killed & system_killed),
      "component_only":len(component_killed-system_killed),
      "system_only":len(system_killed-component_killed),
      "detected_union":len(component_killed | system_killed),
      "mutant_universe":max(int(component["generated"]),int(system["generated"])),
    }
    overlap["undetected"]=overlap["mutant_universe"]-overlap["detected_union"]

    component_mutants={str(row.get("gremlin_id") or ""):row for row in component.get("mutants") or []}
    system_mutants={str(row.get("gremlin_id") or ""):row for row in system.get("mutants") or []}
    mutant_detail=[]
    for mutant_id in sorted(set(component_mutants)|set(system_mutants)):
        c_row=component_mutants.get(mutant_id) or {}
        s_row=system_mutants.get(mutant_id) or {}
        base=c_row or s_row
        mutant_detail.append({
          "gremlin_id":mutant_id,
          "line":int(base.get("line") or -1),
          "operator":str(base.get("operator") or "unknown"),
          "description":str(base.get("description") or ""),
          "component_reached":bool(c_row.get("reached")),
          "component_killed":bool(c_row.get("killed")),
          "component_covering_tests":list(c_row.get("covering_tests") or []),
          "component_killing_test":c_row.get("killing_test"),
          "system_reached":bool(s_row.get("reached")),
          "system_killed":bool(s_row.get("killed")),
          "system_covering_tests":list(s_row.get("covering_tests") or []),
          "system_killing_test":s_row.get("killing_test"),
        })

    component["implementation_reach"]=implementation_line_reach(config_spec,component_tests)
    system["implementation_reach"]=implementation_line_reach(config_spec,system_tests)
    implementation_reach=implementation_line_reach(config_spec,component_tests+system_tests)

    cached_gherkin=(cache_dir/"gherkin.json") if cache_dir else None
    gherkin=(
      gherkin_mutation_metrics(json.loads(cached_gherkin.read_text()))
      if cached_gherkin and cached_gherkin.exists()
      else probe_gherkin_mutation()
    )
    architecture=probe_architecture_fault()
    interface=probe_interface_faults()
    runtime=probe_runtime_fault()

    strength_fact=(STRENGTH.get("contracts") or {}).get("REQ_INVALID_CONFIGURATION_ERRORS") or {}
    triage=strength_fact.get("triage") or {}
    retained_mutmut={
      "metric":"covered_mutant_test_strength",
      "definition":"killed / (killed + survived) for mutmut valid mutants generated only on covered lines",
      "score":strength_fact.get("score"),
      "killed":int(strength_fact.get("killed") or 0),
      "survived":int(strength_fact.get("survived") or 0),
      "valid_mutants":int(strength_fact.get("valid_mutants") or 0),
      "new_survivors":int(triage.get("new_survivors") or 0),
      "existing_survivors":int(triage.get("existing_survivors") or 0),
      "resolved_survivors":int(triage.get("resolved_survivors") or 0),
      "suppressed_survivors":int(triage.get("suppressed_survivors") or 0),
      "unresolved_survivors":int(triage.get("unresolved_survivors") or 0),
      "survivor_examples":list(strength_fact.get("survivor_examples") or []),
      "survivors":list(triage.get("survivors") or []),
      "fresh":strength_fact.get("fresh"),
      "report_url":strength_fact.get("report_url"),
      "allure_url":strength_fact.get("allure_url"),
      "campaign_id":strength_fact.get("campaign_id"),
      "denominator_warning":"mutmut is configured mutate_only_covered_lines=true, so this Test Strength metric is not a full-scope Mutation Reach denominator.",
    }
    implementation={
      "engine":"pytest-gremlins + retained mutmut campaign",
      "mode":"implementation mutation",
      "generated":overlap["mutant_universe"],
      "detected":overlap["detected_union"],
      "score":round(100*overlap["detected_union"]/max(1,overlap["mutant_universe"]),1),
      "target":"REQ_INVALID_CONFIGURATION_ERRORS · validate_config",
      "native_metadata":True,
      "implementation_reach":implementation_reach,
      "overall_detection":round(100*overlap["detected_union"]/max(1,overlap["mutant_universe"]),1),
      "mutant_detail":mutant_detail,
      "retained_mutmut":retained_mutmut,
      "raw_facts_url":"assurance-fault-model-facts.json",
      "mutants_url":strength_fact.get("report_url"),
    }
    layers=[
      {"id":"specification","label":"Specification / model","kind":"mutation-engine",**gherkin},
      {"id":"architecture","label":"Architecture","kind":"negative-control",**architecture},
      {"id":"interface","label":"Interface / protocol","kind":"challenge-suite",**interface},
      {"id":"runtime","label":"Runtime / dependency","kind":"fault-injection-engine",**runtime},
      {"id":"implementation","label":"Implementation","kind":"mutation-engine",**implementation},
    ]
    history=build_dvc_assurance_history(
      assurance_history_rows(),
      metric="retained assurance-snapshot Test Strength across measured contracts",
    )
    contract_history=build_dvc_assurance_history(
      assurance_history_rows("REQ_INVALID_CONFIGURATION_ERRORS"),
      subdir="REQ_INVALID_CONFIGURATION_ERRORS",
      title="REQ_INVALID_CONFIGURATION_ERRORS · Test Strength history",
      metric="retained assurance-snapshot Test Strength for REQ_INVALID_CONFIGURATION_ERRORS",
    )
    rate_limit_history=build_dvc_assurance_history(
      assurance_history_rows("TREQ_RATE_LIMIT_STATE"),
      subdir="TREQ_RATE_LIMIT_STATE",
      title="TREQ_RATE_LIMIT_STATE · covered-mutant Test Strength history",
      metric="retained assurance-snapshot covered-mutant Test Strength for TREQ_RATE_LIMIT_STATE",
    )
    req_spec=probe_invalid_config_specification_fault()
    req_spec.update({
      "claim_section":"public error-category outcome",
      "expected_outcome":"ConfigurationError",
      "mutated_outcome":"ProviderError",
      "parser_validity":"Original and mutated feature text both parse successfully with the Cucumber Gherkin parser.",
      "execution_nodeid":system_tests[0],
      "execution_command":f"uv run pytest -q {system_tests[0]} --no-cov",
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
    implementation.update({
      "source_url":repo_blob_url(config_spec["source"]),
      "detector":"pytest-gremlins native operators + retained mutmut campaign",
      "expected_invariant":"Linked verification should execute the declared implementation scope and detect plausible implementation faults.",
    })
    requirement_layers={
      "specification":{"id":"specification","label":"Specification / model","kind":"scenario-mutation",**req_spec},
      "architecture":{"id":"architecture","label":"Architecture","kind":"negative-control",**req_arch},
      "interface":{"id":"interface","label":"Interface / protocol","kind":"isolation-challenge",**req_interface},
      "runtime":{"id":"runtime","label":"Runtime / dependency","kind":"fault-injection-isolation",**req_runtime},
      "implementation":{"id":"implementation","label":"Implementation","kind":"mutation-engine",**implementation},
    }
    payload={
      "schema_version":"ternforge-fault-model-coverage-p31-1",
      "generated_at":utc_now(),
      "head_sha":git_sha(),
      "obligation_semantics":"A ladder layer is covered only when a real generator/challenge mechanism has been executed against the pilot. Layer scores keep their own denominators and are never averaged into a confidence percentage.",
      "layers":layers,
      "contracts":{
        "REQ_INVALID_CONFIGURATION_ERRORS":{
          "binding":invalid_config_fault_probe_binding(),
          "engine":"pytest-gremlins",
          "scope":"src/llm_router/_internal/config/validation.py::validate_config",
          "mutant_universe":overlap["mutant_universe"],
          "groups":{
            "component_local":{
              "label":"Component · local",
              "system_reach":"component",
              "boundary_mode":"none",
              **component,
            },
            "system_local":{
              "label":"System · local",
              "system_reach":"system",
              "boundary_mode":"none",
              **system,
            },
          },
          "detection_overlap":overlap,
          "layers":requirement_layers,
          "history":contract_history,
        }
      },
      "history":history,
      "contract_histories":{
        "REQ_INVALID_CONFIGURATION_ERRORS":contract_history,
        "TREQ_RATE_LIMIT_STATE":rate_limit_history,
      },
      "known_limitations":[
        "The global interface/protocol pilot probe remains challenge-backed because llm-router has no machine-readable provider interface schema suitable for a generic interface mutator. REQ_INVALID_CONFIGURATION_ERRORS uses a stronger claim-specific boundary-isolation sentinel instead.",
        "Agentic Test Forge is validated for Scenario Outline Examples mutation, but REQ_INVALID_CONFIGURATION_ERRORS is a simple Scenario. Its claim-specific specification negative control is parsed by the official Cucumber Gherkin parser and executed by pytest-bdd; this distinction remains explicit.",
        "Older Assurance History rows contain retained mutation-campaign metrics only. P31 starts explicit multi-metric assurance snapshots/events without back-filling unavailable pre-P31 target/fault-model values.",
      ],
    }
    ASSURANCE_FACTS_PATH.write_text(json.dumps(payload,indent=2))
    shutil.rmtree(ROOT/"coverage",ignore_errors=True)
    return payload


def current_needs():
    payload=json.loads((ROOT/"docs/_build/html/needs.json").read_text())
    version=payload.get("current_version")
    if version not in (payload.get("versions") or {}):
        version=list((payload.get("versions") or {}).keys())[-1]
    return payload["versions"][version]["needs"]


def need_field(content,label):
    match=re.search(
      rf"\*\*{re.escape(label)}\.\*\*\s*(.*?)(?=\n\n\*\*|\Z)",
      str(content or ""),flags=re.DOTALL,
    )
    return " ".join(match.group(1).split()) if match else ""


def contract_assurance_model():
    needs=current_needs()
    depth_by_nodeid={row["nodeid"]:row for row in DEPTH.get("tests") or []}
    reach_order=list((DEPTH.get("classification") or {}).get("system_reach_order") or [])
    boundary_order=list((DEPTH.get("classification") or {}).get("boundary_mode_order") or [])
    rep_order=list((DEPTH.get("classification") or {}).get("representation_fidelity_order") or [])
    ms_order=list((DEPTH.get("classification") or {}).get("ms_validation_order") or [])
    fault_model=json.loads(ASSURANCE_FACTS_PATH.read_text()) if ASSURANCE_FACTS_PATH.exists() else {}
    targets=json.loads(ASSURANCE_TARGETS_PATH.read_text()) if ASSURANCE_TARGETS_PATH.exists() else {"profiles":{},"assignments":{}}

    def producer_info(producer_id):
        p=needs.get(producer_id) or {}
        return {
          "id":producer_id,
          "title":p.get("title") or producer_id,
          "url":"evidence-trust.html#evidence-trust-"+producer_id.lower().replace("_","-"),
          "role":p.get("producer_role"),
          "impact":p.get("producer_impact"),
          "qualified_by":list(p.get("qualified_by") or []),
          "calibrated_by":list(p.get("calibrated_by") or p.get("calibrates_back") or []),
          "residual_doubt":p.get("residual_doubt"),
        }

    contracts={}
    for contract_id,need in needs.items():
        if need.get("type") not in {"req","treq"}:
            continue
        direct=[]
        for evidence_id in need.get("verifies_back") or []:
            evidence_need=needs.get(evidence_id) or {}
            nodeid=evidence_need.get("nodeid")
            depth=depth_by_nodeid.get(nodeid)
            if not nodeid or not depth:
                continue
            producers=[producer_info(pid) for pid in evidence_need.get("produced_by") or []]
            source_path=depth.get("source_path") or nodeid.split("::",1)[0]
            narrative_anchor=evidence_id.replace("TEST_EVIDENCE","PYTEST_LOCAL_EVIDENCE",1)
            direct.append({
              "id":evidence_id,
              "title":depth.get("gherkin_scenario") or evidence_need.get("title") or nodeid.split("::")[-1],
              "nodeid":nodeid,
              "kind":depth.get("verification_kind"),
              "reach":depth.get("system_reach"),
              "reach_basis":depth.get("system_reach_basis"),
              "boundary":depth.get("boundary_mode"),
              "boundary_basis":depth.get("boundary_evidence_basis"),
              "representation":depth.get("representation_fidelity"),
              "representation_basis":depth.get("representation_basis"),
              "environment":depth.get("environment"),
              "environment_basis":depth.get("environment_basis"),
              "scenario_data":"not_classified",
              "scenario_data_basis":"No retained scenario/data representativeness field exists for this evidence path. Environment classification is kept separate and is not relabeled as scenario/data fidelity.",
              "ms_validation":depth.get("ms_validation"),
              "ms_validation_basis":depth.get("ms_validation_basis"),
              "model_producer":depth.get("model_producer"),
              "producers":producers,
              "source_path":source_path,
              "source_url":repo_blob_url(source_path),
              "narrative_url":f"local-pytest-evidence.html#{narrative_anchor}",
              "raw_url":f"ternforge-test-evidence.html#{evidence_id}",
              "allure_url":f"test-results/index.html?tags=TF_SCOPE__{contract_id}",
              "freshness":"not_timestamped",
              "freshness_basis":"Verification Depth retains the execution result but no per-path freshness timestamp; build time is not substituted for evidence freshness.",
            })
        direct.sort(key=lambda row:(
          reach_order.index(row["reach"]) if row["reach"] in reach_order else -1,
          boundary_order.index(row["boundary"]) if row["boundary"] in boundary_order else -1,
          row["kind"] or "",
          row["title"],
        ),reverse=True)
        children=[
          child for child in (need.get("derives_back") or [])
          if (needs.get(child) or {}).get("type") in {"req","treq"}
        ]
        strength=(STRENGTH.get("contracts") or {}).get(contract_id) or {}
        for evidence in direct:
            evidence["mutants_url"]=strength.get("report_url") if strength else None
            evidence["mutation_freshness"]=(
              "current" if strength.get("fresh") is True else
              "stale" if strength.get("fresh") is False else
              "not_measured"
            )
            evidence["mutation_freshness_basis"]=(
              "retained mutation campaign fingerprint is current" if strength.get("fresh") is True else
              "retained mutation campaign fingerprint is stale" if strength.get("fresh") is False else
              "no retained mutation campaign is attributed to this contract"
            )
        implementations=[
          {
            "id":impl_id,
            "title":(needs.get(impl_id) or {}).get("title") or impl_id,
            "url":f"ternforge-python-source-trace.html#{impl_id}",
          }
          for impl_id in (need.get("implements_back") or [])
        ]
        assignment=(targets.get("assignments") or {}).get(contract_id)
        profile=(targets.get("profiles") or {}).get((assignment or {}).get("profile")) if assignment else None
        target=(
          {
            **assignment,
            "profile_id":assignment.get("profile"),
            "profile_name":profile.get("name") if profile else assignment.get("profile"),
            "profile_revision":profile.get("revision") if profile else None,
            "profile_status":profile.get("status") if profile else None,
            "profile_source":profile.get("source") if profile else None,
            "profile_rationale":profile.get("rationale") if profile else None,
            "cadence":(profile or {}).get("cadence"),
            "freshness":(profile or {}).get("freshness"),
            "optional_improvements":list((profile or {}).get("optional_improvements") or []),
            "obligations":list((profile or {}).get("obligations") or []),
          }
          if assignment else None
        )
        contracts[contract_id]={
          "id":contract_id,
          "title":need.get("title") or contract_id,
          "type":need.get("type"),
          "revision":need.get("revision"),
          "statement":need_field(need.get("content"),"Statement"),
          "rationale":need_field(need.get("content"),"Rationale"),
          "verification_intent":need_field(need.get("content"),"Verification intent"),
          "contract_url":f"{need.get('docname')}.html#{contract_id}" if need.get("docname") else f"traceability-reader.html#review-{contract_id}",
          "implementations":implementations,
          "direct":direct,
          "children":children,
          "target":target,
          "strength":{
            "score":strength.get("score"),
            "killed":strength.get("killed"),
            "survived":strength.get("survived"),
            "valid_mutants":strength.get("valid_mutants"),
            "fresh":strength.get("fresh"),
            "report_url":strength.get("report_url"),
            "allure_url":strength.get("allure_url"),
            "campaign_id":strength.get("campaign_id"),
            "triage":{
              "new_survivors":int((strength.get("triage") or {}).get("new_survivors") or 0),
              "existing_survivors":int((strength.get("triage") or {}).get("existing_survivors") or 0),
              "resolved_survivors":int((strength.get("triage") or {}).get("resolved_survivors") or 0),
              "suppressed_survivors":int((strength.get("triage") or {}).get("suppressed_survivors") or 0),
              "unresolved_survivors":int((strength.get("triage") or {}).get("unresolved_survivors") or 0),
            },
          } if strength else None,
        }

    def descendants(root_id):
        seen=set()
        stack=list((needs.get(root_id) or {}).get("derives_back") or [])
        while stack:
            child=stack.pop()
            if child in seen:
                continue
            seen.add(child)
            node=needs.get(child) or {}
            stack.extend(node.get("derives_back") or [])
        return sorted(
          cid for cid in seen
          if (needs.get(cid) or {}).get("type") in {"req","treq"}
        )

    goals=[]
    for goal_id,goal in needs.items():
        if goal.get("type")!="goal":
            continue
        features=[]
        for feature_id in goal.get("derives_back") or []:
            feature=needs.get(feature_id) or {}
            if feature.get("type")!="feature":
                continue
            features.append({
              "id":feature_id,
              "title":feature.get("title") or feature_id,
              "contracts":descendants(feature_id),
            })
        goals.append({
          "id":goal_id,
          "title":goal.get("title") or goal_id,
          "contracts":descendants(goal_id),
          "features":features,
        })
    goals.sort(key=lambda row:row["title"])
    return {
      "schema_version":"p33-local-1",
      "reach_order":reach_order,
      "boundary_order":boundary_order,
      "representation_order":rep_order,
      "ms_validation_order":ms_order,
      "contracts":contracts,
      "goals":goals,
      "fault_model":fault_model,
      "target_schema_version":targets.get("schema_version"),
    }


def evaluate_assurance_obligation(model,contract,obligation):
    rows=contract.get("direct") or []
    fault=((model.get("fault_model") or {}).get("contracts") or {}).get(contract["id"]) or {}
    kind=obligation.get("kind")
    if kind=="frontier_cell":
        matching=[
          row for row in rows
          if row.get("reach")==obligation.get("reach") and row.get("boundary")==obligation.get("boundary")
        ]
        rep_order=model.get("representation_order") or []
        target_rep=obligation.get("representation_min")
        def rep_rank(value):
            try:
                return rep_order.index(value)
            except ValueError:
                return -1
        rep_ok=not target_rep or any(rep_rank(row.get("representation"))>=rep_rank(target_rep) for row in matching)
        strongest=max((row.get("representation") for row in matching),key=rep_rank,default=None)
        return {
          "met":bool(matching and rep_ok),
          "actual":f"{len(matching)} path(s) · strongest representation {strongest or 'n/a'}" if matching else "0 matching paths",
          "value":len(matching),
          "evidence_ids":[row.get("id") for row in matching],
        }
    if kind=="method_count":
        methods=sorted({row.get("kind") for row in rows if row.get("kind")})
        minimum=int(obligation.get("min") or 0)
        return {"met":len(methods)>=minimum,"actual":f"{len(methods)} method type(s)","value":len(methods),"methods":methods}
    if kind in {"mutation_reach","mutation_sensitivity"}:
        group=(fault.get("groups") or {}).get(obligation.get("group")) or {}
        key="mutation_reach" if kind=="mutation_reach" else "sensitivity"
        value=group.get(key)
        minimum=float(obligation.get("min") or 0)
        return {"met":value is not None and float(value)>=minimum,"actual":None if value is None else float(value),"value":value}
    if kind=="test_strength":
        value=(contract.get("strength") or {}).get("score")
        minimum=float(obligation.get("min") or 0)
        return {"met":value is not None and float(value)>=minimum,"actual":value,"value":value}
    if kind=="fault_layer":
        layer=(fault.get("layers") or {}).get(obligation.get("layer")) or {}
        generated=int(layer.get("generated") or 0)
        detected=int(layer.get("detected") or 0)
        return {
          "met":generated>0 and detected>0,
          "actual":f"{detected}/{generated} detected" if generated else "not exercised",
          "value":detected,
        }
    return {"met":False,"actual":"unsupported obligation type","value":None}


def build_assurance_snapshot_history(model):
    existing={
      "schema_version":"ternforge-assurance-history-p31-1",
      "history_starts_at_checkpoint":"p31-local-1",
      "note":"Assurance snapshots start at P31. Older retained DVC mutation history is preserved separately and is not back-filled with unavailable Target/fault-model dimensions.",
      "snapshots":[],
    }
    if ASSURANCE_SNAPSHOTS_PATH.exists():
        try:
            loaded=json.loads(ASSURANCE_SNAPSHOTS_PATH.read_text())
            if loaded.get("schema_version")==existing["schema_version"]:
                existing=loaded
        except Exception:
            pass

    snapshots=list(existing.get("snapshots") or [])
    fault_model=model.get("fault_model") or {}
    for contract_id,contract in sorted((model.get("contracts") or {}).items()):
        target=contract.get("target")
        if not target:
            continue
        obligations=list(target.get("obligations") or [])
        evaluated: list[dict[str, Any]]=[
          {
            "id":obligation.get("id"),
            "label":obligation.get("label"),
            "kind":obligation.get("kind"),
            "blocking":obligation.get("blocking") is not False,
            "target":obligation,
            "result":evaluate_assurance_obligation(model,contract,obligation),
          }
          for obligation in obligations
        ]
        blocking=[row for row in evaluated if row["blocking"]]
        gaps=[row for row in blocking if not row["result"]["met"]]
        fact=((fault_model.get("contracts") or {}).get(contract_id) or {})
        groups=fact.get("groups") or {}
        component=groups.get("component_local") or {}
        system=groups.get("system_local") or {}
        strength=contract.get("strength") or {}
        triage=strength.get("triage") or {}
        layers=fact.get("layers") or {}
        content={
          "contract_id":contract_id,
          "head_sha":git_sha(),
          "checkpoint":PROTOTYPE_BUILD_VERSION,
          "target_profile":target.get("profile_id"),
          "target_revision":target.get("target_revision"),
          "requirement_revision":contract.get("revision"),
          "obligations_met":len(blocking)-len(gaps),
          "obligations_total":len(blocking),
          "blocking_gap_ids":[row["id"] for row in gaps],
          "blocking_gap_labels":[row["label"] for row in gaps],
          "component_mutation_reach":component.get("mutation_reach"),
          "component_mutation_sensitivity":component.get("sensitivity"),
          "system_mutation_reach":system.get("mutation_reach"),
          "system_mutation_sensitivity":system.get("sensitivity"),
          "test_strength":strength.get("score"),
          "new_survivors":triage.get("new_survivors"),
          "survivor_debt":triage.get("existing_survivors"),
          "resolved_survivors":triage.get("resolved_survivors"),
          "fault_layers_detected":sum(1 for row in layers.values() if int(row.get("detected") or 0)>0),
          "fault_layers_total":len(layers),
          "target_source":target.get("source"),
          "target_rationale":target.get("rationale"),
          "issue_links":list(target.get("issue_links") or []),
          "overrides":list(target.get("overrides") or []),
        }
        fingerprint=sha256_text(stable_json(content))
        prior=[row for row in snapshots if row.get("contract_id")==contract_id]
        previous=prior[-1] if prior else None
        if previous and previous.get("fingerprint")==fingerprint:
            continue
        previous_gaps=set((previous or {}).get("blocking_gap_ids") or [])
        current_gaps=set(content["blocking_gap_ids"])
        events=[]
        if previous is None:
            events.append({
              "type":"history_started",
              "detail":"Assurance snapshot retention starts at P31; pre-P31 assurance dimensions are not back-filled.",
            })
            for gap in sorted(current_gaps):
                events.append({"type":"gap_present_at_history_start","obligation_id":gap})
        else:
            if previous.get("target_revision")!=content["target_revision"] or previous.get("target_profile")!=content["target_profile"]:
                events.append({
                  "type":"target_revision",
                  "from_profile":previous.get("target_profile"),
                  "from_revision":previous.get("target_revision"),
                  "to_profile":content["target_profile"],
                  "to_revision":content["target_revision"],
                  "rationale":content["target_rationale"],
                })
            for gap in sorted(current_gaps-previous_gaps):
                events.append({"type":"gap_opened","obligation_id":gap})
            for gap in sorted(previous_gaps-current_gaps):
                events.append({"type":"gap_closed","obligation_id":gap})
        snapshot={**content,"fingerprint":fingerprint,"captured_at":utc_now(),"events":events}
        snapshots.append(snapshot)

    existing["snapshots"]=snapshots
    ASSURANCE_SNAPSHOTS_PATH.write_text(json.dumps(existing,indent=2))
    generated=ROOT/"docs/_build/html/assurance-snapshots.json"
    generated.write_text(json.dumps(existing,indent=2))
    return existing


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
    for row in markdown_table_after(text,"#### Fault-class semantics"):
        ids=re.findall(r"\x60([^\x60]+)\x60",row.get("Fault class",""))
        for class_id in ids:
            fault_class_descriptions[class_id]=row.get("Meaning","")
    fault_groups=[]
    for row in markdown_table_after(text,"### Fault-based testing"):
        ids=re.findall(r"\x60([^\x60]+)\x60",row.get("Fault classes",""))
        fault_groups.append({
          "label":row.get("Group",""),
          "classes":ids,
          "descriptions":{class_id:fault_class_descriptions.get(class_id,"") for class_id in ids},
        })
    return {
      "mutation_reach_floor":thresholds.get("Mutation Reach floor"),
      "mutation_sensitivity_floor":thresholds.get("Mutation Sensitivity floor"),
      "freshness_rule":decision_values.get("Evidence freshness"),
      "fault_class_descriptions":fault_class_descriptions,
      "fault_groups":fault_groups,
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

    mutation={}
    for row in markdown_table_after(section,"### Blocking mutation checks"):
        level_label=row.get("Test level","").strip()
        level=level_keys.get(level_label)
        if not level:
            raise RuntimeError(
              f"{contract_id}: Blocking mutation checks has unknown Test level {level_label!r}"
            )
        checks=row.get("Required checks","")
        known=("Mutation Reach" in checks,"Mutation Sensitivity" in checks)
        if not any(known):
            raise RuntimeError(
              f"{contract_id}: Blocking mutation checks row declares no recognized check"
            )
        mutation[level]={
          "reach":known[0],
          "sensitivity":known[1],
        }
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
      "mutation":mutation,
    }


def verification_criterion_targets():
    policy=project_monitor_policy()
    result={}
    for contract_id in verification_profile_contract_ids():
        target=requirement_monitor_target(contract_id,policy)
        if not target:
            continue
        for cell in target.get("coverage") or []:
            for criterion_id in cell.get("items") or []:
                if criterion_id in result:
                    raise RuntimeError(f"verification criterion appears in multiple target cells: {criterion_id}")
                result[criterion_id]={
                  "profile_contract_id":contract_id,
                  "level":cell.get("level"),
                  "boundary":cell.get("boundary"),
                  "representation":cell.get("representation"),
                  "ms_validation_target":cell.get("ms_validation_target"),
                }
    return result


def local_pytest_evidence_url(test_name):
    path=ROOT/"docs/_build/html/local-pytest-evidence.html"
    if not path.exists():
        return "local-pytest-evidence.html"
    text=path.read_text()
    index=text.find(f">{test_name}<")
    if index<0:
        index=text.find(test_name)
    if index<0:
        return "local-pytest-evidence.html"
    prefix=text[max(0,index-2600):index]
    ids=re.findall(r'id="(PYTEST_LOCAL_EVIDENCE_[A-Z0-9_]+)"',prefix)
    return f"local-pytest-evidence.html#{ids[-1]}" if ids else "local-pytest-evidence.html"


def package_version_or_unknown(name):
    try:
        return package_version(name)
    except Exception:
        return "UNKNOWN"


def current_evidence_qualification_environment():
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
      "assurance_adapter_sha256":sha256_file(ROOT/".ai-bridge/build-mutation-report-prototype.py"),
      "requirement_monitor_sha256":sha256_file(ROOT/".ai-bridge/build-requirement-monitor.py"),
      "upper_assurance_monitor_sha256":sha256_file(ROOT/".ai-bridge/build-upper-assurance-pilot.py"),
      "assurance_monitor_domain_sha256":sha256_file(ROOT/".ai-bridge/assurance_monitor_domain.py"),
      "assurance_monitor_registry_sha256":sha256_file(ROOT/".ai-bridge/assurance_monitor_registry.py"),
      "implementation_faults_sha256":sha256_file(ROOT/".ai-bridge/implementation_faults.py"),
      "qualification_harness_sha256":sha256_file(ROOT/".ai-bridge/qualify-evidence-confidence.py"),
      "trace_bridge_sha256":sha256_file(ROOT/"tests/conftest.py"),
    }


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


CORE_EXECUTION_PRODUCERS={
  "PRODUCER_PYTEST",
  "PRODUCER_PY_TESTKIT",
  "PRODUCER_ALLURE",
  "PRODUCER_PYTEST_BDD",
  "PRODUCER_HYPOTHESIS",
}


def boundary_from_current_evidence(nodeid,allure_row,target_boundary,fallback=None,fallback_basis=None):
    observations=(allure_row or {}).get("observations") or []
    for observation in observations:
        if observation.get("kind")!="boundary-interaction-check":
            continue
        payload=observation.get("payload") or {}
        if payload.get("boundary")!="provider-http":
            continue
        requests=payload.get("requests_received")
        if isinstance(requests,int):
            if requests==0:
                return "none","current retained provider-boundary observation recorded zero HTTP requests",True
            return "substitute",f"current retained provider-boundary observation recorded {requests} HTTP request(s)",True
    external_producers=set((allure_row or {}).get("producer_ids") or [])-CORE_EXECUTION_PRODUCERS
    external_observations={
      observation.get("kind")
      for observation in observations
      if observation.get("kind") in {"external-substitute","external-replay","external-direct"}
    }
    if target_boundary=="none" and not external_producers and not external_observations:
        return "none","current retained producer chain contains no material external participant",True
    return target_boundary or fallback,fallback_basis or "current retained evidence does not prove the declared boundary mode",False


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


def current_reach_for_target(nodeid,verification_kind,target_level,boundary):
    files=current_context_files(nodeid)
    product=[path for path in files if path.startswith("src/llm_router/")]
    has_api=any(path.startswith("src/llm_router/_api/") for path in product)
    has_runtime=any(path.startswith("src/llm_router/_internal/runtime/") for path in product)
    has_provider=any(path.startswith("src/llm_router/_internal/providers/") for path in product)
    if not product:
        return target_level,"current coverage contains no llm-router production code for this testcase",False
    if target_level=="component":
        current=verification_kind in {"unit","property"} and boundary=="none"
        basis="declared Component criterion is backed by current unit/property execution of llm-router code with no material external boundary"
    elif target_level=="component_integration":
        current=verification_kind=="integration" and boundary=="none"
        basis="declared Component Integration criterion is backed by current integration execution without an external-system boundary"
    elif target_level=="system":
        current=verification_kind=="bdd" and has_api and has_runtime and boundary=="none"
        basis="declared System criterion is backed by current public API plus runtime execution with no material external boundary"
    elif target_level=="system_integration":
        current=(
          verification_kind in {"bdd","integration"}
          and has_api and has_runtime and has_provider
          and boundary in {"substitute","replay","direct"}
        )
        basis="declared System Integration criterion is backed by current public API, runtime, provider-adapter and observed external-boundary execution"
    else:
        current=False
        basis=f"current pilot has no execution rule for declared Test level {target_level or 'UNKNOWN'}"
    return target_level,basis,current


def current_representation_from_boundary(boundary,boundary_current,target_representation):
    if not boundary_current:
        return "unknown","representation cannot be established until the current boundary mode is proven",False
    if boundary in {"substitute","replay"}:
        actual="surrogate_simulated"
        basis="current evidence uses a material substitute/replay external participant, so Representation is Surrogate / simulated"
    elif boundary in {"none","direct"}:
        actual="actual"
        basis="current evidence uses actual llm-router code without a material surrogate representation"
    else:
        return "unknown","current boundary mode does not establish Representation",False
    return actual,basis,actual==target_representation




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
          "evidence_url":local_pytest_evidence_url(test_name),
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
              "evidence_url":local_pytest_evidence_url(test_name),
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
    needs=current_needs()
    scopes=IMPL_FAULTS.resolve_impl_scopes(ROOT,needs)
    owners=IMPL_FAULTS.line_owners(scopes)
    descendants=IMPL_FAULTS.descendants_map(needs)
    test_rows=junit_depth_rows() if test_rows is None else test_rows
    return {
      contract_id:IMPL_FAULTS.contract_plan(contract_id,scopes,owners,descendants,test_rows)
      for contract_id,need in sorted(needs.items())
      if need.get("type") in {"req","treq"}
    }


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

    for index,contract_id in enumerate(selected,1):
        plan=plans[contract_id]
        raw_path=IMPL_FAULT_DIR/f"{contract_id}.gremlins.json"
        raw_path.unlink(missing_ok=True)
        run=IMPL_FAULTS.run_engine(ROOT,plan,raw_path)
        contracts[contract_id]={
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
        print(f"[IMPL] {index}/{len(selected)} {contract_id}: exit {run['returncode']} in {run['duration_seconds']}s",flush=True)
        write_campaign()
    write_campaign()
    print(f"[IMPL] campaign finished in {round(time.monotonic()-started,1)}s",flush=True)


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
                classes=IMPL_FAULTS.project_classes(plan,json.loads((ROOT/run["report_path"]).read_text()),ROOT)
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


def requirement_monitor_model(base_model):
    policy=project_monitor_policy()
    junit_actual=junit_monitor_actual()
    junit_faults=junit_fault_actual(policy)
    implementation_faults=implementation_fault_actual()
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
        groups=list((contract_fault.get("groups") or {}).values())
        layers=contract_fault.get("layers") or {}
        implementation=layers.get("implementation") or {}
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
            "groups":contract_fault.get("groups") or {},
            "layers":layers,
            "detection_overlap":contract_fault.get("detection_overlap") or {},
            "retained_mutmut":implementation.get("retained_mutmut") or {},
            "retained_challenges":retained_classes,
            "raw_url":"requirement-monitor-facts.json",
          },
          "history_url":((fault_model.get("contract_histories") or {}).get(contract_id) or {}).get("url"),
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
            if binding.get("assurance_item") or binding.get("fault_challenge"):
                continue
            if criterion_owner.get(binding.get("coverage_item") or ""):
                continue
            linked.append({"nodeid":row["nodeid"],"result":row.get("result")})
        contract["linked_outside_profile"]=linked
    return result



def patch_contract_evidence_view():
    if not ASSURANCE_PAGE.exists():
        return
    if ASSURANCE_TARGETS_PATH.exists():
        shutil.copy2(ASSURANCE_TARGETS_PATH,ROOT/"docs/_build/html/assurance-targets.json")
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
    model=contract_assurance_model()
    model["assurance_snapshots"]=(
        json.loads(ASSURANCE_SNAPSHOTS_PATH.read_text())
        if ASSURANCE_SNAPSHOTS_PATH.exists()
        else {}
    )
    monitor_model=requirement_monitor_model(model)
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
          'Execution health stays in Health; verification depth stays in Depth; mutation changes stay in Mutation Analysis.</p>',
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
      ROOT/"docs/_build/html/verification-health-map.html":None,
      DEPTH_PAGE:"depth",
      ASSURANCE_PAGE:None,
      MUTATION_PAGE:"mutation",
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


def integrate_mutation_portal(summary,feedback):
    ensure_root_favicon()
    if not MTE_VENDOR_PATH.exists():
        raise RuntimeError("pinned Mutation Testing Elements 3.9.0 asset is missing")
    mte_bytes=gzip.decompress(MTE_VENDOR_PATH.read_bytes())
    if hashlib.sha256(mte_bytes).hexdigest()!=MTE_VENDOR_SHA256:
        raise RuntimeError("pinned Mutation Testing Elements 3.9.0 asset digest mismatch")
    mte_target=ROOT/"docs/_build/html/_static/mutation-test-elements.js"
    mte_target.parent.mkdir(parents=True,exist_ok=True)
    mte_target.write_bytes(mte_bytes)
    if ASSURANCE_SNAPSHOTS_PATH.exists():
        (ROOT/"docs/_build/html/assurance-snapshots.json").write_bytes(
          ASSURANCE_SNAPSHOTS_PATH.read_bytes()
        )
    write_mutation_analysis_page(summary,feedback)
    patch_contract_evidence_view()
    subprocess.run(
      [sys.executable,str(ROOT/".ai-bridge/build-requirement-monitor.py")],
      cwd=ROOT,check=True,
    )
    subprocess.run(
      [sys.executable,str(ROOT/".ai-bridge/build-upper-assurance-pilot.py")],
      cwd=ROOT,check=True,
    )
    health_payload=render_health_map_page()
    render_depth_map_page(health_payload)
    patch_traceability_contract_evidence_links()
    patch_verification_contract_evidence_path()
    patch_evidence_trust_need_anchors()
    patch_living_semantic_pages()
    patch_legacy_overview_links()
    patch_portal_navigation()

def refresh_freshness(campaign):
    selected_ids=list(campaign.get("contracts") or {})
    retained_mutmut_version=(campaign.get("engine") or {}).get("version")
    current=build_campaign_inputs(
      campaign["mode"],campaign.get("base_sha"),selected_ids,retained_mutmut_version
    )
    allure_ids=allure_report_ids()

    # A new campaign owns only the contracts it actually measured. Other contracts
    # keep their previous campaign provenance and are freshness-checked independently.
    for contract_id in selected_ids:
        recorded=campaign["contracts"][contract_id]
        fact=STRENGTH["contracts"][contract_id]
        contract_baseline_run_id=recorded.get("baseline_run_id") or campaign.get("baseline_run_id")
        contract_baseline=load_run(contract_baseline_run_id)
        fact.update({
          "campaign_id":campaign["campaign_id"],
          "run_id":campaign.get("run_id"),
          "campaign_mode":campaign["mode"],
          "campaign_head_sha":campaign["head_sha"],
          "baseline_run_id":contract_baseline_run_id,
          "baseline_campaign_id":(contract_baseline or {}).get("campaign_id"),
          "campaign_provenance_url":"../campaign.json",
          "source_fingerprint":recorded["source_fingerprint"],
          "test_set_fingerprint":recorded["test_set_fingerprint"],
          "config_fingerprint":recorded["config_fingerprint"],
        })

    for contract_id,spec in CONTRACTS.items():
        fact=STRENGTH["contracts"][contract_id]
        current_fp=contract_fingerprints(
          contract_id,spec,retained_mutmut_version
        )
        recorded={
          "source_fingerprint":fact.get("source_fingerprint"),
          "test_set_fingerprint":fact.get("test_set_fingerprint"),
          "config_fingerprint":fact.get("config_fingerprint"),
        }
        fresh,reasons=freshness_state(recorded,current_fp)
        fact["fresh"]=fresh
        fact["stale_reasons"]=reasons
        if contract_id in campaign["contracts"]:
            campaign_record=campaign["contracts"][contract_id]
            campaign_record["fresh"]=fresh
            campaign_record["stale_reasons"]=reasons
            campaign_record["current_fingerprints"]=current_fp
        write_wrapper(contract_id,spec,allure_ids,fact)

    campaign["current_check"]={
      "checked_at":utc_now(),
      "head_sha":git_sha(),
      "coverage_run_fingerprint":sha256_file(COVERAGE_DB),
      "allure_run_fingerprint":relevant_allure_run_fingerprint(),
      "fresh":all(bool(campaign["contracts"][cid].get("fresh")) for cid in selected_ids),
    }
    depth_payload=refresh_verification_depth_facts()
    print(
      f"[P34] depth facts: {len(depth_payload.get('tests') or [])} tests · "
      f"{len(depth_payload.get('contracts') or [])} contracts · "
      f"{(depth_payload.get('audit') or {}).get('nodeid_mismatches',0)} nodeid mismatches",
      flush=True,
    )
    summary=build_summary(campaign)
    feedback=build_operator_feedback(campaign)
    summary["operator_feedback"]={
      "families":len(feedback.get("families") or []),
      "sample":feedback.get("sample") or {},
      "filtering_decision":feedback.get("filtering_decision") or {},
    }
    triage_payload={
      "schema_version":"ternforge-mutation-triage-prototype-2",
      "campaign_id":campaign["campaign_id"],
      "run_id":campaign.get("run_id"),
      "baseline_run_id":campaign.get("baseline_run_id"),
      "baseline_campaign_id":campaign.get("baseline_campaign_id"),
      "readiness":summary["readiness"],
      "new_unresolved_survivors":summary["new_unresolved_survivors"],
      "unresolved_survivors":summary["unresolved_survivors"],
      "suppressed_survivors":summary["suppressed_survivors"],
      "resolved_survivors":summary["resolved_survivors"],
      "actionable_contracts":summary["actionable_contracts"],
      "suppression_ledger":load_suppressions(),
      "contracts":{
        contract_id:(STRENGTH["contracts"][contract_id].get("triage") or {})
        for contract_id in CONTRACTS
      },
    }
    STRENGTH["schema_version"]="verification-test-strength-spike-5"
    STRENGTH["campaign"]={
      "campaign_id":campaign["campaign_id"],
      "run_id":campaign.get("run_id"),
      "baseline_run_id":campaign.get("baseline_run_id"),
      "baseline_campaign_id":campaign.get("baseline_campaign_id"),
      "mode":campaign["mode"],
      "head_sha":campaign["head_sha"],
      "current_head_sha":git_sha(),
      "selected_contracts":selected_ids,
      "skipped_contracts":campaign.get("skipped_contracts") or [],
    }
    STRENGTH["summary"]=summary
    STRENGTH_PATH.write_text(json.dumps(STRENGTH,indent=2))
    SUMMARY_PATH.write_text(json.dumps(summary,indent=2))
    TRIAGE_PATH.write_text(json.dumps(triage_payload,indent=2))
    OPERATOR_FEEDBACK_PATH.write_text(json.dumps(feedback,indent=2))
    campaign["adapter"]={
      "name":"ternforge-local-mutmut-report-adapter",
      "version":MUTATION_ADAPTER_VERSION,
      "mutation_semantics_version":MUTATION_SEMANTICS_VERSION,
    }
    CAMPAIGN_PATH.write_text(json.dumps(campaign,indent=2))
    regenerate_verification_maps()
    integrate_mutation_portal(summary,feedback)
    return summary

def build_contract(contract_id,spec,campaign):
    phase="P23"
    contract_started=time.monotonic()
    print(f"[{phase}] running {contract_id}",flush=True)
    run_mutmut(spec)
    from mutmut.__main__ import status_by_exit_code  # ty: ignore[unresolved-import]
    from mutmut.mutation.data import (  # ty: ignore[unresolved-import]
        SourceFileMutationData,
    )
    source_rel=spec["source"]
    source=ROOT/source_rel
    line_coverage=coverage_by_test(spec)
    data=SourceFileMutationData(path=source_rel)
    data.load()
    mutants=[]
    for name,exit_code in data.exit_code_by_key.items():
        if not scope_matches(name,spec):
            continue
        raw=str(status_by_exit_code[exit_code])
        location,description,replacement=mutant_detail(source,name)
        line=int(location["start"]["line"])
        covered=[nodeid for nodeid,lines in line_coverage.items() if line in lines]
        mutant={
          "id":name,
          "mutatorName":"mutmut",
          "location":location,
          "status":STATUS.get(raw,"RuntimeError"),
          "description":description,
          "replacement":replacement}
        if covered:
            mutant["coveredBy"]=covered
        mutants.append(mutant)
    if not mutants:
        raise RuntimeError(
          f"{contract_id}: mutation engine produced no mutants for required scope "
          f"{spec['kind']} {spec['scope']}"
        )
    records=[mutant_record(contract_id,spec,mutant) for mutant in mutants]
    killed=sum(m["status"]=="Killed" for m in mutants)
    survived=sum(m["status"]=="Survived" for m in mutants)
    valid=killed+survived
    score=round(100*killed/valid,1) if valid else None
    state=("high" if score is not None and score>=80 else
           "moderate" if score is not None and score>=60 else
           "low" if score is not None else "na")
    report={
      "schemaVersion":"2.0",
      "thresholds":{"low":60,"high":80},
      "framework":{"name":"mutmut"},
      "config":{
        "ternforgeContract":contract_id,
        "scopeRule":"linked pytest coverage + uniquely attributable @impl owner",
        "implementationScope":f"{spec['kind']} {spec['scope']}"},
      "files":{source_rel:{
        "language":"python",
        "source":source.read_text(),
        "mutants":mutants}},
      "testFiles":report_test_files(spec)}
    out=OUT/contract_id
    out.mkdir(parents=True,exist_ok=True)
    (out/"mutation-report.json").write_text(json.dumps(report,indent=2))
    STRENGTH["contracts"][contract_id].update({
      "score":score,
      "state":state,
      "killed":killed,
      "survived":survived,
      "valid_mutants":valid,
      "report_url":f"mutation-results/{contract_id}/index.html",
      "allure_url":f"test-results/index.html?tags=TF_SCOPE__{contract_id}",
      "report_schema":"Mutation Testing Report Schema 2.0",
      "report_ui":"Mutation Testing Elements 3.9.0"})
    campaign["contracts"][contract_id]["result"]={
      "score":score,
      "state":state,
      "killed":killed,
      "survived":survived,
      "valid_mutants":valid,
      "total_scoped_mutants":len(mutants),
      "report_path":f"mutation-results/{contract_id}/mutation-report.json",
      "mutants":records,
      "duration_seconds":round(time.monotonic()-contract_started,3),
    }
    print(f"[{phase}] {contract_id}: {killed} killed / {survived} survived = {score}% ; {len(mutants)} scoped mutants",flush=True)

def new_campaign(mode,base_ref):
    if mode=="diff":
        selection=resolve_diff_scope(base_ref)
    else:
        selection={
          cid:{
            "selected":True,
            "reasons":["full_audit"],
            "changed_source_lines":[],
            "changed_linked_tests":[],
          }
          for cid in CONTRACTS
        }
    selected_ids=[cid for cid,row in selection.items() if row["selected"]]
    skipped_ids=[cid for cid,row in selection.items() if not row["selected"]]
    inputs=build_campaign_inputs(mode,base_ref,selected_ids)
    started_at=utc_now()
    run_id=f"{inputs['campaign_id']}--{time.time_ns()}"
    contract_baselines={
      contract_id:(
        STRENGTH["contracts"][contract_id].get("run_id")
        or STRENGTH["contracts"][contract_id].get("campaign_id")
      )
      for contract_id in selected_ids
    }
    baseline_run_id=archive_previous_run(run_id)
    baseline_doc=load_run(baseline_run_id)
    baseline_campaign_id=(baseline_doc or {}).get("campaign_id")
    contracts={}
    for contract_id in selected_ids:
        spec=CONTRACTS[contract_id]
        contracts[contract_id]={
          "source_path":spec["source"],
          "scope_kind":spec["kind"],
          "scope":spec["scope"],
          "linked_tests":list(spec["tests"]),
          "selection":selection[contract_id],
          "baseline_run_id":contract_baselines.get(contract_id) or baseline_run_id,
          **inputs["contracts"][contract_id],
        }
    return {
      "schema_version":"ternforge-mutation-campaign-prototype-4",
      "campaign_id":inputs["campaign_id"],
      "run_id":run_id,
      "baseline_run_id":baseline_run_id,
      "baseline_campaign_id":baseline_campaign_id,
      "mode":mode,
      "head_sha":inputs["head_sha"],
      "base_sha":inputs["base_sha"],
      "selected_contracts":selected_ids,
      "skipped_contracts":skipped_ids,
      "scope_resolution":selection,
      "started_at":started_at,
      "finished_at":None,
      "duration_seconds":None,
      "engine":{"name":"mutmut","version":mutation_engine_version()},
      "adapter":{"name":"ternforge-local-mutmut-report-adapter","version":MUTATION_ADAPTER_VERSION,"mutation_semantics_version":MUTATION_SEMANTICS_VERSION},
      "mutation_config":MUTATION_CONFIG,
      "mutation_config_fingerprint":inputs["mutation_config_fingerprint"],
      "source_of_truth":{
        "requirements":"Sphinx-Needs graph",
        "test_execution":"retained pytest/Allure run",
        "line_execution":"Coverage.py dynamic contexts",
        "mutation_detail":"Mutation Testing Report Schema 2.0",
      },
      "input_runs":{
        "coverage_run_fingerprint":inputs["coverage_run_fingerprint"],
        "allure_run_fingerprint":inputs["allure_run_fingerprint"],
      },
      "contracts":contracts,
    }

def parse_args():
    parser=argparse.ArgumentParser(description="llm-router local mutation report prototype")
    parser.add_argument("--mode",choices=["full","diff"],default="full")
    parser.add_argument("--base-ref",help="base git ref/SHA for diff campaigns")
    parser.add_argument("--refresh-freshness",action="store_true",help="recompute freshness/triage without running mutants")
    parser.add_argument("--refresh-assurance",action="store_true",help="rerun P33 fault-model probes and rebuild assurance history")
    parser.add_argument("--refresh-implementation-faults",action="store_true",help="run the pytest-gremlins Implementation fault campaign for every attributable contract")
    parser.add_argument("--contracts",nargs="*",help="limit --refresh-implementation-faults to these contracts")
    parser.add_argument("--full",action="store_true",help="with --refresh-implementation-faults: re-run every contract, not only stale ones")
    parser.add_argument("--suppress",nargs=2,metavar=("CONTRACT_ID","MUTANT_FINGERPRINT"),help="suppress one current surviving mutant")
    parser.add_argument("--unsuppress",nargs=2,metavar=("CONTRACT_ID","MUTANT_FINGERPRINT"),help="remove one mutation suppression")
    parser.add_argument("--reason",help="required suppression reason")
    parser.add_argument("--owner",help="optional suppression owner")
    parser.add_argument("--expires-at",help="optional ISO-8601 suppression expiry")
    args=parser.parse_args()
    maintenance=bool(args.refresh_freshness or args.refresh_assurance or args.refresh_implementation_faults or args.suppress or args.unsuppress)
    if args.mode=="diff" and not args.base_ref and not maintenance:
        parser.error("--base-ref is required for --mode diff")
    if args.suppress and not str(args.reason or "").strip():
        parser.error("--reason is required with --suppress")
    return args

def current_campaign_or_die():
    if not CAMPAIGN_PATH.exists():
        raise SystemExit("no retained campaign.json")
    return json.loads(CAMPAIGN_PATH.read_text())


def ensure_mutmut_overlay():
    if installed_mutmut_version() is not None:
        return
    if os.environ.get("TERNFORGE_MUTATION_OVERLAY") == "1":
        raise RuntimeError("mutmut bootstrap overlay did not expose the mutation engine")
    env=os.environ.copy()
    env["TERNFORGE_MUTATION_OVERLAY"]="1"
    command=[
      "uv","run","--with",f"mutmut=={MUTMUT_VERSION}",
      "python",str(Path(__file__).resolve()),*sys.argv[1:],
    ]
    print(
      f"[P21] bootstrapping isolated mutmut {MUTMUT_VERSION} overlay",
      flush=True,
    )
    completed=subprocess.run(command,cwd=ROOT,env=env)
    raise SystemExit(completed.returncode)


def main():
    args=parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.refresh_implementation_faults:
        IMPL_FAULT_DIR.mkdir(parents=True,exist_ok=True)
        refresh_implementation_fault_campaign(set(args.contracts or []) or None,full=args.full)
        return
    if args.refresh_freshness or args.refresh_assurance or args.suppress or args.unsuppress:
        campaign=current_campaign_or_die()
        if args.refresh_assurance:
            fault_model=build_fault_model_facts()
            print(f"[P33] fault-model ladder: {sum(int(row.get('detected') or 0)>0 for row in fault_model.get('layers') or [])}/{len(fault_model.get('layers') or [])} layers exercised",flush=True)
            print(f"[P33] assurance history: {len((fault_model.get('history') or {}).get('rows') or [])} retained mutation snapshots · DVC plot rebuilt",flush=True)
        if args.suppress:
            contract_id,fingerprint=args.suppress
            result=(campaign.get("contracts",{}).get(contract_id,{}) or {}).get("result") or {}
            survivors={
              row.get("fingerprint")
              for row in result.get("mutants") or []
              if row.get("status")=="Survived"
            }
            if fingerprint not in survivors:
                raise SystemExit("suppression target is not a current retained survivor in this campaign")
            upsert_suppression(contract_id,fingerprint,args.reason,args.owner,args.expires_at)
            print(f"[P21] suppressed {contract_id} {fingerprint[:12]} · {args.reason}",flush=True)
        if args.unsuppress:
            contract_id,fingerprint=args.unsuppress
            removed=remove_suppression(contract_id,fingerprint)
            print(f"[P21] unsuppressed {contract_id} {fingerprint[:12]} · removed={removed}",flush=True)
        apply_triage(campaign)
        summary=refresh_freshness(campaign)
        print(f"[P21] freshness: {summary['fresh_measured_contracts']} fresh / {summary['stale_measured_contracts']} stale",flush=True)
        print(f"[P21] triage: {summary['new_unresolved_survivors']} new unresolved · {summary['unresolved_survivors']} unresolved · {summary['suppressed_survivors']} suppressed · {summary['resolved_survivors']} resolved",flush=True)
        return

    ensure_mutmut_overlay()
    validate_contract_scope_attribution()
    validate_linked_test_nodeids()
    deattribute_shared_scope_strength()
    setup=ROOT/"setup.cfg"
    backup=setup.read_bytes() if setup.exists() else None
    campaign=new_campaign(args.mode,args.base_ref)
    started=time.monotonic()
    phase="P21"
    print(f"[{phase}] campaign {campaign['campaign_id']} · {campaign['mode']} · head {campaign['head_sha'][:12]}",flush=True)
    print(f"[{phase}] selected {len(campaign['selected_contracts'])}/{len(CONTRACTS)} contracts: {', '.join(campaign['selected_contracts']) or 'none'}",flush=True)
    if campaign["skipped_contracts"]:
        print(f"[{phase}] skipped unchanged: {', '.join(campaign['skipped_contracts'])}",flush=True)
    print(f"[{phase}] exact Allure links: {len(allure_report_ids())}",flush=True)
    try:
        for contract_id in campaign["selected_contracts"]:
            build_contract(contract_id,CONTRACTS[contract_id],campaign)
        campaign["finished_at"]=utc_now()
        campaign["duration_seconds"]=round(time.monotonic()-started,3)
        STRENGTH["engine"].update({
          "report_schema":"Mutation Testing Report Schema 2.0",
          "report_ui":"Mutation Testing Elements 3.9.0"})
        apply_triage(campaign)
        summary=refresh_freshness(campaign)
        print(f"[{phase}] retained campaign: {CAMPAIGN_PATH.relative_to(ROOT)}",flush=True)
        print(f"[{phase}] freshness: {summary['fresh_measured_contracts']} fresh / {summary['stale_measured_contracts']} stale",flush=True)
        print(f"[{phase}] triage: {summary['new_unresolved_survivors']} new unresolved · {summary['unresolved_survivors']} unresolved · {summary['suppressed_survivors']} suppressed · {summary['resolved_survivors']} resolved",flush=True)
    finally:
        shutil.rmtree(ROOT/"mutants",ignore_errors=True)
        if backup is None:
            setup.unlink(missing_ok=True)
        else:
            setup.write_bytes(backup)

if __name__=="__main__":
    main()
