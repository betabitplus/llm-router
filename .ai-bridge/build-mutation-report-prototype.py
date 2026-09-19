from __future__ import annotations

import argparse
import ast
import binascii
import hashlib
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
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from html import escape as html_escape
from importlib.metadata import version as package_version
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
STRENGTH: dict[str, Any]=json.loads(STRENGTH_PATH.read_text())
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
MUTATION_PAGE=ROOT/"docs/_build/html/mutation-analysis.html"
ASSURANCE_PAGE=ROOT/"docs/_build/html/verification-assurance.html"
SPEC_HEALTH_PAGE=ROOT/"docs/_build/html/specification-health.html"
SUPPRESSIONS_PATH=ROOT/".ai-bridge/mutation-suppressions.json"
MUTATION_SEMANTICS_VERSION="p21-local-2"
MUTATION_ADAPTER_VERSION="p34-local-2"
PROTOTYPE_BUILD_VERSION="p34-local-1"
MUTATION_CONFIG={
  "process_isolation":"forkserver",
  "forkserver_warmup":"collect",
  "mutate_only_covered_lines":True,
  "max_children":4,
  "thresholds":{"low":60,"high":80},
}
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
    mutmut_version=mutmut_version or package_version("mutmut")
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
    mutmut_version=mutmut_version or package_version("mutmut")
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
    baseline_adapter=baseline.get("adapter") or {}
    current_adapter=campaign.get("adapter") or {}
    baseline_engine=baseline.get("engine") or {}
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
    env=os.environ.copy()
    env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"]="YES"
    mutmut_executable=shutil.which("mutmut")
    if mutmut_executable:
        command=[mutmut_executable,"run","--max-children",str(MUTATION_CONFIG["max_children"])]
    else:
        env.pop("VIRTUAL_ENV",None)
        env.pop("UV_RUN_RECURSION_DEPTH",None)
        command=[
          "uv","run","--with","mutmut","mutmut","run",
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

def patch_depth_boundary_model(t):
    if "<!-- DEPTH-P30-BOUNDARY-MODEL -->" in t:
     return t

    def rep(old,new,n=1):
     nonlocal t
     c=t.count(old)
     if c!=n: raise RuntimeError(f"P30 Depth patch expected {n}, got {c}: {old[:100]!r}")
     t=t.replace(old,new,n)

    rep("The treemap has three selectable projections: standard ISTQB <strong>Test Level</strong>, universal <strong>Representation Fidelity</strong>, and mutation-based <strong>Test Strength</strong>. Test Strength colors only objectively measured contracts. Hover a measured contract for score, survivor debt and one missed-behavior example; click for changes / history. Model/simulation trust remains separate as <strong>Evidence Producer Credibility</strong>.</p>",
        "The treemap has three selectable projections: standard ISTQB <strong>Test Level</strong>, observed <strong>Boundary Reality</strong>, and mutation-based <strong>Test Strength</strong>. Boundary Reality answers how the evidence path interacted with outside reality (local → substitute → replay → direct live); it is an exposure mode, not an assurance-strength score. <strong>Representation Fidelity</strong> now qualifies each concrete evidence path instead of acting as a second independent map axis. Test Strength colors only objectively measured contracts. Model/simulation trust remains separate as <strong>Evidence Producer Credibility</strong>.</p>")
    rep("""    <button class="tf-depth-dimension" type="button" data-depth-mode="representation">
          <span>Representation Fidelity <em class="tf-depth-direction">weak → strong</em></span>
          <strong id="tf-representation-headline">Loading</strong>
          <div class="tf-depth-rail" id="tf-representation-rail"></div>
          <small id="tf-depth-credibility-signal" class="tf-depth-credibility-signal">Evidence credibility · Loading</small>
        </button>""","""    <button class="tf-depth-dimension" type="button" data-depth-mode="boundary">
          <span>Boundary Reality <em class="tf-depth-direction">local → live</em></span>
          <strong id="tf-boundary-headline">Loading</strong>
          <div class="tf-depth-rail" id="tf-boundary-rail"></div>
          <small id="tf-depth-credibility-signal" class="tf-depth-credibility-signal">Representation + producer trust qualify the exact path · details below ↓</small>
        </button>""")
    rep("""  const REPRESENTATION = {
    ""","""  const BOUNDARY = {
        no_evidence: {rank:-1,label:"No evidence",short:"—",color:"#667085",description:"No retained verification evidence."},
        none: {rank:0,label:"Local only",short:"Local",color:"#d49a32",description:"The evidence path remains inside llm-router; no external dependency boundary is crossed."},
        substitute: {rank:1,label:"Substitute",short:"Sub",color:"#3b82f6",description:"The path crosses an external-facing interface through a deterministic substitute/fake."},
        replay: {rank:2,label:"Replay",short:"Replay",color:"#14b8a6",description:"The path replays a previously captured external interaction."},
        direct: {rank:3,label:"Direct live",short:"Live",color:"#2f8f5b",description:"The path directly interacts with the current external dependency. This is not universally required; the Assurance Target decides sufficiency."},
      };
      const REPRESENTATION = {
    """)
    rep("""  const REACH_ORDER=["none","component","component_integration","system","system_integration"];
      const REPRESENTATION_ORDER=""", """  const REACH_ORDER=["none","component","component_integration","system","system_integration"];
      const BOUNDARY_ORDER=["no_evidence","none","substitute","replay","direct"];
      const REPRESENTATION_ORDER=""")
    rep("""        id,index,reachKey:"none",representationKey:"none",validationKey:"na",
    ""","""        id,index,reachKey:"none",boundaryKey:"no_evidence",representationKey:"none",validationKey:"na",
    """)
    rep("""      reachKey:String(audited.system_reach||"none"),
          representationKey:String(audited.representation_fidelity||"none"),
    ""","""      reachKey:String(audited.system_reach||"none"),
          boundaryKey:String(strongestFromRows(testRows,"boundary_mode",BOUNDARY,BOUNDARY_ORDER)||"no_evidence"),
          representationKey:String(audited.representation_fidelity||"none"),
    """)
    rep("""      reachKey: weakest(metrics,"reachKey",REACH_ORDER),
          representationKey: weakest(metrics,"representationKey",REPRESENTATION_ORDER),
    ""","""      reachKey: weakest(metrics,"reachKey",REACH_ORDER),
          boundaryKey: weakest(metrics,"boundaryKey",BOUNDARY_ORDER),
          representationKey: weakest(metrics,"representationKey",REPRESENTATION_ORDER),
    """)
    rep("""      reachDist: distribution(metrics,"reachKey",REACH_ORDER),
          representationDist: distribution(metrics,"representationKey",REPRESENTATION_ORDER),
    ""","""      reachDist: distribution(metrics,"reachKey",REACH_ORDER),
          boundaryDist: distribution(metrics,"boundaryKey",BOUNDARY_ORDER),
          representationDist: distribution(metrics,"representationKey",REPRESENTATION_ORDER),
    """)
    old="""      if(mode==="representation") {
            const maxKey=strongestFromRows(own.testRows,"representation_fidelity",REPRESENTATION,REPRESENTATION_ORDER)
              || own.representationKey;
            lines.push("<b>Representation Fidelity</b> · <span style='color:"+REPRESENTATION[maxKey].color+"'><b>"+REPRESENTATION[maxKey].label+"</b></span>");
            const dist=achievedDistribution(own.testRows,"representation_fidelity",REPRESENTATION,REPRESENTATION_ORDER);
            if(dist.length) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Tests</b></span>");
              dist.forEach(item=>lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(item)+"</span>"));
            }
            const producers=producerStatsForRows(own.testRows);
            if(producers.length) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Evidence producers</b></span>");
              producers.forEach(item=>lines.push(
                "<span class='tf-depth-tooltip-note'>"+
                escapeHtml(producerDisplayName(item.id))+" · "+
                escapeHtml(VALIDATION[item.level]?.label || item.level.toUpperCase())+" · "+
                item.tests+" test"+(item.tests===1?"":"s")+
                "</span>"
              ));
            }
          } else if(mode==="strength") {"""
    new="""      if(mode==="boundary") {
            const maxKey=strongestFromRows(own.testRows,"boundary_mode",BOUNDARY,BOUNDARY_ORDER) || own.boundaryKey;
            lines.push("<b>Boundary Reality</b> · <span style='color:"+BOUNDARY[maxKey].color+"'><b>"+BOUNDARY[maxKey].label+"</b></span>");
            lines.push("<span class='tf-depth-tooltip-note'>Exposure mode only · the Assurance Target decides whether live interaction is required.</span>");
            const dist=achievedDistribution(own.testRows,"boundary_mode",BOUNDARY,BOUNDARY_ORDER);
            if(dist.length) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Tests by boundary</b></span>");
              dist.forEach(item=>lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(item)+"</span>"));
            }
            const qualifiers=new Map();
            own.testRows.forEach(row=>{
              const b=String(row.boundary_mode||"none");
              const rep=String(row.representation_fidelity||"none");
              const key=b+"|"+rep;
              qualifiers.set(key,(qualifiers.get(key)||0)+1);
            });
            if(qualifiers.size) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Same-path representation qualifiers</b></span>");
              [...qualifiers.entries()].forEach(([key,count])=>{
                const [b,rep]=key.split("|");
                lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(BOUNDARY[b]?.label||b)+" · "+escapeHtml(REPRESENTATION[rep]?.label||rep)+" · "+count+" test"+(count===1?"":"s")+"</span>");
              });
            }
            const producers=producerStatsForRows(own.testRows);
            if(producers.length) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Evidence producers / M&amp;S validation</b></span>");
              producers.forEach(item=>lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(producerDisplayName(item.id))+" · "+escapeHtml(VALIDATION[item.level]?.label || item.level.toUpperCase())+" · "+item.tests+" test"+(item.tests===1?"":"s")+"</span>"));
            }
          } else if(mode==="strength") {"""
    rep(old,new)
    rep("""    if(mode==="representation") {
          lines.push("<b>Branch floor</b> · <span style='color:"+REPRESENTATION[metric.representationKey].color+"'><b>"+REPRESENTATION[metric.representationKey].label+"</b></span>");
          lines.push("<span class='tf-depth-tooltip-note'>Contracts · "+escapeHtml(compactDist(metric.representationDist,REPRESENTATION,REPRESENTATION_ORDER))+"</span>");
        } else if(mode==="strength") {""","""    if(mode==="boundary") {
          lines.push("<b>Branch minimum observed boundary</b> · <span style='color:"+BOUNDARY[metric.boundaryKey].color+"'><b>"+BOUNDARY[metric.boundaryKey].label+"</b></span>");
          lines.push("<span class='tf-depth-tooltip-note'>Contracts · "+escapeHtml(compactDist(metric.boundaryDist,BOUNDARY,BOUNDARY_ORDER))+"</span>");
          lines.push("<span class='tf-depth-tooltip-note'>Boundary mode is exposure, not assurance strength.</span>");
        } else if(mode==="strength") {""")
    rep("""    if(mode==="representation") return {dict:REPRESENTATION,order:REPRESENTATION_ORDER,key:"representationKey"};
    ""","""    if(mode==="boundary") return {dict:BOUNDARY,order:BOUNDARY_ORDER,key:"boundaryKey"};
    """)
    rep("""      if(mode==="strength") {
            const fact=isContract ? contractMetrics.get(id)?.strengthFact : null;
            if(fact && fact.fresh===false) addStrengthFreshnessMarker(group,path);
            return;
          }
          if(mode!=="representation") return;

          if(isContract && contractHasLowCredibility(index)) {
            addCredibilityWarningMarker(group,path);
          }

          if(!active) return;""","""      if(mode==="strength") {
            const fact=isContract ? contractMetrics.get(id)?.strengthFact : null;
            if(fact && fact.fresh===false) addStrengthFreshnessMarker(group,path);
          }
          if(mode==="boundary" && isContract && contractHasLowCredibility(index)) {
            addCredibilityWarningMarker(group,path);
          }

          if(!active) return;""")
    rep("""    if(selectedProducer && mode!=="representation") {
          applyMode("representation").then(focusMap);
          return;
        }
        applyCredibilityOutlines();
        focusMap();""","""    applyCredibilityOutlines();
        focusMap();""")
    rep("""    renderRail("tf-reach-rail",root.reachDist,REACH,REACH_ORDER);
        renderRail("tf-representation-rail",root.representationDist,REPRESENTATION,REPRESENTATION_ORDER);
        renderRail("tf-strength-rail",root.strengthDist,STRENGTH,STRENGTH_ORDER);

        const reachMax=strongestPresent(root.reachDist,REACH_ORDER);
        const representationMax=strongestPresent(root.representationDist,REPRESENTATION_ORDER);
        document.getElementById("tf-reach-headline").textContent=
          "Max · "+(reachMax?REACH[reachMax].label:"No evidence");
        document.getElementById("tf-representation-headline").textContent=
          "Max · "+(representationMax?REPRESENTATION[representationMax].label:"No evidence");""","""    renderRail("tf-reach-rail",root.reachDist,REACH,REACH_ORDER);
        renderRail("tf-boundary-rail",root.boundaryDist,BOUNDARY,BOUNDARY_ORDER);
        renderRail("tf-strength-rail",root.strengthDist,STRENGTH,STRENGTH_ORDER);

        const reachMax=strongestPresent(root.reachDist,REACH_ORDER);
        const boundaryMax=strongestPresent(root.boundaryDist,BOUNDARY_ORDER,{ignore:["no_evidence"]});
        document.getElementById("tf-reach-headline").textContent=
          "Max · "+(reachMax?REACH[reachMax].label:"No evidence");
        document.getElementById("tf-boundary-headline").textContent=
          "Max observed · "+(boundaryMax?BOUNDARY[boundaryMax].label:"No evidence");""")
    rep("""      representation:
            "Representation Fidelity\\n"+
            "Question: how close was the verification article to the actual target?\\n"+
            "Current max: "+(representationMax?REPRESENTATION[representationMax].label:"No evidence")+"\\n"+
            "Contracts: "+axisDistributionText(root.representationDist,REPRESENTATION,REPRESENTATION_ORDER),
    ""","""      boundary:
            "Boundary Reality\\n"+
            "Question: how did retained evidence interact with outside reality?\\n"+
            "This is an exposure mode, not a universal weak→strong score. The Assurance Target decides what is required.\\n"+
            "Current maximum observed exposure: "+(boundaryMax?BOUNDARY[boundaryMax].label:"No evidence")+"\\n"+
            "Contracts: "+axisDistributionText(root.boundaryDist,BOUNDARY,BOUNDARY_ORDER),
    """)
    rep("""    if(mode!=="representation") {
          selectedProducer=null;
          hoveredProducer=null;
          hoveredContractId=null;
          updateProducerSelectionUi();
        }
    ""","""    hoveredContractId=null;
        updateProducerSelectionUi();
    """)
    rep("""      hoveredContractId=mode==="representation" && (kind==="Requirement" || kind==="Technical requirement")
            ? String(point.id||"")
            : null;""","""      hoveredContractId=(kind==="Requirement" || kind==="Technical requirement")
            ? String(point.id||"")
            : null;""")
    # marker for idempotence
    rep("</section>","<!-- DEPTH-P30-BOUNDARY-MODEL -->\n</section>")
    return t

def patch_depth_page():
    if not DEPTH_PAGE.exists():
        return
    text=DEPTH_PAGE.read_text()
    if "// DEPTH-P19 freshness marker" not in text:
        text=text.replace(
          "  function applyCredibilityOutlines() {",
          """  // DEPTH-P19 freshness marker: score color remains Test Strength; freshness is orthogonal.
  function addStrengthFreshnessMarker(group,path) {
    group.querySelectorAll(".tf-strength-stale-marker").forEach(node=>node.remove());
    const box=path.getBBox();
    if(box.width<12 || box.height<12) return;
    const circle=document.createElementNS("http://www.w3.org/2000/svg","circle");
    circle.classList.add("tf-strength-stale-marker");
    circle.setAttribute("cx",String(box.x+7));
    circle.setAttribute("cy",String(box.y+7));
    circle.setAttribute("r","4");
    circle.setAttribute("fill","#c2413b");
    circle.setAttribute("stroke","rgba(15,23,42,.75)");
    circle.setAttribute("stroke-width","1.5");
    circle.setAttribute("pointer-events","none");
    group.appendChild(circle);
  }

  function applyCredibilityOutlines() {"""
        )
        text=text.replace(
          '      group.querySelectorAll(".tf-credibility-warning-marker").forEach(node=>node.remove());\n      path.style.stroke="rgb(255, 255, 255)";',
          '      group.querySelectorAll(".tf-credibility-warning-marker,.tf-strength-stale-marker").forEach(node=>node.remove());\n      path.style.stroke="rgb(255, 255, 255)";'
        )
        text=text.replace(
          '      const isContract=kind==="Requirement" || kind==="Technical requirement";\n      if(mode!=="representation") return;',
          """      const isContract=kind==="Requirement" || kind==="Technical requirement";
      if(mode==="strength") {
        const fact=isContract ? contractMetrics.get(id)?.strengthFact : null;
        if(fact && fact.fresh===false) addStrengthFreshnessMarker(group,path);
        return;
      }
      if(mode!=="representation") return;"""
        )
        text=text.replace(
          """          lines.push("<b>Test Strength</b> · <span style='color:"+STRENGTH[key].color+"'><b>"+Number(fact.score).toFixed(1)+"% · "+STRENGTH[key].label+"</b></span>");
          lines.push("<span class='tf-depth-tooltip-note'>"+Number(fact.killed||0)+" killed · "+Number(fact.survived||0)+" survived · "+Number(fact.valid_mutants||0)+" covered valid mutants</span>");
          lines.push("<span class='tf-depth-tooltip-note'>Scope · "+escapeHtml(fact.scope_kind)+" "+escapeHtml(fact.scope)+"</span>");
          lines.push("<span class='tf-depth-tooltip-note'>Linked tests · "+Number(fact.linked_test_count||0)+"</span>");
          lines.push("<span class='tf-depth-tooltip-note'><b>Click → Mutation Analysis</b></span>");""",
          """          lines.push("<b>Test Strength</b> · <span style='color:"+STRENGTH[key].color+"'><b>"+Number(fact.score).toFixed(1)+"% · "+STRENGTH[key].label+"</b></span>");
          lines.push("<span class='tf-depth-tooltip-note'>"+Number(fact.killed||0)+" killed · "+Number(fact.survived||0)+" survived · "+Number(fact.valid_mutants||0)+" covered valid mutants</span>");
          const freshness=fact.fresh===false ? "STALE" : "Fresh";
          const campaign=fact.campaign_mode ? " · "+fact.campaign_mode+" · "+String(fact.campaign_head_sha||"").slice(0,12) : "";
          lines.push("<span class='tf-depth-tooltip-note'><b>"+freshness+"</b>"+escapeHtml(campaign)+"</span>");
          if(fact.fresh===false && Array.isArray(fact.stale_reasons) && fact.stale_reasons.length) {
            lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(fact.stale_reasons.join(" · "))+"</span>");
          }
          lines.push("<span class='tf-depth-tooltip-note'>Scope · "+escapeHtml(fact.scope_kind)+" "+escapeHtml(fact.scope)+"</span>");
          lines.push("<span class='tf-depth-tooltip-note'>Linked tests · "+Number(fact.linked_test_count||0)+"</span>");
          lines.push("<span class='tf-depth-tooltip-note'><b>Click → Mutation Analysis</b></span>");"""
        )
        text=text.replace(
          """    document.getElementById("tf-strength-headline").textContent=
      root.strengthMeasuredCount+" / "+root.strengthTotalCount+" measured";""",
          """    const freshMeasured=Number(strengthFacts?.summary?.fresh_measured_contracts||0);
    const staleMeasured=Number(strengthFacts?.summary?.stale_measured_contracts||0);
    document.getElementById("tf-strength-headline").textContent=
      root.strengthMeasuredCount+" / "+root.strengthTotalCount+" measured · "+freshMeasured+" fresh · "+staleMeasured+" stale";"""
        )
        text=text.replace(
          '"Spike coverage: "+root.strengthMeasuredCount+"/"+root.strengthTotalCount+" contracts",',
          '"Measurement: "+root.strengthMeasuredCount+"/"+root.strengthTotalCount+" contracts · "+Number(strengthFacts?.summary?.fresh_measured_contracts||0)+" fresh · "+Number(strengthFacts?.summary?.stale_measured_contracts||0)+" stale",'
        )

    if "// DEPTH-P21 survivor delta" not in text:
        text=text.replace(
          """          if(fact.fresh===false && Array.isArray(fact.stale_reasons) && fact.stale_reasons.length) {
            lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(fact.stale_reasons.join(" · "))+"</span>");
          }
          lines.push("<span class='tf-depth-tooltip-note'>Scope · "+escapeHtml(fact.scope_kind)+" "+escapeHtml(fact.scope)+"</span>");""",
          """          if(fact.fresh===false && Array.isArray(fact.stale_reasons) && fact.stale_reasons.length) {
            lines.push("<span class='tf-depth-tooltip-note'>"+escapeHtml(fact.stale_reasons.join(" · "))+"</span>");
          }
          // DEPTH-P21 survivor delta
          const triage=fact.triage||{};
          if(triage.baseline_available) {
            const delta=triage.score_delta===null || triage.score_delta===undefined
              ? "score Δ n/a"
              : "score Δ "+(Number(triage.score_delta)>=0?"+":"")+Number(triage.score_delta).toFixed(1)+" pp";
            lines.push("<span class='tf-depth-tooltip-note'><b>Mutation delta</b> · New "+Number(triage.new_survivors||0)+" · Resolved "+Number(triage.resolved_survivors||0)+" · Suppressed "+Number(triage.suppressed_survivors||0)+" · "+delta+"</span>");
            if(Number(triage.new_unresolved_survivors||0)>0) {
              lines.push("<span class='tf-depth-tooltip-note'><b>Attention · "+Number(triage.new_unresolved_survivors||0)+" new unresolved survivor"+(Number(triage.new_unresolved_survivors||0)===1?"":"s")+"</b></span>");
            }
          }
          lines.push("<span class='tf-depth-tooltip-note'>Scope · "+escapeHtml(fact.scope_kind)+" "+escapeHtml(fact.scope)+"</span>");"""
        )
        text=text.replace(
          'root.strengthMeasuredCount+" / "+root.strengthTotalCount+" measured · "+freshMeasured+" fresh · "+staleMeasured+" stale";',
          'root.strengthMeasuredCount+" / "+root.strengthTotalCount+" measured · "+freshMeasured+" fresh · "+staleMeasured+" stale · "+Number(strengthFacts?.summary?.new_unresolved_survivors||0)+" new";'
        )
        text=text.replace(
          '"Measurement: "+root.strengthMeasuredCount+"/"+root.strengthTotalCount+" contracts · "+Number(strengthFacts?.summary?.fresh_measured_contracts||0)+" fresh · "+Number(strengthFacts?.summary?.stale_measured_contracts||0)+" stale",',
          '"Measurement: "+root.strengthMeasuredCount+"/"+root.strengthTotalCount+" contracts · "+Number(strengthFacts?.summary?.fresh_measured_contracts||0)+" fresh · "+Number(strengthFacts?.summary?.stale_measured_contracts||0)+" stale · "+Number(strengthFacts?.summary?.new_unresolved_survivors||0)+" new unresolved",'
        )

    # DEPTH-P27: the P26 watch duplicated the treemap and is intentionally retired.
    # Keep the map as the monitor; hover gives the compact strength facts and click
    # enters the mutation change/history journal.
    text=re.sub(
      r'<div id=\"tf-strength-monitor\".*?<div class=\"ternforge-verification-depth-map-shell\">',
      '<div class="ternforge-verification-depth-map-shell">',text,count=1,flags=re.DOTALL
    )
    css_start=text.find("/* DEPTH-P26 strength monitor */")
    if css_start!=-1:
        css_end=text.find(".ternforge-verification-depth-map-shell {",css_start)
        if css_end!=-1:
            text=text[:css_start]+text[css_end:]
    js_start=text.find("  // DEPTH-P26 strength monitor")
    if js_start!=-1:
        js_end=text.find("  function contractTarget(index) {",js_start)
        if js_end!=-1:
            text=text[:js_start]+text[js_end:]
    text=text.replace("    renderStrengthMonitor();\n","")
    text=text.replace(
      '<small class="tf-depth-credibility-signal">Mutation-based · killed / covered valid mutants · click measured contract → analysis</small>',
      '<small class="tf-depth-credibility-signal">Current snapshot · click measured contract → changes / history</small>'
    )
    text=text.replace(
      """    if(mode===\"strength\") {
      const fact=contractMetrics.get(id)?.strengthFact;
      return fact?.report_url || null;
    }""",
      """    if(mode===\"strength\") {
      const fact=contractMetrics.get(id)?.strengthFact;
      return fact ? \"mutation-analysis.html#mutation-\"+id.toLowerCase() : null;
    }""",
      1
    )
    text=text.replace(
      '    return "verification-assurance.html#assurance-"+id.toLowerCase();',
      '    return "traceability-reader.html#review-"+id;'
    )
    text=text.replace(
      """          lines.push(\"<span class='tf-depth-tooltip-note'>\"+Number(fact.killed||0)+\" killed · \"+Number(fact.survived||0)+\" survived · \"+Number(fact.valid_mutants||0)+\" covered valid mutants</span>\");""",
      """          lines.push(\"<span class='tf-depth-tooltip-note'>\"+Number(fact.killed||0)+\" killed · \"+Number(fact.survived||0)+\" survived</span>\");""",
      1
    )
    text=text.replace(
      """            lines.push(\"<span class='tf-depth-tooltip-note'><b>Mutation delta</b> · New \"+Number(triage.new_survivors||0)+\" · Resolved \"+Number(triage.resolved_survivors||0)+\" · Suppressed \"+Number(triage.suppressed_survivors||0)+\" · \"+delta+\"</span>\");""",
      """            lines.push(\"<span class='tf-depth-tooltip-note'><b>\"+freshness+\"</b> · New \"+Number(triage.new_unresolved_survivors||0)+\" · Debt \"+Number(triage.existing_survivors||0)+\" · \"+delta+\"</span>\");""",
      1
    )
    text=text.replace(
      """          lines.push(\"<span class='tf-depth-tooltip-note'>Scope · \"+escapeHtml(fact.scope_kind)+\" \"+escapeHtml(fact.scope)+\"</span>\");
          lines.push(\"<span class='tf-depth-tooltip-note'>Linked tests · \"+Number(fact.linked_test_count||0)+\"</span>\");
          lines.push(\"<span class='tf-depth-tooltip-note'><b>Click → Mutation Analysis</b></span>\");""",
      """          const examples=Array.isArray(fact.survivor_examples)?fact.survivor_examples:[];
          if(examples.length) lines.push(\"<span class='tf-depth-tooltip-note'><b>Missed example</b> · \"+escapeHtml(String(examples[0].summary||\"\"))+\"</span>\");
          lines.push(\"<span class='tf-depth-tooltip-note'><b>Click → changes / history</b></span>\");""",
      1
    )

    if "// DEPTH-P26 compact strength hover" not in text:
        text=text.replace(
          """          const freshness=fact.fresh===false ? "STALE" : "Fresh";
          const campaign=fact.campaign_mode ? " · "+fact.campaign_mode+" · "+String(fact.campaign_head_sha||"").slice(0,12) : "";
          lines.push("<span class='tf-depth-tooltip-note'><b>"+freshness+"</b>"+escapeHtml(campaign)+"</span>");
          if(fact.fresh===false && Array.isArray(fact.stale_reasons) && fact.stale_reasons.length) {""",
          """          // DEPTH-P26 compact strength hover
          const freshness=fact.fresh===false ? "STALE" : "Fresh";
          if(fact.fresh===false && Array.isArray(fact.stale_reasons) && fact.stale_reasons.length) {""",
          1
        )
    text=text.replace(
      "Test Strength colors only contracts with objectively attributable mutation scope; click a measured contract to inspect its standard Mutation Analysis report.",
      "Test Strength colors only objectively measured contracts. Hover a measured contract for score, survivor debt and one missed-behavior example; click for changes / history."
    )
    text=text.replace(
      "Test Strength colors only objectively measured contracts; the watch row shows score, survivor debt and one missed-behavior example. Click a measured contract for changes / history.",
      "Test Strength colors only objectively measured contracts. Hover a measured contract for score, survivor debt and one missed-behavior example; click for changes / history."
    )
    text=patch_depth_boundary_model(text)
    DEPTH_PAGE.write_text(text)



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
    has_native_depth="Verification Depth Map" in nav_prefix
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
    if has_native_depth:
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
              if candidate.exists() else "#"
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
<p><small>Most recent retained mutation campaigns.</small></p>
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
    text=re.sub(r"<title>.*?</title>","<title>Mutation Analysis &#8212; llm-router 0.24.1 documentation</title>",text,count=1,flags=re.DOTALL)
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


def run_checked(command,*,cwd=ROOT,env=None):
    completed=subprocess.run(
      command,cwd=cwd,env=env,text=True,
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
    rows=[
      row for row in report.get("results") or []
      if start<=int(row.get("line_number") or -1)<=end
    ]
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
    command=[
      shutil.which("uv") or "uv","run","--with","pytest-gremlins","pytest","-q",
      *nodeids,
      "--gremlins",
      f"--gremlin-targets={spec['source']}",
      "--gremlin-report=json",
      "--gremlin-operators=comparison,boundary,boolean,arithmetic,return",
    ]
    run_checked(command)
    report_path=ROOT/"coverage/gremlins/gremlins.json"
    return gremlin_group_metrics(spec,nodeids,json.loads(report_path.read_text()))


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
    paths=sorted(HISTORY_DIR.glob("*.json"))
    if CAMPAIGN_PATH.exists():
        paths.append(CAMPAIGN_PATH)
    rows=[]
    seen=set()
    for path in paths:
        try:
            campaign=json.loads(path.read_text())
        except Exception:
            continue
        run_id=str(campaign.get("run_id") or campaign.get("campaign_id") or path.stem)
        if run_id in seen:
            continue
        campaign_contracts=campaign.get("contracts") or {}
        if contract_id:
            selected=campaign_contracts.get(contract_id) or {}
            selected_score=(selected.get("result") or {}).get("score")
            scores=[float(selected_score)] if selected_score is not None else []
        else:
            scores=[
              (contract.get("result") or {}).get("score")
              for contract in campaign_contracts.values()
            ]
            scores=[float(score) for score in scores if score is not None]
        if not scores:
            continue
        seen.add(run_id)
        new=debt=resolved=0
        triage_contracts=(
          [campaign_contracts.get(contract_id) or {}]
          if contract_id else campaign_contracts.values()
        )
        for contract in triage_contracts:
            triage=(contract.get("result") or {}).get("triage") or {}
            new+=int(triage.get("new_unresolved_survivors") or 0)
            debt+=int(triage.get("existing_survivors") or 0)
            resolved+=int(triage.get("resolved_survivors") or 0)
        rows.append({
          "finished_at":campaign.get("finished_at") or "",
          "run_id":run_id,
          "mode":campaign.get("mode") or "unknown",
          "measured_contracts":len(scores),
          "mutation_sensitivity":round(sum(scores)/len(scores),1),
          "new_survivors":new,
          "survivor_debt":debt,
          "resolved_survivors":resolved,
        })
    rows.sort(key=lambda row:(row["finished_at"],row["run_id"]))
    for index,row in enumerate(rows,1):
        row["step"]=index
    return rows


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
    history=build_dvc_assurance_history(assurance_history_rows())
    contract_history=build_dvc_assurance_history(
      assurance_history_rows("REQ_INVALID_CONFIGURATION_ERRORS"),
      subdir="REQ_INVALID_CONFIGURATION_ERRORS",
      title="REQ_INVALID_CONFIGURATION_ERRORS · Test Strength history",
      metric="retained mutmut Test Strength for REQ_INVALID_CONFIGURATION_ERRORS",
    )
    rate_limit_history=build_dvc_assurance_history(
      assurance_history_rows("TREQ_RATE_LIMIT_STATE"),
      subdir="TREQ_RATE_LIMIT_STATE",
      title="TREQ_RATE_LIMIT_STATE · covered-mutant Test Strength history",
      metric="retained mutmut covered-mutant Test Strength for TREQ_RATE_LIMIT_STATE",
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


def producer_chain_status(producer_ids,qualification):
    if not qualification_is_current(qualification):
        return "UNKNOWN", "qualification record is missing or does not match current tool/code fingerprints"
    required=list(dict.fromkeys(list(producer_ids or [])+["PRODUCER_LLM_ROUTER_TRACE_BRIDGE","PRODUCER_ASSURANCE_ADAPTER","PRODUCER_REQUIREMENT_MONITOR"]))
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


def load_evidence_run_inputs():
    if not EVIDENCE_RUN_INPUTS_PATH.exists():
        return {}
    try:
        return json.loads(EVIDENCE_RUN_INPUTS_PATH.read_text())
    except Exception:
        return {}


def current_input_snapshot(snapshot):
    if not snapshot or not snapshot.get("inputs"):
        return "UNKNOWN","retained run input snapshot is missing",None
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


def depth_model_validation_records():
    return {
      "PRODUCER_SCRIPTED_HTTP_SERVER":{
        "title":"Scripted HTTP provider model",
        "representation_fidelity":"surrogate_simulated",
        "ms_validation":"l0",
        "intended_use":"Provide deterministic provider-shaped HTTP interactions for adapter/router verification.",
        "referent":None,
        "basis":"The surrogate is implemented and its mechanics are qualified, but no structured conceptual-validation record ties each scripted provider behavior to a real referent/intended-use source. Therefore L1 is not claimed.",
        "calibration":[],
      },
      "PRODUCER_VCR":{
        "title":"VCR replay model",
        "representation_fidelity":"surrogate_simulated",
        "ms_validation":"l0",
        "intended_use":"Replay previously captured provider HTTP interactions deterministically.",
        "referent":"historical live-provider capture",
        "basis":"The replay tool is qualified and cassettes originate from recorded interactions, but no structured per-cassette intended-use/conceptual-validation record exists. Therefore L1 is not claimed.",
        "calibration":[],
      },
      "PRODUCER_GOOGLE_GENAI_FAKE_SDK":{
        "title":"Google GenAI fake SDK model",
        "representation_fidelity":"surrogate_simulated",
        "ms_validation":"l2",
        "intended_use":"Reproduce the Google GenAI SDK surface used by the adapter in-process.",
        "referent":"live Google GenAI provider/SDK",
        "basis":"Producer purpose and fake-SDK contracts are explicit; passing live capability experiment EXP_0002 is linked as calibration and compares important provider behaviors at some validation points. No complete intended-domain coverage record exists, so L3 is not claimed.",
        "calibration":["EXP_0002"],
      },
      "PRODUCER_GEMINI_WEBAPI_FAKE_SDK":{
        "title":"Gemini WebAPI fake SDK model",
        "representation_fidelity":"surrogate_simulated",
        "ms_validation":"l2",
        "intended_use":"Reproduce the Gemini WebAPI client/provider surface used by the adapter in-process.",
        "referent":"live Gemini WebAPI provider/client",
        "basis":"Producer purpose and fake-SDK contracts are explicit; passing live capability experiment EXP_0003 is linked as calibration and compares important provider behaviors at some validation points. No complete intended-domain coverage record exists, so L3 is not claimed.",
        "calibration":["EXP_0003"],
      },
    }


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
        "representation_fidelity_semantics":"Ternforge scale: Synthetic/Abstract → Surrogate/Simulated → Representative → Actual. Representative requires intended-use pedigree; replay origin alone is not enough.",
        "ms_validation_order":DEPTH_MS_ORDER,
        "ms_validation_semantics":"NASA-STD-7009A validation-factor projection. Generic substitute/replay evidence remains L0; only explicitly calibrated fake-SDK models reach L2 in this pilot.",
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
    input_state,input_basis,current_input_digest=current_input_snapshot(run_inputs)
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


def requirement_monitor_model(base_model):
    policy=project_monitor_policy()
    junit_actual=junit_monitor_actual()
    junit_faults=junit_fault_actual(policy)
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
        class_actual={}
        implementation=layers.get("implementation") or {}
        native_families=set()
        for group in groups:
            native_families.update((group.get("families") or {}).keys())
        if "comparison" in native_families:
            class_actual["impl.comparison"]={"exercised":True,"detected":True}
        if "boundary" in native_families:
            class_actual["impl.boundary"]={"exercised":True,"detected":True}
        class_actual["impl.control-flow"]={"exercised":False,"detected":False}
        layer_map={
          "runtime.latency-timeout":"runtime",
          "interface.unexpected-interaction":"interface",
          "architecture.forbidden-edge":"architecture",
          "spec.wrong-outcome":"specification",
        }
        for class_id,layer_id in layer_map.items():
            layer=layers.get(layer_id) or {}
            class_actual[class_id]={
              "exercised":bool(layer.get("generated")),
              "detected":bool(layer.get("detected")),
            }
        for class_id in (
          "runtime.unavailable-disconnect","runtime.malformed-response",
          "interface.error-status","interface.payload-schema",
          "architecture.layer-bypass","spec.missing-partition","spec.wrong-ordering-boundary",
        ):
            class_actual.setdefault(class_id,{"exercised":False,"detected":False})

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
            class_actual[class_id]={
              **previous,
              **retained,
              "exercised":exercised,
              "detected":detected,
              "sources":{
                "specialized_probe":previous,
                "retained_test_challenge":retained,
              },
            }

        for fault_group in policy.get("fault_groups") or []:
            for class_id in fault_group.get("classes") or []:
                class_actual.setdefault(
                  class_id,
                  {"exercised":False,"detected":False},
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
    return result


def requirement_monitor_block(monitor_json):
    template=r"""<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-START -->
<style>
.bd-article-container{overflow:visible!important}
.tf-p34-shell{max-width:74rem;margin:0 auto;padding-bottom:34rem}
#verification-assurance-map>section[id^="assurance-"]{scroll-margin-top:4.5rem}
.tf-p34-section{scroll-margin-top:6.75rem}
.tf-p34-section[id^="ce-coverage-"]{scroll-margin-top:24rem}
.tf-p34-head{border:1px solid var(--pst-color-border);border-radius:.55rem;padding:.85rem 1rem;background:var(--pst-color-surface);margin:.5rem 0 .7rem}
.tf-p34-headline{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem}
.tf-p34-head h2{font-size:1.15rem;margin:.1rem 0}
.tf-p34-kicker,.tf-p34-label{font-size:.66rem;letter-spacing:.055em;text-transform:uppercase;color:var(--pst-color-text-muted);font-weight:750}
.tf-p34-status{font-size:.78rem;font-weight:800;border:1px solid var(--pst-color-border);border-radius:999px;padding:.22rem .48rem;white-space:nowrap}
.tf-p34-status.is-met{color:color-mix(in srgb,#2e9d58 88%,var(--pst-color-text-base));border-color:color-mix(in srgb,#2e9d58 62%,var(--pst-color-border));background:color-mix(in srgb,#2e9d58 10%,var(--pst-color-surface))}
.tf-p34-status.is-not-met{color:color-mix(in srgb,#d24b4b 90%,var(--pst-color-text-base));border-color:color-mix(in srgb,#d24b4b 65%,var(--pst-color-border));background:color-mix(in srgb,#d24b4b 9%,var(--pst-color-surface))}
.tf-p34-status.is-unknown{color:var(--pst-color-warning);border-color:color-mix(in srgb,var(--pst-color-warning) 65%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 9%,var(--pst-color-surface))}
.tf-p34-status.is-na{color:var(--pst-color-text-muted);background:color-mix(in srgb,var(--pst-color-border) 20%,transparent)}
.tf-p34-summary{display:grid;grid-template-columns:auto minmax(0,1fr);gap:.35rem .65rem;align-items:start;margin:.65rem 0 .25rem;padding-top:.55rem;border-top:1px solid var(--pst-color-border)}
.tf-p34-summary-label{font-size:.65rem;font-weight:750;letter-spacing:.045em;text-transform:uppercase;color:var(--pst-color-text-muted);padding-top:.2rem;white-space:nowrap}
.tf-p34-summary-items{display:flex;flex-wrap:wrap;gap:.3rem}
.tf-p34-summary-item{display:inline-flex;align-items:center;gap:.3rem;padding:.18rem .34rem;border:1px solid var(--pst-color-border);border-radius:.3rem;font-size:.66rem;background:var(--pst-color-surface);color:inherit}
.tf-p34-summary-item[data-summary-coverage],.tf-p34-summary-item[data-summary-fault]{cursor:pointer}
.tf-p34-summary-item.is-met{border-color:color-mix(in srgb,#2e9d58 55%,var(--pst-color-border))}
.tf-p34-summary-item.is-not-met{border-color:color-mix(in srgb,#d24b4b 60%,var(--pst-color-border));background:color-mix(in srgb,#d24b4b 6%,var(--pst-color-surface))}
.tf-p34-summary-item.is-na{color:var(--pst-color-text-muted)}
.tf-p34-links{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.55rem}
.tf-p34-links a{font-size:.69rem;padding:.2rem .36rem;border:1px solid var(--pst-color-border);border-radius:.3rem;text-decoration:none;background:var(--pst-color-surface)}
.tf-p34-toc{position:sticky;top:calc(var(--pst-header-height,0px) + .35rem);z-index:12;display:flex;gap:.3rem;margin:.4rem 0 .85rem;padding:.32rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:color-mix(in srgb,var(--pst-color-background) 92%,transparent);backdrop-filter:blur(7px)}
.tf-p34-toc a{font-size:.7rem;padding:.2rem .36rem;text-decoration:none;border-radius:.28rem}
.tf-p34-section{margin:1rem 0 1.25rem}
.tf-p34-section-head{display:flex;justify-content:space-between;gap:1rem;align-items:baseline;margin-bottom:.45rem}
.tf-p34-section-head h3{font-size:1rem;margin:0}
.tf-p34-section-head small{color:var(--pst-color-text-muted);font-size:.66rem}
.tf-p34-matrix-wrap{overflow-x:auto}
.tf-p34-matrix{width:100%;min-width:680px;border-collapse:separate;border-spacing:.3rem;table-layout:fixed}
.tf-p34-matrix th{font-size:.67rem;color:var(--pst-color-text-muted);text-align:center;padding:.2rem}
.tf-p34-matrix th:first-child{width:9.5rem;text-align:right}
.tf-p34-cell{width:100%;min-height:3.7rem;padding:.38rem .42rem;border:1px solid var(--pst-color-border);border-radius:.38rem;background:var(--pst-color-surface);text-align:left;cursor:pointer;color:inherit}
.tf-p34-cell strong{display:block;font-size:.72rem}
.tf-p34-cell small{display:block;font-size:.62rem;color:var(--pst-color-text-muted);margin-top:.12rem}
.tf-p34-cell.is-met{border-color:color-mix(in srgb,#2e9d58 68%,var(--pst-color-border));background:color-mix(in srgb,#2e9d58 11%,var(--pst-color-surface))}
.tf-p34-cell.is-not-met{border-color:color-mix(in srgb,#d24b4b 70%,var(--pst-color-border));background:color-mix(in srgb,#d24b4b 10%,var(--pst-color-surface))}
.tf-p34-cell.is-unknown{border-color:color-mix(in srgb,var(--pst-color-warning) 70%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 8%,var(--pst-color-surface))}
.tf-p34-cell.is-na{color:var(--pst-color-text-muted);background:color-mix(in srgb,var(--pst-color-border) 14%,transparent)}
.tf-p34-cell:disabled{cursor:default;opacity:.62}
.tf-p34-cell.is-selected{outline:2px solid var(--pst-color-primary);outline-offset:1px}
.tf-p34-panel{margin:.65rem 0 0;padding:.7rem .8rem;border:1px solid var(--pst-color-border);border-radius:.45rem;background:var(--pst-color-surface)}
.tf-p34-panel-head{display:flex;align-items:center;justify-content:space-between;gap:.7rem;margin-bottom:.55rem}
.tf-p34-panel-head h4{font-size:.88rem;margin:0}
.tf-p34-metrics{width:100%;font-size:.72rem;margin:0}
.tf-p34-metrics th,.tf-p34-metrics td{padding:.28rem .36rem;vertical-align:middle}
.tf-p34-metrics th{text-align:left;color:var(--pst-color-text-muted);font-weight:650;width:34%}
.tf-p34-metrics td:last-child{text-align:right}
.tf-p34-signals{display:grid;gap:.38rem}
.tf-p34-signal{padding:.45rem .5rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:color-mix(in srgb,var(--pst-color-surface) 96%,var(--pst-color-background))}
.tf-p34-signal-top{display:flex;align-items:center;justify-content:space-between;gap:.7rem}
.tf-p34-signal-title{display:inline-flex;align-items:center;gap:.28rem;font-size:.69rem;font-weight:700}
.tf-p34-signal-values{display:flex;gap:.8rem;margin-top:.28rem;font-size:.67rem}
.tf-p34-signal-values span{color:var(--pst-color-text-muted)}
.tf-p34-signal-values strong{color:var(--pst-color-text-base)}
.tf-p34-state-lane{display:flex;flex-wrap:wrap;gap:.28rem;margin-top:.32rem}
.tf-p34-state{display:inline-flex;align-items:center;gap:.22rem;padding:.2rem .32rem;border:1px solid var(--pst-color-border);border-radius:.3rem;font-size:.61rem;color:var(--pst-color-text-muted)}
.tf-p34-state.is-actual,.tf-p34-state.is-target{color:var(--pst-color-text-base);border-color:var(--pst-color-primary)}
.tf-p34-marker{display:inline-block;padding:.04rem .16rem;border-radius:.2rem;font-size:.49rem;font-weight:800;letter-spacing:.03em;background:color-mix(in srgb,var(--pst-color-primary) 12%,var(--pst-color-surface));color:var(--pst-color-primary)}
.tf-p34-items{display:grid;gap:.24rem;margin:.5rem 0}
.tf-p34-item{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:.4rem;align-items:center;font-size:.63rem;border:1px solid var(--pst-color-border);border-radius:.3rem;padding:.28rem .36rem}
.tf-p34-item.is-met{border-color:color-mix(in srgb,#2e9d58 65%,var(--pst-color-border))}
.tf-p34-item.is-not-met{border-color:color-mix(in srgb,#d24b4b 65%,var(--pst-color-border));background:color-mix(in srgb,#d24b4b 7%,var(--pst-color-surface))}
.tf-p34-item code{font-size:.61rem}
.tf-p34-item a{font-size:.61rem;white-space:nowrap}
.tf-p34-signal-name{display:inline-flex;align-items:center;gap:.28rem}
.tf-p34-help{position:relative;display:inline-grid;place-items:center;width:1.05rem;height:1.05rem;padding:0;border:1px solid var(--pst-color-border);border-radius:50%;background:var(--pst-color-surface);color:var(--pst-color-text-muted);font-size:.64rem;font-weight:800;line-height:1;cursor:help}
.tf-p34-help-tip{position:absolute;z-index:40;left:1.25rem;top:auto;bottom:1.25rem;width:min(25rem,72vw);padding:.5rem .58rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-background);color:var(--pst-color-text-base);box-shadow:0 .25rem .8rem color-mix(in srgb,#000 18%,transparent);font-size:.65rem;font-weight:500;line-height:1.4;text-transform:none;letter-spacing:0;opacity:0;visibility:hidden;pointer-events:none}
.tf-p34-help:hover .tf-p34-help-tip,.tf-p34-help:focus .tf-p34-help-tip,.tf-p34-help[aria-expanded="true"] .tf-p34-help-tip{opacity:1;visibility:visible;pointer-events:auto}
.tf-p34-help-tip strong{color:var(--pst-color-text-base)}
.tf-p34-fault-tabs{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.35rem;margin:.5rem 0 .65rem}
.tf-p34-fault-tab{padding:.48rem .5rem;border:1px solid var(--pst-color-border);border-radius:.38rem;background:var(--pst-color-surface);text-align:left;color:inherit;cursor:pointer;min-width:0}
.tf-p34-fault-tab strong{display:block;font-size:.69rem}
.tf-p34-fault-tab span{display:block;font-size:.61rem;color:var(--pst-color-text-muted);margin-top:.18rem}
.tf-p34-fault-tab.is-selected{outline:2px solid var(--pst-color-primary);outline-offset:1px}
.tf-p34-fault-tab.is-met{border-color:color-mix(in srgb,#2e9d58 65%,var(--pst-color-border));background:color-mix(in srgb,#2e9d58 9%,var(--pst-color-surface))}
.tf-p34-fault-tab.is-not-met{border-color:color-mix(in srgb,#d24b4b 68%,var(--pst-color-border));background:color-mix(in srgb,#d24b4b 8%,var(--pst-color-surface))}
.tf-p34-fault-tab.is-na{color:var(--pst-color-text-muted)}
.tf-p34-fault-tab:disabled{cursor:default;opacity:.62}
.tf-p34-fault-classes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.3rem;margin:.45rem 0}
.tf-p34-fault-class{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:.35rem;padding:.34rem .42rem;border:1px solid var(--pst-color-border);border-radius:.3rem;font-size:.64rem;align-items:center}
.tf-p34-history{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.4rem}
.tf-p34-history>div{padding:.48rem .55rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface)}
.tf-p34-history span{display:block;font-size:.62rem;color:var(--pst-color-text-muted)}
.tf-p34-history strong{font-size:.78rem}
#verification-assurance-map>section[id^="assurance-"]{display:none}
#verification-assurance-map>section[id^="assurance-"].tf-contract-evidence-active{display:block}
@media(max-width:900px){
 .tf-p34-fault-tabs{grid-template-columns:1fr 1fr}
 .tf-p34-history{grid-template-columns:1fr 1fr}
 .tf-p34-summary{grid-template-columns:1fr}
}
</style>
<script>
(function(){
  const model=__MODEL__;
  const contracts=model.contracts||{};
  const levelLabels=Object.fromEntries(model.levels||[]);
  const boundaryLabels=Object.fromEntries(model.boundaries||[]);
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const statusClass=s=>"is-"+String(s||"UNKNOWN").toLowerCase().replaceAll(" ","-");
  const statusLabel=s=>({"MET":"PASS","NOT MET":"FAIL","N/A":"N/A","UNKNOWN":"UNKNOWN"})[String(s||"UNKNOWN")]||String(s||"UNKNOWN");
  const pct=v=>Number.isFinite(Number(v))?Number(v).toFixed(1)+"%":"UNKNOWN";
  const ratioPct=(n,d)=>Number(d)>0?((Number(n)/Number(d))*100).toFixed(1)+"%":"N/A";
  const sections=[...document.querySelectorAll('#verification-assurance-map > section[id^="assurance-"]')];
  const overview=document.getElementById("tf-assurance-overview");
  const intro=document.querySelector(".tf-assurance-intro");
  if(intro) intro.remove();

  function targetCell(c,level,boundary){
    return (c.target.coverage||[]).find(row=>row.level===level&&row.boundary===boundary)||null;
  }
  function actualForTarget(c,target){
    if(!target) return [];
    return (target.items||[]).map(id=>c.coverage_actual[id]).filter(Boolean);
  }
  function passedForTarget(c,target){
    return actualForTarget(c,target).filter(row=>row.result==="passed"&&row.level===target.level&&row.boundary===target.boundary);
  }
  function cellStatus(c,target){
    if(!target) return "N/A";
    return passedForTarget(c,target).length===Number(target.declared_count||0)?"MET":"NOT MET";
  }
  function groupForDepth(c,depth){
    return Object.values(c.fault_actual.groups||{}).find(row=>row.system_reach===depth)||{};
  }
  function faultGroupStats(c,group){
    const required=(group.items||[]).filter(item=>item.state==="required");
    const classes=c.fault_actual.classes||{};
    const exercised=required.filter(item=>classes[item.id]?.exercised);
    const detected=exercised.filter(item=>classes[item.id]?.detected);
    let status="N/A";
    if(required.length) status=(exercised.length===required.length&&detected.length===required.length)?"MET":"NOT MET";
    return {required,exercised,detected,status};
  }
  function implementationSensitivity(c){
    const comp=groupForDepth(c,"component");
    return Number.isFinite(Number(comp.sensitivity))?Number(comp.sensitivity):null;
  }
  function overallStatus(c){
    const signals=[];
    for(const target of c.target.coverage||[]) signals.push(cellStatus(c,target));
    for(const group of c.target.fault_groups||[]){
      const stats=faultGroupStats(c,group);
      if(stats.required.length) signals.push(stats.status);
    }
    const reachFloor=Number(model.policy.mutation_reach_floor);
    const sensitivityFloor=Number(model.policy.mutation_sensitivity_floor);
    for(const [level,checks] of Object.entries(c.target.mutation||{})){
      const group=groupForDepth(c,level);
      if(checks.reach) signals.push(Number(group.mutation_reach)>=reachFloor?"MET":"NOT MET");
      if(checks.sensitivity) signals.push(Number(group.sensitivity)>=sensitivityFloor?"MET":"NOT MET");
    }
    if(signals.includes("NOT MET")) return "NOT MET";
    if(signals.includes("UNKNOWN")) return "UNKNOWN";
    return signals.length?"MET":"UNKNOWN";
  }
  function summaryItem(label,status,kind,key){
    const cls='tf-p34-summary-item '+statusClass(status);
    if(status==='N/A'||!kind) return '<span class="'+cls+'"><strong>'+esc(label)+'</strong><span>'+esc(statusLabel(status))+'</span></span>';
    return '<button type="button" class="'+cls+'" data-summary-'+esc(kind)+'="'+esc(key)+'"><strong>'+esc(label)+'</strong><span>'+esc(statusLabel(status))+'</span></button>';
  }
  function coverageSummary(c){
    const byLevel=new Map((model.levels||[]).map(([level])=>[level,"N/A"]));
    for(const target of c.target.coverage||[]){
      const status=cellStatus(c,target);
      const current=byLevel.get(target.level);
      if(current==="N/A"||status==="NOT MET") byLevel.set(target.level,status);
    }
    return (model.levels||[]).map(([level])=>summaryItem(levelLabels[level]||level,byLevel.get(level)||"N/A","coverage",level)).join('');
  }
  function faultSummary(c){
    return (c.target.fault_groups||[]).map((group,index)=>{
      const stats=faultGroupStats(c,group);
      return summaryItem(group.label,stats.status,"fault",String(index));
    }).join('');
  }
  function headerHtml(c){
    const status=overallStatus(c);
    return '<div class="tf-p34-head" id="ce-overview-'+esc(c.id.toLowerCase())+'">'+
      '<div class="tf-p34-headline"><div><div class="tf-p34-kicker">Verification status</div><h2>'+esc(c.id)+'</h2></div><span class="tf-p34-status '+statusClass(status)+'">'+esc(statusLabel(status))+'</span></div>'+
      '<div class="tf-p34-summary"><div class="tf-p34-summary-label">Test Coverage</div><div class="tf-p34-summary-items">'+coverageSummary(c)+'</div>'+
      '<div class="tf-p34-summary-label">Fault-based</div><div class="tf-p34-summary-items">'+faultSummary(c)+'</div></div>'+
      '<div class="tf-p34-links"><a href="'+esc(c.contract_url)+'">Requirement ↗</a><a href="'+esc(c.target.source_url)+'">Verification profile ↗</a><a href="'+esc(model.policy.url)+'">Test plan ↗</a><a href="verification.html">Execution ↗</a></div>'+
      '</div>';
  }
  function matrixHtml(c,selected){
    let head='<thead><tr><th>Test level</th>'+(model.boundaries||[]).map(row=>'<th>'+esc(row[1])+'</th>').join('')+'</tr></thead>';
    let body='<tbody>';
    for(const [level,label] of model.levels||[]){
      body+='<tr><th>'+esc(label)+'</th>';
      for(const [boundary] of model.boundaries||[]){
        const target=targetCell(c,level,boundary);
        const status=cellStatus(c,target);
        const passed=target?passedForTarget(c,target).length:0;
        const key=level+"|"+boundary;
        const subtitle=target?(passed+" / "+Number(target.declared_count||0)):"";
        const disabled=!target;
        body+='<td><button type="button" class="tf-p34-cell '+statusClass(status)+(selected===key?' is-selected':'')+'"'+(disabled?' disabled aria-disabled="true"':' data-cell="'+esc(key)+'"')+'><strong>'+esc(statusLabel(status))+'</strong><small>'+esc(subtitle)+'</small></button></td>';
      }
      body+='</tr>';
    }
    body+='</tbody>';
    return '<div class="tf-p34-matrix-wrap"><table class="tf-p34-matrix">'+head+body+'</table></div>';
  }
  function signalStatus(actual,target){
    if(actual==="UNKNOWN") return "UNKNOWN";
    if(target==="N/A") return actual==="N/A"?"N/A":"UNKNOWN";
    return actual===target?"MET":"NOT MET";
  }
  function representationLabel(key){
    return ({
      synthetic_abstract:"Synthetic / abstract",
      surrogate_simulated:"Surrogate / simulated",
      representative:"Representative",
      actual:"Actual",
      unknown:"UNKNOWN",
    })[key]||String(key||"UNKNOWN");
  }
  function representationHelp(key){
    return ({
      synthetic_abstract:"Constructed analytical or synthetic verification article.",
      surrogate_simulated:"Executable substitute or simulation stands in for the target.",
      representative:"Non-actual article with explicit intended-use pedigree.",
      actual:"The actual target implementation/system/dependency participates.",
    })[key]||"Representation is not classified.";
  }
  function helpButton(text){
    return '<button type="button" class="tf-p34-help" aria-expanded="false" aria-label="Explanation">?<span class="tf-p34-help-tip" role="tooltip">'+esc(text).replaceAll("\n","<br>")+'</span></button>';
  }
  function signalHelp(name){
    return ({
      "Semantic coverage":"Fails when a required behavior case in this cell has no passing evidence.",
      "Representation fidelity":"Stops synthetic or surrogate evidence from being counted as proof that the required target actually ran.",
      "Provenance":"Stops evidence from another test, run, source version, or artifact from being attached to this Requirement.",
      "Producer qualification":"Checks that evidence-producing tools cannot silently turn bad verification into green evidence.",
      "Freshness":"Stops an older result from being reused after code, tests, Gherkin, or verification policy changed.",
    })[name]||"";
  }
  function metricSignalHtml(name,actual,target,status){
    return '<div class="tf-p34-signal"><div class="tf-p34-signal-top"><span class="tf-p34-signal-title">'+esc(name)+helpButton(signalHelp(name))+'</span><span class="tf-p34-status '+statusClass(status)+'">'+esc(statusLabel(status))+'</span></div>'+
      '<div class="tf-p34-signal-values"><span>Actual <strong>'+esc(actual)+'</strong></span><span>Target <strong>'+esc(target)+'</strong></span></div></div>';
  }
  function stateSignalHtml(name,options,actual,target,status){
    const lane=options.map(option=>{
      const isActual=option===actual,isTarget=option===target;
      return '<span class="tf-p34-state'+(isActual?' is-actual':'')+(isTarget?' is-target':'')+'"><span>'+esc(option)+'</span>'+
        (isActual?'<span class="tf-p34-marker">ACTUAL</span>':'')+(isTarget?'<span class="tf-p34-marker">TARGET</span>':'')+'</span>';
    }).join('');
    return '<div class="tf-p34-signal"><div class="tf-p34-signal-top"><span class="tf-p34-signal-title">'+esc(name)+helpButton(signalHelp(name))+'</span><span class="tf-p34-status '+statusClass(status)+'">'+esc(statusLabel(status))+'</span></div><div class="tf-p34-state-lane">'+lane+'</div></div>';
  }
  function coverageDetailHtml(c,key){
    const [level,boundary]=key.split("|");
    const target=targetCell(c,level,boundary);
    if(!target) return '';
    const actual=actualForTarget(c,target);
    const passed=passedForTarget(c,target);
    const status=cellStatus(c,target);
    const actualRep=passed.length&&passed.every(row=>row.representation===passed[0].representation)?passed[0].representation:"unknown";
    const provenance=actual.length&&actual.every(row=>row.provenance==="COMPLETE")?"COMPLETE":actual.length?"INCOMPLETE":"UNKNOWN";
    const producer=actual.length&&actual.every(row=>row.producer_qualification==="QUALIFIED")?"QUALIFIED":actual.length?"UNKNOWN":"UNKNOWN";
    const freshness=actual.length&&actual.every(row=>row.freshness==="CURRENT")?"CURRENT":"UNKNOWN";
    const repActual=representationLabel(actualRep);
    const repTarget=representationLabel(target.representation);
    const repStatus=actualRep==="unknown"?"UNKNOWN":(actualRep===target.representation?"MET":"NOT MET");
    const items=(target.items||[]).map(id=>{
      const row=c.coverage_actual[id];
      const met=row?.result==="passed"&&row.level===target.level&&row.boundary===target.boundary;
      const label=id;
      const semanticHref=c.target.source_url+"#verification-profile-criteria";
      const href=met?(row?.evidence_url||"local-pytest-evidence.html"):semanticHref;
      return '<div class="tf-p34-item '+(met?'is-met':'is-not-met')+'"><span class="tf-p34-status '+statusClass(met?'MET':'NOT MET')+'">'+statusLabel(met?'MET':'NOT MET')+'</span><code>'+esc(label)+'</code><a href="'+esc(href)+'">'+(met?'Evidence ↗':'Criterion ↗')+'</a></div>';
    }).join('');
    const signals=[
      metricSignalHtml("Semantic coverage",String(passed.length),String(target.declared_count),status),
      stateSignalHtml("Representation fidelity",["Synthetic / abstract","Surrogate / simulated","Representative","Actual"],repActual,repTarget,repStatus),
      stateSignalHtml("Provenance",["COMPLETE","INCOMPLETE","UNKNOWN"],provenance,"COMPLETE",signalStatus(provenance,"COMPLETE")),
      stateSignalHtml("Producer qualification",["QUALIFIED","NOT QUALIFIED","UNKNOWN"],producer,"QUALIFIED",signalStatus(producer,"QUALIFIED")),
      stateSignalHtml("Freshness",["CURRENT","STALE","UNKNOWN"],freshness,"CURRENT",signalStatus(freshness,"CURRENT")),
    ].join('');
    return '<div class="tf-p34-panel"><div class="tf-p34-panel-head"><h4>'+esc(levelLabels[level])+' × '+esc(boundaryLabels[boundary])+'</h4><span class="tf-p34-status '+statusClass(status)+'">'+esc(statusLabel(status))+'</span></div>'+
      '<div class="tf-p34-signals">'+signals+'</div>'+
      '<div class="tf-p34-items">'+items+'</div>'+
      '<div class="tf-p34-links"><a href="'+esc(c.contract_url)+'">Requirement ↗</a><a href="'+esc(c.target.source_url)+'">Verification profile ↗</a><a href="test-plan.html#test-plan-configuration-validation-model">Test model ↗</a><a href="requirement-monitor-facts.json">Raw facts ↗</a></div></div>';
  }
  function testCoverageHtml(c,selected){
    const help="Rows = Test Levels; columns = boundary modes (Local no external boundary, Substitute stand-in, Replay recorded, Direct live live dependency); N/A = not required.";
    return '<section class="tf-p34-section" id="ce-coverage-'+esc(c.id.toLowerCase())+'"><div class="tf-p34-section-head"><h3><span class="tf-p34-signal-name">1. Test Coverage'+helpButton(help)+'</span></h3><small>click a required cell for Actual / Target</small></div>'+
      '<div class="tf-p34-matrix-host">'+matrixHtml(c,selected)+'</div><div class="tf-p34-cell-detail">'+coverageDetailHtml(c,selected)+'</div></section>';
  }
  function faultDetectionText(c,group,stats){
    if(group.label==="Implementation"){
      const comp=groupForDepth(c,"component");
      return Number.isFinite(Number(comp.sensitivity))?pct(comp.sensitivity):"UNKNOWN";
    }
    if(!stats.required.length) return "N/A";
    const classes=c.fault_actual.classes||{};
    const detected=stats.exercised.filter(item=>classes[item.id]?.detected).length;
    return stats.exercised.length?(detected+" / "+stats.exercised.length):"N/A";
  }
  function faultTabsHtml(c,selected){
    return '<div class="tf-p34-fault-tabs">'+(c.target.fault_groups||[]).map((group,index)=>{
      const stats=faultGroupStats(c,group);
      const disabled=!stats.required.length;
      if(disabled){
        return '<button type="button" class="tf-p34-fault-tab '+statusClass(stats.status)+'" disabled aria-disabled="true"><strong>'+esc(group.label)+' · N/A</strong><span>No required fault classes</span></button>';
      }
      const coverage=stats.exercised.length+' / '+stats.required.length;
      return '<button type="button" class="tf-p34-fault-tab '+statusClass(stats.status)+(index===selected?' is-selected':'')+'" data-fault-tab="'+index+'"><strong>'+esc(group.label)+' · '+esc(statusLabel(stats.status))+'</strong><span>Coverage '+esc(coverage)+'</span><span>Detection '+esc(faultDetectionText(c,group,stats))+'</span></button>';
    }).join('')+'</div>';
  }
  function faultClassRows(c,group){
    const classes=c.fault_actual.classes||{};
    return (group.items||[]).map(item=>{
      const actual=classes[item.id]||{};
      let status="N/A";
      if(item.state==="required") status=actual.exercised&&actual.detected?"MET":"NOT MET";
      else if(item.state==="optional"&&actual.exercised) status="MET";
      const actualText=actual.exercised?(actual.detected?"DETECTED":"NOT DETECTED"):"NOT EXERCISED";
      const stateLabel=item.state==="na"?"N/A":item.state.toUpperCase();
      let action="";
      if(item.state==="required"&&!actual.exercised) action='<a href="'+esc(c.target.source_url)+'#fault-applicability">Profile ↗</a>';
      else if(actual.exercised) action='<a href="'+esc(c.fault_actual.raw_url)+'">Raw ↗</a>';
      return '<div class="tf-p34-fault-class"><code>'+esc(item.id)+'</code><span>'+esc(stateLabel)+'</span><span class="tf-p34-status '+statusClass(status)+'">'+esc(actualText)+'</span><span>'+action+'</span></div>';
    }).join('');
  }
  function faultMetricHelp(label){
    return ({
      "Required fault classes exercised":"Fails when any required fault class in this group was never challenged.",
      "Exercised classes detected":"Fails when the expected oracle misses a challenged required fault.",
      "Component Mutation Reach":"Fails when too few generated code faults are executed by Component tests.",
      "System Mutation Reach":"Fails when too few generated code faults are executed by System tests.",
      "Component Mutation Sensitivity":"Fails when too many code faults reached by Component tests still survive.",
      "System Mutation Sensitivity":"Fails when too many code faults reached by System tests still survive.",
      "Retained mutmut Test Strength":"Diagnostic retained mutation score; it does not decide PASS or FAIL here.",
    })[label]||"";
  }
  function metricRow(label,actual,target,status){
    return '<tr><th><span class="tf-p34-signal-name">'+esc(label)+helpButton(faultMetricHelp(label))+'</span></th><td>'+esc(actual)+'</td><td>'+esc(target)+'</td><td><span class="tf-p34-status '+statusClass(status)+'">'+esc(statusLabel(status))+'</span></td></tr>';
  }
  function faultDetailHtml(c,index){
    const group=(c.target.fault_groups||[])[index];
    if(!group) return '';
    const stats=faultGroupStats(c,group);
    if(!stats.required.length) return '';
    let metrics='';
    if(group.label==="Implementation"){
      const reachFloor=Number(model.policy.mutation_reach_floor);
      const sensFloor=Number(model.policy.mutation_sensitivity_floor);
      const comp=groupForDepth(c,"component"),sys=groupForDepth(c,"system");
      const mutmut=c.fault_actual.retained_mutmut||{};
      metrics='<table class="tf-p34-metrics"><thead><tr><th>Signal</th><th>Actual</th><th>Target</th><th>Status</th></tr></thead><tbody>'+
        metricRow('Required fault classes exercised',String(stats.exercised.length),String(stats.required.length),stats.status)+
        metricRow('Component Mutation Reach',pct(comp.mutation_reach),'≥ '+reachFloor.toFixed(0)+'%',Number(comp.mutation_reach)>=reachFloor?'MET':'NOT MET')+
        metricRow('System Mutation Reach',pct(sys.mutation_reach),'≥ '+reachFloor.toFixed(0)+'%',Number(sys.mutation_reach)>=reachFloor?'MET':'NOT MET')+
        metricRow('Component Mutation Sensitivity',pct(comp.sensitivity),'≥ '+sensFloor.toFixed(0)+'%',Number(comp.sensitivity)>=sensFloor?'MET':'NOT MET')+
        metricRow('System Mutation Sensitivity',pct(sys.sensitivity),'≥ '+sensFloor.toFixed(0)+'%',Number(sys.sensitivity)>=sensFloor?'MET':'NOT MET')+
        metricRow('Retained mutmut Test Strength',pct(mutmut.score),'DIAGNOSTIC','N/A')+
        '</tbody></table>';
    } else {
      const detected=stats.exercised.filter(item=>c.fault_actual.classes[item.id]?.detected).length;
      metrics='<table class="tf-p34-metrics"><thead><tr><th>Signal</th><th>Actual</th><th>Target</th><th>Status</th></tr></thead><tbody>'+
        metricRow('Required fault classes exercised',String(stats.exercised.length),String(stats.required.length),stats.status)+
        metricRow('Exercised classes detected',String(detected),String(stats.exercised.length),detected===stats.exercised.length?'MET':'NOT MET')+
        '</tbody></table>';
    }
    const groupHelp="Requirement-selected "+group.label+" fault checks.";
    return '<div class="tf-p34-panel"><div class="tf-p34-panel-head"><h4><span class="tf-p34-signal-name">'+esc(group.label)+helpButton(groupHelp)+'</span></h4><span class="tf-p34-status '+statusClass(stats.status)+'">'+esc(statusLabel(stats.status))+'</span></div>'+
      metrics+'<div class="tf-p34-fault-classes">'+faultClassRows(c,group)+'</div>'+
      '<div class="tf-p34-links"><a href="'+esc(c.contract_url)+'">Requirement ↗</a><a href="'+esc(c.target.source_url)+'#fault-applicability">Verification profile ↗</a><a href="test-plan.html#test-plan-fault-model">Fault model ↗</a><a href="mutation-analysis.html#mutation-'+esc(c.id.toLowerCase())+'">Mutation Analysis ↗</a><a href="'+esc(c.fault_actual.raw_url)+'">Raw fault facts ↗</a></div></div>';
  }
  function faultHtml(c,selected){
    const requiredTotal=(c.target.fault_groups||[]).flatMap(g=>g.items||[]).filter(i=>i.state==="required").length;
    const exercisedTotal=(c.target.fault_groups||[]).flatMap(g=>g.items||[]).filter(i=>i.state==="required"&&c.fault_actual.classes[i.id]?.exercised).length;
    const help="Requirement-selected fault checks; N/A means this group has no required fault classes for this Requirement.";
    return '<section class="tf-p34-section" id="ce-faults-'+esc(c.id.toLowerCase())+'"><div class="tf-p34-section-head"><h3><span class="tf-p34-signal-name">2. Fault-based Testing'+helpButton(help)+'</span></h3><small>'+exercisedTotal+' of '+requiredTotal+' required classes exercised</small></div>'+
      '<div class="tf-p34-fault-tabs-host">'+faultTabsHtml(c,selected)+'</div><div class="tf-p34-fault-detail">'+faultDetailHtml(c,selected)+'</div></section>';
  }
  function historyHtml(c){
    const comp=groupForDepth(c,"component"),sys=groupForDepth(c,"system");
    return '<section class="tf-p34-section" id="ce-history-'+esc(c.id.toLowerCase())+'"><div class="tf-p34-section-head"><h3>3. History</h3><small>current comparable target state</small></div>'+
      '<div class="tf-p34-history"><div><span>Verification status</span><strong>'+esc(statusLabel(overallStatus(c)))+'</strong></div><div><span>Component sensitivity</span><strong>'+esc(pct(comp.sensitivity))+'</strong></div><div><span>System sensitivity</span><strong>'+esc(pct(sys.sensitivity))+'</strong></div><div><span>Target revision</span><strong>r'+esc(c.revision??'?')+'</strong></div></div>'+
      (c.history_url?'<div class="tf-p34-links"><a href="'+esc(c.history_url)+'">Full history ↗</a></div>':'')+'</section>';
  }
  function syncMonitorChrome(){
    const header=document.querySelector(".bd-header");
    const toc=document.querySelector(".tf-p34-toc");
    const headerBottom=header?.getBoundingClientRect().bottom||80;
    if(toc) toc.style.top=(headerBottom+8)+"px";
    return {headerBottom,tocHeight:toc?.getBoundingClientRect().height||0};
  }
  function scrollMonitorTarget(element,behavior){
    if(!element) return;
    const chrome=syncMonitorChrome();
    const isInternal=element.classList.contains("tf-p34-section");
    const desiredTop=chrome.headerBottom+(isInternal?chrome.tocHeight+20:16);
    const top=Math.max(0,window.scrollY+element.getBoundingClientRect().top-desiredTop);
    window.scrollTo({top,behavior:behavior||"auto"});
  }
  function firstRequiredFaultIndex(c){
    const index=(c.target.fault_groups||[]).findIndex(group=>faultGroupStats(c,group).required.length>0);
    return index>=0?index:0;
  }
  function contractHtml(c){
    const firstTarget=(c.target.coverage||[]).find(t=>cellStatus(c,t)==="NOT MET")||(c.target.coverage||[])[0];
    const selectedCell=firstTarget?(firstTarget.level+"|"+firstTarget.boundary):"component|none";
    const selectedFault=firstRequiredFaultIndex(c);
    const toc='<nav class="tf-p34-toc" aria-label="Requirement monitor contents"><a href="#ce-coverage-'+esc(c.id.toLowerCase())+'">1 Test Coverage</a><a href="#ce-faults-'+esc(c.id.toLowerCase())+'">2 Fault-based Testing</a><a href="#ce-history-'+esc(c.id.toLowerCase())+'">3 History</a></nav>';
    return '<div class="tf-p34-shell">'+headerHtml(c)+toc+testCoverageHtml(c,selectedCell)+faultHtml(c,selectedFault)+historyHtml(c)+'</div>';
  }
  function installInteractions(section,c){
    let selectedCell=(c.target.coverage||[]).find(t=>cellStatus(c,t)==="NOT MET")||(c.target.coverage||[])[0];
    selectedCell=selectedCell?(selectedCell.level+"|"+selectedCell.boundary):"component|none";
    let selectedFault=firstRequiredFaultIndex(c);
    const rerenderCoverage=()=>{
      section.querySelector('.tf-p34-matrix-host').innerHTML=matrixHtml(c,selectedCell);
      section.querySelector('.tf-p34-cell-detail').innerHTML=coverageDetailHtml(c,selectedCell);
      bindCoverage();
    };
    const bindCoverage=()=>{
      section.querySelectorAll('[data-cell]').forEach(button=>button.addEventListener('click',()=>{
        selectedCell=button.dataset.cell;
        rerenderCoverage();
      }));
    };
    const rerenderFault=()=>{
      section.querySelector('.tf-p34-fault-tabs-host').innerHTML=faultTabsHtml(c,selectedFault);
      section.querySelector('.tf-p34-fault-detail').innerHTML=faultDetailHtml(c,selectedFault);
      bindFault();
    };
    const bindFault=()=>{
      section.querySelectorAll('[data-fault-tab]').forEach(button=>button.addEventListener('click',()=>{
        selectedFault=Number(button.dataset.faultTab||0);
        rerenderFault();
      }));
    };
    const bindSummary=()=>{
      section.querySelectorAll('[data-summary-coverage]').forEach(button=>button.addEventListener('click',()=>{
        const level=button.dataset.summaryCoverage;
        const target=(c.target.coverage||[]).find(row=>row.level===level&&cellStatus(c,row)==='NOT MET')||(c.target.coverage||[]).find(row=>row.level===level);
        if(!target) return;
        selectedCell=target.level+'|'+target.boundary;
        rerenderCoverage();
        scrollMonitorTarget(section,"smooth");
      }));
      section.querySelectorAll('[data-summary-fault]').forEach(button=>button.addEventListener('click',()=>{
        const index=Number(button.dataset.summaryFault);
        const group=(c.target.fault_groups||[])[index];
        if(!group||!faultGroupStats(c,group).required.length) return;
        selectedFault=index;
        rerenderFault();
        scrollMonitorTarget(section.querySelector('#ce-faults-'+c.id.toLowerCase()),"smooth");
      }));
    };
    bindCoverage();
    bindFault();
    bindSummary();
  }

  if(overview){
    const ids=Object.keys(contracts);
    overview.innerHTML=ids.length?'<div class="tf-p34-head"><div class="tf-p34-kicker">Requirement monitors</div>'+ids.map(id=>'<div class="tf-p34-links"><a href="#assurance-'+esc(id.toLowerCase())+'">'+esc(id)+' ↗</a></div>').join('')+'</div>':'';
  }
  for(const section of sections){
    const id=section.id.slice("assurance-".length).toUpperCase();
    const c=contracts[id];
    if(c){
      section.innerHTML=contractHtml(c);
      installInteractions(section,c);
    } else {
      section.innerHTML='<div class="tf-p34-shell"><div class="tf-p34-head"><div class="tf-p34-kicker">Verification status</div><h2>'+esc(id)+'</h2><span class="tf-p34-status is-unknown">UNKNOWN</span><div class="tf-p34-summary"><div class="tf-p34-summary-label">Target</div><div class="tf-p34-summary-items">'+summaryItem("NOT AUTHORED","UNKNOWN",null,null)+'</div></div></div></div>';
    }
  }
  document.addEventListener("click",event=>{
    const button=event.target.closest?.(".tf-p34-help");
    document.querySelectorAll('.tf-p34-help[aria-expanded="true"]').forEach(item=>{
      if(item!==button) item.setAttribute("aria-expanded","false");
    });
    if(!button) return;
    event.preventDefault();
    event.stopPropagation();
    button.setAttribute("aria-expanded",button.getAttribute("aria-expanded")==="true"?"false":"true");
  });
  function show(){
    const target=location.hash.slice(1);
    const anchor=target?document.getElementById(target):null;
    const selected=sections.find(section=>section.id===target)||(anchor?anchor.closest('#verification-assurance-map > section[id^="assurance-"]'):null);
    sections.forEach(section=>section.classList.toggle('tf-contract-evidence-active',section===selected));
    if(overview) overview.hidden=Boolean(selected);
    if(selected){
      const destination=target.startsWith("ce-coverage-")?selected:(anchor&&selected.contains(anchor)?anchor:selected);
      const place=()=>scrollMonitorTarget(destination,"auto");
      window.requestAnimationFrame(place);
      window.setTimeout(place,160);
      window.setTimeout(place,520);
    }
  }
  window.addEventListener("hashchange",show);
  window.addEventListener("resize",syncMonitorChrome);
  window.addEventListener("load",()=>window.setTimeout(show,0),{once:true});
  window.addEventListener("pageshow",()=>window.setTimeout(show,0));
  syncMonitorChrome();
  show();
})();
</script>
<!-- TERNFORGE-P34-REQUIREMENT-MONITOR-END -->"""
    return template.replace("__MODEL__",monitor_json)


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
    model_json=stable_json(model).replace("</","<\\/")
    monitor_model=requirement_monitor_model(model)
    (ASSURANCE_PAGE.parent/"requirement-monitor-facts.json").write_text(
        json.dumps(monitor_model,indent=2,sort_keys=True)+"\n"
    )
    monitor_json=stable_json(monitor_model).replace("</","<\\/")

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
    text=re.sub(
      r'(<h1>Contract Evidence.*?</h1>).*?(?=<section id="assurance-)',
      lambda m:m.group(1)+'\n<div id="tf-assurance-overview"></div>\n',
      text,count=1,flags=re.DOTALL
    )

    block=f"""<!-- TERNFORGE-P33-ASSURANCE-EVIDENCE-START -->
<style>
.tf-assurance-intro{{max-width:70rem;margin-bottom:.85rem}}
#verification-assurance-map>section[id^="assurance-"]{{display:none}}
#verification-assurance-map>section[id^="assurance-"].tf-contract-evidence-active{{display:block}}
.tf-assurance-kicker{{font-size:.69rem;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:var(--pst-color-text-muted)}}
.tf-assurance-claim{{padding:.7rem .8rem;border:1px solid var(--pst-color-border);border-left:4px solid var(--pst-color-primary);border-radius:.35rem;background:var(--pst-color-surface);margin:.45rem 0 .75rem}}
.tf-assurance-claim h3{{margin:.1rem 0 .35rem;font-size:1rem}}
.tf-assurance-claim p{{margin:.2rem 0;font-size:.84rem}}
.tf-assurance-links{{display:flex;gap:.85rem;flex-wrap:wrap;margin-top:.45rem;font-size:.78rem}}
.tf-assurance-profile{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.5rem;margin:.65rem 0 .85rem}}
.tf-assurance-metric{{padding:.55rem .65rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface)}}
.tf-assurance-metric span{{display:block;color:var(--pst-color-text-muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.035em}}
.tf-assurance-metric strong{{display:block;margin-top:.12rem;font-size:.88rem}}
.tf-assurance-section{{margin:1rem 0}}
.tf-assurance-section>h3{{margin-bottom:.25rem;font-size:1rem}}
.tf-assurance-section>p{{font-size:.8rem;color:var(--pst-color-text-muted);margin-top:0}}
.tf-evidence-matrix{{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:.3rem;margin:.3rem 0 .2rem}}
.tf-evidence-matrix th{{font-size:.69rem;color:var(--pst-color-text-muted);font-weight:650;text-align:center;padding:.25rem}}
.tf-evidence-matrix th:first-child{{text-align:right;width:8.5rem}}
.tf-evidence-cell{{height:4.15rem;padding:.42rem .48rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);vertical-align:top;text-align:left}}
.tf-evidence-cell.is-filled{{border-color:color-mix(in srgb,var(--pst-color-primary) 45%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-primary) 8%,var(--pst-color-surface))}}
.tf-evidence-cell.is-target-gap{{border-style:dashed;border-color:color-mix(in srgb,var(--pst-color-warning) 65%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 6%,var(--pst-color-surface))}}
.tf-evidence-cell strong{{display:block;font-size:.78rem}}
.tf-evidence-cell small{{display:block;color:var(--pst-color-text-muted);font-size:.66rem;line-height:1.25;margin-top:.15rem}}
.tf-assurance-envelope-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}}
.tf-assurance-envelope-grid>div>strong{{display:block;font-size:.78rem;margin:0 0 .2rem}}
.tf-assurance-gaps{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem;margin-top:.65rem}}
.tf-assurance-gap{{padding:.55rem .65rem;border-left:3px solid var(--pst-color-warning);background:color-mix(in srgb,var(--pst-color-warning) 7%,transparent);font-size:.78rem}}
.tf-assurance-quality{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.55rem}}
.tf-assurance-quality>div{{padding:.6rem .7rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.78rem}}
.tf-assurance-quality strong{{display:block;margin-bottom:.25rem}}
.tf-assurance-subclaims{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem}}
.tf-assurance-subclaim{{padding:.55rem .65rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.77rem}}
.tf-assurance-subclaim a{{font-weight:650}}
.tf-assurance-evidence-list{{margin-top:.55rem}}
.tf-assurance-evidence-list table{{font-size:.76rem}}
.tf-assurance-overview-metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin:.65rem 0 .85rem}}
.tf-assurance-capabilities{{width:100%;font-size:.76rem}}
.tf-assurance-capabilities td,.tf-assurance-capabilities th{{vertical-align:middle}}
.tf-assurance-goal-row td{{font-weight:700;background:color-mix(in srgb,var(--pst-color-primary) 5%,transparent)}}
.tf-assurance-zero{{color:var(--pst-color-warning);font-weight:700}}
.tf-fault-layer-table{{width:100%;font-size:.76rem}}
.tf-fault-layer-table td,.tf-fault-layer-table th{{vertical-align:top}}
.tf-fault-layer-kind{{font-size:.64rem;color:var(--pst-color-text-muted);text-transform:uppercase;letter-spacing:.03em}}
.tf-assurance-history-frame{{display:block;width:100%;height:360px;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface)}}
.tf-target-card{{padding:.75rem .85rem;border:1px solid var(--pst-color-border);border-left:4px solid var(--pst-color-primary);border-radius:.4rem;background:var(--pst-color-surface);margin:.6rem 0}}
.tf-target-card h4{{margin:.05rem 0 .3rem;font-size:.92rem}}
.tf-target-card p{{margin:.22rem 0;font-size:.78rem}}
.tf-target-status{{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .45rem;border-radius:999px;font-size:.69rem;font-weight:700;border:1px solid var(--pst-color-border)}}
.tf-target-status.is-met{{border-color:color-mix(in srgb,#2e9d58 65%,var(--pst-color-border));background:color-mix(in srgb,#2e9d58 11%,var(--pst-color-surface))}}
.tf-target-status.is-gap{{border-color:color-mix(in srgb,var(--pst-color-warning) 75%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 10%,var(--pst-color-surface))}}
.tf-obligation-table{{width:100%;font-size:.75rem}}
.tf-obligation-table td,.tf-obligation-table th{{vertical-align:top}}
.tf-obligation-ok{{font-weight:750;color:color-mix(in srgb,#2e9d58 88%,var(--pst-color-text-base))}}
.tf-obligation-gap{{font-weight:750;color:var(--pst-color-warning)}}
.tf-evidence-cell.is-target-met{{border-color:color-mix(in srgb,#2e9d58 70%,var(--pst-color-border));background:color-mix(in srgb,#2e9d58 12%,var(--pst-color-surface))}}
.tf-evidence-cell.is-target-missing{{border:2px dashed color-mix(in srgb,var(--pst-color-warning) 78%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 10%,var(--pst-color-surface))}}
.tf-evidence-cell.is-target-partial{{border:2px solid color-mix(in srgb,var(--pst-color-warning) 78%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 7%,var(--pst-color-surface))}}
.tf-evidence-cell.is-extra{{border-color:color-mix(in srgb,var(--pst-color-primary) 55%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-primary) 8%,var(--pst-color-surface))}}
.tf-frontier-legend{{display:flex;flex-wrap:wrap;gap:.45rem;margin:.35rem 0 .6rem;font-size:.69rem;color:var(--pst-color-text-muted)}}
.tf-frontier-legend span{{padding:.2rem .4rem;border:1px solid var(--pst-color-border);border-radius:999px;background:var(--pst-color-surface)}}
.tf-evidence-path-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}}
.tf-evidence-path{{padding:.65rem .7rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface);font-size:.75rem}}
.tf-evidence-path h4{{margin:.05rem 0 .35rem;font-size:.82rem}}
.tf-evidence-path dl{{display:grid;grid-template-columns:7.5rem 1fr;gap:.15rem .5rem;margin:.2rem 0}}
.tf-evidence-path dt{{color:var(--pst-color-text-muted);font-weight:650}}
.tf-evidence-path dd{{margin:0}}
.tf-assurance-gap.is-blocking{{border-left-color:var(--pst-color-warning)}}
.tf-assurance-gap.is-info{{border-left-color:var(--pst-color-primary);background:color-mix(in srgb,var(--pst-color-primary) 6%,transparent)}}
.tf-contract-nav{{display:flex;flex-wrap:wrap;gap:.35rem;margin:.45rem 0 .75rem;padding:.45rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface)}}
.tf-contract-nav a{{font-size:.72rem;padding:.25rem .42rem;border:1px solid var(--pst-color-border);border-radius:.3rem;text-decoration:none}}
.tf-qualifier-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}}
.tf-qualifier-card{{padding:.6rem .7rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface);font-size:.75rem}}
.tf-qualifier-card h4{{margin:.05rem 0 .3rem;font-size:.82rem}}
.tf-qualifier-scale{{display:flex;gap:.2rem;flex-wrap:wrap;margin:.3rem 0}}
.tf-qualifier-step{{padding:.18rem .34rem;border:1px solid var(--pst-color-border);border-radius:999px;font-size:.65rem;color:var(--pst-color-text-muted)}}
.tf-qualifier-step.is-actual{{font-weight:750;color:var(--pst-color-text-base);border-color:var(--pst-color-primary);background:color-mix(in srgb,var(--pst-color-primary) 9%,var(--pst-color-surface))}}
.tf-fault-detail{{margin:.65rem 0;padding:.65rem .75rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface)}}
.tf-fault-detail>summary{{cursor:pointer;font-weight:750;font-size:.83rem}}
.tf-fault-detail dl{{display:grid;grid-template-columns:11rem 1fr;gap:.18rem .55rem;margin:.55rem 0;font-size:.74rem}}
.tf-fault-detail dt{{font-weight:650;color:var(--pst-color-text-muted)}}
.tf-fault-detail dd{{margin:0;min-width:0;overflow-wrap:anywhere}}
.tf-mutant-table{{font-size:.69rem;min-width:900px}}
.tf-mutant-table td,.tf-mutant-table th{{vertical-align:top}}
.tf-state-killed{{font-weight:750;color:color-mix(in srgb,#2e9d58 88%,var(--pst-color-text-base))}}
.tf-state-survived{{font-weight:750;color:var(--pst-color-warning)}}
.tf-argument-tree{{display:grid;gap:.45rem;margin:.55rem 0}}
.tf-argument-node{{padding:.55rem .65rem;border:1px solid var(--pst-color-border);border-left:3px solid var(--pst-color-primary);border-radius:.35rem;background:var(--pst-color-surface);font-size:.75rem}}
.tf-argument-node.is-gap{{border-left-color:var(--pst-color-warning)}}
.tf-argument-children{{margin:.35rem 0 0 1rem;padding-left:.6rem;border-left:1px solid var(--pst-color-border)}}
.tf-incident-loop{{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;margin:.55rem 0}}
.tf-incident-step{{padding:.35rem .5rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.7rem;max-width:15rem}}
.tf-incident-arrow{{color:var(--pst-color-text-muted);font-weight:750}}
.tf-history-events{{display:grid;gap:.35rem}}
.tf-history-event{{padding:.45rem .55rem;border-left:3px solid var(--pst-color-primary);background:color-mix(in srgb,var(--pst-color-primary) 5%,transparent);font-size:.72rem}}
.tf-path-links{{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.45rem}}
.tf-path-links a,.tf-path-links span{{font-size:.68rem;padding:.18rem .32rem;border:1px solid var(--pst-color-border);border-radius:.3rem}}
.tf-assurance-model{{padding:.7rem .8rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface);font-size:.76rem;margin:.75rem 0}}
.tf-assurance-model-grid{{display:grid;grid-template-columns:1.2fr 1fr;gap:.55rem}}
.tf-assurance-model-line{{display:grid;grid-template-columns:1fr auto;gap:.6rem;padding:.28rem .4rem;border-bottom:1px solid var(--pst-color-border)}}
.tf-assurance-model-line:last-child{{border-bottom:0}}
.tf-assurance-formula{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.35rem;margin-top:.55rem}}
.tf-assurance-formula div{{padding:.35rem .45rem;border:1px solid var(--pst-color-border);border-radius:.3rem;background:color-mix(in srgb,var(--pst-color-primary) 4%,var(--pst-color-surface))}}
.tf-target-progress{{height:.8rem;border:1px solid var(--pst-color-border);border-radius:999px;overflow:hidden;background:var(--pst-color-surface);margin:.45rem 0 .25rem}}
.tf-target-progress>span{{display:block;height:100%;background:var(--pst-color-primary)}}
.tf-target-summary{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;margin:.45rem 0 .6rem}}
.tf-target-summary>div{{padding:.45rem .55rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface)}}
.tf-target-summary span{{display:block;font-size:.66rem;color:var(--pst-color-text-muted);text-transform:uppercase}}
.tf-target-summary strong{{font-size:.86rem}}
.tf-scale-wrap{{margin:.35rem 0 .15rem}}
.tf-scale-labels{{display:flex;justify-content:space-between;gap:.25rem;font-size:.63rem;color:var(--pst-color-text-muted)}}
.tf-scale-track{{position:relative;height:.38rem;background:color-mix(in srgb,var(--pst-color-border) 70%,transparent);border-radius:999px;margin:.5rem .1rem .65rem}}
.tf-scale-marker{{position:absolute;top:50%;width:.72rem;height:.72rem;border-radius:50%;transform:translate(-50%,-50%);border:2px solid var(--pst-color-surface);box-shadow:0 0 0 1px var(--pst-color-border)}}
.tf-scale-marker.is-actual{{background:var(--pst-color-primary)}}
.tf-scale-marker.is-target{{background:var(--pst-color-warning);border-radius:.1rem}}
.tf-scale-caption{{display:flex;gap:.8rem;flex-wrap:wrap;font-size:.66rem;color:var(--pst-color-text-muted)}}
.tf-concrete-path{{padding:.55rem .65rem;border-left:3px solid var(--pst-color-primary);background:color-mix(in srgb,var(--pst-color-primary) 5%,transparent);font-size:.74rem;margin-top:.65rem}}
.tf-concrete-path dl{{display:grid;grid-template-columns:9rem 1fr;gap:.12rem .45rem;margin:.25rem 0}}
.tf-concrete-path dt{{font-weight:650;color:var(--pst-color-text-muted)}}
.tf-concrete-path dd{{margin:0}}
.tf-fault-ladder{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.4rem;margin:.55rem 0 .75rem}}
.tf-fault-rung{{position:relative;padding:.55rem .6rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.7rem}}
.tf-fault-rung strong{{display:block;margin-bottom:.25rem}}
.tf-fault-rung ul{{margin:.2rem 0 0;padding-left:1rem}}
.tf-depth-table{{width:100%;font-size:.72rem}}
.tf-depth-table th,.tf-depth-table td{{text-align:right;vertical-align:top}}
.tf-depth-table th:first-child,.tf-depth-table td:first-child{{text-align:left}}
.tf-trust-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem}}
.tf-trust-card{{padding:.55rem .65rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.74rem}}
.tf-trust-card h4{{margin:.05rem 0 .25rem;font-size:.8rem}}
.tf-page-flow{{display:grid;gap:.35rem;justify-items:center;margin:.55rem 0}}
.tf-flow-box{{padding:.35rem .55rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.72rem;text-align:center}}
.tf-flow-triad{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.4rem;width:100%}}
.tf-flow-arrow{{color:var(--pst-color-text-muted);font-weight:750}}
.tf-responsibility-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem}}
.tf-responsibility-item{{padding:.5rem .6rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.72rem}}
.tf-incident-branch{{display:grid;grid-template-columns:1fr 1fr;gap:.55rem;margin:.6rem 0}}
.tf-incident-branch>div{{padding:.55rem .65rem;border:1px solid var(--pst-color-border);border-radius:.35rem;background:var(--pst-color-surface);font-size:.72rem}}
.tf-history-trend{{width:100%;font-size:.72rem}}
.tf-history-trend th,.tf-history-trend td{{vertical-align:top}}
.bd-article-container{{overflow:visible!important}}
.tf-contract-shell{{max-width:74rem}}
.tf-contract-head{{margin-bottom:.75rem}}
.tf-contract-head h2{{margin:.15rem 0 .35rem;font-size:1.35rem}}
.tf-contract-claim{{font-size:.94rem;line-height:1.45;margin:.3rem 0 .45rem}}
.tf-contract-meta{{font-size:.73rem;color:var(--pst-color-text-muted)}}
.tf-external-nav{{display:flex;flex-wrap:wrap;gap:.3rem;margin:.45rem 0 .65rem}}
.tf-external-nav a{{font-size:.68rem;padding:.22rem .38rem;border:1px solid var(--pst-color-border);border-radius:.32rem;text-decoration:none;background:var(--pst-color-surface)}}
.tf-sticky-toc{{position:sticky;top:calc(var(--pst-header-height,0px) + .45rem);z-index:12;display:flex;gap:.25rem;overflow-x:auto;padding:.35rem;margin:.5rem 0 .85rem;border:1px solid var(--pst-color-border);border-radius:.45rem;background:color-mix(in srgb,var(--pst-color-background) 94%,transparent);backdrop-filter:blur(8px);box-shadow:0 2px 8px color-mix(in srgb,#000 10%,transparent)}}
.tf-sticky-toc a{{flex:0 0 auto;font-size:.69rem;padding:.24rem .4rem;border-radius:.28rem;text-decoration:none;color:var(--pst-color-text-base)}}
.tf-sticky-toc a:hover,.tf-sticky-toc a:focus{{background:color-mix(in srgb,var(--pst-color-primary) 10%,transparent)}}
.tf-overview-strip{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;margin:.55rem 0 .45rem}}
.tf-stage-card{{position:relative;padding:.6rem .68rem;border:1px solid var(--pst-color-border);border-radius:.45rem;background:var(--pst-color-surface);min-height:4.2rem}}
.tf-stage-card span{{display:block;font-size:.64rem;text-transform:uppercase;letter-spacing:.04em;color:var(--pst-color-text-muted)}}
.tf-stage-card strong{{display:block;font-size:1.05rem;margin-top:.12rem}}
.tf-stage-card small{{display:block;font-size:.66rem;color:var(--pst-color-text-muted);margin-top:.12rem}}
.tf-stage-card.is-gap{{border-color:color-mix(in srgb,var(--pst-color-warning) 75%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 8%,var(--pst-color-surface))}}
.tf-stage-card.is-actual{{border-color:color-mix(in srgb,var(--pst-color-primary) 58%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-primary) 7%,var(--pst-color-surface))}}
.tf-model-rule{{font-size:.69rem;color:var(--pst-color-text-muted);margin:.25rem 0 .55rem}}
.tf-disclosure{{margin:.45rem 0;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface)}}
.tf-disclosure>summary{{cursor:pointer;padding:.48rem .62rem;font-size:.76rem;font-weight:700}}
.tf-disclosure[open]>summary{{border-bottom:1px solid var(--pst-color-border)}}
.tf-disclosure-body{{padding:.55rem .65rem;font-size:.74rem}}
.tf-disclosure-body p{{margin:.25rem 0}}
.tf-section{{margin:1.15rem 0 1.35rem;scroll-margin-top:5.5rem}}
.tf-section-head{{display:flex;align-items:baseline;gap:.45rem;margin-bottom:.45rem}}
.tf-section-head h3{{margin:0;font-size:1.05rem}}
.tf-section-head small{{color:var(--pst-color-text-muted);font-size:.68rem}}
.tf-frontier-compact .tf-evidence-cell{{height:3.2rem;text-align:center;vertical-align:middle;padding:.28rem}}
.tf-frontier-compact .tf-evidence-cell strong{{font-size:1rem}}
.tf-frontier-compact .tf-evidence-cell small{{font-size:.62rem;line-height:1.15}}
.tf-frontier-compact .tf-evidence-matrix th:first-child{{width:7.7rem}}
.tf-frontier-legend-mini{{display:flex;gap:.55rem;flex-wrap:wrap;font-size:.65rem;color:var(--pst-color-text-muted);margin:.2rem 0 .45rem}}
.tf-frontier-legend-mini b{{color:var(--pst-color-text-base)}}
.tf-qualifier-strip{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.4rem;margin-top:.65rem}}
.tf-mini-gauge{{padding:.48rem .55rem;border:1px solid var(--pst-color-border);border-radius:.38rem;background:var(--pst-color-surface)}}
.tf-mini-gauge strong{{display:block;font-size:.72rem;margin-bottom:.2rem}}
.tf-mini-gauge .tf-scale-labels{{font-size:.58rem}}
.tf-mini-gauge .tf-scale-caption{{font-size:.6rem}}
.tf-fault-strip{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;margin:.35rem 0 .7rem}}
.tf-fault-node{{padding:.58rem .62rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface);min-height:5rem}}
.tf-fault-node span{{display:block;font-size:.61rem;color:var(--pst-color-text-muted);text-transform:uppercase}}
.tf-fault-node strong{{display:block;font-size:.98rem;margin:.15rem 0 .1rem}}
.tf-fault-node small{{font-size:.65rem;color:var(--pst-color-text-muted)}}
.tf-compare{{display:grid;gap:.38rem;margin:.45rem 0}}
.tf-compare-row{{display:grid;grid-template-columns:8rem 1fr 1fr;gap:.5rem;align-items:center;font-size:.7rem}}
.tf-compare-label{{font-weight:700}}
.tf-bar-wrap{{display:grid;grid-template-columns:4.7rem 1fr 3.3rem;gap:.35rem;align-items:center}}
.tf-bar-wrap span:first-child{{font-size:.62rem;color:var(--pst-color-text-muted)}}
.tf-bar-track{{height:.46rem;border-radius:999px;background:color-mix(in srgb,var(--pst-color-border) 70%,transparent);overflow:hidden}}
.tf-bar-fill{{height:100%;background:var(--pst-color-primary)}}
.tf-bar-fill.is-gap{{background:var(--pst-color-warning)}}
.tf-bar-value{{font-size:.65rem;text-align:right}}
.tf-trust-strip{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.4rem;margin:.4rem 0 .65rem}}
.tf-trust-item{{padding:.52rem .58rem;border:1px solid var(--pst-color-border);border-radius:.38rem;background:var(--pst-color-surface);min-height:4.5rem}}
.tf-trust-item span{{display:block;font-size:.6rem;color:var(--pst-color-text-muted);text-transform:uppercase}}
.tf-trust-item strong{{display:block;font-size:.88rem;margin:.16rem 0}}
.tf-trust-item small{{display:block;font-size:.62rem;color:var(--pst-color-text-muted)}}
.tf-trust-item.is-gap{{border-color:color-mix(in srgb,var(--pst-color-warning) 72%,var(--pst-color-border));background:color-mix(in srgb,var(--pst-color-warning) 7%,var(--pst-color-surface))}}
.tf-gap-hero{{padding:.72rem .78rem;border:1px solid color-mix(in srgb,var(--pst-color-warning) 72%,var(--pst-color-border));border-radius:.45rem;background:color-mix(in srgb,var(--pst-color-warning) 7%,var(--pst-color-surface));margin:.35rem 0 .6rem}}
.tf-gap-hero h4{{margin:.05rem 0 .28rem;font-size:.88rem}}
.tf-threshold{{display:grid;grid-template-columns:6rem 1fr 3.5rem;gap:.45rem;align-items:center;margin:.3rem 0;font-size:.68rem}}
.tf-threshold-track{{position:relative;height:.52rem;border-radius:999px;background:color-mix(in srgb,var(--pst-color-border) 72%,transparent);overflow:visible}}
.tf-threshold-fill{{height:100%;border-radius:999px;background:var(--pst-color-warning)}}
.tf-threshold-marker{{position:absolute;top:-.18rem;bottom:-.18rem;width:2px;background:var(--pst-color-text-base);transform:translateX(-1px)}}
.tf-path-group-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem;margin:.4rem 0}}
.tf-path-group{{padding:.65rem .7rem;border:1px solid var(--pst-color-border);border-radius:.42rem;background:var(--pst-color-surface)}}
.tf-path-group h4{{margin:.05rem 0 .28rem;font-size:.85rem}}
.tf-path-group-stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.25rem;margin:.25rem 0}}
.tf-path-group-stats div{{padding:.28rem .32rem;border-radius:.28rem;background:color-mix(in srgb,var(--pst-color-primary) 5%,transparent);font-size:.63rem}}
.tf-exact-path{{display:grid;grid-template-columns:minmax(12rem,1.4fr) repeat(3,minmax(5.5rem,.6fr)) auto;gap:.45rem;align-items:center;padding:.42rem 0;border-bottom:1px solid var(--pst-color-border);font-size:.68rem}}
.tf-exact-path:last-child{{border-bottom:0}}
.tf-exact-path-links{{display:flex;gap:.25rem;flex-wrap:wrap}}
.tf-exact-path-links a,.tf-exact-path-links span{{font-size:.62rem;padding:.14rem .26rem;border:1px solid var(--pst-color-border);border-radius:.25rem;text-decoration:none}}
.tf-history-visual{{display:grid;gap:.36rem;margin:.4rem 0}}
.tf-history-row{{display:grid;grid-template-columns:10rem 1fr 5rem;gap:.5rem;align-items:center;font-size:.68rem}}
.tf-history-track{{height:.42rem;border-radius:999px;background:color-mix(in srgb,var(--pst-color-border) 72%,transparent);overflow:hidden}}
.tf-history-track span{{display:block;height:100%;background:var(--pst-color-primary)}}
.tf-history-values{{font-size:.64rem;text-align:right;color:var(--pst-color-text-muted)}}
.tf-investigate-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;margin:.4rem 0 .6rem}}
.tf-investigate-card{{padding:.58rem .62rem;border:1px solid var(--pst-color-border);border-radius:.4rem;background:var(--pst-color-surface);font-size:.7rem}}
.tf-investigate-card strong{{display:block;margin-bottom:.18rem}}
.tf-investigate-card a{{font-size:.66rem}}
.tf-flow-compact{{display:flex;align-items:center;gap:.25rem;flex-wrap:wrap;font-size:.66rem}}
.tf-flow-compact span{{padding:.25rem .35rem;border:1px solid var(--pst-color-border);border-radius:.28rem;background:var(--pst-color-surface)}}
.tf-flow-compact b{{color:var(--pst-color-text-muted)}}
@media(max-width:950px){{.tf-overview-strip,.tf-fault-strip,.tf-qualifier-strip{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tf-trust-strip{{grid-template-columns:repeat(3,minmax(0,1fr))}}.tf-investigate-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tf-compare-row{{grid-template-columns:7rem 1fr}}.tf-compare-row>.tf-bar-wrap:last-child{{grid-column:2}}}}
@media(max-width:700px){{.tf-overview-strip,.tf-fault-strip,.tf-qualifier-strip,.tf-trust-strip,.tf-path-group-grid,.tf-investigate-grid{{grid-template-columns:1fr}}.tf-sticky-toc{{top:.25rem}}.tf-exact-path{{grid-template-columns:1fr 1fr}}.tf-exact-path>:first-child{{grid-column:1/-1}}.tf-exact-path-links{{grid-column:1/-1}}.tf-history-row{{grid-template-columns:7rem 1fr}}.tf-history-values{{grid-column:2;text-align:left}}}}
@media(max-width:950px){{.tf-assurance-profile{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tf-assurance-quality,.tf-assurance-overview-metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tf-assurance-envelope-grid{{grid-template-columns:1fr}}.tf-fault-ladder{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tf-flow-triad{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.tf-assurance-gaps,.tf-assurance-subclaims,.tf-assurance-quality,.tf-assurance-overview-metrics,.tf-target-summary,.tf-assurance-model-grid,.tf-assurance-formula,.tf-trust-grid,.tf-responsibility-grid,.tf-incident-branch{{grid-template-columns:1fr}}.tf-evidence-matrix{{min-width:650px}}.tf-assurance-matrix-scroll{{overflow-x:auto}}}}
</style>
<script id="tf-assurance-model" type="application/json">{model_json}</script>
<script>
(() => {{
  const model=JSON.parse(document.getElementById("tf-assurance-model").textContent);
  const root=document.getElementById("verification-assurance-map");
  if(!root) return;
  const sections=[...root.querySelectorAll(':scope > section[id^="assurance-"]')];
  const reachLabels={{component:"Component",component_integration:"Component integration",system:"System",system_integration:"System integration"}};
  const boundaryLabels={{none:"Local only",substitute:"Substitute",replay:"Replay",direct:"Direct live"}};
  const repLabels={{synthetic_abstract:"Synthetic / abstract",surrogate_simulated:"Surrogate / simulated",representative:"Representative",actual:"Actual target"}};
  const kindLabels={{bdd:"Behavior",unit:"Unit",integration:"Integration",property:"Property",e2e:"E2E"}};
  const esc=value=>String(value??"").replace(/[&<>\"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c]));
  const contracts=model.contracts||{{}};
  const rank=(order,value)=>Math.max(order.indexOf(value),-1);
  const unique=values=>[...new Set(values.filter(Boolean))];
  const maxBy=(rows,key,order)=>rows.reduce((best,row)=>rank(order,row[key])>rank(order,best)?row[key]:best,null);
  const methods=rows=>unique(rows.map(row=>row.kind));
  const contractLink=id=>'verification-assurance.html#assurance-'+id.toLowerCase();

  const faultModel=model.fault_model||{{}};
  const percent=value=>value===null||value===undefined?'n/a':Number(value).toFixed(1)+'%';
  const coverage=(ids,predicate)=>ids.filter(id=>predicate(contracts[id]||{{}})).length;
  const hasSystemEvidence=c=>(c.direct||[]).some(e=>e.reach==='system'||e.reach==='system_integration');
  const hasDirectEvidence=c=>(c.direct||[]).some(e=>e.boundary==='direct');
  const hasDiversity=c=>methods(c.direct||[]).length>=2;
  const targetObligations=c=>(c.target&&c.target.obligations)||[];
  const faultFact=c=>((faultModel.contracts||{{}})[c.id]||{{}});

  function targetText(o) {{
    if(o.kind==='frontier_cell') return (reachLabels[o.reach]||o.reach)+' × '+(boundaryLabels[o.boundary]||o.boundary)+(o.representation_min?' · representation ≥ '+(repLabels[o.representation_min]||o.representation_min):'');
    if(o.kind==='method_count') return '≥ '+Number(o.min||0)+' verification method types';
    if(o.kind==='mutation_reach') return 'Mutation Reach ≥ '+Number(o.min||0).toFixed(1)+'% · '+esc(o.group||'');
    if(o.kind==='mutation_sensitivity') return 'Sensitivity ≥ '+Number(o.min||0).toFixed(1)+'% · '+esc(o.group||'');
    if(o.kind==='test_strength') return 'Covered-mutant Test Strength ≥ '+Number(o.min||0).toFixed(1)+'%';
    if(o.kind==='fault_layer') return 'Fault layer challenged · '+esc(o.layer||'');
    return esc(o.kind||'obligation');
  }}

  function obligationResult(c,o) {{
    const rows=c.direct||[];
    const fact=faultFact(c);
    if(o.kind==='frontier_cell') {{
      const matching=rows.filter(e=>e.reach===o.reach&&e.boundary===o.boundary);
      const strongest=maxBy(matching,'representation',model.representation_order||[]);
      const repOk=!o.representation_min||matching.some(e=>rank(model.representation_order||[],e.representation)>=rank(model.representation_order||[],o.representation_min));
      return {{met:matching.length>0&&repOk,actual:matching.length?matching.length+' path(s) · strongest representation '+(repLabels[strongest]||strongest||'n/a'):'0 matching paths',value:matching.length,evidenceIds:matching.map(e=>e.id)}};
    }}
    if(o.kind==='method_count') {{
      const count=methods(rows).length;
      return {{met:count>=Number(o.min||0),actual:count+' method type(s)',value:count,methods:methods(rows)}};
    }}
    if(o.kind==='mutation_reach'||o.kind==='mutation_sensitivity') {{
      const group=(fact.groups||{{}})[o.group]||{{}};
      const key=o.kind==='mutation_reach'?'mutation_reach':'sensitivity';
      const value=group[key];
      return {{met:value!==null&&value!==undefined&&Number(value)>=Number(o.min||0),actual:value===null||value===undefined?'not measured':percent(value),value:value}};
    }}
    if(o.kind==='test_strength') {{
      const value=c.strength?.score;
      return {{met:value!==null&&value!==undefined&&Number(value)>=Number(o.min||0),actual:value===null||value===undefined?'not measured':percent(value)+' · killed/(killed+survived) on covered valid mutants',value:value}};
    }}
    if(o.kind==='fault_layer') {{
      const layer=(fact.layers||{{}})[o.layer]||{{}};
      const generated=Number(layer.generated||0), detected=Number(layer.detected||0);
      return {{met:generated>0&&detected>0,actual:generated?detected+'/'+generated+' detected · '+(layer.engine||'unknown engine'):'not exercised',value:detected}};
    }}
    return {{met:false,actual:'unsupported obligation type',value:null}};
  }}

  function targetResults(c) {{
    return targetObligations(c).map(o=>({{obligation:o,...obligationResult(c,o)}}));
  }}

  function targetOverviewHtml(c) {{
    const t=c.target;
    const results=targetResults(c);
    const blocking=results.filter(r=>r.obligation.blocking!==false);
    const met=blocking.filter(r=>r.met).length;
    const gaps=blocking.length-met;
    const pathCount=(c.direct||[]).length;
    const ratio=blocking.length?Math.round((met/blocking.length)*100):0;
    const obligations=results.map(r=>'<tr><td>'+esc(r.obligation.label||r.obligation.id)+'</td><td>'+targetText(r.obligation)+'</td><td>'+esc(r.actual)+'</td><td class="'+(r.met?'tf-obligation-ok':'tf-obligation-gap')+'">'+(r.met?'✓':'GAP')+'</td></tr>').join('');
    const profile=t?'<details class="tf-disclosure"><summary>Target profile · '+esc(t.profile_name||t.profile_id||'Verification profile')+' · v'+esc(t.target_revision??'?')+'</summary><div class="tf-disclosure-body"><p><strong>Why:</strong> '+esc(t.rationale||t.profile_rationale||'No rationale recorded.')+'</p><p><strong>Source:</strong> '+esc(t.source||t.profile_source||'not recorded')+' · <strong>Cadence:</strong> '+esc(t.cadence?.mode||'not recorded')+' · <strong>Freshness:</strong> '+esc(t.freshness?.policy||'not recorded')+'</p><p><a href="assurance-targets.json">Raw target definition →</a></p><div class="pst-scrollable-table-container"><table class="table tf-obligation-table"><thead><tr><th>Obligation</th><th>Target</th><th>Actual</th><th>Status</th></tr></thead><tbody>'+obligations+'</tbody></table></div></div></details>':'<details class="tf-disclosure"><summary>Target profile · not declared</summary><div class="tf-disclosure-body">No explicit Assurance Target is declared. Untargeted theoretical possibilities stay neutral.</div></details>';
    return '<div class="tf-overview-strip" aria-label="Possible Target Actual Gap">'+
      '<div class="tf-stage-card" tabindex="0" title="Theoretical System Reach × Boundary Reality space. Untargeted cells are possibilities, not gaps."><span>Possible</span><strong>4 × 4</strong><small>Reach × Boundary topology</small></div>'+
      '<div class="tf-stage-card" tabindex="0" title="What this versioned Assurance Target says must be demonstrated."><span>Must</span><strong>'+(t?blocking.length:'—')+'</strong><small>'+(t?'blocking obligations':'Target not declared')+'</small></div>'+
      '<div class="tf-stage-card is-actual" tabindex="0" title="Actual evidence evaluated against the current Target. This is obligation completion, not a confidence score."><span>Actual</span><strong>'+(t?met+' / '+blocking.length:pathCount+' paths')+'</strong><small>'+pathCount+' retained evidence path'+(pathCount===1?'':'s')+'</small></div>'+
      '<div class="tf-stage-card'+(gaps?' is-gap':'')+'" tabindex="0" title="Only Target minus Actual is a blocking assurance gap."><span>Gap</span><strong>'+(t?gaps:'—')+'</strong><small>'+(t?'blocking obligation'+(gaps===1?'':'s'):'not evaluated')+'</small></div>'+
      '</div>'+
      (t?'<div class="tf-target-progress" aria-label="'+met+' of '+blocking.length+' target obligations met"><span style="width:'+ratio+'%"></span></div>':'')+
      '<div class="tf-model-rule"><strong>Possible ≠ Must ≠ Actual.</strong> Possible − Must is optional. <strong>Must − Actual is the GAP.</strong> '+(t?met+' / '+blocking.length+' is obligation completion, not confidence.':'')+'</div>'+profile;
  }}

  function scaleHtml(labels,actual,target) {{
    const pos=value=>{{const i=labels.indexOf(value);return i<0?null:(labels.length===1?50:(i/(labels.length-1))*100);}};
    const ap=pos(actual),tp=pos(target);
    return '<div class="tf-scale-wrap"><div class="tf-scale-labels">'+labels.map(x=>'<span>'+esc(x)+'</span>').join('')+'</div><div class="tf-scale-track">'+
      (ap===null?'':'<span class="tf-scale-marker is-actual" style="left:'+ap+'%" title="Actual: '+esc(actual)+'"></span>')+
      (tp===null?'':'<span class="tf-scale-marker is-target" style="left:'+tp+'%" title="Target: '+esc(target)+'"></span>')+
      '</div><div class="tf-scale-caption"><span>● '+esc(actual||'unknown')+'</span>'+(target?'<span>■ '+esc(target)+'</span>':'')+'</div></div>';
  }}

  function frontierQualifiersHtml(c) {{
    const rows=c.direct||[];
    const methodKinds=methods(rows);
    const methodTarget=targetObligations(c).find(o=>o.kind==='method_count');
    const methodActual=methodKinds.length>=3?'3+':methodKinds.length===2?'2 independent':methodKinds.length===1?'1 method':null;
    const methodTargetLabel=methodTarget?(Number(methodTarget.min||0)>=3?'3+':Number(methodTarget.min||0)===2?'2 independent':'1 method'):null;
    const reps=unique(rows.map(e=>e.representation));
    const repActual=reps.length===1?(repLabels[reps[0]]||reps[0]):(reps.length?reps.map(v=>repLabels[v]||v).join(' · '):null);
    const repScale=['Synthetic / abstract','Surrogate / simulated','Representative','Actual target'];
    const material=rows.filter(e=>e.model_producer);
    const msValues=unique(material.map(e=>(e.ms_validation||'l0').toUpperCase()));
    const msActual=material.length?(msValues.length===1?msValues[0]:null):'N/A';
    const pathFresh=unique(rows.map(e=>e.freshness||'not timestamped'));
    const freshActual=pathFresh.includes('current')?'current':pathFresh.includes('stale')?'stale':null;
    const freshTarget=c.target?.freshness?'current':null;
    const scenario=unique(rows.map(e=>(e.scenario_data||'not_classified')==='not_classified'?'Not classified':e.scenario_data));
    const scenarioTitle='Scenario/data: '+(scenario.join(' · ')||'Not classified')+'. No classification is invented.';
    return '<div class="tf-qualifier-strip">'+
      '<div class="tf-mini-gauge" tabindex="0" title="'+esc(scenarioTitle)+'"><strong>Representation</strong>'+scaleHtml(repScale,repActual,null)+'</div>'+
      '<div class="tf-mini-gauge" tabindex="0" title="Surrogate/model credibility is relevant only when a model or surrogate materially stands in for the target."><strong>Model credibility</strong>'+scaleHtml(['N/A','L0','L1','L2','L3','L4'],msActual,null)+'</div>'+
      '<div class="tf-mini-gauge" tabindex="0" title="Methods on retained paths: '+esc(methodKinds.map(k=>kindLabels[k]||k).join(' · ')||'none')+'"><strong>Method corroboration</strong>'+scaleHtml(['1 method','2 independent','3+'],methodActual,methodTargetLabel)+'</div>'+
      '<div class="tf-mini-gauge" tabindex="0" title="Path timestamps: '+esc(pathFresh.join(' · '))+'. Mutation freshness is tracked separately and never substituted for missing execution timestamps."><strong>Freshness</strong>'+scaleHtml(['stale','current'],freshActual,freshTarget)+'</div>'+
      '</div>';
  }}

  function guaranteeFrontierHtml(c) {{
    const rows=c.direct||[];
    const reach=model.reach_order||[];
    const boundary=model.boundary_order||[];
    const frontierTargets=targetObligations(c).filter(o=>o.kind==='frontier_cell');
    const results=targetResults(c);
    const groups=Object.entries(faultFact(c).groups||{{}});
    let html='<div class="tf-frontier-legend-mini"><span><b>●</b> target met</span><span><b>◐</b> evidence exists, qualifier/threshold gap</span><span><b>○</b> required, missing</span><span><b>◆</b> extra evidence</span><span><b>·</b> possible, not required</span></div>';
    html+='<div class="tf-assurance-matrix-scroll tf-frontier-compact"><table class="tf-evidence-matrix"><thead><tr><th>Reach ↓ / Boundary →</th>'+boundary.map(v=>'<th>'+esc(boundaryLabels[v]||v)+'</th>').join('')+'</tr></thead><tbody>';
    for(const r of reach) {{
      html+='<tr><th>'+esc(reachLabels[r]||r)+'</th>';
      for(const b of boundary) {{
        const matching=rows.filter(e=>e.reach===r&&e.boundary===b);
        const target=frontierTargets.find(o=>o.reach===r&&o.boundary===b);
        const groupEntry=groups.find(([id,g])=>g.system_reach===r&&g.boundary_mode===b);
        const groupId=groupEntry?groupEntry[0]:null, group=groupEntry?groupEntry[1]:null;
        const repOk=!target||!target.representation_min||matching.some(e=>rank(model.representation_order||[],e.representation)>=rank(model.representation_order||[],target.representation_min));
        const thresholdResults=groupId?results.filter(x=>(x.obligation.kind==='mutation_reach'||x.obligation.kind==='mutation_sensitivity')&&x.obligation.group===groupId):[];
        const thresholdOk=thresholdResults.every(x=>x.met);
        let symbol='·',cls='',status='Possible; not required; no retained evidence.';
        if(target&&matching.length&&repOk&&thresholdOk){{symbol='●';cls=' is-target-met';status='Target satisfied.';}}
        else if(target&&matching.length){{symbol='◐';cls=' is-target-partial';status='Evidence path exists, but a required qualifier or threshold is not satisfied.';}}
        else if(target){{symbol='○';cls=' is-target-missing';status='Required evidence path is missing.';}}
        else if(matching.length){{symbol='◆';cls=' is-extra';status='Actual evidence exists beyond the current Target.';}}
        const rep=unique(matching.map(e=>repLabels[e.representation]||e.representation)).join(' · ')||'none';
        const meth=methods(matching).map(k=>kindLabels[k]||k).join(' · ')||'none';
        const producerCount=unique(matching.flatMap(e=>(e.producers||[]).map(p=>p.id))).length;
        const scenario=unique(matching.map(e=>(e.scenario_data||'not_classified')==='not_classified'?'Not classified':e.scenario_data)).join(' · ')||'n/a';
        const tip=status+' Methods: '+meth+'. Representation: '+rep+'. Scenario/data: '+scenario+'. Producer chain nodes: '+producerCount+(group?'. Mutation Reach '+percent(group.mutation_reach)+'. Sensitivity '+percent(group.sensitivity)+'.':'');
        const rs=group?'<small>R '+percent(group.mutation_reach)+' · S '+percent(group.sensitivity)+'</small>':'';
        const body='<strong>'+symbol+'</strong>'+rs;
        html+='<td class="tf-evidence-cell'+cls+'" tabindex="0" title="'+esc(tip)+'">'+(matching.length?'<a href="#ce-paths-'+esc(c.id.toLowerCase())+'" style="text-decoration:none;color:inherit">'+body+'</a>':body)+'</td>';
      }}
      html+='</tr>';
    }}
    return html+'</tbody></table></div>'+frontierQualifiersHtml(c);
  }}

  function aggregateFrontierHtml(ids) {{
    const reach=model.reach_order||[];
    const boundary=[...(model.boundary_order||[])].reverse();
    let html='<div class="tf-assurance-matrix-scroll"><table class="tf-evidence-matrix"><thead><tr><th>Boundary reality ↓ / System reach →</th>'+reach.map(value=>'<th>'+esc(reachLabels[value]||value)+'</th>').join('')+'</tr></thead><tbody>';
    for(const b of boundary) {{
      html+='<tr><th>'+esc(boundaryLabels[b]||b)+'</th>';
      for(const r of reach) {{
        const matchingIds=ids.filter(id=>(contracts[id]?.direct||[]).some(e=>e.reach===r&&e.boundary===b));
        const evidence=matchingIds.flatMap(id=>(contracts[id]?.direct||[]).filter(e=>e.reach===r&&e.boundary===b));
        const reps=unique(evidence.map(e=>e.representation));
        html+='<td class="tf-evidence-cell'+(matchingIds.length?' is-filled':'')+'"><strong>'+matchingIds.length+'/'+ids.length+'</strong><small>'+esc(reps.length?'Representation: '+reps.map(v=>repLabels[v]||v).join(' · '):'—')+'</small></td>';
      }}
      html+='</tr>';
    }}
    return html+'</tbody></table></div>';
  }}

  function faultOverviewHtml() {{
    const layers=faultModel.layers||[];
    if(!layers.length) return '';
    const exercised=layers.filter(layer=>Number(layer.detected||0)>0).length;
    const rows=layers.map(layer=>{{
      const numerator=Number(layer.detected||0), denominator=Number(layer.generated||0);
      const signal=denominator ? numerator+'/'+denominator+' · '+percent(layer.score) : 'not measured';
      const note=layer.note||layer.reason||layer.target||'';
      return '<tr><td><strong>'+esc(layer.label||layer.id)+'</strong><br><span class="tf-fault-layer-kind">'+esc(layer.kind||'')+'</span></td><td>'+esc(layer.engine||'')+'<br><small>'+esc(layer.mode||'')+'</small></td><td><strong>'+esc(signal)+'</strong></td><td>'+esc(note)+'</td></tr>';
    }}).join('');
    const limits=(faultModel.known_limitations||[]).map(value=>'<li>'+esc(value)+'</li>').join('');
    const specification=layers.find(x=>x.id==='specification')||{{}};
    const runtime=layers.find(x=>x.id==='runtime')||{{}};
    const specificationProbe=specification.generated?Number(specification.detected||0)+' / '+Number(specification.generated):'n/a';
    return '<section class="tf-assurance-section" id="fault-model-coverage"><h3>Fault-model Coverage · pilot mechanisms</h3><p>This system overview says which mechanisms have been proven operable somewhere in the pilot. It is <strong>not Requirement coverage</strong>; Requirement-specific obligations are evaluated on each Contract Evidence page.</p><div class="tf-assurance-overview-metrics"><div class="tf-assurance-metric"><span>Pilot fault layers exercised</span><strong>'+exercised+' / '+layers.length+'</strong><small>mechanism exercise, not contract coverage</small></div><div class="tf-assurance-metric"><span>Native family metadata</span><strong>pytest-gremlins</strong><small>engine operator labels</small></div><div class="tf-assurance-metric"><span>Agentic Test Forge probe</span><strong>'+esc(specificationProbe)+'</strong><small>Scenario Outline Examples mutants</small></div><div class="tf-assurance-metric"><span>Runtime injector</span><strong>'+esc(runtime.engine||'n/a')+'</strong></div></div><div class="pst-scrollable-table-container"><table class="table tf-fault-layer-table"><thead><tr><th>Fault layer</th><th>Mechanism</th><th>Probe result</th><th>Scope / limitation</th></tr></thead><tbody>'+rows+'</tbody></table></div><p><a href="assurance-fault-model-facts.json">Raw fault-model facts →</a></p>'+(limits?'<details><summary><strong>Known limits</strong></summary><ul>'+limits+'</ul></details>':'')+'</section>';
  }}

  function assuranceHistoryHtml() {{
    const history=faultModel.history||{{}};
    const rows=history.rows||[];
    if(!rows.length) return '';
    const recent=[...rows].slice(-6).reverse().map(row=>'<tr><td>'+esc(row.finished_at||'')+'</td><td>'+esc(row.mode||'')+'</td><td>'+Number(row.measured_contracts||0)+'</td><td>'+percent(row.mutation_sensitivity)+'</td><td>'+Number(row.new_survivors||0)+'</td><td>'+Number(row.survivor_debt||0)+'</td></tr>').join('');
    return '<section class="tf-assurance-section" id="assurance-history"><h3>Assurance History · retained mutation signal</h3><p><strong>'+esc(history.tool||'DVC plots')+'</strong> owns the trend rendering. Old campaigns contain only mutation facts; target/fault-model history is never back-filled with values that were not retained then.</p><iframe class="tf-assurance-history-frame" loading="lazy" title="Assurance history trend" src="'+esc(history.url||'assurance-history/index.html')+'"></iframe><div class="pst-scrollable-table-container"><table class="table tf-fault-layer-table"><thead><tr><th>Finished</th><th>Mode</th><th>Contracts</th><th>Mean Test Strength</th><th>New</th><th>Debt</th></tr></thead><tbody>'+recent+'</tbody></table></div><p><a href="'+esc(history.url||'assurance-history/index.html')+'">Open DVC trend →</a> · <a href="'+esc(history.csv_url||'assurance-history/assurance-history.csv')+'">Raw history CSV →</a></p></section>';
  }}

  function faultDetailLinks(layer) {{
    const links=[];
    if(layer.source_url) links.push('<a href="'+esc(layer.source_url)+'">source</a>');
    if(layer.test_source_url) links.push('<a href="'+esc(layer.test_source_url)+'">detector source</a>');
    if(layer.raw_facts_url) links.push('<a href="'+esc(layer.raw_facts_url)+'">raw retained facts</a>');
    if(layer.mutants_url) links.push('<a href="'+esc(layer.mutants_url)+'">MTE / mutants</a>');
    return links.length?'<p class="tf-path-links">'+links.join('')+'</p>':'';
  }}

  function faultContractHtml(c) {{
    const fact=faultFact(c);
    if(!Object.keys(fact).length) return '<section class="tf-section" id="ce-faults-'+esc(c.id.toLowerCase())+'"><div class="tf-section-head"><h3>2. Fault Detection</h3><small>no Requirement-specific retained campaign</small></div></section>';
    const layers=fact.layers||{{}};
    const spec=layers.specification||{{}}, arch=layers.architecture||{{}}, iface=layers.interface||{{}}, runtime=layers.runtime||{{}}, impl=layers.implementation||{{}};
    const groups=Object.values(fact.groups||{{}});
    const groupForDepth=depth=>groups.find(g=>g.system_reach===depth);
    const comp=groupForDepth('component')||{{}}, sys=groupForDepth('system')||{{}};
    const overlap=fact.detection_overlap||{{}};
    const targetSensitivity=group=>targetObligations(c).find(o=>o.kind==='mutation_sensitivity'&&o.group===group)?.min;
    const pctWidth=value=>Math.max(0,Math.min(100,Number(value)||0));
    const bar=(label,value,target)=>'<div class="tf-bar-wrap" title="'+esc(label)+': '+percent(value)+(target!==undefined?' · target ≥ '+Number(target).toFixed(1)+'%':'')+'"><span>'+esc(label)+'</span><div class="tf-bar-track"><div class="tf-bar-fill'+(target!==undefined&&Number(value)<Number(target)?' is-gap':'')+'" style="width:'+pctWidth(value)+'%"></div></div><span class="tf-bar-value">'+percent(value)+'</span></div>';
    const architectureGenerated=Number(arch.generated||0)+Number(iface.generated||0);
    const architectureDetected=Number(arch.detected||0)+Number(iface.detected||0);
    const node=(label,value,subtitle,tip,cls='')=>'<div class="tf-fault-node'+cls+'" tabindex="0" title="'+esc(tip)+'"><span>'+esc(label)+'</span><strong>'+esc(value)+'</strong><small>'+esc(subtitle)+'</small></div>';
    const layerCards=[
      node('Requirement / model',Number(spec.detected||0)+' / '+Number(spec.generated||0),'challenge detected','Specification/model challenge: '+(spec.mutation||spec.target||'not recorded')+'. Detector: '+(spec.detector||spec.engine||'not recorded')+'.'),
      node('Architecture / interface',architectureDetected+' / '+architectureGenerated,'challenges detected','Architecture: '+Number(arch.detected||0)+'/'+Number(arch.generated||0)+' via '+(arch.engine||'unknown')+'. Interface: '+Number(iface.detected||0)+'/'+Number(iface.generated||0)+' via '+(iface.engine||'unknown')+'.'),
      node('Runtime / dependency',Number(runtime.detected||0)+' / '+Number(runtime.generated||0),'challenge detected','Runtime fault: '+(runtime.fault_family||runtime.mode||'not recorded')+'. Engine: '+(runtime.engine||'not recorded')+'.'),
      node('Implementation',Number(overlap.detected_union||0)+' / '+Number(overlap.mutant_universe||0),'native mutants detected','Stable pytest-gremlins universe. Corroborated '+Number(overlap.corroborated||0)+'. Undetected '+Number(overlap.undetected||0)+'.'),
    ].join('');

    const layerDetail=(title,result,body,links)=>'<div class="tf-responsibility-item"><strong>'+esc(title)+'</strong><br><small>'+esc(result)+'</small><p>'+body+'</p>'+(links||'')+'</div>';
    const layerDetails=layerDetail('Specification / model',Number(spec.detected||0)+' / '+Number(spec.generated||0)+' detected','<strong>Mutant:</strong> <code>'+esc(spec.mutation||'not recorded')+'</code><br><strong>Detector:</strong> '+esc(spec.detector||'not recorded'),faultDetailLinks(spec))+
      layerDetail('Architecture',Number(arch.detected||0)+' / '+Number(arch.generated||0)+' detected','<strong>Injected edge:</strong> <code>'+esc(arch.injected_violation||arch.target||'not recorded')+'</code><br><strong>Detector:</strong> '+esc(arch.detector||arch.engine||'not recorded'),faultDetailLinks(arch))+
      layerDetail('Interface / protocol',Number(iface.detected||0)+' / '+Number(iface.generated||0)+' detected','<strong>Challenge:</strong> '+esc(iface.fault_family||iface.mode||'not recorded')+'<br><strong>Observed:</strong> '+esc(iface.observed_interaction||iface.public_error||'not recorded'),faultDetailLinks(iface))+
      layerDetail('Runtime / dependency',Number(runtime.detected||0)+' / '+Number(runtime.generated||0)+' detected','<strong>Injected:</strong> <code>'+esc(JSON.stringify(runtime.injected_fault||{{type:runtime.fault_family}}))+'</code><br><strong>Observed:</strong> '+esc(runtime.observed_behavior||'not recorded'),faultDetailLinks(runtime));

    const depthColumns=['component','component_integration','system','system_integration'];
    const depthRows=depthColumns.map(depth=>{{
      const g=groupForDepth(depth);
      return '<tr><td>'+esc(reachLabels[depth]||depth)+'</td>'+(g?'<td>'+Number(g.generated||0)+'</td><td>'+Number(g.reached||0)+'</td><td>'+Number(g.killed||0)+'</td><td>'+percent(g.mutation_reach)+'</td><td>'+percent(g.sensitivity)+'</td>':'<td colspan="5">N/A</td>')+'</tr>';
    }}).join('');
    const families=unique(groups.flatMap(g=>Object.keys(g.families||{{}}))).sort();
    const familyRows=families.map(family=>'<tr><th>'+esc(family)+'</th>'+depthColumns.map(depth=>{{const g=groupForDepth(depth),row=g?(g.families||{{}})[family]:null;return row?'<td><strong>S '+percent(row.sensitivity)+'</strong><br><small>R '+percent(row.mutation_reach)+' · '+Number(row.killed||0)+'/'+Number(row.reached||0)+' killed/reached</small></td>':'<td>N/A</td>';}}).join('')+'</tr>').join('');
    const mutmut=impl.retained_mutmut||{{}};
    const mutantRows=(impl.mutant_detail||[]).map(row=>{{
      const compState=row.component_reached?(row.component_killed?'killed':'survived'):'unreached';
      const sysState=row.system_reached?(row.system_killed?'killed':'survived'):'unreached';
      return '<tr><td><code>'+esc(row.gremlin_id||'')+'</code><br>L'+Number(row.line||0)+'</td><td>'+esc(row.operator||'')+'<br><small>'+esc(row.description||'')+'</small></td><td>'+esc(compState)+'</td><td>'+esc(sysState)+'</td><td>'+esc(row.component_killing_test||row.system_killing_test||'not reported')+'</td></tr>';
    }}).join('');
    const diagnostics='<details class="tf-disclosure"><summary>Implementation diagnostics · native families, overlap, exact mutants</summary><div class="tf-disclosure-body">'+
      '<h4>Mutation detection by verification depth</h4><div class="pst-scrollable-table-container"><table class="table tf-depth-table"><thead><tr><th>Depth</th><th>generated</th><th>reached</th><th>killed</th><th>Reach</th><th>Sensitivity</th></tr></thead><tbody>'+depthRows+'</tbody></table></div>'+
      '<h4>Native fault family × evidence depth</h4><div class="tf-assurance-matrix-scroll"><table class="table tf-depth-table"><thead><tr><th>Family</th>'+depthColumns.map(d=>'<th>'+esc(reachLabels[d]||d)+'</th>').join('')+'</tr></thead><tbody>'+familyRows+'</tbody></table></div>'+
      '<h4>Unique / corroborated detection</h4><div class="tf-target-summary"><div><span>Universe</span><strong>'+Number(overlap.mutant_universe||0)+'</strong></div><div><span>Union</span><strong>'+Number(overlap.detected_union||0)+'</strong></div><div><span>Corroborated</span><strong>'+Number(overlap.corroborated||0)+'</strong></div><div><span>Undetected</span><strong>'+Number(overlap.undetected||0)+'</strong></div></div><p><small>Unique by depth · Component '+Number(overlap.component_only||0)+' · Component integration N/A · System '+Number(overlap.system_only||0)+' · System integration N/A</small></p>'+
      '<p><strong>Retained mutmut Test Strength:</strong> '+percent(mutmut.score)+' · '+Number(mutmut.killed||0)+' killed / '+Number(mutmut.survived||0)+' survived / '+Number(mutmut.valid_mutants||0)+' valid. Different denominator; never merged with pytest-gremlins Reach/Sensitivity.</p>'+
      '<details class="tf-disclosure"><summary>Exact mutants · '+Number((impl.mutant_detail||[]).length)+'</summary><div class="tf-disclosure-body tf-assurance-matrix-scroll"><table class="table tf-mutant-table"><thead><tr><th>Mutant</th><th>Family/change</th><th>Component</th><th>System</th><th>Killing test</th></tr></thead><tbody>'+mutantRows+'</tbody></table></div></details>'+
      '<p class="tf-path-links">'+(impl.mutants_url?'<a href="'+esc(impl.mutants_url)+'">MTE / raw mutants</a>':'')+'<a href="mutation-analysis.html#mutation-'+esc(c.id.toLowerCase())+'">Mutation Analysis</a><a href="assurance-fault-model-facts.json">Raw fault facts</a></p></div></details>';

    return '<section class="tf-section" id="ce-faults-'+esc(c.id.toLowerCase())+'"><div class="tf-section-head"><h3>2. Fault Detection</h3><small>which failure classes this evidence can expose</small></div>'+
      '<div class="tf-fault-strip">'+layerCards+'</div>'+
      '<div class="tf-compare"><div class="tf-compare-row"><div class="tf-compare-label">Component</div>'+bar('Reach',comp.mutation_reach)+bar('Sensitivity',comp.sensitivity,targetSensitivity('component_local'))+'</div><div class="tf-compare-row"><div class="tf-compare-label">System</div>'+bar('Reach',sys.mutation_reach)+bar('Sensitivity',sys.sensitivity,targetSensitivity('system_local'))+'</div></div>'+
      '<details class="tf-disclosure"><summary>Fault-layer evidence · specification, architecture, interface, runtime</summary><div class="tf-disclosure-body"><div class="tf-responsibility-grid">'+layerDetails+'</div></div></details>'+diagnostics+'</section>';
  }}

  function overviewHtml() {{
    const ids=Object.keys(contracts);
    const any=coverage(ids,c=>(c.direct||[]).length>0);
    const system=coverage(ids,hasSystemEvidence);
    const targeted=coverage(ids,c=>Boolean(c.target));
    const diverse=coverage(ids,hasDiversity);
    let rows='';
    for(const goal of model.goals||[]) {{
      const gid=goal.contracts||[];
      rows+='<tr class="tf-assurance-goal-row"><td><a href="traceability-reader.html#review-'+esc(goal.id)+'">'+esc(goal.title)+'</a></td><td>'+gid.length+'</td><td>'+coverage(gid,c=>Boolean(c.target))+'/'+gid.length+'</td><td>'+coverage(gid,hasSystemEvidence)+'/'+gid.length+'</td><td>'+coverage(gid,hasDirectEvidence)+'/'+gid.length+'</td><td>'+coverage(gid,hasDiversity)+'/'+gid.length+'</td></tr>';
      for(const feature of goal.features||[]) {{
        const fids=feature.contracts||[];
        rows+='<tr><td>↳ <a href="traceability-reader.html#review-'+esc(feature.id)+'">'+esc(feature.title)+'</a></td><td>'+fids.length+'</td><td>'+coverage(fids,c=>Boolean(c.target))+'/'+fids.length+'</td><td>'+coverage(fids,hasSystemEvidence)+'/'+fids.length+'</td><td>'+coverage(fids,hasDirectEvidence)+'/'+fids.length+'</td><td>'+coverage(fids,hasDiversity)+'/'+fids.length+'</td></tr>';
      }}
    }}
    return '<section id="assurance-evidence-overview"><div class="tf-assurance-kicker">System assurance coverage · not execution health</div><h2>Evidence coverage</h2><p>The primary evidence topology is one <strong>System Reach × Boundary Reality</strong> frontier. Representation fidelity stays attached to concrete paths instead of being promoted into a second combinable matrix.</p><div class="tf-assurance-overview-metrics"><div class="tf-assurance-metric"><span>Contracts with evidence</span><strong>'+any+' / '+ids.length+'</strong></div><div class="tf-assurance-metric"><span>Explicit Assurance Targets</span><strong>'+targeted+' / '+ids.length+'</strong><small>Three deliberately contrasting pilot Assurance Targets</small></div><div class="tf-assurance-metric"><span>System-reach evidence</span><strong>'+system+' / '+ids.length+'</strong></div><div class="tf-assurance-metric"><span>2+ methods</span><strong>'+diverse+' / '+ids.length+'</strong></div></div><section class="tf-assurance-section"><h3>Guarantee Frontier · observed evidence topology</h3>'+aggregateFrontierHtml(ids)+'</section>'+faultOverviewHtml()+assuranceHistoryHtml()+'<section class="tf-assurance-section"><h3>Goal / capability roll-up</h3><p>Target coverage is intentionally distinct from evidence coverage. A contract without a declared target is not automatically red.</p><div class="pst-scrollable-table-container"><table class="table tf-assurance-capabilities"><thead><tr><th>Goal / capability</th><th>Contracts</th><th>Explicit targets</th><th>System reach</th><th>Direct external</th><th>2+ methods</th></tr></thead><tbody>'+rows+'</tbody></table></div></section><p class="tf-assurance-links"><a href="traceability-reader.html">Choose a Requirement / TREQ in Traceability Reader →</a><a href="verification-depth-map.html">Verification Depth →</a><a href="evidence-trust.html">Evidence producer trust →</a></p></section>';
  }}

  function assuranceArgumentHtml(c) {{
    const results=targetResults(c);
    const children=(c.children||[]).map(id=>contracts[id]).filter(Boolean);
    const row=r=>'<div class="tf-argument-node'+(r.met?'':' is-gap')+'"><strong>'+(r.met?'✓ ':'GAP · ')+esc(r.obligation.label||r.obligation.id)+'</strong><br><small>'+targetText(r.obligation)+' · actual: '+esc(r.actual)+'</small></div>';
    const sub=children.length?'<div class="tf-argument-node"><strong>Supporting REQ / TREQ</strong><div class="tf-argument-children">'+children.map(child=>'<a href="'+contractLink(child.id)+'"><code>'+esc(child.id)+'</code> · '+esc(child.title)+'</a><br>').join('')+'</div></div>':'';
    return '<details class="tf-disclosure"><summary>Assurance argument · claim → obligations → evidence</summary><div class="tf-disclosure-body"><div class="tf-argument-node"><strong>'+esc(c.id)+' · '+esc(c.title)+'</strong><br><small>'+esc(c.statement||'No authored statement retained.')+'</small></div><div class="tf-argument-tree">'+results.map(row).join('')+sub+'</div></div></details>';
  }}

  function qualityHtml(c) {{
    const rows=c.direct||[];
    const kinds=methods(rows);
    const producers=unique(rows.flatMap(e=>(e.producers||[]).map(p=>p.id))).map(id=>rows.flatMap(e=>e.producers||[]).find(p=>p.id===id)).filter(Boolean);
    const qualified=producers.filter(p=>(p.qualified_by||[]).length>0).length;
    const producerTip=producers.map(p=>(p.title||p.id)+((p.qualified_by||[]).length?' · '+(p.qualified_by||[]).join(', '):' · no qualification link')).join(' | ');
    const material=rows.filter(e=>e.model_producer);
    const ms=material.length?unique(material.map(e=>(e.ms_validation||'l0').toUpperCase())).join(' · '):'N/A';
    const pathFresh=unique(rows.map(e=>e.freshness||'not timestamped'));
    const mutationFresh=c.strength?(c.strength.fresh?'current':'stale'):'not measured';
    const groups=Object.values(faultFact(c).groups||{{}});
    const weakest=groups.filter(g=>g.sensitivity!==null&&g.sensitivity!==undefined).sort((a,b)=>Number(a.sensitivity)-Number(b.sensitivity))[0];
    const sensitivityTarget=weakest?targetObligations(c).find(o=>o.kind==='mutation_sensitivity'&&o.group===Object.entries(faultFact(c).groups||{{}}).find(([,g])=>g===weakest)?.[0])?.min:null;
    const methodTarget=targetObligations(c).find(o=>o.kind==='method_count')?.min;
    const item=(label,value,sub,tip,cls='')=>'<div class="tf-trust-item'+cls+'" tabindex="0" title="'+esc(tip)+'"><span>'+esc(label)+'</span><strong>'+esc(value)+'</strong><small>'+esc(sub)+'</small></div>';
    const trust=[
      item('Methods',String(kinds.length),methodTarget?'target ≥ '+methodTarget:'types',kinds.map(k=>kindLabels[k]||k).join(' · ')||'No retained methods',methodTarget&&kinds.length<Number(methodTarget)?' is-gap':''),
      item('Producer chain',qualified+' / '+producers.length,'with qualification links',producerTip||'No retained producer chain'),
      item('Surrogate / model',ms,material.length?'M&S credibility':'not material','Only relevant when a surrogate/model materially stands in for the target.'),
      item('Path freshness',pathFresh.join(' · ')||'unknown','mutation '+mutationFresh,'Execution path timestamps: '+(pathFresh.join(' · ')||'unknown')+'. Mutation signal: '+mutationFresh+'.'),
      item('Weakest sensitivity',weakest?percent(weakest.sensitivity):'n/a',sensitivityTarget?'target ≥ '+Number(sensitivityTarget).toFixed(1)+'%':'no target','Weakest measured mutation oracle: '+(weakest?.label||weakest?.system_reach||'n/a')+'. Reach and Sensitivity remain separate.',sensitivityTarget&&Number(weakest?.sensitivity)<Number(sensitivityTarget)?' is-gap':''),
    ].join('');
    return '<section class="tf-section" id="ce-trust-'+esc(c.id.toLowerCase())+'"><div class="tf-section-head"><h3>3. Evidence Trust</h3><small>why the retained evidence is believable</small></div><div class="tf-trust-strip">'+trust+'</div><p class="tf-contract-meta">No scalar confidence score. <a href="evidence-trust.html">Evidence Producer Credibility →</a></p>'+assuranceArgumentHtml(c)+'</section>';
  }}

  function gapDiagnostics(c,r) {{
    const o=r.obligation,links=[];
    let question='Which concrete evidence would satisfy this obligation?';
    if(o.kind==='mutation_sensitivity') {{
      links.push('<a href="#ce-faults-'+esc(c.id.toLowerCase())+'">Fault diagnostics</a>');
      links.push('<a href="mutation-analysis.html#mutation-'+esc(c.id.toLowerCase())+'">Mutation Analysis</a>');
      if(c.strength?.report_url) links.push('<a href="'+esc(c.strength.report_url)+'">MTE survivors</a>');
      question='Which reached mutants survive because the local oracle cannot distinguish the mutated behavior?';
    }} else if(o.kind==='test_strength') {{
      links.push('<a href="mutation-analysis.html#mutation-'+esc(c.id.toLowerCase())+'">Mutation Analysis</a>');
      if(c.strength?.report_url) links.push('<a href="'+esc(c.strength.report_url)+'">MTE survivors</a>');
      question='Which retained survivors correspond to missing assertions for the declared invariant?';
    }} else if(o.kind==='frontier_cell') {{
      links.push('<a href="#ce-frontier-'+esc(c.id.toLowerCase())+'">Evidence Frontier</a>');
      links.push('<a href="#ce-paths-'+esc(c.id.toLowerCase())+'">Evidence Paths</a>');
      question='What concrete path will satisfy the required Reach × Boundary cell and its qualifiers?';
    }} else if(o.kind==='fault_layer') {{
      links.push('<a href="#ce-faults-'+esc(c.id.toLowerCase())+'">Fault Detection</a>');
      links.push('<a href="assurance-fault-model-facts.json">Raw fault facts</a>');
      question='Which required fault challenge is missing or undetected?';
    }}
    return '<details class="tf-disclosure"><summary>Investigate this gap</summary><div class="tf-disclosure-body"><p><strong>Next question:</strong> '+esc(question)+'</p><div class="tf-path-links">'+links.join('')+'</div></div></details>';
  }}

  function gapsHtml(c) {{
    const id=esc(c.id.toLowerCase());
    if(!c.target) return '<section class="tf-section" id="ce-gap-'+id+'"><div class="tf-section-head"><h3>4. Assurance Gap</h3><small>no explicit Target; no inferred blocking gap</small></div></section>';
    const gaps=targetResults(c).filter(r=>r.obligation.blocking!==false&&!r.met);
    if(!gaps.length) return '<section class="tf-section" id="ce-gap-'+id+'"><div class="tf-section-head"><h3>4. Assurance Gap</h3><small>Target − Actual</small></div><div class="tf-stage-card is-actual"><span>Blocking gaps</span><strong>0</strong><small>current Target satisfied</small></div></section>';
    const heroes=gaps.map(r=>{{
      const o=r.obligation;
      const target=Number(o.min),actual=Number(r.value);
      const numeric=Number.isFinite(target)&&Number.isFinite(actual)&&(o.kind==='mutation_sensitivity'||o.kind==='mutation_reach'||o.kind==='test_strength');
      let weakest='Required evidence obligation';
      if(o.kind==='mutation_sensitivity') weakest=(o.group||'').includes('component')?'Component oracle strength':'Mutation oracle strength';
      else if(o.kind==='frontier_cell') weakest=(reachLabels[o.reach]||o.reach)+' × '+(boundaryLabels[o.boundary]||o.boundary);
      else if(o.kind==='fault_layer') weakest=(o.layer||'fault')+' challenge';
      const visual=numeric?'<div class="tf-threshold"><span>Actual</span><div class="tf-threshold-track"><div class="tf-threshold-fill" style="width:'+Math.max(0,Math.min(100,actual))+'%"></div><span class="tf-threshold-marker" style="left:'+Math.max(0,Math.min(100,target))+'%" title="Target '+target.toFixed(1)+'%"></span></div><strong>'+actual.toFixed(1)+'%</strong></div><div class="tf-contract-meta">target ≥ '+target.toFixed(1)+'%</div>':'<p><strong>Target:</strong> '+targetText(o)+'<br><strong>Actual:</strong> '+esc(r.actual)+'</p>';
      return '<div class="tf-gap-hero" tabindex="0" title="Weakest area: '+esc(weakest)+'"><h4>'+esc(o.label||o.id)+'</h4>'+visual+'<div class="tf-contract-meta">Weakest area · '+esc(weakest)+'</div>'+gapDiagnostics(c,r)+'</div>';
    }}).join('');
    const improvements=(c.target.optional_improvements||[]).map(item=>'<li><strong>'+esc(item.label||'Optional improvement')+'</strong> · '+esc(item.rationale||'')+'</li>').join('');
    return '<section class="tf-section" id="ce-gap-'+id+'"><div class="tf-section-head"><h3>4. Assurance Gap</h3><small>only Must − Actual is red</small></div>'+heroes+(improvements?'<details class="tf-disclosure"><summary>Optional improvements · not Target gaps</summary><div class="tf-disclosure-body"><ul>'+improvements+'</ul></div></details>':'')+'</section>';
  }}

  function evidencePathsHtml(c) {{
    const rows=c.direct||[];
    const id=esc(c.id.toLowerCase());
    if(!rows.length) return '<section class="tf-section" id="ce-paths-'+id+'"><div class="tf-section-head"><h3>5. Evidence Paths</h3><small>no retained direct paths</small></div></section>';
    const fact=faultFact(c);
    const groups=new Map();
    for(const e of rows) {{
      const key=[e.reach,e.boundary,e.representation,e.kind].join('|');
      if(!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(e);
    }}
    const groupCards=[...groups.values()].map(items=>{{
      const e=items[0];
      const mut=Object.values(fact.groups||{{}}).find(g=>g.system_reach===e.reach&&g.boundary_mode===e.boundary);
      const producers=unique(items.flatMap(x=>(x.producers||[]).map(p=>p.title||p.id)));
      const scenarios=unique(items.map(x=>(x.scenario_data||'not_classified')==='not_classified'?'Not classified':x.scenario_data));
      const fresh=unique(items.map(x=>x.freshness||'not timestamped'));
      const tip='Paths: '+items.map(x=>x.title).join(' | ')+'. Scenario/data: '+scenarios.join(' · ')+'. Producer chain: '+producers.join(' · ')+'. Freshness: '+fresh.join(' · ')+'.';
      return '<div class="tf-path-group" tabindex="0" title="'+esc(tip)+'"><h4>'+esc(reachLabels[e.reach]||e.reach)+' · '+esc(kindLabels[e.kind]||e.kind)+' <small>× '+items.length+'</small></h4><div class="tf-path-group-stats"><div><strong>'+esc(boundaryLabels[e.boundary]||e.boundary)+'</strong><br>Boundary</div><div><strong>'+esc(repLabels[e.representation]||e.representation)+'</strong><br>Representation</div><div><strong>'+esc(mut?percent(mut.mutation_reach):'n/a')+'</strong><br>Reach</div><div><strong>'+esc(mut?percent(mut.sensitivity):'n/a')+'</strong><br>Sensitivity</div></div></div>';
    }}).join('');
    const exact=rows.map(e=>{{
      const mut=Object.values(fact.groups||{{}}).find(g=>g.system_reach===e.reach&&g.boundary_mode===e.boundary);
      const scenario=(e.scenario_data||'not_classified')==='not_classified'?'Not classified':e.scenario_data;
      const producers=(e.producers||[]).map(p=>p.title||p.id).join(' · ')||'none retained';
      const tip='Scenario/data: '+scenario+'. Producer chain: '+producers+'. Freshness: '+(e.freshness||'not timestamped')+'. M&S: '+((e.ms_validation||'n/a').toUpperCase())+'.';
      const links=[e.narrative_url?'<a href="'+esc(e.narrative_url)+'">Narrative</a>':'',e.allure_url?'<a href="'+esc(e.allure_url)+'">Allure</a>':'',e.raw_url?'<a href="'+esc(e.raw_url)+'">Raw</a>':'',e.mutants_url?'<a href="'+esc(e.mutants_url)+'">Mutants</a>':'<span>Mutants n/a</span>'].filter(Boolean).join('');
      return '<div class="tf-exact-path" tabindex="0" title="'+esc(tip)+'"><strong>'+esc(e.title)+'</strong><span>'+esc(reachLabels[e.reach]||e.reach)+' · '+esc(kindLabels[e.kind]||e.kind)+'</span><span>'+esc(boundaryLabels[e.boundary]||e.boundary)+'</span><span>R '+esc(mut?percent(mut.mutation_reach):'n/a')+' · S '+esc(mut?percent(mut.sensitivity):'n/a')+'</span><div class="tf-exact-path-links">'+links+'</div></div>';
    }}).join('');
    return '<section class="tf-section" id="ce-paths-'+id+'"><div class="tf-section-head"><h3>5. Evidence Paths</h3><small>'+rows.length+' retained paths · grouped for scanning</small></div><div class="tf-path-group-grid">'+groupCards+'</div><details class="tf-disclosure"><summary>Exact paths · '+rows.length+'</summary><div class="tf-disclosure-body">'+exact+'</div></details></section>';
  }}

  function contractHistoryHtml(c) {{
    const id=esc(c.id.toLowerCase());
    const fact=faultFact(c);
    const mutationHistory=(faultModel.contract_histories||{{}})[c.id]||fact.history||{{}};
    const targetHistory=(c.target&&c.target.history)||[];
    const snapshots=((model.assurance_snapshots||{{}}).snapshots||[]).filter(row=>row.contract_id===c.id);
    if(!mutationHistory.url&&!targetHistory.length&&!snapshots.length) return '<section class="tf-section" id="ce-history-'+id+'"><div class="tf-section-head"><h3>6. History</h3><small>no retained contract history yet</small></div></section>';
    const first=snapshots[0]||{{}},last=snapshots[snapshots.length-1]||{{}};
    const histRow=(label,firstValue,lastValue,lastPct,tip)=>'<div class="tf-history-row" tabindex="0" title="'+esc(tip||'')+'"><strong>'+esc(label)+'</strong><div class="tf-history-track"><span style="width:'+Math.max(0,Math.min(100,Number(lastPct)||0))+'%"></span></div><div class="tf-history-values">'+esc(firstValue)+' → '+esc(lastValue)+'</div></div>';
    const obligationPct=Number(last.obligations_total||0)?Number(last.obligations_met||0)/Number(last.obligations_total||1)*100:0;
    const visual='<div class="tf-history-visual">'+
      histRow('Obligations',Number(first.obligations_met||0)+'/'+Number(first.obligations_total||0),Number(last.obligations_met||0)+'/'+Number(last.obligations_total||0),obligationPct,'Target-obligation completion; not a confidence score.')+
      histRow('Component sensitivity',percent(first.component_mutation_sensitivity),percent(last.component_mutation_sensitivity),last.component_mutation_sensitivity,'Killed / reached mutants at Component depth.')+
      histRow('System sensitivity',percent(first.system_mutation_sensitivity),percent(last.system_mutation_sensitivity),last.system_mutation_sensitivity,'Killed / reached mutants at System depth.')+
      histRow('Test Strength',percent(first.test_strength),percent(last.test_strength),last.test_strength,'Retained mutmut covered-mutant Test Strength; separate denominator.')+
      '</div>';
    const revisions=targetHistory.map(row=>'<tr><td>v'+esc(row.revision)+'</td><td>'+esc(row.status||'')+'</td><td>'+esc(row.reason||'')+'</td></tr>').join('');
    const snapshotRows=snapshots.map(row=>'<tr><td>'+esc(row.checkpoint||'')+'</td><td>'+Number(row.obligations_met||0)+' / '+Number(row.obligations_total||0)+'</td><td>'+percent(row.component_mutation_reach)+' / '+percent(row.component_mutation_sensitivity)+'</td><td>'+percent(row.system_mutation_reach)+' / '+percent(row.system_mutation_sensitivity)+'</td><td>'+percent(row.test_strength)+'</td><td>'+Number(row.new_survivors||0)+'</td></tr>').join('');
    const details='<details class="tf-disclosure"><summary>History detail · '+snapshots.length+' retained assurance snapshots</summary><div class="tf-disclosure-body">'+
      (revisions?'<h4>Target revisions</h4><div class="pst-scrollable-table-container"><table class="table tf-obligation-table"><thead><tr><th>Revision</th><th>Status</th><th>Reason</th></tr></thead><tbody>'+revisions+'</tbody></table></div>':'')+
      (snapshots.length?'<h4>Prospective assurance snapshots</h4><div class="tf-assurance-matrix-scroll"><table class="table tf-obligation-table"><thead><tr><th>Checkpoint</th><th>Obligations</th><th>Component R / S</th><th>System R / S</th><th>Test Strength</th><th>New survivors</th></tr></thead><tbody>'+snapshotRows+'</tbody></table></div><p><a href="assurance-snapshots.json">Raw assurance snapshots →</a></p>':'')+
      (mutationHistory.url?'<p><a href="'+esc(mutationHistory.url)+'">DVC mutation trend →</a> · <a href="'+esc(mutationHistory.csv_url)+'">Raw mutation history CSV →</a></p>':'')+
      '<p><small>Older mutation campaigns are not back-filled with Target/fault-model dimensions that were not retained then.</small></p></div></details>';
    return '<section class="tf-section" id="ce-history-'+id+'"><div class="tf-section-head"><h3>6. History</h3><small>'+snapshots.length+' prospective snapshots · no historical back-fill</small></div>'+visual+'<div class="tf-contract-meta">New survivors: '+Number(last.new_survivors||0)+' · survivor debt: '+Number(last.survivor_debt||0)+(mutationHistory.url?' · <a href="'+esc(mutationHistory.url)+'">DVC trend →</a>':'')+'</div>'+details+'</section>';
  }}

  function investigationHtml(c) {{
    const id=esc(c.id.toLowerCase());
    const raw=(c.direct||[]).find(e=>e.raw_url)?.raw_url||('test-results/index.html?tags=TF_SCOPE__'+c.id);
    const cards=[
      ['What does the claim mean?','Living Specification',c.contract_url],
      ['Did verification fail now?','Health / Allure','verification-health-map.html'],
      ['How far does evidence reach?','Verification Depth','verification-depth-map.html'],
      ['Why is fault detection weak?','Mutation Analysis','mutation-analysis.html#mutation-'+id],
      ['Why trust the producer?','Evidence Producer Credibility','evidence-trust.html'],
      ['Need raw forensic detail?','Raw evidence',raw],
    ].map(([q,label,href])=>'<div class="tf-investigate-card"><strong>'+esc(q)+'</strong><a href="'+esc(href)+'">'+esc(label)+' →</a></div>').join('');
    const incident=c.target?'<details class="tf-disclosure"><summary>If a defect escapes · investigation loop</summary><div class="tf-disclosure-body"><div class="tf-flow-compact"><span>escaped defect</span><b>→</b><span>classify why assurance missed it</span><b>→</b><span>evidence/oracle weak <strong>or</strong> Target insufficient</span><b>→</b><span>strengthen evidence <strong>or</strong> revise Target</span><b>→</b><span>new evidence</span><b>→</b><span>Target satisfied</span><b>→</b><span>close issue</span></div><p><small>Target revisions retain profile version, rationale, issue/incident link, overrides and prior history. Current target v'+esc(c.target.target_revision??'?')+'.</small></p></div></details>':'';
    const roles='<details class="tf-disclosure"><summary>Responsibility map</summary><div class="tf-disclosure-body"><div class="tf-responsibility-grid">'+
      '<div class="tf-responsibility-item"><strong>Living Specification</strong><br>meaning, rationale, intended proof logic</div>'+
      '<div class="tf-responsibility-item"><strong>Contract Evidence</strong><br>Must vs Actual, trust, gaps</div>'+
      '<div class="tf-responsibility-item"><strong>Verification Health</strong><br>what passes/fails now</div>'+
      '<div class="tf-responsibility-item"><strong>Verification Depth</strong><br>reach and boundary exposure</div>'+
      '<div class="tf-responsibility-item"><strong>Mutation Analysis</strong><br>fault sensitivity and survivor debt</div>'+
      '<div class="tf-responsibility-item"><strong>Allure / MTE / raw</strong><br>forensic execution detail</div>'+
      '</div></div></details>';
    return '<section class="tf-section" id="ce-investigate-'+id+'"><div class="tf-section-head"><h3>7. Investigate</h3><small>open only the layer you need</small></div><div class="tf-investigate-grid">'+cards+'</div>'+incident+roles+'</section>';
  }}

  function contractHtml(c) {{
    const id=esc(c.id.toLowerCase());
    const rawEvidence=(c.direct||[]).find(e=>e.raw_url)?.raw_url||('test-results/index.html?tags=TF_SCOPE__'+c.id);
    const external='<nav class="tf-external-nav" aria-label="Related verification views">'+
      '<a href="'+esc(c.contract_url)+'">Semantics</a><a href="traceability-reader.html#review-'+esc(c.id)+'">Traceability</a><a href="verification-health-map.html">Health</a><a href="verification-depth-map.html">Depth</a><a href="mutation-analysis.html#mutation-'+id+'">Mutation</a><a href="'+esc(rawEvidence)+'">Raw evidence</a></nav>';
    const toc='<nav class="tf-sticky-toc" aria-label="Contract Evidence contents">'+
      '<a href="#ce-overview-'+id+'">Overview</a><a href="#ce-frontier-'+id+'">1 Frontier</a><a href="#ce-faults-'+id+'">2 Faults</a><a href="#ce-trust-'+id+'">3 Trust</a><a href="#ce-gap-'+id+'">4 Gap</a><a href="#ce-paths-'+id+'">5 Paths</a><a href="#ce-history-'+id+'">6 History</a><a href="#ce-investigate-'+id+'">7 Investigate</a></nav>';
    const why=(c.rationale||c.verification_intent)?'<details class="tf-disclosure"><summary>Why / verification intent</summary><div class="tf-disclosure-body">'+(c.rationale?'<p><strong>Why:</strong> '+esc(c.rationale)+'</p>':'')+(c.verification_intent?'<p><strong>Verification intent:</strong> '+esc(c.verification_intent)+'</p>':'')+'</div></details>':'';
    return '<div class="tf-contract-shell"><div class="tf-contract-head" id="ce-overview-'+id+'"><div class="tf-assurance-kicker">Contract Evidence</div><h2>'+esc(c.id)+' · '+esc(c.title)+'</h2><p class="tf-contract-claim">'+esc(c.statement||'No authored statement retained.')+'</p>'+external+why+targetOverviewHtml(c)+'</div>'+toc+
      '<section class="tf-section" id="ce-frontier-'+id+'"><div class="tf-section-head"><h3>1. Evidence Frontier</h3><small>where evidence exists · what is required · what is optional</small></div>'+guaranteeFrontierHtml(c)+'</section>'+
      faultContractHtml(c)+qualityHtml(c)+gapsHtml(c)+evidencePathsHtml(c)+contractHistoryHtml(c)+investigationHtml(c)+'</div>';
  }}

  const overview=document.getElementById("tf-assurance-overview");
  if(overview) overview.innerHTML=overviewHtml();
  for(const section of sections) {{
    const id=section.id.slice('assurance-'.length).toUpperCase();
    const c=contracts[id];
    if(c) section.innerHTML=contractHtml(c);
  }}
  function show() {{
    const target=location.hash.slice(1);
    const anchor=target?document.getElementById(target):null;
    const selected=sections.find(section=>section.id===target)||(anchor?anchor.closest('#verification-assurance-map > section[id^="assurance-"]'):null);
    sections.forEach(section=>section.classList.toggle('tf-contract-evidence-active',section===selected));
    if(overview) overview.hidden=Boolean(selected);
    if(selected) window.setTimeout(()=>{{
      const destination=anchor&&selected.contains(anchor)?anchor:selected;
      destination.scrollIntoView({{block:'start'}});
    }},0);
  }}
  window.addEventListener('hashchange',show);
  show();
}})();
</script>
<!-- TERNFORGE-P33-ASSURANCE-EVIDENCE-END -->"""
    monitor_block=requirement_monitor_block(monitor_json)
    text=text.replace("</body>",monitor_block+"\n</body>",1)
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
      "For contract-level proof, use the <strong>Contract evidence</strong> link on the Requirement / TREQ you are reviewing. For a one-screen overview of the same specification,"
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



def patch_specification_health_mutation(summary):
    if not SPEC_HEALTH_PAGE.exists():
        return
    text=SPEC_HEALTH_PAGE.read_text()
    text=re.sub(
      r"<!-- TERNFORGE-P22-MEASUREMENT-START -->.*?<!-- TERNFORGE-P22-MEASUREMENT-END -->",
      "",text,flags=re.DOTALL
    )
    total=int(summary.get("total_contracts") or 0)
    measured=int(summary.get("measured_contracts") or 0)
    block=f"""<!-- TERNFORGE-P22-MEASUREMENT-START -->
<div class="admonition note">
<p class="admonition-title">Mutation measurement coverage</p>
<p><strong>{measured}/{total}</strong> Requirement/TREQ contracts currently have objectively attributable Test Strength measurement · {int(summary.get('fresh_measured_contracts') or 0)} fresh · {int(summary.get('stale_measured_contracts') or 0)} stale · {max(total-measured,0)} N/A/unmeasured · {len(STRENGTH.get('unattributed') or [])} shared-scope diagnostic(s).</p>
<p>This is coverage of mutation evidence, not a global mutation score. <a href="verification-depth-map.html">Open Test Strength on Verification Depth Map</a>.</p>
</div>
<!-- TERNFORGE-P22-MEASUREMENT-END -->"""
    text,count=re.subn(r"(<h1>Specification health.*?</h1>)",lambda m:m.group(1)+"\n"+block,text,count=1,flags=re.DOTALL)
    if count:
        SPEC_HEALTH_PAGE.write_text(text)

def patch_portal_navigation():
    pages={
      ROOT/"docs/_build/html/index.html":None,
      ROOT/"docs/_build/html/verification.html":None,
      ROOT/"docs/_build/html/verification-health-map.html":None,
      DEPTH_PAGE:"depth",
      ASSURANCE_PAGE:None,
      SPEC_HEALTH_PAGE:None,
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
    write_mutation_analysis_page(summary,feedback)
    patch_contract_evidence_view()
    subprocess.run(
      [sys.executable,str(ROOT/".ai-bridge/build-requirement-monitor.py")],
      cwd=ROOT,check=True,
    )
    patch_traceability_contract_evidence_links()
    patch_verification_contract_evidence_path()
    patch_living_semantic_pages()
    patch_specification_health_mutation(summary)
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
    patch_depth_page()
    integrate_mutation_portal(summary,feedback)
    return summary

def build_contract(contract_id,spec,campaign):
    from mutmut.__main__ import status_by_exit_code  # ty: ignore[unresolved-import]
    from mutmut.mutation.data import (  # ty: ignore[unresolved-import]
        SourceFileMutationData,
    )
    phase="P23"
    contract_started=time.monotonic()
    print(f"[{phase}] running {contract_id}",flush=True)
    run_mutmut(spec)
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
      "engine":{"name":"mutmut","version":package_version("mutmut")},
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
    parser.add_argument("--suppress",nargs=2,metavar=("CONTRACT_ID","MUTANT_FINGERPRINT"),help="suppress one current surviving mutant")
    parser.add_argument("--unsuppress",nargs=2,metavar=("CONTRACT_ID","MUTANT_FINGERPRINT"),help="remove one mutation suppression")
    parser.add_argument("--reason",help="required suppression reason")
    parser.add_argument("--owner",help="optional suppression owner")
    parser.add_argument("--expires-at",help="optional ISO-8601 suppression expiry")
    args=parser.parse_args()
    maintenance=bool(args.refresh_freshness or args.refresh_assurance or args.suppress or args.unsuppress)
    if args.mode=="diff" and not args.base_ref and not maintenance:
        parser.error("--base-ref is required for --mode diff")
    if args.suppress and not str(args.reason or "").strip():
        parser.error("--reason is required with --suppress")
    return args

def current_campaign_or_die():
    if not CAMPAIGN_PATH.exists():
        raise SystemExit("no retained campaign.json")
    return json.loads(CAMPAIGN_PATH.read_text())

def main():
    args=parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
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
