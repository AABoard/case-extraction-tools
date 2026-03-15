"""Tests for pipelines."""

from pathlib import Path

import pytest

from case_extraction.pipelines import PaperToCasePipeline, BatchIngestPipeline


def test_paper_pipeline_requires_llm():
    """PaperToCasePipeline needs real doc + LLM; test structure only."""
    p = PaperToCasePipeline(export_formats=["json"], validate_output=True)
    assert p.export_formats == ["json"]
    assert p.validate_output is True


def test_batch_discover_extensions():
    batch = BatchIngestPipeline()
    assert ".pdf" in [e.lower() for e in batch.extensions]


def test_batch_single_file(tmp_path):
    """Batch with single supported file discovers it."""
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"dummy")
    batch = BatchIngestPipeline(extensions=[".pdf"])
    paths = batch._discover_inputs(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "doc.pdf"
