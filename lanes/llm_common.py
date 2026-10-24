from __future__ import annotations

import json

from lanes.base import LaneError, Row, TruncatedAnswer

ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "printed_label": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                    "min": {"type": "string"},
                    "max": {"type": "string"},
                    "verbatim": {"type": "string"},
                },
                "required": ["printed_label", "value", "unit", "min", "max"],
            },
        }
    },
    "required": ["rows"],
}

INSTRUCTIONS = (
    "Extract every measurement row of the calibration certificate page. A row has a parameter "
    "name, a measured value, a unit, a lower and an upper tolerance. Copy numbers exactly as "
    "printed. Return JSON {\"rows\": [...]}. If the page has no measurement rows return "
    "{\"rows\": []}."
)


def parse_rows(page_no: int, completion) -> list[Row]:
    """A length-truncated answer is an error, never an empty page."""
    if completion.truncated:
        raise TruncatedAnswer(f"page {page_no}: answer cut off by the length limit")
    try:
        data = json.loads(completion.text)
        items = data["rows"]
        return [
            Row(page_no, str(d["printed_label"]), str(d["value"]), str(d["unit"]), str(d["min"]),
                str(d["max"]), str(d.get("verbatim", "")))
            for d in items
        ]
    except (ValueError, KeyError, TypeError) as exc:
        raise LaneError(f"page {page_no}: unparseable answer ({exc})") from exc
