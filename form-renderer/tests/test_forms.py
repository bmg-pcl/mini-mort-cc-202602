"""Tests for form loading and validation utilities."""

import json
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forms import DEFAULT_FORM, get_all_elements, load_form, validate_responses


@pytest.fixture
def sample_form():
    return load_form(DEFAULT_FORM)


def test_load_default_form(sample_form):
    assert "title" in sample_form
    assert "pages" in sample_form
    assert len(sample_form["pages"]) > 0


def test_get_all_elements(sample_form):
    elements = get_all_elements(sample_form)
    assert len(elements) > 0
    names = [e["name"] for e in elements]
    assert "full_name" in names
    assert "email" in names


def test_validate_responses_missing_required(sample_form):
    errors = validate_responses(sample_form, {})
    assert len(errors) > 0
    assert any("Full Name" in e for e in errors)


def test_validate_responses_all_present(sample_form):
    responses = {
        "full_name": "Alice",
        "email": "alice@example.com",
        "overall_rating": 5,
    }
    errors = validate_responses(sample_form, responses)
    assert len(errors) == 0


def test_default_form_file_exists():
    assert DEFAULT_FORM.exists()
    data = json.loads(DEFAULT_FORM.read_text())
    assert "pages" in data
