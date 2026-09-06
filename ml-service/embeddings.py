"""Embedding + similarity utilities for deterministic skill matching.

Uses OpenAI ``text-embedding-3-small`` by default: small, cheap, and requires
no local torch/sentence-transformers install (which kept SkillQuest's earlier
KeyBERT stack heavy and hard to deploy). The score math lives here, not in an
LLM, so matching is deterministic, reproducible, and auditable.
"""

import math
import os
from typing import List

from dotenv import load_dotenv

from llm import get_client

load_dotenv()

DEFAULT_EMBED_MODEL = os.getenv("SKILLQUEST_EMBED_MODEL", "text-embedding-3-small")


async def embed_texts(texts: List[str], *, model: str = None) -> List[List[float]]:
    """Embed a batch of texts, preserving input order. Empty input -> []."""
    cleaned = [t if (t and t.strip()) else " " for t in texts]
    if not cleaned:
        return []
    client = get_client()
    resp = await client.embeddings.create(
        model=model or DEFAULT_EMBED_MODEL,
        input=cleaned,
    )
    ordered = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in ordered]


def cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 on degenerate input."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)

