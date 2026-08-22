"""Persistent and forked sessions
==============================

Persist a real conversation, restore it, fork it, and let the two branches diverge.
"""
# %%

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from llm_router import LLMRouter, Model, Provider, RouterProfile, Session


def build_router(session: Session) -> LLMRouter:
    """Build one live router bound to a session."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        session=session,
        temperature=0.0,
        seed=42,
    )


def main() -> None:
    """Run the live persistence and branching flow."""
    with TemporaryDirectory(prefix="llm-router-session-") as temp_dir:
        output_dir = Path(temp_dir)
        saved_path = output_dir / "session.json"
        original_path = output_dir / "session-original.json"
        branch_path = output_dir / "session-branch.json"

        session = Session(system="Follow instructions exactly.")
        router = build_router(session)
        first = router.query("Secret code for this chat: 81723. Reply only OK.")
        print(first.output_text)
        session.save(saved_path)

        restored = Session.load(saved_path)
        branch = restored.fork()
        restored_router = build_router(restored)
        branch_router = build_router(branch)

        updated = restored_router.query(
            "Update the secret code to 12345. Reply only OK."
        )
        print(updated.output_text)
        original = restored_router.query("What is the secret code? Reply only digits.")
        branched = branch_router.query("What is the secret code? Reply only digits.")

        restored.save(original_path)
        branch.save(branch_path)

        print(
            f"original={original.output_text.strip()} history={len(restored.history)}"
        )
        print(f"branch={branched.output_text.strip()} history={len(branch.history)}")
        print(f"saved={original_path}")
        print(f"saved={branch_path}")


# %%
if __name__ == "__main__":
    main()
