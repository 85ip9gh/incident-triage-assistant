"""Runtime configuration, read from environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNBOOKS_DIR = REPO_ROOT / "runbooks"

# Default model. Claude Opus 5 is the strongest reasoning model; override with
# TRIAGE_MODEL (e.g. claude-sonnet-5 or claude-haiku-4-5) to trade quality for
# cost/latency on high-volume triage.
DEFAULT_MODEL = "claude-opus-5"

# Server-side fallback for policy refusals. Claude Opus 5 runs elevated
# cybersecurity safeguards, and incident triage reads a lot like the content
# those classifiers watch for: malware behaviour, intrusion signals, exploit
# traces. A false positive returns HTTP 200 with stop_reason="refusal" rather
# than an error, so without a fallback a legitimate triage just stops.
# claude-opus-4-8 is the documented target for cyber-category refusals.
# Set TRIAGE_FALLBACK_MODEL="" to disable and surface refusals directly.
DEFAULT_FALLBACK_MODEL = "claude-opus-4-8"

# Beta flag gating the `fallbacks` array form. The newer `fallbacks="default"`
# scalar (which routes by refusal category instead of pinning a model) uses
# server-side-fallback-2026-07-01 and is the better long-term shape, but it is
# not in the anthropic 0.117.0 typings, where `fallbacks` is
# Iterable[BetaFallbackParam]. A bare str satisfies Iterable and would risk
# serializing into single characters, so pin the array form until the SDK
# types the scalar. Pairing either header with the other form returns a 400.
FALLBACK_BETA_FLAG = "server-side-fallback-2026-06-01"


@dataclass(frozen=True)
class Settings:
    """Immutable settings snapshot for one run."""

    model: str
    fallback_model: str | None
    max_tokens: int
    top_k: int
    runbooks_dir: Path


def load_settings() -> Settings:
    """Build a Settings object from the current environment."""
    # An explicitly empty TRIAGE_FALLBACK_MODEL disables the fallback; unset
    # falls back to the default. os.getenv alone cannot tell those apart.
    fallback_model = os.getenv("TRIAGE_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL).strip()

    return Settings(
        model=os.getenv("TRIAGE_MODEL", DEFAULT_MODEL),
        fallback_model=fallback_model or None,
        max_tokens=int(os.getenv("TRIAGE_MAX_TOKENS", "8192")),
        top_k=int(os.getenv("TRIAGE_TOP_K", "3")),
        runbooks_dir=Path(os.getenv("TRIAGE_RUNBOOKS_DIR", str(DEFAULT_RUNBOOKS_DIR))),
    )
