"""Provider-isolated agent loop with bounded, validated tool calls."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from app.tools import TOOL_FUNCTIONS, TOOL_SCHEMAS, analyze_trends, calculate_kpis, compare_properties

SYSTEM_PROMPT = """You are an AI Business Operations Analyst for a synthetic property portfolio.
Use tools whenever a factual claim about the portfolio is needed. Never invent data or calculate KPIs mentally.
Your response must clearly label Finding, Evidence, Interpretation, Recommendation (only if supported), and Limitation when relevant.
Do not disclose private reasoning. Mention the tool-derived evidence concisely. The dataset has no guest satisfaction, channel conversion, or external-action capability."""
MAX_TOOL_ROUNDS = 6

@dataclass
class AgentReply:
    text: str
    evidence: list[dict[str, Any]]
    activity: list[str]
    error: str | None = None


def _demo_reply(question: str) -> AgentReply:
    """Offline demo mode gives a usable, transparent fallback without pretending to be an LLM."""
    normalized = question.lower()
    ids = [int(x) for x in re.findall(r"property\s+(\d+)", normalized)]
    if any(word in normalized for word in ("delete", "modify", "change data")):
        return AgentReply("I can't make external or destructive changes. This MVP is read-only decision support.", [], [])
    if any(word in normalized for word in ("guest satisfaction", "review score", "conversion", "channel")):
        return AgentReply("**Limitation:** that metric is not available in the synthetic portfolio dataset. I can analyze revenue, nights, costs, bookings, cancellations, occupancy, ADR, RevPAR, and contribution margin.", [], [])
    if "underperform" in normalized and (7 in ids or "property 7" in normalized):
        comparison = compare_properties("portfolio")
        trend = analyze_trends(7, "occupancy")
        weak = next(row for row in comparison["data"]["properties"] if row["property_id"] == 7)
        benchmark = comparison["data"]["portfolio_benchmark"]
        text = (f"**Finding:** Property 7 is underperforming on RevPAR.\n\n"
                f"**Evidence:** Its RevPAR is ${weak['revpar']:,.2f}, {abs(weak['vs_portfolio_revpar_pct']):.1f}% below the portfolio's ${benchmark['revpar']:,.2f}. "
                f"Occupancy is {weak['occupancy']:.1%} versus {benchmark['occupancy']:.1%}, while ADR is ${weak['adr']:,.2f} versus ${benchmark['adr']:,.2f}.\n\n"
                f"**Interpretation:** The large occupancy gap is the primary driver; pricing is comparatively closer to the portfolio level.\n\n"
                f"**Recommendation:** Investigate demand generation and booking conversion before applying a broad ADR reduction.\n\n"
                f"**Limitation:** The dataset has no channel-level traffic or conversion data, so it cannot identify the exact cause of the booking-volume gap.")
        return AgentReply(text, [comparison, trend], ["Compared Property 7 with the portfolio", "Analyzed Property 7 occupancy trend"])
    if len(ids) >= 2 or "compare" in normalized:
        selected = ids[:2] if len(ids) >= 2 else [3, 8]
        result = compare_properties(selected)
        if not result["success"]: return AgentReply("I couldn't complete that comparison: " + result["error"], [result], [])
        rows = result["data"]["properties"]
        text = "**Evidence-based comparison:**\n\n" + "\n".join(f"- **{r['property_name']} (Property {r['property_id']})**: occupancy {r['occupancy']:.1%}, ADR ${r['adr']:,.2f}, RevPAR ${r['revpar']:,.2f}, contribution margin ${r['contribution_margin']:,.0f}." for r in rows) + "\n\n**Limitation:** This compares recorded portfolio metrics only; it does not establish causality."
        return AgentReply(text, [result], [f"Compared Properties {', '.join(map(str, selected))}"])
    if "trend" in normalized or "improved" in normalized or "last six" in normalized:
        property_id = ids[0] if ids else 4
        result = analyze_trends(property_id, "occupancy", "2025-07", "2025-12")
        if result["success"]:
            data = result["data"]
            monthly_evidence = ", ".join(
                "{}: {:.1%}".format(item["month"][:7], item["value"])
                for item in data["monthly_values"]
            )
            text = (
                f"**Finding:** Property {property_id}'s occupancy {data['direction']} by {data['change']:.1%} "
                "from July to December 2025.\n\n"
                f"**Evidence:** {monthly_evidence}.\n\n"
                "**Limitation:** The synthetic data cannot explain the operational cause of the change."
            )
            return AgentReply(text, [result], ["Analyzed occupancy trend"])
    return AgentReply("I’m in offline demo mode. Try: “Why is Property 7 underperforming?”, “Compare Property 3 and Property 8”, or “Has Property 4's occupancy improved over the last six months?” Set `AGENT_MODE=openai` and `OPENAI_API_KEY` to enable open-ended model-driven analysis.", [], [])


def _openai_reply(question: str, history: list[dict[str, str]]) -> AgentReply:
    try:
        from openai import OpenAI
    except ImportError:
        return AgentReply("The OpenAI package is not installed. Install requirements and retry.", [], [], "missing_dependency")
    if not os.getenv("OPENAI_API_KEY"):
        return AgentReply("OPENAI_API_KEY is not configured. Add it to a local .env file or use demo mode.", [], [], "missing_api_key")
    client = OpenAI()
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": question}]
    evidence, activity = [], []
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto")
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            if not message.tool_calls:
                return AgentReply(message.content or "I could not generate a response.", evidence, activity)
            for call in message.tool_calls:
                try:
                    arguments = json.loads(call.function.arguments)
                    tool = TOOL_FUNCTIONS.get(call.function.name)
                    result = tool(**arguments) if tool else {"success": False, "error": "Unknown tool requested."}
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    result = {"success": False, "error": f"Invalid tool arguments: {exc}"}
                evidence.append(result); activity.append(f"Used {call.function.name}")
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        return AgentReply("I reached the safe tool-call limit before completing the analysis. Please narrow the question.", evidence, activity, "tool_limit")
    except Exception as exc:
        return AgentReply("The model service is unavailable right now. Please try again later or use demo mode.", evidence, activity, type(exc).__name__)


def answer(question: str, history: list[dict[str, str]] | None = None) -> AgentReply:
    if not question.strip(): return AgentReply("Please enter a business question.", [], [])
    if os.getenv("AGENT_MODE", "demo").lower() == "openai":
        return _openai_reply(question, history or [])
    return _demo_reply(question)
