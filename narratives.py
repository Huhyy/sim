import re

def load_narratives(path="narratives.txt"):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split by "Luna X –"
    chunks = re.split(r"Luna\s+(\d+)\s+–", text)

    narratives = {}

    # chunks format:
    # ["", "1", "text1", "2", "text2", ...]
    for i in range(1, len(chunks), 2):
        month = int(chunks[i])
        content = chunks[i + 1].strip()
        narratives[month] = content

    return narratives


# cache once
NARRATIVES = load_narratives()


def get_narrative(month):
    return NARRATIVES.get(month, "No narrative available.")