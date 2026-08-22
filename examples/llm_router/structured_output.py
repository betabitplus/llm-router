"""Structured output
=================

Run a real model request and validate the result against a public Pydantic DTO.
"""
# %%

from __future__ import annotations

from pydantic import BaseModel

from llm_router import LLMRouter, Model


class LegalCase(BaseModel):
    """Small public response shape for the example."""

    case_name: str
    court: str
    plaintiffs: list[str]
    defendants: list[str]


def main() -> None:
    """Run the live structured-output example."""
    case_text = (
        "In Smith v. Acme Corp., filed in the United States District Court for "
        "the Northern District of California, plaintiffs Alice Smith and Bob Smith "
        "sued defendants Acme Corp. and Jane Doe for breach of contract."
    )
    router = LLMRouter(Model.GEMINI_FLASH, temperature=0.0, seed=42)
    response = router.query(
        [
            "Extract the legal case details. Return only the requested structure.",
            case_text,
        ],
        response_schema=LegalCase,
    )
    parsed = LegalCase.model_validate_json(response.output_text)
    print(parsed.model_dump_json(indent=2))
    print(f"usage={response.usage}")


# %%
if __name__ == "__main__":
    main()
