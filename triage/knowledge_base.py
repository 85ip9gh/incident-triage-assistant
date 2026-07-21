"""Runbook loading and retrieval.

The knowledge base is a directory of markdown runbooks. Retrieval uses a small,
dependency-free BM25 implementation: error text and runbooks share a lot of
literal tokens (error strings, tool names, exit codes), so lexical ranking is a
strong, transparent first stage before the LLM reasons over the results.

The `Retriever` protocol keeps this pluggable: swap in a semantic/embedding
retriever without touching the engine.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization."""
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class Runbook:
    id: str
    title: str
    content: str


@dataclass(frozen=True)
class ScoredRunbook:
    runbook: Runbook
    score: float


@runtime_checkable
class Retriever(Protocol):
    def search(self, query: str, top_k: int) -> list[ScoredRunbook]: ...


class BM25Index:
    """Okapi BM25 over a fixed set of runbooks. Pure Python, no dependencies."""

    def __init__(self, runbooks: Iterable[Runbook], k1: float = 1.5, b: float = 0.75):
        self.runbooks: list[Runbook] = list(runbooks)
        self.k1 = k1
        self.b = b

        self._docs_tokens = [
            tokenize(f"{r.title}\n{r.content}") for r in self.runbooks
        ]
        self._doc_len = [len(toks) for toks in self._docs_tokens]
        self._avgdl = (
            sum(self._doc_len) / len(self._doc_len) if self._doc_len else 0.0
        )
        self._freqs = [Counter(toks) for toks in self._docs_tokens]

        n = len(self.runbooks)
        df: Counter[str] = Counter()
        for toks in self._docs_tokens:
            df.update(set(toks))
        # BM25 idf with the +1 smoothing variant so scores stay non-negative.
        self._idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def search(self, query: str, top_k: int = 3) -> list[ScoredRunbook]:
        q_terms = tokenize(query)
        scored: list[ScoredRunbook] = []
        for i, runbook in enumerate(self.runbooks):
            freqs = self._freqs[i]
            dl = self._doc_len[i]
            score = 0.0
            for term in q_terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                denom = tf + self.k1 * (
                    1 - self.b + self.b * dl / self._avgdl if self._avgdl else 1.0
                )
                score += idf * (tf * (self.k1 + 1)) / denom
            scored.append(ScoredRunbook(runbook=runbook, score=score))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[: max(top_k, 0)]


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def load_runbooks(runbooks_dir: Path) -> list[Runbook]:
    """Load every ``*.md`` file in ``runbooks_dir`` as a Runbook."""
    runbooks: list[Runbook] = []
    for path in sorted(Path(runbooks_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _extract_title(text, fallback=path.stem.replace("-", " ").title())
        runbooks.append(Runbook(id=path.stem, title=title, content=text))
    return runbooks


class KnowledgeBase:
    """A searchable collection of runbooks."""

    def __init__(self, runbooks: Iterable[Runbook], retriever: Retriever | None = None):
        self.runbooks: list[Runbook] = list(runbooks)
        self._retriever: Retriever = retriever or BM25Index(self.runbooks)

    @classmethod
    def from_dir(cls, runbooks_dir: Path) -> "KnowledgeBase":
        runbooks = load_runbooks(runbooks_dir)
        if not runbooks:
            raise FileNotFoundError(f"No runbooks (*.md) found in {runbooks_dir}")
        return cls(runbooks)

    def retrieve(self, query: str, top_k: int = 3) -> list[ScoredRunbook]:
        return self._retriever.search(query, top_k=top_k)

    def __len__(self) -> int:
        return len(self.runbooks)
