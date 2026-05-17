"""Tests for validators."""

import pytest

from case_extraction.validators import validate_case, normalize_case


def test_normalize_case_empty():
    out = normalize_case({})
    assert out.get("summary")
    assert out.get("case_id")
    assert out.get("case_type") == "Research Summary"
    assert out.get("status") == "Completed"


def test_normalize_case_partial():
    raw = {"summary": "Test", "implementing_organization": {"location": "Boston"}}
    out = normalize_case(raw)
    assert out["summary"] == "Test"
    assert out["implementing_organization"]["location"] == "Boston"


def test_validate_sample_case():
    from pathlib import Path
    from case_extraction.pdf_export import load_case
    sample = Path(__file__).parent.parent / "config" / "schema" / "sample_case.json"
    case = load_case(sample)
    result = validate_case(case)
    assert result.valid
    assert result.normalized
