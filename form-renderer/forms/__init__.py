"""Survey.js form loading and parsing utilities."""

import json
from pathlib import Path
from typing import Any


def load_form(path: str | Path) -> dict[str, Any]:
    """Load a survey.js JSON form definition from disk."""
    with open(path) as f:
        return json.load(f)


def get_all_elements(form: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all elements across all pages."""
    elements = []
    for page in form.get("pages", []):
        elements.extend(page.get("elements", []))
    return elements


def validate_responses(form: dict[str, Any], responses: dict[str, Any]) -> list[str]:
    """Check required fields are present. Returns list of error messages."""
    errors = []
    for el in get_all_elements(form):
        if el.get("isRequired") and not responses.get(el["name"]):
            errors.append(f"Field '{el.get('title', el['name'])}' is required.")
    return errors


DEFAULT_FORM = Path(__file__).parent / "sample_survey.json"
