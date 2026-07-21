"""Streamlit UI for the incident-triage assistant.

Run with:  streamlit run app.py
The knowledge base loads and retrieval works without an API key; producing a
triage requires ANTHROPIC_API_KEY (in the environment or a local .env file).
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from triage.config import load_settings
from triage.engine import TriageEngine

load_dotenv()

SAMPLE_INCIDENTS = {
    "Database pool": (
        "HikariPool-1 - Connection is not available, request timed out after "
        "30000ms. Postgres: FATAL: sorry, too many clients already."
    ),
    "OOMKilled pod": (
        "kubectl describe pod shows Last State: Terminated, Reason: OOMKilled, "
        "Exit Code: 137. The container restarts every few minutes under load."
    ),
    "Expired TLS cert": (
        "curl: SSL certificate problem: certificate has expired. Services report "
        "x509: certificate has expired or is not yet valid since 02:00 UTC."
    ),
    "Kafka lag": (
        "Consumer group lag rising, records-lag-max high, consumers falling "
        "behind and rebalancing repeatedly."
    ),
}

SEVERITY_COLORS = {
    "critical": "#b42318",
    "high": "#d1462f",
    "medium": "#b54708",
    "low": "#027a48",
}
CONFIDENCE_COLORS = {"high": "#027a48", "medium": "#b54708", "low": "#667085"}


@st.cache_resource(show_spinner=False)
def get_engine() -> TriageEngine:
    return TriageEngine.from_settings()


def _badge(label: str, value: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">'
        f"{label}: {value.upper()}</span>"
    )


st.set_page_config(page_title="Incident Triage Assistant", page_icon="🚨", layout="centered")

engine = get_engine()
settings = engine.settings

st.title("🚨 Incident Triage Assistant")
st.caption(
    "Paste an alert, error, log line, or stack trace. The assistant retrieves the "
    "most relevant runbooks and asks Claude for a grounded root-cause and fix."
)

with st.sidebar:
    st.subheader("Configuration")
    st.write(f"**Model:** `{settings.model}`")
    st.write(f"**Runbooks loaded:** {len(engine.kb)}")
    st.write(f"**Retriever:** BM25, top-{settings.top_k}")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning(
            "No `ANTHROPIC_API_KEY` set. Retrieval works, but generating a triage "
            "needs a key (environment variable or a local `.env`)."
        )
    st.divider()
    st.caption("Load a sample:")
    for name, text in SAMPLE_INCIDENTS.items():
        if st.button(name, use_container_width=True):
            st.session_state["incident"] = text

incident = st.text_area(
    "Incident",
    key="incident",
    height=160,
    placeholder="e.g. Back-off restarting failed container; CrashLoopBackOff on web-7c9...",
)

col_run, col_preview = st.columns([1, 1])
run = col_run.button("Triage", type="primary", use_container_width=True)
preview = col_preview.button("Preview retrieval", use_container_width=True)

if preview and incident.strip():
    st.subheader("Retrieved runbooks")
    for sr in engine.retrieve(incident):
        st.write(f"`{sr.score:5.2f}`  **{sr.runbook.title}**  ({sr.runbook.id})")

if run and incident.strip():
    with st.spinner("Retrieving runbooks and triaging..."):
        try:
            resp = engine.triage(incident)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Triage failed: {exc}")
            st.stop()

    r = resp.result
    st.markdown(
        _badge("Severity", r.severity.value, SEVERITY_COLORS.get(r.severity.value, "#667085"))
        + "&nbsp;&nbsp;"
        + _badge(
            "Confidence", r.confidence.value, CONFIDENCE_COLORS.get(r.confidence.value, "#667085")
        ),
        unsafe_allow_html=True,
    )
    st.subheader(r.summary)

    st.markdown("**Root cause**")
    st.write(r.root_cause)

    st.markdown("**Remediation steps**")
    for i, step in enumerate(r.remediation_steps, 1):
        st.write(f"{i}. {step}")

    if r.commands:
        st.markdown("**Commands**")
        st.code("\n".join(r.commands), language="bash")

    st.markdown("**Escalation**")
    st.write(r.escalation)

    if r.relevant_runbooks:
        st.markdown("**Grounded in**")
        st.write(", ".join(r.relevant_runbooks))

    with st.expander("Runbooks retrieved for this incident"):
        for sr in resp.retrieved:
            st.markdown(f"**{sr.runbook.title}**  ·  score `{sr.score:.2f}`")
            st.markdown(sr.runbook.content)
            st.divider()

    st.caption(
        f"{resp.model} · {resp.input_tokens} in / {resp.output_tokens} out tokens"
    )
elif (run or preview) and not incident.strip():
    st.info("Enter some incident text first.")
