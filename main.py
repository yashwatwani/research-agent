# main.py — Streamlit UI for the research agent
#
# Usage:
#   streamlit run main.py
#
# Opens at http://localhost:8501

import asyncio
import streamlit as st
from src.eval.tracer import init_tracing
from src.agent.researcher import run_agent
from src.agent.logger import log_interaction
from src.agent.suggestions import get_suggestions

# initialise tracing once per Streamlit session
# st.cache_resource ensures this runs only once even as the script re-runs
@st.cache_resource
def setup_tracing():
    init_tracing()
    return True

setup_tracing()

# ── page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="centered",
)

# ── header ───────────────────────────────────────────────────
st.title("🔬 Research Agent")
st.caption(
    "Ask a research question — AI, technology, science, geopolitics, current events, "
    "and factual deep-dives. The agent searches the web, stores what it learns, and "
    "synthesises a structured report."
)
st.divider()

# ── example questions ────────────────────────────────────────
with st.expander("Example questions"):
    examples = [
        "What is the Model Context Protocol and why was it introduced?",
        "How does Graph RAG differ from standard vector RAG?",
        "What companies have adopted MCP and why?",
        "What are the latest developments in retrieval-augmented generation?",
        "How does pgvector integrate with PostgreSQL for semantic search?",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state["prefill"] = ex

# ── input ─────────────────────────────────────────────────────
prefill = st.session_state.pop("prefill", "")
question = st.text_area(
    "Your question",
    value=prefill,
    height=80,
    placeholder="What is the Model Context Protocol and why was it introduced?",
)

col1, col2 = st.columns([1, 5])
with col1:
    run = st.button("Research", type="primary")

# ── run ───────────────────────────────────────────────────────
if run and question.strip():
    with st.spinner("Researching…"):
        state = asyncio.run(run_agent(question.strip()))

    # log every interaction
    log_interaction(
        question=state.question,
        report=state.report or "",
        groundedness_score=state.groundedness_score,
        blocked=state.blocked,
        block_reason=state.block_reason,
        context=getattr(state, "context_text", "") or "",
        source="ui",
    )

    st.divider()

    if state.blocked:
        reason = state.block_reason or ""

        # out of scope — friendly educational message
        if "out_of_scope" in reason:
            st.warning("**Out of scope**", icon="🔍")
            st.markdown(
                "This agent is built for **research questions** — topics like AI, technology, "
                "science, geopolitics, current events, and factual analysis.\n\n"
                "Simple lookups, trivia, personal advice, and casual questions are outside "
                "its scope. It works best when a question needs synthesis across multiple "
                "sources — not just a single-sentence answer."
            )

        # injection attempt
        elif any(w in reason.lower() for w in ["inject", "block", "system", "prompt"]):
            st.error("**Request blocked**", icon="🚫")
            st.markdown(
                "This question was flagged as a potential prompt injection attempt. "
                "If this was a legitimate research question, try rephrasing it clearly."
            )

        # any other block reason
        else:
            st.warning("**Request blocked**", icon="⚠️")
            st.markdown(f"Reason: {reason}")

        # suggestions — always show these for out-of-scope, useful context
        with st.spinner("Finding related research questions…"):
            suggestions = get_suggestions(question.strip())

        if suggestions:
            st.markdown("**You could try asking:**")
            for s in suggestions:
                if st.button(f"→ {s}", key=s):
                    st.session_state["prefill"] = s
                    st.rerun()

    elif state.error:
        st.error(f"Agent error: {state.error}")

    else:
        # success — show report
        if state.groundedness_score is not None:
            score = state.groundedness_score
            color = "green" if score >= 0.7 else "orange" if score >= 0.5 else "red"
            st.markdown(
                f"<span style='color:{color};font-size:13px;'>"
                f"Groundedness score: {score:.2f}"
                f"</span>",
                unsafe_allow_html=True,
            )

        st.markdown(state.report)

        # retrieved context — collapsed by default, useful for debugging
        context = getattr(state, "context_text", "") or ""
        if context:
            with st.expander("Retrieved context (debug)"):
                st.text(context[:3000])

elif run and not question.strip():
    st.warning("Please enter a question first.")