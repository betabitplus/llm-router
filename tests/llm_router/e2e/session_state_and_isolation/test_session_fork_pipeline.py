# %%
"""LLM Router e2e: session fork and divergent history.

Why:
    Verifies that session forking works correctly with the QwenChat
    provider.

Covers:
    Area: QwenChat session flow
    Behavior: `Session.fork()`, branching behavior
    Interface: `LLMRouter(..., session=...)`, `query(...)`

Checks:
    If the original branch continues after the fork, then it recalls `12345`.
    If the fork remains isolated from later writes, then it recalls `81723`.
    If branch divergence is preserved, then the original history length is `6` and the
    fork history length is `4`.
    If later writes stay isolated to the original branch, then the original user history
    contains the update prompt and the forked history does not.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.session_state_and_isolation.test_session_fork_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/session_state_and_isolation/test_session_fork_pipeline.py
"""

from __future__ import annotations

from pathlib import Path

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
    Session,
)
from tests.llm_router.support.builders import build_output_path

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_session,
]


# =============================================================================
# Scenario
# =============================================================================

_BRANCH_OUTPUT_FILENAME = "_chat_session_fork_qwenchat_branch.json"
_ORIGINAL_OUTPUT_FILENAME = "_chat_session_fork_qwenchat_original.json"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_ASK_REMEMBER = "Remember this secret code exactly: 81723. Reply only OK."
_ASK_UPDATE = "Update the secret code to 12345. Reply only OK."
_ASK_RECALL = "What is the secret code? Reply only digits, no punctuation or words."
# The prompts are deliberately tiny so the interesting part is branch divergence,
# not generation quality.


# =============================================================================
# Helpers
# =============================================================================


def build_output_paths() -> tuple[Path, Path]:
    """Build the demo output paths."""
    return (
        build_output_path(_ORIGINAL_OUTPUT_FILENAME),
        build_output_path(_BRANCH_OUTPUT_FILENAME),
    )


# =============================================================================
# Pipeline
# =============================================================================


def build_router(*, session: Session) -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        session=session,
        limits_by_provider={
            # This scenario tests session fork semantics, not rate limiting.
            # Disable waits so VCR replay stays fast.
            Provider.QWENCHAT: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            ),
        },
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> tuple[Session, Session, str, str]:
    """Fork after turn one, diverge, and compare results."""
    session = Session(system=_SYSTEM_PROMPT)
    router = build_router(session=session)

    # Turn 1 establishes the shared history that both branches should inherit.
    first_response = router.query(_ASK_REMEMBER)
    assert first_response.data is not None

    # Fork immediately after turn 1 so the branch starts from the same memory.
    forked_session = session.fork()
    fork_router = build_router(session=forked_session)

    # Update only the original branch to create divergence.
    second_response = router.query(_ASK_UPDATE)
    assert second_response.data is not None

    # Now ask both branches the same recall question.
    original = router.query(_ASK_RECALL)
    assert original.data is not None

    branched = fork_router.query(_ASK_RECALL)
    assert branched.data is not None

    return (
        session,
        forked_session,
        original.data.choices[0].message.content.strip(),
        branched.data.choices[0].message.content.strip(),
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(
    session: Session,
    forked_session: Session,
    original_text: str,
    branched_text: str,
) -> None:
    """Assert the forked-session behavior."""
    # The original branch should remember the updated value.
    assert original_text == "12345"
    # The fork should keep the old value, which proves true divergence.
    assert branched_text == "81723"
    # History lengths make the divergence concrete: the original branch kept an
    # extra turn, while the fork stayed shorter.
    assert len(session.history) == 6
    assert len(forked_session.history) == 4

    original_user_text = "\n".join(
        str(part)
        for message in session.history
        if message.role == "user"
        for part in message.parts
        if isinstance(part, str)
    )
    forked_user_text = "\n".join(
        str(part)
        for message in forked_session.history
        if message.role == "user"
        for part in message.parts
        if isinstance(part, str)
    )
    assert _ASK_UPDATE in original_user_text
    assert _ASK_UPDATE not in forked_user_text


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify session forking preserves branch-local state."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the fork-and-diverge conversation.
    session, forked_session, original_text, branched_text = run_pipeline()
    # Then prove the two branches remember different values.
    assert_pipeline_response(session, forked_session, original_text, branched_text)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)

    # Run the same fork-and-diverge flow the test asserts.
    session, forked_session, original_text, branched_text = run_pipeline()

    console.demo_step(
        "What Happened",
        "We forked one conversation into a branch, and both sessions "
        "then continued independently.",
        details=[
            f"Original answer: {original_text} (history={len(session.history)})",
            f"Fork answer: {branched_text} (history={len(forked_session.history)})",
        ],
    )

    # Persist both branches so the divergence is visible on disk too.
    original_path, branch_path = build_output_paths()
    session.save(original_path)
    forked_session.save(branch_path)

    console.demo_step(
        "Saved Session Evidence",
        "Both session snapshots were saved so you can see that the "
        "histories diverged cleanly after the fork.",
        details=[
            f"Original session JSON: {original_path.read_text(encoding='utf-8')}",
            f"Branch session JSON: {branch_path.read_text(encoding='utf-8')}",
        ],
    )
    console.demo_outcome(
        "This passed because the branch kept its own timeline instead "
        "of overwriting or contaminating the original session."
    )


if __name__ == "__main__":
    main()
# %%
