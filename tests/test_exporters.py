"""Tests for exporters."""

import tempfile
from pathlib import Path

import pytest

from case_extraction.exporters import JsonExporter, PdfExporter, HtmlExporter, get_exporter
from case_extraction.pdf_export import load_case


@pytest.fixture
def sample_case():
    p = Path(__file__).parent.parent / "config" / "schema" / "sample_case.json"
    return load_case(p)


def test_json_exporter(sample_case):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "case.json"
        JsonExporter().export(sample_case, out)
        assert out.exists()
        assert "case_id" in out.read_text()


def test_html_exporter(sample_case):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "case.html"
        HtmlExporter().export(sample_case, out)
        assert out.exists()
        assert "AAB-CASE" in out.read_text()


def test_pdf_exporter(sample_case):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "case.pdf"
        PdfExporter().export(sample_case, out)
        assert out.exists()
        assert out.stat().st_size > 0


def test_get_exporter():
    assert get_exporter("json").format_name == "JSON"
    assert get_exporter("html").file_extension == ".html"
    with pytest.raises(ValueError):
        get_exporter("xyz")
