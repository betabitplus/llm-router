"""Bindings for upper-level session continuity assurance scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, Model, Provider, RouterProfile, Session
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("sessions/assurance.feature")

for _test_name, _criterion in (
    (
        "test_a_persisted_fork_keeps_branch_state_without_changing_its_source",
        "AC_SESSION_FORK_PERSISTENCE_ISOLATION",
    ),
    (
        "test_a_restored_session_continues_independently_from_its_sibling",
        "AOV_SESSION_RESTORED_CONTINUITY",
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(
        "REQ_SESSION_LIFECYCLE[revision==1]",
        "REQ_SESSION_PERSISTENCE[revision==1]",
    )(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _criterion, _test_name

_OPENAI_PATH = openai_chat_path()


def _seeded_session() -> Session:
    session = Session(system="Keep conversation context explicit.")
    session.remember(
        user_content="remembered question",
        assistant_text="remembered answer",
    )
    return session


@given("a session contains a remembered source turn", target_fixture="integration_case")
def remembered_source_turn() -> dict[str, Any]:
    source = _seeded_session()
    return {"source": source, "source_history": source.history}


@when("a fork is extended, persisted, and restored")
def persist_extended_fork(integration_case: dict[str, Any], tmp_path: Path) -> None:
    forked = integration_case["source"].fork()
    forked.remember(user_content="branch question", assistant_text="branch answer")
    path = forked.save(tmp_path / "branch-session.json")
    integration_case["restored"] = Session.load(path)


@then("the source session remains unchanged")
def source_session_is_unchanged(integration_case: dict[str, Any]) -> None:
    source = integration_case["source"]
    assert source.history == integration_case["source_history"]
    assert len(source.history) == 2


@then("the restored branch contains the source and branch turns")
def restored_branch_contains_both_turns(integration_case: dict[str, Any]) -> None:
    restored = integration_case["restored"]
    assert restored.build_messages("next") == [
        "Keep conversation context explicit.",
        "User: remembered question",
        "Assistant: remembered answer",
        "User: branch question",
        "Assistant: branch answer",
        "User: next",
    ]


@given(
    "a persisted session and an independent sibling session",
    target_fixture="outcome_case",
)
def persisted_and_sibling_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY", "session-assurance-key")
    persisted = _seeded_session()
    restored = Session.load(persisted.save(tmp_path / "restored-session.json"))
    sibling = Session(system="Sibling context.")
    sibling.remember(user_content="sibling question", assistant_text="sibling answer")
    return {
        "restored": restored,
        "sibling": sibling,
        "sibling_history": sibling.history,
        "restored_history_before": restored.history,
    }


@when("the restored session continues through the public router")
def restored_session_continues(outcome_case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="continued answer"),
                )
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            router = LLMRouter(
                RouterProfile(
                    provider=Provider.OPENROUTER,
                    model=Model.DEEPSEEK_V3,
                ),
                session=outcome_case["restored"],
                temperature=0.0,
            )
            outcome_case["response"] = router.query("follow-up question")
        requests = server.recorded_requests("POST", _OPENAI_PATH)
        assert len(requests) == 1
        outcome_case["payload"] = json.loads(requests[0].body.decode("utf-8"))
        server.retain_current_boundary_evidence()


@then("the provider receives the restored history before the new message")
def provider_receives_restored_history(outcome_case: dict[str, Any]) -> None:
    payload_text = json.dumps(outcome_case["payload"]["messages"])
    assert "remembered question" in payload_text
    assert "remembered answer" in payload_text
    assert "follow-up question" in payload_text
    assert payload_text.index("remembered question") < payload_text.index(
        "follow-up question"
    )
    assert payload_text.index("remembered answer") < payload_text.index(
        "follow-up question"
    )


@then("only the restored session remembers the provider response")
def only_restored_session_changes(outcome_case: dict[str, Any]) -> None:
    restored = outcome_case["restored"]
    sibling = outcome_case["sibling"]
    assert outcome_case["response"].output_text == "continued answer"
    assert len(restored.history) == len(outcome_case["restored_history_before"]) + 2
    assert restored.history[-1].role == "assistant"
    assert restored.history[-1].parts == ("continued answer",)
    assert sibling.history == outcome_case["sibling_history"]
