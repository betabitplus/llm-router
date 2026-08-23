"""Persist and fork a conversation
===============================

Save one live session, restore it, fork it, and then prove that the two histories
can diverge without sharing later messages.
"""
# sphinx_gallery_tags = ["sessions", "persistence", "routing"]
# sphinx_gallery_thumbnail_path = "_static/gallery/sessions.svg"

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from llm_router import LLMRouter, Model, Provider, RouterProfile, Session


def build_router(session: Session) -> LLMRouter:
    """Build a router bound to one session."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        session=session,
        temperature=0.0,
        seed=42,
    )


# %%
# Create and persist history
# --------------------------
# A ``Session`` records the conversation used by the router. ``save()`` writes that
# public history format; no router internals need to be serialized.
def save_initial_session(path: Path) -> None:
    """Create one live conversation and persist it to ``path``."""
    session = Session(system="Follow instructions exactly.")
    router = build_router(session)
    router.query("Secret code for this chat: 81723. Reply only OK.")
    session.save(path)


# %%
# Restore once, then fork
# -----------------------
# ``load()`` reconstructs the saved history and ``fork()`` copies it. Updating the
# restored branch after the fork must not change the forked branch.
def restore_and_fork(path: Path) -> tuple[Session, Session]:
    """Restore a saved session, fork it, and update only one branch."""
    restored = Session.load(path)
    forked = restored.fork()
    restored_router = build_router(restored)
    restored_router.query("Update the secret code to 12345. Reply only OK.")
    return restored, forked


# %%
# Verify that the histories diverged
# ----------------------------------
# Ask the same question on both branches. The outputs make the persistence and
# isolation behavior visible without dumping the full message history.
if __name__ == "__main__":
    with TemporaryDirectory(prefix="llm-router-session-") as temp_dir:
        saved_path = Path(temp_dir) / "session.json"
        save_initial_session(saved_path)
        restored, forked = restore_and_fork(saved_path)

        restored_answer = build_router(restored).query(
            "What is the secret code? Reply only digits."
        )
        forked_answer = build_router(forked).query(
            "What is the secret code? Reply only digits."
        )

        print(f"restored code: {restored_answer.output_text.strip()}")
        print(f"forked code:   {forked_answer.output_text.strip()}")
        print(
            f"history messages: restored={len(restored.history)} "
            f"forked={len(forked.history)}"
        )

# %%
# The restored branch sees the updated code while the fork keeps the pre-fork value,
# demonstrating that later conversation state is isolated between branches.
