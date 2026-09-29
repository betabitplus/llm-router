from __future__ import annotations

import ast
import enum
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from importlib.metadata import version as package_version
from pathlib import Path

import vcr
from vcr.errors import CannotOverwriteExistingCassetteException

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/_build/html/evidence-confidence-qualification.json"
OBSERVATION_TYPE = "application/vnd.ternforge.verification-observation+json"


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def version_or_unknown(name: str) -> str:
    try:
        return package_version(name)
    except Exception:
        return "UNKNOWN"


# The tools count by what they do, as the builder counts them: one implementation of the
# fingerprints (implementation_faults.code_digest and plugin_sha256) for both.
FINGERPRINTS = runpy.run_path(str(ROOT / ".ai-bridge/implementation_faults.py"), run_name="evidence_confidence_fingerprints")


def semantic_calibration_sha256() -> str | None:
    """One digest over the calibration set that qualifies the semantic mutant cascade."""
    folder = ROOT / ".ai-bridge/semantic-mutants/calibration"
    files = sorted(path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    if not files:
        return None
    return hashlib.sha256(b"".join(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes() for path in files)).hexdigest()


def assessor_calibration_sha256() -> str | None:
    """One digest over the assessors' frozen calibration answers and their record."""
    folder = ROOT / ".ai-bridge/semantic-mutants/assessor-calibration"
    files = sorted(path for path in folder.rglob("*") if path.is_file()) if folder.is_dir() else []
    if not files:
        return None
    return hashlib.sha256(b"".join(str(path.relative_to(folder)).encode() + b"\0" + path.read_bytes() for path in files)).hexdigest()


def environment() -> dict[str, str | None]:
    return {
        "python": sys.version.split()[0],
        "pytest": version_or_unknown("pytest"),
        "pytest_bdd": version_or_unknown("pytest-bdd"),
        "allure_pytest": version_or_unknown("allure-pytest"),
        "py_lib_testkit": version_or_unknown("py-lib-testkit"),
        "coverage": version_or_unknown("coverage"),
        "hypothesis": version_or_unknown("hypothesis"),
        "vcrpy": version_or_unknown("vcrpy"),
        "pytest_recording": version_or_unknown("pytest-recording"),
        "assurance_adapter_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/build-mutation-report-prototype.py"),
        "requirement_monitor_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/build-requirement-monitor.py"),
        "upper_assurance_monitor_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/build-upper-assurance-pilot.py"),
        "assurance_monitor_domain_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/assurance_monitor_domain.py"),
        "assurance_monitor_registry_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/assurance_monitor_registry.py"),
        "implementation_faults_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/implementation_faults.py"),
        "mutation_extension_sha256": FINGERPRINTS["plugin_sha256"](),
        "semantic_mutants_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/semantic_mutants.py"),
        "semantic_calibration_sha256": semantic_calibration_sha256(),
        "model_generation_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/model_generation.py"),
        "survivor_equivalence_sha256": FINGERPRINTS["code_digest"](ROOT / ".ai-bridge/survivor_equivalence.py"),
        "qualification_harness_sha256": FINGERPRINTS["code_digest"](Path(__file__)),
        "trace_bridge_sha256": FINGERPRINTS["code_digest"](ROOT / "tests/conftest.py"),
    }


def junit_status(testcase: ET.Element) -> str:
    if testcase.find("failure") is not None or testcase.find("error") is not None:
        return "failed"
    if testcase.find("skipped") is not None:
        return "skipped"
    return "passed"


def junit_index(path: Path) -> dict[str, dict[str, str]]:
    root = ET.parse(path).getroot()
    result: dict[str, dict[str, str]] = {}
    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname") or ""
        name = testcase.attrib.get("name") or ""
        nodeid = f"{classname.replace('.', '/')}.py::{name}"
        properties = {
            prop.attrib.get("name"): prop.attrib.get("value")
            for prop in testcase.findall("./properties/property")
        }
        result[nodeid] = {"status": junit_status(testcase), "name": name, "properties": properties}
    return result


def allure_index(directory: Path) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for path in directory.glob("*-result.json"):
        payload = json.loads(path.read_text())
        observation_payload: dict[str, object] | None = None
        observation_path: Path | None = None
        for attachment in payload.get("attachments") or []:
            if attachment.get("type") != OBSERVATION_TYPE:
                continue
            candidate = directory / str(attachment.get("source") or "")
            if not candidate.exists():
                continue
            observation = json.loads(candidate.read_text())
            observation_payload = observation.get("payload") or {}
            observation_path = candidate
            break
        if not observation_payload:
            continue
        nodeid = str(observation_payload.get("nodeid") or "")
        if not nodeid:
            continue
        result.setdefault(nodeid, []).append(
            {
                "status": str(payload.get("status") or "unknown").lower(),
                "start": payload.get("start"),
                "stop": payload.get("stop"),
                "producer_ids": list(observation_payload.get("producer_ids") or []),
                "observation_nodeid": nodeid,
                "result_sha256": sha256_file(path),
                "observation_sha256": sha256_file(observation_path) if observation_path else None,
            }
        )
    return result



def raw_allure_index(directory: Path) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for path in directory.glob("*-result.json"):
        payload = json.loads(path.read_text())
        full_name = str(payload.get("fullName") or "")
        if "#" not in full_name:
            continue
        module_name, test_name = full_name.split("#", 1)
        nodeid = f"{module_name.replace('.', '/')}.py::{test_name}"
        result.setdefault(nodeid, []).append(
            {
                "status": str(payload.get("status") or "unknown").lower(),
                "start": payload.get("start"),
                "stop": payload.get("stop"),
                "result_sha256": sha256_file(path),
            }
        )
    return result

