"""Enrichment source interface.

An ``EnrichmentSource`` looks up a project in an external EU catalogue and returns a
JSON payload to store. Real sources make HTTP calls; the fake is deterministic.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EnrichmentSource(Protocol):
    name: str

    def enrich(self, *, title: str | None, acronym: str | None) -> dict | None:
        """Return a payload dict for a match, or None if nothing was found."""
        ...
