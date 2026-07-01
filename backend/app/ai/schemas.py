"""Structured result of AI proposal extraction.

These Pydantic models define the schema the LLM must fill (via tool-use) and that the
pipeline validates before persisting. Every extraction carries a confidence score, and
partners record the source page where they were found (provenance).
"""

from datetime import date

from pydantic import BaseModel, Field


class ExtractedPartner(BaseModel):
    legal_name: str
    country: str | None = None
    role: str | None = Field(default=None, description="coordinator | partner")
    pic_number: str | None = None
    org_type: str | None = Field(default=None, description="NGO, university, SME, public…")
    source_page: int | None = None


class ExtractedProject(BaseModel):
    title: str | None = None
    acronym: str | None = None
    programme: str | None = Field(default=None, description="Erasmus+, Horizon Europe…")
    call_identifier: str | None = None
    summary: str | None = None
    total_budget: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_months: int | None = None
    partners: list[ExtractedPartner] = Field(default_factory=list)
    # Overall extraction confidence, 0..1.
    confidence: float = 0.0