def unique_suffix(index: dict[str, object], suffix: str) -> str:
    matches = [key for key in index if key.endswith(suffix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one nodeid ending {suffix!r}, got {matches!r}")
    return matches[0]


def external_controls() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    tests_dir = ROOT / "tests"
    with tempfile.TemporaryDirectory(prefix="evidence_confidence_", dir=tests_dir) as raw_tmp:
        tmp = Path(raw_tmp)
        (tmp / "test_control.py").write_text(
            "import pytest\n\n"
            "pytestmark = [\n"
            "    pytest.mark.verifies('REQ_INVALID_CONFIGURATION_ERRORS[revision==1]'),\n"
            "    pytest.mark.verification_kind('unit'),\n"
            "]\n\n"
            "@pytest.mark.coverage_item('REQ_INVALID_CONFIGURATION_ERRORS:qualification:pass')\n"
            "def test_control_pass():\n"
            "    assert True\n\n"
            "@pytest.mark.coverage_item('REQ_INVALID_CONFIGURATION_ERRORS:qualification:fail')\n"
            "def test_control_fail():\n"
            "    assert False, 'intentional false-green control'\n"
        )
        (tmp / "control.feature").write_text(
            "@REQ_INVALID_CONFIGURATION_ERRORS[revision==1]\n"
            "Feature: evidence confidence qualification\n"
            "  Scenario: Working scenario stays green\n"
            "    Given qualification setup exists\n"
            "    Then qualification deliberately passes\n\n"
            "  Scenario: Broken scenario is not green\n"
            "    Given qualification setup exists\n"
            "    Then qualification deliberately fails\n"
        )
        (tmp / "test_bdd_control.py").write_text(
            "from pytest_bdd import given, scenarios, then\n\n"
            f"scenarios({str(tmp / 'control.feature')!r})\n\n"
            "@given('qualification setup exists')\n"
            "def qualification_setup():\n"
            "    return True\n\n"
            "@then('qualification deliberately passes')\n"
            "def qualification_deliberately_passes():\n"
            "    assert True\n\n"
            "@then('qualification deliberately fails')\n"
            "def qualification_deliberately_fails():\n"
            "    assert False, 'intentional BDD false-green control'\n"
        )
        (tmp / "test_property_control.py").write_text(
            "import pytest\n"
            "from hypothesis import given, strategies as st\n\n"
            "pytestmark = [\n"
            "    pytest.mark.verifies('REQ_INVALID_CONFIGURATION_ERRORS[revision==1]'),\n"
            "    pytest.mark.verification_kind('property'),\n"
            "]\n\n"
            "@given(st.integers())\n"
            "def test_property_control_pass(value):\n"
            "    assert isinstance(value, int)\n\n"
            "@given(st.integers())\n"
            "def test_property_control_fail(value):\n"
            "    assert value != value, 'intentional Hypothesis false-green control'\n"
        )
        junit = tmp / "junit.xml"
        allure = tmp / "allure-results"
        input_snapshot = tmp / "evidence-run-inputs.json"
        command = [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            str(tmp / "test_control.py"),
            str(tmp / "test_bdd_control.py"),
            str(tmp / "test_property_control.py"),
            "-c",
            str(ROOT / "pyproject.toml"),
            f"--junitxml={junit}",
            f"--alluredir={allure}",
            "--record-mode=none",
            "--block-network",
            r"--allowed-hosts=localhost,127\.0\.0\.1",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
            env={**os.environ, "TERNFORGE_EVIDENCE_RUN_INPUTS": str(input_snapshot)},
        )
        if completed.returncode != 1:
            raise AssertionError(
                "qualification run must fail because the negative controls deliberately fail; "
                f"got exit {completed.returncode}\n{completed.stdout[-4000:]}"
            )
        if not junit.exists() or not allure.exists():
            raise AssertionError("qualification run did not retain JUnit and Allure artifacts")

        ji = junit_index(junit)
        observation_index = allure_index(allure)
        raw_index = raw_allure_index(allure)
        pass_node = unique_suffix(ji, "::test_control_pass")
        fail_node = unique_suffix(ji, "::test_control_fail")
        bdd_pass_node = unique_suffix(ji, "::test_working_scenario_stays_green")
        bdd_fail_node = unique_suffix(ji, "::test_broken_scenario_is_not_green")
        property_pass_node = unique_suffix(ji, "::test_property_control_pass")
        property_fail_node = unique_suffix(ji, "::test_property_control_fail")

        def exact_raw(nodeid: str) -> dict[str, object]:
            rows = raw_index.get(nodeid) or []
            if len(rows) != 1:
                raise AssertionError(f"expected one exact raw Allure result for {nodeid}, got {len(rows)}")
            return rows[0]

        def exact_observation(nodeid: str) -> dict[str, object]:
            rows = observation_index.get(nodeid) or []
            if len(rows) != 1:
                raise AssertionError(f"expected one exact Allure observation for {nodeid}, got {len(rows)}")
            return rows[0]

        pass_raw = exact_raw(pass_node)
        fail_raw = exact_raw(fail_node)
        bdd_pass_raw = exact_raw(bdd_pass_node)
        bdd_fail_raw = exact_raw(bdd_fail_node)
        property_pass_raw = exact_raw(property_pass_node)
        property_fail_raw = exact_raw(property_fail_node)
        pass_observation = exact_observation(pass_node)
        bdd_pass_observation = exact_observation(bdd_pass_node)
        property_pass_observation = exact_observation(property_pass_node)

        pytest_ok = (
            ji[pass_node]["status"] == "passed"
            and ji[fail_node]["status"] == "failed"
            and ji[bdd_pass_node]["status"] == "passed"
            and ji[bdd_fail_node]["status"] == "failed"
            and ji[property_pass_node]["status"] == "passed"
            and ji[property_fail_node]["status"] == "failed"
        )
        raw_rows = (
            pass_raw,
            fail_raw,
            bdd_pass_raw,
            bdd_fail_raw,
            property_pass_raw,
            property_fail_raw,
        )
        allure_ok = (
            [row["status"] for row in raw_rows]
            == ["passed", "failed", "passed", "failed", "passed", "failed"]
            and all(isinstance(row.get("start"), int) and isinstance(row.get("stop"), int) for row in raw_rows)
            and all(row.get("result_sha256") for row in raw_rows)
        )
        testkit_ok = all(
            row.get("observation_nodeid") == node
            and "PRODUCER_PY_TESTKIT" in set(row.get("producer_ids") or [])
            and "PRODUCER_PYTEST" in set(row.get("producer_ids") or [])
            and "PRODUCER_ALLURE" in set(row.get("producer_ids") or [])
            and row.get("observation_sha256")
            for node, row in (
                (pass_node, pass_observation),
                (bdd_pass_node, bdd_pass_observation),
                (property_pass_node, property_pass_observation),
            )
        )
        bdd_ok = (
            ji[bdd_pass_node]["status"] == "passed"
            and ji[bdd_fail_node]["status"] == "failed"
            and bdd_pass_raw["status"] == "passed"
            and bdd_fail_raw["status"] == "failed"
            and "PRODUCER_PYTEST_BDD" in set(bdd_pass_observation.get("producer_ids") or [])
        )
        hypothesis_ok = (
            ji[property_pass_node]["status"] == "passed"
            and ji[property_fail_node]["status"] == "failed"
            and property_pass_raw["status"] == "passed"
            and property_fail_raw["status"] == "failed"
            and "PRODUCER_HYPOTHESIS" in set(property_pass_observation.get("producer_ids") or [])
        )
        snapshot = json.loads(input_snapshot.read_text()) if input_snapshot.exists() else {}
        pass_source = pass_node.split("::", 1)[0]
        fail_source = fail_node.split("::", 1)[0]
        pass_props = ji[pass_node].get("properties") or {}
        fail_props = ji[fail_node].get("properties") or {}
        trace_bridge_ok = (
            pass_props.get("coverage_item") == "REQ_INVALID_CONFIGURATION_ERRORS:qualification:pass"
            and fail_props.get("coverage_item") == "REQ_INVALID_CONFIGURATION_ERRORS:qualification:fail"
            and pass_props.get("source_path") == pass_source
            and fail_props.get("source_path") == fail_source
            and pass_props.get("source_sha256") == sha256_file(ROOT / pass_source)
            and fail_props.get("source_sha256") == sha256_file(ROOT / fail_source)
            and (snapshot.get("inputs") or {}).get(pass_source) == pass_props.get("source_sha256")
            and (snapshot.get("inputs") or {}).get(fail_source) == fail_props.get("source_sha256")
        )

        from py_lib_testkit import ScriptedHTTPServer, ScriptedResponse

        route = "/qualification-probe"
        with ScriptedHTTPServer(
            port=0,
            routes={
                ("GET", route): [
                    ScriptedResponse(
                        status_code=200,
                        body=b"ok",
                        headers={"Content-Type": "text/plain"},
                    )
                ]
            },
        ) as server:
            scripted_before = server.request_count("GET", route)
            with urllib.request.urlopen(server.base_url + route, timeout=2.0) as response:
                scripted_body = response.read()
            scripted_after = server.request_count("GET", route)
        scripted_http_ok = scripted_before == 0 and scripted_after == 1 and scripted_body == b"ok"

        vcr_route = "/vcr-qualification"
        cassette = tmp / "vcr-control.yaml"
        with ScriptedHTTPServer(
            port=0,
            routes={
                ("GET", vcr_route): [
                    ScriptedResponse(
                        status_code=200,
                        body=b"recorded",
                        headers={"Content-Type": "text/plain"},
                    )
                ]
            },
        ) as server:
            vcr_url = server.base_url + vcr_route
            with vcr.use_cassette(str(cassette), record_mode="once"):
                with urllib.request.urlopen(vcr_url, timeout=2.0) as response:
                    vcr_recorded_body = response.read()
        with vcr.use_cassette(str(cassette), record_mode="none"):
            with urllib.request.urlopen(vcr_url, timeout=2.0) as response:
                vcr_replayed_body = response.read()
        vcr_rejected_mismatch = False
        try:
            with vcr.use_cassette(str(cassette), record_mode="none"):
                urllib.request.urlopen(vcr_url + "-not-recorded", timeout=2.0).read()
        except CannotOverwriteExistingCassetteException:
            vcr_rejected_mismatch = True
        vcr_ok = (
            cassette.exists()
            and vcr_recorded_body == b"recorded"
            and vcr_replayed_body == b"recorded"
            and vcr_rejected_mismatch
        )

        producers = {
            "PRODUCER_PYTEST": {
                "status": "QUALIFIED" if pytest_ok else "NOT QUALIFIED",
                "intended_use": "execute verification tests and preserve pass/fail in retained JUnit evidence",
                "false_green_control": "an intentionally failing unit test must remain failed while the passing control remains passed",
            },
            "PRODUCER_ALLURE": {
                "status": "QUALIFIED" if allure_ok else "NOT QUALIFIED",
                "intended_use": "retain exact test status, identity and execution timestamps",
                "false_green_control": "intentional pass/fail results must keep the same statuses and execution timestamps in Allure",
            },
            "PRODUCER_PY_TESTKIT": {
                "status": "QUALIFIED" if testkit_ok else "NOT QUALIFIED",
                "intended_use": "attach the execution observation and exact producer chain to the correct test result",
                "false_green_control": "passing evidence admitted by the monitor must retain an observation whose nodeid and producer identities match that exact testcase; mismatches are rejected by the adapter",
            },
            "PRODUCER_PYTEST_BDD": {
                "status": "QUALIFIED" if bdd_ok else "NOT QUALIFIED",
                "intended_use": "bind Gherkin scenarios to pytest execution without hiding a failing Then step",
                "false_green_control": "a passing BDD scenario must identify pytest-bdd as its producer and an intentionally failing Then step must remain failed in both JUnit and Allure",
            },
            "PRODUCER_HYPOTHESIS": {
                "status": "QUALIFIED" if hypothesis_ok else "NOT QUALIFIED",
                "intended_use": "generate property-based examples without hiding a falsifying example",
                "false_green_control": "a passing generated property must identify Hypothesis while an intentionally falsifiable property remains failed in both JUnit and Allure",
            },
            "PRODUCER_LLM_ROUTER_TRACE_BRIDGE": {
                "status": "QUALIFIED" if trace_bridge_ok else "NOT QUALIFIED",
                "intended_use": "retain the semantic coverage-item binding and exact test-source digest used by the retained run",
                "false_green_control": "coverage_item and source SHA-256 in JUnit must match the exact control testcase and the run-start input snapshot",
            },
            "PRODUCER_SCRIPTED_HTTP_SERVER": {
                "status": "QUALIFIED" if scripted_http_ok else "NOT QUALIFIED",
                "intended_use": "measure whether the provider HTTP boundary was contacted during a negative-interaction assertion",
                "false_green_control": "the sentinel request counter must report zero before a request and exactly one after one real localhost request",
            },
            "PRODUCER_VCR": {
                "status": "QUALIFIED" if vcr_ok else "NOT QUALIFIED",
                "intended_use": "replay the retained HTTP interaction selected by the test without accepting an unrecorded request as a match",
                "false_green_control": "an exact recorded request must replay while a mismatched unrecorded request is rejected in replay-only mode",
            },
        }
        details = {
            "command_exit": completed.returncode,
            "control_nodeids": {
                "pass": pass_node,
                "fail": fail_node,
                "bdd_pass": bdd_pass_node,
                "bdd_fail": bdd_fail_node,
                "property_pass": property_pass_node,
                "property_fail": property_fail_node,
            },
            "input_snapshot_sha256": sha256_file(input_snapshot),
            "retained_statuses": {
                "junit": {
                    node: ji[node]["status"]
                    for node in (
                        pass_node,
                        fail_node,
                        bdd_pass_node,
                        bdd_fail_node,
                        property_pass_node,
                        property_fail_node,
                    )
                },
                "allure": {
                    node: exact_raw(node)["status"]
                    for node in (
                        pass_node,
                        fail_node,
                        bdd_pass_node,
                        bdd_fail_node,
                        property_pass_node,
                        property_fail_node,
                    )
                },
            },
        }
        return producers, details


def internal_controls() -> dict[str, dict[str, object]]:
    adapter = runpy.run_path(str(ROOT / ".ai-bridge/build-mutation-report-prototype.py"), run_name="evidence_confidence_adapter")
    domain = runpy.run_path(
        str(ROOT / ".ai-bridge/assurance_monitor_domain.py"),
        run_name="evidence_confidence_monitor_domain",
    )
    upper = runpy.run_path(
        str(ROOT / ".ai-bridge/build-upper-assurance-pilot.py"),
        run_name="evidence_confidence_upper_monitor",
    )

    execution_link_state = adapter["execution_link_state"]
    good = execution_link_state(
        "passed",
        {"status": "passed", "observation_nodeid": "x.py::test_x", "start": 1100, "stop": 1200},
        1000,
        2000,
        "x.py::test_x",
    )
    mismatch = execution_link_state(
        "passed",
        {"status": "failed", "observation_nodeid": "x.py::test_x", "start": 1100, "stop": 1200},
        1000,
        2000,
        "x.py::test_x",
    )
    stale = execution_link_state(
        "passed",
        {"status": "passed", "observation_nodeid": "x.py::test_x", "start": 20000, "stop": 20100},
        1000,
        2000,
        "x.py::test_x",
    )
    nested_attachments = list(
        adapter["allure_attachments"](
            {
                "attachments": [{"source": "top.json"}],
                "steps": [
                    {
                        "attachments": [{"source": "nested.json"}],
                        "steps": [{"attachments": [{"source": "deep.json"}]}],
                    }
                ],
            }
        )
    )
    revision_registry = {
        "REQ_X": {"revision": 2, "derives": [], "source_path": "requirements/x.md"}
    }
    revision_match = adapter["verifies_current_revision"]
    revision_control_ok = (
        revision_match("REQ_X[revision==2]", "REQ_X", revision_registry)
        and not revision_match("REQ_X[revision==1]", "REQ_X", revision_registry)
        and not revision_match("REQ_OTHER[revision==2]", "REQ_X", revision_registry)
        and not revision_match("REQ_X", "REQ_X", revision_registry)
    )

    target_parser = adapter["requirement_monitor_target"]
    target_globals = target_parser.__globals__
    original_profile_source = target_globals["verification_profile_source"]
    profile_path, profile_section = original_profile_source("REQ_PUBLIC_API_SURFACE")
    parser_rejections = []
    malformed_sections = (
        profile_section.replace("Local", "Local typo", 1),
        profile_section.replace("Representation         | ALL", "Representation typo    | ALL", 1),
        profile_section.replace("**Representation basis.**", "**Representation note.**", 1),
        profile_section.replace(
            "<REQ_PUBLIC_API_SURFACE>",
            "<REQ_PROVIDER_RETRY>",
            1,
        ),
        # A profile may turn off only a Test Plan arid rule, only by Mutate, and only with a reason.
        profile_section + "\n### Mutation policy\n\n| Rule | Decision | Why |\n| --- | --- | --- |\n| `arid.unknown` | Mutate | a reason |\n",
        profile_section + "\n### Mutation policy\n\n| Rule | Decision | Why |\n| --- | --- | --- |\n| `arid.logging` | Skip | a reason |\n",
        # Semantic mutants challenge only an applied spec.* or interface.* class, within budget.
        profile_section + "\n### Semantic mutants\n\n| Fault class | Target | Budget | Risk |\n| --- | --- | --- | --- |\n| `impl.comparison` | `src/llm_router/__init__.py::x` | 1 | a risk |\n",
        profile_section + "\n### Semantic mutants\n\n| Fault class | Target | Budget | Risk |\n| --- | --- | --- | --- |\n| `spec.wrong-outcome` | `src/llm_router/__init__.py::x` | 5 | a risk |\n",
    )
    try:
        for malformed in malformed_sections:
            target_globals["verification_profile_source"] = (
                lambda _contract_id, malformed=malformed: (profile_path, malformed)
            )
            try:
                target_parser(
                    "REQ_PUBLIC_API_SURFACE",
                    adapter["project_monitor_policy"](),
                )
            except RuntimeError:
                parser_rejections.append(True)
            else:
                parser_rejections.append(False)
    finally:
        target_globals["verification_profile_source"] = original_profile_source
    parser_fail_closed_ok = parser_rejections == [True] * len(malformed_sections)

    specialized_binding = adapter["invalid_config_fault_probe_binding"]()
    specialized_current = adapter["specialized_fault_binding_current"]
    stale_revision_binding = json.loads(json.dumps(specialized_binding))
    stale_revision_binding["revision"] = int(stale_revision_binding["revision"]) - 1
    stale_source_binding = json.loads(json.dumps(specialized_binding))
    stale_source_binding["source_sha256"] = "0" * 64
    stale_inputs_binding = json.loads(json.dumps(specialized_binding))
    stale_inputs_binding["probe_input_set_sha256"] = "0" * 64
    specialized_binding_control_ok = (
        specialized_current(
            "REQ_INVALID_CONFIGURATION_ERRORS",
            {"binding": specialized_binding},
        )
        and not specialized_current(
            "REQ_INVALID_CONFIGURATION_ERRORS",
            {"binding": stale_revision_binding},
        )
        and not specialized_current(
            "REQ_INVALID_CONFIGURATION_ERRORS",
            {"binding": stale_source_binding},
        )
        and not specialized_current(
            "REQ_INVALID_CONFIGURATION_ERRORS",
            {"binding": stale_inputs_binding},
        )
    )

    snapshot_binding = adapter["snapshot_run_binding"]
    run_start_ms = 1_790_000_000_000
    snapshot_binding_ok = (
        snapshot_binding("2026-09-21T14:13:19Z", run_start_ms)[0] is True
        and snapshot_binding("2026-09-21T16:13:20Z", run_start_ms)[0] is False
        and snapshot_binding("2026-09-20T14:13:20Z", run_start_ms)[0] is False
        and snapshot_binding(None, run_start_ms)[0] is False
        and snapshot_binding("2026-09-21T14:13:19Z", None)[0] is False
    )

    adapter_ok = (
        snapshot_binding_ok
        and good == {"coherent": True, "freshness": "CURRENT", "reason": "JUnit and exact Allure result agree and belong to the same retained execution window"}
        and mismatch.get("coherent") is False
        and mismatch.get("freshness") == "UNKNOWN"
        and stale.get("coherent") is False
        and stale.get("freshness") == "STALE"
        and [row.get("source") for row in nested_attachments] == ["top.json", "nested.json", "deep.json"]
        and revision_control_ok
        and parser_fail_closed_ok
        and specialized_binding_control_ok
    )

    quantified_status = domain["quantified_status"]
    combine = domain["combine"]
    cell_state = domain["cell_state"]
    projection_ok = (
        quantified_status(["QUALIFIED", "UNKNOWN"], "QUALIFIED", "ALL") == "UNKNOWN"
        and quantified_status(["QUALIFIED", "NOT QUALIFIED"], "QUALIFIED", "ALL") == "NOT MET"
        and combine(["MET", "UNKNOWN"]) == "UNKNOWN"
        and combine(["MET", "NOT MET"]) == "NOT MET"
    )
    synthetic_contract = {
        "target": {
            "gate_aggregation": {
                key: {"rule": "ALL"}
                for key in ("semantic_coverage", "representation", "provenance", "producer_qualification", "freshness", "ms_validation")
            }
        },
        "coverage_actual": {
            "REQ_X:component:x": [
                {
                    "level": "component",
                    "boundary": "none",
                    "result": "passed",
                    "representation": "actual",
                    "provenance": "COMPLETE",
                    "provenance_scope": "traceability_only",
                    "producer_qualification": "QUALIFIED",
                    "producer_qualification_scope": "runner_only",
                    "freshness": "CURRENT",
                    "ms_validation": "na",
                }
            ]
        },
    }
    synthetic_target = {
        "level": "component",
        "level_label": "Component",
        "boundary": "none",
        "boundary_label": "Local",
        "declared_count": 1,
        "items": ["REQ_X:component:x"],
        "representation": "actual",
    }
    state = cell_state(synthetic_contract, synthetic_target)
    projection_ok = projection_ok and state["provenance_status"] == "UNKNOWN" and state["producer_status"] == "UNKNOWN" and state["overall"] == "UNKNOWN"

    weaker_representation_target = dict(synthetic_target)
    weaker_representation_target["representation"] = "surrogate_simulated"
    actual_over_surrogate = cell_state(
        synthetic_contract,
        weaker_representation_target,
    )
    weaker_representation_contract = json.loads(json.dumps(synthetic_contract))
    weaker_representation_contract["coverage_actual"]["REQ_X:component:x"][0][
        "representation"
    ] = "surrogate_simulated"
    surrogate_under_actual = cell_state(
        weaker_representation_contract,
        synthetic_target,
    )
    projection_ok = projection_ok and (
        actual_over_surrogate["representation_status"] == "MET"
        and actual_over_surrogate["representation_matched"] == 1
        and surrogate_under_actual["representation_status"] == "NOT MET"
        and surrogate_under_actual["representation_matched"] == 0
    )

    multi_binding_contract = json.loads(json.dumps(synthetic_contract))
    first_binding = multi_binding_contract["coverage_actual"]["REQ_X:component:x"][0]
    first_binding["provenance_scope"] = "full_chain"
    first_binding["producer_qualification_scope"] = "full_chain"
    second_binding = dict(first_binding)
    second_binding["result"] = "failed"
    multi_binding_contract["coverage_actual"]["REQ_X:component:x"].append(second_binding)
    multi_binding_state = cell_state(multi_binding_contract, synthetic_target)
    projection_ok = projection_ok and (
        multi_binding_state["semantic_status"] == "NOT MET"
        and multi_binding_state["overall"] == "NOT MET"
        and multi_binding_state["semantic_actual"] == 0
        and multi_binding_state["failed_count"] == 1
        and multi_binding_state["retained_count"] == 2
        and multi_binding_state["missing_count"] == 0
    )

    extra_passing_contract = json.loads(json.dumps(synthetic_contract))
    extra_first = extra_passing_contract["coverage_actual"]["REQ_X:component:x"][0]
    extra_first["provenance_scope"] = "full_chain"
    extra_first["producer_qualification_scope"] = "full_chain"
    extra_passing_contract["coverage_actual"]["REQ_X:component:x"].append(
        dict(extra_first)
    )
    extra_passing_state = cell_state(extra_passing_contract, synthetic_target)
    projection_ok = projection_ok and (
        extra_passing_state["semantic_status"] == "NOT MET"
        and extra_passing_state["overall"] == "NOT MET"
        and extra_passing_state["semantic_actual"] == 0
        and extra_passing_state["retained_count"] == 2
    )

    surrogate_contract = json.loads(json.dumps(synthetic_contract))
    surrogate_row = surrogate_contract["coverage_actual"]["REQ_X:component:x"][0]
    surrogate_row["representation"] = "surrogate_simulated"
    surrogate_row["ms_validation"] = "l2"
    surrogate_without_target = cell_state(surrogate_contract, synthetic_target)
    surrogate_target = dict(synthetic_target)
    surrogate_target["representation"] = "surrogate_simulated"
    surrogate_target["ms_validation_target"] = "l2"
    surrogate_l2 = cell_state(surrogate_contract, surrogate_target)
    surrogate_row["ms_validation"] = "l0"
    surrogate_l0 = cell_state(surrogate_contract, surrogate_target)
    surrogate_row["ms_validation"] = "l2"
    surrogate_target_l0 = dict(surrogate_target)
    surrogate_target_l0["ms_validation_target"] = "l0"
    surrogate_l2_over_l0 = cell_state(surrogate_contract, surrogate_target_l0)
    surrogate_row["ms_validation"] = "l0"
    surrogate_l0_over_l0 = cell_state(surrogate_contract, surrogate_target_l0)
    projection_ok = projection_ok and (
        surrogate_without_target["ms_status"] == "UNKNOWN"
        and surrogate_without_target["ms_applicable_count"] == 1
        and surrogate_l2["ms_status"] == "MET"
        and surrogate_l2["ms_matched"] == 1
        and surrogate_l0["ms_status"] == "NOT MET"
        and surrogate_l0["ms_matched"] == 0
        and surrogate_l2_over_l0["ms_status"] == "N/A"
        and surrogate_l2_over_l0["ms_matched"] == 0
        and surrogate_l0_over_l0["ms_status"] == "N/A"
        and surrogate_l0_over_l0["ms_matched"] == 0
    )

    contract_domain_state = domain["contract_domain_state"]
    linked_base = {"target": {"coverage": [], "fault_groups": []}, "coverage_actual": {}, "fault_actual": {"classes": {}, "groups": {}}}
    linked_passing = contract_domain_state({**linked_base, "linked_outside_profile": [{"nodeid": "t.py::test_extra", "result": "passed"}]}, {})
    linked_failing = contract_domain_state({**linked_base, "linked_outside_profile": [{"nodeid": "t.py::test_extra", "result": "failed"}]}, {})
    projection_ok = projection_ok and (
        linked_passing["coverage"] != "NOT MET"
        and linked_failing["coverage"] == "NOT MET"
        and linked_failing["overall"] == "NOT MET"
    )

    # Fault classes: a missed or unchallenged required class fails, an undecided challenge
    # (a semantic mutant with no distinguishing input) is UNKNOWN and never PASS, and the
    # mutant tally keeps every outcome apart.
    fault_state = domain["fault_state"]
    implementation_group = {
        "label": "Implementation",
        "items": [{"id": "impl.control-flow", "state": "required"}],
    }

    def fault_status(actual: dict) -> dict:
        return fault_state({"fault_actual": {"classes": {"impl.control-flow": actual}}}, implementation_group, {})

    caught_state = fault_status({"exercised": True, "detected": True, "caught": 3, "suppressed": 1, "invalid": 1})
    missed_state = fault_status({"exercised": True, "detected": False, "caught": 3, "survived_reached": 1, "unreached": 2})
    undecided_state = fault_status({"exercised": False, "detected": False, "undecided": 1})
    partly_undecided = fault_status({"exercised": True, "detected": True, "caught": 2, "undecided": 1})
    unchallenged_state = fault_status({"exercised": False, "detected": False})
    projection_ok = projection_ok and (
        caught_state["status"] == "MET"
        and caught_state["mutants"] == {"caught": 3, "survived": 0, "unreached": 0, "unknown": 0, "suppressed": 1, "invalid": 1}
        and missed_state["status"] == "NOT MET"
        and missed_state["classes"][0]["state"] == "missed"
        and missed_state["mutants"]["survived"] == 1
        and missed_state["mutants"]["unreached"] == 2
        and undecided_state["status"] == "UNKNOWN"
        and undecided_state["classes"][0]["state"] == "unknown"
        and partly_undecided["status"] == "UNKNOWN"
        and unchallenged_state["status"] == "NOT MET"
        and unchallenged_state["mutants"] is None
    )

    upper_criterion_state = upper["criterion_state"]
    upper_profile = ROOT / "docs/assurance-profiles/routing.md"
    upper_test_source = ROOT / "tests/conftest.py"
    upper_target = {
        "id": "ASSURANCE_CONTROL",
        "method": "pytest-bdd",
        "test_level": "System Integration",
        "boundary": "Substitute",
        "representation": "Surrogate",
        "required_executions": 1,
        "owner_id": "GOAL_ROUTING_RELIABILITY",
        "profile_path": str(upper_profile.relative_to(ROOT)),
    }
    upper_source_sha = sha256_file(upper_test_source)
    upper_profile_sha = sha256_file(upper_profile)
    upper_row = {
        "nodeid": "qualification::upper_assurance_control",
        "result": "passed",
        "source_path": str(upper_test_source.relative_to(ROOT)),
        "source_sha256": upper_source_sha,
        "classification_current": True,
        "level": "system_integration",
        "boundary": "substitute",
        "representation": "surrogate_simulated",
        "producer_ids": [
            "PRODUCER_PYTEST",
            "PRODUCER_PY_TESTKIT",
            "PRODUCER_PYTEST_BDD",
            "PRODUCER_SCRIPTED_HTTP_SERVER",
        ],
    }
    upper_nodes = upper["parse_need_graph"]()
    upper_input_paths = upper["upper_evidence_input_paths"](
        upper_target, upper_row, {"inputs": {}}, upper_nodes
    )
    upper_run_inputs = {
        "inputs": {
            relative: sha256_file(ROOT / relative)
            for relative in upper_input_paths
            if (ROOT / relative).is_file()
        }
    }
    upper_producer_ids = (
        "PRODUCER_PYTEST",
        "PRODUCER_PY_TESTKIT",
        "PRODUCER_UPPER_ASSURANCE_MONITOR",
        "PRODUCER_PYTEST_BDD",
        "PRODUCER_SCRIPTED_HTTP_SERVER",
        "PRODUCER_LLM_ROUTER_TRACE_BRIDGE",
        "PRODUCER_ASSURANCE_ADAPTER",
    )
    upper_qualification = {
        "producers": {
            producer_id: {"status": "QUALIFIED"}
            for producer_id in upper_producer_ids
        }
    }
    upper_good = upper_criterion_state(
        upper_target,
        [upper_row],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_missing_execution = upper_criterion_state(
        upper_target,
        [],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_unknown_qualification = json.loads(json.dumps(upper_qualification))
    upper_unknown_qualification["producers"]["PRODUCER_PYTEST_BDD"]["status"] = "UNKNOWN"
    upper_unknown_producer = upper_criterion_state(
        upper_target,
        [upper_row],
        run_inputs=upper_run_inputs,
        qualification=upper_unknown_qualification,
    )
    upper_bad_qualification = json.loads(json.dumps(upper_qualification))
    upper_bad_qualification["producers"]["PRODUCER_SCRIPTED_HTTP_SERVER"]["status"] = (
        "NOT QUALIFIED"
    )
    upper_bad_producer = upper_criterion_state(
        upper_target,
        [upper_row],
        run_inputs=upper_run_inputs,
        qualification=upper_bad_qualification,
    )
    upper_stale_inputs = json.loads(json.dumps(upper_run_inputs))
    upper_stale_inputs["inputs"][str(upper_test_source.relative_to(ROOT))] = "0" * 64
    upper_stale_source = upper_criterion_state(
        upper_target,
        [upper_row],
        run_inputs=upper_stale_inputs,
        qualification=upper_qualification,
    )
    upper_missing_profile_inputs = json.loads(json.dumps(upper_run_inputs))
    upper_missing_profile_inputs["inputs"].pop(str(upper_profile.relative_to(ROOT)))
    upper_missing_profile = upper_criterion_state(
        upper_target,
        [upper_row],
        run_inputs=upper_missing_profile_inputs,
        qualification=upper_qualification,
    )
    upper_wrong_level = upper_criterion_state(
        upper_target,
        [{**upper_row, "level": "component_integration"}],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_weaker_representation = upper_criterion_state(
        {**upper_target, "representation": "Actual"},
        [upper_row],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_unclassified = upper_criterion_state(
        upper_target,
        [{**upper_row, "classification_current": False}],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_unqualified_observed = upper_criterion_state(
        upper_target,
        [{**upper_row, "producer_ids": [*upper_row["producer_ids"], "PRODUCER_VCR"]}],
        run_inputs=upper_run_inputs,
        qualification=upper_qualification,
    )
    upper_projection_ok = (
        upper_good["status"] == "MET"
        and upper_good["execution_status"] == "MET"
        and upper_good["producer_qualification"]["status"] == "MET"
        and upper_good["freshness"]["status"] == "MET"
        and upper_missing_execution["status"] == "NOT MET"
        and upper_unknown_producer["status"] == "UNKNOWN"
        and upper_bad_producer["status"] == "NOT MET"
        and upper_stale_source["status"] == "NOT MET"
        and upper_missing_profile["status"] == "NOT MET"
        and upper_wrong_level["status"] == "NOT MET"
        and upper_weaker_representation["status"] == "NOT MET"
        and upper_unclassified["status"] == "UNKNOWN"
        and upper_unqualified_observed["status"] == "UNKNOWN"
    )

    return {
        "PRODUCER_ASSURANCE_ADAPTER": {
            "status": "QUALIFIED" if adapter_ok else "NOT QUALIFIED",
            "intended_use": "join retained execution artifacts without accepting mismatched status or stale run membership",
            "false_green_control": "status disagreement, out-of-run timestamps, a freshness snapshot not captured at the retained run's session start, stale/missing Requirement revision pins, and specialized fault-probe facts bound to other inputs or another mutation-engine configuration must be rejected while coherent current evidence remains current",
        },
        "PRODUCER_REQUIREMENT_MONITOR": {
            "status": "QUALIFIED" if projection_ok else "NOT QUALIFIED",
            "intended_use": "project Target versus Actual without converting missing or failed confidence evidence into green status",
            "false_green_control": "UNKNOWN, NOT QUALIFIED, partial-scope trust, exact-cardinality violations, under-validated surrogate paths, a vacuous L0 model-validation target, a failing test that verifies the contract outside its required cases, and a missed, unchallenged or undecided fault class must never become a false PASS",
        },
        "PRODUCER_UPPER_ASSURANCE_MONITOR": {
            "status": "QUALIFIED" if upper_projection_ok else "NOT QUALIFIED",
            "intended_use": "project Feature, Goal, and Product/System assurance from child status plus explicitly declared cross-contract and validation criteria",
            "false_green_control": "missing execution, UNKNOWN or NOT QUALIFIED observed producers, a path at the wrong test level/boundary or below the declared realism, unclassified paths, stale test source, or missing/stale Assurance Profile provenance must never become a false PASS",
        },
    }


def project_sdk_controls() -> dict[str, dict[str, object]]:
    """Qualify llm-router-owned SDK substitutes against retained adapter cross-checks."""
    junit_path = ROOT / "test-results/pytest-junit.xml"
    if not junit_path.exists():
        return {}

    ji = junit_index(junit_path)
    producer_source = (ROOT / "docs/evidence-producers.md").read_text()
    specs = {
        "PRODUCER_GOOGLE_GENAI_FAKE_SDK": {
            "qualifications": (
                "QUAL_GOOGLE_GENAI_FAKE_SUCCESS",
                "QUAL_GOOGLE_GENAI_FAKE_ERROR",
            ),
            "tests": (
                "tests/llm_router/integration/test_google_genai_adapter_fake.py::test_sync_google_adapter_uses_sdk_boundary_and_normalizes_result",
                "tests/llm_router/integration/test_google_genai_adapter_fake.py::test_google_sdk_retryable_status_is_translated_to_provider_error",
            ),
        },
        "PRODUCER_GEMINI_WEBAPI_FAKE_SDK": {
            "qualifications": (
                "QUAL_GEMINI_WEBAPI_FAKE_SUCCESS",
                "QUAL_GEMINI_WEBAPI_FAKE_ERROR",
            ),
            "tests": (
                "tests/llm_router/integration/test_gemini_webapi_adapter_fake.py::test_sync_gemini_webapi_crosses_sdk_boundary",
                "tests/llm_router/integration/test_gemini_webapi_adapter_fake.py::test_gemini_webapi_retryable_status_is_translated",
                "tests/llm_router/integration/test_gemini_webapi_adapter_fake.py::test_gemini_webapi_provider_specific_error_code_is_preserved",
            ),
        },
    }

    result: dict[str, dict[str, object]] = {}
    for producer_id, spec in specs.items():
        tests = spec["tests"]
        declared = producer_id in producer_source and all(
            qualification_id in producer_source
            for qualification_id in spec["qualifications"]
        )
        retained = True
        for nodeid in tests:
            row = ji.get(nodeid) or {}
            properties = row.get("properties") or {}
            source_path = nodeid.split("::", 1)[0]
            retained = retained and (
                row.get("status") == "passed"
                and properties.get("source_path") == source_path
                and properties.get("source_sha256")
                == sha256_file(ROOT / source_path)
            )
        qualified = bool(declared and retained)
        result[producer_id] = {
            "status": "QUALIFIED" if qualified else "NOT QUALIFIED",
            "intended_use": (
                "reproduce the provider SDK surface used by the real adapter for "
                "success and provider-error translation"
            ),
            "false_green_control": (
                "the current retained adapter success and error cross-checks must all "
                "pass from source-digest-matched test bytes; a happy-path-only or "
                "error-shape-incompatible fake cannot qualify"
            ),
        }
    return result


def implementation_fault_controls() -> dict[str, dict[str, object]]:
    """Qualify the mutation engine and the Implementation fault-class projection."""
    faults = runpy.run_path(
        str(ROOT / ".ai-bridge/implementation_faults.py"),
        run_name="evidence_confidence_implementation_faults",
    )

    # Scope resolution: decorators above or below the annotation, methods, statements.
    source = (
        "import dataclasses\n\n"
        "@dataclasses.dataclass\n"
        "# @impl Box, IMPL_BOX, [REQ_BOX[revision==1]]\n"
        "class Box:\n"
        "    size: int = 0\n\n"
        "    # @impl Grow, IMPL_GROW, [REQ_GROW[revision==1]]\n"
        "    @classmethod\n"
        "    def grow(cls, value):\n"
        "        return value + 1\n\n"
        "# @impl Wiring, IMPL_WIRING, [REQ_WIRING[revision==1]]\n"
        "REGISTRY = {'box': Box}\n"
    )
    lines = source.splitlines()
    tree = __import__("ast").parse(source)
    box = faults["annotated_node"](tree, lines, 4)
    grow = faults["annotated_node"](tree, lines, 8)
    wiring = faults["annotated_node"](tree, lines, 13)
    resolution_ok = (
        box is not None
        and faults["scope_kind_and_name"](tree, box, 3) == ("class", "Box")
        and grow is not None
        and faults["scope_kind_and_name"](tree, grow, 9) == ("method", "Box.grow")
        and wiring is not None
        and faults["scope_kind_and_name"](tree, wiring, 14) == ("statement", "L14")
    )

    # Attribution: every contract that claims a line challenges it with its own tests, a
    # parent with its derived child's as well; the other claimants are recorded beside it.
    needs = {
        "REQ_P": {"type": "req"},
        "TREQ_C": {"type": "treq", "derives": ["REQ_P"]},
        "REQ_S1": {"type": "req"},
        "REQ_S2": {"type": "req"},
        "REQ_A": {"type": "req"},
        "REQ_B": {"type": "req"},
    }
    scopes = [
        {"impl_id": "I1", "source": "m.py", "kind": "function", "qualname": "f", "start": 1, "end": 5, "owners": ["REQ_P", "TREQ_C"]},
        {"impl_id": "I2", "source": "m.py", "kind": "function", "qualname": "g", "start": 10, "end": 12, "owners": ["REQ_S1", "REQ_S2"]},
        {"impl_id": "I3", "source": "m.py", "kind": "class", "qualname": "K", "start": 20, "end": 30, "owners": ["REQ_A"]},
        {"impl_id": "I4", "source": "m.py", "kind": "method", "qualname": "K.m", "start": 25, "end": 27, "owners": ["REQ_B"]},
    ]
    owners = faults["line_owners"](scopes)
    descendants = faults["descendants_map"](needs)
    tests = [
        {"nodeid": "t.py::test_p", "result": "passed", "verifies": ["REQ_P"]},
        {"nodeid": "t.py::test_c", "result": "passed", "verifies": ["TREQ_C"]},
        {"nodeid": "t.py::test_c_failed", "result": "failed", "verifies": ["TREQ_C"]},
        {"nodeid": "t.py::test_a", "result": "passed", "verifies": ["REQ_A"]},
        {"nodeid": "t.py::test_b", "result": "passed", "verifies": ["REQ_B"]},
        {"nodeid": "t.py::test_s1", "result": "passed", "verifies": ["REQ_S1"]},
    ]
    plan = lambda contract_id: faults["contract_plan"](contract_id, scopes, owners, descendants, tests)
    parent, child, sibling, broad, nested = plan("REQ_P"), plan("TREQ_C"), plan("REQ_S1"), plan("REQ_A"), plan("REQ_B")
    attribution_ok = (
        parent.get("blocked") is None
        and parent["attributable_lines"] == {"m.py": [1, 2, 3, 4, 5]}
        and parent["tests"] == ["t.py::test_c", "t.py::test_p"]
        and parent["tests_not_passing"] == ["t.py::test_c_failed"]
        and child.get("blocked") is None
        and child["attributable_lines"] == {"m.py": [1, 2, 3, 4, 5]}
        and child["shared_with"] == ["REQ_P"]
        and child["tests"] == ["t.py::test_c"]
        and sibling.get("blocked") is None
        and sibling["attributable_lines"] == {"m.py": [10, 11, 12]}
        and sibling["shared_with"] == ["REQ_S2"]
        and sibling["tests"] == ["t.py::test_s1"]
        and broad.get("blocked") is None
        and broad["attributable_lines"] == {"m.py": list(range(20, 31))}
        and broad["shared_with"] == ["REQ_B"]
        and nested.get("blocked") is None
        and nested["attributable_lines"] == {"m.py": [25, 26, 27]}
        and nested["tests"] == ["t.py::test_b"]
        and plan("REQ_UNKNOWN").get("blocked") == "no_impl_scope"
    )

    # Projection: every valid, unsuppressed mutant of a class must be caught; a mutant no
    # test reaches is not caught; invalid and suppressed mutants never count as caught.
    root = Path(tempfile.gettempdir()).resolve()
    target = str(root / "m.py")
    report = {
        "results": [
            {"gremlin_id": "g1", "file_path": target, "line_number": 21, "operator": "comparison", "description": "> to >=", "status": "zapped", "covered": True},
            {"gremlin_id": "g2", "file_path": target, "line_number": 21, "operator": "boundary", "description": "boundary shift +/-1", "status": "survived", "covered": False},
            {"gremlin_id": "g3", "file_path": target, "line_number": 22, "operator": "boolean", "description": "and to or", "status": "survived", "covered": True},
            {"gremlin_id": "g4", "file_path": target, "line_number": 23, "operator": "return", "description": "return value to None", "status": "zapped", "covered": True},
            {"gremlin_id": "g5", "file_path": target, "line_number": 24, "operator": "return", "description": "return value to None", "status": "pardoned", "suppression": {"category": "equivalent", "reason": "r", "line": 24}},
            # A mutant on a line no scope of the contract claims counts for no class of it.
            {"gremlin_id": "g6", "file_path": target, "line_number": 35, "operator": "comparison", "description": "== to !=", "status": "survived", "covered": True},
            {"gremlin_id": "g7", "file_path": target, "line_number": 21, "operator": "arithmetic", "description": "+ to -", "status": "survived", "covered": True},
            {"gremlin_id": "g8", "file_path": target, "line_number": 29, "operator": "comparison", "description": "== to !=", "status": "error", "covered": True},
            {"gremlin_id": "g9", "file_path": target, "line_number": 28, "operator": "statement", "description": "removed x.append(1)", "status": "zapped", "covered": True},
            {"gremlin_id": "g10", "file_path": target, "line_number": 30, "operator": "body", "description": "body → return None", "status": "survived"},
            # An operator the Test Plan does not map challenges no class, caught or not.
            {"gremlin_id": "g11", "file_path": target, "line_number": 21, "operator": "unmapped", "description": "x to y", "status": "zapped", "covered": True},
        ],
        "ternforge": {
            "not_planted": [
                {"file_path": target, "line_number": 22, "operator": "statement", "rule": "arid.logging"},
                {"file_path": target, "line_number": 35, "operator": "statement", "rule": "arid.logging"},
            ]
        },
    }
    classes = faults["project_classes"](broad, report, root)
    all_caught = faults["project_classes"](
        broad,
        {"results": [dict(row, status="zapped", covered=True) for row in report["results"] if row["gremlin_id"] in {"g1", "g2", "g3", "g4", "g7", "g9", "g10"}]},
        root,
    )
    outcome = faults["mutant_outcome"]
    projection_ok = (
        classes["impl.comparison"]["exercised"] is True
        and classes["impl.comparison"]["detected"] is True
        and classes["impl.comparison"]["judged"] == 1
        and classes["impl.comparison"]["invalid"] == 1
        and classes["impl.boundary"]["exercised"] is False
        and classes["impl.boundary"]["detected"] is False
        and classes["impl.boundary"]["unreached"] == 1
        and classes["impl.control-flow"]["exercised"] is True
        and classes["impl.control-flow"]["detected"] is False
        and classes["impl.control-flow"]["judged"] == 2
        and classes["impl.control-flow"]["suppressed"] == 1
        and classes["impl.effect"]["exercised"] is True
        and classes["impl.effect"]["detected"] is False
        and classes["impl.effect"]["survived_reached"] == 1
        and classes["impl.effect"]["not_planted"] == {"arid.logging": 1}
        and classes["impl.arithmetic"]["exercised"] is True
        and classes["impl.arithmetic"]["detected"] is False
        and classes["impl.arithmetic"]["survived_reached"] == 1
        and all(row["detected"] for row in all_caught.values())
        and outcome({"status": "survived", "covered": False}) == "notreached"
        and outcome({"status": "survived"}) == "survived"
        and outcome({"status": "timeout"}) == "caught"
        and outcome({"status": "pardoned"}) == "suppressed"
        and outcome({"status": "error"}) == "invalid"
        and faults["blocked_classes"]("x")["impl.effect"] == {"exercised": False, "detected": False, "basis": "x"}
    )
    # A verdict that calls a survivor equivalent suppresses that survivor alone, counted as a verdict (ADR_0006).
    survivor = next(row for row in report["results"] if row["status"] == "survived" and row.get("covered"))
    judged_class = faults["CLASS_BY_OPERATOR"][survivor["operator"]]
    equivalent = {"verdict": "equivalent", "reason": "r", "by": "m"}
    with_verdict = faults["project_classes"](broad, report, root, {survivor["gremlin_id"]: equivalent})
    on_caught = faults["project_classes"](broad, report, root, {"g4": equivalent})
    projection_ok = projection_ok and (
        with_verdict[judged_class]["suppressed_by_verdict"] == 1
        and with_verdict[judged_class]["suppressed"] == classes[judged_class]["suppressed"] + 1
        and with_verdict[judged_class]["survived_reached"] == classes[judged_class]["survived_reached"] - 1
        and on_caught[faults["CLASS_BY_OPERATOR"]["return"]]["suppressed_by_verdict"] == 0
        and on_caught[faults["CLASS_BY_OPERATOR"]["return"]]["caught"] == classes[faults["CLASS_BY_OPERATOR"]["return"]]["caught"]
    )

    # Reuse: a retained result counts only while engine, scope, tests and inputs match.
    engine_now = faults["engine_configuration"]()
    reuse_plan = {"attributable_lines": {"m.py": [21, 22]}, "tests": ["tests/x/test_a.py::test_one"]}
    reuse_entry = {
        "engine": engine_now,
        "plan_key": faults["plan_key"](reuse_plan),
        "shared_inputs_sha256": "shared",
        "inputs": {"tests/x/test_a.py": "a"},
    }
    entry_state = faults["entry_state"]
    reuse_ok = (
        entry_state(reuse_entry, reuse_plan, "shared", {"tests/x/test_a.py": "a"}) == ("current", "")
        and entry_state({**reuse_entry, "engine": {**engine_now, "plugin_sha256": "old"}}, reuse_plan, "shared", {"tests/x/test_a.py": "a"})[0] == "stale"
        and entry_state(reuse_entry, {**reuse_plan, "tests": ["tests/x/test_a.py::test_two"]}, "shared", {"tests/x/test_a.py": "a"})[0] == "stale"
        and entry_state(reuse_entry, reuse_plan, "changed", {"tests/x/test_a.py": "a"})[0] == "stale"
        and entry_state(reuse_entry, reuse_plan, "shared", {"tests/x/test_a.py": "b"})[0] == "stale"
        and entry_state(reuse_entry, reuse_plan, "shared", {"tests/x/test_a.py": "a", "features/x.feature": "f"})[0] == "stale"
        and entry_state(reuse_entry, reuse_plan, "shared", {"tests/x/test_a.py": None})[0] == "stale"
    )
    with tempfile.TemporaryDirectory(prefix="ternforge-reuse-inputs-") as temp_dir:
        tmp = Path(temp_dir)
        (tmp / "tests/x/cassettes/test_a").mkdir(parents=True)
        (tmp / "tests/x/test_a.py").write_text("from tests.x.test_b import step\n")
        (tmp / "tests/x/test_b.py").write_text("def step():\n    pass\n")
        (tmp / "tests/x/helpers.py").write_text("VALUE = 1\n")
        (tmp / "tests/x/cassettes/test_a/one.yaml").write_text("interactions: []\n")
        (tmp / "features").mkdir()
        (tmp / "features/x.feature").write_text("Feature: X\n")
        own = faults["contract_inputs"](
            tmp,
            reuse_plan,
            [{"nodeid": "tests/x/test_a.py::test_one", "gherkin_feature": "features/x.feature"}],
        )
        shared = faults["shared_inputs"](tmp)
        reuse_ok = reuse_ok and (
            set(own) == {"tests/x/test_a.py", "tests/x/test_b.py", "tests/x/cassettes/test_a/one.yaml", "features/x.feature"}
            and "tests/x/helpers.py" in shared
            and "tests/x/test_a.py" not in shared
        )
        # Fingerprints by meaning. A tool keeps its digest through a comment, a docstring, a
        # reformatting or a moved line, and loses it with changed code. Code under test keeps
        # its digest through a comment edited in place, and loses it with changed code, a
        # `# mutation:` pragma or a moved line.
        base = 'def f(x):\n    """Doc."""\n    return x + 1  # note\n'
        variants = {
            "base": base,
            "comment": 'def f(x):\n    """Doc."""\n    return x + 1  # a longer note\n',
            "docstring": 'def f(x):\n    """Other doc."""\n    return x + 1  # note\n',
            "format": 'def f( x ):\n    """Doc."""\n    return (x + 1)  # note\n',
            "moved": '# header\ndef f(x):\n    """Doc."""\n    return x + 1  # note\n',
            "pragma": 'def f(x):\n    """Doc."""\n    return x + 1  # mutation: equivalent same value\n',
            "code": 'def f(x):\n    """Doc."""\n    return x + 2  # note\n',
        }
        code, source = {}, {}
        for name, text in variants.items():
            (tmp / f"digest_{name}.py").write_text(text)
            code[name] = faults["code_digest"](tmp / f"digest_{name}.py")
            source[name] = faults["source_digest"](tmp / f"digest_{name}.py")
        reuse_ok = reuse_ok and (
            len({code[name] for name in ("base", "comment", "docstring", "format", "moved", "pragma")}) == 1
            and code["code"] != code["base"]
            and source["comment"] == source["base"]
            and len({source[name] for name in ("base", "moved", "pragma", "code")}) == 4
            and faults["input_digest"](tmp / "tests/x/cassettes/test_a/one.yaml") == faults["sha256_bytes"](b"interactions: []\n")
        )
        # Product code counts per contract, as PIT counts it: the file that holds the contract's
        # mutants is its own input, other product code is no one's shared input.
        (tmp / "src/llm_router").mkdir(parents=True)
        (tmp / "src/llm_router/m.py").write_text("def f():\n    return 1\n")
        (tmp / "src/llm_router/other.py").write_text("def g():\n    return 2\n")
        owned = faults["contract_inputs"](
            tmp,
            {**reuse_plan, "files": ["src/llm_router/m.py"]},
            [{"nodeid": "tests/x/test_a.py::test_one", "gherkin_feature": "features/x.feature"}],
        )
        shared_now = faults["shared_inputs"](tmp)
        reuse_ok = reuse_ok and (
            "src/llm_router/m.py" in owned and "src/llm_router/other.py" not in owned
            and not any(path.startswith("src/") for path in shared_now)
        )
        # A mutant's time limit follows its tests, as PIT's does: 1.25 × their time + 10 s, then a
        # confirming run with twice that; without a measured baseline the fixed 30 s and 300 s.
        limits = faults["time_limits"]
        limited = faults["engine_env"](tmp / "scratch-limits", limits=limits(2.0))
        reuse_ok = reuse_ok and (
            limits(None) == (30.0, 300.0) and limits(2.0) == (12.5, 25.0) and limits(0.0) == (10.0, 20.0)
            and limited.get("TERNFORGE_GREMLIN_TIMEOUT") == "12.5" and limited.get("TERNFORGE_GREMLIN_CONFIRM_TIMEOUT") == "25.0"
        )

    # Engine: every operator family exists, and a mutant counts as caught only when a
    # real pytest run of the selected tests fails. The controls use fixtures,
    # parametrization and a pytest-bdd scenario, because a runner that cannot execute
    # those must never turn them into caught mutants. A second target pins the
    # extension: statement and body removal, arid code kept out, a visible suppression,
    # the validity filter, unreached code, a profile turning a rule off, and the
    # pull-request diff that does not run uncovered mutants.
    engine_ok = False
    engine_detail: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="ternforge-gremlins-qualification-") as temp_dir:
        tmp = Path(temp_dir)
        (tmp / "pytest.ini").write_text("[pytest]\nbdd_features_base_dir = features\n")
        (tmp / "features").mkdir()
        (tmp / "control_target.py").write_text(
            "def classify(value, enabled) -> str:\n"
            "    if value > 10 and enabled:\n"
            "        return 'big'\n"
            "    return 'small'\n"
        )
        effects_source = (
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n\n"
            "class Ledger:\n"
            "    def __init__(self):\n"
            "        self.entries = []\n"
            "        self.total = 0\n\n"
            "    def record(self, value: int) -> None:\n"
            "        logger.debug('recording %s', value > 0)\n"
            "        self.entries.append(value)\n"
            "        self.total += value\n"
            "        _log_recorded(value)\n\n"
            "    def average(self) -> float:\n"
            "        return self.total / len(self.entries)\n\n"
            "    def reset(self) -> None:\n"
            "        self.entries.clear()\n"
            "        self.total = 0\n\n\n"
            "def _log_recorded(value: int) -> None:\n"
            "    logger.info('recorded %s', value)\n\n\n"
            "def unused(value: int) -> bool:\n"
            "    return value > 3\n\n\n"
            "def stream(values):\n"
            "    yield from values\n\n\n"
            "def pinned(value: int) -> int:\n"
            "    return abs(value)  # mutation: equivalent[return] qualification control of a visible suppression\n\n\n"
            "def checked(value: int) -> int:  # mutation: bogus without a known category\n"
            "    if value < 0:\n"
            "        raise ValueError('negative')\n"
            "    return value\n"
        )
        (tmp / "control_effects.py").write_text(effects_source)
        (tmp / "control_nosite.py").write_text("VALUE = 'a'\n")
        # The Python operators (PyTation's, a condition replaced, a plain condition negated): a
        # target with a site for each, a strong suite that pins every one and a weak one that
        # asserts nothing.
        (tmp / "control_python.py").write_text(
            "from dataclasses import dataclass\n\n\n"
            "@dataclass\n"
            "class Window:\n"
            "    min_size: int\n"
            "    max_size: int\n"
            "    label: str = 'w'\n\n\n"
            "def make(min_size: int, max_size: int, *, label: str = 'w') -> Window:\n"
            "    return Window(min_size=min_size, max_size=max_size, label=label)\n\n\n"
            "def named(min_size: int, max_size: int) -> Window:\n"
            "    return make(min_size, max_size, label='named')\n\n\n"
            "def span(window: Window) -> int:\n"
            "    return window.max_size - window.min_size\n\n\n"
            "def shout(text: str) -> str:\n"
            "    return text.strip().upper()\n\n\n"
            "def as_number(text: str) -> int:\n"
            "    return int(text)\n\n\n"
            "def allowed(code: str, strict: bool) -> bool:\n"
            "    return code in {'a', 'b'} or not strict\n\n\n"
            "def gate(ready: bool, level: int) -> str:\n"
            "    if ready:\n"
            "        return 'open'\n"
            "    return 'closed' if level > 1 else 'shut'\n"
        )
        python_calls = (
            "make(1, 2, label='x'), make(1, 2), named(1, 2), span(Window(1, 5)), shout(' ab '), as_number('7'), "
            "allowed('a', True), allowed('b', True), allowed('z', True), allowed('z', False), "
            "gate(True, 0), gate(False, 2), gate(False, 1), gate(False, 0)"
        )
        (tmp / "test_python_strong.py").write_text(
            "from control_python import Window, allowed, as_number, gate, make, named, shout, span\n\n"
            "def test_python_strong():\n"
            f"    assert [{python_calls}] == [\n"
            "        Window(1, 2, 'x'), Window(1, 2, 'w'), Window(1, 2, 'named'), 4, 'AB', 7,\n"
            "        True, True, False, True, 'open', 'closed', 'shut', 'shut',\n"
            "    ]\n"
        )
        (tmp / "test_python_weak.py").write_text(
            "from control_python import Window, allowed, as_number, gate, make, named, shout, span\n\n"
            "def test_python_weak():\n"
            f"    [{python_calls}]\n"
        )
        effect_lines = effects_source.splitlines()

        def line_of(marker: str) -> int:
            return next(index for index, line in enumerate(effect_lines, 1) if marker in line)

        (tmp / "test_effects_strong.py").write_text(
            "import pytest\n"
            "from control_effects import Ledger, checked, pinned\n\n"
            "def test_record_and_reset():\n"
            "    ledger = Ledger()\n"
            "    ledger.record(2)\n"
            "    ledger.record(5)\n"
            "    assert ledger.entries == [2, 5]\n"
            "    assert ledger.total == 7\n"
            "    assert ledger.average() == 3.5\n"
            "    ledger.reset()\n"
            "    assert ledger.entries == []\n"
            "    assert ledger.total == 0\n\n"
            "def test_pinned():\n"
            "    assert pinned(-2) == 2\n"
            "    assert pinned(3) == 3\n\n"
            "def test_checked():\n"
            "    assert checked(4) == 4\n"
            "    assert checked(0) == 0\n"
            "    with pytest.raises(ValueError):\n"
            "        checked(-1)\n"
        )
        feature = (
            "Feature: Control\n"
            "  Scenario: Classify a big enabled value\n"
            "    Given the value 11\n"
            "    When it is classified while enabled\n"
            "    Then the class is \"big\"\n"
        )
        (tmp / "features/control.feature").write_text(feature)
        bdd_steps = (
            "from pytest_bdd import given, parsers, scenario, then, when\n"
            "from control_target import classify\n\n"
            "@scenario('control.feature', 'Classify a big enabled value')\n"
            "def test_bdd_classify():\n"
            "    pass\n\n"
            "@given(parsers.parse('the value {value:d}'), target_fixture='value')\n"
            "def given_value(value):\n"
            "    return value\n\n"
            "@when('it is classified while enabled', target_fixture='result')\n"
            "def classified(value):\n"
            "    return classify(value, True)\n\n"
        )
        (tmp / "test_bdd_strong.py").write_text(
            bdd_steps
            + "@then(parsers.parse('the class is \"{expected}\"'))\n"
            "def check(result, expected):\n"
            "    assert result == expected\n"
        )
        (tmp / "test_bdd_weak.py").write_text(
            bdd_steps
            + "@then(parsers.parse('the class is \"{expected}\"'))\n"
            "def check(result, expected):\n"
            "    pass\n"
        )
        (tmp / "test_strong.py").write_text(
            "import pytest\n"
            "from control_target import classify\n\n"
            "@pytest.mark.parametrize(('value', 'enabled', 'expected'), [(11, True, 'big'), (10, True, 'small'), (11, False, 'small')])\n"
            "def test_strong(monkeypatch, value, enabled, expected):\n"
            "    monkeypatch.setenv('TERNFORGE_CONTROL', '1')\n"
            "    assert classify(value, enabled) == expected\n"
        )
        (tmp / "test_weak.py").write_text(
            "import pytest\n"
            "from control_target import classify\n\n"
            "@pytest.mark.parametrize('value', [11, 10])\n"
            "def test_weak(monkeypatch, value):\n"
            "    monkeypatch.setenv('TERNFORGE_CONTROL', '1')\n"
            "    classify(value, True)\n"
            "    classify(value, False)\n"
        )
        suites = {
            "strong": ["test_strong.py::test_strong[11-True-big]", "test_strong.py::test_strong[10-True-small]", "test_strong.py::test_strong[11-False-small]", "test_bdd_strong.py::test_bdd_classify"],
            "weak": ["test_weak.py::test_weak[11]", "test_weak.py::test_weak[10]", "test_bdd_weak.py::test_bdd_classify"],
        }
        effect_tests = ["test_effects_strong.py"]
        tails: dict[str, str] = {}

        sidecars: dict[str, dict] = {}

        def engine_run(name: str, tests: list[str], target_file: str, **env_options: object) -> tuple[int, dict]:
            completed = subprocess.run(
                faults["engine_command"](tmp, tests, [target_file], project=ROOT, config="pytest.ini"),
                cwd=tmp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=900,
                env=faults["engine_env"](tmp / "scratch", **env_options),
            )
            report_path = tmp / "coverage/gremlins/gremlins.json"
            payload = json.loads(report_path.read_text()) if report_path.exists() else {}
            if report_path.exists():
                report_path.unlink()
            sidecar_path = tmp / "coverage/gremlins/ternforge-extension.json"
            sidecars[name] = json.loads(sidecar_path.read_text()) if sidecar_path.exists() else {}
            if sidecar_path.exists():
                sidecar_path.unlink()
            tails[name] = completed.stdout[-1500:]
            return completed.returncode, payload

        strong_code, strong_report = engine_run("strong", suites["strong"], "control_target.py")
        weak_code, weak_report = engine_run("weak", suites["weak"], "control_target.py")
        # Scope filter: only mutants on line 2 may run, each exactly as in the full run.
        scoped_code, scoped_report = engine_run("scoped", suites["strong"], "control_target.py", scope={"control_target.py": [2]})
        effects_code, effects_report = engine_run("effects", effect_tests, "control_effects.py")
        log_line = line_of("logger.debug")
        rule_off_code, rule_off_report = engine_run(
            "rule_off", effect_tests, "control_effects.py", scope={"control_effects.py": [log_line]}, arid_rules=[]
        )
        # A target with no mutation site: the engine writes no report, the extension's facts stay beside it.
        nosite_code, nosite_report = engine_run("nosite", effect_tests, "control_nosite.py")
        unused_lines = [line_of("def unused"), line_of("return value > 3")]
        total_line = line_of("self.total += value")
        diff_code, diff_report = engine_run(
            "diff", effect_tests, "control_effects.py",
            scope={"control_effects.py": [*unused_lines, total_line]}, skip_uncovered=True,
        )
        python_code, python_report = engine_run("python", ["test_python_strong.py"], "control_python.py")
        python_weak_code, python_weak_report = engine_run("python_weak", ["test_python_weak.py"], "control_python.py")

        strong = list(strong_report.get("results") or [])
        weak = list(weak_report.get("results") or [])
        scoped_rows = list(scoped_report.get("results") or [])
        full_on_line = {
            str(row.get("gremlin_id")): str(row.get("status"))
            for row in strong
            if int(row.get("line_number") or -1) == 2
        }
        scoped_by_id = {str(row.get("gremlin_id")): str(row.get("status")) for row in scoped_rows}
        scope_ok = (
            scoped_code == 0
            and bool(full_on_line)
            and len(full_on_line) < len(strong)
            and scoped_by_id == full_on_line
            and all(int(row.get("line_number") or -1) == 2 for row in scoped_rows)
        )
        honest_ok = (
            strong_code == 0
            and weak_code == 0
            and bool(strong)
            and all(row.get("status") == "zapped" and row.get("selected_tests") and row.get("covered") is True for row in strong)
            and len(weak) == len(strong)
            and not any(row.get("status") in faults["KILLED"] for row in weak)
        )

        effects = list(effects_report.get("results") or [])
        extension = effects_report.get("ternforge") or {}
        helper_line = line_of("_log_recorded(value)")
        unused_start, unused_end = line_of("def unused"), line_of("return value > 3")
        in_unused = [row for row in effects if unused_start <= int(row.get("line_number") or -1) <= unused_end]
        pinned_return = [row for row in effects if row.get("operator") == "return" and int(row.get("line_number") or -1) == line_of("return abs(value)")]
        others = [row for row in effects if row not in in_unused and row not in pinned_return]
        not_planted = {(int(row["line_number"]), row["operator"], row["rule"]) for row in extension.get("not_planted") or []}
        pragmas = (extension.get("pragmas") or {}).get("control_effects.py") or []
        effects_ok = (
            effects_code == 0
            and {"statement", "body"} <= {str(row.get("operator")) for row in effects}
            and bool(others)
            and all(row.get("status") == "zapped" and row.get("covered") is True for row in others)
            and bool(in_unused)
            and all(row.get("status") == "survived" and row.get("covered") is False for row in in_unused)
            and all(faults["mutant_outcome"](row) == "notreached" for row in in_unused)
            and len(pinned_return) == 1
            and pinned_return[0].get("status") == "pardoned"
            and (pinned_return[0].get("suppression") or {}).get("category") == "equivalent"
            and (log_line, "statement", "arid.logging") in not_planted
            and (log_line, "comparison", "arid.logging") in not_planted
            # A project's private log helper (`_log_…`) only logs as well.
            and (helper_line, "statement", "arid.logging") in not_planted
            and not any(int(row.get("line_number") or -1) == helper_line for row in effects)
            and any(row.get("operator") == "arithmetic" and row.get("status") == "zapped" for row in effects)
            # Only the enclosing function's body mutant may sit on the logging line: it is
            # anchored on the first line the body runs.
            and not any(int(row.get("line_number") or -1) == log_line and row.get("operator") != "body" for row in effects)
            and (extension.get("filtered") or {}).get("body: generator") == 1
            and (extension.get("filtered") or {}).get("body: dunder method", 0) >= 1
            and any(item.get("category") == "equivalent" and item.get("matched") == 1 for item in pragmas)
            and any(item.get("category") == "bogus" and item.get("error") for item in pragmas)
            and all(row.get("fingerprint") and row.get("location") and row.get("replacement") for row in effects)
            and len({row.get("fingerprint") for row in effects}) == len(effects)
        )
        rule_off = list(rule_off_report.get("results") or [])
        rule_off_ok = (
            rule_off_code == 0
            and any(row.get("operator") == "statement" and int(row.get("line_number") or -1) == log_line for row in rule_off)
            and not ((rule_off_report.get("ternforge") or {}).get("not_planted"))
        )
        diff_rows = list(diff_report.get("results") or [])
        diff_unused = [row for row in diff_rows if int(row.get("line_number") or -1) in unused_lines]
        diff_total = [row for row in diff_rows if int(row.get("line_number") or -1) == total_line]
        diff_ok = (
            diff_code == 0
            and bool(diff_unused)
            and all(row.get("run_skipped") == "not covered" and row.get("status") == "survived" for row in diff_unused)
            and bool(diff_total)
            and all(row.get("status") == "zapped" and not row.get("run_skipped") for row in diff_total)
        )
        python_rows = list(python_report.get("results") or [])
        python_weak_rows = list(python_weak_report.get("results") or [])
        python_operators = {"argument", "condition", "conditional", "negation", "container", "conversion", "method", "attribute"}
        python_ok = (
            python_code == 0 and python_weak_code == 0
            and python_operators <= {str(row.get("operator")) for row in python_rows}
            and all(row.get("status") == "zapped" and row.get("covered") is True for row in python_rows)
            and len(python_weak_rows) == len(python_rows)
            and not any(row.get("status") in faults["KILLED"] for row in python_weak_rows)
            # The dataclass requires min_size and max_size: those keywords are never removed.
            and ((python_report.get("ternforge") or {}).get("filtered") or {}).get("argument: required parameter") == 2
            and all(row.get("replacement") and row.get("fingerprint") for row in python_rows)
        )
        # What the Python operators leave alone, straight from the operators: a loop's condition
        # is never made True or negated (it would never end), a call standing as a statement, on
        # a module, on a class or awaited is never cut to its receiver, a tuple a statement unpacks
        # or returns and a subscript keep their elements, a literal already of its conversion's
        # type keeps it, and a swapped attribute is the most similar one the code reads.
        extension = runpy.run_path(str(ROOT / ".ai-bridge/pytest_plugins/ternforge_mutation.py"), run_name="evidence_confidence_mutation_extension")
        sample = ast.parse(
            "import logging\n"
            "__all__ = ['a', 'b']\n"
            "async def f(items, p, client, d):\n"
            "    while items:\n"
            "        items.pop()\n"
            "    x, y = (1, 2)\n"
            "    logging.getLogger('n').info('m')\n"
            "    name = logging.getLogger('n').name\n"
            "    value = Config.load()\n"
            "    data = await client.fetch()\n"
            "    s = str('x') + str(p)\n"
            "    k = d[1, 2]\n"
            "    return p.max_wait - p.min_wait, p.label\n"
        )
        extension["annotate"](sample)
        found = {type(node).__name__ + ":" + ast.unparse(node): node for node in ast.walk(sample) if isinstance(node, ast.Call | ast.Attribute)}
        loop_test = next(node for node in ast.walk(sample) if isinstance(node, ast.While)).test
        unpacked = next(node for node in ast.walk(sample) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple)).value
        exported = next(node for node in ast.walk(sample) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "__all__").value
        returned = next(node for node in ast.walk(sample) if isinstance(node, ast.Return)).value
        subscripted = next(node for node in ast.walk(sample) if isinstance(node, ast.Subscript)).slice
        conditional, negation = extension["ConditionalReplacement"](), extension["NegationInsertion"]()
        method, container = extension["MethodCallRemoval"](), extension["ContainerElementRemoval"]()
        conversion, attribute = extension["ConversionRemoval"](), extension["AttributeSwap"]()
        swapped = attribute.mutate(found["Attribute:p.max_wait"])
        operators_ok = (
            [node.value for node in conditional.mutate(loop_test)] == [False] and not negation.can_mutate(loop_test)
            and not method.can_mutate(found["Call:items.pop()"])
            and not method.can_mutate(found["Call:logging.getLogger('n').info('m')"])
            and not method.can_mutate(found["Call:Config.load()"])
            and not method.can_mutate(found["Call:client.fetch()"])
            and method.can_mutate(found["Call:logging.getLogger('n')"]) is False
            and not any(container.can_mutate(node) for node in (unpacked, exported, returned, subscripted))
            and not conversion.can_mutate(found["Call:str('x')"]) and conversion.can_mutate(found["Call:str(p)"])
            and len(swapped) == 1 and swapped[0].attr == "min_wait" and not attribute.can_mutate(found["Attribute:p.label"])
        )
        nosite_ok = (
            nosite_code == 0
            and not nosite_report
            and (sidecars.get("nosite", {}).get("ternforge") or {}).get("schema") == "ternforge-mutation-extension-1"
            and (sidecars.get("effects", {}).get("ternforge") or {}) == (effects_report.get("ternforge") or {})
        )
        # The campaign runs several contracts at once, each in a copy: a copy must change no outcome.
        with tempfile.TemporaryDirectory(prefix="ternforge-isolated-qualification-") as copy_dir:
            copy_root = faults["working_tree_copy"](tmp, Path(copy_dir) / "copy")
            plan = {"tests": suites["strong"], "files": ["control_target.py"], "attributable_lines": {"control_target.py": [1, 2, 3, 4]}}
            isolated_raw = Path(copy_dir) / "isolated.json"
            isolated_run = faults["run_engine_isolated"](tmp, copy_root, plan, isolated_raw, project=ROOT)
            isolated = json.loads(isolated_raw.read_text()).get("results") or [] if isolated_run["report_retained"] else []
        isolated_ok = (
            bool(isolated)
            and {str(row.get("fingerprint")): row.get("status") for row in isolated} == {str(row.get("fingerprint")): row.get("status") for row in strong}
            and all(str(row.get("file_path") or "").startswith(str(tmp.resolve())) for row in isolated)
        )
        # A mutant whose tests outrun the first time limit is caught only when a second run with room to spare runs out too.
        (tmp / "slow_target.py").write_text("def double(value: int) -> int:\n    return value * 2\n")
        (tmp / "test_slow_weak.py").write_text("import time\nfrom slow_target import double\n\ndef test_slow():\n    time.sleep(1.5)\n    double(2)\n")
        slow_env = {**faults["engine_env"](tmp / "scratch-slow"), "TERNFORGE_GREMLIN_TIMEOUT": "1", "TERNFORGE_GREMLIN_CONFIRM_TIMEOUT": "30"}
        subprocess.run(faults["engine_command"](tmp, ["test_slow_weak.py"], ["slow_target.py"], project=ROOT, config="pytest.ini"), cwd=tmp, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, env=slow_env)
        slow_path = tmp / "coverage/gremlins/gremlins.json"
        slow = list((json.loads(slow_path.read_text()).get("results") or []) if slow_path.exists() else [])
        timeout_ok = bool(slow) and all(row.get("status") == "survived" for row in slow)
        families = {str(row.get("operator")) for row in [*strong, *effects, *python_rows]}
        engine_ok = (
            honest_ok
            and python_ok
            and operators_ok
            and families == set(faults["OPERATORS"])
            and scope_ok
            and effects_ok
            and rule_off_ok
            and diff_ok
            and nosite_ok
            and isolated_ok
            and timeout_ok
        )
        engine_detail = {
            "families": sorted(families),
            "scoped": {"faults": len(scoped_rows), "same_as_full_run": scoped_by_id == full_on_line and bool(full_on_line)},
            "strong": {"faults": len(strong), "caught": sum(row.get("status") in faults["KILLED"] for row in strong)},
            "weak": {"faults": len(weak), "caught": sum(row.get("status") in faults["KILLED"] for row in weak)},
            "effects": {
                "faults": len(effects),
                "caught": sum(row.get("status") in faults["KILLED"] for row in effects),
                "not_reached": len(in_unused),
                "suppressed": len(pinned_return),
                "not_planted": len(not_planted),
                "filtered": extension.get("filtered") or {},
                "ok": effects_ok,
            },
            "python": {
                "faults": len(python_rows),
                "caught": sum(row.get("status") in faults["KILLED"] for row in python_rows),
                "weak_caught": sum(row.get("status") in faults["KILLED"] for row in python_weak_rows),
                "by_operator": dict(sorted(Counter(str(row.get("operator")) for row in python_rows).items())),
                "filtered": (python_report.get("ternforge") or {}).get("filtered") or {},
                "ok": python_ok,
                "operators_leave_alone": operators_ok,
            },
            "rule_turned_off": rule_off_ok,
            "diff_skips_uncovered": diff_ok,
            "no_site_keeps_extension_facts": nosite_ok,
            "isolated_copy_same_outcomes": isolated_ok,
            "slow_suite_no_false_catch": {"ok": timeout_ok, "statuses": sorted({str(row.get("status")) for row in slow})},
            "configuration": faults["engine_configuration"](),
        }
        if not engine_ok:
            engine_detail["tails"] = tails

    return {
        "PRODUCER_PYTEST_GREMLINS": {
            "status": "QUALIFIED" if engine_ok else "NOT QUALIFIED",
            "intended_use": "generate comparison, boundary, arithmetic, boolean, return, statement and body mutants and Python's own (a removed argument, operand, conversion, method call or container element, a swapped attribute, a condition replaced or negated) on the declared target, keep arid code and suppressed mutants out of the run, and report a mutant as caught only when a selected test fails and as not reached when no test covers its line",
            "false_green_control": "parametrized, fixture-using and pytest-bdd tests that assert nothing must catch no mutant; tests that pin the behavior must catch every planted mutant in every family, Python's own among them, and tests that assert nothing none of them; a keyword the callee requires is never removed, a loop's condition is never made True or negated, a statement, module, class or awaited call is never cut to its receiver; a scoped run must reproduce the full run's mutants on those lines exactly; mutants in logging code must not be planted unless the policy turns the rule off; a suppressed mutant must not run and must carry its category; a generator or dunder body must not be replaced; mutants of uncovered code must be reported not reached, and the diff run must not run them",
            "control": engine_detail,
        },
        "PRODUCER_IMPLEMENTATION_FAULT_ADAPTER": {
            "status": "QUALIFIED" if resolution_ok and attribution_ok and projection_ok and reuse_ok else "NOT QUALIFIED",
            "intended_use": "resolve @impl scopes from the graph, attribute each mutated line to one contract family, project engine results onto Implementation fault classes by outcome (caught, survived, not reached, invalid, suppressed), and reuse a retained result only while it is still current",
            "false_green_control": "a line several contracts claim challenged for one of them with another's tests, a failing test, an unreached, surviving, invalid or suppressed mutant, an unmapped operator, or a retained result whose engine, scope, arid rules, tests or inputs changed must never make a class detected; a fingerprint ignores only what cannot change a run (comments, docstrings and layout of a tool; comments edited in place in code under test), never changed code, a mutation pragma or a moved line; the product file that holds a contract's mutants stales that contract, and a mutant's time limit follows its tests' measured time",
        },
    }


def semantic_mutant_controls() -> dict[str, dict[str, object]]:
    """Qualify the semantic mutant cascade on its calibration set: every proposal with a known
    outcome must get exactly that outcome, and a draft test must be kept or rejected as specified."""
    cascade = runpy.run_path(str(ROOT / ".ai-bridge/semantic_mutants.py"), run_name="evidence_confidence_semantic")
    calibration = ROOT / ".ai-bridge/semantic-mutants/calibration"
    payload = json.loads((calibration / "proposals.json").read_text())
    expected = {row["id"]: row["expected"] for row in payload["proposals"]}

    # Bounded by paths, as the Test Plan bounds it, so the control repeats on any machine.
    judgement = {"seconds": 60, "paths": 100, "members": ["m1", "m2"], "threshold": 0.5, "calibrated": True, "answers": payload["judgement_answers"]}

    def run(drafts: dict[str, str], proposals: list[dict] | None = None) -> list[dict]:
        request = {
            "root": str(calibration),
            "contract_id": "CALIBRATION",
            "proposals": payload["proposals"] if proposals is None else proposals,
            "tests": ["checks/calibration_checks.py"],
            "context_sha256": {cascade["selection_key"](row): payload["context_sha256"] for row in payload["proposals"]},
            "drafts": drafts,
            "judgement": judgement,
            # The campaign's limits for tests that take a few seconds: a mutant that hangs is caught.
            "time_limits": [15.0, 30.0],
        }
        with tempfile.TemporaryDirectory(prefix="ternforge-semantic-qualification-") as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            result_path = Path(temp_dir) / "result.json"
            request_path.write_text(json.dumps(request))
            subprocess.run(
                [shutil.which("uv") or "uv", "run", "--with", "pytest-gremlins==1.9.0", "--with", "crosshair-tool==0.0.110", "python",
                 str(ROOT / ".ai-bridge/semantic_mutants.py"), "run", str(request_path), str(result_path)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800,
            )
            return list(json.loads(result_path.read_text())["results"]) if result_path.exists() else []

    results = run(cascade["load_drafts"]("calibration"))
    # The builder judges a contract's proposals in chunks at once: judged so, the calibration set gets
    # the same outcome for every proposal, and a repeated mutant stays in its original's chunk.
    builder = runpy.run_path(str(ROOT / ".ai-bridge/build-mutation-report-prototype.py"), run_name="evidence_confidence_chunks")
    chunks = builder["cascade_chunks"](calibration, payload["proposals"], 2)
    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        parts = list(pool.map(lambda chunk: {"results": run(cascade["load_drafts"]("calibration"), [payload["proposals"][index] for index in chunk])}, chunks))
    chunked = builder["merge_chunks"](payload["proposals"], chunks, parts)["results"]
    chunked_same = [(row["id"], row["outcome"]) for row in chunked] == [(row["id"], row["outcome"]) for row in results]
    repeated_together = any({"C-CAUGHT", "C-REPEATED"} <= {payload["proposals"][index]["id"] for index in chunk} for chunk in chunks)
    # The same mutant selected for two classes carries one id twice: its results keep their places.
    twins = [{"id": "SM-TWIN", "class": "c1"}, {"id": "SM-TWIN", "class": "c2"}]
    twin_rows = [{"id": "SM-TWIN", "class": "c1", "outcome": "caught"}, {"id": "SM-TWIN", "class": "c2", "outcome": "duplicate"}]
    merged_twins = builder["merge_chunks"](twins, [[0, 1]], [{"results": twin_rows}])["results"]
    twins_ok = (
        [(row["class"], row["outcome"]) for row in merged_twins] == [("c1", "caught"), ("c2", "duplicate")]
        and not builder["results_pair"](list(reversed(twin_rows)), twins)
    )
    # Draft tests against whole mutated modules, judged in two processes at once, are kept and rejected
    # as the cascade keeps and rejects them, and come back in their order.
    distinguished = next(row for row in payload["proposals"] if row["id"] == "C-DISTINGUISHED")
    pin_path, pin_qualname = distinguished["target"].split("::", 1)
    pin_module = cascade["apply_replacement"]((calibration / pin_path).read_text(), pin_qualname, distinguished["replacement"])
    kept_draft = cascade["load_drafts"]("calibration")["C-DISTINGUISHED"]
    pin_items = [
        {"key": key, "path": pin_path, "mutated_source": pin_module, "draft": draft, "tests": ["checks/calibration_checks.py"], "qualname": pin_qualname}
        for key, draft in (("kept", kept_draft), ("rejected", (calibration / "rejected.draft.py").read_text()), ("kept again", kept_draft))
    ]
    pinned = builder["judge_pins_at_once"](calibration, pin_items, 2)
    pins_ok = [(row["key"], row["accepted"]) for row in pinned] == [("kept", True), ("rejected", False), ("kept again", True)]
    outcomes = {row["id"]: row["outcome"] for row in results}
    reasons = {row["id"]: str(row.get("reason") or "") for row in results}
    judged = {row["id"]: row.get("judgement") or {} for row in results}
    found_by = {row["id"]: (row.get("differential") or {}).get("by") for row in results}
    kept = next((row.get("draft") or {} for row in results if row["id"] == "C-DISTINGUISHED"), {})
    rejected_results = run({"C-DISTINGUISHED": (calibration / "rejected.draft.py").read_text()})
    rejected = next((row.get("draft") or {} for row in rejected_results if row["id"] == "C-DISTINGUISHED"), {})
    primitive_results = run({"C-DISTINGUISHED": (calibration / "rejected-primitive.draft.py").read_text()})
    primitive = next((row.get("draft") or {} for row in primitive_results if row["id"] == "C-DISTINGUISHED"), {})
    projection = cascade["class_projection"](results).get("spec.wrong-outcome") or {}
    # A mutant that hangs leaves no test process behind once its time limit stopped the run.
    leftover = subprocess.run(["pgrep", "-f", "checks/calibration_checks.py"], capture_output=True, text=True, check=False).stdout.split()
    # A type its module imports only for type checking leaves a function without an input strategy
    # instead of stopping the cascade.
    with tempfile.TemporaryDirectory(prefix="ternforge-hints-qualification-") as temp_dir:
        hinted_path = Path(temp_dir) / "hinted_control.py"
        hinted_path.write_text(
            "from __future__ import annotations\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from elsewhere import Hidden\n\n\n"
            "def take(value: Hidden) -> int:\n    return 1\n"
        )
        hinted = runpy.run_path(str(hinted_path), run_name="hinted_control")
        try:
            cascade["_hints"](hinted["take"], hinted)
            hints_refused = False
        except TypeError:
            hints_refused = True
    # A selection is a class at a target: a function whose proposals are of one class still owes
    # the other classes selected for it, and a selection without any proposal keeps its class undecided.
    missing = cascade["targets_without_proposals"](
        [{"class": "spec.wrong-outcome", "target": "src/calibration_target.py::double", "budget": 1, "risk": "r"},
         {"class": "spec.wrong-outcome", "target": "src/calibration_target.py::Record.summary", "budget": 1, "risk": "r"},
         {"class": "spec.missing-partition", "target": "src/calibration_target.py::double", "budget": 1, "risk": "r"}],
        payload["proposals"],
    )
    unchallenged = cascade["add_targets_without_proposals"](
        cascade["class_projection"](results),
        [{"class": "spec.missing-partition", "target": "src/calibration_target.py::nowhere", "budget": 1, "risk": "r"}],
    ).get("spec.missing-partition") or {}
    normal_form = cascade["normal_form"]
    # A scenario pytest-bdd generates has no function of its own: its module's steps are the example.
    with tempfile.TemporaryDirectory(prefix="ternforge-example-qualification-") as temp_dir:
        module = Path(temp_dir) / "tests/test_scenarios.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            'from pytest_bdd import given, scenarios\n\nscenarios("records.feature")\n'
            'globals()["test_a_record"] = globals()["test_a_record"]\n\n\n'
            '@given("a record", target_fixture="record")\ndef a_record() -> dict:\n    return {"name": "r"}\n'
        )
        scenario_example = cascade["example_test"](Path(temp_dir), ["tests/test_scenarios.py::test_a_record"])
    # A draft that fails on the original is rejected with pytest's errors, the same on every run.
    failing_output = (
        "E   AssertionError: in /tmp/ternforge-copy/tests/t.py for <Record at 0x10ab3f>\n>   raise\n"
        "E   AssertionError: in /tmp/ternforge-copy/tests/t.py for <Record at 0x7ffe01>\nE   KeyError: 'name'\n"
    )
    failing_errors = cascade["test_errors"](failing_output, Path("/tmp/ternforge-copy"))
    failing_reason = cascade["draft_rejection"]({"ran": True, "passes_on_original": 0, "original_errors": failing_errors, "fails_on_mutant": True})
    # A draft is judged in the project's style: formatted and safely fixed, and a lint rule it still breaks rejects it.
    sloppy = "import os\nimport pytest\ndef test_x(unused):\n    value=1\n    try:\n        assert value==1\n    except Exception:\n        pass\n"
    normalized, lint = cascade["normalize_draft"](sloppy, "tests/llm_router/mutation_pins/test_pin_qualification.py")
    renormalized, relint = cascade["normalize_draft"](normalized, "tests/llm_router/mutation_pins/test_pin_qualification.py")
    lint_reason = cascade["draft_rejection"]({"ran": False, "lint": lint})
    style_ok = (
        "import os" not in normalized and "value = 1" in normalized and renormalized == normalized and relint == lint
        and any("S110" in item for item in lint) and any("ARG001" in item for item in lint)
        and lint_reason.startswith("it breaks the project's lint rules (ruff: ")
        and cascade["DRAFT_PASSES"] == 5
    )
    # A Technical requirement's pin may import its module and the project modules that module imports;
    # `from package import module` imports the module, not the package.
    with tempfile.TemporaryDirectory(prefix="ternforge-pin-imports-") as imports_dir:
        tree = Path(imports_dir) / "src"
        for name, text in {
            "pkg/__init__.py": "", "pkg/other.py": "", "pkg/util.py": "", "pkg/sub/__init__.py": "", "pkg/sub/base.py": "",
            "pkg/sub/mod.py": "import json\nimport pkg.util\nfrom .base import Thing\nfrom .. import other\n",
        }.items():
            (tree / name).parent.mkdir(parents=True, exist_ok=True)
            (tree / name).write_text(text)
        resolved = cascade["module_imports"](tree / "pkg/sub/mod.py", "pkg.sub.mod")
    imports_ok = (
        resolved == {"pkg", "pkg.other", "pkg.util", "pkg.sub.base"}
        and cascade["draft_imports"]("from pkg.sub import mod\n", {"pkg.sub.mod"}) == {"pkg.sub.mod"}
        and cascade["draft_imports"]("from pkg.sub import mod\n") == {"pkg.sub"}
    )
    # The grounding check finds, before anything runs, each name, member and argument a draft uses that
    # the project does not define, and nothing else: whatever the tree alone cannot settle (a name from
    # an outside package, a constant, a submodule, an inherited constructor) is never a problem.
    with tempfile.TemporaryDirectory(prefix="ternforge-grounding-") as grounding_dir:
        project = Path(grounding_dir)
        for name, text in {
            "src/pkg/__init__.py": "from outside_lib import Helper\n\nfrom .types import Child, Kind, Limits, Record\n",
            "src/pkg/types.py": (
                "from dataclasses import dataclass\nfrom enum import StrEnum\n\nfrom pydantic import BaseModel\n\nCONSTANT = 1\n\n\n"
                "class Kind(StrEnum):\n    A = \"a\"\n    B = \"b\"\n\n    def label(self) -> str:\n        return self.value\n\n\n"
                "@dataclass\nclass Limits:\n    rate: float\n    burst: int = 1\n\n\n"
                "class Record(BaseModel):\n    name: str\n\n\n"
                "class Base:\n    def __init__(self, *, size: int) -> None:\n        self.size = size\n\n\n"
                "class Child(Base):\n    pass\n"
            ),
            "src/pkg/_internal/__init__.py": "",
            "src/pkg/_internal/deep.py": "class Hidden:\n    pass\n",
            "tests/support/helpers.py": "VALUE = 1\n\n\ndef helper() -> None:\n    return None\n",
        }.items():
            (project / name).parent.mkdir(parents=True, exist_ok=True)
            (project / name).write_text(text)
        grounded, grounded_used = cascade["grounding_problems"](project, (
            "from pkg import Child, Helper, Kind, Limits, Record, _internal\nfrom pkg.types import CONSTANT\n"
            "from tests.support.helpers import VALUE, helper\n\n\ndef test_good():\n"
            "    assert Kind.A.value == \"a\" and Kind.B and Kind.label\n    Limits(rate=1.0, burst=2)\n    Record(name=\"x\")\n"
            "    Child(size=1)\n    Helper(anything=1)\n    assert CONSTANT == VALUE and helper() is None and _internal\n"
        ), "pkg")
        invented, _invented_used = cascade["grounding_problems"](project, (
            "from pkg import Child, Kind, Limits\nfrom pkg.types import Hidden\nfrom pkg.nowhere import Thing\n\n\n"
            "def test_bad():\n    assert Kind.C and Hidden and Thing\n    Limits(rate=1.0, limit=2)\n    Child(width=1)\n"
        ), "pkg")
        # A call that leaves out what a constructor needs, directly or through the draft's own subclass;
        # a positional argument fills its field, and a subclass with fields of its own is not judged.
        unbuilt, _unbuilt_used = cascade["grounding_problems"](project, (
            "from pkg import Child, Limits, Record\n\n\nclass Wider(Child):\n    label = \"w\"\n\n\n"
            "class Own(Child):\n    extra: int = 0\n\n\n"
            "class Short(Child):\n    def __init__(self, label: str) -> None:\n        super().__init__(width=label)\n\n\n"
            "def test_unbuilt():\n    Limits(burst=2)\n    Limits(1.0)\n    Record()\n    Wider(width=1)\n    Own(depth=1)\n"
        ), "pkg")
        (project / "pyproject.toml").write_text("[tool.pytest.ini_options]\nasyncio_mode = \"auto\"\n")
        auto_rule = cascade["asyncio_rule"](project)
        (project / "pyproject.toml").write_text("[tool.pytest.ini_options]\naddopts = \"-q\"\n")
        strict_rule = cascade["asyncio_rule"](project)
        callers = cascade["module_callers"](
            "def helper(value):\n    return value\n\n\ndef caller():\n    return helper(1)\n\n\n"
            "class Owner:\n    def method(self):\n        return helper(2)\n",
            "helper",
        )
        callees = cascade["module_callees"](
            "def check(value):\n    return value > 0\n\n\ndef unused():\n    return 0\n\n\n"
            "def target(values):\n    return list(filter(check, values))\n",
            "target",
        )
        summary_errors = cascade["test_errors"](
            "F\n=== short test summary info ===\n"
            "FAILED tests/test_x.py::test_x - Failed: async def functions are not natively supported.\n1 failed\n",
            Path("/tmp/ternforge-copy"),
        )
        card = cascade["api_card"](project, "from pkg import Kind, Limits\n", package="pkg")
        gaps = cascade["context_gaps"](["pkg.Kind", "pkg.types.Limits", "tests.support.helpers.helper"], "Build it with Kind and helper().")
    grounding_ok = (
        grounded == []
        and {"pkg.Kind", "pkg.Helper", "pkg.types.CONSTANT", "tests.support.helpers.helper"} <= set(grounded_used)
        and invented == [
            "Child cannot be built without size",
            "Child takes no argument width; it takes size",
            "Kind has no member C; its members are A, B",
            "Limits takes no argument limit; it takes burst, rate",
            "pkg.types has no Hidden (it lives in pkg._internal.deep)",
            "the project has no module pkg.nowhere",
        ]
        and unbuilt == [
            "Child cannot be built without size",
            "Child takes no argument width; it takes size",
            "Limits cannot be built without rate",
            "Record cannot be built without name",
            "Wider cannot be built without size",
            "Wider takes no argument width; it takes size",
        ]
        and auto_rule == "" and "@pytest.mark.asyncio" in strict_rule
        and "def caller():" in callers and "def method(self):" in callers and "def helper" not in callers
        and "def check(value):" in callees and "def unused" not in callees and "def target" not in callees
        and summary_errors == ["Failed: async def functions are not natively supported."]
        and "`Kind` (from pkg.types): an enum whose only members are A, B" in card
        and "`Limits` (from pkg.types): Limits(rate: float, burst: int = …)" in card
        and gaps == ["pkg.types.Limits"]
        and "sources" in cascade["DRAFT_ANSWER_SCHEMA"]["required"]
        and cascade["draft_rejection"]({"ran": False, "grounding": invented[:1]}).startswith("it does not fit the project's code as written: Child cannot")
    )
    # The draft author's aids: the path to a changed line, read from the function's code, and what a
    # weak draft reached, a statement counted on its first line and a function's def not as a call.
    demo = (
        "def f(x, items):\n    if x is None:\n        return 0\n    for item in items:\n        try:\n            value = int(item)\n"
        "        except ValueError:\n            continue\n        except TypeError:\n            if x > 1:\n                return -1\n    return 1\n"
    )
    path_text = cascade["path_to_line"](demo, "f", 11)
    spread = "def g(flag):\n    return dict(\n        a=1,\n        b=flag,\n    )\n"
    spread_defect = spread.replace("b=flag", "b=not flag")
    reach_all = cascade["reach_text"](cascade["draft_reach"](spread_defect, spread, "g", [2]))
    reach_none = cascade["reach_text"](cascade["draft_reach"](spread_defect, spread, "g", [1]))
    # The check a model with tools runs in its copy: a forbidden primitive is refused unrun, a weak draft
    # is told what it reached of the defect.
    proposal = next(row for row in payload["proposals"] if row["id"] == "C-DISTINGUISHED")
    target_path, target_name = proposal["target"].split("::", 1)
    defect = cascade["apply_replacement"]((calibration / target_path).read_text(), target_name, proposal["replacement"])
    weak_draft = (
        "from calibration_target import Record  # ty: ignore[unresolved-import]\n\n\n"
        "def test_summary_names_the_record() -> None:\n    value = \"s\"\n    assert Record(name=\"n\", secret=value, level=3).summary()[\"name\"] == \"n\"\n"
    )
    agent_reports = {}
    with tempfile.TemporaryDirectory(prefix="ternforge-agent-check-qualification-") as temp_dir:
        room = cascade["prepare_workspace"](calibration, Path(temp_dir) / "copy", {
            "path": target_path, "qualname": target_name, "mutated_source": defect, "tests": ["checks/calibration_checks.py"],
            "as_path": cascade["DRAFT_PATH"], "extra_imports": [],
        })
        for name, draft_text in (("primitive", (calibration / "rejected-primitive.draft.py").read_text()), ("weak", weak_draft)):
            (Path(room["root"]) / room["write"]).write_text(draft_text)
            done = subprocess.run(room["command"].split(), cwd=room["root"], text=True, capture_output=True, timeout=900, check=False)
            agent_reports[name] = done.stdout
        copied = sorted(item.name for item in Path(room["root"]).iterdir())
    aids_ok = (
        path_text == (
            "The changed line 11 runs only when `x is None` is false (else line 2 leaves first); the loop over `items` runs (line 4); "
            "the block under the try at line 5 raises TypeError and not ValueError, which are caught first; `x > 1` is true (line 10)."
        )
        and reach_all == ": it runs the changed line 4, yet nothing it checks depends on what the change does"
        and reach_none == ": it never runs the function under test, so it never reaches the changed line 4"
        and cascade["line_ranges"]([2, 4, 5, 6, 12]) == "2, 4–6 and 12"
        and room["command"] == cascade["CHECK_COMMAND"] and room["write"] == cascade["DRAFT_PATH"]
        # The copy holds the project's code, tests and settings and the check, and nothing else: no history, no keys.
        and ".draft-tools" in copied and set(copied) <= {".draft-tools", "src", "tests", "features", "checks", "pyproject.toml", "uv.lock"}
    )
    agent_ok = (
        "- not run: " in agent_reports.get("primitive", "") and "exec" in agent_reports.get("primitive", "")
        and "- on the original: passes 5 of 5 runs" in agent_reports.get("weak", "")
        and "passes, so the test misses it: of the changed lines" in agent_reports.get("weak", "") and "but never line" in agent_reports.get("weak", "")
        and "The cascade would reject it" in agent_reports.get("weak", "")
        and cascade["CHECK_COMMAND"] in cascade["with_tools"]("Q", "tests/test_x.py") and "tests/test_x.py" in cascade["with_tools"]("Q", "tests/test_x.py")
    )
    ok = (
        outcomes == expected
        and "adds an import" in reasons.get("C-CONFINED", "")
        and "does not define" in reasons.get("C-INVALID", "")
        and "does not import" in reasons.get("C-UNIMPORTABLE", "")
        and "do not finish on it" in reasons.get("C-HANGS", "")
        and "earlier proposal is the same mutant" in reasons.get("C-REPEATED", "")
        and chunked_same
        and repeated_together
        and twins_ok
        and pins_ok
        and not leftover
        and hints_refused
        and found_by.get("C-SYMBOLIC") == "symbolic search"
        and (judged.get("C-EQUIVALENT") or {}).get("status") == "likely-equivalent"
        and (judged.get("C-REFUTED") or {}).get("status") == "unsure"
        and [item.get("by") for item in (judged.get("C-REFUTED") or {}).get("refuted") or []] == ["m1"]
        and kept.get("accepted") is True
        and rejected.get("accepted") is False
        and "os" in (rejected.get("imports_beyond_allowed") or [])
        and rejected.get("fails_on_mutant") is False
        and rejected.get("ran") is False
        and primitive.get("accepted") is False
        and primitive.get("ran") is False
        and "exec" in (primitive.get("primitives") or [])
        and [(row["class"], row["target"]) for row in missing] == [("spec.missing-partition", "src/calibration_target.py::double")]
        and unchallenged.get("undecided") == 1
        and unchallenged.get("not_generated") == 1
        and unchallenged.get("exercised") is False
        and projection.get("exercised") is True
        and projection.get("detected") is False
        and projection.get("undecided") == 3
        and normal_form("def f(x):\n    # note\n    return x") == normal_form('def f(x):\n    """Doc."""\n    return (x)')
        and normal_form("def f(x):\n    return x") != normal_form("def f(x):\n    return -x")
        and '@given("a record"' in scenario_example and "def a_record" in scenario_example
        and "scenarios(" not in scenario_example and "globals()" not in scenario_example
        and failing_errors == ["AssertionError: in ./tests/t.py for <Record>", "KeyError: 'name'"]
        and failing_reason == "it does not pass on the original 5 times in a row (pytest: AssertionError: in ./tests/t.py for <Record> | KeyError: 'name')"
        and style_ok
        and imports_ok
        and grounding_ok
        and aids_ok
        and agent_ok
    )
    return {
        "PRODUCER_SEMANTIC_MUTANT_CASCADE": {
            "status": "QUALIFIED" if ok else "NOT QUALIFIED",
            "intended_use": "judge frozen semantic mutant proposals for a named risk without a model: reject identical, duplicate, invalid and unconfined ones, run the rest against the contract's passing tests in an isolated copy, and look for an input that tells a survivor apart from the original",
            "false_green_control": "a calibration set with a known outcome for every proposal: an identical, a rule-duplicate, an invalid, a confined one that adds an import, one whose module no longer imports, a caught, an equivalent (must stay undecided, never caught, and only be labelled likely equivalent by unanimous assessors), a distinguishable (must be found), one only the symbolic search finds, one whose assessor input is refuted, a stale, a reviewer-judged equivalent and a mutant an earlier proposal repeats; the set judged in chunks at once, as the builder judges a contract, with the same outcome for every proposal and the repeated mutant in its original's chunk, and the results of one mutant selected for two classes, which carry one id, kept in their places; draft tests against a whole mutated module judged in two processes at once, kept and rejected in their order; a kept draft, a draft that imports beyond the allowed and one that uses exec, both rejected without being run; a selected target without proposals that must keep its class undecided; a scenario pytest-bdd generates, whose example for a draft must be its module's step definitions; a draft failing on the original, rejected with pytest's errors free of the copy's path and memory addresses; a draft in the project's style only, formatted and safely fixed, rejected for a lint rule it still breaks; the imports a draft may use, where `from package import module` imports the module and a Technical requirement's module brings the project modules it imports itself; and a small project on which the grounding check must find exactly the invented member, the two unknown arguments, the misplaced import and the missing module of one draft, the arguments a call leaves out (also through the draft's own subclass and its super().__init__, not for a positional argument or a subclass with fields of its own) in another, and nothing in a third that uses a name from an outside package, a constant, a submodule, a test helper and an inherited constructor, with the API card naming every enum member and field, and a name the draft uses that its question never shows counted as a gap; pytest's reason for a failure without error lines; the async test rule only for pytest-asyncio's strict mode; the callers of a module-level function and the functions of its module it calls or hands on; the path to a changed line read from its function's branches, loops, handlers and early exits; what a weak draft reached of its defect, a statement counted on its first line and a function's def not as a call; and the check a model with tools runs in its copy of the calibration project, refusing a forbidden primitive unrun and telling a weak draft which changed lines it never reached",
            "control": {
                "outcomes": outcomes, "expected": expected, "reasons": reasons, "kept_draft": kept, "rejected_draft": rejected,
                "chunks": [[payload["proposals"][index]["id"] for index in chunk] for chunk in chunks], "chunked_same": chunked_same,
                "pins_at_once": [(row["key"], row["accepted"]) for row in pinned],
                "primitive_draft": primitive, "projection": projection, "target_without_proposals": unchallenged,
                "judgement": {key: {"status": value.get("status"), "found_by": found_by.get(key)} for key, value in judged.items() if value},
                "scenario_example_lines": len(scenario_example.splitlines()),
                "grounding": {"grounded": grounded, "invented": invented, "unbuilt": unbuilt},
                "aids": {"path": path_text, "reach_all": reach_all, "reach_none": reach_none},
                "agent_check": agent_reports,
            },
        }
    }


def model_generation_controls() -> dict[str, dict[str, object]]:
    """Qualify the model generation adapter without calling a model. It must read a recorded real
    answer of every backend it may use, keep every failure from becoming an answer, defer a call
    above the budget, try backends in order, and bind what it stores to what the model returned."""
    models = runpy.run_path(str(ROOT / ".ai-bridge/model_generation.py"), run_name="evidence_confidence_models")
    semantic = runpy.run_path(str(ROOT / ".ai-bridge/semantic_mutants.py"), run_name="evidence_confidence_semantic_ingest")
    fixtures = ROOT / ".ai-bridge/semantic-mutants/calibration/model-fixtures"
    invocation = models["Invocation"]
    checks: dict[str, bool] = {}

    # Recorded real answers of claude-cli, and variants of them that must never read as an answer.
    stream = (fixtures / "claude-cli-success.ndjson").read_text()
    schema = json.loads((fixtures / "claude-cli-success.schema.json").read_text())
    events = [json.loads(line) for line in stream.splitlines() if line.strip()]
    recorded = next(event for event in events if event["type"] == "result")
    read = models["parse_claude_stream"](stream, "", 0, schema)
    checks["claude reads a recorded answer, its tokens, price and windows"] = (
        read.outcome == "ok"
        and read.structured == recorded["structured_output"]
        and read.tokens.get("output") == recorded["usage"]["output_tokens"]
        and read.list_usd == round(recorded["total_cost_usd"], 6)
        and (read.windows or {}).get("five_hour") is not None
        and bool(read.backend_version)
    )

    def variant(change) -> str:
        copied = [json.loads(json.dumps(event)) for event in events]
        change({event["type"]: event for event in copied})
        return "\n".join(json.dumps(event) for event in copied if event.get("type") != "dropped")

    failures = {
        "an answer that breaks its schema is invalid": (
            variant(lambda by: by["result"]["structured_output"]["proposals"][0].pop("replacement")), "invalid"),
        "a rejected usage window is rejected": (
            variant(lambda by: by["rate_limit_event"]["rate_limit_info"].update(status="rejected")), "rejected"),
        "a call billed to an API key is an error": (
            variant(lambda by: by["system"].update(apiKeySource="ANTHROPIC_API_KEY")), "error"),
        "a stream without a result is an error": (variant(lambda by: by["result"].update(type="dropped")), "error"),
        "a usage-limit error is rejected": (
            variant(lambda by: by["result"].update(is_error=True, subtype="error_during_execution", api_error_status=429)), "rejected"),
    }
    for label, (text, outcome) in failures.items():
        parsed = models["parse_claude_stream"](text, "", 1, schema)
        checks[label] = parsed.outcome == outcome and parsed.structured is None
    ineligible = models["parse_antigravity_json"]((fixtures / "antigravity-cli-ineligible.json").read_text(), "", 1, schema)
    checks["an ineligible Antigravity account is unavailable, without its link"] = (
        ineligible.outcome == "unavailable" and ineligible.structured is None and "http" not in ineligible.reason and "<" not in ineligible.reason
    )
    backends_qualified = ["claude-cli"] if all(checks.values()) else []
    agy_success = fixtures / "antigravity-cli-success.json"
    if agy_success.exists():
        agy_schema = json.loads((fixtures / "antigravity-cli-success.schema.json").read_text())
        agy_recorded = json.loads(agy_success.read_text())
        agy_read = models["parse_antigravity_json"](agy_success.read_text(), "", 0, agy_schema)
        agy_checks = {
            "antigravity reads a recorded answer and its tokens": (
                agy_read.outcome == "ok" and agy_read.structured == agy_recorded["structured_output"]
                and agy_read.tokens.get("output") == agy_recorded["usage"]["output_tokens"]
                and agy_read.tokens.get("input") == agy_recorded["usage"]["input_tokens"]
            ),
        }

        def agy_variant(change) -> str:
            copied = json.loads(json.dumps(agy_recorded))
            change(copied)
            return json.dumps(copied)

        agy_failures = {
            "an Antigravity answer that breaks its schema is invalid": (agy_variant(lambda payload: payload["structured_output"].pop("reason")), "invalid"),
            "an Antigravity call that reached for a denied tool is invalid": (
                agy_variant(lambda payload: payload.update(structured_output=None, response="", denied_actions=[{"action": "command"}])), "invalid"),
            "an exhausted Antigravity quota is rejected": (
                agy_variant(lambda payload: payload.update(status="ERROR", error="RESOURCE_EXHAUSTED: quota exceeded", structured_output=None)), "rejected"),
            "an Antigravity run without a JSON answer is an error": ("", "error"),
        }
        for label, (text, outcome) in agy_failures.items():
            parsed = models["parse_antigravity_json"](text, "" if text else "agy crashed", 0 if text else 1, agy_schema)
            agy_checks[label] = parsed.outcome == outcome and parsed.structured is None
        checks.update(agy_checks)
        if all(agy_checks.values()):
            backends_qualified.append("antigravity-cli")

    # Claude CLI profiles: each signs in with its own folder; the host session's variables never reach a call.
    saved = {key: os.environ.get(key) for key in ("CLAUDE_CODE_QUALIFY_MARKER", "CLAUDE_CONFIG_DIR", "TERNFORGE_CLAUDE_PROFILE")}
    # run_path returns a copy of the module's names; the functions read their own.
    profile_globals = models["claude_profile"].__globals__
    setting = profile_globals["CLAUDE_PROFILE_SETTING"]
    try:
        os.environ["CLAUDE_CODE_QUALIFY_MARKER"] = "1"
        os.environ["CLAUDE_CONFIG_DIR"] = "/elsewhere"
        os.environ.pop("TERNFORGE_CLAUDE_PROFILE", None)
        plain, named = models["claude_env"]("default"), models["claude_env"]("second")
        with tempfile.TemporaryDirectory(prefix="ternforge-profile-qualification-") as profile_dir:
            profile_globals["CLAUDE_PROFILE_SETTING"] = Path(profile_dir) / "claude-profile"
            unset = models["claude_profile"]()
            profile_globals["CLAUDE_PROFILE_SETTING"].write_text("second\n")
            chosen = models["claude_profile"]()
            os.environ["TERNFORGE_CLAUDE_PROFILE"] = "third"
            overridden = models["claude_profile"]()
        checks["a Claude profile signs in with its own folder, and the host session's variables never reach a call"] = (
            "CLAUDE_CONFIG_DIR" not in plain and "CLAUDE_CODE_QUALIFY_MARKER" not in plain and "CLAUDE_CODE_QUALIFY_MARKER" not in named
            and named.get("CLAUDE_CONFIG_DIR") == str(models["CLAUDE_PROFILES_DIR"] / "second")
            and unset[0] == "default" and chosen[0] == "second" and overridden[0] == "third"
        )
    finally:
        profile_globals["CLAUDE_PROFILE_SETTING"] = setting
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # One run over scripted backends: the guard, the order, the limit, and nothing stored from a failure.
    class Scripted:
        def __init__(self, answers):
            self.answers = list(answers)
            self.calls = 0
            self.caps = []

        def version(self) -> str:
            return "0.0.0"

        def invoke(self, **request):
            self.calls += 1
            self.caps.append(request.get("usd_cap"))
            return self.answers.pop(0)

    def probe(windows=None):
        return invocation("ok", "", {"text": "OK"}, {"input": 1, "output": 1}, 0.001, 0.1, windows, "0.0.0", "m")

    answer = {"proposals": [{"defect": "reads the output tokens as the input tokens", "replacement": "def f(x):\n    return x + 1"}]}

    def answered(windows=None):
        return invocation("ok", "", answer, {"input": 10, "output": 5}, 0.01, 1.0, windows, "0.0.0", "m")

    budget = {"five_hour": 0.8, "seven_day": 0.7, "calls_per_run": 5, "usd_per_call": 0.5, "draft_attempts": 2}
    both = [{"order": 1, "backend": "claude-cli", "model": "first"}, {"order": 2, "backend": "antigravity-cli", "model": "second"}]
    request = {
        "purpose": "semantic-mutants", "contract_id": "CALIBRATION", "subject": "src/x.py::f", "system": "s",
        "prompt": "p", "schema": semantic["mutant_answer_schema"](2),
    }
    with tempfile.TemporaryDirectory(prefix="ternforge-model-qualification-") as temp_dir:
        temp = Path(temp_dir)

        def run_with(roles, backends, name, limits=budget):
            return models["Run"]({"generator": roles, "draft_author": roles}, limits, ledger_path=temp / f"{name}.jsonl", backends=backends)

        full = Scripted([probe({"five_hour": 0.85, "seven_day": 0.1})])
        run = run_with(both[:1], {"claude-cli": full}, "deferred")
        row, response = run.call("generator", response_dir=temp / "deferred", **request)
        checks["a window above its limit defers the call without making it"] = (
            row["outcome"] == "deferred" and response is None and full.calls == 1 and not (temp / "deferred").exists()
            and [entry["outcome"] for entry in run.rows] == ["ok", "deferred"]
        )

        signed = Scripted([probe(), answered()])
        signed.profile = "second"
        run = run_with(both[:1], {"claude-cli": signed}, "account")
        run.call("generator", response_dir=temp / "account", **request)
        label = models["account_label"]("second")
        checks["every ledger row names the sign-in it used by a label that carries no profile name"] = (
            [entry.get("account") for entry in run.rows] == [label, label]
            and label.startswith("profile-") and "second" not in label and models["account_label"]("default") == "default"
        )

        absent = Scripted([invocation("unavailable", "not signed in")])
        second = Scripted([probe(), answered()])
        run = run_with(both, {"claude-cli": absent, "antigravity-cli": second}, "fallback")
        row, response = run.call("generator", response_dir=temp / "fallback", **request)
        stored = json.loads(next((temp / "fallback").glob("*.json")).read_text()) if response else {}
        checks["an unavailable backend falls back to the next in order"] = (
            response is not None and response["backend"] == "antigravity-cli" and response["model"] == "second"
            and row["response_sha256"] == models["response_sha256"](stored)
            and [entry["outcome"] for entry in run.rows] == ["unavailable", "unavailable", "ok", "ok"]
        )

        steady = Scripted([probe(), answered(), answered()])
        run = run_with(both[:1], {"claude-cli": steady}, "limit", {**budget, "calls_per_run": 1})
        first, _ = run.call("generator", response_dir=temp / "limit", **request)
        second_row, second_response = run.call("generator", response_dir=temp / "limit", **request)
        checks["the run's call limit defers the next call"] = (
            first["outcome"] == "ok" and second_row["outcome"] == "deferred" and second_response is None and steady.calls == 2
        )

        # Calls made at once: a backend takes at most its parallel calls, the run's limit is never
        # overrun by calls reserved together, and the results come back in the order asked.
        class Concurrent(Scripted):
            def __init__(self, answers):
                super().__init__(answers)
                self.active = self.most = 0
                self.guard = threading.Lock()

            def invoke(self, **request):
                with self.guard:
                    self.active += 1
                    self.most = max(self.most, self.active)
                time.sleep(0.2)
                with self.guard:
                    self.active -= 1
                    return super().invoke(**request)

        busy = Concurrent([probe(), answered(), answered(), answered(), answered()])
        run = run_with(both[:1], {"claude-cli": busy}, "parallel", {**budget, "calls_per_run": 4, "parallel_calls": 2})
        results = run.call_many([{"role": "generator", "response_dir": temp / "parallel", **request, "subject": subject} for subject in "abcde"])
        checks["calls made at once respect each backend's parallel limit and the run's call limit, in the order asked"] = (
            busy.most == 2
            and sorted(row["outcome"] for row, _response, _attempts in results) == ["deferred", "ok", "ok", "ok", "ok"]
            and [row["subject"] for row, _response, _attempts in results] == list("abcde")
            and busy.calls == 5
            and all(row.get("parallel_limit") == 2 and row.get("in_flight") in {1, 2} for row, _response, _attempts in results if row["outcome"] == "ok")
        )
        # A pool that answers overloaded (capacity or rate, not quota) halves its limit, then grows back
        # by one at a time, never above the ceiling; the ledger says so.
        strained = Concurrent([probe(), invocation("error", "the call failed: UNAVAILABLE (code 503): No capacity available"), *[answered() for _ in range(5)]])
        run = run_with(both[:1], {"claude-cli": strained}, "strained", {**budget, "calls_per_run": 10, "parallel_calls": 2})
        results = run.call_many([{"role": "generator", "response_dir": temp / "strained", **request, "subject": subject} for subject in "abcdef"])
        # The ledger in the order calls finished: threads take their turn in any order of the requests.
        timeline = [row for row in run.rows if row.get("role") == "generator"]
        backed = [index for index, row in enumerate(timeline) if row.get("backed_off")]
        checks["a pool that answers overloaded halves its limit and grows back one at a time, and the ledger says so"] = (
            len(backed) == 1 and any(row.get("parallel_limit") == 1 for row in timeline[backed[0] + 1:])
            and max(row.get("parallel_limit") or 0 for row in timeline) == 2
            and run.limits.get(run.concurrency_pool("claude-cli", both[0]["model"])) == 2 and strained.most <= 2
        )
        # Slow start: a pool whose calls at the limit are all answered doubles its limit up to the ceiling.
        eager = Concurrent([probe(), *[answered() for _ in range(12)]])
        run = run_with(both[:1], {"claude-cli": eager}, "eager", {**budget, "calls_per_run": 20, "parallel_calls": 2, "parallel_calls_max": 4})
        results = run.call_many([{"role": "generator", "response_dir": temp / "eager", **request, "subject": f"s{index}"} for index in range(12)])
        eager_limits = [row.get("parallel_limit") for row in run.rows if row.get("role") == "generator"]
        checks["a pool whose calls are answered grows its limit from the start value to the ceiling and never past it"] = (
            eager.most == 4 and eager_limits[0] == 2 and max(eager_limits) == 4
            and run.limits.get(run.concurrency_pool("claude-cli", both[0]["model"])) == 4
            and all(row["outcome"] == "ok" for row, _response, _attempts in results)
        )

        # A price cap is a fuse that follows the role's most expensive answered call, never a price
        # list that a change of the models' prices leaves in the way.
        (temp / "priced.jsonl").write_text(json.dumps({"schema": models["LEDGER_SCHEMA"], "role": "generator", "outcome": "ok", "list_usd": 0.4, "call_id": "earlier"}) + "\n")
        priced = Scripted([probe(), answered()])
        run = models["Run"]({"generator": both[:1]}, budget, ledger_path=temp / "priced.jsonl", backends={"claude-cli": priced})
        run.call("generator", response_dir=temp / "priced", **request)
        checks["a call's price cap follows its role's most expensive answered call, never below the Test Plan's"] = (
            priced.caps == [0.05, 1.2] and models["price_cap"](budget, {}, "generator", False) == 0.5
        )
        dear = invocation("ok", "", answer, {"input": 10, "output": 5}, 0.9, 1.0, None, "0.0.0", "m")
        capped = Scripted([probe(), invocation("capped", "the call reached its list-price cap"), dear])
        run = run_with(both[:1], {"claude-cli": capped}, "capped")
        row, response = run.call("generator", response_dir=temp / "capped", **request)
        stopped = Scripted([probe(), invocation("capped", "the call reached its list-price cap"), invocation("capped", "the call reached its list-price cap")])
        after = Scripted([probe(), answered()])
        run_next = run_with(both, {"claude-cli": stopped, "antigravity-cli": after}, "stopped")
        next_row, next_response = run_next.call("generator", response_dir=temp / "stopped", **request)
        checks["a call that reaches its price cap is asked once more at twice the cap, then of the next model"] = (
            response is not None and capped.caps == [0.05, 0.5, 1.0] and [entry["outcome"] for entry in run.rows] == ["ok", "capped", "ok"]
            and run.price_cap("generator", False) == 2.7
            and next_response is not None and next_response["backend"] == "antigravity-cli" and stopped.caps == [0.05, 0.5, 1.0]
            and [entry["outcome"] for entry in run_next.rows] == ["ok", "capped", "capped", "ok", "ok"] and next_row["outcome"] == "ok"
        )

        # A call asks for its level by flag and the ledger records it; a retry answers one level up the
        # model's ladder; a level that has not passed its canaries is skipped for the next one up.
        class Leveled(Scripted):
            def __init__(self, answers):
                super().__init__(answers)
                self.efforts = []

            def invoke(self, **request):
                self.efforts.append(request.get("effort"))
                return super().invoke(**request)

        climbing = Leveled([probe(), answered(), answered(), answered()])
        leveled_run = models["Run"](
            {"draft_author": [{"order": 1, "backend": "claude-cli", "model": "first", "effort": ["low", "medium"]}]}, budget,
            ledger_path=temp / "levels.jsonl", backends={"claude-cli": climbing},
        )
        first_rows = leveled_run.call_with_attempts("draft_author", response_dir=temp / "levels", **request)[2]
        retry_rows = leveled_run.call_with_attempts("draft_author", response_dir=temp / "levels", step=1, **request)[2]
        leveled_run.blocked[("draft_author", "claude-cli", "first", "low")] = "failed its canaries"
        skipped_rows = leveled_run.call_with_attempts("draft_author", response_dir=temp / "levels", **request)[2]
        stored_levels = sorted(json.loads(path.read_text()).get("effort") for path in (temp / "levels").glob("*.json"))
        checks["a call asks for its level by flag and records it, a retry climbs the model's ladder, and a level its canaries have not passed is skipped"] = (
            climbing.efforts == [None, "low", "medium", "medium"]
            and [row.get("effort") for row in first_rows + retry_rows + skipped_rows] == ["low", "medium", "medium"]
            and stored_levels == ["low", "medium", "medium"]
        )

        # Several Antigravity accounts through agm: a run reads their quotas, moves agy alone to the one
        # with the most left once the one in use is spent, asks a rejected call again on another account,
        # defers when none has any left, names every account by a digest and puts agy back at the end.
        class FakeAgm:
            executable = "agm"

            def __init__(self, quotas, active):
                self.quotas, self.active, self.switches = quotas, active, []
                self.addresses = {alias: f"{alias}@example.test" for alias in quotas}

            def snapshot(self):
                return {alias: {**row, "agy": alias == self.active} for alias, row in self.quotas.items()}

            def cli_address(self):
                return self.addresses[self.active]

            def alias_of(self, address):
                return next(alias for alias, known in self.addresses.items() if known == address)

            def switch(self, alias):
                self.switches.append(alias)
                self.active = alias
                return True

        class AgyScripted(Scripted):
            smaller_pool = "other"

            def __init__(self, answers, accounts):
                super().__init__(answers)
                self.accounts, self.profile = accounts, ""

            @staticmethod
            def quota_pool(model):
                return "gemini" if model.startswith("gemini") else "other"

        switcher = FakeAgm({"main": {"gemini-pro": 0, "gemini-flash": 0, "other": 10}, "second": {"gemini-pro": 99, "gemini-flash": 99, "other": 100}}, "main")
        spent = invocation("rejected", "the Antigravity quota rejected the call: RESOURCE_EXHAUSTED")
        agy_accounts = AgyScripted([probe(), answered(), spent], switcher)
        claude_after = Scripted([probe(), answered()])
        pro_first = [{"order": 1, "backend": "antigravity-cli", "model": "gemini-3.1-pro-high"}, {"order": 2, "backend": "claude-cli", "model": "claude-sonnet-5-5"}]
        accounts_run = models["Run"]({"generator": pro_first}, budget, ledger_path=temp / "accounts.jsonl", backends={"antigravity-cli": agy_accounts, "claude-cli": claude_after})
        first_row, first_answer = accounts_run.call("generator", response_dir=temp / "accounts", **request)
        _second_row, second_answer = accounts_run.call("generator", response_dir=temp / "accounts", **{**request, "subject": "src/x.py::g"})
        accounts_run.restore_accounts()
        ledger_text = json.dumps(accounts_run.rows)
        listed = "EMAIL  STATUS  GEM-PRO  GEM-FLASH  CLAUDE\n-----\na@example.test  cli,ide  0%  0%  10%\nb@example.test  99%  99%  100%\n"
        checks["with several Antigravity accounts a run moves agy alone to one with quota left, asks a rejected call again on another, defers when none has any, names accounts by a digest and puts agy back"] = (
            first_answer is not None and first_answer["backend"] == "antigravity-cli" and first_row["account"] == models["account_label"]("second")
            and second_answer is not None and second_answer["backend"] == "claude-cli"
            and [row["outcome"] for row in accounts_run.rows if row["backend"] == "antigravity-cli"] == ["ok", "ok", "rejected", "deferred"]
            and switcher.switches == ["second", "main"] and switcher.active == "main"
            and '"main"' not in ledger_text and '"second"' not in ledger_text
            and models["parse_agm_list"](listed) == {
                "a@example.test": {"agy": True, "gemini-pro": 0, "gemini-flash": 0, "other": 10},
                "b@example.test": {"agy": False, "gemini-pro": 99, "gemini-flash": 99, "other": 100},
            }
            and models["parse_agm_aliases"]("ALIAS  EMAIL\nsecond  b@example.test\n") == {"b@example.test": "second"}
            and [models["quota_family"](model) for model in ("gemini-3.1-pro-high", "gemini-3.8-flash-high", "claude-opus-4-6-thinking")] == ["gemini-pro", "gemini-flash", "other"]
        )

        # A refusal that names when its quota resets keeps that quota spent on the account agy's
        # credential store confirmed until then, in the next run too, and the call goes to another
        # account; a refusal the store did not confirm, or whose reset has passed, blocks nothing. Once
        # every account is spent, the call waits without being made.
        stamp = datetime.now(UTC)

        def refused(alias, model, hours_ago, resets, verified):
            return {"schema": models["LEDGER_SCHEMA"], "backend": "antigravity-cli", "model": model, "account": models["account_label"](alias),
                    "outcome": "rejected", "at": (stamp - timedelta(hours=hours_ago)).isoformat(timespec="seconds").replace("+00:00", "Z"),
                    "reason": f"the Antigravity quota rejected the call: Individual quota reached. Resets in {resets}.", "account_verified": verified}

        pro = "gemini-3.1-pro-high"
        spent_rows = [refused("main", pro, 1, "10h0m0s", True), refused("second", pro, 1, "10h0m0s", False), refused("main", "gemini-3.8-flash-high", 30, "5h0m0s", True)]
        (temp / "spent.jsonl").write_text("".join(json.dumps(row) + "\n" for row in spent_rows))
        roomy = FakeAgm({"main": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}, "second": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}}, "main")
        moved_agy = AgyScripted([probe(), answered()], roomy)
        spent_run = models["Run"]({"generator": [{"order": 1, "backend": "antigravity-cli", "model": pro}]}, budget,
                                  ledger_path=temp / "spent.jsonl", backends={"antigravity-cli": moved_agy})
        spent_row, spent_answer = spent_run.call("generator", response_dir=temp / "spent", **request)
        (temp / "all-spent.jsonl").write_text("".join(json.dumps(row) + "\n" for row in [refused("main", pro, 1, "10h0m0s", True), refused("second", pro, 2, "20h0m0s", True)]))
        empty = FakeAgm({"main": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}, "second": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}}, "second")
        waiting_agy = AgyScripted([probe()], empty)
        waiting_run = models["Run"]({"generator": [{"order": 1, "backend": "antigravity-cli", "model": pro}]}, budget,
                                    ledger_path=temp / "all-spent.jsonl", backends={"antigravity-cli": waiting_agy})
        waiting_row, waiting_answer = waiting_run.call("generator", response_dir=temp / "all-spent", **request)
        checks["a refusal that names when its quota resets keeps it spent on the account the credential store confirmed until then, and the call goes to another account"] = (
            spent_answer is not None and spent_row["account"] == models["account_label"]("second") and roomy.switches == ["second"]
            and spent_run.quota_left("antigravity-cli", "main", pro) == -1 and spent_run.quota_left("antigravity-cli", "second", pro) == 99
            and spent_run.quota_left("antigravity-cli", "main", "gemini-3.8-flash-high") == 99
            and waiting_answer is None and waiting_row["outcome"] == "deferred" and "resets at" in waiting_row["reason"]
            and waiting_agy.calls == 1 and empty.switches == []
        )

        # agm's list may name another account than the one agy's credential store holds: the store says
        # which account agy uses, a switch counts once the store holds the new account, and a refusal
        # that arrives when the store holds another account blames none and follows the store.
        class AgmCommands:
            def __init__(self, listed_cli, store, follows=True):
                self.listed_cli, self.store, self.follows = listed_cli, store, follows

            def __call__(self, command, **_kwargs):
                verb = command[1]
                out = {
                    "alias": "ALIAS  EMAIL\nmain  a@example.test\nsecond  b@example.test\n",
                    "list": "".join(f"{address}  {'cli' if address == self.listed_cli else ''}  50%  50%  50%\n" for address in ("a@example.test", "b@example.test")),
                    "sync": f"Account Sync Status\n\nCLI (agy) credential store: {self.store}\n  Present in local DB.\n",
                }.get(verb, "")
                if verb == "switch" and self.follows:
                    self.store = command[2]
                return subprocess.CompletedProcess(command, 0, out, "")

        diverged = models["AgmAccounts"]("agm", AgmCommands("b@example.test", "a@example.test"))
        diverged_snapshot = diverged.snapshot()
        stuck = models["AgmAccounts"]("agm", AgmCommands("a@example.test", "a@example.test", follows=False))
        stuck.snapshot()

        class Flipping(AgyScripted):
            def invoke(self, **request):
                self.accounts.active = "main"
                return super().invoke(**request)

        flipped = FakeAgm({"main": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}, "second": {"gemini-pro": 99, "gemini-flash": 99, "other": 99}}, "second")
        flipping_agy = Flipping([probe(), invocation("rejected", "the Antigravity quota rejected the call: Individual quota reached. Resets in 90h0m0s."), answered()], flipped)
        flip_run = models["Run"]({"generator": [{"order": 1, "backend": "antigravity-cli", "model": pro}]}, budget,
                                 ledger_path=temp / "flip.jsonl", backends={"antigravity-cli": flipping_agy})
        _flip_row, flip_answer = flip_run.call("generator", response_dir=temp / "flip", **request)
        flip_refusal = next(row for row in flip_run.rows if row["outcome"] == "rejected")
        checks["agy's credential store, not agm's list, says which account agy uses: a switch counts once the store holds it, and a refusal the store no longer confirms blames no account"] = (
            {alias: row["agy"] for alias, row in diverged_snapshot.items()} == {"main": True, "second": False}
            and diverged.switch("second") and diverged.cli_address() == "b@example.test"
            and not stuck.switch("second")
            and flip_answer is not None and flip_refusal["account_verified"] is False and flip_refusal["account"] == models["account_label"]("second")
            and flip_run.quota_left("antigravity-cli", "second", pro) == 99 and flip_run.quota_left("antigravity-cli", "main", pro) == 99
            and flipping_agy.profile == "main"
        )

        # Two channels at once: while the first model's pool runs as many calls as it takes, the role's
        # next model on another pool answers; once the first has room again, it answers.
        spill_run = models["Run"](
            {"generator": both}, {**budget, "parallel_calls": 1, "parallel_calls_max": 1}, ledger_path=temp / "spill.jsonl",
            backends={"claude-cli": Scripted([probe(), answered()]), "antigravity-cli": Scripted([probe(), answered()])},
        )
        busy_pool = spill_run.concurrency_pool("claude-cli", both[0]["model"])
        _count, _limit, busy_epoch = spill_run.enter(busy_pool)
        _row, spilled_answer = spill_run.call("generator", response_dir=temp / "spill", **request)
        spill_run.leave(busy_pool, busy_epoch, False, False)
        _row, first_answer = spill_run.call("generator", response_dir=temp / "spill", **{**request, "subject": "src/x.py::g"})
        checks["two channels at once: while the first model's pool is full the role's next model on another pool answers, and the first answers once it has room"] = (
            spilled_answer is not None and spilled_answer["backend"] == "antigravity-cli"
            and first_answer is not None and first_answer["backend"] == "claude-cli"
        )

        # A Claude sign-in with no room left in its windows hands over to another signed-in profile of the
        # machine that has room, probed once; the ledger names the one each call used.
        class Profiled(Scripted):
            def __init__(self, answers):
                super().__init__(answers)
                self.profile, self.used = "first", []

            def profiles(self):
                return ["first", "second"]

            def invoke(self, **request):
                self.used.append(self.profile)
                return super().invoke(**request)

        full_window, roomy_window = {"five_hour": 1.0, "seven_day": 0.2}, {"five_hour": 0.1, "seven_day": 0.2}
        profiled = Profiled([probe(full_window), probe(roomy_window), answered(roomy_window)])
        profile_run = models["Run"]({"generator": both[:1]}, budget, ledger_path=temp / "profiles.jsonl", backends={"claude-cli": profiled})
        handed_row, handed_answer = profile_run.call("generator", response_dir=temp / "profiles", **request)
        checks["a Claude sign-in with no room left hands over to another signed-in profile that has room, probed once"] = (
            handed_answer is not None and profiled.used == ["first", "second", "second"]
            and handed_row["account"] == models["account_label"]("second")
            and [entry["outcome"] for entry in profile_run.rows] == ["ok", "ok", "ok"]
        )

        sloppy = Scripted([probe(), invocation("invalid", "the answer breaks its schema")])
        untouched = Scripted([probe(), answered()])
        run = run_with(both, {"claude-cli": sloppy, "antigravity-cli": untouched}, "invalid")
        row, response = run.call("generator", response_dir=temp / "invalid", **request)
        checks["an invalid answer stores nothing and is not retried elsewhere"] = (
            row["outcome"] == "invalid" and response is None and not (temp / "invalid").exists() and untouched.calls == 0
        )

        limited = Scripted([probe(), invocation("rejected", "window full")])
        spare = Scripted([probe(), answered(), answered()])
        run = run_with(both, {"claude-cli": limited, "antigravity-cli": spare}, "rejected")
        row, response = run.call("generator", response_dir=temp / "rejected", **request)
        _again, again_response = run.call("generator", response_dir=temp / "rejected", **{**request, "subject": "src/x.py::g"})
        checks["a rejected call moves on, and the full window defers the next"] = (
            response is not None and response["backend"] == "antigravity-cli" and limited.calls == 2
            and [entry["outcome"] for entry in run.rows if entry["backend"] == "claude-cli"] == ["ok", "rejected", "deferred"]
            and again_response is not None and again_response["backend"] == "antigravity-cli"
        )

        # A backend without an account window (a scripted one meters each model apart; Antigravity has a
        # Gemini pool and one for the rest): a full quota stops the models of its pool alone.
        per_model = Scripted([probe(), invocation("rejected", "Individual quota reached"), answered(), answered()])
        same_backend = [{"order": 1, "backend": "antigravity-cli", "model": "a"}, {"order": 2, "backend": "antigravity-cli", "model": "b"}]
        run = run_with(same_backend, {"antigravity-cli": per_model}, "per-model")
        _row, per_model_response = run.call("generator", response_dir=temp / "per-model", **request)
        _row, per_model_again = run.call("generator", response_dir=temp / "per-model", **{**request, "subject": "src/x.py::h"})
        pools = models["AntigravityCli"].quota_pool
        checks["Antigravity's two quota pools: the Gemini family, and every other model"] = (
            pools("gemini-3.1-pro-high") == pools("gemini-3.8-flash-high") == "gemini"
            and pools("claude-sonnet-4-6") == pools("claude-opus-4-6-thinking") == pools("gpt-oss-120b-medium") == "other"
        )
        checks["a model's own full quota defers only that model on a backend that meters models apart"] = (
            per_model_response is not None and per_model_response["model"] == "b"
            and per_model_again is not None and per_model_again["model"] == "b"
            and [entry["outcome"] for entry in run.rows if entry.get("model") == "a"] == ["rejected", "deferred"]
        )

        # Antigravity reports neither quota, so its smaller pool is bounded by the calls the ledger shows
        # it took in the last seven days: older calls, Gemini calls and calls never made do not count.
        pool_now = datetime.now(UTC)

        def pool_row(model, outcome, days):
            written = (pool_now - timedelta(days=days)).isoformat(timespec="seconds").replace("+00:00", "Z")
            return {"at": written, "backend": "antigravity-cli", "model": model, "outcome": outcome, "role": "generator"}

        week_ledger = temp / "pool-week.jsonl"
        week_ledger.write_text("".join(json.dumps(row) + "\n" for row in [
            pool_row("claude-a", "ok", 1), pool_row("claude-a", "invalid", 2), pool_row("claude-a", "ok", 6),
            pool_row("claude-a", "ok", 8), pool_row("claude-a", "deferred", 1), pool_row("gemini-a", "ok", 1),
        ]))

        class Pooled(Scripted):
            quota_pool = staticmethod(models["AntigravityCli"].quota_pool)
            smaller_pool = models["AntigravityCli"].smaller_pool

        pooled = Pooled([probe(), answered(), answered()])
        run = models["Run"](
            {"generator": [{"order": 1, "backend": "antigravity-cli", "model": "claude-a"}],
             "draft_author": [{"order": 1, "backend": "antigravity-cli", "model": "gemini-a"}]},
            {**budget, "pool_calls_per_week": 4}, ledger_path=week_ledger, backends={"antigravity-cli": pooled},
        )
        within, within_response = run.call("generator", response_dir=temp / "pool-week", **request)
        over, over_response = run.call("generator", response_dir=temp / "pool-week", **{**request, "subject": "src/x.py::k"})
        gemini, gemini_response = run.call("draft_author", response_dir=temp / "pool-week", **{**request, "subject": "src/x.py::m"})
        checks["the smaller pool's calls in the last seven days defer its next call at the limit, and a Gemini call still goes"] = (
            within["outcome"] == "ok" and within_response is not None
            and over["outcome"] == "deferred" and "4 calls in the last 7 days" in over["reason"] and over_response is None
            and gemini["outcome"] == "ok" and gemini_response is not None and pooled.calls == 3
        )

        if response is not None:
            tampered = {**response, "prompt": response["prompt"] + " "}
            broken = {**response, "structured": {"proposals": []}}
            checks["a stored answer is bound to its prompt, schema and content"] = (
                models["verify_response"](response) == []
                and "the prompt does not match its digest" in models["verify_response"](tampered)
                and "the answer breaks its schema" in models["verify_response"](broken)
                and models["response_sha256"](broken) != models["response_sha256"](response)
            )
        totals = models["spend"](run.rows)
        attempted = [entry for entry in run.rows if entry["role"] != "probe"]
        checks["the spend of a run adds up its calls and counts no deferred attempt as a call"] = (
            totals["attempts"] == len(attempted)
            and totals["calls"] == sum(entry["outcome"] not in {"deferred", "unavailable"} for entry in attempted)
            and totals["deferred"] == sum(entry["outcome"] == "deferred" for entry in attempted) > 0
            and totals["tokens"]["output"] == sum(int((entry.get("tokens") or {}).get("output") or 0) for entry in run.rows)
            and totals["tokens"]["total"] == sum(
                int((entry.get("tokens") or {}).get(key) or 0) for entry in run.rows for key in ("input", "cache_read", "cache_write", "output")
            )
        )

    # The Test Plan tables are read fail-closed.
    parse_roles, parse_budget = models["parse_roles"], models["parse_budget"]
    roles_ok = [
        {"Role": role, "Order": "1", "Backend": "`claude-cli`", "Model": "`m`"} for role in models["ROLES"]
    ]
    budget_ok = [
        {"Budget": label, "Limit": {"five_hour": "80%", "seven_day": "70%", "usd_per_call": "$0.50", "usd_per_tool_call": "$5.00", "agy_quota_floor": "0%"}.get(key, "2")}
        for label, key in models["BUDGET_LABELS"].items()
    ]

    def refuses(parse, rows) -> bool:
        try:
            parse(rows)
        except RuntimeError:
            return True
        return False

    checks["the Model generation and budget tables are read fail-closed"] = (
        bool(parse_roles(roles_ok)) and parse_budget(budget_ok)["five_hour"] == 0.8
        and refuses(parse_roles, [*roles_ok, {"Role": "Judge", "Order": "1", "Backend": "`claude-cli`", "Model": "`m`"}])
        and refuses(parse_roles, [{**roles_ok[0], "Backend": "`api`"}, *roles_ok[1:]])
        and refuses(parse_roles, [{**roles_ok[0], "Order": "2"}, *roles_ok[1:]])
        and refuses(parse_roles, roles_ok[:1])
        and refuses(parse_budget, budget_ok[:-1])
        and refuses(parse_budget, [{**budget_ok[0], "Limit": "eighty"}, *budget_ok[1:]])
    )
    # A level is named fail-closed: a rising ladder only for a role whose every answer execution
    # checks, one level for a judge and the generator, a level the backend takes, and none for an
    # Antigravity model whose id names its level.
    def with_effort(role, effort, **change):
        return [{**row, "Effort": effort, **change} if row["Role"] == role else row for row in roles_ok]

    checks["a model's level is read fail-closed: a rising ladder only where execution checks every answer, one level for a judge and the generator, none for a model whose id names it"] = (
        parse_roles(with_effort("Draft test author", "`low` → `high`"))["draft_author"][0]["effort"] == ["low", "high"]
        and parse_roles(with_effort("Survivor verdict", "`xhigh`"))["verdict"][0]["effort"] == ["xhigh"]
        and parse_roles(roles_ok)["verdict"][0]["effort"] == []
        and refuses(parse_roles, with_effort("Survivor verdict", "`low` → `high`"))
        and refuses(parse_roles, with_effort("Semantic mutant generator", "`low` → `high`"))
        and refuses(parse_roles, with_effort("Draft test author", "`high` → `low`"))
        and refuses(parse_roles, with_effort("Draft test author", "`low` → `low`"))
        and refuses(parse_roles, with_effort("Survivor verdict", "`turbo`"))
        and refuses(parse_roles, with_effort("Survivor verdict review", "`low`", Backend="`antigravity-cli`", Model="`gemini-3.8-flash-high`"))
    )
    # An assessor's ladder of levels is one model per level, and the calibration climbs it one level at
    # a time, stopping at the first level that meets the calibration floors.
    seats = models["parse_assessors"]([
        {"Assessor": "1", "Order": "1", "Backend": "`claude-cli`", "Model": "`a`", "Effort": "`low` → `medium`"},
        {"Assessor": "1", "Order": "2", "Backend": "`claude-cli`", "Model": "`b`", "Effort": ""},
        {"Assessor": "2", "Order": "1", "Backend": "`antigravity-cli`", "Model": "`c-high`", "Effort": "—"},
    ])
    distinct_ids = ["d1", "d2", "d3", "d4", "d5"]
    ladder_answers = {pid: {"claude-cli:a@low": {"verdict": "equivalent" if pid == "d1" else "distinct"}, "claude-cli:a@medium": {"verdict": "distinct"}} for pid in distinct_ids}
    ladder_confirmed = {pid: {"claude-cli:a@low": pid in {"d2", "d3"}, "claude-cli:a@medium": True} for pid in distinct_ids}
    ladder_below = models["ladder_below_floors"](seats, {"claude-cli:a@low", "claude-cli:a@medium"}, distinct_ids, ladder_answers, ladder_confirmed, {}, 0.1)
    observed_equivalent = models["calibration_floors"]("claude-cli:a@medium", distinct_ids, ladder_answers, ladder_confirmed, {f"o{index}": {"claude-cli:a@medium": {"verdict": "equivalent"}} for index in range(2)}, 0.1)
    checks["an assessor's ladder of levels is one model per level, climbed one level at a time until a level meets the calibration floors"] = (
        [row["key"] for row in seats] == ["claude-cli:a@low", "claude-cli:a@medium", "claude-cli:b", "antigravity-cli:c-high"]
        and [row["order"] for row in seats] == [1, 2, 3, 1]
        and models["calibration_search"](seats, set()) == {"claude-cli:a@low", "claude-cli:b", "antigravity-cli:c-high"}
        and ladder_below == {"claude-cli:a@low"}
        and models["calibration_search"](seats, ladder_below) == {"claude-cli:a@medium", "claude-cli:b", "antigravity-cli:c-high"}
        and models["calibration_search"](seats, {"claude-cli:a@low", "claude-cli:a@medium"}) == {"claude-cli:b", "antigravity-cli:c-high"}
        and not observed_equivalent["met"] and observed_equivalent["distinct_answered"] == 7
    )
    # An assessor may list several models in order; every combination of its usable models, one per
    # assessor, is one the calibration must cover.
    parse_assessors, combine = models["parse_assessors"], models["assessor_configurations"]
    seats_ok = [
        {"Assessor": "1", "Order": "1", "Backend": "`antigravity-cli`", "Model": "`claude-a`"},
        {"Assessor": "1", "Order": "2", "Backend": "`claude-cli`", "Model": "`claude-b`"},
        {"Assessor": "2", "Order": "1", "Backend": "`antigravity-cli`", "Model": "`gemini-a`"},
    ]
    seated = parse_assessors(seats_ok)
    keys = [row["key"] for row in seated]
    checks["an assessor's models are read in order, and each combination of usable ones is one per assessor"] = (
        [(row["assessor"], row["order"]) for row in seated] == [(1, 1), (1, 2), (2, 1)]
        and combine(seated, set(keys)) == [[keys[0], keys[2]], [keys[1], keys[2]]]
        and combine(seated, {keys[1], keys[2]}) == [[keys[1], keys[2]]] and combine(seated, {keys[0]}) == []
        and parse_assessors([{key: value for key, value in row.items() if key != "Order"} for row in seats_ok[1:]]) != []
        and refuses(parse_assessors, [{**seats_ok[0], "Order": "2"}, *seats_ok[1:]])
        and refuses(parse_assessors, [seats_ok[1], seats_ok[0], seats_ok[2]])
        and refuses(parse_assessors, [*seats_ok, {**seats_ok[0], "Assessor": "3"}])
        and refuses(parse_assessors, [{**seats_ok[2], "Assessor": "3"}, *seats_ok[:2]])
    )

    # What an accepted answer becomes: at most the budget, one per distinct mutant, each naming its call.
    context = {"requirement": {"id": "CALIBRATION", "revision": 1, "statement": "s"}, "criteria": [], "risk": "r", "budget": 2, "target": "src/x.py::f"}
    selection = {"class": "spec.wrong-outcome", "target": "src/x.py::f", "budget": 2, "risk": "r"}
    reply = {"call_id": "call", "backend": "claude-cli", "backend_version": "1", "model": "m", "prompt_sha256": "p", "structured": {"proposals": [
        {"defect": "adds one to the result", "replacement": "def f(x):\n    return x + 1"},
        {"defect": "the same defect, reformatted", "replacement": "def f(x):\n    # again\n    return (x + 1)"},
        {"defect": "subtracts one from the result", "replacement": "def f(x):\n    return x - 1"},
    ]}}
    taken = semantic["proposals_from_answer"](selection, context, reply, "digest", "def f(x):\n    return x")
    checks["an answer yields at most the budget of distinct, attributed proposals"] = (
        [row["rationale"] for row in taken] == ["adds one to the result", "subtracts one from the result"]
        and all(row["generator"] == {**row["generator"], "kind": "model", "call_id": "call", "response_sha256": "digest"} for row in taken)
        and taken[0]["id"] == semantic["proposal_id"]("def f(x):\n    return (x + 1)")
        and semantic["draft_from_answer"]("SM-1", {"test_code": "def test_x():\n    pass"}).startswith("# semantic-mutant: SM-1\n")
    )

    # A call with tools (the draft author's ladder) is held to its copy of the project: it may read the
    # copy, write one file and run one command, without asking anyone and without the person's own
    # settings, never under the person's home; a call without tools keeps no tool at all; only the
    # claude CLI serves a role with tools; and what the tools did is read back from the stream.
    workspace = models["Workspace"](root=Path("/tmp/copy"), write="tests/test_pin.py", command="python3 .draft-tools/check.py")
    cli = models["ClaudeCli"](executable="claude", profile="default")
    with_tools = cli.command("m", "s", {"type": "object"}, 5.0, workspace)
    without = cli.command("m", "s", {"type": "object"}, 0.5)
    settings = json.loads(with_tools[with_tools.index("--settings") + 1])
    agy = models["AntigravityCli"](executable="agy")
    tool_stream = "\n".join(json.dumps(event) for event in (
        {"type": "system", "subtype": "init", "claude_code_version": "2.1.0", "model": "m", "apiKeySource": "none"},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}, {"type": "text", "text": "x"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}, {"type": "tool_use", "name": "Read"}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": "", "structured_output": {"test_code": "x" * 30},
         "usage": {"input_tokens": 1, "output_tokens": 1}, "permission_denials": [{"tool_name": "WebFetch"}]},
    ))
    used = models["parse_claude_stream"](tool_stream, "", 0, {"type": "object"})
    roles_with_tools = [{"Role": role, "Order": "1", "Backend": "`claude-cli`", "Model": "`m`"} for role in models["ROLES"]]
    leveled = cli.command("m", "s", {"type": "object"}, 0.5, effort="high")
    agy_leveled = agy.command("m", "s", "p", None, effort="high")
    checks["no call reads the person's settings, and a level is asked for by flag on either backend only when one is set"] = (
        without[without.index("--setting-sources") + 1] == "" and with_tools[with_tools.index("--setting-sources") + 1] == ""
        and leveled[leveled.index("--effort") + 1] == "high" and "--effort" not in without and "--effort" not in with_tools
        and agy_leveled[agy_leveled.index("--effort") + 1] == "high" and "--effort" not in agy.command("m", "s", "p", None)
    )
    checks["a call with tools is held to its copy of the project, through the claude CLI only, and what its tools did is read back"] = (
        with_tools[with_tools.index("--tools") + 1] == models["TOOLS"] == "Read,Grep,Glob,Write,Edit,Bash"
        and with_tools[with_tools.index("--permission-mode") + 1] == "dontAsk"
        and with_tools[with_tools.index("--setting-sources") + 1] == ""
        and settings == {"permissions": {
            "allow": ["Read(./**)", "Glob", "Grep", "Write(./tests/test_pin.py)", "Edit(./tests/test_pin.py)", "Bash(python3 .draft-tools/check.py)"],
            "deny": ["Read(~/**)", "Write(~/**)", "Edit(~/**)"],
        }}
        and {"--strict-mcp-config", "--safe-mode", "--disable-slash-commands", "--no-session-persistence"} <= set(with_tools)
        and "--dangerously-skip-permissions" not in with_tools and "bypassPermissions" not in with_tools
        and without[without.index("--tools") + 1] == "" and "--permission-mode" not in without and "--settings" not in without
        and agy.invoke(model="m", system="s", prompt="p", schema=None, workspace=workspace).outcome == "unavailable"
        and bool(parse_roles(roles_with_tools))
        and refuses(parse_roles, [{**row, "Backend": "`antigravity-cli`"} if row["Role"] == "Draft test author with tools" else row for row in roles_with_tools])
        and used.outcome == "ok" and used.tools_used == {"Read": 2, "Bash": 1} and used.denied == ["WebFetch"]
    )

    ok = all(checks.values()) and "claude-cli" in backends_qualified
    return {
        "PRODUCER_MODEL_GENERATION_ADAPTER": {
            "status": "QUALIFIED" if ok else "NOT QUALIFIED",
            "intended_use": "call a subscription CLI model for semantic mutants and draft tests (ADR_0004), store only answers within their schema, and ledger and budget every call",
            "false_green_control": "recorded real answers and their failing variants (schema break, rejected window, API-key billing, missing result, usage limit, ineligible account) must never read as an answer; scripted runs must defer above the budget (a window, the run's calls, the smaller pool's week), fall back in order, store nothing from a failure, and bind every stored answer to its prompt, schema and content; a call with tools is held to its copy of the project (read and search it, write one file, run one command, nothing under the person's home, no one asked), only the claude CLI serves a role with tools, and what the tools did and what was refused is read back from the stream",
            "backends_qualified": backends_qualified,
            "control": checks,
        }
    }


