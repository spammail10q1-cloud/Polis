"""Local retrieval over a curated, versioned evidence corpus.

The MVP uses a deterministic local hybrid retriever: hashed token/bigram
embeddings for semantic-ish similarity plus lexical overlap and tag boosts. The
embedding column and interface are intentionally compatible with a future
pgvector-backed retriever; no external embedding API is required for the demo.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvidenceSource
from app.schemas import CitationOut

EMBEDDING_DIM = 384
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-]{1,}", re.IGNORECASE)

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "will",
    "would", "could", "should", "have", "has", "had", "about", "into", "your", "you",
    "what", "which", "when", "where", "how", "why", "does", "did", "not", "can", "may",
    "might", "given", "tell", "explain", "please", "there", "their", "they", "them",
    "using", "use", "used", "also", "more", "most", "than", "then", "but", "its", "it",
}


def tokenize(text: str) -> list[str]:
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def embed_text(text: str) -> list[float]:
    vector = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    tokens = tokenize(text)
    features: list[tuple[str, float]] = [(token, 1.0) for token in tokens]
    features.extend((f"{tokens[i]}::{tokens[i + 1]}", 0.5) for i in range(len(tokens) - 1))
    for feature, weight in features:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "little") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * weight
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def _lexical_score(query_tokens: list[str], document: str) -> float:
    doc_tokens = Counter(tokenize(document))
    if not query_tokens or not doc_tokens:
        return 0.0
    score = 0.0
    for token in set(query_tokens):
        if token in doc_tokens:
            score += 1.0 + math.log(1 + doc_tokens[token])
    return score / (len(set(query_tokens)) ** 0.5)


def retrieve(
    db: Session,
    query: str,
    *,
    tags: list[str] | None = None,
    limit: int = 4,
) -> list[tuple[EvidenceSource, float, dict]]:
    sources = list(db.scalars(select(EvidenceSource)).all())
    if not sources:
        return []
    query_vector = embed_text(query)
    query_tokens = tokenize(query)
    boost_terms = {tag.lower() for tag in (tags or [])}
    ranked: list[tuple[EvidenceSource, float, dict]] = []
    for source in sources:
        cosine = _cosine(query_vector, source.embedding or embed_text(source.title + " " + source.summary))
        lexical = _lexical_score(query_tokens, f"{source.title} {source.summary} {source.content} {' '.join(source.tags)}")
        tag_hits = len(boost_terms.intersection({str(tag).lower() for tag in source.tags + [source.title, source.organization]}))
        score = 0.55 * cosine + 0.35 * lexical + 0.10 * min(tag_hits, 3)
        debug = {
            "cosine": round(cosine, 4),
            "lexical": round(lexical, 4),
            "tag_boost": round(min(tag_hits, 3), 2),
            "score": round(score, 4),
        }
        ranked.append((source, score, debug))
    ranked.sort(key=lambda item: (item[1], item[0].organization), reverse=True)
    return ranked[:limit]


def citation(source: EvidenceSource) -> CitationOut:
    return CitationOut(
        id=source.id,
        title=source.title,
        organization=source.organization,
        url=source.url,
        published_at=source.published_at,
        evidence_level=source.evidence_level,
        summary=source.summary,
    )


def citations(db: Session, ids: list[str]) -> list[CitationOut]:
    if not ids:
        return []
    sources = db.scalars(select(EvidenceSource).where(EvidenceSource.id.in_(set(ids)))).all()
    by_id = {source.id: source for source in sources}
    return [citation(by_id[source_id]) for source_id in dict.fromkeys(ids) if source_id in by_id]


def snippets_for(source: EvidenceSource, query: str, max_chars: int = 520) -> str:
    """Extract a query-relevant sentence window without generating new text."""
    sentences = re.split(r"(?<=[.!?])\s+", source.content)
    query_terms = set(tokenize(query))
    scored = []
    for sentence in sentences:
        terms = set(tokenize(sentence))
        overlap = len(query_terms.intersection(terms))
        scored.append((overlap, len(sentence), sentence))
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    selected = ""
    for _overlap, _length, sentence in scored:
        if len(selected) + len(sentence) > max_chars:
            continue
        selected = f"{selected} {sentence}".strip()
        if len(selected) > max_chars * 0.65:
            break
    return selected or source.summary
