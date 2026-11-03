
import re

RULES = [
    (
        "decision",
        re.compile(
            r"^\s*(?:decision|decided|we decided)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "task",
        re.compile(
            r"^\s*(?:TODO|TASK|ACTION ITEM)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "blocker",
        re.compile(
            r"^\s*(?:BLOCKER|BLOCKED BY)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "risk",
        re.compile(
            r"^\s*RISK\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "dependency",
        re.compile(
            r"^\s*(?:DEPENDENCY|DEPENDS ON)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "open_question",
        re.compile(
            r"^\s*(?:QUESTION|OPEN QUESTION)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "api",
        re.compile(
            r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+(/api/[^\s,;]+)",
            re.IGNORECASE,
        ),
    ),
]


def extract_candidates(text):
    """
    Extract only claims with explicit textual signals.
    Every result includes the original evidence line.
    """
    candidates = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()

        if not line:
            continue

        for item_type, pattern in RULES:
            match = pattern.search(line)

            if not match:
                continue

            if item_type == "api":
                title = match.group(1).rstrip(".,)")
            else:
                title = match.group(1).strip()

            if not title:
                continue

            candidates.append({
                "item_type": item_type,
                "title": title[:255],
                "description": line,
                "evidence_text": line,
                "evidence_location": {
                    "line": line_number,
                },
            })

    return candidates