def markdown_table(text: str, heading: str) -> list[dict[str, str]]:
    """The table right under a heading, as the builder reads it."""
    import re

    match = re.search(rf"^{re.escape(heading)}\s*$\n\n((?:\|.*\|\n?)+)", text, flags=re.MULTILINE)
    if not match:
        return []
    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    split = lambda line: [cell.strip() for cell in line.strip("|").split("|")]  # noqa: E731
    headers = split(lines[0])
    return [dict(zip(headers, split(line), strict=False)) for line in lines[2:] if len(split(line)) == len(headers)]


def survivor_judgement_controls() -> dict[str, dict[str, object]]:
    """Qualify the symbolic search and the witness check on labelled pairs: every distinct pair's
    input must be confirmed and no equivalent pair's; the symbolic search must find and confirm an
    input for the pairs it is expected to decide and none for its equivalent pairs; a witness that
    reaches beyond plain values must never be evaluated; an assessor's equivalent must only label."""
    judge = runpy.run_path(str(ROOT / ".ai-bridge/survivor_equivalence.py"), run_name="evidence_confidence_judgement")
    folder = ROOT / ".ai-bridge/semantic-mutants/calibration/equivalence"
    payload = judge["calibration_payload"](folder)
    crosshair = [shutil.which("uv") or "uv", "run", "--project", str(ROOT), "--with", "crosshair-tool==0.0.110", "python"]
    checks: dict[str, bool] = {}
    shapes, witnesses, symbolic = {}, {}, {}
    with tempfile.TemporaryDirectory(prefix="ternforge-judgement-qualification-") as temp_dir:
        temp = Path(temp_dir)
        modules = {}
        for pair in payload["pairs"]:
            original_source, mutant_source = judge["pair_sources"](folder, pair)
            harness = judge["harness_for"](original_source, pair["target"])
            shapes[pair["id"]] = harness.get("shape") or harness.get("reason")
            if "reason" in harness:
                continue
            token = pair["id"].lower()
            original_file, mutant_file = temp / f"q_original_{token}.py", temp / f"q_mutant_{token}.py"
            original_file.write_text(judge["with_harness"](original_source, harness))
            mutant_file.write_text(judge["with_harness"](mutant_source, harness))
            original = judge["load_module"](original_file, f"q_original_{token}")
            mutant = judge["load_module"](mutant_file, f"q_mutant_{token}")
            modules[pair["id"]] = (original, mutant, harness)
            if pair["label"] == "distinct":
                witnesses[pair["id"]] = judge["verify_witness"](original, mutant, pair["witness"], harness["parameters"])["verified"]
            if pair.get("symbolic"):
                found = judge["run_symbolic"](original_file, mutant_file, 10, crosshair)
                confirmed = found.get("status") == "different" and judge["verify_witness"](original, mutant, found.get("arguments") or {}, harness["parameters"])["verified"]
                symbolic[pair["id"]] = {"label": pair["label"], "status": found.get("status"), "confirmed": confirmed, "seconds": found.get("seconds")}
        labels = {pair["id"]: pair["label"] for pair in payload["pairs"]}
        checks["every calibration pair has a harness"] = set(shapes.values()) <= {"function", "method", "initializer"} and len(shapes) == len(labels)
        checks["every distinct pair's input is confirmed by execution"] = len(witnesses) == sum(label == "distinct" for label in labels.values()) and all(witnesses.values())
        # CrossHair explores paths in a seeded order: the same bound on paths gives the same search twice.
        repeated = [judge["run_symbolic"](temp / "q_original_d01.py", temp / "q_mutant_d01.py", 60, crosshair, paths=40) for _ in range(2)]
        checks["a bound on paths repeats the same search"] = repeated[0].get("status") == "different" and all(
            {key: row.get(key) for key in ("status", "arguments", "paths")} == {key: repeated[0].get(key) for key in ("status", "arguments", "paths")}
            for row in repeated
        )
        checks["the symbolic search finds and confirms an input for its distinct pairs"] = bool(symbolic) and all(
            row["confirmed"] for row in symbolic.values() if row["label"] == "distinct"
        ) and any(row["label"] == "distinct" for row in symbolic.values())
        checks["the symbolic search confirms no input for its equivalent pairs"] = all(
            not row["confirmed"] for row in symbolic.values() if row["label"] == "equivalent"
        ) and any(row["label"] == "equivalent" for row in symbolic.values())
        # A witness is evaluated only when it is a plain value.
        original, _mutant, _harness = modules["D10"]
        namespace = {**vars(original), "Color": enum.Enum("Color", {"RED": 1})}
        refused = [
            "__import__('os').system('true')", "open('x')", "eval('1')", "(lambda: 1)()", "[item for item in range(3)]",
            "Tally.__init__", "Tally(count=1).bump(1)", "print('x')", "globals()", "Color.__class__", "Tally(**{'count': 1})",
        ]
        allowed = ["{'a': -1}", "('',)", "-1", "float('nan')", "Tally(count=0)", "Color.RED", "<Color.RED: 1>"]
        checks["a witness that reaches beyond plain values is never evaluated"] = all(judge["witness_problems"](item, namespace) for item in refused)
        checks["a plain witness is accepted"] = not any(judge["witness_problems"](item, namespace) for item in allowed)
        checks["found values are written back as expressions that evaluate"] = (
            judge["friendly_repr"](("",)) == "('',)" and judge["friendly_repr"](float("nan")) == "float('nan')"
            and judge["friendly_repr"](namespace["Color"].RED) == "Color.RED" and judge["friendly_repr"](namespace["Tally"](count=1)) == "Tally(count=1)"
        )
        # A version that does not repeat itself tells nothing apart, and an address is not behaviour.
        clock = "import time\n\n\ndef stamp(step: int) -> float:\n    return time.monotonic() + step\n"
        locker = (
            "import threading\n\n\nclass Box:\n    def __init__(self) -> None:\n        self.lock = threading.RLock()\n        self.size = 1\n\n\n"
            "def make(size: int) -> Box:\n    box = Box()\n    box.size = size\n    return box\n"
        )
        steadiness = {}
        for label, source, target in (("clock", clock, "stamp"), ("locker", locker, "make")):
            steady_harness = judge["harness_for"](source, target)
            sides = []
            for side in ("a", "b"):
                file = temp / f"q_{label}_{side}.py"
                file.write_text(judge["with_harness"](source, steady_harness))
                sides.append(judge["load_module"](file, f"q_{label}_{side}"))
            steadiness[label] = (sides, steady_harness)
        (clock_a, clock_b), clock_harness = steadiness["clock"]
        (lock_a, lock_b), lock_harness = steadiness["locker"]
        unstable = judge["verify_witness"](clock_a, clock_b, {"step": "1"}, clock_harness["parameters"])
        steady = judge["verify_witness"](lock_a, lock_b, {"size": "2"}, lock_harness["parameters"])
        checks["a version that does not repeat itself tells nothing apart, and an address is not behaviour"] = (
            not unstable["verified"] and "does not repeat itself" in unstable["reason"]
            and not steady["verified"] and steady["reason"] == "both versions behave the same on it"
        )
        long_original, long_mutant = judge["contrast"]("x" * 400 + "a", "x" * 400 + "b")
        checks["long outcomes are shown where they differ"] = (
            long_original != long_mutant and long_original.endswith("a") and judge["contrast"]("ab", "ac") == ("ab", "ac")
        )
        fraction, fraction_mutant, fraction_harness = modules["D02"]
        checks["a non-finite input never tells versions apart"] = not judge["verify_witness"](fraction, fraction_mutant, {"value": "float('nan')"}, fraction_harness["parameters"])["verified"]
        # A rule mutant is rebuilt from its location and checked against the text the report names.
        originals = (folder / "originals.py").read_text()
        import ast as _ast

        function = next(node for node in _ast.parse(originals).body if isinstance(node, _ast.FunctionDef) and node.name == "d01_non_negative")
        compare = next(node for node in _ast.walk(function) if isinstance(node, _ast.Compare))
        location = {"start": {"line": compare.lineno, "column": compare.col_offset + 1}, "end": {"line": compare.end_lineno, "column": int(compare.end_col_offset or 0) + 1}}
        record = {"qualname": "d01_non_negative", "operator": "comparison", "location": location, "original": "value > 0", "replacement": "value >= 0"}
        rebuilt = judge["rule_mutant_source"](originals, record)
        expected = judge["function_source"]((folder / "mutants.py").read_text(), "d01_non_negative")
        checks["a rule mutant is rebuilt exactly, and a location naming other code is refused"] = (
            _ast.dump(_ast.parse(rebuilt.get("mutated") or "")) == _ast.dump(_ast.parse(expected or ""))
            and "reason" in judge["rule_mutant_source"](originals, {**record, "original": "value < 0"})
        )
        # The judgement: a confirmed assessor input decides; an equivalent only labels, and only calibrated and unanimous.
        share_original, share_mutant = judge["pair_sources"](folder, next(pair for pair in payload["pairs"] if pair["id"] == "D14"))
        double_original, double_mutant = judge["pair_sources"](folder, next(pair for pair in payload["pairs"] if pair["id"] == "E01"))
        verdict = lambda source, mutant, target, answers, members, calibrated, token: judge["judge_survivor"](  # noqa: E731
            source, mutant, target, scratch=temp, token=token, seconds=0, answers=answers, members=members, threshold=0.5, calibrated=calibrated,
        )
        equivalent = {"a": {"verdict": "equivalent", "confidence": 0.9}, "b": {"verdict": "equivalent", "confidence": 0.8}}
        found = verdict(share_original, share_mutant, "d14_share", {"a": {"verdict": "distinct", "confidence": 0.7, "arguments": {"total": "-3", "parts": "2"}, "call_id": "q"}}, ["a"], True, "j1")
        labelled = verdict(double_original, double_mutant, "e01_double", equivalent, ["a", "b"], True, "j2")
        uncalibrated = verdict(double_original, double_mutant, "e01_double", equivalent, ["a", "b"], False, "j3")
        incomplete = verdict(double_original, double_mutant, "e01_double", equivalent, ["a", "b", "c"], True, "j4")
        refuted = verdict(double_original, double_mutant, "e01_double", {"a": {"verdict": "distinct", "confidence": 0.7, "arguments": {"value": "3"}}}, ["a"], True, "j5")
        checks["a confirmed assessor input decides a survivor"] = found.get("status") == "found" and (found.get("witness") or {}).get("by") == "a"
        checks["only a calibrated, unanimous equivalent labels a survivor, and only as likely equivalent"] = (
            labelled.get("status") == "likely-equivalent" and uncalibrated.get("status") == "unsure" and incomplete.get("status") == "unsure"
        )
        checks["a refuted input decides nothing"] = refuted.get("status") == "unsure" and [row["by"] for row in refuted.get("refuted") or []] == ["a"]
        originals_source = (folder / "originals.py").read_text()
        # The search may substitute plain values for a parameter declared object; the assessors are asked about the declaration.
        loose = judge["harness_for"]("def loose(value: object) -> int:\n    return 1\n", "loose")
        asked = judge["assessor_prompt"](target="loose", original="return 1", mutant="return 2", harness=loose)
        checks["an assessor is asked about the parameters as declared, not the search's substitutes"] = (
            loose.get("parameters") == [("value", judge["PAYLOAD_TYPE"])] and "value: object" in asked and judge["PAYLOAD_TYPE"] not in asked
        )
        # A witness may name the project's classes beyond the module's imports, never an ambiguous name.
        import types as _types

        package = _types.ModuleType("tfq_pkg")
        models_module = _types.ModuleType("tfq_pkg.models")
        other_module = _types.ModuleType("tfq_pkg.other")
        for module_name, module in (("tfq_pkg", package), ("tfq_pkg.models", models_module), ("tfq_pkg.other", other_module)):
            sys.modules[module_name] = module
        try:
            Shade = enum.Enum("Shade", {"DARK": 1}, module="tfq_pkg.models")
            models_module.Shade = Shade
            models_module.Twin = type("Twin", (Exception,), {"__module__": "tfq_pkg.models"})
            other_module.Twin = type("Twin", (Exception,), {"__module__": "tfq_pkg.other"})
            target = _types.ModuleType("tfq_target")
            target.Own = type("Own", (Exception,), {"__module__": "tfq_target"})
            names = judge["witness_namespace"](target, "tfq_pkg")
            checks["a witness may name the project's classes beyond the module's imports, never an ambiguous one"] = (
                names.get("Shade") is Shade and "Twin" not in names and "Own" in names
                and "Shade" not in judge["witness_namespace"](target, None)
                and not judge["witness_problems"]("Shade.DARK", names) and judge["witness_problems"]("Shade.LIGHT", names) == ["Shade has no member LIGHT"]
                and judge["project_package"]("/a/src/b/src/tfq_pkg/models.py") == "tfq_pkg" and judge["project_package"]("tests/x.py") is None
            )
        finally:
            for module_name in ("tfq_pkg", "tfq_pkg.models", "tfq_pkg.other"):
                sys.modules.pop(module_name, None)
        # The assessors learn how to build the project's types their target takes or names.
        tree = temp / "guide" / "src" / "tfq_guide"
        tree.mkdir(parents=True)
        (tree / "models.py").write_text(
            "from dataclasses import dataclass, field\nfrom enum import Enum\n\n\nclass Shade(Enum):\n    DARK = 1\n    LIGHT = 2\n\n\n"
            "@dataclass\nclass Box:\n    shade: Shade\n    size: int = 1\n    tag: str = field(default='', init=False)\n\n"
            "    @property\n    def area(self) -> int:\n        return self.size * self.size\n"
        )
        use = "from tfq_guide.models import Box\n\n\ndef pack(box: Box) -> int:\n    return box.size\n\n\ndef loose(thing: object) -> bool:\n    return isinstance(thing, Box)\n"
        (tree / "use.py").write_text(use)
        guide = judge["input_guide"](str(tree / "use.py"), judge["harness_for"](use, "pack"))
        loose_guide = judge["input_guide"](str(tree / "use.py"), judge["harness_for"](use, "loose"))
        checks["the assessors are told how the project's types their target takes or names are built, their properties included"] = (
            "Box(shade: Shade, size: int = …); its properties: area -> int" in guide and "Shade is an enum: DARK, LIGHT" in guide and "tag" not in guide
            and "Box(shade: Shade" in loose_guide
            and judge["input_guide"](str(folder / "originals.py"), judge["harness_for"](originals_source, "e01_double")) == ""
        )
        # An argument given as text is the expression; any other JSON value stands for itself.
        read = judge["argument_text"]
        checks["an answer's arguments are read as expressions, a JSON value as its literal"] = (
            read("-3") == "-3" and read('"x-"') == '"x-"' and read(0) == "0" and read(0.5) == "0.5" and read(True) == "True"
            and read(None) == "None" and read(["a"]) == "['a']" and read({"a": -5}) == "{'a': -5}"
            and not judge["answer_problems"]({"verdict": "distinct", "confidence": 1, "arguments": {"value": 0}, "reason": "r"})
            and bool(judge["answer_problems"]({"verdict": "distinct", "confidence": 1, "arguments": {}, "reason": "r"}))
            and bool(judge["answer_problems"]({"verdict": "equivalent", "confidence": 1.5, "arguments": {}, "reason": "r"}))
        )
        # An answer's sources are its own question's words: copied as they stand, long enough to show
        # something, and quoting a line the change touches; a verdict's also the requirement it turns on.
        clip_original = 'def clip(value: int) -> str:\n    if value > 0:\n        return "```" + str(value)\n    return ""'
        clip_mutant = 'def clip(value: int) -> str:\n    if value >= 0:\n        return "```" + str(value)\n    return ""'
        clip_harness = judge["harness_for"](clip_original + "\n", "clip")
        asked_clip = judge["assessor_prompt"](target="clip", original=clip_original, mutant=clip_mutant, harness=clip_harness, context="Risk the change realizes: zero")
        answer = {"verdict": "distinct", "confidence": 0.9, "arguments": {"value": 0}, "reason": "zero is shown"}
        sourced = {
            name: judge["answer_problems"]({**answer, "sources": sources}, asked_clip)
            for name, sources in (
                ("grounded", ["if value >= 0:"]), ("invented", ["if value > 1:"]), ("beside", ['return "```" + str(value)']),
                ("short", ["value"]), ("none", []),
            )
        }
        verdict_question = judge["verdict_prompt"](
            context="Requirement R (Clip): A positive value is shown with its fence.", target="clip", original=clip_original,
            mutant=clip_mutant, judgement="nothing was found; its label is unsure.",
        )
        pin = {"verdict": "pin", "level": "requirement", "reason": "zero is shown now", "test_focus": "zero shows nothing"}
        pinned = judge["verdict_problems"]({**pin, "sources": ["A positive value is shown with its fence.", "if value > 0:"]}, False, verdict_question)
        unmoored = judge["verdict_problems"]({**pin, "sources": ["if value > 0:"]}, False, verdict_question)
        again = judge["asked_again"](verdict_question, ["x"])
        checks["an answer's sources are its own question's words: a line the change touches, and for a verdict the requirement it turns on"] = (
            sourced["grounded"] == []
            and sourced["invented"] == ["its source «if value > 1:» is not in the question", "none of its sources quotes a line the change touches"]
            and sourced["beside"] == ["none of its sources quotes a line the change touches"]
            and sourced["short"] == ["its source «value» is too short to show anything", "none of its sources quotes a line the change touches"]
            and sourced["none"] == ["it cites no source"]
            and pinned == [] and unmoored == ["none of its sources quotes the requirement, Feature, Goal or criterion it turns on"]
            and judge["asked_question"](again) == verdict_question and judge["verdict_problems"]({**pin, "sources": ["x"]}, False, again)[0] == "its source «x» is not in the question"
            and "Requirement R" not in asked_clip
        )
    # A shown outcome never carries the machine it ran on: a found input may make the code read an
    # environment variable, and a witness goes into a model's question and a public record.
    planted = "tf-qualification-value-7c1e"
    os.environ["TF_QUALIFICATION_SECRET"] = planted
    try:
        shown = judge["redact_environment"](f"{{'env_var': 'TF_QUALIFICATION_SECRET', 'value': '{planted}'}} in {Path.home()}/project")
    finally:
        os.environ.pop("TF_QUALIFICATION_SECRET", None)
    checks["a shown outcome names an environment variable without its value and the home directory without its path"] = (
        planted not in shown and "<$TF_QUALIFICATION_SECRET>" in shown and str(Path.home()) not in shown
    )
    threshold = judge["conformal_threshold"]
    checks["the split-conformal threshold follows its rank"] = (
        threshold([0.0] * 14, 0.1) == 0.0 and threshold([0.1, 0.9], 0.1) is None
        and threshold([0.2] * 9 + [0.95], 0.1) == 0.95 and judge["label"](0.95, 0.95) == "unsure" and judge["label"](0.96, 0.95) == "likely equivalent"
    )
    ok = all(checks.values())
    return {
        "PRODUCER_SYMBOLIC_DIFFERENTIAL": {
            "status": "QUALIFIED" if ok else "NOT QUALIFIED",
            "intended_use": "decide surviving mutants without a model: a symbolic search (CrossHair) over a typed harness, and every proposed input confirmed by execution before it counts",
            "false_green_control": "labelled pairs: every distinct pair's input confirmed, the symbolic search finding and confirming inputs for its distinct pairs and none for its equivalent pairs; witnesses that reach beyond plain values never evaluated; non-finite inputs never counting; a rule mutant rebuilt exactly from its location; an assessor's equivalent only labelling, calibrated and unanimous; an answer's sources found word for word in its own question, one of them on a line the change touches and, for a verdict, one on the requirement it turns on; a shown outcome naming an environment variable without its value and the home directory without its path",
            "control": {"checks": checks, "symbolic": symbolic},
        }
    }


