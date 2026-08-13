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


@dataclass(frozen=True)
class Settings:
    """Immutable settings snapshot for one run."""

    model: str
    max_tokens: int
    top_k: int
    runbooks_dir: Path


def load_settings() -> Settings:
    """Build a Settings object from the current environment."""
    return Settings(
        model=os.getenv("TRIAGE_MODEL", DEFAULT_MODEL),
        max_tokens=int(os.getenv("TRIAGE_MAX_TOKENS", "8192")),
        top_k=int(os.getenv("TRIAGE_TOP_K", "3")),
        runbooks_dir=Path(os.getenv("TRIAGE_RUNBOOKS_DIR", str(DEFAULT_RUNBOOKS_DIR))),
    )
