"""Streamlit browser UI for the AI Business Operations Analyst."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
# Community Cloud exposes secrets through st.secrets rather than a local .env file.
# Copy only declared runtime settings into this process; never render or log their values.
try:
    for secret_name in ("AGENT_MODE", "OPENAI_API_KEY", "OPENAI_MODEL"):
        if secret_name in st.secrets:
            os.environ.setdefault(secret_name, str(st.secrets[secret_name]))
except FileNotFoundError:
    pass
from app.db import DATABASE_PATH
if not DATABASE_PATH.exists():
    # A fresh deployment can start from the repository without a developer-created DB file.
    from scripts.seed_data import build_database
    build_database()
from app.agent import answer

st.set_page_config(page_title="AI Business Operations Analyst", page_icon="📊", layout="centered")
st.title("AI Business Operations Analyst")
st.caption("Evidence-based decision support for a synthetic property portfolio. Read-only, with no external actions.")

with st.sidebar:
    st.subheader("Portfolio scope")
    st.write("8 synthetic properties · Jan-Dec 2025")
    st.write(f"Mode: `{os.getenv('AGENT_MODE', 'demo')}`")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("activity"):
            with st.expander("Analysis activity"):
                st.write("\n".join(f"- {item}" for item in message["activity"]))
        if message.get("evidence"):
            with st.expander("Evidence used"):
                st.json(message["evidence"])

if prompt := st.chat_input("Ask about revenue, occupancy, pricing, costs, cancellations, or trends…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
    with st.chat_message("assistant"):
        with st.spinner("Analyzing portfolio data…"):
            reply = answer(prompt, history)
        st.markdown(reply.text)
        if reply.activity:
            with st.expander("Analysis activity"):
                st.write("\n".join(f"- {item}" for item in reply.activity))
        if reply.evidence:
            with st.expander("Evidence used"):
                st.json(reply.evidence)
    st.session_state.messages.append({"role": "assistant", "content": reply.text, "activity": reply.activity, "evidence": reply.evidence})
