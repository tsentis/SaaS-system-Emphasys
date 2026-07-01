"""Text embeddings behind a swappable interface.

Anthropic does not provide an embeddings endpoint, so a real deployment plugs in a
provider (e.g. Voyage AI) here. ``FakeEmbedder`` is deterministic and dependency-free
so semantic-search wiring is testable now; identical text yields identical vectors.
"""

import hashlib
import math
import random
from typing import Protocol

from app.models.enrichment import EMBEDDING_DIM


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        rng = random.Random(seed)
        vec = [rng.gauss(0.0, 1.0) for _ in range(EMBEDDING_DIM)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def get_embedder() -> Embedder:
    return FakeEmbedder()