def assessor_ensemble_controls() -> dict[str, dict[str, object]]:
    """Qualify the assessor ensemble by replaying its frozen calibration: the answers belong to stored,
    ledgered calls; the judgement of every pair and the split-conformal threshold recompute to what
    the record holds; and the labelled distinct pairs stay within the Test Plan's rate. No model is called."""
    judge = runpy.run_path(str(ROOT / ".ai-bridge/survivor_equivalence.py"), run_name="evidence_confidence_ensemble")
    models = runpy.run_path(str(ROOT / ".ai-bridge/model_generation.py"), run_name="evidence_confidence_ensemble_models")
    folder = ROOT / ".ai-bridge/semantic-mutants/calibration/equivalence"
    calibration = ROOT / ".ai-bridge/semantic-mutants/assessor-calibration"
    record_path = calibration / "calibration.json"
    base = {
        "intended_use": "label a survivor likely equivalent only when every assessor of the Test Plan, each through one usable model, judges it equivalent above a split-conformal threshold, advisory; distinct only through a confirmed input",
        "false_green_control": "the frozen calibration replayed: every answer bound to a stored, ledgered call; each pair's judgement and the threshold recomputed; the labelled distinct pairs within the Test Plan's false-equivalent rate; the calibration current for the assessors, the question, the pairs and the rate; every observed pair a real survivor the symbolic search left unsure, that a recorded mutation pin proves distinct and the campaign now catches, its answers the triage's own for the question it names",
    }
    if not record_path.exists():
        return {"PRODUCER_ASSESSOR_ENSEMBLE": {**base, "status": "NOT QUALIFIED", "control": {"reason": "the assessors have not been calibrated yet"}}}
    record = json.loads(record_path.read_text())
    plan = (ROOT / "docs/test-plan.md").read_text()
    assessors = models["parse_assessors"](markdown_table(plan, "##### Survivor judgement"))
    settings = models["parse_judgement"](markdown_table(plan, "###### Judgement settings"))
    keys = [row["key"] for row in assessors]
    prompt_sha = hashlib.sha256((judge["ASSESSOR_TEMPLATE"] + "\0" + judge["ASSESSOR_SYSTEM"] + "\0" + json.dumps(judge["ASSESSOR_SCHEMA"], sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
    checks: dict[str, bool] = {}
    checks["the calibration is current for the Test Plan's assessors, the question, the pairs and the rate"] = (
        record.get("members") == keys and record.get("prompt_sha256") == prompt_sha
        and record.get("pairs_sha256") == judge["calibration_sha256"](folder) and record.get("alpha") == settings["alpha"]
        and record.get("complete") is True
    )
    ledger = {row["call_id"]: row for row in models["read_ledger"]()}
    bound = True
    for answers in (record.get("answers") or {}).values():
        for answer in answers.values():
            response_path = calibration / "responses" / f"{answer.get('call_id')}.json"
            response = json.loads(response_path.read_text()) if response_path.exists() else {}
            structured = response.get("structured") or {}
            row = ledger.get(str(answer.get("call_id"))) or {}
            # The answer is its stored response read by the current rule: arguments and problems included.
            bound = bound and bool(response) and not models["verify_response"](response) and (
                models["response_sha256"](response) == answer.get("response_sha256") == row.get("response_sha256")
                and row.get("outcome") == "ok" and structured.get("verdict") == answer.get("verdict")
                and structured.get("confidence") == answer.get("confidence")
                and {key: judge["argument_text"](value) for key, value in (structured.get("arguments") or {}).items()} == answer.get("arguments")
                and judge["answer_problems"](structured, str(response.get("prompt") or "")) == answer.get("problems")
            )
    checks["every calibration answer is a stored, ledgered call's answer"] = bound and bool(record.get("answers"))
    # Each answer is stored under the model and level its call asked for.
    checks["every calibration answer is stored under the model and level its call asked for"] = all(
        models["entry_key"](str(answer.get("backend") or ""), str(answer.get("model") or ""), str((ledger.get(str(answer.get("call_id"))) or {}).get("effort") or "")) == member
        for answers in (record.get("answers") or {}).values() for member, answer in answers.items()
    )
    # Which models may answer for their assessor, recomputed from the answers: every labelled pair
    # answered, and every observed pair the first such models all answered (the record keeps only those).
    payload = judge["calibration_payload"](folder)
    observed = record.get("observed") or {}

    def clean(given):
        return {key: value for key, value in (given or {}).items() if key in keys and not value.get("problems")}

    labelled_complete = {key for key in keys if all(key in clean((record.get("answers") or {}).get(pair["id"])) for pair in payload["pairs"])}
    # Each model's input on a labelled distinct pair is confirmed by execution again; a level of a
    # ladder that misses the calibration floors does not answer, and the first models follow from the rest.
    distinct_pairs = [pair for pair in payload["pairs"] if pair["label"] == "distinct"]
    labelled_answers = {pid: clean(given) for pid, given in (record.get("answers") or {}).items()}
    confirmed_by: dict[str, dict[str, bool]] = {}
    with tempfile.TemporaryDirectory(prefix="ternforge-ensemble-inputs-") as temp_dir:
        for index, pair in enumerate(distinct_pairs):
            original_source, mutant_source = judge["pair_sources"](folder, pair)
            confirmed_by[pair["id"]] = {
                member: judge["judge_survivor"](
                    original_source, mutant_source, pair["target"], scratch=Path(temp_dir), token=f"f{index}m{keys.index(member)}", seconds=0,
                    answers={member: answer}, members=[member], threshold=None, calibrated=False,
                ).get("status") == "found"
                for member, answer in (labelled_answers.get(pair["id"]) or {}).items() if answer.get("verdict") == "distinct"
            }
    observed_answers = record.get("observed_answers") or {pair_id: clean(pair.get("answers")) for pair_id, pair in observed.items()}
    below = models["ladder_below_floors"](assessors, labelled_complete, [pair["id"] for pair in distinct_pairs], labelled_answers, confirmed_by, observed_answers, settings["alpha"])
    eligible = labelled_complete - below
    primary = next(iter(models["assessor_configurations"](assessors, eligible)), [])
    usable = {key for key in eligible if all(key in clean(pair.get("answers")) for pair in observed.values())}
    configurations = models["assessor_configurations"](assessors, usable)
    # The observed answers a ladder's level is judged by are stored, ledgered calls' answers at that level.
    ladder_keys = {row["key"] for row in assessors if row.get("levels")}
    ladder_bound = True
    for pair_id, given in observed_answers.items():
        for member, answer in (given or {}).items():
            if member not in ladder_keys:
                continue
            response_path = ROOT / ".ai-bridge/survivor-triage" / pair_id.split(":", 1)[0] / "responses" / f"{answer.get('call_id')}.json"
            response = json.loads(response_path.read_text()) if response_path.exists() else {}
            row = ledger.get(str(answer.get("call_id"))) or {}
            ladder_bound = ladder_bound and bool(response) and not models["verify_response"](response) and (
                models["response_sha256"](response) == answer.get("response_sha256") == row.get("response_sha256")
                and row.get("outcome") == "ok" and (response.get("structured") or {}).get("verdict") == answer.get("verdict")
                and models["entry_key"](str(response.get("backend") or ""), str(response.get("model") or ""), str(response.get("effort") or "")) == member
            )
    checks["every observed answer a ladder's level is judged by is a stored, ledgered call's answer at that level"] = ladder_bound
    checks["the usable assessor models and every combination of them recompute to the record, one model per assessor"] = (
        bool(configurations) and sorted(usable) == record.get("usable") and sorted(below) == (record.get("below_floors") or [])
        and [row.get("members") for row in record.get("configurations") or []] == configurations
        and all(all(key in clean(pair.get("answers")) for key in primary) for pair in observed.values())
    )
    # The observed pairs: real survivors the symbolic search left unsure and a mutation pin proves distinct (ADR_0006),
    # asked the triage's own question.
    campaign_path = ROOT / "test-results/implementation-faults/campaign.json"
    campaign = json.loads(campaign_path.read_text()) if campaign_path.exists() else {}
    observed_ok = True
    observed_scores = {}
    for pair_id, pair in observed.items():
        contract_id, key = pair.get("contract_id"), pair.get("fingerprint")
        verdicts_path = ROOT / ".ai-bridge/survivor-verdicts" / str(contract_id) / "verdicts.json"
        pin = ((json.loads(verdicts_path.read_text()) if verdicts_path.exists() else {}).get(key) or {}).get("pin") or {}
        report_path = ROOT / str((((campaign.get("contracts") or {}).get(contract_id) or {}).get("run") or {}).get("report_path") or "")
        rows = {str(row.get("fingerprint")): row for row in (json.loads(report_path.read_text()).get("results") or [])} if report_path.is_file() else {}
        caught = str((rows.get(key) or {}).get("status")) in {"zapped", "timeout"}
        for member in sorted(usable):
            answer = (pair.get("answers") or {}).get(member) or {}
            response_path = ROOT / ".ai-bridge/survivor-triage" / str(contract_id) / "responses" / f"{answer.get('call_id')}.json"
            response = json.loads(response_path.read_text()) if response_path.exists() else {}
            row = ledger.get(str(answer.get("call_id"))) or {}
            structured = response.get("structured") or {}
            observed_ok = observed_ok and bool(response) and not models["verify_response"](response) and (
                models["response_sha256"](response) == answer.get("response_sha256") == row.get("response_sha256")
                and row.get("outcome") == "ok" and response.get("prompt_sha256") == pair.get("prompt_sha256")
                and structured.get("verdict") == answer.get("verdict") and structured.get("confidence") == answer.get("confidence")
                and judge["answer_problems"](structured, str(response.get("prompt") or "")) == answer.get("problems") == []
            )
        observed_ok = observed_ok and caught and (pin.get("cascade") or {}).get("accepted") is True and pin.get("path") == pair.get("pin_path")
        # Only what the triage puts to the assessors is exchangeable with its questions.
        observed_ok = observed_ok and (pair.get("symbolic") or {}).get("status") in judge["SEARCH_UNDECIDED"]
        given = clean(pair.get("answers"))
        observed_scores[pair_id] = [judge["ensemble_score"]([given[member] for member in combination], len(combination)) for combination in configurations]
        observed_ok = observed_ok and observed_scores[pair_id] == pair.get("scores") and observed_scores[pair_id][:1] == [pair.get("score")]
    checks["every observed pair is a survivor the symbolic search left unsure and a recorded mutation pin proves distinct, answered by every usable assessor model in stored, ledgered calls"] = observed_ok
    recomputed: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="ternforge-ensemble-qualification-") as temp_dir:
        for pair in payload["pairs"]:
            original_source, mutant_source = judge["pair_sources"](folder, pair)
            given = clean((record.get("answers") or {}).get(pair["id"]))
            judged = [
                judge["judge_survivor"](
                    original_source, mutant_source, pair["target"], scratch=Path(temp_dir), token=f"e{pair['id'].lower()}c{index}", seconds=0,
                    answers={member: given[member] for member in combination if member in given}, members=combination, threshold=None, calibrated=False,
                )
                for index, combination in enumerate(configurations or [primary or keys])
            ]
            scores = [row.get("score", 0.0) if row.get("status") != "found" else 0.0 for row in judged]
            recomputed[pair["id"]] = {"status": judged[0].get("status"), "score": scores[0], "scores": scores}
    stored = record.get("pairs") or {}
    checks["every pair's judgement recomputes to the record, for every combination of usable models"] = all(
        (stored.get(pid) or {}).get("status") == row["status"] and (stored.get(pid) or {}).get("score") == row["score"]
        and (stored.get(pid) or {}).get("scores") == row["scores"]
        for pid, row in recomputed.items()
    )
    # Each combination gets its own split-conformal threshold, and the highest is the one that labels,
    # so a label keeps the Test Plan's rate whichever models answered.
    combinations = []
    for index, combination in enumerate(configurations):
        distinct = [recomputed[pair["id"]]["scores"][index] for pair in payload["pairs"] if pair["label"] == "distinct"] + [scores[index] for scores in observed_scores.values()]
        combination_threshold = judge["conformal_threshold"](distinct, settings["alpha"])
        labelled_here = sum(1 for score in distinct if combination_threshold is not None and score > combination_threshold)
        combinations.append({"members": combination, "threshold": combination_threshold, "distinct": len(distinct), "labelled_distinct": labelled_here})
    thresholds = [row["threshold"] for row in combinations]
    threshold = max(thresholds) if thresholds and None not in thresholds else None
    labelled = sum(row["labelled_distinct"] for row in combinations)
    checks["every combination's threshold recomputes, the highest is the record's, and at most the Test Plan's rate of distinct pairs is labelled"] = (
        threshold == record.get("threshold") and threshold is not None and combinations == record.get("configurations")
        and all(row["labelled_distinct"] <= settings["alpha"] * row["distinct"] for row in combinations)
    )
    # The assessors' canary (ADR_0006): each usable model finds a confirmed input for at least 80% of the labelled distinct
    # pairs, and calls at most the Test Plan's rate of all distinct pairs, labelled or observed, equivalent.
    floors = {
        member: models["calibration_floors"](member, [pair["id"] for pair in distinct_pairs], labelled_answers, confirmed_by, observed_answers, settings["alpha"])
        for member in sorted(usable)
    }
    checks["every usable assessor model meets the calibration floors: inputs for 80% of the labelled distinct pairs, at most the rate of all distinct pairs called equivalent"] = bool(floors) and all(row["met"] for row in floors.values())
    ok = all(checks.values())
    # The record is bound here, not in the shared environment: a calibration run then leaves every other producer current.
    control = {"checks": checks, "threshold": threshold, "labelled_distinct": labelled, "floors": floors, "record_sha256": sha256_file(record_path), "calibration_sha256": assessor_calibration_sha256()}
    return {"PRODUCER_ASSESSOR_ENSEMBLE": {**base, "status": "QUALIFIED" if ok else "NOT QUALIFIED", "control": control}}


def model_canary_controls() -> dict[str, dict[str, object]]:
    """Qualify the model canaries by replaying their records (ADR_0006): every answer a stored,
    ledgered call's by the model its record names; each generator and verdict case recomputed from
    its answer; each draft case bound to the draft its answer makes; and known wrong answers failing.
    A record may pass or fail: the builder skips a model whose record failed or is missing."""
    semantic = runpy.run_path(str(ROOT / ".ai-bridge/semantic_mutants.py"), run_name="evidence_confidence_canaries")
    models = runpy.run_path(str(ROOT / ".ai-bridge/model_generation.py"), run_name="evidence_confidence_canary_models")
    calibration = ROOT / ".ai-bridge/semantic-mutants/calibration"
    results_dir = ROOT / ".ai-bridge/semantic-mutants/canary-results"
    results_path = results_dir / "results.json"
    base = {
        "intended_use": "let a model answer for a role only after it passed that role's canaries, cases with a known outcome, and again after any change of model, question or canary set",
        "false_green_control": "the canary records replayed: answers bound to stored, ledgered calls; generator and verdict cases recomputed; draft cases bound to their drafts and the cascade's verdict; a wrong verdict and an unconfined proposal failing; an unanswered call keeping only the record of the same questions",
    }
    canaries = json.loads((calibration / "canaries.json").read_text())
    results = json.loads(results_path.read_text()) if results_path.exists() else {}
    ledger = {row["call_id"]: row for row in models["read_ledger"]()}
    questions = {role: semantic["canary_questions"](calibration, canaries, role) for role in semantic["CANARY_ROLES"]}
    bound = recomputed = True
    for record in results.values():
        role = record.get("role")
        if record.get("questions_sha256") != semantic["canary_questions_sha256"](questions.get(role) or []):
            continue
        by_id = {question["id"]: question for question in questions.get(role) or []}
        for case_id, case in (record.get("cases") or {}).items():
            question = by_id.get(case_id)
            if case.get("outcome") != "ok" or question is None:
                recomputed = recomputed and not case.get("passed")
                continue
            response_path = results_dir / "responses" / f"{case.get('call_id')}.json"
            response = json.loads(response_path.read_text()) if response_path.exists() else {}
            row = ledger.get(str(case.get("call_id"))) or {}
            bound = bound and bool(response) and not models["verify_response"](response) and (
                models["response_sha256"](response) == case.get("response_sha256") == row.get("response_sha256")
                and row.get("outcome") == "ok" and response.get("model") == record.get("model")
                and str(row.get("effort") or "") == str(record.get("effort") or "")
            )
            structured = response.get("structured") or {}
            if role == "generator":
                passed = semantic["generator_canary_passed"](calibration, question, structured)[0]
            elif role in ("verdict", "verdict_review"):
                passed = semantic["verdict_canary_passed"](question, structured)[0]
            else:
                draft = semantic["draft_from_answer"](question["proposal"]["id"], structured)
                passed = bool((case.get("cascade") or {}).get("accepted")) and case.get("draft_sha256") == hashlib.sha256(draft.encode()).hexdigest()
            recomputed = recomputed and passed == bool(case.get("passed"))
        recomputed = recomputed and bool(record.get("passed")) == all(bool(case.get("passed")) for case in (record.get("cases") or {}).values())
    checks = {
        "every canary answer is a stored, ledgered call's answer, by the model its record names": bound,
        "every canary case recomputes to its record": recomputed,
        "a wrong verdict fails its canary": not semantic["verdict_canary_passed"](questions["verdict"][0], {"verdict": "equivalent", "level": "requirement", "reason": "both are the same", "test_focus": ""})[0],
        "the right verdict fails its canary when a source is not in its question": not semantic["verdict_canary_passed"](
            next(question for question in questions["verdict"] if question["expected"] == "pin"),
            {"verdict": "pin", "level": "requirement", "reason": "as the question shows", "test_focus": "the case", "sources": ["a sentence nobody wrote here"]})[0],
        "an escalation inside a requirement's scope fails its canary": not semantic["verdict_canary_passed"](
            next(question for question in questions["verdict"] if question["expected"] == "escalate"), {"verdict": "escalate", "level": "requirement", "reason": "a product decision", "test_focus": ""})[0],
        "a proposal that imports fails the generator canary": not semantic["generator_canary_passed"](calibration, questions["generator"][0], {"proposals": [{"defect": "d", "replacement": "    def summary(self) -> dict[str, object]:\n        import os\n        return {\"name\": os.sep}"}]})[0],
    }
    # A run whose call went unanswered keeps the record of the same questions, and only of those.
    passed_record = {"questions_sha256": "q", "passed": True, "cases": {"C": {"outcome": "ok", "passed": True}}}
    unanswered = {"questions_sha256": "q", "passed": False, "cases": {"C": {"outcome": "rejected", "passed": False}}}
    answered_wrong = {"questions_sha256": "q", "passed": False, "cases": {"C": {"outcome": "invalid", "passed": False}}}
    judge = runpy.run_path(str(ROOT / ".ai-bridge/survivor_equivalence.py"), run_name="evidence_confidence_review")
    reviewed = judge["reviewed_verdict"]
    answer = {"verdict": "irrelevant", "level": "requirement", "reason": "no requirement asks for it", "test_focus": "", "model": "claude-opus-5-5", "problems": []}
    agree = {"verdict": "equivalent", "level": "requirement", "reason": "the same", "test_focus": "", "model": "gemini-3.1-pro-high", "problems": [], "prompt_sha256": "q"}
    disagree = {**agree, "verdict": "pin", "reason": "the requirement asks for it", "test_focus": "check the total"}
    checks["a suppression counts only when a review of another family agrees, and a disagreeing review pins the mutant"] = (
        (reviewed({"prompt_sha256": "q", "answer": answer, "review": agree}) or {}).get("verdict") == "irrelevant"
        and (reviewed({"prompt_sha256": "q", "answer": answer, "review": disagree}) or {}).get("verdict") == "pin"
        and reviewed({"prompt_sha256": "q", "answer": answer}) is None
        and reviewed({"prompt_sha256": "q", "answer": answer, "review": {**agree, "prompt_sha256": "other"}}) is None
        and (reviewed({"prompt_sha256": "q", "answer": {**answer, "verdict": "pin"}}) or {}).get("verdict") == "pin"
    )
    after = semantic["canary_record_after"]
    checks["an unanswered canary keeps the record of the same questions, never of other questions or over a wrong answer"] = (
        after(passed_record, unanswered) is passed_record
        and after({**passed_record, "questions_sha256": "other"}, unanswered) is unanswered
        and after(None, unanswered) is unanswered
        and after(passed_record, answered_wrong) is answered_wrong
    )
    ok = all(checks.values())
    control = {"checks": checks, "records": {key: bool(record.get("passed")) for key, record in sorted(results.items())}, "results_sha256": sha256_file(results_path) if results_path.exists() else None}
    return {"PRODUCER_MODEL_CANARIES": {**base, "status": "QUALIFIED" if ok else "NOT QUALIFIED", "control": control}}


# The three control groups that run the engine, the cascade and the symbolic search take nearly all
# of a qualification's time. Each is read back when nothing it depends on changed, as a build cache
# reads back an action: its code here with every function of this script it calls, the tool files it
# runs, read by meaning, the locked environment and the Python it runs on.
CONTROL_CACHE = ROOT / "test-results/qualification-controls.json"
CONTROL_INPUTS = {
    "implementation_fault_controls": (".ai-bridge/implementation_faults.py", ".ai-bridge/pytest_plugins/*.py"),
    "semantic_mutant_controls": (
        ".ai-bridge/semantic_mutants.py", ".ai-bridge/survivor_equivalence.py", ".ai-bridge/pytest_plugins/*.py",
        ".ai-bridge/semantic-mutants/calibration/**/*",
    ),
    "survivor_judgement_controls": (".ai-bridge/survivor_equivalence.py", ".ai-bridge/semantic-mutants/calibration/equivalence/**/*"),
    "scenario_mutant_controls": (".ai-bridge/scenario_mutants.py",),
    "architecture_mutant_controls": (".ai-bridge/architecture_mutants.py",),
}


def scenario_mutant_controls() -> dict[str, dict[str, object]]:
    """Qualify the scenario oracle mutants (050) on a small pytest-bdd project whose Then steps check
    strongly, through a helper, weakly and not at all."""
    tool = runpy.run_path(str(ROOT / ".ai-bridge/scenario_mutants.py"), run_name="evidence_confidence_scenario_mutants")
    with tempfile.TemporaryDirectory(prefix="ternforge-scenario-qualification-") as temp_dir:
        tmp = Path(temp_dir)
        for name in ("src", "features", "tests"):
            (tmp / name).mkdir()
        (tmp / "pyproject.toml").write_text('[tool.pytest.ini_options]\nbdd_features_base_dir = "features"\n')
        (tmp / "src" / "classify_control.py").write_text("def classify(value):\n    return 'big' if value > 10 else 'small'\n")
        scenario = "  @{tag}[revision==1]\n  Scenario: {name}\n    Given the value {value}\n    When it is classified\n    Then the class is {outcome}\n\n"
        (tmp / "features" / "control.feature").write_text(
            "Feature: Control\n\n"
            + scenario.format(tag="REQ_STRONG", name="A big value", value=11, outcome="big")
            + scenario.format(tag="REQ_STRONG", name="A small value", value=3, outcome="small")
            + scenario.format(tag="REQ_WEAK", name="A recorded value", value=5, outcome="recorded")
            + scenario.format(tag="REQ_NONE", name="A logged value", value=7, outcome="logged")
        )
        (tmp / "tests" / "test_control.py").write_text(
            "from classify_control import classify\n"
            "from pytest_bdd import given, parsers, scenarios, then, when\n\n"
            "scenarios('control.feature')\n\n\n"
            "def _assert_class(result, expected):\n    assert result == expected\n\n\n"
            "@given(parsers.parse('the value {value:d}'), target_fixture='value')\n"
            "def given_value(value):\n    return value\n\n\n"
            "@when('it is classified', target_fixture='result')\n"
            "def classified(value):\n    return classify(value)\n\n\n"
            "@then('the class is big')\n"
            "def is_big(result):\n    assert result == 'big'\n\n\n"
            "@then('the class is small')\n"
            "def is_small(result):\n    _assert_class(result, 'small')\n\n\n"
            "@then('the class is recorded')\n"
            "def is_recorded(result):\n    assert len(result) >= 0\n\n\n"
            "@then('the class is logged')\n"
            "def is_logged(result):\n    print(result)\n"
        )
        results = tool["run"](tmp, tool["generate"](tmp, ROOT / ".venv/bin/pytest"), ROOT / ".venv/bin/pytest")
    by_function: dict[str, list[str]] = {}
    for row in results:
        by_function.setdefault(row["function"], []).append(row["outcome"])
    contracts = {row["function"]: sorted({item for scenario in row["scenarios"] for item in scenario["contracts"]}) for row in results}
    ok = (
        by_function.get("is_big") == ["caught"]
        and by_function.get("is_small") == ["caught"] and by_function.get("_assert_class") == ["caught"]
        and by_function.get("is_recorded") == ["survived"]
        and by_function.get("is_logged") == ["unchecked"]
        and contracts.get("is_big") == ["REQ_STRONG[revision==1]"] and contracts.get("is_recorded") == ["REQ_WEAK[revision==1]"]
        and "given_value" not in by_function and "classified" not in by_function
    )
    return {
        "PRODUCER_SCENARIO_MUTANTS": {
            "status": "QUALIFIED" if ok else "NOT QUALIFIED",
            "intended_use": "change what one Then step, or an assertion helper it reaches, compares with, run the scenarios that use it and report the mutant caught only when one of them fails, and report a Then step that checks nothing",
            "false_green_control": "a strongly checked step, one checked through a helper and the helper itself must be caught; a weak comparison that holds for another expectation must survive; a step that only prints must be reported as checking nothing; Given and When steps are never mutated; a scenario's contracts come from its tags",
            "control": {"outcomes": by_function, "contracts": contracts},
        }
    }


def architecture_mutant_controls() -> dict[str, dict[str, object]]:
    """Qualify the architecture mutants (050) on a small package with a forbidden-dependency rule and
    the same rule made hollow by an exception for the very edge it forbids."""
    tool = runpy.run_path(str(ROOT / ".ai-bridge/architecture_mutants.py"), run_name="evidence_confidence_architecture_mutants")
    with tempfile.TemporaryDirectory(prefix="ternforge-architecture-qualification-") as temp_dir:
        tmp = Path(temp_dir)
        for name in ("src/app", "src/app/low", "src/app/high"):
            (tmp / name).mkdir(parents=True)
            (tmp / name / "__init__.py").write_text("")
        rule = '[[tool.importlinter.contracts]]\nname = "{name}"\nid = "{id}"\ntype = "forbidden"\nsource_modules = ["app.low"]\nforbidden_modules = ["app.high"]\n{extra}\n'
        (tmp / "pyproject.toml").write_text(
            '[tool.importlinter]\nroot_packages = ["app"]\n\n'
            + rule.format(name="Low must not import high", id="low-not-high", extra="")
            + rule.format(name="Low may import high by exception", id="hollow", extra='ignore_imports = ["app.low -> app.high"]')
        )
        results = tool["run"](tmp, tool["generate"](tmp), ROOT / ".venv/bin/lint-imports")
    outcomes = {row["contract"]: row["outcome"] for row in results}
    ok = outcomes == {"low-not-high": "caught", "hollow": "survived"}
    return {
        "PRODUCER_ARCHITECTURE_MUTANTS": {
            "status": "QUALIFIED" if ok else "NOT QUALIFIED",
            "intended_use": "add one import each import-linter rule forbids to a copy of the code and report the rule caught only when the linter reports that rule broken",
            "false_green_control": "a forbidden-dependency rule must be caught on the edge it forbids, and the same rule whose exception lets that edge in must survive",
            "control": {"outcomes": outcomes},
        }
    }


def control_code_digest(name: str) -> str:
    """A control group's code by meaning, with every function, class and constant of this script it reaches."""
    tree = ast.parse(Path(__file__).read_text())
    definitions: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    definitions[target.id] = node
    seen: set[str] = set()
    queue = [name]
    while queue:
        current = queue.pop()
        if current in seen or current not in definitions:
            continue
        seen.add(current)
        queue.extend(node.id for node in ast.walk(definitions[current]) if isinstance(node, ast.Name))
    return hashlib.sha256("\n".join(ast.dump(definitions[current]) for current in sorted(seen)).encode()).hexdigest()


def cached_controls(controls) -> dict[str, dict[str, object]]:
    """Run a heavy control group, or read back its last result when it qualified and nothing it
    depends on has changed since."""
    name = controls.__name__
    files = sorted({path for pattern in (*CONTROL_INPUTS[name], "pyproject.toml", "uv.lock") for path in ROOT.glob(pattern) if path.is_file() and "__pycache__" not in path.parts})
    key = hashlib.sha256(json.dumps({
        "code": control_code_digest(name),
        "inputs": {str(path.relative_to(ROOT)): FINGERPRINTS["input_digest"](path) for path in files},
        "python": sys.version,
    }, sort_keys=True).encode()).hexdigest()
    cache = json.loads(CONTROL_CACHE.read_text()) if CONTROL_CACHE.exists() else {}
    entry = cache.get(name) or {}
    if entry.get("key") == key and entry.get("producers") and all(row.get("status") == "QUALIFIED" for row in entry["producers"].values()):
        print(f"[QUALIFY] {name}: nothing it depends on changed since {entry.get('ran_at')}, its result read back", flush=True)
        return entry["producers"]
    producers = controls()
    cache[name] = {"key": key, "producers": producers, "ran_at": datetime.now(UTC).isoformat().replace("+00:00", "Z")}
    CONTROL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True, default=str) + "\n")
    return producers


