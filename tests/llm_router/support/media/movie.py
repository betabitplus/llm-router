"""llm_router-specific movie scenario helpers.

Why:
    Reuses one structured movie-record contract across sync and async AI Studio
    tests so those e2e files stay small and comparable.

When to use:
    Import from here when a scenario requests structured movie metadata for the
    film *Inception*.

How:
    Use `MovieRecord`, `build_movie_prompt()`, and
    `assert_movie_record_response(...)` rather than redefining the same schema
    and assertions in each file.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from llm_router import LLMRouterResponse
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    parse_json_object,
)


class Actor(BaseModel):
    """Structured cast member entry."""

    name: str
    character_name: str


class Review(BaseModel):
    """Short review entry."""

    source: str
    rating: float = Field(description="Rating out of 10")


class MovieRecord(BaseModel):
    """Structured movie record used by the AI Studio text scenario."""

    movie_title: str
    director: str
    cast: list[Actor] = Field(min_length=3)
    reviews: list[Review] = Field(min_length=2)
    tagline: str


def build_movie_prompt() -> str:
    """Build the shared movie-record prompt."""
    return (
        "Generate a database entry for the 2010 movie Inception.\n\n"
        "Return JSON with:\n"
        "- movie_title\n"
        "- director\n"
        "- cast: at least 3 actors with `name` and `character_name`\n"
        "- reviews: at least 2 entries with `source` and numeric `rating`\n"
        "- tagline\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def assert_movie_record_response(response: LLMRouterResponse) -> MovieRecord:
    """Assert coarse invariants for the Inception movie-record scenario."""
    assert_output_text_not_empty(response)
    parsed = MovieRecord.model_validate(parse_json_object(response.output_text))

    assert parsed.movie_title == "Inception"
    assert "nolan" in parsed.director.lower()
    assert parsed.tagline.strip()
    assert len(parsed.cast) >= 3
    assert len(parsed.reviews) >= 2
    return parsed
