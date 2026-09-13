"""Safe database creation and read-only access for the demo portfolio."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "portfolio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS properties (
    property_id INTEGER PRIMARY KEY,
    property_name TEXT NOT NULL UNIQUE,
    market TEXT NOT NULL,
    property_type TEXT NOT NULL,
    bedrooms INTEGER NOT NULL CHECK (bedrooms > 0)
);
CREATE TABLE IF NOT EXISTS monthly_performance (
    property_id INTEGER NOT NULL REFERENCES properties(property_id),
    month TEXT NOT NULL,
    available_nights INTEGER NOT NULL CHECK (available_nights >= 0),
    booked_nights INTEGER NOT NULL CHECK (booked_nights >= 0 AND booked_nights <= available_nights),
    revenue REAL NOT NULL CHECK (revenue >= 0),
    operating_cost REAL NOT NULL CHECK (operating_cost >= 0),
    cancellations INTEGER NOT NULL CHECK (cancellations >= 0),
    bookings INTEGER NOT NULL CHECK (bookings >= 0 AND cancellations <= bookings),
    PRIMARY KEY (property_id, month)
);
"""


def connection(read_only: bool = True, db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Return a SQLite connection; agent calls use immutable-style read-only mode."""
    if read_only:
        if not db_path.exists():
            raise FileNotFoundError("Portfolio database is missing. Run scripts/seed_data.py first.")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(db_path: Path = DATABASE_PATH) -> None:
    """Create the schema used by the synthetic demo dataset."""
    with connection(False, db_path) as conn:
        conn.executescript(SCHEMA)
