# AI Business Operations Analyst - case study

## Problem
Portfolio questions often require manual reconciliation of occupancy, pricing, revenue, and costs. This project makes the first investigation conversational while keeping claims tied to deterministic business data.

## Solution
A Streamlit chat UI calls a bounded agent loop. The agent chooses from validated read-only data retrieval, KPI calculation, property comparison, and trend-analysis tools. SQLite performs aggregation and arithmetic; the model only interprets returned evidence.

## Reliability choices

- Synthetic, documented data with validation checks
- Parameterized read-only database access; no arbitrary SQL or external actions
- Explicit missing-data and scope responses
- Tool-input validation and a six-round agent cap
- User-visible operational activity and evidence, without chain-of-thought

## Limitations

This is an MVP with synthetic monthly data, a constrained domain, and no causal channel/conversion signals. It is decision support, not an autonomous action system.
