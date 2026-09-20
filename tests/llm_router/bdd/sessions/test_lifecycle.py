"""Bindings for session lifecycle BDD scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pytest_bdd import given, scenarios, then, when

from llm_router import FileSchema, Session, VideoSchema, VideoUrlSchema
from tests.llm_router.support.workers.concurrency_isolation import (
    run_concurrency_isolation_inprocess,
)

scenarios("sessions/lifecycle.feature")

for _test_name, _criterion in (
    (
        "test_remembered_turns_are_included_in_later_messages",
        "VC_SESSION_HISTORY_INCLUDED",
    ),
    (
        "test_history_can_be_ignored_for_one_request",
        "VC_SESSION_HISTORY_SUPPRESSED",
    ),
    (
        "test_a_fork_starts_with_the_same_history_and_then_changes_independently",
        "VC_SESSION_FORK_ISOLATION",
    ),
    (
        "test_saving_and_loading_preserves_the_session",
        "VC_SESSION_PUBLIC_PERSISTENCE",
    ),
    (
        "test_clearing_a_session_removes_history_but_keeps_it_reusable",
        "VC_SESSION_CLEAR_REUSE",
    ),
    (
        "test_concurrent_requests_keep_their_session_state_separate",
        "VC_SESSION_CONCURRENT_ISOLATION",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])
del _criterion, _test_name

for _test_name, _path_id in (
    ("test_saving_and_loading_preserves_an_embedded_file", "file"),
    ("test_saving_and_loading_preserves_an_embedded_image", "image"),
    ("test_saving_and_loading_preserves_an_embedded_local_video", "local-video"),
    (
        "test_saving_and_loading_preserves_a_remote_video_descriptor",
        "remote-video",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(
        "VC_SESSION_PUBLIC_MEDIA_PERSISTENCE"
    )(globals()[_test_name])
    globals()[_test_name] = pytest.mark.coverage_path(_path_id)(globals()[_test_name])
del _path_id, _test_name


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


@given("a session contains an embedded file", target_fixture="case")
def embedded_file(tmp_path: Path) -> dict[str, Any]:
    path = tmp_path / "input.bin"
    path.write_bytes(b"public-file-bytes")
    session = Session(system="system")
    session.remember(
        user_content=(
            FileSchema(path=str(path), mime_type="application/octet-stream"),
        ),
        assistant_text="stored",
    )
    return {"session": session}


@given("a session contains an embedded image", target_fixture="case")
def embedded_image() -> dict[str, Any]:
    image = Image.new("RGBA", (3, 2), (12, 34, 56, 78))
    session = Session(system="system")
    session.remember(user_content=(image,), assistant_text="stored")
    return {"session": session}


@given("a session contains an embedded local video", target_fixture="case")
def embedded_local_video(tmp_path: Path) -> dict[str, Any]:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"public-video-bytes")
    session = Session(system="system")
    session.remember(
        user_content=(
            VideoSchema(path=str(path), fps=2, start_offset=1, end_offset=5),
        ),
        assistant_text="stored",
    )
    return {"session": session}


@given("a session contains a remote video descriptor", target_fixture="case")
def remote_video_descriptor() -> dict[str, Any]:
    session = Session(system="system")
    session.remember(
        user_content=(
            VideoUrlSchema(
                url="https://video.example/clip.mp4",
                fps=3,
                start_offset=2,
                end_offset=8,
            ),
        ),
        assistant_text="stored",
    )
    return {"session": session}


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


@then("the embedded file is preserved")
def embedded_file_is_preserved(case: dict[str, Any]) -> None:
    part = case["loaded"].history[0].parts[0]
    assert Path(part.path).read_bytes() == b"public-file-bytes"
    assert part.mime_type == "application/octet-stream"


@then("the embedded image is preserved")
def embedded_image_is_preserved(case: dict[str, Any]) -> None:
    part = case["loaded"].history[0].parts[0]
    assert isinstance(part, Image.Image)
    assert part.mode == "RGBA"
    assert part.size == (3, 2)
    assert part.getpixel((0, 0)) == (12, 34, 56, 78)


@then("the embedded local video is preserved")
def embedded_local_video_is_preserved(case: dict[str, Any]) -> None:
    part = case["loaded"].history[0].parts[0]
    assert Path(part.path).read_bytes() == b"public-video-bytes"
    assert (part.fps, part.start_offset, part.end_offset) == (2, 1, 5)


@then("the remote video descriptor is preserved")
def remote_video_descriptor_is_preserved(case: dict[str, Any]) -> None:
    part = case["loaded"].history[0].parts[0]
    assert part.url == "https://video.example/clip.mp4"
    assert (part.fps, part.start_offset, part.end_offset) == (3, 2, 8)


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
