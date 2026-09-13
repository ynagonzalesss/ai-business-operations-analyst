"""Fail fast if the safe demo dataset violates its documented rules."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import connection


def validate() -> list[str]:
    checks = {
        "duplicate property/month records": "SELECT property_id, month FROM monthly_performance GROUP BY property_id, month HAVING COUNT(*) > 1",
        "invalid month strings": "SELECT month FROM monthly_performance WHERE date(month) IS NULL",
        "invalid nights": "SELECT * FROM monthly_performance WHERE booked_nights > available_nights OR booked_nights < 0 OR available_nights < 0",
        "negative financial or booking values": "SELECT * FROM monthly_performance WHERE revenue < 0 OR operating_cost < 0 OR bookings < 0 OR cancellations < 0",
        "cancellations above bookings": "SELECT * FROM monthly_performance WHERE cancellations > bookings",
        "missing required values": "SELECT * FROM monthly_performance WHERE property_id IS NULL OR month IS NULL OR revenue IS NULL",
    }
    failures = []
    with connection() as conn:
        for name, query in checks.items():
            if conn.execute(query).fetchone():
                failures.append(name)
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        raise SystemExit("Validation failed: " + ", ".join(errors))
    print("Data validation passed.")
