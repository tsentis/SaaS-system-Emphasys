"""Concrete enrichment sources.

``CordisSource`` and ``FtPortalSource`` make best-effort HTTP calls to public EU
endpoints and fail soft (return None) so a network hiccup never breaks a request.
``FakeSource`` is deterministic for tests / offline operation.
"""


class FakeSource:
    def __init__(self, name: str = "fake") -> None:
        self.name = name

    def enrich(self, *, title: str | None, acronym: str | None) -> dict | None:
        query = acronym or title
        if not query:
            return None
        return {
            "source": self.name,
            "matched": True,
            "query": {"title": title, "acronym": acronym},
            "records": [{"id": f"{self.name.upper()}-0001", "title": query}],
        }


class CordisSource:
    name = "cordis"
    BASE_URL = "https://cordis.europa.eu/search/api/rest/v1/results"

    def enrich(self, *, title: str | None, acronym: str | None) -> dict | None:
        query = acronym or title
        if not query:
            return None
        try:
            import httpx

            resp = httpx.get(
                self.BASE_URL,
                params={"q": query, "format": "json", "num": 5},
                timeout=15.0,
            )
            resp.raise_for_status()
            return {"source": self.name, "matched": True, "data": resp.json()}
        except Exception:  # noqa: BLE001 — fail soft; caller stores nothing
            return None


class FtPortalSource:
    name = "ft_portal"
    BASE_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"

    def enrich(self, *, title: str | None, acronym: str | None) -> dict | None:
        query = acronym or title
        if not query:
            return None
        try:
            import httpx

            resp = httpx.get(
                self.BASE_URL,
                params={"apiKey": "SEDIA", "text": query, "pageSize": 5},
                timeout=15.0,
            )
            resp.raise_for_status()
            return {"source": self.name, "matched": True, "data": resp.json()}
        except Exception:  # noqa: BLE001
            return None


def build_registry() -> dict[str, object]:
    return {s.name: s for s in (CordisSource(), FtPortalSource())}


def get_enrichment_registry() -> dict[str, object]:
    """FastAPI dependency; overridden in tests with fake sources."""
    return build_registry()
