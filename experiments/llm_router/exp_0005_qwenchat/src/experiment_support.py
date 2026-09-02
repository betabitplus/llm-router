from __future__ import annotations

import re
from pathlib import Path

import pymupdf
from PIL import Image
from pydantic import BaseModel, Field

_INPUTS = Path(__file__).resolve().parent.parent / "inputs"


class PaperMetadata(BaseModel):
    title: str
    title_words: list[str] = Field(min_length=3, max_length=3)


class EvidenceSnippet(BaseModel):
    text: str = Field(min_length=8)
    source: str


class PDFDigest(BaseModel):
    metadata: PaperMetadata
    abstract_one_sentence: str = Field(min_length=20)
    contributions: list[str] = Field(min_length=3, max_length=3)
    evidence: list[EvidenceSnippet] = Field(min_length=2, max_length=2)
    key_entities: list[str] = Field(min_length=4, max_length=4)


class SceneSummary(BaseModel):
    primary_subject: str = Field(min_length=3)
    setting: str = Field(min_length=3)
    visible_objects: list[str] = Field(min_length=3)
    evidence: list[str] = Field(min_length=2)


def get_llm_router_test_data_path(filename: str) -> Path:
    path = _INPUTS / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_test_image(filename: str = "test_image.png") -> Image.Image:
    return Image.open(get_llm_router_test_data_path(filename))


def build_pdf_digest_prompt() -> str:
    return (
        "You are given a PDF file attachment.\n\n"
        "Extract content from the PDF (focus on the paper itself, not file metadata).\n"
        "Return JSON with:\n"
        "- metadata.title: exact paper title from page 1, as a single line\n"
        "- metadata.title_words: exactly 3 distinct words taken from the title, preserving case\n"
        "- abstract_one_sentence: one sentence summarizing the Abstract (<= 25 words)\n"
        "- contributions: exactly 3 short bullet points (<= 12 words each)\n"
        "- evidence: exactly 2 verbatim snippets copied from page 1 (8+ chars).\n"
        "- key_entities: exactly 4 proper nouns or model names that appear on page 1\n\n"
        "Return ONLY valid JSON. No markdown."
    )


def build_scene_summary_prompt() -> str:
    return (
        "Describe the attached image and return JSON.\n\n"
        "Return exactly these keys:\n"
        "- primary_subject: a short phrase naming the main thing shown\n"
        "- setting: a short phrase describing the setting\n"
        "- visible_objects: at least 3 short object names\n"
        "- evidence: at least 2 short phrases grounding the answer in the image\n\n"
        "If the scene is a road, highway, or traffic setting, mention that clearly.\n"
        "Return ONLY valid JSON. No markdown."
    )


def normalize_text_for_match(text: str) -> str:
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = " ".join(text.split())
    return re.sub(r"\s*-\s*", "-", text)


def extract_expected_pdf_facts(pdf_path: Path) -> tuple[str, str]:
    doc = pymupdf.open(str(pdf_path))
    page = doc.load_page(0)
    text = page.get_text("text") or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", ""
    title_lines = lines[1:3] if len(lines) >= 3 else lines[:2]
    return normalize_text_for_match(text), " ".join(title_lines).strip()
