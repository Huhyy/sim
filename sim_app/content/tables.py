"""Monthly financial table content."""

import json
from pathlib import Path

TABLES_PATH = Path(__file__).resolve().parent / "data" / "tables.json"


def load_tables():
    with open(TABLES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


TABLES = load_tables()


def get_month(month: int) -> dict:
    key = str(month)

    if key not in TABLES:
        raise ValueError(f"Month {month} not found in tables.json")

    return TABLES[key]


__all__ = [
    "TABLES",
    "TABLES_PATH",
    "get_month",
    "load_tables",
]
