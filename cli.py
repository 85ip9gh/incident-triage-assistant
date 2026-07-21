#!/usr/bin/env python3
"""Command-line entry point for the incident-triage assistant.

Examples:
    python cli.py "HikariPool-1 - Connection is not available, timed out after 30000ms"
    kubectl logs mypod --previous | python cli.py
    python cli.py --file incident.log
    python cli.py --retrieval-only "OOMKilled exit code 137"   # no API call
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from triage.engine import TriageEngine, TriageResponse
from triage.knowledge_base import ScoredRunbook


def _read_incident(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            return fh.read()
    if args.incident:
        return args.incident
    return sys.stdin.read()


def _print_retrieval(retrieved: list[ScoredRunbook]) -> None:
    print("Retrieved runbooks:")
    for sr in retrieved:
        print(f"  [{sr.score:6.2f}]  {sr.runbook.title}  ({sr.runbook.id})")


def _print_triage(resp: TriageResponse) -> None:
    r = resp.result
    line = "=" * 68
    print(line)
    print(f"SUMMARY     {r.summary}")
    print(f"SEVERITY    {r.severity.value.upper()}      CONFIDENCE  {r.confidence.value.upper()}")
    print(line)
    print("\nROOT CAUSE")
    print(f"  {r.root_cause}")

    print("\nREMEDIATION STEPS")
    for i, step in enumerate(r.remediation_steps, 1):
        print(f"  {i}. {step}")

    if r.commands:
        print("\nCOMMANDS")
        for cmd in r.commands:
            print(f"  $ {cmd}")

    print("\nESCALATION")
    print(f"  {r.escalation}")

    if r.relevant_runbooks:
        print("\nGROUNDED IN")
        for name in r.relevant_runbooks:
            print(f"  - {name}")

    print(
        f"\n[{resp.model}  |  {resp.input_tokens} in / {resp.output_tokens} out tokens]"
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="AI incident-triage assistant (RAG over runbooks + Claude)."
    )
    parser.add_argument(
        "incident",
        nargs="?",
        help="Incident text. If omitted, reads from stdin.",
    )
    parser.add_argument("--file", "-f", help="Read incident text from a file.")
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Show only the retrieved runbooks; make no API call (no key needed).",
    )
    args = parser.parse_args(argv)

    incident = _read_incident(args)
    if not incident.strip():
        parser.error("No incident text provided (argument, --file, or stdin).")

    engine = TriageEngine.from_settings()

    if args.retrieval_only:
        _print_retrieval(engine.retrieve(incident))
        return 0

    try:
        resp = engine.triage(incident)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the CLI user
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_triage(resp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
