"""Narrative content."""

import re
from pathlib import Path

NARRATIVES_PATH = Path(__file__).resolve().parents[2] / "narratives.txt"


def load_narratives(path=NARRATIVES_PATH):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split by "Luna X –"
    chunks = re.split("Luna\\s+(\\d+)\\s+\u2013", text)

    narratives = {}

    # chunks format:
    # ["", "1", "text1", "2", "text2", ...]
    for i in range(1, len(chunks), 2):
        month = int(chunks[i])
        content = chunks[i + 1].strip()
        narratives[month] = content

    return narratives


NARRATIVES = load_narratives()


def get_narrative(month):
    return NARRATIVES.get(month, "No narrative available.")


__all__ = [
    "NARRATIVES",
    "NARRATIVES_PATH",
    "get_narrative",
    "load_narratives",
]
