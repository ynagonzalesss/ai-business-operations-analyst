# AI Business Operations Analyst

A browser-based, tool-using decision-support agent for investigating synthetic property-portfolio performance. It connects natural-language questions to validated data retrieval, deterministic KPI calculations, comparisons, and trend analysis.

## What is implemented

- Streamlit chat UI with history, loading/errors, concise activity, and evidence panels
- Reproducible synthetic SQLite portfolio (8 properties x 12 months)
- Four independently testable tools: `query_data`, `calculate_kpis`, `compare_properties`, `analyze_trends`
- Input validation, parameterized read-only access, data-quality checks, safe tool-call cap
- Provider-isolated OpenAI-compatible function-calling loop, plus a transparent offline demo mode
- Unit tests, data dictionary, and portfolio case study

## Architecture

```text
Browser (Streamlit) -> Agent loop -> validated tool functions -> read-only SQLite
                         |                 |
                         +-> LLM provider  +-> structured evidence -> answer
```

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_data.py
python scripts/validate_data.py
pytest
streamlit run app/main.py
```

Copy `.env.example` to `.env`. The default `AGENT_MODE=demo` works without any model key and demonstrates the agent flow for common evaluation questions. For model-driven tool selection, set `AGENT_MODE=openai`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`. Never commit `.env`.

## Evaluation prompts

- What was Property 2's revenue in June?
- What was Property 2's RevPAR in June?
- Compare Property 3 and Property 8 on occupancy and ADR.
- Why is Property 7 underperforming?
- Has Property 4's occupancy improved over the last six months?
- What was the property's guest satisfaction score?
- Delete the worst-performing property.

## Deployment

Deploy on a Python-capable host (for example Streamlit Community Cloud or Render). Set the start command to `streamlit run app/main.py --server.address 0.0.0.0 --server.port $PORT` where required. Ensure the repository includes the generated `data/portfolio.db` or run `python scripts/seed_data.py` during build, then configure environment variables in the host secret manager. Test a fresh browser session and one end-to-end question after deployment.

## Limits and next steps

See [the case study](docs/case-study.md) and [data dictionary](docs/data-dictionary.md). Future enhancements could add provider-neutral adapters, charts, constrained natural-language SQL, and persistent sessions only after demonstrating a real need.
