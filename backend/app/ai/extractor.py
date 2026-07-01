"""LLM extraction behind a swappable interface.

``AnthropicExtractor`` uses Claude structured tool-use to fill the extraction schema.
``FakeExtractor`` is deterministic and needs no API key — used by tests and as a safe
fallback when ``ANTHROPIC_API_KEY`` is unset, so the pipeline always runs.
"""

import json
import re
from typing import Protocol

from app.ai.schemas import ExtractedPartner, ExtractedProject
from app.core.config import settings

EXTRACTION_PROMPT = (
    "You are analysing a European project proposal. Extract the project metadata and "
    "the list of partner organizations. Use the provided tool to return structured "
    "data. If a field is not present, omit it. For each partner, record the page "
    "number where you found it. Give an overall confidence between 0 and 1."
)

# JSON schema handed to Claude as a tool. Mirrors app.ai.schemas.ExtractedProject.
EXTRACTION_TOOL = {
    "name": "record_project",
    "description": "Record the structured project proposal data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "acronym": {"type": "string"},
            "programme": {"type": "string"},
            "call_identifier": {"type": "string"},
            "summary": {"type": "string"},
            "total_budget": {"type": "number"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            "duration_months": {"type": "integer"},
            "partners": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "legal_name": {"type": "string"},
                        "country": {"type": "string"},
                        "role": {"type": "string"},
                        "pic_number": {"type": "string"},
                        "org_type": {"type": "string"},
                        "source_page": {"type": "integer"},
                    },
                    "required": ["legal_name"],
                },
            },
            "confidence": {"type": "number"},
        },
    },
}


class Extractor(Protocol):
    def extract(self, text: str) -> ExtractedProject: ...


class AnthropicExtractor:
    """Real extractor using the Anthropic Messages API with forced tool-use."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.anthropic_extraction_model

    def extract(self, text: str) -> ExtractedProject:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=EXTRACTION_PROMPT,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "record_project"},
            messages=[{"role": "user", "content": text[:120_000]}],
        )
        for block in message.content:
            if block.type == "tool_use":
                return ExtractedProject.model_validate(block.input)
        raise ValueError("Model did not return the expected tool call")


class FakeExtractor:
    """Deterministic extractor for tests / no-key operation.

    Pulls light signals from the text (acronym-like tokens, partner cues) so results
    vary with input but are fully reproducible.
    """

    def extract(self, text: str) -> ExtractedProject:
        acronym = None
        m = re.search(r"\b([A-Z]{3,20})\b", text)
        if m:
            acronym = m.group(1)

        partners: list[ExtractedPartner] = []
        for i, line in enumerate(text.splitlines()):
            low = line.lower()
            if "coordinator" in low or "partner" in low:
                name = line.strip()[:120] or f"Organization {i}"
                role = "coordinator" if "coordinator" in low else "partner"
                partners.append(
                    ExtractedPartner(legal_name=name, role=role, source_page=1)
                )

        title = None
        for line in text.splitlines():
            if line.strip():
                title = line.strip()[:200]
                break

        return ExtractedProject(
            title=title,
            acronym=acronym,
            summary=(text.strip()[:500] or None),
            partners=partners[:20],
            confidence=0.5 if text.strip() else 0.0,
        )


def get_extractor() -> Extractor:
    """Return the real extractor when a key is configured, else the fake."""
    if settings.anthropic_api_key and settings.anthropic_api_key not in {"", "x"}:
        return AnthropicExtractor()
    return FakeExtractor()


def dump_project(project: ExtractedProject) -> str:
    """Serialize an extraction for storage/debug."""
    return json.dumps(project.model_dump(mode="json"), default=str)
