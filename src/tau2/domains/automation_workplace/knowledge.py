"""Sparse retrieval over task-local workplace knowledge documents."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from tau2.domains.automation_workplace.data_model import KnowledgeDocument


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))


def search_documents(
    documents: dict[str, KnowledgeDocument], query: str, top_k: int
) -> list[dict[str, Any]]:
    """Return BM25-ranked full documents, preserving version metadata."""
    if not query.strip():
        return []
    ordered = sorted(documents.values(), key=lambda document: document.document_id)
    corpus = [
        _tokens(
            " ".join(
                [
                    document.title,
                    document.status,
                    " ".join(document.tags),
                    document.content,
                ]
            )
        )
        for document in ordered
    ]
    if not corpus:
        return []
    average_length = sum(map(len, corpus)) / len(corpus)
    document_frequency: Counter[str] = Counter()
    for tokens in corpus:
        document_frequency.update(set(tokens))

    query_tokens = _tokens(query)
    scores: list[tuple[float, int]] = []
    for index, tokens in enumerate(corpus):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_tokens:
            frequency = document_frequency.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log(
                (len(corpus) - frequency + 0.5) / (frequency + 0.5) + 1
            )
            term_frequency = frequencies[term]
            score += (
                inverse_frequency
                * (term_frequency * 2.5)
                / (
                    term_frequency
                    + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / average_length)
                )
            )
        if score > 0:
            scores.append((score, index))
    scores.sort(key=lambda item: (-item[0], ordered[item[1]].document_id))

    results = []
    for score, index in scores[:top_k]:
        document = ordered[index]
        results.append(
            {
                "document_id": document.document_id,
                "title": document.title,
                "status": document.status,
                "updated_at": document.updated_at,
                "score": round(score, 4),
                "content": document.content,
            }
        )
        if document.attachments:
            results[-1]["attachment_ids"] = list(document.attachments)
    return results
