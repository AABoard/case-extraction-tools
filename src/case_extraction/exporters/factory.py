"""Factory for case exporters (Open/Closed Principle)."""

from pathlib import Path
from typing import Iterable

from .base import CaseExporter
from .json_exporter import JsonExporter
from .pdf_exporter import PdfExporter
from .html_exporter import HtmlExporter

_REGISTRY: dict[str, type[CaseExporter]] = {
    "json": JsonExporter,
    "pdf": PdfExporter,
    "html": HtmlExporter,
}


def get_exporter(format_name: str) -> CaseExporter:
    """Return exporter for format (json, pdf, html)."""
    key = format_name.lower().strip()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown format: {format_name}. Use: {', '.join(_REGISTRY)}")
    return _REGISTRY[key]()


def get_exporters_for_formats(formats: Iterable[str]) -> list[CaseExporter]:
    """Return list of exporters for given format names."""
    return [get_exporter(f) for f in formats]
