"""PDF exporter for case records (AAB Case Registry format)."""

from pathlib import Path
from typing import Any

from .base import CaseExporter

# Lazy import to avoid reportlab dependency when not using PDF
def _build_pdf(case: dict[str, Any], output_path: Path) -> None:
    from ..pdf_export import build_pdf
    build_pdf(case, output_path)


class PdfExporter(CaseExporter):
    """Export case to AAB Case Registry PDF."""

    @property
    def format_name(self) -> str:
        return "PDF"

    @property
    def file_extension(self) -> str:
        return ".pdf"

    def export(self, case: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _build_pdf(case, output_path)