def main() -> None:
    external, details = external_controls()
    internal = internal_controls()
    project_sdk = project_sdk_controls()
    implementation = cached_controls(implementation_fault_controls)
    semantic = cached_controls(semantic_mutant_controls)
    generation = model_generation_controls()
    judgement = cached_controls(survivor_judgement_controls)
    ensemble = assessor_ensemble_controls()
    canaries = model_canary_controls()
    scenario = cached_controls(scenario_mutant_controls)
    architecture = cached_controls(architecture_mutant_controls)
    producers = {
        **external, **internal, **project_sdk, **implementation, **semantic, **generation, **judgement, **ensemble, **canaries,
        **scenario, **architecture,
    }
    payload = {
        "schema": "ternforge-evidence-producer-qualification-1",
        "qualified_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "environment": environment(),
        "policy": "QUALIFIED means the producer passed the retained intended-use false-green control for the exact current tool/code fingerprint; missing or stale qualification is UNKNOWN.",
        "producers": producers,
        "control_run": details,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    bad = [producer_id for producer_id, row in producers.items() if row["status"] != "QUALIFIED"]
    print(f"qualification: {len(producers)-len(bad)}/{len(producers)} producers QUALIFIED")
    for producer_id, row in producers.items():
        print(f"  {producer_id}: {row['status']} — {row['false_green_control']}")
    if bad:
        raise SystemExit("NOT QUALIFIED: " + ", ".join(bad))


if __name__ == "__main__":
    main()
