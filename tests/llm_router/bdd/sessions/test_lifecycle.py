"""Bindings for session lifecycle BDD scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pytest_bdd import given, scenarios, then, when

from llm_router import Session
from tests.llm_router.support.workers.concurrency_isolation import (
    run_concurrency_isolation_inprocess,
)

scenarios("sessions/lifecycle.feature")


def _session() -> Session:
    session = Session(system="system")
    session.remember(user_content="hello", assistant_text="answer")
    return session


@given("a session contains previous conversation turns", target_fixture="case")
def previous_conversation() -> dict[str, Any]:
    return {"session": _session()}


@given("a session contains conversation history", target_fixture="case")
def conversation_history() -> dict[str, Any]:
    return {"session": _session()}


@when("a new message is built with history")
def build_with_history(case: dict[str, Any]) -> None:
    case["messages"] = case["session"].build_messages("next")


@then("the previous turns appear before the new message")
def history_precedes_new_message(case: dict[str, Any]) -> None:
    assert case["messages"] == [
        "system",
        "User: hello",
        "Assistant: answer",
        "User: next",
    ]


@when("a new message is built without history")
def build_without_history(case: dict[str, Any]) -> None:
    case["messages"] = case["session"].build_messages("next", include_history=False)


@then("only the current message and system instruction are used")
def history_is_excluded(case: dict[str, Any]) -> None:
    assert case["messages"] == ["system", "User: next"]


@when("the session is forked and the fork receives another turn")
def fork_and_extend_session(case: dict[str, Any]) -> None:
    case["fork"] = case["session"].fork()
    case["fork"].remember(user_content="branch", assistant_text="branch answer")


@then("the original session remains unchanged")
def original_is_unchanged(case: dict[str, Any]) -> None:
    assert len(case["session"].history) == 2
    assert len(case["fork"].history) == 4
    assert case["session"].history != case["fork"].history


@when("it is saved and loaded")
def save_and_load(case: dict[str, Any], tmp_path: Path) -> None:
    path = case["session"].save(tmp_path / "session.json")
    case["loaded"] = Session.load(path)


@then("its conversation state is preserved")
def persisted_state_is_preserved(case: dict[str, Any]) -> None:
    assert case["loaded"].system == case["session"].system
    assert case["loaded"].history == case["session"].history


@when("the session is cleared")
def clear_session(case: dict[str, Any]) -> None:
    case["session"].clear()


@then("its history is empty")
def history_is_empty(case: dict[str, Any]) -> None:
    assert case["session"].history == ()


@then("new turns can still be added")
def cleared_session_is_reusable(case: dict[str, Any]) -> None:
    case["session"].remember(user_content="new", assistant_text="fresh")
    assert len(case["session"].history) == 2


@given("two independent sessions execute concurrently", target_fixture="case")
def concurrent_sessions() -> dict[str, Any]:
    return {}


@when("both requests complete")
def complete_concurrent_requests(case: dict[str, Any]) -> None:
    case["result"] = run_concurrency_isolation_inprocess()


@then("each session contains only its own conversation")
def concurrent_session_state_is_isolated(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    assert result.alpha_text == "ALPHA"
    assert result.beta_text == "BETA"
    assert result.alpha_history_length == result.beta_history_length == 2
    assert result.alpha_user_parts == ["Reply only ALPHA."]
    assert result.beta_user_parts == ["Reply only BETA."]


@then("each request keeps its own routing result")
def concurrent_routing_state_is_isolated(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.request_count == 2
    assert len(result.alpha_routing_trace) == len(result.beta_routing_trace) == 1
    assert result.alpha_routing_trace[0]["error_type"] is None
    assert result.beta_routing_trace[0]["error_type"] is None
