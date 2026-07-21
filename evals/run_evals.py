#!/usr/bin/env python3
"""Evaluate the triage pipeline against a labelled case set.

Two modes:

  Retrieval eval (default, offline, no API key):
      For each case, run BM25 retrieval and check whether the expected runbook
      appears in the top-k. Reports hit@k and mean reciprocal rank (MRR).

  Full eval (--full, requires ANTHROPIC_API_KEY):
      Additionally run the LLM triage and check that the expected runbook is
      cited and (optionally) that the severity matches.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --full
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the package importable when run as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.config import load_settings  # noqa: E402
from triage.knowledge_base import KnowledgeBase  # noqa: E402

CASES_PATH = Path(__file__).resolve().parent / "cases.json"


def _reciprocal_rank(ranked_ids: list[str], target: str) -> float:
    for i, rid in enumerate(ranked_ids, start=1):
        if rid == target:
            return 1.0 / i
    return 0.0


def run_retrieval_eval(kb: KnowledgeBase, cases: list[dict], top_k: int) -> bool:
    hits = 0
    rr_total = 0.0
    print(f"Retrieval eval  (top_k={top_k}, {len(cases)} cases)\n")
    for case in cases:
        ranked = kb.retrieve(case["incident"], top_k=top_k)
        ranked_ids = [sr.runbook.id for sr in ranked]
        target = case["expected_runbook"]
        hit = target in ranked_ids
        rr = _reciprocal_rank(ranked_ids, target)
        hits += int(hit)
        rr_total += rr
        mark = "PASS" if hit else "FAIL"
        top = ranked_ids[0] if ranked_ids else "-"
        print(f"  [{mark}]  {case['name']:<24}  top={top:<34}  rr={rr:.2f}")

    n = len(cases)
    print(f"\n  hit@{top_k}: {hits}/{n} ({hits / n:.0%})    MRR: {rr_total / n:.3f}")
    return hits == n


def run_full_eval(cases: list[dict]) -> bool:
    from triage.engine import TriageEngine  # imported lazily; needs a key at call time

    engine = TriageEngine.from_settings()
    passed = 0
    print(f"\nFull LLM eval  ({len(cases)} cases)\n")
    for case in cases:
        resp = engine.triage(case["incident"])
        cited_ids = _match_titles_to_ids(resp.result.relevant_runbooks, engine)
        cite_ok = case["expected_runbook"] in cited_ids
        sev_ok = (
            "expected_severity" not in case
            or resp.result.severity.value == case["expected_severity"]
        )
        ok = cite_ok and sev_ok
        passed += int(ok)
        mark = "PASS" if ok else "FAIL"
        print(
            f"  [{mark}]  {case['name']:<24}  "
            f"sev={resp.result.severity.value:<8} conf={resp.result.confidence.value}"
        )
    n = len(cases)
    print(f"\n  passed: {passed}/{n} ({passed / n:.0%})")
    return passed == n


def _match_titles_to_ids(titles: list[str], engine) -> set[str]:
    """Map cited runbook titles back to ids (titles are what the model returns)."""
    by_title = {rb.title.lower(): rb.id for rb in engine.kb.runbooks}
    ids = set()
    for title in titles:
        rid = by_title.get(title.strip().lower())
        if rid:
            ids.add(rid)
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the triage pipeline.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run the LLM triage eval (requires ANTHROPIC_API_KEY).",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    kb = KnowledgeBase.from_dir(settings.runbooks_dir)

    ok = run_retrieval_eval(kb, cases, top_k=settings.top_k)
    if args.full:
        ok = run_full_eval(cases) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
