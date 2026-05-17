"""Paper-to-case pipeline: parse -> extract -> validate -> export."""

from pathlib import Path
from typing import Any

from ..parsers.pdf_parser import extract_text_from_pdf_with_meta
from ..parsers.docx_parser import extract_text_from_docx_with_meta
from ..parsers.text_parser import extract_from_text_with_meta
from ..extractors.case_extractor import extract_case_from_text
from ..validators import validate_case
from ..exporters import get_exporter, get_exporters_for_formats
from .base import BasePipeline, PipelineResult


class PaperToCasePipeline(BasePipeline):
    """Single document: parse -> extract -> validate -> export to selected formats."""

    def __init__(
        self,
        export_formats: list[str] | None = None,
        validate_output: bool = True,
        doc_type_hint: str | None = None,
    ) -> None:
        self.export_formats = export_formats or ["json"]
        self.validate_output = validate_output
        self.doc_type_hint = doc_type_hint

    def _parse(self, path: Path) -> str:
        """Parse document to text based on extension."""
        sfx = path.suffix.lower()
        if sfx == ".pdf":
            text, _ = extract_text_from_pdf_with_meta(path)
            return text
        if sfx in (".docx", ".doc"):
            text, _ = extract_text_from_docx_with_meta(path)
            return text
        if sfx in (".txt", ".md", ".html"):
            text, _ = extract_from_text_with_meta(path)
            return text or ""
        raise ValueError(f"Unsupported format: {sfx}")

    def run(
        self,
        input_path: Path,
        output_dir: Path | None = None,
        output_stem: str | None = None,
        **kwargs: Any,
    ) -> PipelineResult:
        input_path = Path(input_path)
        stem = output_stem or input_path.stem
        out_dir = Path(output_dir) if output_dir else input_path.parent

        try:
            text = self._parse(input_path)
        except Exception as e:
            return PipelineResult(success=False, error=str(e), source_path=input_path)

        try:
            case = extract_case_from_text(
                text,
                document_type_hint=kwargs.get("doc_type") or self.doc_type_hint,
                validate=self.validate_output,
            )
        except Exception as e:
            return PipelineResult(success=False, error=str(e), source_path=input_path)

        exporters = get_exporters_for_formats(self.export_formats)
        for exporter in exporters:
            ext = exporter.file_extension
            out_path = out_dir / f"{stem}_case{ext}"
            try:
                exporter.export(case, out_path)
            except Exception as e:
                return PipelineResult(
                    success=False,
                    error=f"Export {ext}: {e}",
                    source_path=input_path,
                    case=case,
                )

        primary_ext = exporters[0].file_extension if exporters else ".json"
        primary_out = out_dir / f"{stem}_case{primary_ext}"
        return PipelineResult(
            success=True,
            output_path=primary_out,
            case=case,
            source_path=input_path,
        )
