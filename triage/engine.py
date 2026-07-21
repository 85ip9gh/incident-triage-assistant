"""The triage engine: retrieve relevant runbooks, then ask Claude to diagnose.

This is a retrieval-augmented generation (RAG) pipeline. The BM25 stage narrows
the knowledge base to the most relevant runbooks; Claude reasons over just those,
with structured output guaranteeing a machine-usable result.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from .config import Settings, load_settings
from .knowledge_base import KnowledgeBase, ScoredRunbook
from .models import TriageResult

SYSTEM_PROMPT = """\
You are an experienced site reliability engineer acting as an incident-triage \
assistant. You are given an alert, error, log excerpt, or stack trace, plus the \
most relevant runbooks retrieved from the team knowledge base. Diagnose the most \
probable root cause and produce a concrete, actionable remediation plan.

Rules:
- Ground your analysis in the retrieved runbooks. If they clearly do not cover the \
incident, say so in the summary, rely on general SRE knowledge, and lower your \
confidence accordingly.
- Never invent commands, file paths, hostnames, or configuration that are not \
supported by the incident text or the runbooks. It is better to describe a step in \
words than to fabricate a precise command.
- Prefer the smallest safe action that confirms the diagnosis before any \
destructive or irreversible step.
- Order remediation_steps and commands from first to last.
- Set confidence honestly: use "high" only when the evidence clearly matches a \
known failure mode, "low" when you are largely guessing."""


@dataclass
class TriageResponse:
    """Everything a caller needs to render one triage."""

    result: TriageResult
    retrieved: list[ScoredRunbook]
    model: str
    input_tokens: int
    output_tokens: int


def _format_runbooks(retrieved: list[ScoredRunbook]) -> str:
    if not retrieved:
        return "(no runbooks matched this incident)"
    blocks = []
    for i, sr in enumerate(retrieved, start=1):
        blocks.append(
            f'<runbook index="{i}" title="{sr.runbook.title}" '
            f'match_score="{sr.score:.2f}">\n{sr.runbook.content}\n</runbook>'
        )
    return "\n\n".join(blocks)


class TriageEngine:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        settings: Settings | None = None,
        client: "anthropic.Anthropic | None" = None,
    ):
        self.kb = knowledge_base
        self.settings = settings or load_settings()
        # Client is created lazily so retrieval works without an API key.
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "TriageEngine":
        settings = settings or load_settings()
        kb = KnowledgeBase.from_dir(settings.runbooks_dir)
        return cls(kb, settings=settings)

    @property
    def client(self) -> "anthropic.Anthropic":
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def retrieve(self, incident: str) -> list[ScoredRunbook]:
        return self.kb.retrieve(incident, top_k=self.settings.top_k)

    def triage(
        self, incident: str, retrieved: list[ScoredRunbook] | None = None
    ) -> TriageResponse:
        if retrieved is None:
            retrieved = self.retrieve(incident)

        user_content = (
            "## Retrieved runbooks\n\n"
            + _format_runbooks(retrieved)
            + "\n\n## Incident\n\n"
            + incident.strip()
            + "\n\nTriage this incident."
        )

        response = self.client.messages.parse(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": user_content}],
            output_format=TriageResult,
        )

        result = response.parsed_output
        if result is None:
            raise RuntimeError(
                "Claude did not return a parseable TriageResult "
                f"(stop_reason={response.stop_reason})."
            )

        return TriageResponse(
            result=result,
            retrieved=retrieved,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
