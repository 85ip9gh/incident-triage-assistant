"""AI incident-triage assistant.

Retrieves the most relevant runbooks for an incident (alert, error, log excerpt,
or stack trace) and asks Claude to produce a grounded, structured triage: probable
root cause, remediation steps, and commands to run.
"""

from .config import Settings, load_settings
from .knowledge_base import KnowledgeBase, Runbook, ScoredRunbook
from .models import Confidence, Severity, TriageResult

__all__ = [
    "Settings",
    "load_settings",
    "KnowledgeBase",
    "Runbook",
    "ScoredRunbook",
    "Confidence",
    "Severity",
    "TriageResult",
]

__version__ = "0.1.0"
