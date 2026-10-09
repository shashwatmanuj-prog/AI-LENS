
"""Robust JSON extraction from model output.

Gemma may return JSON inside Markdown fences or include explanatory text.
Extract the first valid JSON object and tolerate trailing commas.
"""

from __future__ import annotations

import json
import re
from typing import Any


_FENCE = re.compile(
    r"```(?:json)?\s*(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class ModelOutputError(ValueError):
    """The model's reply could not be turned into the expected JSON object."""


def _first_balanced_object(text: str) -> str | None:
    """Find the first complete JSON object while respecting quoted strings."""
    start = text.find("{")

    while start != -1:
        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]

            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1

                if depth == 0:
                    return text[start : i + 1]

        start = text.find("{", start + 1)

    return None


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract and decode a JSON object from model-generated text."""
    if not text or not text.strip():
        raise ModelOutputError("Model returned an empty response.")

    text = text.lstrip("\ufeff").strip()

    # Prefer fenced JSON, then inspect the full response.
    candidates = _FENCE.findall(text)
    candidates.append(text)

    for candidate in candidates:
        obj = _first_balanced_object(candidate)

        if obj is None:
            continue

        try:
            parsed = json.loads(obj)
        except json.JSONDecodeError:
            # Tolerate trailing commas, e.g. {"items": [],}
            cleaned = re.sub(r",\s*([}\]])", r"\1", obj)

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                continue

        if isinstance(parsed, dict):
            return parsed

    raise ModelOutputError(
        "Could not find a valid JSON object in the model response."
    )
