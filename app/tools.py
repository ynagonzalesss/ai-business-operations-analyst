"""Validated, deterministic tools exposed to the analyst agent."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.db import connection

ALLOWED_FIELDS = {"month", "available_nights", "booked_nights", "revenue", "operating_cost", "cancellations", "bookings"}
ALLOWED_METRICS = {"revenue", "occupancy", "adr", "revpar", "contribution_margin", "cancellation_rate", "booked_nights"}


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _result(name: str, started: float, data: Any = None, error: str | None = None) -> dict[str, Any]:
    return ToolResult(not bool(error), data, error, {"tool": name, "duration_ms": round((time.perf_counter() - started) * 1000, 1)}).to_dict()


def _valid_month(value: str | None) -> bool:
    return value is None or (len(value) == 7 and value[4] == "-" and value[:4].isdigit() and value[5:].isdigit() and 1 <= int(value[5:]) <= 12)


def _property_ids(property_id: int | None) -> tuple[bool, list[int] | str]:
    if property_id is None:
        return True, []
    if not isinstance(property_id, int) or property_id < 1:
        return False, "property_id must be a positive integer."
    with connection() as conn:
        exists = conn.execute("SELECT 1 FROM properties WHERE property_id = ?", (property_id,)).fetchone()
    return (True, [property_id]) if exists else (False, f"Property {property_id} does not exist in this portfolio.")


def _where(property_id: int | None, start_month: str | None, end_month: str | None) -> tuple[str, list[Any]]:
    terms, args = [], []
    if property_id is not None:
        terms.append("mp.property_id = ?"); args.append(property_id)
    if start_month:
        terms.append("mp.month >= ?"); args.append(f"{start_month}-01")
    if end_month:
        terms.append("mp.month <= ?"); args.append(f"{end_month}-31")
    return (" WHERE " + " AND ".join(terms)) if terms else "", args


def query_data(property_id: int | None = None, start_month: str | None = None, end_month: str | None = None, fields: list[str] | None = None) -> dict[str, Any]:
    """Retrieve non-sensitive monthly records using a controlled parameterized query."""
    started = time.perf_counter()
    valid, value = _property_ids(property_id)
    if not valid: return _result("query_data", started, error=str(value))
    if not _valid_month(start_month) or not _valid_month(end_month) or (start_month and end_month and start_month > end_month):
        return _result("query_data", started, error="Use YYYY-MM months with start_month no later than end_month.")
    fields = fields or sorted(ALLOWED_FIELDS)
    if not isinstance(fields, list) or not set(fields).issubset(ALLOWED_FIELDS):
        return _result("query_data", started, error=f"fields must be selected from: {sorted(ALLOWED_FIELDS)}")
    where, args = _where(property_id, start_month, end_month)
    selected = ", ".join(f"mp.{field}" for field in fields)
    query = f"SELECT p.property_id, p.property_name, {selected} FROM monthly_performance mp JOIN properties p ON p.property_id = mp.property_id{where} ORDER BY mp.month, p.property_id"
    with connection() as conn:
        rows = [dict(row) for row in conn.execute(query, args).fetchall()]
    return _result("query_data", started, {"rows": rows, "row_count": len(rows), "period": {"start_month": start_month, "end_month": end_month}})


def _kpis(where: str, args: list[Any], group: bool = False) -> list[dict[str, Any]]:
    select = "p.property_id, p.property_name," if group else ""
    grouping = " GROUP BY p.property_id, p.property_name" if group else ""
    query = f"""SELECT {select}
      SUM(mp.available_nights) AS available_nights, SUM(mp.booked_nights) AS booked_nights,
      ROUND(SUM(mp.revenue), 2) AS revenue, ROUND(SUM(mp.operating_cost), 2) AS operating_cost,
      SUM(mp.cancellations) AS cancellations, SUM(mp.bookings) AS bookings,
      ROUND(CAST(SUM(mp.booked_nights) AS REAL) / NULLIF(SUM(mp.available_nights), 0), 4) AS occupancy,
      ROUND(SUM(mp.revenue) / NULLIF(SUM(mp.booked_nights), 0), 2) AS adr,
      ROUND(SUM(mp.revenue) / NULLIF(SUM(mp.available_nights), 0), 2) AS revpar,
      ROUND(SUM(mp.revenue) - SUM(mp.operating_cost), 2) AS contribution_margin,
      ROUND(CAST(SUM(mp.cancellations) AS REAL) / NULLIF(SUM(mp.bookings), 0), 4) AS cancellation_rate
      FROM monthly_performance mp JOIN properties p ON p.property_id = mp.property_id{where}{grouping}"""
    with connection() as conn:
        return [dict(row) for row in conn.execute(query, args).fetchall()]


def calculate_kpis(property_id: int | None = None, start_month: str | None = None, end_month: str | None = None) -> dict[str, Any]:
    """Calculate standardized portfolio KPIs in SQLite, never in the language model."""
    started = time.perf_counter(); valid, value = _property_ids(property_id)
    if not valid: return _result("calculate_kpis", started, error=str(value))
    if not _valid_month(start_month) or not _valid_month(end_month) or (start_month and end_month and start_month > end_month):
        return _result("calculate_kpis", started, error="Use valid YYYY-MM month boundaries.")
    where, args = _where(property_id, start_month, end_month)
    return _result("calculate_kpis", started, {"kpis": _kpis(where, args), "period": {"start_month": start_month, "end_month": end_month}})


def compare_properties(property_ids: list[int] | str, start_month: str | None = None, end_month: str | None = None) -> dict[str, Any]:
    """Compare a selected set of properties, or every property when given 'portfolio'."""
    started = time.perf_counter()
    if not _valid_month(start_month) or not _valid_month(end_month) or (start_month and end_month and start_month > end_month):
        return _result("compare_properties", started, error="Use valid YYYY-MM month boundaries.")
    if property_ids != "portfolio" and (not isinstance(property_ids, list) or len(property_ids) < 2 or not all(isinstance(x, int) for x in property_ids)):
        return _result("compare_properties", started, error="property_ids must be 'portfolio' or a list of at least two numeric property IDs.")
    if property_ids == "portfolio":
        filter_sql, args = "", []
    else:
        placeholders = ",".join("?" for _ in property_ids)
        filter_sql, args = f" WHERE mp.property_id IN ({placeholders})", list(property_ids)
        with connection() as conn:
            found = conn.execute(f"SELECT COUNT(*) FROM properties WHERE property_id IN ({placeholders})", args).fetchone()[0]
        if found != len(set(property_ids)): return _result("compare_properties", started, error="One or more property IDs do not exist.")
    date_where, date_args = _where(None, start_month, end_month)
    if filter_sql and date_where: filter_sql += " AND " + date_where.removeprefix(" WHERE ")
    elif not filter_sql: filter_sql = date_where
    rows = _kpis(filter_sql, args + date_args, group=True)
    portfolio = _kpis(date_where, date_args)[0]
    for row in rows:
        row["vs_portfolio_revpar_pct"] = round((row["revpar"] / portfolio["revpar"] - 1) * 100, 1) if portfolio["revpar"] else None
    return _result("compare_properties", started, {"properties": rows, "portfolio_benchmark": portfolio, "period": {"start_month": start_month, "end_month": end_month}})


def analyze_trends(property_id: int, metric: str, start_month: str | None = None, end_month: str | None = None) -> dict[str, Any]:
    """Measure a supported metric over time and report an evidence-based direction."""
    started = time.perf_counter(); valid, value = _property_ids(property_id)
    if not valid: return _result("analyze_trends", started, error=str(value))
    if metric not in ALLOWED_METRICS: return _result("analyze_trends", started, error=f"metric must be one of: {sorted(ALLOWED_METRICS)}")
    if not _valid_month(start_month) or not _valid_month(end_month) or (start_month and end_month and start_month > end_month): return _result("analyze_trends", started, error="Use valid YYYY-MM month boundaries.")
    where, args = _where(property_id, start_month, end_month)
    metric_expr = {"revenue": "revenue", "booked_nights": "booked_nights", "occupancy": "CAST(booked_nights AS REAL)/NULLIF(available_nights,0)", "adr": "revenue/NULLIF(booked_nights,0)", "revpar": "revenue/NULLIF(available_nights,0)", "contribution_margin": "revenue-operating_cost", "cancellation_rate": "CAST(cancellations AS REAL)/NULLIF(bookings,0)"}[metric]
    with connection() as conn:
        rows = [dict(row) for row in conn.execute(f"SELECT month, ROUND({metric_expr}, 4) AS value FROM monthly_performance mp{where} ORDER BY month", args).fetchall()]
    if len(rows) < 2: return _result("analyze_trends", started, error="At least two monthly records are required for a trend.")
    change = round(rows[-1]["value"] - rows[0]["value"], 4)
    direction = "increased" if change > 0 else "decreased" if change < 0 else "was flat"
    return _result("analyze_trends", started, {"property_id": property_id, "metric": metric, "monthly_values": rows, "change": change, "direction": direction})


TOOL_FUNCTIONS = {"query_data": query_data, "calculate_kpis": calculate_kpis, "compare_properties": compare_properties, "analyze_trends": analyze_trends}

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "query_data", "description": "Retrieve validated monthly business records.", "parameters": {"type": "object", "properties": {"property_id": {"type": "integer"}, "start_month": {"type": "string", "description": "YYYY-MM"}, "end_month": {"type": "string", "description": "YYYY-MM"}, "fields": {"type": "array", "items": {"type": "string", "enum": sorted(ALLOWED_FIELDS)}}}}}},
    {"type": "function", "function": {"name": "calculate_kpis", "description": "Calculate deterministic revenue, occupancy, ADR, RevPAR, margin, and cancellation KPIs.", "parameters": {"type": "object", "properties": {"property_id": {"type": "integer"}, "start_month": {"type": "string"}, "end_month": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "compare_properties", "description": "Benchmark two or more properties or the full portfolio.", "parameters": {"type": "object", "properties": {"property_ids": {"oneOf": [{"type": "string", "enum": ["portfolio"]}, {"type": "array", "items": {"type": "integer"}, "minItems": 2}]}, "start_month": {"type": "string"}, "end_month": {"type": "string"}}, "required": ["property_ids"]}}},
    {"type": "function", "function": {"name": "analyze_trends", "description": "Analyze a supported metric across months for one property.", "parameters": {"type": "object", "properties": {"property_id": {"type": "integer"}, "metric": {"type": "string", "enum": sorted(ALLOWED_METRICS)}, "start_month": {"type": "string"}, "end_month": {"type": "string"}}, "required": ["property_id", "metric"]}}},
]
