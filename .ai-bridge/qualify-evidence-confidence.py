from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
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
        "assurance_adapter_sha256": sha256_file(ROOT / ".ai-bridge/build-mutation-report-prototype.py"),
        "requirement_monitor_sha256": sha256_file(ROOT / ".ai-bridge/build-requirement-monitor.py"),
        "upper_assurance_monitor_sha256": sha256_file(ROOT / ".ai-bridge/build-upper-assurance-pilot.py"),
        "assurance_monitor_ui_sha256": sha256_file(ROOT / ".ai-bridge/assurance_monitor_ui.py"),
        "assurance_monitor_domain_sha256": sha256_file(ROOT / ".ai-bridge/assurance_monitor_domain.py"),
        "assurance_monitor_registry_sha256": sha256_file(ROOT / ".ai-bridge/assurance_monitor_registry.py"),
        "qualification_harness_sha256": sha256_file(Path(__file__)),
        "trace_bridge_sha256": sha256_file(ROOT / "tests/conftest.py"),
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
    parser_fail_closed_ok = parser_rejections == [True, True, True, True]

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

    adapter_ok = (
        good == {"coherent": True, "freshness": "CURRENT", "reason": "JUnit and exact Allure result agree and belong to the same retained execution window"}
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
    projection_ok = projection_ok and (
        surrogate_without_target["ms_status"] == "UNKNOWN"
        and surrogate_without_target["ms_applicable_count"] == 1
        and surrogate_l2["ms_status"] == "MET"
        and surrogate_l2["ms_matched"] == 1
        and surrogate_l0["ms_status"] == "NOT MET"
        and surrogate_l0["ms_matched"] == 0
        and surrogate_l2_over_l0["ms_status"] == "MET"
        and surrogate_l2_over_l0["ms_matched"] == 1
    )

    fault_state = domain["fault_state"]
    implementation_group = {
        "label": "Implementation",
        "items": [{"id": "impl.control-flow", "state": "required"}],
    }
    mutation_contract = {
        "fault_actual": {
            "classes": {
                "impl.control-flow": {"exercised": True, "detected": True}
            },
            "groups": {
                "component_local": {
                    "generated": 10,
                    "reached": 10,
                    "killed": 0,
                    "mutation_reach": 100.0,
                    "sensitivity": 0.0,
                }
            },
        },
        "target": {
            "mutation": {
                "component": {"reach": True, "sensitivity": False}
            }
        },
    }
    mutation_policy = {
        "mutation_reach_floor": 80.0,
        "mutation_sensitivity_floor": 80.0,
    }
    reach_only = fault_state(
        mutation_contract,
        implementation_group,
        mutation_policy,
    )
    sensitivity_contract = json.loads(json.dumps(mutation_contract))
    sensitivity_contract["target"]["mutation"]["component"] = {
        "reach": False,
        "sensitivity": True,
    }
    sensitivity_actual = sensitivity_contract["fault_actual"]["groups"][
        "component_local"
    ]
    sensitivity_actual["mutation_reach"] = 0.0
    sensitivity_actual["killed"] = 10
    sensitivity_actual["sensitivity"] = 100.0
    sensitivity_only = fault_state(
        sensitivity_contract,
        implementation_group,
        mutation_policy,
    )
    missing_threshold_policy = dict(mutation_policy)
    missing_threshold_policy["mutation_reach_floor"] = None
    missing_threshold = fault_state(
        mutation_contract,
        implementation_group,
        missing_threshold_policy,
    )
    projection_ok = projection_ok and (
        reach_only["status"] == "MET"
        and reach_only["mutation"][0]["reach_selected"] is True
        and reach_only["mutation"][0]["sensitivity_selected"] is False
        and sensitivity_only["status"] == "MET"
        and sensitivity_only["mutation"][0]["reach_selected"] is False
        and sensitivity_only["mutation"][0]["sensitivity_selected"] is True
        and missing_threshold["status"] == "UNKNOWN"
    )

    upper_criterion_state = upper["criterion_state"]
    upper_profile = ROOT / "docs/assurance-profiles/routing.md"
    upper_test_source = ROOT / "tests/conftest.py"
    upper_target = {
        "id": "ASSURANCE_CONTROL",
        "method": "pytest-bdd",
        "boundary": "Substitute",
        "required_executions": 1,
    }
    upper_source_sha = sha256_file(upper_test_source)
    upper_profile_sha = sha256_file(upper_profile)
    upper_row = {
        "result": "passed",
        "source_path": str(upper_test_source.relative_to(ROOT)),
        "source_sha256": upper_source_sha,
    }
    upper_run_inputs = {
        "inputs": {
            str(upper_profile.relative_to(ROOT)): upper_profile_sha,
            str(upper_test_source.relative_to(ROOT)): upper_source_sha,
        }
    }
    upper_producer_ids = (
        "PRODUCER_PYTEST",
        "PRODUCER_PY_TESTKIT",
        "PRODUCER_UPPER_ASSURANCE_MONITOR",
        "PRODUCER_PYTEST_BDD",
        "PRODUCER_SCRIPTED_HTTP_SERVER",
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
    upper_projection_ok = (
        upper_good["status"] == "MET"
        and upper_good["execution_status"] == "MET"
        and upper_good["producer_qualification"]["status"] == "MET"
        and upper_good["freshness"]["status"] == "MET"
        and upper_missing_execution["status"] == "NOT MET"
        and upper_unknown_producer["status"] == "UNKNOWN"
        and upper_bad_producer["status"] == "NOT MET"
        and upper_stale_source["status"] == "NOT MET"
        and upper_missing_profile["status"] == "UNKNOWN"
    )

    return {
        "PRODUCER_ASSURANCE_ADAPTER": {
            "status": "QUALIFIED" if adapter_ok else "NOT QUALIFIED",
            "intended_use": "join retained execution artifacts without accepting mismatched status or stale run membership",
            "false_green_control": "status disagreement, out-of-run timestamps, stale/missing Requirement revision pins, and stale specialized fault-probe bindings must be rejected while coherent current evidence remains current",
        },
        "PRODUCER_REQUIREMENT_MONITOR": {
            "status": "QUALIFIED" if projection_ok else "NOT QUALIFIED",
            "intended_use": "project Target versus Actual without converting missing or failed confidence evidence into green status",
            "false_green_control": "UNKNOWN, NOT QUALIFIED, partial-scope trust, exact-cardinality violations, under-validated surrogate paths, and unselected or threshold-less mutation checks must never become a false PASS",
        },
        "PRODUCER_UPPER_ASSURANCE_MONITOR": {
            "status": "QUALIFIED" if upper_projection_ok else "NOT QUALIFIED",
            "intended_use": "project Feature, Goal, and Product/System assurance from child status plus explicitly declared cross-contract and validation criteria",
            "false_green_control": "missing execution, UNKNOWN or NOT QUALIFIED producers, stale test source, or missing/stale Assurance Profile provenance must never become a false PASS",
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


def main() -> None:
    external, details = external_controls()
    internal = internal_controls()
    project_sdk = project_sdk_controls()
    producers = {**external, **internal, **project_sdk}
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
