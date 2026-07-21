"""Offline tests for the knowledge base and BM25 retriever.

These exercise the retrieval stage end to end and need no API key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage.config import load_settings
from triage.knowledge_base import BM25Index, KnowledgeBase, Runbook, tokenize

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS_DIR = REPO_ROOT / "runbooks"
CASES = json.loads((REPO_ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return KnowledgeBase.from_dir(RUNBOOKS_DIR)


def test_tokenize_lowercases_and_splits():
    assert tokenize("OOMKilled Exit-Code 137!") == ["oomkilled", "exit", "code", "137"]


def test_knowledge_base_loads_all_runbooks(kb: KnowledgeBase):
    md_files = list(RUNBOOKS_DIR.glob("*.md"))
    assert len(kb) == len(md_files) >= 7
    assert all(rb.title for rb in kb.runbooks)


def test_empty_dir_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        KnowledgeBase.from_dir(tmp_path)


def test_scores_are_sorted_and_non_negative(kb: KnowledgeBase):
    results = kb.retrieve("HikariPool connection pool timed out", top_k=5)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(s >= 0 for s in scores)


def test_top_k_is_respected(kb: KnowledgeBase):
    assert len(kb.retrieve("disk full no space left on device", top_k=2)) == 2


def test_bm25_ranks_exact_error_string_first():
    runbooks = [
        Runbook("a", "Alpha", "unrelated content about caching and latency"),
        Runbook("b", "Beta", "OOMKilled exit code 137 memory limit exceeded"),
    ]
    index = BM25Index(runbooks)
    top = index.search("OOMKilled exit code 137", top_k=1)[0]
    assert top.runbook.id == "b"


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_expected_runbook_in_top_k(kb: KnowledgeBase, case: dict):
    top_k = load_settings().top_k
    ranked_ids = [r.runbook.id for r in kb.retrieve(case["incident"], top_k=top_k)]
    assert case["expected_runbook"] in ranked_ids
