"""Create reproducible synthetic portfolio data with intentional performance patterns."""
from __future__ import annotations

import calendar
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import DATABASE_PATH, create_schema

PROPERTIES = [
    (1, "Harbor House", "Seattle", "Apartment", 2, 0.78, 175, 0.37, 0.05),
    (2, "Desert View", "Phoenix", "Condo", 1, 0.73, 145, 0.39, 0.04),
    (3, "Lakeside Loft", "Austin", "Apartment", 2, 0.84, 205, 0.35, 0.03),
    (4, "Summit Cabin", "Denver", "Cabin", 3, 0.62, 260, 0.42, 0.06),
    (5, "Garden Studio", "Portland", "Studio", 1, 0.80, 120, 0.34, 0.04),
    (6, "Coastal Retreat", "San Diego", "House", 3, 0.77, 310, 0.40, 0.05),
    # Purposefully weak booking volume with stable pricing: the key investigation example.
    (7, "Canyon Residence", "Phoenix", "House", 2, 0.51, 190, 0.45, 0.10),
    (8, "Cityline Suite", "Chicago", "Condo", 2, 0.75, 185, 0.38, 0.08),
]


def build_database(path: Path = DATABASE_PATH) -> None:
    if path.exists():
        path.unlink()
    create_schema(path)
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO properties(property_id, property_name, market, property_type, bedrooms) VALUES (?, ?, ?, ?, ?)",
            [row[:5] for row in PROPERTIES],
        )
        rows = []
        for property_id, _, _, _, _, base_occupancy, base_adr, cost_ratio, cancellation_rate in PROPERTIES:
            for month_number in range(1, 13):
                month = f"2025-{month_number:02d}-01"
                days = calendar.monthrange(2025, month_number)[1]
                # Seasonal lift, plus Property 4 recovering over the latter six months.
                seasonal = 0.10 if month_number in (6, 7, 8) else (-0.07 if month_number in (1, 2) else 0)
                recovery = (month_number - 6) * 0.018 if property_id == 4 and month_number > 6 else 0
                occupancy = max(0.30, min(0.94, base_occupancy + seasonal + recovery))
                if property_id == 7 and month_number in (5, 6, 7):
                    occupancy -= 0.06
                available = days
                booked = round(available * occupancy)
                adr = base_adr * (1.12 if month_number in (6, 7, 8) else 0.94 if month_number in (1, 2) else 1)
                revenue = round(booked * adr, 2)
                costs = round(revenue * cost_ratio + available * 8, 2)
                bookings = max(1, round(booked / 3.1))
                cancellations = min(bookings, round(bookings * cancellation_rate))
                rows.append((property_id, month, available, booked, revenue, costs, cancellations, bookings))
        conn.executemany(
            """INSERT INTO monthly_performance
            (property_id, month, available_nights, booked_nights, revenue, operating_cost, cancellations, bookings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    print(f"Created {path} with {len(rows)} monthly records.")


if __name__ == "__main__":
    build_database()
